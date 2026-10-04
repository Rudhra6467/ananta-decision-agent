"""The eye: one fast tracker on live prices (Madhav, 2026-10-03: "a set of rules watching and an eye like tracker").

Every 10 seconds it reads the live price of our 10 coins (Kraken's public ticker: the same market Hands uses; no keys) and
checks them against the levels the slower sections ARM (docs/knowledge/watches.json, trigger = level_cross):

  MY_STOPS      your own paper positions' stops and targets          -> sold at the live price, phone note
  PRICE_ALERTS  your "tell me if X goes above / below / moves" lines -> phone note
  BTC_SHOCK     Bitcoin down 2% or more within 15 minutes            -> phone note (at most once an hour)
  ZONE_ENTRY    the live price comes down into a support zone        -> feed; phone when the coin's attention is HIGH
  ZONE_TOUCH    ...a zone kind history supports, market allowed      -> a $100 evidence trade (watch_engine), stop checked live

Bar-close rules are NOT checked here: a 15-minute rule cannot change between closes. The Explorer keeps its own execution on
5-minute candles (so live and history replay stay the same engine). If the ticker cannot be reached, the eye falls back to
the Explorer's last 5-minute prices and says so.

Paper only. Runs as one thread inside the Jarvis service (start()); tick() is plain and testable.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from typing import Any, Callable

INTERVAL = 10
SHOCK_PCT, SHOCK_WINDOW, SHOCK_COOLDOWN = -2.0, 15 * 60, 60 * 60
ZONE_REPEAT_S, ZONE_PUSH_COOLDOWN, ZONE_TOUCH_GAP = 6 * 3600, 6 * 3600, 20 * 86400
ARM_EVERY = 15 * 60
KRAKEN = {"BTC": ("XBTUSD", "XXBTZUSD"), "ETH": ("ETHUSD", "XETHZUSD"), "SOL": ("SOLUSD",), "ADA": ("ADAUSD",), "DOGE": ("XDGUSD", "XXDGZUSD"),
          "AVAX": ("AVAXUSD",), "BCH": ("BCHUSD",), "LINK": ("LINKUSD",), "LTC": ("LTCUSD", "XLTCZUSD"), "XRP": ("XRPUSD", "XXRPZUSD")}

STATE: dict[str, Any] = {"running": False, "started": None, "last_t": None, "source": None, "ticks": 0, "errors": 0, "last_error": None,
                         "prices": {}, "armed": {}, "armed_t": 0.0, "events_today": 0}
_hist: dict[str, deque] = {}
_cool: dict[str, float] = {}
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# prices
# ---------------------------------------------------------------------------
def fetch_kraken(get=None) -> dict[str, float]:
    import requests

    get = get or requests.get
    r = get("https://api.kraken.com/0/public/Ticker", params={"pair": ",".join(v[0] for v in KRAKEN.values())}, timeout=8)
    d = r.json()
    if d.get("error"):
        raise RuntimeError("kraken: " + "; ".join(d["error"])[:120])
    res = d.get("result") or {}
    out = {}
    for coin, names in KRAKEN.items():
        key = next((n for n in names if n in res), None)
        if key:
            out[coin] = float(res[key]["c"][0])
    if len(out) < 8:
        raise RuntimeError(f"kraken returned {len(out)} of 10 prices")
    return out


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------
def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS eye_events (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, coin TEXT, price REAL, title TEXT, body TEXT, "
                 "pushed INTEGER, detail TEXT)")


def _event(j, kind: str, coin: str | None, price: float | None, title: str, body: str, push: Callable | None, detail: dict | None = None) -> dict:
    pushed = 0
    if push:
        try:
            push(title, body)
            pushed = 1
        except Exception:  # noqa: BLE001  never break the eye
            pushed = 0
    e = {"id": uuid.uuid4().hex[:12], "t": int(j.now()), "kind": kind, "coin": coin, "price": price, "title": title, "body": body,
         "pushed": pushed, "detail": json.dumps(detail or {}, default=str)}
    j.db.execute("INSERT INTO eye_events VALUES (?,?,?,?,?,?,?,?,?)", tuple(e[k] for k in ("id", "t", "kind", "coin", "price", "title", "body", "pushed", "detail")))
    j.db.commit()
    STATE["events_today"] = STATE.get("events_today", 0) + 1
    return e


def recent(j, hours: float = 72, limit: int = 50) -> list[dict]:
    _table(j)
    rows = j.db.execute("SELECT id, t, kind, coin, price, title, body, pushed FROM eye_events WHERE t >= ? ORDER BY t DESC LIMIT ?",
                        (int(j.now() - hours * 3600), limit)).fetchall()
    return [dict(zip(("id", "t", "kind", "coin", "price", "title", "body", "pushed"), r)) for r in rows]


# ---------------------------------------------------------------------------
# the levels the slower sections arm (refreshed every 15 minutes)
# ---------------------------------------------------------------------------
def arm(j) -> dict:
    """zones per coin (support bands near price, with history and attention), each coin's last daily close (for 'moves X%'
    alerts) and the market regime (Bitcoin vs its 50-day average)."""
    from jarvis.service import watch_engine, zones_watch
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R

    armed: dict[str, Any] = {"zones": {}, "prev_close": {}, "atr": {}, "attention": {}, "regime": None}
    try:
        b = zones_watch.board(j)
        for r in b.get("coins", []):
            armed["zones"][r["coin"]] = [{k: z.get(k) for k in ("bot", "top", "kinds", "history", "side")} for z in r.get("zones", [])
                                         if z.get("side") in ("support", "here")]
            armed["atr"][r["coin"]] = r.get("atr")
            armed["attention"][r["coin"]] = (r.get("attention") or {}).get("level")
    except Exception as exc:  # noqa: BLE001
        armed["zones_error"] = str(exc)[:120]
    try:
        btc = _daily(j, "BTC")
        if btc:
            armed["regime"] = watch_engine.regime_at(R.Series(btc), int(j.now()))
        for c in R.COINS:
            D = btc if c == "BTC" else _daily(j, c)
            if D:
                armed["prev_close"][c] = D[-1][4]
    except Exception as exc:  # noqa: BLE001
        armed["daily_error"] = str(exc)[:120]
    return armed


def _cool_ok(key: str, gap: float, now: float) -> bool:
    if now - _cool.get(key, 0) < gap:
        return False
    _cool[key] = now
    return True


# ---------------------------------------------------------------------------
# one look
# ---------------------------------------------------------------------------
def tick(j, px: dict[str, float], push: Callable | None = None, armed: dict | None = None, source: str = "kraken") -> list[dict]:
    from jarvis.service import watch_engine
    from jarvis.service.alerts import Alerts
    from jarvis.service.manual import Manual

    _table(j)
    watch_engine._table(j)
    now = float(j.now())
    armed = armed if armed is not None else STATE.get("armed") or {}
    prev = dict(STATE.get("prices") or {})
    events: list[dict] = []
    for c, p in px.items():
        _hist.setdefault(c, deque(maxlen=200)).append((now, p))

    # MY_STOPS: your own book, on the live price
    try:
        for f in Manual(j.db, j.now).check_stops(px, push=push):
            events.append(_event(j, "MY_STOP", f.get("coin"), f.get("price"), f"Your {f.get('coin')} paper position was sold",
                                 f"at about ${f.get('price', 0):,.6g} (stop or target reached on the live price)", None, f))
    except Exception as exc:  # noqa: BLE001
        STATE["last_error"] = f"stops: {str(exc)[:100]}"

    # PRICE_ALERTS: your lines, on the live price
    try:
        for a in Alerts(j.db, j.now).check_prices(px, armed.get("prev_close") or {}, push=push):
            events.append(_event(j, "ALERT", a["coin"], px.get(a["coin"]), f"Alert: {a['coin']}", a["message"], None, {"alert": a["id"]}))
    except Exception as exc:  # noqa: BLE001
        STATE["last_error"] = f"alerts: {str(exc)[:100]}"

    # BTC_SHOCK: Bitcoin down 2% or more within 15 minutes
    h = [x for x in _hist.get("BTC", []) if now - x[0] <= SHOCK_WINDOW]
    if h and "BTC" in px:
        top = max(x[1] for x in h)
        drop = 100 * (px["BTC"] / top - 1)
        if drop <= SHOCK_PCT and _cool_ok("shock", SHOCK_COOLDOWN, now):
            mins = int((now - max(x for x in h if x[1] == top)[0]) / 60) or 1
            events.append(_event(j, "BTC_SHOCK", "BTC", px["BTC"], f"Bitcoin fell {abs(drop):.1f}% in {mins} minutes",
                                 f"From about ${top:,.0f} to ${px['BTC']:,.0f}. Open paper trades may hit their stops; nothing needs you unless you want to act.",
                                 push, {"drop_pct": round(drop, 2), "minutes": mins}))

    # ZONE_ENTRY and ZONE_TOUCH: the live price comes down into a support zone
    for c, zones in (armed.get("zones") or {}).items():
        p, p0 = px.get(c), prev.get(c)
        if p is None or p0 is None:
            continue
        for z in zones:
            top, bot = z.get("top"), z.get("bot")
            if top is None or bot is None or not (p0 > top >= p):
                continue
            zkey = f"zone:{c}:{bot:.8g}"
            if not _cool_ok(zkey, ZONE_REPEAT_S, now):
                continue                                          # price hovering at the edge: one entry, not many
            kinds = "+".join(z.get("kinds") or []).lower() or "zone"
            att = (armed.get("attention") or {}).get(c)
            loud = att == "HIGH" and _cool_ok(f"zonepush:{c}", ZONE_PUSH_COOLDOWN, now)
            events.append(_event(j, "ZONE_ENTRY", c, p, f"{c} entered a zone ({kinds})",
                                 f"Price came down into ${bot:,.6g}-{top:,.6g}; history: {z.get('history', 'untested').lower()}. The lookout starts now.",
                                 push if loud else None, {"zone": [bot, top], "kinds": z.get("kinds"), "attention": att}))
            # ZONE_TOUCH (registered 2026-10-03): a supported kind, market allowed, one per coin, not the same zone within 20 days
            if z.get("history") == "SUPPORTED" and armed.get("regime") == "ALLOWED":
                same = False
                for (dj,) in j.db.execute("SELECT detail FROM evidence_trades WHERE watch='ZONE_TOUCH' AND coin=? AND signal_t >= ?",
                                          (c, int(now - ZONE_TOUCH_GAP))).fetchall():
                    zz = (json.loads(dj or "{}").get("zone") or [None])[0]
                    same = same or (zz is not None and abs(zz - bot) <= 1e-9 * max(1.0, abs(bot)))
                atr = (armed.get("atr") or {}).get(c) or 0.0
                stop = round(bot - 0.5 * atr, 10) if atr else None
                if not same:
                    t = watch_engine.open_eye_trade(j, "ZONE_TOUCH", c, p, stop, f"entered a {kinds} zone ({z.get('history', '').lower()}), market allowed",
                                                    {"zone": [bot, top], "kinds": z.get("kinds"), "atr": atr}, armed.get("regime"))
                    if t:
                        events.append(_event(j, "ZONE_TOUCH", c, p, f"Evidence trade: {c} zone touch",
                                             f"$100 paper at about ${p:,.6g}; stop ${stop:,.6g} (half a daily range under the zone), else 20 days." if stop else
                                             f"$100 paper at about ${p:,.6g}; 20 days.", None, {"trade": t["id"]}))

    # evidence trades opened by the eye: their stops, on the live price
    try:
        for t in watch_engine.open_with_stops(j):
            p = px.get(t["coin"])
            if p is not None and p <= t["stop"]:
                r = watch_engine.close_at(j, t["id"], p, "stop (live price)")
                if r:
                    events.append(_event(j, "EVIDENCE_EXIT", t["coin"], p, f"Evidence trade closed: {t['coin']} {t['watch'].lower().replace('_', ' ')}",
                                         f"Stop reached at about ${p:,.6g}: {'+' if r['net_usd'] >= 0 else '-'}${abs(r['net_usd']):.2f} on $100.", None, r))
    except Exception as exc:  # noqa: BLE001
        STATE["last_error"] = f"evidence stops: {str(exc)[:100]}"

    STATE.update(prices=dict(px), last_t=now, source=source, ticks=STATE.get("ticks", 0) + 1)
    return events


# ---------------------------------------------------------------------------
# the loop
# ---------------------------------------------------------------------------
def start(get_j: Callable[[], Any], push: Callable | None = None, interval: float = INTERVAL) -> bool:
    """One thread inside the Jarvis service. Safe to call twice (the second call does nothing)."""
    with _lock:
        if STATE.get("running"):
            return False
        STATE.update(running=True, started=time.time())

    def loop():
        fails = 0
        while STATE.get("running"):
            t0 = time.time()
            try:
                j = get_j()
                if time.time() - STATE.get("armed_t", 0) > ARM_EVERY:
                    STATE["armed"], STATE["armed_t"] = arm(j), time.time()
                try:
                    px, src = fetch_kraken(), "kraken"
                    fails = 0
                except Exception as exc:  # noqa: BLE001  the ticker is down: the Explorer's last 5-minute prices, and say so
                    fails += 1
                    STATE["last_error"] = f"ticker: {str(exc)[:100]}"
                    px, src = (j.prices() if fails % 6 == 1 else {}), "explorer 5m (ticker down)"
                if px:
                    tick(j, px, push=push, source=src)
            except Exception as exc:  # noqa: BLE001  never let the eye die
                STATE["errors"] = STATE.get("errors", 0) + 1
                STATE["last_error"] = str(exc)[:160]
            time.sleep(max(1.0, interval - (time.time() - t0)))

    threading.Thread(target=loop, name="ananta-eye", daemon=True).start()
    return True


def status(j) -> dict:
    armed = STATE.get("armed") or {}
    n_zones = sum(len(v) for v in (armed.get("zones") or {}).values())
    last = STATE.get("last_t")
    return {"running": bool(STATE.get("running")), "every_seconds": INTERVAL, "source": STATE.get("source"),
            "last_look": time.strftime("%H:%M:%S", time.localtime(last)) if last else None,
            "seconds_since_last_look": round(time.time() - last, 1) if last else None, "looks": STATE.get("ticks", 0),
            "errors": STATE.get("errors", 0), "last_error": STATE.get("last_error"), "prices": STATE.get("prices"),
            "armed": {"zones": n_zones, "regime": armed.get("regime"), "coins_with_zones": sorted(armed.get("zones") or {})},
            "watching": ["your stops and targets", "your price alerts", "a sudden Bitcoin drop (2% in 15 minutes)",
                         "price entering a support zone (and the zone-touch evidence trade)"],
            "recent": recent(j, 72, 20)}
