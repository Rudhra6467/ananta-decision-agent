"""Paper shadow for the short dip trade (H07, review #14; Madhav's OK 2026-10-03).

When the H07 read fires on a coin (close above its 200-day average, RSI(10) under 30), the shadow "buys" $100 at the next day's open
and "sells" at the next open after a close with RSI(10) over 40, or at the open 10 days after entry, with NDAX costs on both sides.
Nothing is sent to Hands or any exchange: it is a record of what the rule would have done, kept from now on as clean evidence.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

NOTIONAL = 100.0
MAX_DAYS = 10


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS shadow_h07 (id TEXT PRIMARY KEY, coin TEXT, signal_day TEXT, entry_day TEXT, entry REAL, "
                 "exit_day TEXT, exit REAL, net_usd REAL, why TEXT, status TEXT)")


def _day(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def watch(j) -> dict:
    """Open on new H07 fires; fill entries at the next open; close by the rule. Daily candles only (closed days)."""
    from jarvis.service.reads_watch import NAMES, _daily
    from src.research import reads as R

    _table(j)
    opened, filled, closed = [], [], []
    for c in NAMES:
        D = _daily(j, c)
        if len(D) < 260:
            continue
        days = [_day(b[0]) for b in D]
        r10 = R.rsi([b[4] for b in D], 10)
        S = R.Series(D)
        i = len(D) - 1
        fire = S.sma200[i] is not None and D[i][4] > S.sma200[i] and r10[i] is not None and r10[i] < 30
        busy = j.db.execute("SELECT 1 FROM shadow_h07 WHERE coin=? AND status IN ('WAITING','OPEN')", (c,)).fetchone()
        if fire and not busy and not j.db.execute("SELECT 1 FROM shadow_h07 WHERE coin=? AND signal_day=?", (c, days[i])).fetchone():
            j.db.execute("INSERT INTO shadow_h07 VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (uuid.uuid4().hex[:12], c, days[i], None, None, None, None, None, f"RSI(10) {r10[i]:.0f}, above the 200-day", "WAITING"))
            opened.append(c)
        for sid, sday, eday, entry in j.db.execute("SELECT id, signal_day, entry_day, entry FROM shadow_h07 WHERE coin=? AND status IN ('WAITING','OPEN')", (c,)).fetchall():
            if sday not in days:
                continue
            k = days.index(sday) + 1
            if k >= len(D):
                continue                                          # the entry day has not closed yet
            cost = R.cost(c)
            if eday is None:
                entry = D[k][1]
                j.db.execute("UPDATE shadow_h07 SET entry_day=?, entry=?, status='OPEN' WHERE id=?", (days[k], entry, sid))
                filled.append(c)
            for m in range(k, min(k + MAX_DAYS, len(D))):
                out_k = None
                if r10[m] is not None and r10[m] > 40 and m + 1 < len(D):
                    out_k, why = m + 1, f"RSI(10) back over 40 on {days[m]}"
                elif m == k + MAX_DAYS - 1 and k + MAX_DAYS < len(D):
                    out_k, why = k + MAX_DAYS, "10 days"
                if out_k is not None:
                    px = D[out_k][1]
                    net = NOTIONAL * (px / entry * (1 - cost) ** 2 - 1)
                    j.db.execute("UPDATE shadow_h07 SET exit_day=?, exit=?, net_usd=?, why=why || ' -> ' || ?, status='CLOSED' WHERE id=?",
                                 (days[out_k], px, round(net, 2), why, sid))
                    closed.append({"coin": c, "net_usd": round(net, 2)})
                    break
    j.db.commit()
    return {"opened": opened, "filled": filled, "closed": closed}


def report(j) -> dict:
    _table(j)
    rows = [dict(zip(("id", "coin", "signal_day", "entry_day", "entry", "exit_day", "exit", "net_usd", "why", "status"), r))
            for r in j.db.execute("SELECT * FROM shadow_h07 ORDER BY signal_day DESC")]
    done = [r for r in rows if r["status"] == "CLOSED"]
    return {"name": "Short dip trade (H07) paper shadow", "trades": rows[:30], "closed": len(done), "open": sum(r["status"] == "OPEN" for r in rows),
            "waiting": sum(r["status"] == "WAITING" for r in rows),
            "net_usd": round(sum(r["net_usd"] for r in done), 2) if done else 0.0,
            "win_rate": round(sum(r["net_usd"] > 0 for r in done) / len(done), 2) if done else None,
            "history": "review #14: +3.9% / +5.6% per trade over ordinary uptrend days, about 70% wins, in both periods (few cases)",
            "note": "Paper only: $100 per signal, NDAX costs, nothing sent to an exchange."}
