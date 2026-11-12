"""12 Nov 2026 (the keen outside audit, G-34; repair 5's second confirm check, D1 to D7). When the free backup model answers in Claude's
place it cannot look up our records. A question about a record gets no backup answer at all; in an answer to any other question, a
sentence that says a record has not happened (or not yet), or does not exist, is withheld. What a record found passes."""
import json

from jarvis.service import appmap, ask

# the second confirm check's own sentences (recheck/pkg5_confirm2_probe.py), then two sets written before they were first run
DENIALS = [
    "We ran no review 42.", "We did not run review 42.", "The research team never ran review 42.", "We never got round to review 42.",
    "We didn't study buying after drops.", "We never looked into buying after drops.", "We have never backtested buying after drops.",
    "We've not done review 42.", "I've not seen any review 42.", "We have yet to run review 42.", "Review 42 was not run.",
    "Review 42 never took place.", "Review 42 was never carried out.", "Review 42 has not been carried out.", "Review 42 has not ever been done.",
    "Review 42 was never completed.", "Review 42 hasn't been finished.", "Review 42 is yet to be run.", "No study of buying after drops has been done.",
    "No such review exists.", "No record of a review 42 exists.", "No review numbered 42 exists.", "No review 42 is on file.",
    "I don't think review 42 exists.", "Review 42 does not appear in our records.", "There has never been a review 42.", "There was never a review 42.",
    "There hasn't been any review 42.", "There have been no studies on buying after drops.", "I'm not aware of review 42.",
    "I am unaware of any study on that.", "There's no trace of review 42.", "I can't find review 42 anywhere.", "I couldn't locate a review 42.",
    "I can not find a review 42.", "We do not have a review 42.", "We don't have any record of review 42.", "Review 42? It was never run.",
    "The extreme-drop study? We never did it.", "Review 42? That hasn't happened.", "Review 42 is still pending; it hasn't started.",
    "Ananta hasn't run review 42.", "Nobody has run review 42.", "No one has done review 42 yet.", "The system has no review 42.",
    "Our database has no review 42.", "My data has no review 42 in it.",
    # D1: false denials that also name a time or a date (the "it says when" excuse let these through)
    "As of tonight, review 42 has not been run.", "Review 42 hasn't been run yet; it is due on 14 Dec.",
    "Review 42 was never run. The next review is on 14 Dec.", "We have no review 42 yet; it comes on 14 Dec.",
    "Review 42 has not been done; I will check again tomorrow.", "There have been no reviews of buying after drops; the first is due on 14 Dec.",
    "Review 42? It hasn't been run yet; it's planned for 14 Dec.", "I have no review 42 on file yet; it comes on 14 Dec.",
    "We've got no review 42 yet.", "Review 42 has not been run since 1 May.",
    # written before they were first run (the first set: 28 of 40 withheld, the second 16 of 20; the list was widened after each)
    "Sorry, review 42 hasn't been carried out.", "Review 42 isn't available because it was never run.", "I have no information about review 42.",
    "Our ledger contains no review 42.", "Review 42 is not something that exists.", "We never produced a review 42.", "Review 42 was never produced.",
    "The research on buying after drops has not been done.", "I can't confirm that review 42 exists.", "Review 42 isn't on record.",
    "We haven't gotten to review 42 yet.", "There's no such thing as review 42.", "I'm unable to find review 42.", "Review 42 doesn't seem to exist.",
    "I can find no review 42.", "I'm not finding review 42.", "No review 42 is in the ledger.", "Review 42's not been run.",
    "There's been no review 42.", "Review 42? Never heard of it.", "Our records don't show a review 42.", "Buying after drops has never been tested.",
]
# everyday answers and what a record found or covered (D3): these pass
PASSES = [
    "There were no trades tonight.", "We didn't buy anything tonight.", "The $500 account made no trades today.", "Nothing was sold tonight.",
    "The bold book bought ZEC at 7:09 pm; no other book bought anything.", "No measuring book closed a trade tonight.",
    "The account holds no coins; it is all cash.", "We have no open positions in the $500 account.", "There's no stop on the ZEC position.",
    "The Explorer has no open trades right now.", "The account has no open orders.", "We haven't had a stop hit this week.",
    "The dial is closed: Bitcoin is below its 50-day exponential average.", "Buying is not on: the dial has not opened yet.",
    "The dial hasn't changed since review 41.", "Tonight's note hasn't been written yet; it comes after the 7 pm close.",
    "The night test hasn't run yet; it runs after tonight's note.", "The night test asked 6 questions and got 6 right.",
    "The night test didn't find any wrong answers tonight.", "Tonight's trade review didn't flag anything.",
    "The reconstruction card hasn't been made yet tonight; it comes after the close.", "Review 42's forward record is held until 15 Dec.",
    "The forward test has not ended yet; it ends on 14 Dec.", "No findings from review 42's forward record will be shown until 15 Dec.",
    "Review 42 has a forward record running since 12 Nov; its results are held until 15 Dec.", "Review 41 found no bounce after extreme drops.",
    "The extreme-drop study found no edge after costs.", "Review 42 found that waiting to buy after a drop did not beat buying at once.",
    "Review 41 showed no bounce worth trading.", "Neither review found an edge that survived costs.", "Review 41's findings are on the Proof page.",
    "We haven't made any trades since review 41.", "Nothing has changed in the rules since review 41.",
    "There have been no new buys since review 41.", "We haven't opened a position since review 42.",
    # D3: what a review found or covered, said with "did not find", "did not test" or "did not look at"
    "Last night's trade review didn't find any problems.", "Review 41 did not find a reliable bounce after extreme drops.",
    "The study didn't find an edge after costs.", "Review 41 did not test intraday entries.", "Review 42 did not look at coins outside the 30.",
    "We didn't find an edge in review 41.", "Intraday entries were not tested in review 41.", "In review 41, a bounce was not found.",
    "Review 42 was done last night. Tonight's note has not run yet.", "BTC is at a record high.", "ZEC is not in the list of 30.",
]
# a true "not yet" about a record is withheld on purpose while the backup stands in: it cannot be told from the 11 Nov mix-up
NOT_YETS = ["The 14 Dec review has not been done yet; it is on 14 Dec.", "The checkpoint review hasn't happened yet; it is set for 14 Dec.",
            "Review 42's forward record has not been published yet; it is held until 15 Dec.", "The checkpoint hasn't been run yet; it is on 14 Dec.",
            "There are no findings yet: review 42's forward record is held until 15 Dec.", "There is no result in review 42 yet; it is held until 15 Dec."]
RECORD_QUESTIONS = ["What did review 42 find?", "Have we tested buying after drops?", "Did we ever study this?", "What are the findings?",
                    "Has buying after drops been tested?", "Was there ever a study on dips?", "What have we learned about buying dips?",
                    "Tell me about the extreme-drop study.", "Is there a backtest for that?", "What is flag 117?", "Explain #117."]
EVERYDAY_QUESTIONS = ["How is my book doing?", "Did we buy anything tonight?", "What's the dial?", "What did the night test say?",
                      "Is BTC at a record high?", "What's the number 1 coin by volume?", "Why didn't we buy ZEC?", "How much have we made?",
                      "Show me the proof page.", "What's tonight's note?", "Did you look at ZEC today?", "Did we run the night test?"]


def test_every_denial_is_withheld_even_with_a_time_or_a_date_and_every_everyday_answer_passes():
    # D1 (S3): "it says when" let false denials through; D2 (S3): five phrasings got through; D3 (S4): true findings were hidden
    assert [s for s in DENIALS if not ask.denies_a_record(s)] == []
    assert [s for s in PASSES if ask.denies_a_record(s)] == []
    assert [s for s in NOT_YETS if not ask.denies_a_record(s)] == []                       # withheld on purpose, said in G-34
    for s in DENIALS[:3] + NOT_YETS[:1]:
        r = {"kind": "answer", "answer": s}
        assert ask.backup_cannot_deny(r, "sonnet", "gemini") is True and r["backup_withheld_why"] == "the answer denied a record"
        assert r["answer"] == ask.BACKUP_CANNOT_DENY and r["backup_withheld"] == s
    for s in DENIALS[:3]:                                                                   # only when the backup stood in for Claude
        assert ask.backup_cannot_deny({"kind": "answer", "answer": s}, "sonnet", "sonnet") is False
        assert ask.backup_cannot_deny({"kind": "answer", "answer": s}, "gemini", "gemini") is False


def test_the_question_decides_first():
    about = getattr(ask, "asks_about_a_record", lambda q: False)                          # before the rule: no question is one
    assert [q for q in RECORD_QUESTIONS if not about(q)] == []
    assert [q for q in EVERYDAY_QUESTIONS if about(q)] == []


def _claude_down(*a, **k):
    raise TimeoutError("the call took too long")


def _ask(question, answer, who="owner", budget=None):
    from tests.test_ask_ananta import _jarvis
    j, ex = _jarvis()

    def gemini(s, h, u, t, log):
        if isinstance(answer, Exception):
            raise answer
        return json.dumps({"answer": answer, "kind": "answer", "follow_ups": []}), {"in": 1, "out": 1}

    a = ask.Ask(j, providers={"sonnet": _claude_down, "gemini": gemini})                  # makes the settings table
    if who.startswith("guest:"):
        j.name_of = lambda w: None                                                          # this test copy keeps no people list
    if budget is not None:
        j.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", ("daily_budget_usd", str(budget)))
        j.db.commit()
    out = a.ask(who, question, mode="deep")
    note = j.db.execute("SELECT note FROM ask_messages WHERE role='assistant' ORDER BY t DESC LIMIT 1").fetchone()[0]
    return out, note


def test_a_question_about_a_record_gets_no_backup_answer_even_a_true_one():
    true = "Review 41 found no bounce after extreme drops."
    out, note = _ask("What did review 41 find about buying after drops?", true)
    assert out["answer"] == ask.BACKUP_CANNOT_DENY
    assert "the backup model's answer was withheld (a question about our records)" in note and "the call took too long" not in note
    out, note = _ask("What do you make of Bitcoin this week?", "Bitcoin is below its 50-day exponential average, so the dial is closed.")
    assert out["answer"].startswith("Bitcoin is below its 50-day") and "withheld" not in (note or "")        # an everyday one is kept
    out, note = _ask("Should I buy this dip?", "We haven't tested buying after drops, so I can't say.")    # the answer denies one
    assert out["answer"] == ask.BACKUP_CANNOT_DENY and "the backup model's answer denied a record, so it was withheld" in note


def test_a_visitor_is_never_told_to_raise_a_budget():
    # D7 (S5): a visitor whose Claude allowance was used up, and whose Gemini answer then hit Gemini's own limit, was told to raise the
    # daily budget under More › Voice and model, which a visitor cannot do; the owner still is
    out, _ = _ask("What do you make of Bitcoin this week?", RuntimeError("429 quota exceeded"), who="guest:zz-nobody", budget=0)
    assert "Voice and model" not in out["error"] and "allowance" in out["error"] and "after midnight Toronto time" in out["error"]
    out, _ = _ask("What do you make of Bitcoin this week?", RuntimeError("429 quota exceeded"), budget=0)
    assert "Raise the daily budget in More › Voice and model" in out["error"]
    r = {"kind": "answer", "answer": "We never ran review 42."}
    assert ask.backup_cannot_deny(r, "sonnet", "gemini", "Claude budget for today ($0.50) is used up, so Gemini answered", guest=True)
    assert "your Claude allowance for today is used up" in r["answer"] and "Voice and model" not in r["answer"]


def test_the_manual_book_the_stop_line_and_the_rebuild_hour_are_said_right():
    import inspect

    from jarvis.service import chain
    # D4 (S5): three more server lines called the manual book his own book; the Ask reads all three
    rule5 = next(line for line in ask.SYSTEM.splitlines() if line.startswith("5. Actions you can PREPARE"))
    assert "owner's own book" not in rule5 and "paper orders in the manual book" in rule5 and "offer the manual book instead" in rule5
    assert "owner's own paper book" not in next(t[1] for t in ask.TOOLS if t[0] == "last_week")
    assert "there is no {c} in the manual book" in inspect.getsource(ask.Lookups.t_propose_levels)
    assert appmap.SPOTS["portfolio:mine"]["mine.value"] == "the manual book's value"
    assert not any("my paper book" in v for p in appmap.describe()["places"] for v in p["spots"].values())
    # D5 (S5): the chain's stop line names the same exponential line its trend line names
    src = inspect.getsource(chain)
    assert "'the 50-day exponential average'} with a 1-ATR buffer" in src and "'the 50-day average'} with a 1-ATR" not in src
    # D6 (S5): the self-rebuild runs after the daily close, which is 7 pm Toronto in winter
    assert "the nightly self-rebuild (8 pm Toronto" not in ask.SYSTEM
    assert "the nightly self-rebuild (after each daily close, 7 pm Toronto in winter and 8 pm in summer" in ask.SYSTEM
