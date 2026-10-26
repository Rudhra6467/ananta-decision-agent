"""index_cross_dates (purpose technicals_history; Madhav, 26 Oct 2026: "when did the 50-day last cross the 200-day?"): only the event list
leaves the sealed loader, never a price or a return; any other purpose is refused; the read is logged."""
import json

import pandas as pd
import pytest

from india import sealed


def test_other_purposes_are_refused():
    for p in ("paper_context", "paper_lookback", "research", "holdout"):
        with pytest.raises(PermissionError):
            sealed.index_cross_dates(p, ["NIFTY 50"])


def test_only_cross_dates_leave_and_the_read_is_logged(tmp_path, monkeypatch):
    data = tmp_path / "india"
    (data / "silver/kite_index/day").mkdir(parents=True)
    (data / "manifests").mkdir()
    days = pd.bdate_range("2022-01-03", periods=600)
    up = [100 + i * 0.5 for i in range(300)]
    down = [up[-1] - i * 0.8 for i in range(1, 301)]
    pd.DataFrame({"index_name": "NIFTY 50", "date": days.date, "close": up + down}).to_parquet(data / "silver/kite_index/day/day.parquet")
    monkeypatch.setattr(sealed.paths, "data_dir", lambda: data)
    monkeypatch.setattr(sealed.paths, "manifest_dir", lambda: data / "manifests")
    ev = sealed.index_cross_dates("technicals_history", ["NIFTY 50"], since="2022-01-01")
    assert ev and all(set(e) == {"index_name", "date", "pair", "direction", "sessions_ago"} for e in ev)
    d200 = [e for e in ev if e["pair"] == "50/200"]
    assert len(d200) == 1 and d200[0]["direction"] == "down" and d200[0]["date"] > str(days[300].date())
    log = [json.loads(x) for x in (data / "manifests" / "sealed_access.jsonl").read_text().splitlines()]
    assert log[-1]["purpose"] == "technicals_history" and "cross dates only" in log[-1]["what"]
