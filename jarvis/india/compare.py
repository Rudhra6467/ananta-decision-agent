"""The managed book against your holdings and the Nifty 500, over the same days.

5 Nov 2026 (the 20-day synopsis): the managed book counts from its start (the 29 Oct close), while "as you have it" and the Nifty 500
counted from 22 Oct, so Ananta said "+1.51% against +2.52%" and the Money screen said "same start" for three different windows. On the
same days the managed book was about 2.3 points behind, not 1. One owner for the comparison: the Ask, Money and Today all read same_window().
"""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path.home() / "ananta_data" / "india"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _day(d: str) -> str:
    y, m, dd = str(d).split("-")
    return f"{int(dd)} {MONTHS[int(m) - 1]}"


def same_window(data: Path = DATA) -> dict:
    """Managed, your holdings as you have them, and the Nifty 500, all from the close before the managed book's first session."""
    try:
        v = json.loads((data / "paper" / "account" / "view.json").read_text()).get("benchmark") or {}
        rows = [json.loads(x) for x in (data / "paper" / "account" / "benchmark.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return {"ready": False, "words": "the comparison is not built yet"}
    start = v.get("managed_start_day")
    rows = [r for r in rows if r.get("day")]
    base = [r for r in rows if str(r["day"]) < str(start or "")]
    last = rows[-1] if rows else {}
    if not start or not base or last.get("managed_ret_pct") is None or not base[-1].get("frozen_inr") or not last.get("frozen_inr"):
        return {"ready": False, "words": "the managed book has no session scored yet"}
    b = base[-1]
    yours = (last["frozen_inr"] / b["frozen_inr"] - 1) * 100
    n500 = ((1 + (last.get("nifty500_ret_pct") or 0) / 100) / (1 + (b.get("nifty500_ret_pct") or 0) / 100) - 1) * 100
    managed = float(last["managed_ret_pct"])
    s = v.get("managed_sessions") or last.get("managed_sessions")
    return {"ready": True, "since": b["day"], "since_words": _day(b["day"]), "through": last["day"], "through_words": _day(last["day"]),
            "managed_pct": round(managed, 2), "yours_pct": round(yours, 2), "nifty500_pct": round(n500, 2),
            "managed_minus_yours_pts": round(managed - yours, 2), "sessions": s,
            "words": (f"From the {_day(b['day'])} close (the managed book's start) to {_day(last['day'])}: the managed book {managed:+.2f}%, "
                      f"your holdings as you have them {yours:+.2f}%, the Nifty 500 {n500:+.2f}% (price index). Session {s} of 60; nothing is "
                      f"read into the gap before session 60.")}
