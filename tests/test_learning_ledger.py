"""The repair-shop ledger (Oct 21): the Oct 14 weekly ticket filed at last (TK19), and the hand-written ledger checked against the
database as a warning in the morning review (the full generator, PW-LEDGER-GENERATE, waits for after the window)."""
import json
import time
from pathlib import Path

from tests.test_learning_loop import NOW, SUN, DAY, _pair, loop  # noqa: F401  (the fixture)

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------- 3. the Oct 14 ticket, filed
def test_the_oct_14_random_beat_the_pick_ticket_is_in_the_ledger():
    led = json.loads((REPO / "docs" / "repair_shop" / "ledger.json").read_text())
    tk = [t for t in led["tickets"] if t.get("lesson") == "random beat the pick"]
    assert len(tk) == 1 and tk[0]["id"] == "TK19" and tk[0]["review"] == "R33"
    assert tk[0]["decisions"] == ["2fa79120821d", "450cfffaeac5", "58058e45d50b"]
    assert "weekly/2026-10-14.md" in tk[0]["from"] and "DOGE" in tk[0]["what"] and "I approve all" in tk[0]["did"]
    assert tk[0]["status"] in ("OPEN", "WAITING_FOR_EVIDENCE") and led["updated"] >= tk[0]["date"]
    assert "random beat the pick" in (REPO / "docs" / "repair_shop" / "weekly" / "2026-10-14.md").read_text()


def test_the_ledger_on_this_branch_agrees_with_itself():
    from jarvis.service import knowledge_build

    j = type("J", (), {"dir": str(REPO), "now": lambda self: time.time()})()
    assert knowledge_build.ledger(j)["problems"] == []
