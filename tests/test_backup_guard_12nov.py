"""12 Nov 2026 (the keen outside audit, G-34; repair 5's confirm checks, D1 to D7 and E1 to E8; the interim outside review of the
process). When the free backup model answers in Claude's place it cannot vouch for our records. A question about a record, or a short
follow-up to one in the same conversation, is not put to the backup at all; any other backup reply that speaks of a record anywhere in
it, true or not, is withheld; a record named only as a point in time ("since review 41") does not count, and everyday answers pass."""
import json

from jarvis.service import appmap, ask

# false denials: the second confirm check's own (recheck/pkg5_confirm2_probe.py), two sets written before they were first run, and the
# third confirm check's 48 (recheck/pkg5_confirm3.md: 20 of them got past the old word lists)
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
    "We do not have a review 42.", "We don't have any record of review 42.", "Review 42? It was never run.", "The extreme-drop study? We never did it.",
    "Review 42? That hasn't happened.", "Review 42 is still pending; it hasn't started.", "Ananta hasn't run review 42.", "Nobody has run review 42.",
    "The system has no review 42.", "Our database has no review 42.", "As of tonight, review 42 has not been run.",
    "Review 42 hasn't been run yet; it is due on 14 Dec.", "We have no review 42 yet; it comes on 14 Dec.", "I have no information about review 42.",
    "Our ledger contains no review 42.", "We never produced a review 42.", "The research on buying after drops has not been done.",
    "I can't confirm that review 42 exists.", "We haven't gotten to review 42 yet.", "There's no such thing as review 42.", "Review 42 doesn't seem to exist.",
    "Review 42's not been run.", "Review 42? Never heard of it.", "Our records don't show a review 42.", "Buying after drops has never been tested.",
    # the third confirm check's (E1)
    "No review has looked at buying after drops.", "Ananta never got around to testing that.", "We have not had the chance to run review 42.",
    "Review 42 remains undone.", "The team hasn't gotten to review 42 yet.", "Review 42 was planned but never carried out.",
    "We are still waiting to run review 42.", "Review 42 isn't real.", "Our team has never studied buying after drops.", "Buying after drops is untested.",
    "We lack any study of buying after drops.", "Nothing has been done on buying after drops yet.", "The research on dips is still to come.",
    "The builders didn't run review 42.", "Review 42 got cancelled before it ran.", "Review 42 never got started.", "Review 42? Not done yet.",
    "Review 42 is not ready yet; it comes on 14 Dec.", "Review 42 is still in progress.", "Review 42 is scheduled for 14 Dec, so we don't know yet.",
    "Sadly, we never got to the extreme-drop study.", "The dip study was not carried out by the team.", "That review was never published.",
    "As far as I know, there is no review 42.", "I see nothing about a review 42 in the records.", "Review 42 has not been conducted to date.",
    "So far, buying after drops hasn't been studied.", "They never ran review 42.", "Until today there has been no review 42.",
    "We haven't done that study; it is on the plan for December.", "The dip study? It never happened.", "Since 1 Nov, no review has been run.",
    "There has been no backtest of H07 on the 30 coins.", "No checkpoint has happened.", "H07 was never backtested on the 30 coins.",
    "Review forty-two has not been run.",
]
# said in a conversation about a record: "it", "that one" or a bare number is the record
IN_A_RECORD_TALK = ["No, it hasn't been run yet.", "We haven't run 42 yet.", "That one was never run."]
# true answers about a record: withheld too while the backup stands in, because it cannot vouch for them either
RECORD_CONTENT = [
    "Review 41 found no bounce after extreme drops.", "The extreme-drop study found no edge after costs.", "Review 41 showed no bounce worth trading.",
    "Review 42 found that waiting to buy after a drop did not beat buying at once.", "Neither review found an edge that survived costs.",
    "Review 41's findings are on the Proof page.", "Review 41 did not test intraday entries.", "Review 42 did not look at coins outside the 30.",
    "In review 41, a bounce was not found.", "Review 42's forward record is held until 15 Dec.", "The forward test has not ended yet; it ends on 14 Dec.",
    "The 14 Dec review has not been done yet; it is on 14 Dec.", "The checkpoint hasn't been run yet; it is on 14 Dec.",
    "There were no new findings in review 41.", "The study shows no record of a reliable bounce."]
# everyday answers: these pass (a record named only as a point in time does not count)
EVERYDAY = [
    "There were no trades tonight.", "We didn't buy anything tonight.", "The $500 account made no trades today.", "Nothing was sold tonight.",
    "The bold book bought ZEC at 7:09 pm; no other book bought anything.", "No measuring book closed a trade tonight.",
    "The account holds no coins; it is all cash.", "We have no open positions in the $500 account.", "There's no stop on the ZEC position.",
    "The dial is closed: Bitcoin is below its 50-day exponential average.", "Buying is not on: the dial has not opened yet.",
    "The dial hasn't changed since review 41.", "Tonight's note hasn't been written yet; it comes after the 7 pm close.",
    "The night test hasn't run yet; it runs after tonight's note.", "The night test didn't find any wrong answers tonight.",
    "Tonight's trade review didn't flag anything.", "The reconstruction card hasn't been made yet tonight; it comes after the close.",
    "We haven't made any trades since review 41.", "We haven't bought anything since review 41 was published.", "There were no findings on tonight's card.",
    "There are no findings to report tonight.", "BTC is at a record high.", "ZEC is not in the list of 30.", "Bitcoin hasn't tested 90,000 since October.",
    "The 50-day average was tested twice this week and held.", "I'll look into ZEC's drop when the candles land.",
    "I analysed tonight's candles: Bitcoin closed 1% lower.", "The research tier has no new coins this week.", "The dial has not opened since the audit.",
    "No, it hasn't been run yet."]                                                     # outside a talk about a record, "it" is not one
RECORD_QUESTIONS = [
    "What did review 42 find?", "Have we tested buying after drops?", "Did we ever study this?", "What are the findings?", "Has buying after drops been tested?",
    "Was there ever a study on dips?", "What have we learned about buying dips?", "Tell me about the extreme-drop study.", "Is there a backtest for that?",
    "What is flag 117?", "Explain #117.",
    # the third confirm check's 32 (14 got past the old rule)
    "Has anyone checked whether buying after a crash pays?", "Is there any evidence that the dial works?", "Which hypotheses have we already ruled out?",
    "Was the breakout idea ever checked against random entries?", "Do we have any data showing dips bounce?",
    "Did you ever compare buying at once with waiting after a drop?", "What has the repair shop concluded about the Explorer?",
    "Is buying after big drops proven to work for us?", "Tell me what we know about bounces after extreme drops.", "Did the 11 Nov reconstruction find anything?",
    "Did we ever run the numbers on buying dips?", "Did we look at buying after drops before?", "Does waiting after a drop beat buying straight away, by our numbers?",
    "Has Ananta looked at the 9 Nov crash yet?", "Did Ananta ever try waiting a day before buying a dip?", "What did our 9 Nov audit say about the stops?",
    "Have we got a backtest of H07 on the 30 coins?", "Did the research team look at funding rates?", "What's the status of the 14 Dec checkpoint?",
    "Did we test a tighter stop last month?", "Have we registered the eight findings for the forward test?", "Has H14 been tested yet?",
    "Have we measured how often the stop gets hit by a wick?", "Have we checked if the 200-day line matters?"]
EVERYDAY_QUESTIONS = [
    "How is my book doing?", "Did we buy anything tonight?", "What's the dial?", "What did the night test say?", "Is BTC at a record high?",
    "What's the number 1 coin by volume?", "Why didn't we buy ZEC?", "How much have we made?", "Show me the proof page.", "What's tonight's note?",
    "Did you look at ZEC today?", "Did we run the night test?",
    # the third confirm check's 18 that use one of the old rule's words (E3)
    "Can you review my open positions?", "Give me a quick review of the market today.", "Could you review today's trades?", "Did we try to buy ZEC tonight?",
    "Did we try to sell ZEC?", "Did you check if any stops were hit?", "Which coin is #1 by volume today?", "What is the research universe?",
    "Is SOL in the research tier?", "Is Solana in our research tier?", "Has BTC hit a new record?", "What's your track record so far?",
    "Any findings on tonight's card?", "Did you study the chart I sent?", "What's rule 1 of my mandate?", "What do you know about Solana?",
    "What do you know about me?", "What do we know about the Fed meeting?", "Is the dial open after the audit?"]


def test_a_reply_that_speaks_of_a_record_is_withheld_true_or_not_and_everyday_answers_pass():
    # E1 (S3): where the old question list and answer list both missed, a false denial reached the person (9 of 10 pairs)
    speaks = getattr(ask, "speaks_of_a_record", lambda s, context=False: ask.denies_a_record(s))    # before: only denials counted
    assert [s for s in DENIALS if not speaks(s)] == []
    assert [s for s in IN_A_RECORD_TALK if not speaks(s, context=True)] == []
    assert [s for s in RECORD_CONTENT if not speaks(s)] == []                                      # true, but not the backup's to say
    assert [s for s in EVERYDAY if speaks(s)] == []
    for s in DENIALS[:3] + RECORD_CONTENT[:2]:
        r = {"kind": "answer", "answer": s}
        assert ask.backup_cannot_deny(r, "sonnet", "gemini") is True and r["backup_withheld"] == s
        assert r["answer"] == ask.BACKUP_CANNOT_DENY and r["backup_withheld_why"] == "the reply spoke of our records"
    for s in DENIALS[:3]:                                                                   # only when the backup stood in for Claude
        assert ask.backup_cannot_deny({"kind": "answer", "answer": s}, "sonnet", "sonnet") is False
        assert ask.backup_cannot_deny({"kind": "answer", "answer": s}, "gemini", "gemini") is False


def test_the_question_decides_first_and_reads_the_conversation_before_it():
    about = ask.asks_about_a_record
    assert [q for q in RECORD_QUESTIONS if not about(q)] == []
    assert [q for q in EVERYDAY_QUESTIONS if about(q)] == []                                # E3 (S4): ordinary words are not records
    try:                                                                                    # E1: "did it run?" named no record
        follow = [about("Did it run?", ["What did review 42 find?"]), about("And what about 41?", ["Has review 42 run?"]),
                  about("Was it published?", ["Tell me about the dip study.", "Thanks."])]
    except TypeError:
        follow = [False]
    assert follow == [True, True, True]
    assert about("Did it run?", ["How is Bitcoin doing?"]) is False
    assert about("And how is Bitcoin doing today against its 50-day average?", ["What did review 42 find?"]) is False


def _claude_down(*a, **k):
    raise TimeoutError("the call took too long")


def _ask(question, reply, who="owner", budget=None, thread=None, j=None, calls=None, done_tool=None):
    from tests.test_ask_ananta import _jarvis
    if j is None:
        j, _ = _jarvis()

    def gemini(s, h, u, t, log):
        if calls is not None:
            calls.append(u)
        if isinstance(reply, Exception):
            raise reply
        if done_tool:
            log.append({"tool": done_tool, "args": {}, "ok": True})
        body = reply if isinstance(reply, dict) else {"answer": reply, "kind": "answer", "follow_ups": []}
        return json.dumps(body), {"in": 1, "out": 1}

    a = ask.Ask(j, providers={"sonnet": _claude_down, "gemini": gemini})                  # makes the settings table
    if who.startswith("guest:"):
        j.name_of = lambda w: None                                                          # this test copy keeps no people list
    if budget is not None:
        j.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", ("daily_budget_usd", str(budget)))
        j.db.commit()
    out = a.ask(who, question, thread=thread, mode="deep")
    note = j.db.execute("SELECT note FROM ask_messages WHERE role='assistant' ORDER BY t DESC, rowid DESC LIMIT 1").fetchone()[0]
    return out, note, j


def test_a_question_about_a_record_is_never_put_to_the_backup_nor_a_follow_up_to_one():
    # E2 (S3): the backup answered, its card or note stood, and its words were hidden behind "ask me again": asked again, it was done twice
    calls = []
    out, note, j = _ask("What did review 41 find about buying after drops?", "Review 41 found no bounce after extreme drops.", calls=calls)
    assert out["answer"] == ask.BACKUP_CANNOT_DENY and calls == []
    assert "the question is about our records, so the backup model was not asked" in note and "the call took too long" not in note
    out, note, j = _ask("Did it run?", "No, it hasn't been run yet.", thread=out["thread"], j=j, calls=calls)   # E1: the follow-up
    assert out["answer"] == ask.BACKUP_CANNOT_DENY and calls == []
    out, note, j = _ask("What do you make of Bitcoin this week?", "Bitcoin is below its 50-day exponential average, so the dial is closed.",
                        j=j, calls=calls)
    assert out["answer"].startswith("Bitcoin is below its 50-day") and len(calls) == 1 and "withheld" not in (note or "")
    out, note, _ = _ask("Should I buy this dip?", "We haven't tested buying after drops, so I can't say.")    # the reply speaks of one
    assert out["answer"] == ask.BACKUP_CANNOT_DENY and "the backup model's reply spoke of our records, so it was withheld" in note
    out, note, _ = _ask("What did review 41 find?", "x", budget=0)                         # over budget: the note says Gemini was not asked
    assert out["answer"] == ask.BACKUP_CANNOT_DENY_BUDGET and "so Gemini answered" not in note and "was not asked" in note


def test_the_whole_reply_is_read_whatever_its_kind():
    # 11 Nov: the false "no review 42" sat in the breakdown; E8 (S5): a question back ("clarify") or "cannot do yet" was not read
    eleventh = {"kind": "answer", "answer": "Here is where things stand.", "follow_ups": [],
                "breakdown": ["Reviews stop at #34 (34 completed, 13 passed).", "No review 42 exists in our system."],
                "evidence": [{"label": "Completed reviews", "value": "34 total (13 passed)", "source": "MARKET_BRIEF.evidence"}]}
    out, note, _ = _ask("Should I buy this dip?", eleventh)
    assert out["answer"] == ask.BACKUP_CANNOT_DENY and out.get("breakdown") in ([], None) and out.get("evidence") in ([], None)
    for kind in ("clarify", "cannot_do_yet", "not_understood", "out_of_scope"):
        r = {"kind": kind, "answer": "We never ran review 42; which one do you mean?", "options": [{"label": "Review 41"}]}
        assert ask.backup_cannot_deny(r, "sonnet", "gemini") is True and r["kind"] == "answer" and r["options"] == []
    r = {"kind": "answer", "answer": "Bitcoin is 2% below its 50-day exponential average.", "follow_ups": ["Shall I start review 42 for you?"]}
    assert ask.backup_cannot_deny(r, "sonnet", "gemini") is True and r["follow_ups"] == []


def test_what_the_backup_already_did_is_said_so_it_is_not_asked_for_twice():
    out, note, _ = _ask("Remember that I like ETH under 3,000.", "Saved. Review 41 says to wait for the dial.", done_tool="remember")
    assert out["answer"].startswith(ask.BACKUP_CANNOT_DENY)
    assert "While it answered, the backup saved your note; that stands, so there is no need to ask for it again." in out["answer"]


def test_a_visitor_is_never_told_to_raise_a_budget():
    # D7 (S5): a visitor whose Claude allowance was used up, and whose Gemini answer then hit Gemini's own limit, was told to raise the
    # daily budget under More › Voice and model, which a visitor cannot do; the owner still is
    out, _, _ = _ask("What do you make of Bitcoin this week?", RuntimeError("429 quota exceeded"), who="guest:zz-nobody", budget=0)
    assert "Voice and model" not in out["error"] and "allowance" in out["error"] and "after midnight Toronto time" in out["error"]
    out, _, _ = _ask("What do you make of Bitcoin this week?", RuntimeError("429 quota exceeded"), budget=0)
    assert "Raise the daily budget in More › Voice and model" in out["error"]
    r = {"kind": "answer", "answer": "We never ran review 42."}
    assert ask.backup_cannot_deny(r, "sonnet", "gemini", "Claude budget for today ($0.50) is used up, so Gemini answered", guest=True)
    assert "your Claude allowance for today is used up" in r["answer"] and "Voice and model" not in r["answer"]


def test_the_manual_book_the_stop_line_and_the_rebuild_hour_are_said_right():
    import inspect

    from jarvis.service import chain
    # D4 (S5) and E4 (S5): four server lines and the manual book's own lookup called it his own book; the Ask reads all of them
    rule5 = next(line for line in ask.SYSTEM.splitlines() if line.startswith("5. Actions you can PREPARE"))
    assert "owner's own book" not in rule5 and "paper orders in the manual book" in rule5 and "offer the manual book instead" in rule5
    assert "owner's own paper book" not in next(t[1] for t in ask.TOOLS if t[0] == "last_week")
    book = next(t[1] for t in ask.TOOLS if t[0] == "manual_book")
    assert "own manual paper book" not in book and "kept apart from his $500 account" in book
    assert "there is no {c} in the manual book" in inspect.getsource(ask.Lookups.t_propose_levels)
    assert appmap.SPOTS["portfolio:mine"]["mine.value"] == "the manual book's value"
    assert not any("my paper book" in v for p in appmap.describe()["places"] for v in p["spots"].values())
    # D5 (S5): the chain's stop line names the same exponential line its trend line names
    src = inspect.getsource(chain)
    assert "'the 50-day exponential average'} with a 1-ATR buffer" in src and "'the 50-day average'} with a 1-ATR" not in src
    # D6 (S5): the self-rebuild runs after the daily close, which is 7 pm Toronto in winter
    assert "the nightly self-rebuild (8 pm Toronto" not in ask.SYSTEM
    assert "the nightly self-rebuild (after each daily close, 7 pm Toronto in winter and 8 pm in summer" in ask.SYSTEM
