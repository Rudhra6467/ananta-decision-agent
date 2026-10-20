"""Say = show (request #73, Oct 20): the screen an answer opens is the book the voice talks about.
The fixtures are real voice turns (question heard, words spoken, screen moves) from Oct 2-20 that the checker caught."""
import json
import sqlite3

import pytest

from jarvis.service import appmap as am
from jarvis.service import sayshow


@pytest.fixture(autouse=True)
def _no_local_voice(monkeypatch):
    monkeypatch.setenv("ANANTA_VOICE_LOCAL", "0")     # tests never call the Mac's voice server
    monkeypatch.setenv("ASK_LOCAL", "0")              # ... or the Mac's model server


def go(t: str) -> dict:
    return {"do": "go_to", "target": t, "label": am.SCREENS[t]["name"]}


BACK = {"do": "back", "label": "Back"}

# Oct 20 07:36 and 07:37 Toronto: Madhav asked about the $500 book; the voice talked about it; the screen opened the T3 portfolio
Q0736 = "Yeah, what happened? Like, what's up with our current positions like that $500 we are holding? It shows $11 less. Any bad trades, good trades? What's up with that?"
S0736 = ("Morning, sir. The $500 book is down about 11 dollars, roughly two percent, and that's all unrealized: no trades have closed. "
         "We hold Bitcoin and Ethereum from Oct 11, and both have slipped since. The market gate is still open and no brake has fired.")
Q0737 = ("I don't know, is it worth holding those trades or like at what position we have taken and why have we taken those trades and is "
         "it worth holding or like changing the positions?")
S0737 = ("I'd hold both, sir. We bought Bitcoin and Ethereum on October 11 because the market gate was open, and the rules put up to 60 "
         "percent of the book in them while it is. They're down a few percent and about 40 percent is still cash. No stop or brake has fired.")
# Oct 2: the cockpit opened while the voice talked about the Explorer and T3
Q1002 = "Ananta, what's the current state of the system right now? Which strategies are enabled, what's the regime, and how many open positions are there?"
S1002 = ("Good afternoon, Madhav. Everything is running smoothly across our three main systems. The Explorer, the T3 portfolio, and the hourly "
         "watch are all active, with the T3 portfolio currently in automatic mode. We have 21 open positions in total across our different books.")
# Oct 11: evidence:forwarded opened while it talked about the Explorer's trades
Q1011a = "Okay. How like in the past history, how many good trades we have taken and how many number of bad trades we have taken in the last seven days history."
S1011a = ("Mostly bad, sir. These are totals since late September, because I don't have a clean seven-day split. In the Explorer, about 35 of "
          "roughly 520 closed trades won, so more than nine in ten lost. Random entries did about as badly, so nothing has beaten random yet.")
# Oct 11: the Explorer opened while it talked about the trend portfolio review (evidence)
Q1011b = "Question three. What's the history behind that rule? Did it come from a backtest, a study, or a lesson from a past drawdown?"
S1011b = ("It came from a backtest, sir, not a single drawdown lesson. In the trend portfolio review, the Bitcoin 50-day gate cut drawdowns in "
          "both history periods, and in the Luna crash it kept us at zero against a loss of about 56 percent.")
# Oct 11: the T3 portfolio opened while it talked about evidence and the $500 account
Q1011c = "Question nine. What's the biggest open dependency blocking the next step?"
S1011c = ("The biggest blocker, sir, is the missing live promotion rule, request 27. Without a written trade count, gain and loss limit that "
          "you approve, paper evidence can't turn into the five hundred dollar account. Did you mean the data feeds?")
# Matched ones that must stay as they are
Q1002b = "How is our portfolio doing today?"
S1002b = "Good afternoon, Madhav. Our T3 portfolio is down about two point six percent since we started it. Today has been rough."
Q1002c = "have the thing to empty it."
S1002c = ("I hear you, Madhav. You're asking if I have a way to empty the portfolio. I cannot sell everything for you, but you have a kill "
          "switch in the Cockpit that can stop the autopilot and close positions.")


def test_new_aliases_send_the_500_book_home():
    assert am.guess(Q0736) == "home"
    for q in ("how is the NDAX account", "what's in the 500 book", "the five hundred we put in", "what we are holding", "our account"):
        assert am.guess(q) == "home", q
    assert am.guess("show me the trend portfolio") == "portfolio" and am.guess("how is T3") == "portfolio"
    assert am.guess("How is our portfolio doing today?") == "portfolio"           # plain "portfolio" still means T3 when nothing else is said
    assert am.resolve(None, "$500") == ("home", "Home") and am.resolve(None, "trend portfolio")[0] == "portfolio"
    assert am.quick_command(None, "show me the 500 book")["ui"][0]["target"] == "home"
    assert am.quick_command(None, "open the account")["ui"][0]["target"] == "home"
    assert "$500" in am.SCREENS["portfolio"]["shows"]                             # the model's map says where the $500 lives


def test_books_named_reads_what_was_said():
    assert am.books_named(S0736) == ["home"]                                      # the market gate and brakes name no book
    assert am.books_named(S1002) == ["portfolio:explorer", "portfolio"]
    assert am.books_named(S0737) == []
    assert am.books_named("Here is my own book, and your paper book is flat.") == ["jarvis", "portfolio:mine"]


def test_the_0736_flash_to_t3_and_back_is_dropped():
    ui, pts, note = am.say_show(None, S0736, [go("portfolio"), BACK], [], Q0736)
    assert ui == [] and pts == [] and note == "dropped portfolio+back"


def test_the_0736_words_move_the_screen_to_the_500_book():
    ui, pts, note = am.say_show(None, S0736, [go("portfolio")], [{"spot": "portfolio.value", "sentence": 1}], Q0736)
    assert ui == [go("home")] and note == "retargeted portfolio->home"
    assert pts == [{"spot": "home.value", "sentence": 1}]                      # the $500 card glows on "The $500 book is down..."
    ui, pts, note = am.say_show(None, S0736, [go("portfolio")], [], Q0736, here={"screen": "home"})
    assert ui == [] and pts == [{"spot": "home.value", "sentence": 1}] and note.endswith("(already open)")


def test_the_other_mismatches_from_the_checker():
    assert am.say_show(None, S0737, [go("portfolio")], [], Q0737) == ([], [], "dropped portfolio")          # names no book
    ui, pts, note = am.say_show(None, S1002, [go("cockpit")], [{"spot": "cockpit.controls", "sentence": 1}], Q1002)
    assert ui == [] and pts == [] and note == "dropped cockpit"                                         # two books named, none asked
    ui, pts, note = am.say_show(None, S1011a, [go("evidence:forwarded")], [], Q1011a)
    assert ui == [go("portfolio:explorer")] and pts == [{"spot": "explorer.value", "sentence": 2}]
    assert note == "retargeted evidence:forwarded->portfolio:explorer"
    assert am.say_show(None, S1011b, [go("portfolio:explorer")], [], Q1011b)[0] == []                   # the review: evidence and T3
    assert am.say_show(None, S1011c, [go("portfolio")], [{"spot": "portfolio.value", "sentence": 0}], Q1011c)[:2] == ([], [])


def test_moves_that_match_the_words_are_kept():
    pts = [{"spot": "portfolio.value", "sentence": 1}]
    assert am.say_show(None, S1002b, [go("portfolio")], pts, Q1002b) == ([go("portfolio")], pts, "kept portfolio")
    assert am.say_show(None, S1002c, [go("cockpit")], [], Q1002c)[0] == [go("cockpit")]
    assert am.say_show(None, "Here's the evidence screen, Madhav.", [go("evidence:forwarded")], [], "and the repairs?")[2] == "kept evidence:forwarded"


def test_what_he_asked_to_see_wins_unless_the_word_was_vague():
    said = "The trend portfolio is up two percent today."
    assert am.say_show(None, said, [go("portfolio:explorer")], [], "Show me the Explorer")[2] == "kept portfolio:explorer (asked)"
    # "portfolio" is vague (Madhav says it for the $500 account too): the spoken words decide
    assert am.say_show(None, S0736, [go("portfolio")], [], "show me the portfolio")[0] == [go("home")]
    assert am.say_show(None, "It is down a little today.", [go("portfolio")], [], "show me the portfolio")[2] == "kept portfolio (asked)"
    # "our open trades" is not a request to open anything
    assert am.say_show(None, "Quiet markets would not worry me.", [go("portfolio:explorer")], [], "what about these open trades?")[0] == []


def test_coin_trade_and_other_pages_are_never_touched():
    coin = {"do": "open", "target": "coin:BTC", "label": "BTC coin page"}
    assert am.say_show(None, "The Explorer bought Bitcoin.", [coin], [{"spot": "coin.chart", "sentence": 0}], "how is bitcoin")[:2] == \
        ([coin], [{"spot": "coin.chart", "sentence": 0}])
    tab = go("ananta")
    assert am.say_show(None, "Taking you to the Ananta tab now.", [tab], [], "No, let's go back to the Ananda tap.") == ([tab], [], "")
    scroll = {"do": "scroll", "dir": "down", "label": "Scroll down"}
    assert am.say_show(None, "Here is more.", [scroll], [], "what's below this?") == ([scroll], [], "")


def test_a_back_he_asked_for_stays():
    ui, _, note = am.say_show(None, "Here's the trend portfolio. Going back now.", [go("portfolio"), BACK], [],
                              "Show me the trend portfolio, then take me back.")
    assert ui == [go("portfolio"), BACK] and note == "kept portfolio"


def test_ask_moves_to_the_book_the_voice_names_and_stores_the_note(monkeypatch):
    from jarvis.service import ask, speech
    from tests.test_ask_ananta import _jarvis

    monkeypatch.setattr(speech, "prepare_answer", lambda s, v, sp, make=None: "vid")
    j, ex = _jarvis()

    def fake(s, h, u, L, log):                       # the model opens "portfolio" while it talks about the $500 book
        L.call("ui_go", {"target": "portfolio"})
        return json.dumps({"kind": "answer", "answer": S0736}), {"in": 1, "out": 1}
    A = ask.Ask(j, providers={"gemini": fake})
    r = A.ask("o@x.com", Q0736, mode="everyday", voice=True, context={"here": {"screen": "ananta"}})
    assert r["ui"] == [go("home")] and r["points"] == [{"spot": "home.value", "sentence": 1}]
    assert r["say_show"] == "retargeted portfolio->home"
    stored = json.loads(j.db.execute("SELECT reply FROM ask_messages WHERE id=?", (r["id"],)).fetchone()[0])
    assert stored["say_show"] == "retargeted portfolio->home" and stored["ui"] == r["ui"]

    def claims(s, h, u, L, log):                     # a dropped move the answer still claims is said plainly
        L.call("ui_go", {"target": "cockpit"})
        return json.dumps({"kind": "answer", "answer": "I've opened it for you. " + S1002}), {"in": 1, "out": 1}
    A.providers["gemini"] = claims
    r = A.ask("o@x.com", Q1002, mode="everyday", voice=True, context={"here": {"screen": "ananta"}})
    assert r["ui"] == [] and r["say_show"] == "dropped cockpit" and "couldn't move the screen" in r["answer"]


def test_app_reports_land_in_voice_ui_and_the_summary_counts_them():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE ask_messages (id TEXT, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT)")
    for aid, t, rep in [("a1", 1000, {"ui": [go("home")], "say_show": "retargeted portfolio->home"}),
                        ("a2", 1100, {"ui": [], "say_show": "dropped portfolio+back; dropped cockpit"}),
                        ("a3", 1200, {"ui": [go("portfolio:explorer")], "say_show": "kept portfolio:explorer"}),
                        ("a4", 1300, {"ui": []})]:
        db.execute("INSERT INTO ask_messages VALUES (?,?,?,?,?,?)", (aid, "th", t, "assistant", None, json.dumps(rep)))
    assert sayshow.record(db, "a1", [{"target": "home", "ok": True, "landed": "Home"}], ["home.value"], 1001)
    sayshow.record(db, "a3", [{"target": "portfolio:explorer", "ok": False, "landed": "Ask Ananta"}], [], 1201)
    aid, ui, res, note = db.execute("SELECT answer_id, ui_json, results_json, say_show FROM voice_ui ORDER BY t").fetchone()
    assert aid == "a1" and json.loads(ui) == [go("home")] and note == "retargeted portfolio->home"
    assert json.loads(res) == {"results": [{"target": "home", "ok": True, "landed": "Home"}], "spots": ["home.value"]}
    s = sayshow.summary(db, now=2000, days=7)
    assert (s["answers"], s["kept"], s["retargeted"], s["dropped"], s["reported"], s["failed"]) == (3, 1, 1, 2, 2, 1)
    assert "1 moved to the book the voice named" in s["line"]
    assert sayshow.summary(db, now=1000 + 30 * 86400, days=7)["answers"] == 0
    with pytest.raises(ValueError):
        sayshow.record(db, "../x", [], [], 1)


def test_ui_result_route_is_owner_only(monkeypatch):
    from tests.test_routes_accept_app_bodies import _client

    c, h = _client(monkeypatch)
    body = {"answer_id": "abc123", "results": [{"target": "home", "ok": True, "landed": "Home"}], "spots": ["home.value"]}
    assert c.post("/v3/voice/ui_result", json=body).status_code == 401
    r = c.post("/v3/voice/ui_result", json=body, headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True}
    assert c.post("/v3/voice/ui_result", json={**body, "answer_id": "../x"}, headers=h).status_code == 400


def test_checker_before_and_after_on_the_logged_cases():
    turns = [{"t": "2026-10-20T07:36:58", "mode": "voice:auto", "heard": Q0736, "answer": S0736, "ui": [go("portfolio"), BACK]},
             {"t": "2026-10-20T07:37:47", "mode": "voice:auto", "heard": Q0737, "answer": S0737, "ui": [go("portfolio")]},
             {"t": "2026-10-02T13:30:58", "mode": "voice:everyday", "heard": Q1002, "answer": S1002, "ui": [go("cockpit")]},
             {"t": "2026-10-11T14:20:33", "mode": "voice:auto", "heard": Q1011a, "answer": S1011a, "ui": [go("evidence:forwarded")]},
             {"t": "2026-10-11T04:08:18", "mode": "voice:auto", "heard": Q1011b, "answer": S1011b, "ui": [go("portfolio:explorer")]},
             {"t": "2026-10-02T15:27:37", "mode": "voice:auto", "heard": Q1002b, "answer": S1002b, "ui": [go("portfolio")]},
             {"t": "2026-10-02T16:41:39", "mode": "voice:nav", "rmode": "nav", "heard": "Open Ethereum", "answer": "Sure. Opening ETH.",
              "ui": [{"do": "open", "target": "coin:ETH"}]},
             {"t": "2026-10-02T16:41:41", "mode": "voice:nav", "rmode": "nav", "heard": "Go back.", "answer": "Sure, going back.", "ui": [BACK]}]
    r = sayshow.check(turns)
    assert r["moved"] == 8
    assert r["before"] == {"matched": 2, "mismatch": 5, "unclear": 0}
    assert r["after"] == {"matched": 3, "mismatch": 0, "unclear": 0, "dropped": 4}
