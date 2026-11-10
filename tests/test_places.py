"""The redesign's places (Madhav, 10 Nov 2026: "yes for all your recommendations. lets complete it and test it as planned").

The plan's checks, as tests: the eight rules on every first-layer payload (the word budget), every tap goes somewhere that exists (the
tap-through), and nothing the old screens showed is lost (coverage: the old cards' facts are one tap down). Built from fixed inputs, so
nothing here reads the live book, Kite or NDAX."""
import datetime as dt
import json
import re
from pathlib import Path

import pytest

from jarvis import placekit as K
from jarvis.service import places as CP
from jarvis.service import surfaces as S
from tests.test_crypto_surfaces_10nov import CLOSED, LINE

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis" / "app"
TABS = {p.stem for p in (APP / "app" / "new").glob("*.tsx") if not p.stem.startswith("_")}
NOW = dt.datetime(2026, 11, 10, 12, 30, tzinfo=S.TOR)
BOOK = {"started": "2026-10-11", "value_cad": 467.55, "cash_cad": 467.55, "return_pct": -6.49, "positions": {},
        "closed": [{"coin": "SOL", "sleeve": "EDGE", "in": "2026-10-27", "out": "2026-11-06", "pnl_cad": -3.38, "pct": -12.01, "why": "10 days"},
                   {"coin": "BTC", "sleeve": "CORE", "in": "2026-11-05", "out": "2026-11-06", "pnl_cad": -3.49, "pct": -5.85, "why": "dial closed"}],
        "recent_fills": [], "brakes": {}, "graduation": {"passed": 3, "of": 10, "verdict": "NOT READY", "closed_trades": 2}}
FILLS = [{"t": dt.datetime(2026, 10, 27, 1, tzinfo=dt.timezone.utc).timestamp(), "coin": "SOL", "side": "BUY", "sleeve": "EDGE", "qty": 0.198418, "px": 141.67, "fee": 0.06, "why": "H07: RSI(10) 30"},
         {"t": dt.datetime(2026, 11, 6, 1, tzinfo=dt.timezone.utc).timestamp(), "coin": "SOL", "side": "SELL", "sleeve": "EDGE", "qty": 0.198418, "px": 125.15, "fee": 0.05, "why": "10 days"},
         {"t": dt.datetime(2026, 11, 5, 1, tzinfo=dt.timezone.utc).timestamp(), "coin": "BTC", "side": "BUY", "sleeve": "CORE", "qty": 0.00052844, "px": 112763.88, "fee": 0.12, "why": "core-v2 tranche 1"},
         {"t": dt.datetime(2026, 11, 6, 1, tzinfo=dt.timezone.utc).timestamp(), "coin": "BTC", "side": "SELL", "sleeve": "CORE", "qty": 0.00052844, "px": 106589.0, "fee": 0.11, "why": "dial closed"}]
LIST = {"counts": {"YOU": 2, "WORK": 3, "DATE": 4, "PARKED": 5},
        "you": [{"id": "flag 73", "kind": "YOU", "market": "both", "line": "Turn on phone notes: the Apple push key needs your Apple ID sign-in once.", "advice": "your step at the Mac"},
                {"id": "flag 74", "kind": "YOU", "market": "both", "line": "Look at the worker Mac: it dropped out twice on 9 Nov.", "advice": "your step"}],
        "work": [{"id": "flag 6", "market": "crypto", "line": "Ananta cannot say when you last spoke with it. It should know the date."}],
        "dated": [{"id": "flag 84", "market": "crypto", "line": "First night of the 10 Nov changes: check the 7:05 pm run.", "due": "2026-11-10"}],
        "parked": [{"id": "flag 77", "market": "both", "line": "The public App Store listing: parked until phone notes work."}]}
CHANGES = [{"date": "2026-11-10", "market": "both", "area": "app", "status": "decided", "words": "Decided on Madhav's yes: the screens as drawn on the design canvas, and Icon A.",
            "why": "Madhav, 10 Nov", "checked": "the open list read back"},
           {"date": "2026-11-10", "market": "crypto", "area": "crypto_books", "status": "live", "words": "Repaired: the $500 book's missing ETH trade is recorded as sold.", "why": "w", "checked": "c"}]


def _closes(n=120, start=80000.0):
    return [start * (1 + 0.001 * ((k * 7) % 13 - 6)) for k in range(n)]


@pytest.fixture()
def crypto(monkeypatch):
    from jarvis import selfknow
    from jarvis.service import discipline, feed, health, nightcheck, officer, openlist
    monkeypatch.setattr(S, "_book", lambda j: json.loads(json.dumps(BOOK)))
    monkeypatch.setattr(S, "_dial", lambda j: dict(CLOSED))
    monkeypatch.setattr(feed, "last_closes", lambda j: {"BTC": 75368.0, "ETH": 2135.0, "SOL": 86.74})
    monkeypatch.setattr(feed, "prices", lambda j: {"BTC": 73043.0, "ETH": 2025.0, "SOL": 82.42})
    monkeypatch.setattr(health, "status", lambda j: {"all_ok": True, "last_check_s_ago": 30})
    monkeypatch.setattr(discipline, "plan_line", lambda j: {"line": LINE, "checks": []})
    monkeypatch.setattr(openlist, "collect", lambda j: json.loads(json.dumps(LIST)))
    monkeypatch.setattr(selfknow, "changes", lambda: list(CHANGES))
    monkeypatch.setattr(officer, "latest", lambda j, n=3: [{"day": "2026-11-10", "t": 0, "note": "Sir, the account sat entirely in cash today. No brake fired.", "cost_usd": 0.02}])
    monkeypatch.setattr(officer, "clean_nights", lambda j: {"in_a_row": 0, "need": 30, "since": "2026-11-11"})
    monkeypatch.setattr(nightcheck, "latest", lambda: None)
    monkeypatch.setattr(S, "_repairs", lambda j: [{"day": "2026-11-10", "what": "ETH sale", "cash_added": 28.06}])
    monkeypatch.setattr(S, "book_gap", lambda j, b: [])
    monkeypatch.setattr(S, "_running", lambda h: {"ok": True, "words": "Everything is running", "checked": "checked just now"})
    cc = _closes()
    monkeypatch.setattr(S, "coin_chart", lambda j, coin, n=120: {"chart": {"closes": cc, "sma50": [x * 1.02 for x in cc], "sma200": [x * 0.97 for x in cc]},
                                                                  "words": f"{S.COIN_NAME.get(coin, coin)} closed at $75,368 on Mon 9 Nov. That is 5.0% below its 50-day average.", "note": "Daily closes."})
    monkeypatch.setattr(S, "account_chart", lambda j: {"chart": {"dates": ["2026-10-10", "2026-11-09"], "yours": [500.0, 439.49], "untouched": [500.0, 454.0]}})
    monkeypatch.setattr(S, "proof", lambda j: {"studies": {"big": 16, "sub": "2 active · 4 parked · 8 measured only", "explain": {"points": ["Two are active."]}},
                                               "exam": {"grade": "Pass", "day": "2026-11-08", "words": "20/20 facts · Sun 8 Nov"},
                                               "clocks": [{"name": "The evidence window (Rule A and B)", "done": 27, "need": 60, "finish_words": "Mon 14 Dec"}],
                                               "missed": {"words": "In 7 days your ten main coins made 29 big moves. 1 missed."}, "last_night": {"words": "Found nothing new."},
                                               "links": [{"label": "The repair board", "route": "/flags"}, {"label": "What we missed", "route": "/missed"}]})
    monkeypatch.setattr(S, "money", lambda j: {"books": [{"id": "managed", "label": "The $500 book", "ret_pct": -6.5}, {"id": "index", "label": "Bitcoin, just held", "ret_pct": -9.2}],
                                               "books_ask": "Explain the book.", "under_check": None})
    monkeypatch.setattr(CP, "_fills", lambda j: list(FILLS))

    class FakeNow(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)
    monkeypatch.setattr(CP.dt, "datetime", FakeNow)

    class J:
        def people(self):
            return {"visitors": []}
    return J()


def _targets(x, path="payload"):
    """Every tap in a payload, with where it is."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("to", "more") and isinstance(v, dict):
                yield path + "." + k, v
            if k == "primary" and isinstance(v, dict) and isinstance(v.get("to"), dict):
                yield path + ".primary", v["to"]
            yield from _targets(v, path + "." + k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _targets(v, f"{path}[{i}]")


def _app_route_exists(r: str) -> bool:
    r = r.split("?")[0].strip("/")
    base = APP / "app"
    if (base / (r + ".tsx")).exists() or (base / r / "index.tsx").exists():
        return True
    head = r.split("/")[0]
    return any((base / head).glob("[[]*[]].tsx")) if (base / head).is_dir() else False


def _check_taps(payload: dict, places: set):
    bad = []
    for where, to in _targets(payload):
        if "tab" in to and to["tab"] not in TABS:
            bad.append(f"{where}: tab {to['tab']} is not a place on the bar")
        if "place" in to and to["place"] not in places and not to["place"].startswith("coin:"):
            bad.append(f"{where}: place {to['place']} does not exist")
        if "page" in to and not (to["page"].get("parts") and (to["page"].get("pinned") or {}).get("ask")):
            bad.append(f"{where}: a page with no parts or no main button")
        if "route" in to and not _app_route_exists(to["route"]):
            bad.append(f"{where}: route {to['route']} is not a screen of the app")
        if "ask" in to and len(str(to["ask"]).split()) < 3:
            bad.append(f"{where}: a question too short to ask")
        if not set(to) & {"tab", "place", "page", "sheet", "ask", "route", "action"}:
            bad.append(f"{where}: a tap that goes nowhere: {to}")
    return bad


CRYPTO = ["home", "markets", "activity", "more", "account", "why", "proof", "notices", "openlist", "people", "coin:ETH"]


@pytest.mark.parametrize("name", CRYPTO)
def test_every_crypto_place_keeps_the_eight_rules(crypto, name):
    p = CP.get(crypto, name)
    assert K.problems(name, p) == []


@pytest.mark.parametrize("name", CRYPTO)
def test_every_tap_on_a_crypto_place_goes_somewhere(crypto, name):
    places = set(CP.PLACES) | {"needs"}
    assert _check_taps(CP.get(crypto, name), places) == []


def test_home_says_the_account_today_and_what_needs_you(crypto):
    h = CP.get(crypto, "home")
    hero = next(p for p in h["parts"] if p["t"] == "hero")
    assert hero["value"] == "C$467.55" and hero["tone"] == "bad" and "−6.5%" in hero["change"]
    today = next(p for p in h["parts"] if p["t"] == "today")
    assert today["line"] == "No new buys. All in cash." and today["to"] == {"place": "why"}
    needs = next(p for p in h["parts"] if p["t"] == "rows" and p["title"] == "Needs you")
    assert [r["title"] for r in needs["rows"]] == ["Turn on phone notes", "Look at the worker Mac"]
    assert needs["rows"][0]["to"]["sheet"]["text"].startswith("The Apple push key")       # the sheet does not repeat its title
    assert h["bell"]["count"] == 2
    assert K.words_on(h) <= K.MAX["home_words"]
    # the old Today's two boxes are the summary boxes; a correction is a notice card that can be closed
    boxes = next(p for p in h["parts"] if p["t"] == "boxes")["items"]
    assert boxes[0]["label"] == "Bitcoin" and boxes[0]["value"] == "$73,043" and boxes[1]["label"] == "In coins"
    assert any("corrected" in n["line"] for n in next(p for p in h["parts"] if p["t"] == "notices")["items"])


def test_nothing_the_old_screens_showed_is_lost(crypto):
    """Coverage: the old Today's four cards and Money's blocks are each one tap down, in the same facts."""
    why = CP.get(crypto, "why")
    assert any("below its 50-day average ($79,321)" in i["text"] for i in next(p for p in why["parts"] if p["t"] == "points")["items"])
    acct = CP.get(crypto, "account")
    text = json.dumps(acct, ensure_ascii=False)
    for fact in ("C$467.55", "Bitcoin, just held", "−9.2%", "Closed trades", "Day "):
        assert fact in text, fact
    receipt = next(r for p in acct["parts"] if p["t"] == "rows" and p.get("title") == "Closed trades" for r in p["rows"])["to"]["page"]
    kv = [r for p in receipt["parts"] if p["t"] == "kv" for r in p["rows"]]
    assert any(r["k"] == "Result" for r in kv) and any(r["k"] == "Why sold" for r in kv)
    mk = json.dumps(CP.get(crypto, "markets"), ensure_ascii=False)
    for fact in ("BAT", "MUBARAK", "Held back", "MEGA", "BMT", "118 coins checked"):
        assert fact in mk, fact
    act = json.dumps(CP.get(crypto, "activity"), ensure_ascii=False)
    for fact in ("Nightly note", "Sold Solana", "Sold Bitcoin", "Bought Bitcoin", "The screens as drawn"):
        assert fact in act, fact
    more = json.dumps(CP.get(crypto, "more"), ensure_ascii=False)
    for fact in ("Strategies", "Weekly exam", "Night test", "People", "The open list", "Repair board"):
        assert fact in more, fact


def test_the_open_list_answers_for_both_markets(crypto):
    n = CP.get(crypto, "needs", market="india")
    assert n["count"] == 2 and n["push"]["on"] is False and n["list_value"] == "2 need you"
    page = CP.get(crypto, "notices", market="india")
    assert K.problems("notices", page) == []


# ------------------------------------------------------------------------------------------------ the kit's own rules
def test_clip_keeps_whole_words_and_never_ends_on_a_small_word():
    assert K.clip("Small follow-ups to the reconstruction v2: the card", 8, 46) == "Small follow-ups to the reconstruction v2…"
    assert K.clip("No change", 8, 46) == "No change"
    assert not K.clip("The account is worth about C$446, down 12% since it started", 6, 40).endswith(("the…", "of…", "to…"))


def test_title_and_label_come_from_the_line():
    assert K.title_sub("Turn on phone notes: the Apple push key needs your Apple ID sign-in once.") == ("Turn on phone notes", "The Apple push key needs your Apple ID…")
    t, s = K.title_sub("Ananta cannot say when you last spoke with it. It should know the date.")
    assert t.startswith("Ananta cannot say") and s.startswith("It should know")


def test_problems_catches_what_breaks_a_rule():
    bad = K.surface("home", "crypto", [K.hero("a", "1"), K.hero("b", "2"),
                                       K.rows("Long", [K.row("one two three four five six seven", "a"), K.row("x"), K.row("y"), K.row("z")]),
                                       K.points(["one two three four five six seven eight nine ten eleven"]), {"t": "rows", "rows": [], "tone": "pink"}])
    got = " | ".join(K.problems("home", bad))
    for why in ("more than one hero number", "4 rows in one section", "a row's name is too long", "a point of more than ten words", "tone"):
        assert why in got, why
    assert K.problems("page", K.page("No button", [K.line("x")]))                       # rule 6: a page has one main button


def test_the_app_draws_every_part_the_server_sends():
    src = (APP / "src" / "place.tsx").read_text()
    for t in K.PART_TYPES:
        assert f'case "{t}"' in src, f"src/place.tsx does not draw {t}"


def test_one_look_the_owner_always_lands_on_the_places():
    look = (APP / "src" / "look.ts").read_text()
    assert 'newHome = "/new/home"' in look and 'let current: Look = "new"' in look
    assert TABS >= {"home", "markets", "ask", "activity", "more"} and not {"today", "money", "proof", "people"} & TABS
    assert "<SheetHost />" in (APP / "app" / "_layout.tsx").read_text()


def test_the_mark_and_the_icons_read_one_source():
    src = (APP / "src" / "logo.tsx").read_text()
    block = src[src.index("MARK2-START"):src.index("MARK2-END")]
    m = json.loads(block[block.index("{"):block.rindex("}") + 1])
    assert set(m["facets"]) == {"lo", "li", "ri", "ro", "bt", "bb"} and len(m["blades"]) == 3
    assert "mark2()" in (APP / "scripts" / "make_icons.py").read_text()
    assert not re.search(r"F2CF66", (APP / "src" / "place.tsx").read_text())                # the soft gold is gone from the redesign


def test_a_first_time_reader_answers_five_questions_from_the_top_of_home(crypto):
    """The plan's first-time-reader test: how much do I have, is it up or down, what did Ananta do today, does it need me, is everything
    running. Each is answered by the first four parts of Home, without a tap and without reading a sentence longer than thirteen words."""
    h = CP.get(crypto, "home")
    top = h["parts"][:4]
    hero = top[0]
    assert hero["t"] == "hero" and hero["value"].startswith("C$")                        # how much do I have
    assert hero["tone"] in ("good", "bad", None) and hero["change"]                      # up or down, with its sign
    assert top[1]["t"] == "today" and K.nwords(top[1]["line"]) <= 9                      # what Ananta did today
    assert h["bell"]["count"] == 2 and top[3]["title"] == "Needs you"                    # does it need me
    assert hero["status"]["words"] == "Running"                                          # is everything running
    assert all(K.nwords(s) <= 13 for s in K._texts(top))
