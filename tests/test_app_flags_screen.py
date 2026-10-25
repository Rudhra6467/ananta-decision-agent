"""My flags screen (Madhav, 23 Oct; 25 Oct: the Flag button left every screen, flags are said to Ananta): the line under the title says how to flag."""
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app"


def test_flags_subtitle_says_how_to_flag():
    screen = (APP / "app" / "flags.tsx").read_text()
    assert "tell Ananta by voice or chat" in screen and "Flag button" not in screen
    assert "FlagButton" not in (APP / "app" / "_layout.tsx").read_text()
