"""Madhav, 10 Nov 2026 22:12 Toronto, after looking at build 12: a number in Home's two boxes opens "like in second pic (the Needs you
sheet), but up to 75-80% of screen ... easy to close or swipe down to continue using in the same screen. For all in the 2 boxes".
22:23: "Yes" to Markets' boxes too, "and make sure the design of those sheets looks premium and feel premium"."""
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app"
PLACE = (APP / "src" / "place.tsx").read_text()
BODY = PLACE.split("function PlaceSheet(", 1)[1].split("\nfunction ", 1)[0]          # the tall sheet only (11 Nov: the item sheet follows it)


def test_home_and_markets_boxes_open_their_numbers_in_a_tall_sheet():
    assert 'const SHEET_PLACES = ["home", "markets"];' in PLACE
    assert "const overHome = SHEET_PLACES.includes(data?.name);" in PLACE, "Home's two boxes"
    assert 'case "peek": out.push(<Peek key={k} p={SHEET_PLACES.includes(data?.name) ? { ...p, items: (p.items || []).map(inSheet) } : p} />)' in PLACE, "Markets' boxes"
    assert "pages: b.pages ? b.pages.map(" in PLACE, "every number of a paged box, not only the first"
    assert 'if (to.place && to.as === "sheet") { openSheet({ place: to.place, peek: to.peek }); return; }' in PLACE
    assert "if (s.place) return <PlaceSheet key={s.place} name={s.place} peek={s.peek} />;" in PLACE


def test_the_sheet_is_tall_and_easy_to_close():
    assert "height * 0.78" in BODY, "about 78% of the screen (75-80% asked)"
    assert "PanResponder.create" in BODY and "g.dy > h * 0.22 || g.vy > 0.75" in BODY, "a swipe or a fling down on its top closes it"
    assert "contentOffset.y < -64" in BODY, "a pull down past the top of its page closes it (iPhone)"
    assert BODY.count("onPress={() => dismiss(0)}") == 2, "a tap on the dimmed screen above it, and the X"
    assert 'e.key === "Escape"' in BODY, "Escape on the web"
    assert "<Parts data={data}" in BODY and "<Pinned p={data?.pinned} />" in BODY, "the same page as before: chart, levels, Ask Ananta, the second button"
    assert 'userSelect: "none"' in BODY, "on the web a drag on its top never selects text (that cancels the drag)"


def test_the_sheet_looks_and_feels_premium():
    stage = PLACE.split("export function SheetStage(", 1)[1].split("\nfunction ", 1)[0]
    assert "outputRange: [0.94, 1]" in stage and "borderRadius: 22" in stage and '"#000"' in stage, "the screen behind steps back, rounded, on black"
    assert "<SheetStage><Stack" in (APP / "app" / "_layout.tsx").read_text()
    assert "Animated.spring(SHEET_Y, { toValue: 0, ...OPEN" in BODY and "overshootClamping: true" in BODY, "springs up; closes without a bounce"
    assert "Math.sqrt(-g.dy) * 4" in BODY, "gives a little when pulled up, then no more"
    assert "tap();" in BODY and "soft();" in BODY, "a light tap when it opens, a tick at the closing point"
    assert "{peek ? <Hero p={peek} /> : null}" in BODY and "<Shimmer h={300} />" in BODY, "the number shows at once while the page loads"
    assert "SHEET_CACHE.get(key)" in BODY, "a page seen before opens from memory"
    assert "style={ROUND()}" in BODY, "a soft round X"
    assert "<HideButton" not in BODY, "11 Nov 07:51 (Madhav: \"Only in home tab\"): the eye is on Home, not on the sheet"
    assert "shadowRadius: 28" in BODY and "<Fade />" in BODY, "a shadow, and a fade above the buttons"


def test_leaving_the_sheet_closes_it():
    assert "if (to.tab || to.place || to.page) closeSheet();" in PLACE, "Show the portfolio or a tab closes the sheet first"
    assert "SHEET_Y.setValue(1);" in BODY.split("return () =>", 1)[1], "and the screen behind comes back to full size"


def test_he_answers_in_the_needs_you_sheet_and_can_clear_notifications():
    # Madhav, 10 Nov 22:33: a Yes in the sheet ("get approved straight away"), and a way to clear notifications that keeps the item on the list
    assert "function AnswerList(" in PLACE and '"/v3/openlist/answer", a.due ? { key: s.key, answer: a.id, due: a.due } : { key: s.key, answer: a.id }' in PLACE
    assert "const talk = s.primary ? [" in PLACE and "s.key && Array.isArray(s.answers) ? s.answers : []" in PLACE, "a sheet with no answers still offers Ask"
    assert 'if (to.action === "clear_needs") { clearNeeds(); return; }' in PLACE and '{ key: "all", answer: "later" }' in PLACE
    assert "refreshPlaces();" in PLACE, "the bell and the places read again after an answer"
    assert '"/v3/openlist"' in (APP / "src" / "api.ts").read_text(), "the open list lives with the sign-in service for both markets"
