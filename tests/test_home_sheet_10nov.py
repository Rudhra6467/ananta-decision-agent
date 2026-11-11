"""Madhav, 10 Nov 2026 22:12 Toronto, after looking at build 12: a number in Home's two boxes opens "like in second pic (the Needs you
sheet), but up to 75-80% of screen ... easy to close or swipe down to continue using in the same screen. For all in the 2 boxes"."""
from pathlib import Path

PLACE = (Path(__file__).resolve().parents[1] / "jarvis" / "app" / "src" / "place.tsx").read_text()


def test_home_boxes_open_their_numbers_in_a_tall_sheet():
    assert 'const overHome = data?.name === "home";' in PLACE, "only Home's boxes; Markets' boxes keep their full pages"
    assert "inSheet(b)" in PLACE and "pages: b.pages ? b.pages.map(" in PLACE, "every number of a paged box, not only the first"
    assert 'if (to.place && to.as === "sheet") { openSheet({ place: to.place }); return; }' in PLACE
    assert "if (s.place) return <PlaceSheet key={s.place} name={s.place} />;" in PLACE


def test_the_sheet_is_tall_and_easy_to_close():
    body = PLACE.split("function PlaceSheet(", 1)[1].split("\nexport function MainButton(", 1)[0]
    assert "height * 0.78" in body, "about 78% of the screen (75-80% asked)"
    assert "PanResponder.create" in body and "g.dy > keep.current.H * 0.18 || g.vy > 0.8" in body, "a swipe down on its top closes it"
    assert "contentOffset.y < -64" in body, "a pull down past the top of its page closes it (iPhone)"
    assert body.count("onPress={dismiss}") == 2, "a tap on the dimmed Home above it, and the X"
    assert "<Parts data={data}" in body and "<Pinned p={data?.pinned} />" in body, "the same page as before: chart, levels, Ask Ananta, the second button"
    assert 'userSelect: "none"' in body, "on the web a drag on its top never selects text (that cancels the drag)"


def test_leaving_the_sheet_closes_it():
    assert "if (to.tab || to.place || to.page) closeSheet();" in PLACE, "Show the portfolio or a tab closes the sheet first"
