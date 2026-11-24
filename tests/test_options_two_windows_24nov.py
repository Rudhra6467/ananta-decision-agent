"""24 Nov 2026 (Madhav, screenshots: the Options page +Rs 1,07,747, the account's Options box +Rs 1,21,322): both pages say both windows in one
sentence; the chart starts on a trading day; sheets stay solid in the glass look."""
from pathlib import Path

from jarvis.india import places as P
from jarvis.india import surfaces as IS

ROOT = Path(__file__).resolve().parents[1]


def _row(day, rs):
    return {"date": day, "legs": {"option": {"net_rs_realistic": rs}}}


def test_both_windows_in_one_sentence(monkeypatch):
    rows = [_row("2026-10-26", 1000), _row("2026-10-27", -5000), _row("2026-10-30", 20000), _row("2026-11-20", 60000)]
    monkeypatch.setattr(IS, "_sp1_outcomes", lambda: rows)
    monkeypatch.setattr(IS, "_managed", lambda: {"start_day": "2026-10-30", "day": "2026-11-20"})
    w = P.options_two_windows()
    assert "Since the line began (Mon 26 Oct): +₹76,000 over 4 trades" in w
    assert "from Fri 30 Oct" in w and "+₹80,000 over 2 trades" in w and "the 2 trades before that made −₹4,000" in w


def test_the_chart_starts_on_a_weekday(monkeypatch):
    monkeypatch.setattr(IS, "_sp1_outcomes", lambda: [_row("2026-10-26", 1000)])
    monkeypatch.setattr(P.views, "options", lambda: {"capital_inr": 50000})
    assert P.option_points()[0][0] == "2026-10-23"


def test_sheets_are_solid_in_the_glass_look():
    theme = (ROOT / "jarvis" / "app" / "src" / "theme.ts").read_text()
    glass = theme.split("const GLASS")[1].split("};")[0]
    assert "sheet" not in glass                                      # the glass look never makes a sheet see-through
    assert 'sheet: "#FFFFFF"' in theme and 'sheet: "#1D1F23"' in theme
    assert "backgroundColor: C.sheet" in (ROOT / "jarvis" / "app" / "src" / "place.tsx").read_text()
    assert "backgroundColor: C.sheet" in (ROOT / "jarvis" / "app" / "src" / "choicesheet.tsx").read_text()
