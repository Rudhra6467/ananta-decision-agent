"""The item sheet and its choices (Madhav, 11 Nov 2026). 07:51, with Claude's Usage sheet: "Notification sheets like this ... where you can
drag up or down and also tells the same structurally the same"; "there is no need of hide symbol in all the pages right? Only in home tab".
08:13, with YouTube's "Ask about this video" sheet: "every notification gets, gives me the options like this, and upon clicking, I can
select any action, or ... have an explanation of the action ... a down arrow towards the end"."""
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app" / "src"
PLACE = (APP / "place.tsx").read_text()
SCREEN = (APP / "placescreen.tsx").read_text()
ITEM = PLACE.split("function ItemSheet(", 1)[1].split("\nfunction ", 1)[0]
LIST = PLACE.split("function AnswerList(", 1)[1].split("\nexport function ", 1)[0]


def test_every_item_and_notification_opens_in_the_item_sheet():
    assert "return <ItemSheet key={String(s.key || s.title || \"\")} s={s} />;" in PLACE
    assert "function SheetCards(" in PLACE and "progress" in PLACE.split("function SheetCards(", 1)[1].split("\nfunction ", 1)[0]


def test_it_drags_up_and_down_and_closes_every_way():
    assert "height * 0.75" in ITEM, "it opens at the height it needs, at most 75% of the screen"
    assert "PanResponder.create" in ITEM and "Math.sqrt(h - w) * 4" in ITEM, "up: it grows to all of it, then gives a little"
    assert "else if (h < r) { t = r - h; h = r; }" in ITEM, "down: smaller first, then it slides"
    assert "t > r * 0.25 || (t > 0 && g.vy > 0.75)" in ITEM, "further down or a fling closes it"
    assert ITEM.count("onPress={() => dismiss(0)}") == 2 and 'e.key === "Escape"' in ITEM and "contentOffset.y < -64" in ITEM
    assert "soft();" in ITEM and "tap();" in ITEM and 'userSelect: "none"' in ITEM
    assert "<AnswerList s={s} onDone={() => dismiss(0)} />" in ITEM, "the choices sit in the sheet's page"


def test_each_choice_is_a_row_with_an_arrow_that_says_what_it_does():
    assert "rows.map((a, i) =>" in LIST and 'name={isOpen ? "chevup" : "chevdown"}' in LIST
    assert "onPress={() => act(a)}" in LIST and "onPress={() => toggle(id)}" in LIST, "the row does it; the arrow only explains"
    assert "{a.explain}</Text>" in LIST and "accessibilityState={{ expanded: isOpen }}" in LIST
    assert "a.due ? { key: s.key, answer: a.id, due: a.due }" in LIST, "a postpone row sends its day"
    assert 'if (a.id === "talk")' in LIST and "refreshPlaces();" in LIST
    assert 'chevdown: "' in PLACE and 'ask: "' in PLACE


def test_the_eye_is_on_home_only():
    assert '{name === "home" ? <HideButton /> : null}' in SCREEN
    page = SCREEN.split("export function PageScreen(", 1)[1]
    assert "<HideButton" not in page and "<HideButton" not in ITEM
    assert "<HideButton" not in PLACE.split("function PlaceSheet(", 1)[1].split("\nfunction ", 1)[0]


def test_before_and_after_is_drawn():
    assert 'case "ba": out.push(<BeforeAfter key={k} p={p} />); break;' in PLACE and "function BeforeAfter(" in PLACE
