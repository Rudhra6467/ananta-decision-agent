"""Paper shadow for the short dip trade (H07, review #14; Madhav's OK 2026-10-03).

Since the watch registry (2026-10-03) H07 is one of the daily watches run by jarvis/service/watch_engine.py into the shared
evidence book (evidence_trades); this module keeps the H07 view the app and Ask already use.

The rule (unchanged): when the close is above its 200-day average and RSI(10) is under 30, "buy" $100 at the next day's open
and "sell" at the next open after a close with RSI(10) over 40, or at the open 10 days after entry, with NDAX costs on both
sides. Nothing is sent to Hands or any exchange.
"""
from __future__ import annotations

NOTIONAL = 100.0
MAX_DAYS = 10


def _table(j) -> None:
    """The original table (kept so older copies and guest sandboxes still open); new trades live in evidence_trades."""
    j.db.execute("CREATE TABLE IF NOT EXISTS shadow_h07 (id TEXT PRIMARY KEY, coin TEXT, signal_day TEXT, entry_day TEXT, entry REAL, "
                 "exit_day TEXT, exit REAL, net_usd REAL, why TEXT, status TEXT)")


def watch(j) -> dict:
    from jarvis.service import watch_engine

    r = watch_engine.run(j, watches=("H07",))
    return {"opened": [x["coin"] for x in r["opened"] if x["watch"] == "H07"],
            "filled": [x["coin"] for x in r["filled"] if x["watch"] == "H07"],
            "closed": [{"coin": x["coin"], "net_usd": x.get("net_usd")} for x in r["closed"] if x["watch"] == "H07"]}


def report(j) -> dict:
    from jarvis.service import watch_engine

    rows = []
    for t in watch_engine.trades(j, "H07", 200):
        rows.append({"id": t["id"], "coin": t["coin"], "signal_day": t["signal_day"], "entry_day": t["entry_day"], "entry": t["entry"],
                     "exit_day": t["exit_day"], "exit": t["exit"], "net_usd": t["net_usd"],
                     "why": t["why"] + (f" -> {t['exit_why']}" if t.get("exit_why") else ""), "status": t["status"]})
    done = [r for r in rows if r["status"] == "CLOSED"]
    return {"name": "Short dip trade (H07) paper shadow", "trades": rows[:30], "closed": len(done), "open": sum(r["status"] == "OPEN" for r in rows),
            "waiting": sum(r["status"] == "WAITING" for r in rows),
            "net_usd": round(sum(r["net_usd"] for r in done), 2) if done else 0.0,
            "win_rate": round(sum(r["net_usd"] > 0 for r in done) / len(done), 2) if done else None,
            "history": "review #14: +3.9% / +5.6% per trade over ordinary uptrend days, about 70% wins, in both periods (few cases)",
            "note": "Paper only: $100 per signal, NDAX costs, nothing sent to an exchange."}
