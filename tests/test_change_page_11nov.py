"""A change page that reads easily (Madhav, 11 Nov 2026, 07:51: "how do we present the content in a more readable and easy to understand
way. Like simple language, simple points, graphs or any other structures"): In short, Before and after, Why in his own words, and the
full record one tap down."""
from jarvis import placekit as K
from jarvis import selfknow
from jarvis.service import places

LINE = {"date": "2026-11-11", "market": "both", "area": "watchdog", "status": "live",
        "words": "Fixed: the self-check tells the other market's item with its side. And one errored run of a part that runs every 15 minutes, "
                 "followed by a clean run, is now a low blip, not HIGH for 24 hours.",
        "why": 'Madhav, 11 Nov 06:50 Toronto: "i dont want to wait, when we have everything we need, just get it done" (the open findings of '
               "the earlier audits). Faults only, from Ananta's own records; no book rule changed. Register R-007, seen again on 11 Nov.",
        "checked": "tests/test_open_findings_11nov.py (the side named; one blip low); tests/test_runcheck.py; the live check (~/ananta_runs/x.log)",
        "commits": ["cc682e4"], "source": "session",
        "plain": ["India answers now say when a problem is on the crypto side.", "A one-time hiccup that fixed itself shows as small."],
        "before_after": [{"label": "One missed scan, then clean runs", "before": "HIGH for 24 hours", "after": "a low blip"}]}


def _part(page, t, title=None):
    return next(p for p in page["parts"] if p.get("t") == t and (title is None or p.get("title") == title))


def test_the_page_says_in_short_before_and_after_and_why_in_his_words():
    pg = places.change_page(LINE)
    assert [p["t"] for p in pg["parts"]] == ["pill", "heading", "points", "ba", "points", "link", "trust"]
    assert pg["parts"][0]["text"] == "Live · Wed 11 Nov" and pg["parts"][1]["text"] == "The watchdog"
    assert [i["text"] for i in _part(pg, "points", "In short")["items"]] == LINE["plain"]
    assert _part(pg, "ba")["rows"] == LINE["before_after"] and _part(pg, "ba")["title"] == "Before and after"
    why = [i["text"] for i in _part(pg, "points", "Why")["items"]]
    assert why[0] == "You said on 11 Nov: “i dont want to wait, when we have everything we need, just get it done” (the open findings of the earlier audits)"
    assert why[1:] == ["Faults only, from Ananta's own records.", "No book rule changed."], "register numbers stay in the full record"
    full = _part(pg, "link")["to"]["page"]
    assert full["title"] == "The full record" and full["pinned"]["ask"]
    assert [i["text"] for i in _part(full, "points", "How it was checked")["items"]] == ["A test: the side named; one blip low", "The live check"]
    assert {r["k"]: r["v"] for r in _part(full, "kv")["rows"]} == {"Day": "Wed 11 Nov", "Market": "Both", "Status": "Live", "Commits": "cc682e4"}
    assert any("Register R-007" in i["text"] for i in _part(full, "points", "Why, in full")["items"])
    assert K.problems("change", pg) == []


def test_a_line_without_plain_words_gives_its_first_two_sentences():
    ln = {k: v for k, v in LINE.items() if k not in ("plain", "before_after")}
    pg = places.change_page(ln)
    assert [p["t"] for p in pg["parts"]] == ["pill", "heading", "points", "points", "link", "trust"]
    short = [i["text"] for i in _part(pg, "points", "In short")["items"]]
    assert short[0] == "The self-check tells the other market's item with its side" and short[1].startswith("And one errored run")


def test_his_words_are_found_however_the_book_wrote_them():
    assert places._why_points("Madhav, 5 Nov 09:32: 'real fix is to have Ananta start speaking while it's still writing the answer.'.") == [
        "You said on 5 Nov: “real fix is to have Ananta start speaking while it's still writing the answer”"]
    assert places._why_points("Madhav, 2 Nov: yes.") == ["Your yes on 2 Nov."]
    assert places._why_points("Madhav, 1 Nov") == ["You asked for it on 1 Nov."]
    assert places._why_points("Madhav, 3 Nov: clarity over features.") == ["You said on 3 Nov: clarity over features."]


def test_the_real_book_reads_well_on_every_page():
    selfknow._CACHE.clear()
    rows = selfknow.changes()
    assert all(K.problems("change", places.change_page(r)) == [] for r in rows)
    today = [r for r in rows if r["date"] == "2026-11-11"]
    assert len([r for r in today if r.get("plain")]) >= 16, "the 11 Nov lines carry their plain words"
    nights = next(r for r in today if r["words"].startswith("The 14 nightly records"))
    assert nights["before_after"] == [{"label": "28 Oct close", "before": "C$452.03", "after": "C$479.39"},
                                      {"label": "10 Nov close", "before": "C$439.49", "after": "C$467.55"}]
