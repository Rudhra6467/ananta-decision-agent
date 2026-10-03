"""Credit tracking (BACKLOG A3): which layer moved each decision, and was it right?

Every day after the close, one record per coin: what each layer said at that moment (market gate, coin trend, the chain's verdict and
where it stopped, the zone and its attention, Madhav's setups, the news verdict). Twenty days later the record gets its outcome (the
coin's return from that close). The report then asks, per layer signal: when it was present, did the next 20 days go better than
when it was absent? Explorer paper trades are joined to the record of their entry day, so the trading engine and the reasoning
layers finally meet in one place (BACKLOG A2, first step).

Live evidence only: small numbers for months. Nothing here changes a decision; it tells the repair shop where to look.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone

HORIZON = 20
SIGNALS = {
    "market_allowed": "Market allowed (BTC above its 50-day)",
    "coin_trend_up": "Coin in its own uptrend",
    "chain_candidate": "Decision chain: candidate",
    "in_supported_zone": "Inside or testing a zone history supports",
    "attention_high": "Attention HIGH",
    "setup_fired": "One of your setups showing",
    "setup_close": "One of your setups one sign away",
    "news_caution_or_block": "News CAUTION or BLOCK",
}


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS credit_records (day TEXT, coin TEXT, t INTEGER, close REAL, signals TEXT, detail TEXT, "
                 "fwd20 REAL, PRIMARY KEY (day, coin))")


def _day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def record(j) -> int:
    """Write today's records (the last closed day), once per coin."""
    from jarvis.service import chain, news_watch, reads_watch, zones_watch

    _table(j)
    zb = zones_watch.board(j)
    day = zb.get("day")
    if not day or j.db.execute("SELECT 1 FROM credit_records WHERE day=? LIMIT 1", (day,)).fetchone():
        return 0
    try:
        ch = {r["coin"]: r for r in chain.board(j).get("coins", [])}
    except Exception:  # noqa: BLE001  no Explorer state: the chain part stays empty
        ch = {}
    rb = {r["coin"]: r for r in reads_watch.board(j).get("coins", [])}
    news = {n["coin"]: n["verdict"] for n in news_watch.latest(j, None, 2) if n["day"] >= day}
    n = 0
    for z in zb.get("coins", []):
        c = z["coin"]
        cr = ch.get(c) or {}
        gates = {g["gate"]: g["status"] for g in cr.get("gates", [])}
        focus = (z["inside"] or [None])[0] or z.get("tested")
        reads = (rb.get(c) or {}).get("reads", [])
        sig = {"market_allowed": gates.get("REGIME") == "PASS", "coin_trend_up": gates.get("TREND") == "PASS",
               "chain_candidate": cr.get("verdict") == "CANDIDATE",
               "in_supported_zone": bool(focus and focus.get("history") == "SUPPORTED"),
               "attention_high": z["attention"]["level"] == "HIGH",
               "setup_fired": any(x["state"] == "FIRED" for x in reads), "setup_close": any(x["state"] == "CLOSE" for x in reads),
               "news_caution_or_block": news.get(c) in ("CAUTION", "BLOCK")}
        detail = {"stops_at": cr.get("stops_at"), "attention": z["attention"]["level"], "zone": focus and "+".join(focus["kinds"]),
                  "news": news.get(c), "setups": [x["variant"] for x in reads if x["state"] in ("FIRED", "CLOSE")]}
        j.db.execute("INSERT OR IGNORE INTO credit_records VALUES (?,?,?,?,?,?,?)",
                     (day, c, int(j.now()), z["price"], json.dumps(sig), json.dumps(detail), None))
        n += 1
    j.db.commit()
    return n


def settle(j) -> int:
    """Fill the 20-day outcome of records old enough, from the daily candles."""
    from jarvis.service.reads_watch import _daily

    _table(j)
    rows = j.db.execute("SELECT day, coin, close FROM credit_records WHERE fwd20 IS NULL").fetchall()
    bars: dict = {}
    n = 0
    for day, c, px in rows:
        D = bars.setdefault(c, _daily(j, c))
        days = [_day(b[0]) for b in D]
        if day not in days:
            continue
        k = days.index(day)
        if k + HORIZON < len(D):
            j.db.execute("UPDATE credit_records SET fwd20=? WHERE day=? AND coin=?", (D[k + HORIZON][4] / D[k][4] - 1, day, c))
            n += 1
    j.db.commit()
    return n


def _explorer_trades(j) -> list[dict]:
    ex = j._explorer() if hasattr(j, "_explorer") else None
    if not ex:
        return []
    fills, closed = {}, {}
    for (js,) in ex.store.book.execute("SELECT json FROM events WHERE kind IN ('FILLED','CLOSED') ORDER BY seq"):
        e = json.loads(js)
        if e.get("shadow"):
            continue
        (fills if e["kind"] == "FILLED" else closed)[e["id"]] = e
    return [{"coin": f["coin"], "day": _day(f["t"]), "setup": f.get("setup"), "net_usd": closed[i].get("net_usd")}
            for i, f in fills.items() if i in closed]


def report(j) -> dict:
    _table(j)
    rows = [(d, c, json.loads(s), json.loads(dt), f) for d, c, s, dt, f in
            j.db.execute("SELECT day, coin, signals, detail, fwd20 FROM credit_records ORDER BY day")]
    settled = [r for r in rows if r[4] is not None]
    by = []
    for k, name in SIGNALS.items():
        on = [r[4] for r in settled if r[2].get(k)]
        off = [r[4] for r in settled if not r[2].get(k)]
        by.append({"signal": k, "name": name, "with_n": len(on), "without_n": len(off),
                   "with_fwd20_pct": round(100 * statistics.mean(on), 2) if on else None,
                   "without_fwd20_pct": round(100 * statistics.mean(off), 2) if off else None,
                   "diff_pts": round(100 * (statistics.mean(on) - statistics.mean(off)), 2) if on and off else None})
    rec = {(r[0], r[1]): r for r in rows}
    trades = []
    for t in _explorer_trades(j):
        r = rec.get((t["day"], t["coin"]))
        trades.append({**t, "signals": r[2] if r else None})
    joined = [t for t in trades if t["signals"]]
    ex_by = []
    for k, name in SIGNALS.items():
        on = [t["net_usd"] for t in joined if t["signals"].get(k) and t["net_usd"] is not None]
        off = [t["net_usd"] for t in joined if not t["signals"].get(k) and t["net_usd"] is not None]
        if on or off:
            ex_by.append({"signal": k, "name": name, "with_n": len(on), "with_net_usd": round(statistics.mean(on), 2) if on else None,
                          "without_n": len(off), "without_net_usd": round(statistics.mean(off), 2) if off else None})
    days = sorted({r[0] for r in rows})
    return {"records": len(rows), "settled": len(settled), "days": len(days), "since": days[0] if days else None,
            "horizon_days": HORIZON, "by_signal": by, "explorer": {"closed_trades": len(trades), "joined": len(joined), "by_signal": ex_by},
            "note": "Live evidence: each coin's record at every daily close, scored 20 days later. Small numbers for months; "
                    "a difference means 'look here', not a proven effect."}


def watch(j) -> dict:
    return {"recorded": record(j), "settled": settle(j)}
