"""Live path (flag 239, design parts 5 and 6): reconciliation turns the kill switch on at any planted difference; the survival check in
record mode marks the 5% day and the 22% pause on exactly the right days and acts on nothing while ENFORCE is off."""
import json

import pytest

from india.live import reconcile, survival, switches
from live_fakes import FakeKite


@pytest.fixture(autouse=True)
def live_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_LIVE_DIR", str(tmp_path / "live_india"))
    switches.turn_off(by="Madhav")


SYM = "BANKNIFTY26DEC63400CE"
LEDGER = [
    {"step": "after", "what": "entry", "ok": True, "answer": {"order_id": "O1"}, "decision": {"tradingsymbol": SYM}},
    {"step": "after", "what": "gtt", "ok": True, "answer": {"trigger_id": 901}, "decision": {"tradingsymbol": SYM}},
]
CLEAN = dict(trades=[{"order_id": "O1", "tradingsymbol": SYM}], positions={"net": [{"tradingsymbol": SYM, "quantity": 30}]},
             gtts=[{"id": 901, "status": "active", "condition": {"tradingsymbol": SYM}}])


def test_clean_books_agree():
    assert reconcile.differences(LEDGER, **CLEAN) == []
    k = FakeKite()
    k._trades, k._positions, k._gtts = CLEAN["trades"], CLEAN["positions"], CLEAN["gtts"]
    assert reconcile.run(k, LEDGER)["ok"] and not switches.kill_on()
    assert k.sent == [] and set(k.gets) == {"/trades", "/portfolio/positions", "/gtt/triggers"}


@pytest.mark.parametrize("plant,word", [
    (lambda c: c["trades"].append({"order_id": "X9", "tradingsymbol": SYM}), "did not send"),
    (lambda c: c["positions"]["net"].append({"tradingsymbol": "NIFTY26D0826000CE", "quantity": 65}), "never entered"),
    (lambda c: c["gtts"].clear(), "missing at Zerodha"),
    (lambda c: c["gtts"].append({"id": 777, "status": "active", "condition": {"tradingsymbol": SYM}}), "does not know"),
])
def test_each_planted_difference_turns_the_kill_switch_on(plant, word):
    c = json.loads(json.dumps(CLEAN))
    plant(c)
    k = FakeKite()
    k._trades, k._positions, k._gtts = c["trades"], c["positions"], c["gtts"]
    out = reconcile.run(k, LEDGER)
    assert not out["ok"] and any(word in d for d in out["differences"])
    assert switches.kill_on()


def test_unreadable_zerodha_turns_it_on():
    class Down(FakeKite):
        def trades(self):
            raise RuntimeError("no answer")
    assert not reconcile.run(Down(), LEDGER)["ok"] and switches.kill_on()


def test_a_deleted_gtt_is_not_missing():
    led = LEDGER + [{"step": "before", "what": "gtt_delete", "path": "/gtt/triggers/901"}]
    c = {**CLEAN, "gtts": []}
    assert reconcile.differences(led, **c) == []


DAYS = [  # start, low, end in rupees
    {"date": "2026-12-01", "start": 100_000, "low": 99_000, "end": 101_000},
    {"date": "2026-12-02", "start": 101_000, "low": 95_950, "end": 97_000},   # 5.0% day: the day line
    {"date": "2026-12-03", "start": 97_000, "low": 96_000, "end": 99_000},
    {"date": "2026-12-04", "start": 99_000, "low": 80_000, "end": 80_000},    # 19.2% day; 20.8% under 101,000: no pause yet
    {"date": "2026-12-07", "start": 80_000, "low": 78_700, "end": 79_000},    # 22.08% under 101,000: the pause line
    {"date": "2026-12-08", "start": 79_000, "low": 79_000, "end": 82_000},
]


def test_survival_lines_fire_on_exactly_the_expected_days():
    rows = survival.check(DAYS)
    assert [r["date"] for r in rows if r["day_line"]] == ["2026-12-02", "2026-12-04", ]
    assert [r["date"] for r in rows if r["pause_line"]] == ["2026-12-07"]
    assert [r["paused"] for r in rows] == [False, False, False, False, True, True]
    assert rows[1]["hwm"] == 101_000 and rows[4]["dd"] == pytest.approx(0.220792, abs=1e-6)


def test_record_mode_acts_on_nothing(tmp_path, monkeypatch):
    f = tmp_path / "book.jsonl"
    f.write_text("\n".join(json.dumps(d) for d in reversed(DAYS)))
    rows = survival.record(f)
    assert rows[-1]["paused"] and survival.actions(rows) == ["record only (ENFORCE is off)"]
    monkeypatch.setattr(switches, "ENFORCE", True)
    assert survival.actions(rows) == ["no new entry until Madhav resumes"]
