"""12 Nov 2026 (Madhav, a screenshot of the voice screen: "there is no chat option and also couldn't access all the options available from
the screen"). In the redesign the Ask place was drawn edge to edge: its top row sat under the phone's status bar and the floating bar
covered its typing box, the voice screen's orb and "End voice · type instead". These checks read the app's source, the way
tests/test_places.py does, so the fix cannot quietly fall out again."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app"
ASK = (APP / "app" / "(tabs)" / "ask.tsx").read_text()
BAR = (APP / "app" / "new" / "_layout.tsx").read_text()
STAGE = (APP / "src" / "voicestage.tsx").read_text()
ROOT = (APP / "app" / "_layout.tsx").read_text()
ONCE = (APP / "src" / "once.ts").read_text()


def test_ask_leaves_room_for_the_status_bar_and_the_floating_bar():
    assert "useSafeAreaInsets" in ASK
    assert "const padTop = isNew ? ins.top : 0;" in ASK
    assert "BAR_ROOM + Math.max(ins.bottom, 12)" in ASK                   # the typing box stands above the bar
    assert ASK.count("paddingTop: padTop") >= 3                           # the chat, "Ananta now" and the voice screen
    assert "export const BAR_ROOM = 64 + 26 + 10;" in ONCE


def test_the_bar_steps_aside_on_the_big_voice_screen():
    assert "setVoiceStage(onStage)" in ASK
    assert "const onStage = isNew && live && !showChat;" in ASK
    assert "(typing || stage) && active === \"ask\"" in BAR


def test_the_voice_screen_has_a_chat_button_and_the_chat_has_a_way_back():
    assert 'accessibilityLabel="Show the chat"' in STAGE
    assert ">Chat</Text>" in STAGE
    assert "End voice · type instead" in STAGE
    assert ">Voice screen</Text>" in ASK                                  # back from the conversation to the voice screen


def test_ask_is_bronze_in_the_redesign_and_keeps_its_accent_in_classic():
    assert "BRONZE = isNew;" in ASK
    assert "return BRONZE ? C.gold : C.accent;" in ASK
    body = ASK.split("const AC = {", 1)[1].split("\n", 1)[1]
    assert not re.search(r"(?<![A-Za-z])C\.accent", body)                # every piece of the screen reads the one holder


def test_the_voice_pill_returns_to_the_redesigns_ask_and_clears_the_top_row():
    assert "goTab(askHome(!!me?.guest))" in ROOT
    assert "onNew ? { bottom: BAR_ROOM + Math.max(ins.bottom, 12) + 8 } : { top: 56 }" in ROOT
    look = (APP / "src" / "look.ts").read_text()
    assert '"/(tabs)/ask" : "/new/ask"' in look


def test_no_layout_preview_screen_ships():
    assert not (APP / "app" / "zzpreview.tsx").exists()
