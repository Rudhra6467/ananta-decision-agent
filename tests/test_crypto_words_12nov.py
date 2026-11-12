"""12 Nov 2026, audit repair 5 (flag 121, stored 202): the crypto Ask and the crypto words (the keen outside audit's G-29, G-30, G-31,
G-32, G-34, G-41, G-47 and G-50). Each test failed on the code before the repair (4c4cc12) and passes after it. Display and Ask only:
nothing here trades, and no rule, threshold or pinned file changes. Counts only: no money of a measuring book before 15 Dec."""
import json

from jarvis import placekit as K
from jarvis.service import ask, briefs, officer
from jarvis.service import places as CP
from jarvis.service import surfaces as S
from tests.test_crypto_surfaces_10nov import CLOSED, NOW, _bars, _fake_today
from tests.test_places import crypto_setup
from tests.test_universe_live import J

DAY = 86400
MIDNIGHT_12NOV = 1794441600                       # Thu 12 Nov 2026, 00:00 UTC: the close of the 11 Nov candle (7 pm Toronto on Wed 11 Nov)


# ------------------------------------------------------------------------------------------------ G-29: one price for "today", one tap apart

def test_a_coins_page_leads_with_homes_own_live_figure_and_says_the_close_apart(monkeypatch, tmp_path):
    j = _fake_today(monkeypatch, tmp_path)
    monkeypatch.setattr(S, "coin_chart", lambda j, coin, n=120: {"chart": {"closes": [75368.0, 73796.0]}, "as_of": "10 Nov close",
                                                                  "words": "Bitcoin closed.", "note": "Daily closes."})
    live = {"coin": "BTC", "label": "Bitcoin", "value": "$74,358", "tone": "good", "sub": "+0.8% since 7 pm", "sub2": "Live · 12:30 pm"}
    monkeypatch.setattr(S, "_coin_pages", lambda j, dial, now, closes=None: [dict(live)])
    page = CP.coin_page(j, "BTC")
    hero = next(p for p in page["parts"] if p["t"] == "hero")
    assert (hero["value"], hero["change"], hero["tone"]) == ("$74,358", "+0.8%", "good")          # Home's box, one tap back
    assert hero["since"] == "since 7 pm · Live · 12:30 pm"
    assert {"t": "line", "text": "The 10 Nov close: $73,796, −2.1% on that day."} in page["parts"]  # the close, said apart
    # no live price: the last close leads, as before, and is not said twice
    monkeypatch.setattr(S, "_coin_pages", lambda j, dial, now, closes=None: [{"coin": "BTC", "value": "$73,796", "sub": "Tue 10 Nov close",
                                                                              "sub2": "no live price now"}])
    page = CP.coin_page(j, "BTC")
    hero = next(p for p in page["parts"] if p["t"] == "hero")
    assert hero["value"] == "$73,796" and hero["since"] == "at the 10 Nov close"
    assert not any(p["t"] == "line" and "close:" in p["text"] for p in page["parts"])


def test_a_crypto_day_chart_says_the_last_24_hours_and_india_keeps_its_session():
    from jarvis import chartkit
    bars = [[MIDNIGHT_12NOV + k * 3600, 100.0, 102.0, 99.0, 100.0 + k, 1.0] for k in range(24)]
    assert chartkit.shape("Bitcoin", "crypto", "1D", "1h", ["1D"], bars)["over"] == "over the last 24 hours"
    assert chartkit.shape("Nifty 50", "india", "1D", "5m", ["1D"], bars)["over"] == "over the day"
    assert chartkit.shape("Bitcoin", "crypto", "5D", "1h", ["5D"], bars)["over"] == "over 5 days"


# ------------------------------------------------------------------------------------------------ G-30 and G-31: two lookups the Ask lacked

def _night_j(tmp_path):
    from jarvis.service import brain, ndax_book, watch_engine
    now = MIDNIGHT_12NOV + 19 * 3600 + 46 * 60    # 14:46 Toronto on Thu 12 Nov
    j = J(tmp_path, now=now)
    j._explorer = lambda: None
    watch_engine._table(j)
    brain._table(j)
    ndax_book._table(j)
    rows = [("b1", "JARVIS_BOLD", "ZEC", MIDNIGHT_12NOV + 540, "OPEN")]                                         # the bold book's buy tonight
    rows += [(f"m{k}", "H07-UA" if k % 2 else "BRK", "SOL", MIDNIGHT_12NOV - 5 * DAY, "OPEN") for k in range(6)]  # measuring rows open for days
    rows += [("w1", "RBD", "ADA", MIDNIGHT_12NOV, "WAITING"), ("r1", "RANDOM_BOLD", "XRP", MIDNIGHT_12NOV + 540, "OPEN")]   # a twin is no book
    for i, w, c, t, st in rows:
        j.db.execute("INSERT INTO evidence_trades (id, watch, coin, source, signal_t, entry_t, status) VALUES (?,?,?,?,?,?,?)", (i, w, c, "test", t, t, st))
    j.db.commit()
    return j


def test_did_we_buy_anything_tonight_is_answered_from_every_book(monkeypatch, tmp_path):
    j = _night_j(tmp_path)
    monkeypatch.setattr(ask, "_book_status", lambda j: {"value_cad": 467.55, "cash_cad": 467.55, "positions": {}})
    nc = officer.night_counts(j)
    assert nc["bold_bought_tonight"] == ["ZEC"] and nc["evidence_rows_open"] == 8
    assert nc["open_by_book"] == {"JARVIS_BOLD": 1, "H07-UA": 3, "BRK": 3, "RBD": 1}
    out = ask.Lookups(j).call("books_tonight", {})
    acct = out["your_account"]
    assert acct["bought_tonight"] == [] and acct["sold_tonight"] == [] and acct["holds"] == [] and acct["value_cad"] == 467.55
    assert out["bold_book_bought_tonight"] == ["ZEC"] and out["measuring_books"]["open_in_all"] == 8    # never "nothing is open in any book"
    assert out["measuring_books"]["open_by_book"] == nc["open_by_book"]                                  # the nightly note's own counts
    assert out["tonight"].startswith("since the Wed 11 Nov daily close")
    assert "never say a book holds nothing unless its count here is 0" in out["say"]
    assert "net_usd" not in json.dumps(out)                                                             # counts only before 15 Dec
    assert "error" in ask.Lookups(j, guest=True).call("books_tonight", {})
    names = [t[0] for t in ask.TOOLS]
    assert "books_tonight" in names and "night_test" in names
    assert '"Did we buy anything tonight / is anything open / what happened tonight?" -> books_tonight' in ask.SYSTEM
    assert any("the Explorer's open trades only" in str(c) for c in ask.Lookups.t_overview.__code__.co_consts)


def test_what_did_the_night_test_say_reads_the_night_test(monkeypatch, tmp_path):
    from jarvis.service import nightcheck
    j = _night_j(tmp_path)
    res = {"market": "crypto", "day": "2026-11-12", "t": MIDNIGHT_12NOV + 1800, "asked": 12, "right": 10, "ungraded": 1, "not_asked": 0,
           "wrong": [{"id": "q4", "name": "the book's value", "question": "What is the book worth?", "why": "said C$439, the book is C$467.55"}],
           "look": [{"id": "q7", "name": "Bitcoin's price", "figures": ["$81,449"]}], "stopped_for_budget": False, "cost_usd": 0.04, "line": "10 of 12 right"}
    monkeypatch.setattr(nightcheck, "latest", lambda: dict(res))
    out = ask.Lookups(j).call("night_test", {})
    assert (out["evening"], out["asked"], out["right"], out["could_not_mark"], out["figures_worth_a_second_look"]) == ("Wed 11 Nov", 12, 10, 1, 1)
    assert out["the_figures"] == [{"question": "Bitcoin's price", "figures": ["$81,449"]}]     # P5-N9: the figures, not only how many
    assert out["wrong"] == [{"question": "What is the book worth?", "why": "said C$439, the book is C$467.55"}]
    assert "not the nightly trade review" in out["not_this"]
    assert '"What did the night test say?" -> night_test' in ask.SYSTEM
    monkeypatch.setattr(nightcheck, "latest", lambda: None)
    assert ask.Lookups(j).call("night_test", {})["ran"] is False
    assert "error" in ask.Lookups(j, guest=True).call("night_test", {})


# ------------------------------------------------------------------------------------------------ G-32: "my money" is the $500 account

def test_my_money_is_the_500_account_in_the_prompt_and_the_brief(monkeypatch, tmp_path):
    s = ask.SYSTEM
    assert "OUR BOOKS (say these names): THE $500 ACCOUNT (the book500 lookup, in CAD" in s
    assert '"how much is my paper money", "how are we doing overall", "my money"' in s
    assert "give ONE line for all books together first" not in s                           # the sentence that sent it to the measuring books
    assert "your own paper book (orders Madhav asked for" not in s and 'call it "the manual book"' in s
    assert "THE $500 ACCOUNT first, the brief's your_account" in s
    from jarvis.service import views
    from jarvis.service.manual import Manual
    monkeypatch.setattr(officer, "book_status", lambda j: {"value_cad": 467.55, "cash_cad": 467.55, "return_pct": -6.49, "positions": {}})
    monkeypatch.setattr(views, "trades_list", lambda j: {"value": 1700.0, "start": 2000.0, "unrealized": 0.0, "realized": -300.0, "open": [], "closed": [],
                                                         "pending": []})
    monkeypatch.setattr(views, "holdings", lambda j: {"mode": "AUTO", "value": 1790.0, "start": 2000.0, "return_pct": -10.5, "cash": 1790.0, "costs_paid": 4.0,
                                                      "holdings": [], "not_held": [], "pending": [], "shadow": {"return_pct": -10.0}, "btc_gate": False})
    monkeypatch.setattr(views, "evidence_forwarded", lambda j: {"in_use": []})
    monkeypatch.setattr(Manual, "state", lambda self, px: {"equity": 876.0, "return_pct": -12.4, "positions": []})
    monkeypatch.setattr(views, "markets", lambda j: {"coins": []})
    monkeypatch.setattr(views, "day_summary", lambda j: {"paper_value": 3490.0, "start_value": 4000.0, "today_change": -12.0})

    class JJ(J):
        def prices(self):
            return {}
    briefs.clear()
    b = briefs.portfolio_brief(JJ(tmp_path))
    briefs.clear()
    assert list(b)[1] == "your_account" and b["your_account"]["value_cad"] == 467.55 and "my paper money" in b["your_account"]["what"]
    assert "all_books" not in b and "my_paper_book" not in b
    assert "never his money" in b["measuring_books_together"]["what"] and "never his money" in b["explorer_book"]["what"]
    assert b["manual_book"]["value"] == 876.0 and "never 'your own paper book'" in b["manual_book"]["what"]


# ------------------------------------------------------------------------------------------------ G-34: the backup model never denies a record

def test_a_backup_answer_may_not_deny_a_record():
    deny = {"kind": "answer", "answer": "We haven't run a review 42 yet.", "breakdown": ["x"], "evidence": ["y"]}
    r = dict(deny)
    assert ask.backup_cannot_deny(r, "sonnet", "gemini") is True
    assert r["answer"] == ask.BACKUP_CANNOT_DENY and r["backup_withheld"] == "We haven't run a review 42 yet." and r["breakdown"] == []
    assert ask.backup_cannot_deny(dict(deny), "sonnet", "sonnet") is False                  # Claude itself may say what is not there
    assert ask.backup_cannot_deny(dict(deny), "gemini", "gemini") is False                  # an everyday answer was meant to be Gemini's
    assert ask.backup_cannot_deny({"kind": "answer", "answer": "Review 42 waits until 15 Dec."}, "sonnet", "gemini") is False
    for said in ("There is no such review.", "That study does not exist.", "I did not run review 42 yet", "No record of that trade."):
        assert ask.denies_a_record(said), said


def test_when_claude_fails_the_backups_denial_is_withheld_and_the_reason_kept():
    from tests.test_ask_ananta import _jarvis
    j, ex = _jarvis()

    def claude_down(*a, **k):
        raise TimeoutError("the call took too long")

    def gemini(s, h, u, t, log):
        return json.dumps({"answer": "We haven't run a review 42 yet.", "kind": "answer", "follow_ups": []}), {"in": 1, "out": 1}

    out = ask.Ask(j, providers={"sonnet": claude_down, "gemini": gemini}).ask("owner", "What did review 42 find about buying after drops?", mode="deep")
    assert out["answer"] == ask.BACKUP_CANNOT_DENY
    note = j.db.execute("SELECT note FROM ask_messages WHERE role='assistant' ORDER BY t DESC LIMIT 1").fetchone()[0]
    assert "Claude is unavailable right now (TimeoutError after" in note and "so Gemini answered" in note
    assert "the backup model's answer denied a record, so it was withheld" in note
    assert "the call took too long" not in note                                             # the failure's kind, never its text


# ------------------------------------------------------------------------------------------------ G-41: the dial's 50-day line is exponential

def test_the_dials_50_day_line_is_named_exponential_with_its_number(monkeypatch, tmp_path):
    pts = S._dial_points(CLOSED, {"BTC": 75368.41}, NOW)
    assert pts[1] == "That is 5.0% below its 50-day exponential average ($79,321), so buying is off"
    assert S._ema50("below its 50-day average (79,321)") == "below its 50-day exponential average (79,321)"
    j = _fake_today(monkeypatch, tmp_path)
    m = S.money(j)
    assert "below its 50-day exponential average (79,321)" in m["dial_block"]["why"]
    assert m["dial_block"]["rule"] == "Buying is allowed only while Bitcoin closes above both its 50-day exponential and 200-day averages."
    assert m["plan"]["brief"].endswith("until Bitcoin closes above both its 50-day exponential and 200-day averages.")
    assert "50-day exponential average and its 200-day average, review #25" in ask.SYSTEM
    from jarvis.service import discipline
    assert "50-day exponential average" in discipline.STATE_WORDS["FRAGILE"]
    monkeypatch.setattr("jarvis.service.feed.daily", lambda j, coin: _bars())
    words = S.chart(None, "btc")["words"]
    assert "its 50-day exponential average ($" in words and "its 50-day average" not in words


def test_the_dials_page_draws_and_says_the_exponential_line(monkeypatch):
    j = crypto_setup(monkeypatch)
    w = CP.why(j)
    assert {"label": "50-day exponential", "style": "dash"} in next(p for p in w["parts"] if p["t"] == "chart")["legend"]
    assert {"t": "line", "text": "Bitcoin closed under its 50-day exponential average, so cash is the position."} in w["parts"]
    mk = CP.markets(j)
    assert "under its 50-day exponential average" in json.dumps(mk, ensure_ascii=False) and not K.problems("markets", mk)


# ------------------------------------------------------------------------------------------------ G-47: "eaten by costs" said what it counts

def test_the_costs_check_says_moved_less_than_its_costs_and_splits_it(tmp_path):
    from jarvis.service import discipline, reviews
    j = J(tmp_path, now=MIDNIGHT_12NOV + 60000)
    reviews._table(j)
    tagged = [(100.0, 100.3, -0.3), (100.0, 99.8, -0.8), (100.0, 100.9, 0.2), (100.0, 99.9, -0.7)]   # turned, lost, still made money, lost
    rows = [(f"c{k}", e, x, n, ["COSTS_ATE"]) for k, (e, x, n) in enumerate(tagged)] + [(f"o{k}", 100.0, 97.0, -3.6, ["NEVER_WORKED"]) for k in range(8)]
    for i, e, x, n, tags in rows:
        j.db.execute("INSERT INTO trade_reviews (id, t, book, watch, coin, entry, exit, net_usd, tags) VALUES (?,?,?,?,?,?,?,?,?)",
                     (i, j.now() - DAY, "Explorer", "E1", "SOL", e, x, n, json.dumps(tags)))
    j.db.commit()
    c = next(x for x in discipline.officer_checks(j) if x["id"] == "explorer_costs")
    assert c["words"] == ("4 of 12 Explorer trades in 30 days moved less than their costs, up or down: 1 made money before costs and lost after, "
                          "2 had lost before any cost, 1 still made money")
    assert c["state"] == "OK" and c["split"] == {"moved_less_than_costs": 4, "gain_turned_to_loss": 1, "lost_before_costs": 2, "still_made_money": 1}
    assert reviews.TAG_WORDS["COSTS_ATE"] == "moved less than its costs" and "eaten by costs" not in json.dumps(c)
    assert 'never "eaten by costs"' in officer.NOTE_RULES and "an explorer eaten by costs" not in officer.NOTE_RULES


# ------------------------------------------------------------------------------------------------ G-50: Proof and More promise no more than they check

def test_proof_has_no_old_gate_and_says_what_its_counts_are(monkeypatch, tmp_path):
    from jarvis.service import missed, reconstruct
    j = _fake_today(monkeypatch, tmp_path)
    monkeypatch.setattr(missed, "recent", lambda j, days: {"counts": {"CAUGHT": 9, "SEEN": 20, "MISSED": 0, "CAUGHT_TRADE_OK": 0}, "moves": []})
    monkeypatch.setattr(reconstruct, "latest", lambda j: {"day": "2026-11-11", "findings": [], "market": {"dial_words": "Closed"}})
    p = S.proof(j)
    assert p["clocks"][0]["name"] == "The evidence window (Rule A and B)" and not any("Round trips" in c["name"] for c in p["clocks"])
    assert "round trips" not in p["clocks_ask"] and "graduation" not in p["clocks_ask"]
    assert (p["missed"]["big"], p["missed"]["held"], p["missed"]["seen"], p["missed"]["missed"]) == (29, 9, 20, 0)
    assert p["last_night"]["day"] == "2026-11-11" and {"label": "The nightly evidence", "route": "/reconstruction"} in p["links"]
    pts = p["studies"]["explain"]["points"]
    assert any(x.startswith("The one rule that passed its research test on history is the short dip trade; that is not yet a live result.") for x in pts)
    assert not any("measured edge" in x for x in pts) and "measured edge" not in S.STRAT_Q


def test_more_and_proof_say_noticed_and_when_the_evidence_was_updated(monkeypatch):
    j = crypto_setup(monkeypatch)
    base = S.proof(j)
    p = {**base, "missed": {"words": "In 7 days ...", "big": 29, "held": 9, "seen": 20, "missed": 0},
         "last_night": {"words": "Found nothing new.", "day": "2026-11-11"},
         "clocks": base["clocks"] + [{"name": "Clean nights in a row (book, note and candle agree)", "done": 1, "need": 30,
                                      "finish_words": "29 more to go; counted from 11 Nov"}]}
    monkeypatch.setattr(S, "proof", lambda j: p)
    more = CP.more(j)
    tiles = {t["label"]: t["value"] for part in more["parts"] if part.get("t") == "tiles" for t in part["items"]}
    assert tiles["Big moves"] == "29 of 29 noticed" and tiles["The evidence"] == "Updated 11 Nov" and "Missed" not in tiles
    assert "Live" not in tiles.values() and not K.problems("more", more)
    pr = CP.proof(j)
    row = next(r for part in pr["parts"] if part.get("t") == "rows" for r in part.get("rows") or [] if r.get("title") == "Big moves, 7 days")
    assert (row["sub"], row["right"]) == ("9 held by paper books, 20 only seen", "0 missed")
    bars = next(part for part in pr["parts"] if part.get("t") == "bars")["items"]
    assert [b["name"] for b in bars] == ["Evidence window", "Nights book, note, candle agree"] and not K.problems("proof", pr)
    monkeypatch.setattr(S, "proof", lambda j: {**p, "last_night": None})
    tiles = {t["label"]: t["value"] for part in CP.more(j)["parts"] if part.get("t") == "tiles" for t in part["items"]}
    assert tiles["The evidence"] == "Not run yet"


def test_india_no_longer_says_the_sealed_years_were_never_looked_at():
    from jarvis.india import surfaces as IS
    pts = IS.studies_explain({"research": {"versions_tested": 1440, "verdicts": {"VALIDATED": 3}}, "indicator_knowledge": {}})["points"]
    assert pts[1] == ("1440 versions were tested on 2000-2017 and then checked on 2018-2023, never on 2024 onward. The years from 2024 are kept "
                      "sealed from research; they were opened on 20 Oct 2026 for another study, the index options line.")
    assert not any("never looked at" in x for x in pts)


# ------------------------------------------------------------------------------------------------ repair 5's outside check (P5-N1 to N9)

def _notes(j, *rows):
    officer._table(j)
    for day, t in rows:
        j.db.execute("INSERT INTO officer_notes (day, t, note, facts, cost_usd) VALUES (?,?,?,?,?)", (day, t, "a note", "{}", 0.0))
    j.db.commit()


def test_tonight_starts_at_the_close_never_at_the_note_before_last(monkeypatch, tmp_path):
    # P5-N1: once tonight's note was written, "tonight" reached back to the note before it (about 42 hours at 1 pm), so a daytime buy of
    # the day before was called tonight's
    j = _night_j(tmp_path)
    _notes(j, ("2026-11-11", MIDNIGHT_12NOV - DAY + 352), ("2026-11-12", MIDNIGHT_12NOV + 360))
    j.db.execute("INSERT INTO evidence_trades (id, watch, coin, source, signal_t, entry_t, status) VALUES (?,?,?,?,?,?,?)",
                 ("b0", "JARVIS_BOLD", "SOL", "test", MIDNIGHT_12NOV - 6 * 3600, MIDNIGHT_12NOV - 6 * 3600, "OPEN"))  # 1 pm Wed, before the close
    j.db.commit()
    monkeypatch.setattr(ask, "_book_status", lambda j: {"value_cad": 467.55, "cash_cad": 467.55, "positions": {}})
    assert officer.night_window(j)[2] == MIDNIGHT_12NOV - DAY + 352           # the note's own night still runs from the note before it
    out = ask.Lookups(j).call("books_tonight", {})
    assert out["bold_book_bought_tonight"] == ["ZEC"]                          # the 7:09 pm buy; never Wednesday's 1 pm one
    assert out["tonight"].startswith("since the Wed 11 Nov daily close (7 pm Toronto)")


def test_the_random_twins_are_counted_apart_open_and_closed(monkeypatch, tmp_path):
    # P5-N7: the closes under "measuring books" took in the random twins' closes while the open count left the twins out
    j = _night_j(tmp_path)
    shut = MIDNIGHT_12NOV - DAY                                                 # stamped with the 11 Nov candle's open: tonight's closes
    for i, w, c in (("r2", "RANDOM_BOLD", "DOGE"), ("r3", "JARVIS_RANDOM", "LINK"), ("c1", "H07-UA", "ADA")):
        j.db.execute("INSERT INTO evidence_trades (id, watch, coin, source, signal_t, entry_t, exit_t, status, net_usd) VALUES (?,?,?,?,?,?,?,?,?)",
                     (i, w, c, "test", shut - 3 * DAY, shut - 3 * DAY, shut, "CLOSED", 1.0))
    j.db.execute("INSERT INTO evidence_trades (id, watch, coin, source, signal_t, entry_t, status) VALUES (?,?,?,?,?,?,?)",
                 ("r4", "JARVIS_RANDOM", "AVAX", "test", MIDNIGHT_12NOV + 600, MIDNIGHT_12NOV + 600, "OPEN"))
    j.db.commit()
    monkeypatch.setattr(ask, "_book_status", lambda j: {"value_cad": 467.55, "cash_cad": 467.55, "positions": {}})
    out = ask.Lookups(j).call("books_tonight", {})
    mb, tw = out["measuring_books"], out["random_twins"]
    assert mb["closed_tonight_by_rule"] == {"H07-UA": {"n": 1}}                # a book's close, a count; no twin, no money before 15 Dec
    assert (tw["open"], tw["closed_tonight"]) == (2, 2) and "never a book" in tw["what"]
    assert "JARVIS_RANDOM" not in mb["open_by_book"] and mb["open_in_all"] == 8
    nc = officer.night_counts(j)
    assert nc["twins_open"] == 2 and nc["evidence_rows_open"] == 8 and "JARVIS_RANDOM" not in nc["open_by_book"]


def test_the_backup_guard_reads_curly_apostrophes_and_lets_everyday_answers_through():
    # P5-N2 and N3: the outside check's own sentences (planned Claude Sonnet, answered by Gemini)
    withheld = ["We haven’t run a review 42 yet.", "We’ve never run review 42.", "I couldn't find review 42 in our records.",
                "I don't see any review 42 on file.", "Review 42 was never run.", "There is no review 42.", "That isn't in our records."]
    passes = ["We haven't made any trades today: the dial is closed.", "There were no trades tonight; the dial is closed.",
              "There are no trades open in the account.", "We haven't opened any new positions since 4 Nov.", "We have not held Bitcoin since 28 Oct.",
              "The night test has not run yet tonight; it runs after the close.", "There is no note for tonight yet; it comes after the close.",
              "We haven't recorded enough closed trades yet to judge the bold book.", "We did not trade today.",
              "Not yet: the forward record of review 42 is held until 15 Dec.", "Nothing is open in any book.",
              "There is no result in review 42 yet; it is held until 15 Dec."]
    for said in withheld:
        r = {"kind": "answer", "answer": said}
        assert ask.backup_cannot_deny(r, "sonnet", "gemini") is True and r["answer"] == ask.BACKUP_CANNOT_DENY, said
    for said in passes:
        r = {"kind": "answer", "answer": said}
        assert ask.backup_cannot_deny(r, "sonnet", "gemini") is False and r["answer"] == said, said
    # the budget path: Claude is out until midnight, so "ask me again in a minute" would not be true
    r = {"kind": "answer", "answer": "We haven't run a review 42 yet."}
    assert ask.backup_cannot_deny(r, "sonnet", "gemini", "Claude budget for today ($2.00) is used up, so Gemini answered") is True
    assert r["answer"] == ask.BACKUP_CANNOT_DENY_BUDGET and "until midnight Toronto time" in r["answer"] and "in a minute" not in r["answer"]


def test_over_budget_the_withheld_answer_says_after_midnight(monkeypatch):
    from tests.test_ask_ananta import _jarvis
    j, ex = _jarvis()

    def gemini(s, h, u, t, log):
        return json.dumps({"answer": "We haven’t run a review 42 yet.", "kind": "answer", "follow_ups": []}), {"in": 1, "out": 1}

    a = ask.Ask(j, providers={"sonnet": lambda *x, **k: (_ for _ in ()).throw(AssertionError("over budget: never called")), "gemini": gemini})
    j.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", ("daily_budget_usd", "0"))
    j.db.commit()
    out = a.ask("owner", "What did review 42 find about buying after drops?", mode="deep")
    assert out["answer"] == ask.BACKUP_CANNOT_DENY_BUDGET
    note = j.db.execute("SELECT note FROM ask_messages WHERE role='assistant' ORDER BY t DESC LIMIT 1").fetchone()[0]
    assert "is used up, so Gemini answered" in note and "the backup model's answer denied a record, so it was withheld" in note


def test_the_note_the_eye_the_lookups_and_the_chain_name_the_exponential_line(monkeypatch, tmp_path):
    # P5-N4: the dial's raw words ("below its 50-day average (79,104)") reached the nightly note's facts, the Ask's exposure lookup and the
    # mission view; the eye's phone note and the decision chain's market gate wrote the same line as "its 50-day average"
    import inspect

    from jarvis.service import chain, ev, exposure, eye, market_shift, universe_watch, views
    d = {"dial_words": "Closed", "why": ["Bitcoin is below its 50-day average (79,104)", "and below its 200-day average (95,000)"]}
    assert officer.dial_why(d) == ["Bitcoin is below its 50-day exponential average (79,104)", "and below its 200-day average (95,000)"]
    assert d["why"][0] == "Bitcoin is below its 50-day average (79,104)"            # the pinned dial's own words are untouched
    assert 'never just "its 50-day average"' in officer.NOTE_RULES
    assert '"why": dial_why(d)' in inspect.getsource(officer.facts)                 # the note's facts carry the named line
    seen = []
    monkeypatch.setattr(eye, "_cool_ok", lambda key, cool, now: True)
    monkeypatch.setattr(eye, "_event", lambda j, kind, coin, p, title, body, push, extra: seen.append(title) or {"id": "e1"})
    j = J(tmp_path, now=MIDNIGHT_12NOV + 3600)
    market_shift.live(j, {"BTC": 70000.0}, {"btc_ema50": 79000.0, "regime": "ALLOWED"})
    market_shift.live(j, {"BTC": 90000.0}, {"btc_ema50": 79000.0, "regime": "RISK_OFF"})
    assert seen == ["Bitcoin is under its 50-day exponential average", "Bitcoin is back above its 50-day exponential average"]
    src = inspect.getsource(market_shift.close)                                     # the close's phone note, said on a regime change
    assert "closed under its 50-day exponential average" in src and "closed above its 50-day exponential average" in src
    assert "its 50-day exponential average ({_pct(bc, be50)" in inspect.getsource(chain)
    monkeypatch.setattr(exposure, "state", lambda j: d)
    monkeypatch.setattr(exposure, "books", lambda j: {})
    monkeypatch.setattr(ev, "table", lambda: [])
    monkeypatch.setattr(ev, "fidelity", lambda j: {})
    monkeypatch.setattr(universe_watch, "would_be", lambda j: {})
    monkeypatch.setattr("jarvis.service.app._main", lambda: j)                     # never the service's own book
    out = ask.Lookups(j).call("exposure", {})
    assert out["dial"]["why"][0] == "Bitcoin is below its 50-day exponential average (79,104)" and out["dial"]["dial_words"] == "Closed"
    assert d["why"][0] == "Bitcoin is below its 50-day average (79,104)"            # a copy: the dial's cache is never changed
    monkeypatch.setattr(officer, "book_status", lambda j: {"value_cad": 467.55, "cash_cad": 467.55, "positions": {}})
    monkeypatch.setattr(officer, "latest", lambda j, n=1: [])
    acct = views.mission(j)["account"]
    assert acct["dial"]["why"][0] == "Bitcoin is below its 50-day exponential average (79,104)"
    assert acct["next"] == "the next decision comes at the daily close (7 pm Toronto)"


def test_the_daily_close_is_7_pm_in_winter_and_8_pm_in_summer(monkeypatch, tmp_path):
    from jarvis.service import reads_watch, setups
    assert officer.close_clock(MIDNIGHT_12NOV + 5 * 3600) == "7 pm"
    assert officer.close_clock(1782864000 + 3600) == "8 pm"                          # 1 Jul 2026: its close was 8 pm on 30 Jun, Toronto
    j = J(tmp_path, now=MIDNIGHT_12NOV + 5 * 3600)
    assert reads_watch._close_clock(j) == "7 pm"
    monkeypatch.setattr(setups, "latest", lambda j: None)
    assert ask.Lookups(j).call("setups_board", {})["board"] == "no board yet: the first scan runs after the next daily close (7 pm Toronto)"


def test_my_book_opens_the_account_and_the_manual_book_is_called_so():
    # P5-N6: "my book" and "my paper book" moved the screen to the manual book; the tour and the weekly summary called it "your own paper book"
    import inspect

    from jarvis.service import appmap, week
    assert appmap.guess("How is my book doing?") == "home" and appmap.guess("show me my paper book") == "home"
    assert appmap.guess("what is in the manual book?") == "portfolio:mine"
    tour = inspect.getsource(appmap.tour)
    assert "your own paper book" not in tour and "And this is the manual book." in tour
    src = inspect.getsource(week.week)
    assert "Your own paper book" not in src and '"The manual book (orders you asked for by hand)"' in src


def test_the_evidence_card_is_named_by_the_evening_it_was_made(monkeypatch, tmp_path):
    # P5-N8: the card made at 00:40 UTC on 12 Nov (7:40 pm Toronto on Wed 11 Nov) read "Updated 12 Nov" on More
    from jarvis.service import missed, reconstruct
    j = _fake_today(monkeypatch, tmp_path)
    monkeypatch.setattr(missed, "recent", lambda j, days: {"counts": {"CAUGHT": 9, "SEEN": 20, "MISSED": 0, "CAUGHT_TRADE_OK": 0}, "moves": []})
    card = {"day": "2026-11-12", "t": MIDNIGHT_12NOV + 2400, "about_day": "2026-11-11", "findings": [], "market": {"dial_words": "Closed"}}
    monkeypatch.setattr(reconstruct, "latest", lambda j: dict(card))
    p = S.proof(j)
    assert p["last_night"]["evening"] == "Wed 11 Nov" and p["last_night"]["words"].startswith("Wed 11 Nov: Closed.")
    out = ask.Lookups(j).call("discipline", {"part": "reconstruction"})
    assert out["reconstruction_last_night"]["made_on_the_evening_of"] == "Wed 11 Nov"
    j2 = crypto_setup(monkeypatch)
    monkeypatch.setattr(S, "proof", lambda j: p)
    more = CP.more(j2)
    tiles = {t["label"]: t["value"] for part in more["parts"] if part.get("t") == "tiles" for t in part["items"]}
    assert tiles["The evidence"] == "Updated Wed 11 Nov" and not K.problems("more", more)
