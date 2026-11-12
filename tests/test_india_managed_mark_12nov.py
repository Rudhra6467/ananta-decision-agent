"""12 Nov 2026, the keen outside audit (G-03; open-list flag 118): the managed book was filled and marked only by the evening run, about 15
hours after each close. The nightly job now fills the session's plan and marks the book as soon as the day file is in; the next plan stays
with the evening run, which then finds the fills done. Synthetic bars only (tests/test_india_managed.py's world)."""
import json

import pandas as pd

from india import managed as m
from tests.test_india_managed import DAY, world  # noqa: F401  (world is the managed book's fixture)

_FIXTURES = (world,)
NXT = "2026-11-02"


def _with_next_session(monkeypatch):
    bars = m.bars()
    last = bars[bars["date"] == pd.Timestamp(DAY)].set_index("symbol")
    add = [{"symbol": s, "date": pd.Timestamp(NXT), "open": float(last.loc[s, "close"]), "high": float(last.loc[s, "close"]) * 1.01,
            "low": float(last.loc[s, "close"]) * 0.99, "close": float(last.loc[s, "close"]) * 1.002, "volume": 1e6, "turnover": 2e8} for s in last.index]
    bars2 = pd.concat([bars, pd.DataFrame(add)], ignore_index=True)
    monkeypatch.setattr(m, "bars", lambda: bars2)


def test_the_book_is_filled_and_marked_at_the_close_without_writing_a_plan(world, monkeypatch):
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    m.run(DAY)                                                     # the evening run of 30 Oct: the plan for Mon 2 Nov
    _with_next_session(monkeypatch)
    r = m.mark_after_close()                                       # the nightly job of 2 Nov, after the day file
    assert r["status"] == "marked" and r["day"] == NXT and r["fills"] >= 2
    v = json.loads((world / "paper" / "managed" / "view.json").read_text())
    assert v["day"] == NXT and "nightly job" in v["marked_by"] and v["plan"]["for_session"] == NXT
    plans = [json.loads(x) for x in (world / "paper" / "managed" / "plans.jsonl").read_text().splitlines()]
    assert [p["for_session"] for p in plans] == [NXT]               # no plan for 3 Nov yet: that stays with the evening run
    assert m.mark_after_close()["status"] == "already marked"      # the 02:30 catch-up does nothing


def test_the_evening_run_then_fills_nothing_twice_keeps_what_the_day_did_and_writes_the_plan(world, monkeypatch):
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    m.run(DAY)
    _with_next_session(monkeypatch)
    m.mark_after_close()
    marked = json.loads((world / "paper" / "managed" / "view.json").read_text())
    ledger = (world / "paper" / "managed" / "ledger.jsonl").read_text()
    v = m.run(NXT)                                                 # the evening run of 2 Nov (06:50 IST on 3 Nov)
    assert (world / "paper" / "managed" / "ledger.jsonl").read_text() == ledger   # no fill twice
    assert [t["symbol"] for t in v["filled_today"]] == [t["symbol"] for t in marked["filled_today"]]
    assert v["value_inr"] == marked["value_inr"] and v["day"] == NXT                # one number for the close, whichever run wrote it
    assert v["plan"]["for_session"] == "2026-11-03"
