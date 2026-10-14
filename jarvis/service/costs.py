"""Where the AI money goes (Madhav, 2026-10-09: "understand which parts of the tokens are expensive before deciding how to divide them").

Every answer and every brain decision is logged in ask_messages with its model, tokens and cost; since Oct 9 each answer also
records how its input split into fresh tokens, cached reads and cache writes (timing.in_fresh / cache_read / cache_write).
summary() groups the last N days by job (chat, voice, brain, tests) and model, so the Cockpit can show it plainly.
"""
from __future__ import annotations

import collections
import json
import time
from typing import Any


def summary(dbs: list, days: int = 30) -> dict[str, Any]:
    since = int(time.time()) - days * 86400
    rows: dict[tuple, list] = collections.defaultdict(lambda: [0, 0, 0, 0.0])
    fresh = cread = cwrite = measured = 0
    for db in dbs:
        for prov, tin, tout, cost, mode, thread, timing in db.execute(
                "SELECT provider, tokens_in, tokens_out, cost_usd, mode, thread, timing FROM ask_messages WHERE role='assistant' AND t>=?", (since,)):
            job = ("brain" if thread == "brain" else "tests" if (mode or "").startswith("eval") or (thread or "").startswith("acceptance")
                   else "voice" if "voice" in (mode or "") else "chat")
            tier = {"sonnet": "Claude Sonnet", "opus": "Claude Opus", "haiku": "Claude Haiku", "claude": "Claude Sonnet", "local": "Mac (free)"}.get(
                prov or "", "Gemini (free)")
            r = rows[(job, tier)]
            r[0] += 1
            r[1] += tin or 0
            r[2] += tout or 0
            r[3] += cost or 0.0
            try:
                tm = json.loads(timing or "{}")
            except ValueError:
                tm = {}
            if "in_fresh" in tm:
                measured += 1
                fresh += tm.get("in_fresh", 0)
                cread += tm.get("cache_read", 0)
                cwrite += tm.get("cache_write", 0)
    total = sum(r[3] for r in rows.values())
    tin = sum(r[1] for r in rows.values())
    out = [{"job": j, "model": m, "answers": r[0], "tokens_in": r[1], "tokens_out": r[2], "usd": round(r[3], 2),
            "share": round(r[3] / total, 3) if total else 0, "avg_in": round(r[1] / r[0]) if r[0] else 0}
           for (j, m), r in sorted(rows.items(), key=lambda kv: -kv[1][3])]
    split = None
    if measured:
        t = max(1, fresh + cread + cwrite)
        split = {"answers": measured, "fresh_pct": round(100 * fresh / t), "cached_pct": round(100 * cread / t), "written_pct": round(100 * cwrite / t)}
    return {"days": days, "usd": round(total, 2), "tokens_in": tin, "tokens_out": sum(r[2] for r in rows.values()), "rows": out, "input_split": split}
