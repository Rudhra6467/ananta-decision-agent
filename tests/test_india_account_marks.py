"""25 Oct audit: the account twin is marked at the last session's NSE closes when the Zerodha snapshot is stale (sealed purpose account_marks)."""
import ast
from pathlib import Path

import pandas as pd
import pytest

from india import account, sealed

INDIA = Path(__file__).resolve().parents[1] / "india"


def test_only_account_reads_marks():
    callers = []
    for f in INDIA.glob("*.py"):
        if f.name == "sealed.py":
            continue
        tree = ast.parse(f.read_text())
        if any(isinstance(n, ast.Attribute) and n.attr == "read_marks" for n in ast.walk(tree)) or any(
                isinstance(n, ast.Constant) and n.value == "account_marks" for n in ast.walk(tree)):
            callers.append(f.name)
    assert callers == ["account.py"]


def test_read_marks_refuses_history_and_other_purposes():
    with pytest.raises(PermissionError):
        sealed.read_marks("paper_review", "2026-10-23", ["TCS"])
    with pytest.raises(PermissionError):
        sealed.read_marks("account_marks", "2025-06-02", ["TCS"])          # before the paper's first day: history, refused


def test_stale_snapshot_uses_nse_closes(monkeypatch):
    monkeypatch.setattr(account, "last_session", lambda now=None: "2026-10-23")
    monkeypatch.setattr(sealed, "read_marks", lambda purpose, day, symbols: pd.DataFrame([{"symbol": "TCS", "close": 3000.0}]))
    px, note = account.stale_marks({"day": "2026-10-21"}, ["TCS", "INFY"])
    assert px == {"TCS": 3000.0} and note["marked_at"] == "NSE close 2026-10-23" and note["closes_found"] == 1 and note["of"] == 2
    px, note = account.stale_marks({"day": "2026-10-23"}, ["TCS"])
    assert px == {} and note["marked_at"] == "snapshot"


def test_demerged_pair_reads_as_one_holding():
    n = account.demerger_notes({"TMPV": {"avg": 241.5, "last": 265.45, "qty": 27}, "TMCV": {"avg": 109.26, "last": 396.0, "qty": 27}, "TCS": {"avg": 1, "last": 2, "qty": 1}})
    assert set(n) == {"TMPV", "TMCV"} and "+88.6%" in n["TMCV"] and "68.85%" in n["TMPV"]
