"""Flag 293 (Madhav, 27 Nov 2026: 'yes to adding the list of holidays as well'): a US holiday does not make the previous US close stale.
The list feeds the staleness mark and its words only; these tests also prove no SP1 decision reads the mark."""
from __future__ import annotations

import ast
import datetime as dt
from pathlib import Path

from india import ussessions

D = dt.date


def test_thanksgiving_friday_reads_wednesday():
    # Fri 27 Nov 2026: the US was shut on Thu 26 Nov, so Wed 25 Nov's close is the latest
    assert ussessions.last_us_session_before(D(2026, 11, 27)) == D(2026, 11, 25)


def test_ordinary_days_unchanged():
    assert ussessions.last_us_session_before(D(2026, 11, 30)) == D(2026, 11, 27)  # Monday reads Friday
    assert ussessions.last_us_session_before(D(2026, 11, 25)) == D(2026, 11, 24)
    assert ussessions.last_us_session_before(D(2026, 12, 28)) == D(2026, 12, 24)  # Christmas Friday shut, weekend


def test_every_listed_holiday_is_a_weekday_in_a_covered_year():
    for d in ussessions.US_HOLIDAYS:
        assert d.weekday() < 5 and d.year in ussessions.COVERED_YEARS


def _funcs_reading(name: str) -> set[str]:
    src = Path(__file__).resolve().parents[1] / "india" / "sp1paper.py"
    tree = ast.parse(src.read_text())
    out = set()
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for n in ast.walk(fn):
            if isinstance(n, ast.Constant) and n.value == name:
                out.add(fn.name)
    return out


def test_no_decision_reads_the_stale_mark():
    """Replay guard: the mark is written by the plan and read only to prepare again before the open; decide_point, live and the scoring
    never see it, so every options decision is the same with or without the holiday list."""
    readers = _funcs_reading("stale")
    # overnight writes it, prepare stores it in the plan and logs it, run prepares again before the open; nothing else may read it
    assert readers <= {"overnight", "prepare", "run"}, readers
    for f in ("decide_point", "live", "predict", "choose", "xrow", "score", "replay", "replay_ledger"):
        assert f not in readers, f"{f} reads the stale mark"
