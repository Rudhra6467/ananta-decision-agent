"""The $500 NDAX book, live on paper (plan D9, D12, D13). The rules are src/research/book500.py, the same code the backtest ran.

Once a day, after the daily candles land (universe_watch.run_daily), step():
  1. marks the book at NDAX's live bids in CAD and feeds the brakes (D12)
  2. sells: H07 trades whose RSI(10) closed over 40 or that are 10 days old; judgment trades whose brain trade closed; the core when
     the dial closed
  3. buys, if the brakes allow: the core when the dial opened; H07 signals on tier-A NDAX coins while the dial is closed; the brain's
     new buys on NDAX coins (judgment sleeve)
Every fill is at NDAX's own ask (buy) or bid (sell) at that moment, plus the 0.20% fee, and the quantity follows the instrument's
minimum and step; each fill records the bid and ask beside it (the execution check). Paper only: nothing is sent to NDAX.
"""
from __future__ import annotations

import json
import time

from src.research import book500 as B

DAY = 86400
_CACHE: dict = {}


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS book500 (k TEXT PRIMARY KEY, v TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS book500_fills (t INTEGER, coin TEXT, side TEXT, sleeve TEXT, qty REAL, px REAL, bid REAL, ask REAL, "
                 "fee REAL, why TEXT)")


def _get(j, k: str, default=None):
    r = j.db.execute("SELECT v FROM book500 WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default


def _put(j, k: str, v) -> None:
    j.db.execute("INSERT OR REPLACE INTO book500 VALUES (?,?)", (k, json.dumps(v)))


def _http(url: str):
    import requests

    return requests.get(url, timeout=20).json()


def instruments(get=None) -> dict:
    if _CACHE.get("inst_t", 0) > time.time() - DAY and _CACHE.get("inst"):
        return _CACHE["inst"]
    _CACHE["inst"] = B.instruments(get or _http)
    _CACHE["inst_t"] = time.time()
    return _CACHE["inst"]


def fx(get=None) -> float:
    """USD -> CAD, the Bank of Canada's latest daily rate."""
    if _CACHE.get("fx_t", 0) > time.time() - 6 * 3600 and _CACHE.get("fx"):
        return _CACHE["fx"]
    d = (get or _http)("https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1")
    _CACHE["fx"] = float(d["observations"][-1]["FXUSDCAD"]["v"])
    _CACHE["fx_t"] = time.time()
    return _CACHE["fx"]


def quote(coin: str, inst: dict, get=None) -> dict | None:
    """NDAX's best bid and ask in CAD now."""
    k = inst.get(coin)
    if not k:
        return None
    try:
        d = (get or _http)(f"https://api.ndax.io:8443/AP/GetLevel1?OMSId=1&InstrumentId={k['id']}")
        bid, ask = float(d.get("BestBid") or 0), float(d.get("BestOffer") or 0)
        return {"bid": bid, "ask": ask} if bid > 0 and ask >= bid else None
    except Exception:  # noqa: BLE001
        return None


def passed_rules(j, dial) -> list[str]:
    """The rules allowed into the edge sleeve now (Madhav, Oct 13: "pushing whatever passed"): a measured cell for tier A in this dial
    state that passed on history in both periods (review #26's table), AND the strategy ACTIVE or the rule PROMOTED on the ladder."""
    from jarvis.service import ev, strategy_status, universe_watch

    state = "OPEN" if dial else "CLOSED"
    try:
        prom = universe_watch.promoted(j)
    except Exception:  # noqa: BLE001
        prom = set()
    out = []
    for r in ev.table():
        if r["state"] != state or r["tier"] != "A":
            continue
        e = strategy_status.of_watch(r["rule"])
        active = bool(e and e[1].get("status") == "ACTIVE")
        if active or f"{r['rule']}-UA" in prom:
            out.append(r["rule"])
    return sorted(set(out))


def edge_signals(j, C: dict, tier_a: list[str], dial, bar_t: int) -> list[tuple[str, str, str]]:
    """(coin, rule, why) for today's signals of the passed rules on tier-A NDAX coins. H07 is read from the candles here; any other
    rule's signal is the universe book's row opened on this close (universe_watch runs before the book each night)."""
    out = []
    rules = passed_rules(j, dial)
    if "H07" in rules:
        for c in sorted(tier_a, key=lambda x: (C[x].rsi10[-1] if x in C and C[x].rsi10[-1] is not None else 99)):
            if c in C and B.h07(C[c], len(C[c].t) - 1):
                out.append((c, "H07", f"H07: RSI(10) {C[c].rsi10[-1]:.0f}, above the 200-day"))
    others = [r for r in rules if r != "H07"]
    if others:
        day = B._day(bar_t)
        marks = ",".join("?" for _ in others)
        rows = j.db.execute(f"SELECT coin, watch FROM evidence_trades WHERE signal_day=? AND status IN ('OPEN','WAITING') AND watch IN ({marks})",
                            (day, *[f"{r}-UA" for r in others])).fetchall()
        for coin, watch in rows:
            if coin in C and coin in tier_a:
                out.append((coin, watch.split("-U")[0], f"{watch.split('-U')[0]}: passed on history and the ladder; signal on this close"))
    return out


def _coins(j, inst: dict, rate: float) -> tuple[dict, list[str]]:
    from jarvis.service import feed, registry

    reg = registry.load(j)
    tier_a = sorted(c for c, k in reg.get("coins", {}).items() if k.get("ndax") and k.get("tier") == "A" and c in inst)
    C = {}
    for c in sorted(set(tier_a) | set(B.CORE)):
        D = feed.daily(j, c)
        if len(D) >= 210:
            C[c] = B.Coin([(b[0], b[1] * rate, b[2] * rate, b[3] * rate, b[4] * rate) for b in D])
    return C, tier_a


def _brakes(state: dict | None) -> B.Brakes:
    b = B.Brakes(backtest=False)
    for k, v in (state or {}).items():
        setattr(b, k, tuple(v) if k == "week" and v else v)
    return b


def status(j) -> dict:
    _table(j)
    s = _get(j, "state")
    if not s:
        return {"started": False, "note": "the book starts at the next daily close"}
    fills = [dict(zip(("t", "coin", "side", "sleeve", "qty", "px", "bid", "ask", "fee", "why"), r))
             for r in j.db.execute("SELECT * FROM book500_fills ORDER BY t DESC LIMIT 20")]
    inside = j.db.execute("SELECT COUNT(*), SUM(px >= bid - 1e-9 AND px <= ask + 1e-9) FROM book500_fills").fetchone()
    return {"started": s["started"], "value_cad": s.get("value"), "cash_cad": round(s["cash"], 2), "return_pct": round(100 * ((s.get("value") or B.START_CAD) / B.START_CAD - 1), 2),
            "positions": s["pos"], "closed": s.get("closed", [])[-20:], "brakes": {k: s["brakes"].get(k) for k in ("paused", "block_until", "fired", "streak")},
            "brake_log": s["brakes"].get("log", [])[-10:], "dial_open": s.get("dial"), "last_step": s.get("last_step"),
            "execution_check": {"fills": inside[0], "inside_bid_ask": inside[1] or 0}, "recent_fills": fills,
            "rules": "src/research/book500.py (docs/research/BOOK500.md)"}


def audit(j) -> dict:
    """The sizing audit (gate check engine_sizing): every entry, open or closed, against D9."""
    _table(j)
    s = _get(j, "state") or {}
    rows = [dict(p, coin=c) for c, p in (s.get("pos") or {}).items()] + list(s.get("closed") or [])
    bad = []
    for r in rows:
        vp = r.get("value_pct") if "value_pct" in r else round(100 * r["paid"] / (r.get("book_value") or B.START_CAD), 2)
        if r.get("sleeve") == "CORE":
            if vp > 100 * B.CORE.get(r.get("coin"), 0) + 1.0:
                bad.append({**r, "why": "core over its weight"})
        elif (r.get("risk_pct") or 0) > 100 * B.RISK_PER_TRADE + 0.01 or vp > 100 * B.MAX_PER_TRADE + 0.5:
            bad.append({**r, "why": "setup over 0.5% risk or 10% of the book"})
    return {"entries": len(rows), "violations": len(bad), "list": bad[:10]}


def resume(j) -> dict:
    """Madhav resumes the book after the 15% brake paused it (owner only)."""
    _table(j)
    s = _get(j, "state")
    if not s:
        return {"ok": False}
    s["brakes"]["paused"] = False
    s["brakes"]["peak"] = s.get("value")
    s["brakes"].setdefault("log", []).append({"day": time.strftime("%Y-%m-%d"), "brake": "resumed by Madhav"})
    _put(j, "state", s)
    j.db.commit()
    return {"ok": True, "value_cad": s.get("value")}


def step(j, get=None, now: float | None = None) -> dict:
    _table(j)
    now = int(now or time.time())
    inst = instruments(get)
    rate = fx(get)
    C, tier_a = _coins(j, inst, rate)
    if "BTC" not in C:
        return {"error": "no Bitcoin history"}
    btc = C["BTC"]
    bar_t = btc.t[-1]
    s = _get(j, "state") or {"started": time.strftime("%Y-%m-%d", time.gmtime(now)), "cash": B.START_CAD, "pos": {}, "closed": [], "brakes": {},
                                 "judged": []}
    if s.get("last_bar") == bar_t:
        return {"skipped": "already stepped on this close", "bar": B._day(bar_t)}
    brakes = _brakes(s["brakes"])
    Q: dict = {}

    def q(c):
        if c not in Q:
            Q[c] = quote(c, inst, get)
        return Q[c]

    def fill(c, side, sleeve, qty, why):
        k = q(c)
        px = k["ask"] if side == "BUY" else k["bid"]
        fee = qty * px * B.NDAX_FEE
        j.db.execute("INSERT INTO book500_fills VALUES (?,?,?,?,?,?,?,?,?,?)", (now, c, side, sleeve, qty, px, k["bid"], k["ask"], fee, why))
        return px, fee

    def mark() -> float:
        v = s["cash"]
        for c, p in s["pos"].items():
            k = q(c)
            v += p["qty"] * (k["bid"] if k else p["last"])
            if k:
                p["last"] = k["bid"]
        return round(v, 2)

    out: dict = {"bar": B._day(bar_t), "usdcad": rate, "sold": [], "bought": [], "skipped": []}
    closed_pnls = []

    def sell(c, why):
        p = s["pos"][c]
        if not q(c):
            out["skipped"].append(f"{c}: no NDAX quote to sell")
            return
        px, fee = fill(c, "SELL", p["sleeve"], p["qty"], why)
        got = p["qty"] * px - fee
        s["cash"] += got
        pnl = got - p["paid"]
        if p["sleeve"] != "CORE":
            closed_pnls.append(pnl)
        s["closed"].append({"coin": c, "sleeve": p["sleeve"], "in": p["day"], "out": time.strftime("%Y-%m-%d", time.gmtime(now)), "pnl_cad": round(pnl, 2),
                            "pct": round(100 * pnl / p["paid"], 2), "why": why,
                            "risk_pct": p.get("risk_pct"), "value_pct": round(100 * p["paid"] / (p.get("book_value") or B.START_CAD), 2), "dial": p.get("dial")})
        out["sold"].append(f"{c} ({why})")
        del s["pos"][c]

    # 1. exits
    for c in list(s["pos"]):
        p = s["pos"][c]
        S = C.get(c)
        if p["sleeve"] == "EDGE":
            if (S and B.h07_exit(S, len(S.t) - 1)) or now - p["t"] >= B.H07_DAYS * DAY - 3600:
                sell(c, "RSI(10) over 40" if S and B.h07_exit(S, len(S.t) - 1) else "10 days")
        elif p["sleeve"] == "JUDGMENT":
            r = j.db.execute("SELECT status, exit_why FROM evidence_trades WHERE id=?", (p.get("trade_id"),)).fetchone()
            if r and r[0] == "CLOSED":
                sell(c, f"the brain's trade closed ({r[1]})")
    dial = B.dial_open(btc, len(btc.t) - 1)
    if dial is False:
        for c in [c for c, p in s["pos"].items() if p["sleeve"] == "CORE"]:
            sell(c, "dial closed")
    # 2. the book's value and the brakes (on the close just ended; buys follow it, as in the backtest)
    value = mark()
    brakes.close(bar_t, value, closed_pnls)
    may = brakes.may_buy(bar_t + DAY)
    used = lambda sl: sum(p["paid"] for p in s["pos"].values() if p["sleeve"] == sl)  # noqa: E731
    risk_open = lambda: sum(p.get("risk", 0) for p in s["pos"].values() if p["sleeve"] != "CORE")  # noqa: E731

    def buy(c, sleeve, value_cad, why, **extra):
        k = q(c)
        if not k:
            out["skipped"].append(f"{c}: no NDAX quote")
            return False
        qty = B.round_qty(min(value_cad, s["cash"] / (1 + B.NDAX_FEE)), k["ask"], inst.get(c))
        if not qty:
            out["skipped"].append(f"{c}: under NDAX's minimum order")
            return False
        px, fee = fill(c, "BUY", sleeve, qty, why)
        s["cash"] -= qty * px + fee
        s["pos"][c] = {"sleeve": sleeve, "qty": qty, "paid": qty * px + fee, "t": now, "day": time.strftime("%Y-%m-%d", time.gmtime(now)), "last": px,
                       "book_value": value, "dial": dial, **extra}
        if "risk" in extra:
            s["pos"][c]["risk_pct"] = round(100 * extra["risk"] / value, 3)
        out["bought"].append(f"{c} {sleeve} ${qty * px:.2f}")
        return True

    if may:
        if dial and not any(p["sleeve"] == "CORE" for p in s["pos"].values()):
            for c, w in B.CORE.items():
                buy(c, "CORE", w * value, "dial open")
        for c, rule, why in edge_signals(j, C, tier_a, dial, bar_t):       # Oct 13: every rule that passed its bar, not H07 alone
            if c in s["pos"]:
                continue
            S = C[c]
            k = q(c)
            if not k:
                continue
            v, risk, inv = B.size_setup(value, k["ask"], S.atr14[-1], used("EDGE"), B.EDGE_SLEEVE, risk_open())
            twins = sum(1 for d, p in s["pos"].items() if p["sleeve"] == "EDGE" and d in C and (B.corr(S, C[d], bar_t) or 0) > B.CORR_LIMIT)
            if not v or twins >= B.CORR_MAX_OPEN:
                out["skipped"].append(f"{c}: {'correlation limit' if v else 'risk or sleeve limit'}")
                continue
            buy(c, "EDGE", v, why, risk=round(risk, 2), inv=inv, rule=rule, stop_on_ndax=round(k["ask"] - B.NDAX_STOP_ATR * S.atr14[-1], 8))
        # the judgment sleeve: the brain's new buys on NDAX coins since the last step
        since = s.get("last_step_t") or now - DAY
        for tid, c, trade_id in j.db.execute("SELECT id, coin, trade_id FROM brain_decisions WHERE action='TAKE' AND t > ? AND trade_id IS NOT NULL",
                                             (since,)).fetchall() if _has(j, "brain_decisions") else []:
            if tid in s["judged"] or c in s["pos"] or c not in inst or c not in C:
                continue
            s["judged"].append(tid)
            k = q(c)
            if not k:
                continue
            v, risk, inv = B.size_setup(value, k["ask"], C[c].atr14[-1], used("JUDGMENT"), B.JUDGMENT_SLEEVE, risk_open())
            if v:
                buy(c, "JUDGMENT", v, "the brain's buy", risk=round(risk, 2), inv=inv, trade_id=trade_id,
                    stop_on_ndax=round(k["ask"] - B.NDAX_STOP_ATR * C[c].atr14[-1], 8))
    else:
        out["skipped"].append("brakes: no new buys" + (" (PAUSED until Madhav resumes)" if brakes.paused else f" until {B._day(brakes.block_until)}"))
    s["value"] = mark()
    s["dial"] = dial
    s["brakes"] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in brakes.__dict__.items()}
    s["last_bar"], s["last_step_t"], s["last_step"] = bar_t, now, time.strftime("%Y-%m-%d %H:%M", time.gmtime(now))
    s["judged"] = s["judged"][-200:]
    _put(j, "state", s)
    j.db.commit()
    out["value_cad"] = s["value"]
    return out


def _has(j, table: str) -> bool:
    return bool(j.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())
