"""The survival check, record mode (design part 5; the rules are in india/paper_config.json: a 5% loss in a day, 22% under the high-water mark).

For each day of a book: the day's start equity, the high-water mark, the worst moment of the day, and whether the 5% day line or the
22% pause line was crossed. It changes nothing: check() is a pure function and read_series() only reads a file. What enforce mode would
do (close every live position and block entries at the day line; block entries until Madhav resumes at the pause line) is returned as
words by actions(), and only when switches.ENFORCE is on; it is off. Paper keeps recording both paths as now. T15 reads this.
"""
from __future__ import annotations

import json
from pathlib import Path

from india.live import switches

DAY_LOSS = 0.05
PAUSE_DD = 0.22


def check(days: list[dict], day_loss: float = DAY_LOSS, pause_dd: float = PAUSE_DD) -> list[dict]:
    """days: in date order, each {'date', 'start', 'low', 'end'} in rupees (low = the worst equity seen that day, realised plus open).
    Missing low counts as min(start, end). Returns one row per day; 'paused' stays true from the first crossing (until a resume,
    which is Madhav's and is not modelled here)."""
    out, hwm, paused = [], None, False
    for d in days:
        start, end = float(d["start"]), float(d["end"])
        low = float(d["low"]) if d.get("low") is not None else min(start, end)
        low = min(low, start, end)
        hwm = start if hwm is None else max(hwm, start)
        day_loss_pct = (start - low) / start if start > 0 else 1.0
        dd = (hwm - low) / hwm if hwm > 0 else 1.0
        day_line = day_loss_pct >= day_loss - 1e-12
        pause_line = dd >= pause_dd - 1e-12
        paused = paused or pause_line
        out.append({"date": d["date"], "start": start, "hwm": hwm, "low": low, "end": end, "day_loss": round(day_loss_pct, 6),
                    "dd": round(dd, 6), "day_line": day_line, "pause_line": pause_line, "paused": paused})
        hwm = max(hwm, end)
    return out


def actions(rows: list[dict]) -> list[str]:
    """What enforce mode would do on the last day. Record mode (ENFORCE off): nothing, said plainly."""
    if not rows:
        return []
    r = rows[-1]
    if not switches.ENFORCE:
        return ["record only (ENFORCE is off)"]
    acts = []
    if r["day_line"]:
        acts.append("close every live position; no new entry today")
    if r["paused"]:
        acts.append("no new entry until Madhav resumes")
    return acts


def read_series(path: Path) -> list[dict]:
    """Read a book's day rows from a JSON-lines file of {'date', 'start', 'low', 'end'}; reads only."""
    rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    return sorted(rows, key=lambda r: r["date"])


def record(path: Path) -> list[dict]:
    """The runner: read a book's series and check it. Writes nothing."""
    return check(read_series(path))
