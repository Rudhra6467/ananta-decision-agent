"""5 Nov 2026 (Madhav: "yes to all", B): the 09:08 IST pre-open read."""
import datetime as dt
import json

from jarvis.india import preopen


def _fetch(moved: bool):
    from jarvis.india import livesession
    livesession._CACHE.clear()                  # quotes are cached for a minute

    def f(syms):
        out = {}
        for s in syms:
            prev = 100.0
            last = 101.0 if (moved or not s.startswith("NSE:NIFTY")) else 100.0
            if s in ("NSE:SBIN", "NSE:ITC"):
                last = 99.0
            out[s] = {"last_price": last, "ohlc": {"close": prev}}
        return out
    return f


def test_the_read_and_its_words():
    d = preopen.read(_fetch(True), now=dt.datetime(2026, 11, 6, 9, 9, tzinfo=preopen.IST))
    w = preopen.words(d)
    assert d["index_moved"] and d["heavy"]["up"] == 8 and d["heavy"]["down"] == 2
    assert w.startswith("Pre-open read at 09:09 IST") and "Nifty indicated near 101 (+1.0% on yesterday's close)" in w
    assert "8 of 10 heavy stocks indicated higher" in w and "nothing trades on them" in w


def test_an_index_quote_that_did_not_move_is_not_said():
    d = preopen.read(_fetch(False), now=dt.datetime(2026, 11, 6, 9, 9, tzinfo=preopen.IST))
    w = preopen.words(d)
    assert not d["index_moved"] and "Nifty indicated" not in w and "heavy stocks" in w


def test_today_reads_the_file_only_in_the_morning(tmp_path, monkeypatch):
    monkeypatch.setattr(preopen, "OUT", tmp_path)
    d = preopen.read(_fetch(True), now=dt.datetime(2026, 11, 6, 9, 9, tzinfo=preopen.IST))
    (tmp_path / "2026-11-06.json").write_text(json.dumps(d))
    clk = {"today_india": "2026-11-06", "latest_session": "2026-11-06", "state": "closed"}
    assert preopen.today(clk) is None
