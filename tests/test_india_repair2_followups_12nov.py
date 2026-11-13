"""12 Nov 2026 evening, the outside check of repair 2 (recheck/pkg2_check.md): N2, a failed nightly marking step was swallowed and counted
as ok; N3, a holding at an older close from the quote book was not said; N7, the managed book kept a holding's old price without a word
when it had no bar that day. Synthetic bars and made-up numbers only."""
import inspect
import json

import pandas as pd

from india import account, managed as m, nightly
from tests.test_india_account_frozen_marks_12nov import BOOK, lake  # noqa: F401  (lake is the account's fixture)
from tests.test_india_managed import DAY, world  # noqa: F401  (world is the managed book's fixture)
from tests.test_india_managed_mark_12nov import NXT

_FIXTURES = (world, lake)


def test_a_holding_with_no_bar_that_day_is_named_not_kept_at_its_old_price_in_silence(world, monkeypatch):
    # N7 (S3)
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    m.run(DAY)
    held = sorted(json.loads((world / "paper" / "managed" / "state.json").read_text())["positions"])
    gone = held[0]
    bars = m.bars()
    last = bars[bars["date"] == pd.Timestamp(DAY)].set_index("symbol")
    add = [{"symbol": s, "date": pd.Timestamp(NXT), "open": float(last.loc[s, "close"]), "high": float(last.loc[s, "close"]) * 1.01,
            "low": float(last.loc[s, "close"]) * 0.99, "close": float(last.loc[s, "close"]) * 1.002, "volume": 1e6, "turnover": 2e8}
           for s in last.index if s != gone]                                        # no bar for one holding on 2 Nov (suspended, say)
    bars2 = pd.concat([bars, pd.DataFrame(add)], ignore_index=True)
    monkeypatch.setattr(m, "bars", lambda: bars2)
    m.mark_after_close()
    v = json.loads((world / "paper" / "managed" / "view.json").read_text())
    assert v["kept_old_price"] == {gone: DAY}
    assert f"1 holding had no close on {NXT} and stays at an older price ({gone}, last marked {DAY})" in v["words"]
    # 13 Nov: repair 2's sentence and repair 4's options sentence met in one view by a hand merge; both stand, once each, in that order
    assert v["words"].count("older price") == 1 and v["words"].count(v["options_counted"]) == 1
    assert v["words"].index("older price") < v["words"].index(v["options_counted"])
    assert "options_value_inr" in v and "holdings" in v
    st = json.loads((world / "paper" / "managed" / "state.json").read_text())
    assert all(p.get("last_on") == NXT for s, p in st["positions"].items() if s != gone)


def test_every_holding_marked_says_nothing_extra(world, monkeypatch):
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    v = m.run(DAY)
    assert v["kept_old_price"] == {} and "older price" not in v["words"]


def test_a_failed_nightly_mark_is_told_in_the_jobs_error_file_and_the_nightly_runs_it(monkeypatch, capsys):
    # N2 (S3): the error was swallowed and the step counted as ok; no test checked that the nightly calls it
    monkeypatch.setattr(m, "mark_after_close", lambda: (_ for _ in ()).throw(KeyError("positions")))
    r = nightly._managed_mark()
    assert r["status"] == "error" and r["why"].startswith("KeyError")
    assert "india.nightly managed_mark FAILED KeyError" in capsys.readouterr().err
    assert '("managed_mark", _managed_mark)' in inspect.getsource(nightly.run)


def test_a_holding_at_an_older_close_from_the_quote_book_is_said(lake):
    # N3 (S3): the night's quote book was not built, so the 10 Nov close stood for 11 Nov without a word
    (lake / "manifests" / "quotebook.json").write_text(json.dumps({"as_of": "2026-11-10", "quotes": {"IEX": {"close": 112.0, "as_of": "2026-11-10"}}}))
    v = account.benchmark(dict(BOOK, positions=dict(BOOK["positions"])), {"last_session": "2026-11-11"})
    assert v["frozen_older_close"] == {"IEX": "2026-11-10"}
    assert "1 of your holdings are at an older close in this line (IEX at the 2026-11-10 close; the quote book has no 2026-11-11 close" in v["words"]
    row = json.loads((lake / "paper" / "account" / "benchmark.jsonl").read_text().splitlines()[-1])
    assert row["frozen_older_close"] == {"IEX": "2026-11-10"}
