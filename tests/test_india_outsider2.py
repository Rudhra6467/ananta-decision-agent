"""27 Oct 2026 night, second outside review: the daily call's record counts next-session scores once (it had jumped from 1 of 6 to 1 of 8
when the 5-session scores were added in), the options line under 10 sessions is 'too early to grade', and the lookup-only TRI / IPO files.
Fixture files only; the network is never touched."""
import datetime as dt
import json

from india import allocator, lookupdata, paths, readmodel


def test_daily_call_counts_next_session_scores_once(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    (tmp_path / "paper").mkdir()
    rows = [{"kind": "call", "data_through": "2026-10-16", "call": "BULLISH", "rule": "r", "null_call": "BULLISH"},
            {"kind": "call", "data_through": "2026-10-19", "call": "BULLISH", "rule": "r", "null_call": "BEARISH"},
            {"kind": "score", "data_through": "2026-10-16", "horizon": 1, "score": -1, "null_score": -1},
            {"kind": "score", "data_through": "2026-10-19", "horizon": 1, "score": 1, "null_score": -1},
            {"kind": "score", "data_through": "2026-10-16", "horizon": 5, "score": -1, "null_score": 1},
            {"kind": "score", "data_through": "2026-10-19", "horizon": 1, "score": 1, "null_score": -1}]          # a repeated line counts once
    (tmp_path / "paper" / "calls.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    c = readmodel.call("2026-10-19")
    assert (c["scored"], c["hits"], c["null_hits"]) == (2, 1, 0)
    assert c["five_sessions"] == {"scored": 1, "hits": 0, "null_hits": 1}
    assert "1 of 2 calls right" in c["words"]


def test_options_line_too_early_to_grade():
    r = {"options_inr": 34000, "evidence_sessions": 20}
    o = allocator.rate_options({"sp1": {"book": {"sessions": 2}}, "market": {"vix_close": 16.0}}, r, 34000)
    assert o["too_early_to_grade"] and o["grade_words"].startswith("too early to grade (2 sessions") and o["words"].startswith("Too early to grade")
    assert o["grade"] in "ABCD" and isinstance(o["score"], int)                                     # the score itself is unchanged
    o = allocator.rate_options({"sp1": {"book": {"sessions": 12}}, "market": {"vix_close": 16.0}}, r, 34000)
    assert not o["too_early_to_grade"] and o["grade_words"].startswith("grade ")


class _Resp:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


class _Sess:
    def __init__(self, body):
        self.body = body

    def post(self, *a, **k):
        return _Resp(self.body)


def test_tri_chunk_parses_both_shapes():
    rows = [{"Date": "27 Oct 2026", "TotalReturnsIndex": "34,579.35"}, {"Date": "bad", "TotalReturnsIndex": "1"}]
    a, b = dt.date(2026, 10, 1), dt.date(2026, 10, 27)
    assert lookupdata._tri_chunk(_Sess(rows), "Nifty 50", a, b) == [("2026-10-27", 34579.35)]
    assert lookupdata._tri_chunk(_Sess({"d": json.dumps(rows)}), "Nifty 50", a, b) == [("2026-10-27", 34579.35)]


def test_ipo_keeps_the_last_good_list_when_a_fetch_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(lookupdata.time, "sleep", lambda s: None)
    (tmp_path / "mf_cache").mkdir()
    (tmp_path / "mf_cache" / "ipo.json").write_text(json.dumps({"built_at": "2026-10-26T20:00:00", "current": [{"symbol": "OLD"}], "upcoming": []}))

    class S:
        headers = {}

        def get(self, url, timeout):
            if "current" in url:
                raise OSError("blocked")
            return _Resp({"data": [{"symbol": "NEW", "companyName": "New Ltd", "issueStartDate": "-", "priceBand": "Rs.10 to Rs.11"}]})
    monkeypatch.setattr(lookupdata.requests, "Session", S)
    out = lookupdata.ipo(log=lambda *a: None)
    j = json.loads((tmp_path / "mf_cache" / "ipo.json").read_text())
    assert j["current"] == [{"symbol": "OLD"}] and j["upcoming"] == [{"symbol": "NEW", "companyName": "New Ltd", "priceBand": "Rs.10 to Rs.11"}]
    assert out["errors"] and "kept the list from 2026-10-26" in out["errors"][0]
