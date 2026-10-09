"""The Explorer's 15-minute setups on every coin, as shadows (engine plan U3, decision D6).

The same engine as the live Explorer and the history replay (src/intelligence/explorer_engine.CoinEngine, rulebook v0), fed
from the universe feed's candles (5-minute candles and the 15-minute to 4-hour candles built from them, daily candles), one
saved state per coin in its own database (universe_explorer.sqlite), so it scales to every coin and never touches the live
Explorer's files (D7). Every order is a shadow (reason UNIVERSE): no account, no caps, every signal followed to its exit and
scored, with the engine's own random entries as the bar. These setups lost after costs in seven years of history (review #9),
so they never wake the brain outside the 10; they are evidence, by tier.

  step(j)            one 15-minute round over every registry coin (BTC first: the others' context)
  scoreboard(j)      setups x tier: closed shadows, average per $100 after costs, against the random entries of the same tier
  compare_lab10(j)   the side-by-side check on the 10 (U3.5): this engine on Binance candles against the live Explorer on Kraken's
Paper only.
"""
from __future__ import annotations

import json
import pickle
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

DB = "universe_explorer.sqlite"
WARM_N = {"5m": 400, "15m": 300, "30m": 200, "1h": 200, "4h": 100, "1d": 300}
STATE: dict[str, Any] = {"running": False, "last": None, "errors": {}}
_lock = threading.Lock()


def _con(j) -> sqlite3.Connection:
    con = sqlite3.connect(str(Path(j.dir) / DB), timeout=30, check_same_thread=False)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS engines (coin TEXT PRIMARY KEY, pkl BLOB, last_open TEXT, t INTEGER);
        CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT);
        CREATE TABLE IF NOT EXISTS trades (id TEXT PRIMARY KEY, coin TEXT, tier TEXT, setup TEXT, shadow TEXT, exit_t INTEGER, net REAL, json TEXT);
        CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
    """)
    return con


def _bars(j, coin: str, tf: str, n: int) -> list[tuple]:
    from jarvis.service import feed

    if tf == "1d":
        return feed.daily(j, coin)[-n:]
    return feed.bars(j, coin, tf, n)


def _closed(bars: list[tuple], tf: str, now: float) -> list[tuple]:
    from src.intelligence import explorer_engine as xe

    return [b for b in bars if b[0] + xe.TF_S[tf] <= now]


def step(j, coins: list[str] | None = None, now: float | None = None) -> dict:
    from jarvis.service import registry
    from src.intelligence import explorer_engine as xe
    from src.intelligence.explorer_live import events_of

    now = now or time.time()
    con = _con(j)
    out = {"coins": 0, "scans": 0, "orders": 0, "closed": 0, "errors": {}}
    t0 = time.time()
    try:
        members = coins or registry.members(j)
        order = (["BTC"] if "BTC" in members else []) + [c for c in members if c != "BTC"]
        tiers = {c: registry.tier_of(j, c) or "C" for c in order}
        r = con.execute("SELECT v FROM meta WHERE k='btc_hist'").fetchone()
        btc_hist: list = json.loads(r[0]) if r else []

        def btc_ctx(T):
            best = None
            for t, v in reversed(btc_hist):
                if t <= T:
                    best = (t, v)
                    break
            return best[1] if best and T - best[0] <= 2 * 3600 else {}

        events: list[tuple] = []
        for coin in order:
            try:
                row = con.execute("SELECT pkl, last_open FROM engines WHERE coin=?", (coin,)).fetchone()

                def on_event(e, coin=coin):
                    if e.get("kind") in ("ORDER", "CLOSED", "FILLED"):
                        events.append((int(e.get("t") or 0), e["kind"], coin, e.get("id"), json.dumps(e, default=str)))

                if row:
                    eng = pickle.loads(row[0])
                    last_open = json.loads(row[1])
                    eng.attach(btc_ctx=btc_ctx, slot_ok=lambda c, t: "UNIVERSE", on_event=on_event)
                    bars = {}
                    for tf in xe.ORDER_TF:
                        step_s = xe.TF_S[tf]
                        lo = last_open.get(tf, -1)
                        if lo + 2 * step_s <= now:
                            n = min(WARM_N[tf], int((now - lo) // step_s) + 3) if lo > 0 else WARM_N[tf]
                            bars[tf] = _closed(_bars(j, coin, tf, n), tf, now)
                    ev = events_of(bars, last_open)
                else:
                    tfrom = int(now // 900) * 900 + 900
                    eng = xe.CoinEngine(coin, trade_from_t=tfrom)
                    eng.attach(btc_ctx=btc_ctx, slot_ok=lambda c, t: "UNIVERSE", on_event=on_event)
                    bars = {tf: _closed(_bars(j, coin, tf, WARM_N[tf]), tf, now) for tf in xe.ORDER_TF}
                    last_open = {}
                    ev = events_of(bars)
                i = 0
                while i < len(ev):
                    T = ev[i][0]
                    while i < len(ev) and ev[i][0] == T:
                        eng.on_bar(ev[i][2], ev[i][3])
                        if coin == "BTC" and ev[i][2] == "1h":
                            v = eng.btc_view()
                            if v:
                                btc_hist.append((v["btc_1h_close_t"], v))
                        i += 1
                    if T % 900 == 0:
                        eng.scan(T)
                        out["scans"] += 1
                rows = eng.trade_rows(eng.actual_closed) + eng.trade_rows()
                eng.actual_closed, eng.closed = [], []
                for rw in rows:
                    con.execute("INSERT OR REPLACE INTO trades VALUES (?,?,?,?,?,?,?,?)",
                                (rw["id"], coin, tiers[coin], rw["setup"], rw["shadow"], rw.get("ACTUAL_exit_t"), rw.get("ACTUAL_net"),
                                 json.dumps(rw, default=str)))
                    out["closed"] += 1
                for tf, b in bars.items():
                    if b:
                        last_open[tf] = max(last_open.get(tf, -1), b[-1][0])
                con.execute("INSERT OR REPLACE INTO engines VALUES (?,?,?,?)", (coin, pickle.dumps(eng), json.dumps(last_open), int(now)))
                out["coins"] += 1
            except Exception as exc:  # noqa: BLE001  one coin failing never stops the others
                out["errors"][coin] = str(exc)[:120]
        con.executemany("INSERT INTO events (t, kind, coin, id, json) VALUES (?,?,?,?,?)", events)
        out["orders"] = sum(1 for e in events if e[1] == "ORDER")
        con.execute("INSERT OR REPLACE INTO meta VALUES ('btc_hist', ?)", (json.dumps(btc_hist[-800:]),))
        con.commit()
    finally:
        con.close()
    out["seconds"] = round(time.time() - t0, 1)
    out["errors"] = dict(list(out["errors"].items())[:10])
    STATE["last"] = {"t": int(now), **out}
    return out


def step_async(j) -> bool:
    """From the feed's 5-minute round: run a step in its own thread at each 15-minute close (never two at once)."""
    if int(time.time() // 300) % 3 != 0 or not _lock.acquire(blocking=False):
        return False

    def go():
        try:
            step(j)
        except Exception as exc:  # noqa: BLE001
            STATE["errors"]["step"] = str(exc)[:200]
        finally:
            _lock.release()

    threading.Thread(target=go, name="ananta-universe-explorer", daemon=True).start()
    return True


def scoreboard(j) -> dict:
    con = _con(j)
    try:
        rows = con.execute("SELECT tier, setup, shadow, net, exit_t FROM trades WHERE net IS NOT NULL").fetchall()
        n_ev = con.execute("SELECT COUNT(*) FROM events WHERE kind='ORDER'").fetchone()[0]
    finally:
        con.close()
    by: dict = {}
    for tier, setup, shadow, net, xt in rows:
        key = (tier, "RANDOM" if shadow == "RANDOM" else setup)
        by.setdefault(key, []).append((net, xt))
    out = []
    for (tier, setup), xs in sorted(by.items()):
        days = len({time.strftime("%Y-%m-%d", time.gmtime(x[1])) for x in xs if x[1]})
        avg = round(sum(x[0] for x in xs) / len(xs), 2)
        base = by.get((tier, "RANDOM"))
        bavg = round(sum(x[0] for x in base) / len(base), 2) if base else None
        out.append({"tier": tier, "setup": setup, "closed": len(xs), "market_days": days, "avg_usd": avg,
                    "vs_random_usd": round(avg - bavg, 2) if bavg is not None and setup != "RANDOM" else None})
    return {"rows": out, "orders_seen": n_ev, "last": STATE.get("last"),
            "note": "Shadows only: the 15-minute setups lost after costs in history (review #9); they never wake the brain outside the 10."}


def compare_lab10(j, hours: float = 24) -> dict:
    """U3.5: on the 10, does this engine (Binance candles) see the same setups as the live Explorer (Kraken candles)?"""
    from src.research import reads as R

    since = int(time.time() - hours * 3600)
    con = _con(j)
    try:
        mine = {(c, int(t), json.loads(js).get("setup")) for t, c, js in
                con.execute("SELECT t, coin, json FROM events WHERE kind='ORDER' AND t >= ?", (since,)) if c in R.COINS}
    finally:
        con.close()
    try:
        ex = j._explorer()
        live = {(e["coin"], int(e.get("t") or 0), e.get("setup")) for e in
                (json.loads(js) for (js,) in ex.store.book.execute("SELECT json FROM events WHERE kind='ORDER' AND t >= ?", (since,)))
                if e.get("shadow") != "RANDOM"}
    except Exception:  # noqa: BLE001
        live = set()
    mine = {x for x in mine if x[2] != "RND"}
    both = mine & live
    return {"hours": hours, "live_explorer": len(live), "universe_engine": len(mine), "same": len(both),
            "agreement_pct": round(100 * len(both) / max(1, len(mine | live)), 1),
            "note": "Different candles (Binance against USDT vs Kraken against USD) move setups by a bar or a few cents; the same engine and "
                    "rules, so most should agree. The 10-coin books keep using the live Explorer."}
