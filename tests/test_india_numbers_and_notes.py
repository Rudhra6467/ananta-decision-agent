"""3 Nov 2026 (outside trader grade, round 4): every figure must come from the facts; one request naming two notes files both."""
from jarvis.india import ask, numcheck

FACTS = {"trader_desk": {"prep": {"open_option_trades": [{"premium_paid_inr_per_lot": 24699, "lot": 30, "bought_at": 823.3, "paper_move_inr_per_lot": -279}]}},
         "today_live": {"index_now": {"rows": {"NIFTY 50": {"last": 23810.85, "high": 23810.85, "low": 23482.8}}}},
         "account_value": {"value_inr": 161313, "words": "worth Rs 1,61,313"}}


def test_a_worked_out_rupee_figure_is_caught():
    p = numcheck.check("The most it can lose is about Rs 53,500 for the Bank Nifty lot.", FACTS)
    assert numcheck.figures(p) == ["Rs 53,500"]


def test_figures_from_the_facts_pass_rounded_or_not():
    for a in ("The most it can lose is about Rs 24,700 for the lot.", "It is about Rs -279 a lot, and the Nifty closed at 23,811 near its low of 23,483.",
              "Your account is worth about Rs 1,61,300.", "Nifty swings about 234 points on 09:15 IST; in 2026 the trial runs 20 sessions."):
        f = {**FACTS, "trader_desk": {**FACTS["trader_desk"], "prep": {**FACTS["trader_desk"]["prep"], "indices": {"NIFTY 50": {"expected_move_points": 234}}}}}
        assert numcheck.check(a, f) == [], a


def test_scrub_drops_only_the_sentence_with_the_figure():
    a = "Both are bought calls. The loss is capped at about Rs 53,500. A gap up helps them."
    assert numcheck.scrub(a, ["Rs 53,500"]) == "Both are bought calls. A gap up helps them."


def test_two_notes_in_one_request(tmp_path, monkeypatch):
    monkeypatch.setattr(ask, "ASK_DIR", tmp_path)
    th = "t-notes"
    ask._append(th, {"id": "1", "role": "user", "text": "Why can't we go deep and look into more of the data at least when needed?"})
    ask._append(th, {"id": "2", "role": "assistant", "answer": "Tell me which gap to start with and it would be written down first."})
    ask._append(th, {"id": "3", "role": "user", "text": "Our data set feels limited, I didn't even know how good our data sets were."})
    ask._append(th, {"id": "4", "role": "assistant", "answer": "Say the word and I will put that down as a research item to check first."})
    msg = "Yeah, along with the last conversation, your first thing. And this one is also to be registered and somehow to be notified."
    ask._append(th, {"id": "5", "role": "user", "text": msg})
    e = ask._earlier_subject(th, msg)
    assert e and e.startswith("Why can't we go deep")
    assert ask._earlier_subject(th, "please register this one as a research item") is None



def test_two_notes_without_an_offer_when_he_says_the_last_one(tmp_path, monkeypatch):
    monkeypatch.setattr(ask, "ASK_DIR", tmp_path)
    th = "t-notes2"
    ask._append(th, {"id": "1", "role": "user", "text": "Why can't we go deeper into the data when needed?"})
    ask._append(th, {"id": "2", "role": "assistant", "answer": "We can go deeper whenever it's needed."})
    ask._append(th, {"id": "3", "role": "user", "text": "Our data sets feel limited."})
    ask._append(th, {"id": "4", "role": "assistant", "answer": "It is worth keeping an eye on."})
    msg = "Yeah, along with the last conversation, last one, your first thing. And this one is also to be registered."
    ask._append(th, {"id": "5", "role": "user", "text": msg})
    assert ask._earlier_subject(th, msg).startswith("Why can't we go deeper")


def test_a_list_already_said_is_not_spoken_again():
    r = ask.finish({"answer": "Four are on the cut list, in this order: JIOFIN, LICI, KARURVYSYA and IEX.",
                    "breakdown": ["JIOFIN: trim", "LICI: trim", "KARURVYSYA: halve", "IEX: halve"]}, "cut list", True)
    assert "1)" not in r["answer"]
