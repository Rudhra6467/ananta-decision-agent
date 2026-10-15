"""Fidelity below the backtest goes to the repair shop by itself, once per cell (audit FIX1-5, Oct 15)."""
import sqlite3
import types


def test_a_cell_below_its_backtest_is_forwarded_once(monkeypatch):
    from jarvis.service import core, ev, requests_log

    j = types.SimpleNamespace(db=core.SafeDB(sqlite3.connect(":memory:")), now=lambda: 2_000_000_000)
    cells = [{"rule": "H07", "state": "CLOSED", "tier": "A", "paper_trades": 12, "paper_avg_pct": 1.0, "backtest_avg_pct": 6.3,
              "verdict": "BELOW BACKTEST: check costs, fills and timing"},
             {"rule": "H07", "state": "OPEN", "tier": "A", "paper_trades": 2, "paper_avg_pct": 5.0, "backtest_avg_pct": 2.2, "verdict": "too few trades"}]
    monkeypatch.setattr(ev, "fidelity", lambda j: {"cells": cells})
    pushed = []
    assert ev.fidelity_alert(j, lambda t, b: pushed.append(t)) == ["H07|CLOSED|A"]
    assert ev.fidelity_alert(j, lambda t, b: pushed.append(t)) == []                 # once per cell
    rows = requests_log.list_(j)
    assert len(rows) == 1 and rows[0]["by"] == "ananta-auto" and "6.30%" in rows[0]["text"] and len(pushed) == 1
