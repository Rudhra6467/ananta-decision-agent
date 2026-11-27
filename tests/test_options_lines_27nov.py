"""27 Nov 2026 (flag 282): the Options pages say both windows (24 Nov) in short lines, each inside a page line's word limit, same numbers."""
from jarvis import placekit as K
from jarvis.india import places as P
from jarvis.india import surfaces as IS


def _row(day, rs):
    return {"date": day, "legs": {"option": {"net_rs_realistic": rs}}}


def test_two_windows_in_short_lines(monkeypatch):
    rows = [_row("2026-10-26", 1000), _row("2026-10-27", -5000), _row("2026-10-30", 20000), _row("2026-11-20", 60000), _row("2026-11-26", 3000)]
    rows[-1]["scored_at"] = "2026-11-27"
    monkeypatch.setattr(IS, "_sp1_outcomes", lambda: rows)
    monkeypatch.setattr(IS, "_managed", lambda: {"start_day": "2026-10-30", "day": "2026-11-26"})
    lines = P.options_two_windows_lines()
    assert lines[0] == "Since the line began (Mon 26 Oct): +₹79,000 over 5 trades."
    assert lines[1].startswith("Your account counts it from Fri 30 Oct, when the managed book started: +₹80,000 over 2 trades")
    assert lines[2] == "The 2 trades before that made −₹4,000."
    assert lines[3].startswith("1 trade scored after the last close joins")
    assert all(K.nwords(x) <= K.MAX["page_line"] for x in lines), lines
    # the one-sentence form keeps every number, for any reader that wants it whole
    whole = P.options_two_windows()
    for x in ("+₹79,000", "+₹80,000", "−₹4,000"):
        assert x in whole


def test_one_window_only(monkeypatch):
    monkeypatch.setattr(IS, "_sp1_outcomes", lambda: [_row("2026-10-30", 1000)])
    monkeypatch.setattr(IS, "_managed", lambda: {"start_day": "2026-10-30", "day": "2026-11-26"})
    assert P.options_two_windows_lines() == ["Since the line began (Fri 30 Oct): +₹1,000 over 1 trades."]
