"""Movers and their news (india/movernews.py, NC1's live side): the window, the kinds and the words, on a made-up session."""
import datetime as dt
import gzip
import json

from india import movernews, paths


def _setup(tmp_path, monkeypatch):
    man = tmp_path / "manifests"
    man.mkdir()
    monkeypatch.setattr(paths, "manifest_dir", lambda: man)
    movers = [{"symbol": "AAA", "side": "up", "cc": 0.08}, {"symbol": "BBB", "side": "up", "cc": 0.06}, {"symbol": "CCC", "side": "down", "cc": -0.07}]
    (man / "missed_2026-11-25.json").write_text(json.dumps({"date": "2026-11-25", "movers": movers}))
    root = tmp_path / "announce_api"
    (root / "2026").mkdir(parents=True)
    rows23 = [{"symbol": "AAA", "desc": "Financial Result Updates", "attchmntText": "AAA Ltd has informed the Exchange regarding Financial Results",
               "exchdisstime": "23-Nov-2026 18:05:00"},
              {"symbol": "BBB", "desc": "Updates", "attchmntText": "BBB has received an order worth Rs 300 crore", "exchdisstime": "23-Nov-2026 11:00:00"}]
    rows25 = [{"symbol": "CCC", "desc": "Resignation", "attchmntText": "resignation of Mr Y as Chief Executive Officer", "exchdisstime": "25-Nov-2026 10:40:00"},
              {"symbol": "CCC", "desc": "Trading Window", "attchmntText": "closure of trading window", "exchdisstime": "25-Nov-2026 10:41:00"},
              {"symbol": "AAA", "desc": "Updates", "attchmntText": "AAA has received an order", "exchdisstime": "25-Nov-2026 16:10:00"}]
    for name, rows in (("20261123.json.gz", rows23), ("20261125.json.gz", rows25)):
        with gzip.open(root / "2026" / name, "wt") as f:
            f.write(json.dumps(rows))
    return root


def test_the_previous_session_skips_holidays_and_weekends():
    hol = {dt.date(2026, 11, 24)}
    assert movernews.previous_session(dt.date(2026, 11, 25), hol) == dt.date(2026, 11, 23)
    assert movernews.previous_session(dt.date(2026, 11, 23), hol) == dt.date(2026, 11, 20)


def test_the_window_runs_from_the_previous_close_to_this_close(tmp_path, monkeypatch):
    root = _setup(tmp_path, monkeypatch)
    n = movernews.news_for(dt.date(2026, 11, 25), dt.date(2026, 11, 23), root)
    assert [x["kinds"] for x in n["AAA"]] == [["results"]]                        # 23 Nov 18:05 counts; 25 Nov 16:10 is after this close
    assert "BBB" not in n                                                          # 23 Nov 11:00 was before the previous close
    assert [x["kinds"] for x in n["CCC"]] == [["management_exit"]]                 # the trading-window notice is routine


def test_the_lines_say_who_had_news_and_of_what_kind(tmp_path, monkeypatch):
    root = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(movernews, "_history", lambda: {"A|results": {"confirmed": 10, "cont_mean": -0.0046},
                                                       "A|management_exit": {"confirmed": 5, "cont_mean": -0.0108},
                                                       "A|no_news": {"cont_mean": -0.0183}})
    r = movernews.report(dt.date(2026, 11, 25), holidays={dt.date(2026, 11, 24)}, root=root)
    text = "\n".join(r["lines"])
    assert "1 of 2 gainers had company news (results 1)" in text
    assert "1 of 1 losers had company news (a senior exit 1)" in text
    assert "AAA (results)" in text and "CCC (a senior exit)" in text
    assert "with no news it gave back 1.8%" in text and "A study, not a rule." in text


def test_days_before_the_live_paper_start_are_not_read(tmp_path, monkeypatch):
    man = tmp_path / "manifests"
    man.mkdir()
    monkeypatch.setattr(paths, "manifest_dir", lambda: man)
    (man / "missed_2026-10-01.json").write_text(json.dumps({"date": "2026-10-01", "movers": [{"symbol": "X", "side": "up"}]}))
    assert "only live paper days" in movernews.report(dt.date(2026, 10, 1))["lines"][0]
