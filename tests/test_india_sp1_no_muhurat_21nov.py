"""21 Nov 2026 (the keen audit's G-02; decided 14 Nov, choice a: the Muhurat hour is no session anywhere): the options line's morning read
must not take the Sunday Muhurat hour of 8 Nov as the previous session for Mon 9 Nov. Fails on the code before (no no_special_sessions)."""
import datetime as dt

import pandas as pd

from india import sp1paper


def test_the_muhurat_hour_and_weekends_are_not_a_previous_session(monkeypatch):
    from india import nse

    monkeypatch.setattr(nse, "special_sessions", lambda: {dt.date(2026, 11, 8)})
    raw = pd.DataFrame({"date": [dt.date(2026, 11, 6), dt.date(2026, 11, 7), dt.date(2026, 11, 8)], "index_name": "NIFTY 50", "close": [1.0, 2.0, 3.0]})
    kept = sp1paper.no_special_sessions(raw)
    assert list(kept["date"]) == [dt.date(2026, 11, 6)]                       # Friday 6 Nov is the previous session for Monday 9 Nov


def test_without_the_list_weekends_still_go(monkeypatch):
    from india import nse

    def boom():
        raise OSError("no manifest")
    monkeypatch.setattr(nse, "special_sessions", boom)
    raw = pd.DataFrame({"date": [dt.date(2026, 11, 6), dt.date(2026, 11, 8)], "close": [1.0, 3.0]})
    assert list(sp1paper.no_special_sessions(raw)["date"]) == [dt.date(2026, 11, 6)]
