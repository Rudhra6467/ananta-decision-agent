"""News recorder (the blunder guard, every day): one AI news check per coin per day, after the daily close.

Two jobs in one:
  * point-in-time news history: a verdict recorded the same day, so later studies can use news without hindsight
    (BACKLOG E1; review #5 showed old headlines are thin and the model may know how old stories ended);
  * the lookout's last look: a coin with HIGH attention is checked first, and its verdict shows in the zone lookout.
Cost: Claude Haiku, about a cent per coin, so about 10 cents a day for the 10 coins. It only runs when Ask Ananta is on and the
day's AI budget has room (the same switch and budget as everything else). Evidence for Madhav, never an order.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS news_log (day TEXT, coin TEXT, t INTEGER, verdict TEXT, why TEXT, json TEXT, "
                 "PRIMARY KEY (day, coin))")


def today(j) -> str:
    return datetime.fromtimestamp(j.now(), timezone.utc).strftime("%Y-%m-%d")


def latest(j, coin: str | None = None, days: int = 14) -> list[dict]:
    try:
        _table(j)
        q = "SELECT day, coin, verdict, why, json FROM news_log WHERE t >= ?" + (" AND coin=?" if coin else "") + " ORDER BY day DESC, coin"
        args = (int(j.now()) - days * 86400,) + ((coin.upper(),) if coin else ())
        rows = j.db.execute(q, args).fetchall()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for d, c, v, w, js in rows:
        x = json.loads(js or "{}")
        out.append({"day": d, "coin": c, "verdict": v, "why": w, "damage": x.get("damage", [])[:3], "good": x.get("good", [])[:2]})
    return out


def watch(j, check=None, max_per_run: int = 4) -> list[dict]:
    """Check coins not yet checked today: HIGH attention first, then the rest (a few per 15-minute run, so one slow search
    never blocks the other jobs)."""
    from jarvis.service import reads_watch, zones_watch

    check = check or reads_watch.news_check
    _table(j)
    day = today(j)
    done = {c for (c,) in j.db.execute("SELECT coin FROM news_log WHERE day=?", (day,))}
    b = zones_watch.board(j)
    order = [r["coin"] for r in b.get("coins", [])]                     # already sorted by attention, highest first
    order += [c for c in reads_watch.NAMES if c not in order]
    out = []
    for c in order:
        if c in done or len(out) >= max_per_run:
            continue
        res = check(j, c)
        if res.get("verdict") == "NOT_CHECKED":
            break                                                        # switch off or budget used: stop for this run
        j.db.execute("INSERT OR REPLACE INTO news_log VALUES (?,?,?,?,?,?)",
                     (day, c, int(j.now()), res.get("verdict"), res.get("why"), json.dumps(res)))
        j.db.commit()
        out.append({"coin": c, "verdict": res.get("verdict")})
    return out
