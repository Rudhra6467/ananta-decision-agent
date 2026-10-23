"""My flags screen (Madhav, 23 Oct): the line under the title says where the Flag button is, and that matches where it sits."""
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app"


def test_flags_subtitle_says_where_the_flag_button_is():
    screen = (APP / "app" / "flags.tsx").read_text()
    assert "Flag button at the bottom left of every screen" in screen


def test_flag_button_really_sits_bottom_left():
    button = (APP / "src" / "flag.tsx").read_text()
    assert 'position: "absolute", left:' in button and "bottom:" in button
