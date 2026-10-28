"""27 Oct night outside review of the India Ask (Madhav, 21:29: "be an outsider and analyze those answers according to the market ... and
perform the fixes"): the horizon of the money, evidence that fits, a decision only when asked, the next-session date, no cut-off sentences,
plain words, unconditional safety, the order conflict, one source per number and the per-turn lookup."""
import datetime as dt

from jarvis.india import answerguide as G
from jarvis.india import ask as A
from jarvis.india import askwords as W
from jarvis.india import marketcontext as MC


def test_the_horizon_decides_which_evidence_fits():
    assert G.horizon("Should I take a personal loan to buy stocks while the market is down?") == "personal_finance"
    assert G.horizon("Should I invest in gold or the Nifty for the next 5 years?") == "long_term"
    assert G.horizon("Is SBI Gold Fund Direct Plan Growth a good fund to hold?") == "long_term"
    assert G.horizon("Where would you put a stop-loss on a breakout trade?") == "trade"
    assert G.horizon("How has Reliance done this year?") is None
    g = G.guide("My Nifty index fund SIP is down. Should I stop it?", {})
    assert g["horizon"] == "long_term" and any("Do not use the 50/200-day averages" in x for x in g["lines"])
    assert any("Do not quote the practice book" in x for x in g["lines"]) and g["decision_asked"]


def test_a_decision_only_when_asked_and_the_book_only_when_asked():
    assert not G.decision_asked("What is a bracket order and when would I use it?")
    assert not G.decision_asked("How big an emergency fund should I have before I start trading?")
    assert G.decision_asked("Is TCS a good buy now?") and G.decision_asked("My friend's SIP: should he continue?")
    assert any("No decision was asked" in x for x in G.guide("What is the put-call ratio?", {})["lines"])
    assert G.book_question("How is the practice book doing?") and not G.book_question("Should I buy gold?")
    assert not any("Do not quote the practice book" in x for x in G.guide("What is the win rate of your picks?", {})["lines"])


def test_safety_and_topic_lines():
    loan = G.guide("Should I take a personal loan to invest in shares since the market fell?", {})["lines"]
    assert any("plain no" in x and "no condition" in x for x in loan)
    tip = " ".join(G.guide("A Telegram group says this penny stock will double. Buy?", {})["lines"])
    assert "SEBI Check" in tip and "@valid" in tip
    assert any("put writers" in x for x in G.guide("What does a high PCR mean in India?", {})["lines"])
    assert any("diversified fund" in x and "FACTS.lookup" in x for x in G.guide("Small caps fell 30%, buy now?", {})["lines"])
    r = G.guide("What is the rupee doing and does it matter for my holdings?",
                {"account_allocation": {"holdings_ranked": [{"symbol": "TATAPOWER"}, {"symbol": "TMPV"}, {"symbol": "XYZ"}]}})
    assert set(r["rupee_sensitivity"]["holdings"]) == {"TATAPOWER", "TMPV"} and "not an Ananta test" in r["rupee_sensitivity"]["note"]


def test_next_session_skips_weekends_and_holidays(monkeypatch):
    monkeypatch.setattr(G, "_holidays", lambda: {dt.date(2026, 11, 10)})
    assert G.next_session_after("2026-10-27") == dt.date(2026, 10, 28)
    assert G.next_session_after("2026-10-30") == dt.date(2026, 11, 2)          # Friday -> Monday
    assert G.next_session_after("2026-11-09") == dt.date(2026, 11, 11)         # the holiday is skipped
    assert G.day_words("2026-10-28") == "Wed 28 Oct" and G.next_session_after(None) is None


def test_the_sign_off_removal_never_leaves_a_cut_sentence():
    a = A.finish({"answer": "Sir, the gap is small and the tests found no edge; paper only, not advice."}, "what is the gap", True)["answer"]
    assert a == "Sir, the gap is small and the tests found no edge."
    b = A.finish({"answer": "Sir, keep the SIPs, and this is not advice."}, "what about my sips", True)["answer"]
    assert b == "Sir, keep the SIPs."
    assert A._close_cut("Sir, hold it, but") == "Sir, hold it." and A.tidy_end("Sir, The rupee is weaker") == "Sir, the rupee is weaker."


def test_plain_words_for_in_house_jargon():
    s = W.words("On the liquid 250 the research book had 3 scored sessions and 1 call(s); the study fill minus the realistic fill is the slippage.")
    assert "liquid" not in s and "250 most traded stocks" in s and "practice book" in s and "3 sessions with a result" in s
    assert "1 call;" in s and "(s)" not in s and "ideal price minus the realistic price" in s
    assert W.words("2 trade(s) and the full suggestion") == "2 trades and the suggested change"
    assert W.words("Book over 2 scored session(s): 1 scored trade(s), index +48 bp") == "Book over 2 sessions with a result: 1 trade with a result, index +0.48%"
    assert W.words(W.words("the liquid-250 stocks")) == W.words("the liquid-250 stocks")       # idempotent
    assert "YouTube stocks teacher" in W.name("TWT-H22", {"TWT-H22": "A 7% stop"})
    assert W.words("The lookup holds no year-to-date figure.") == "Ananta's data holds no year-to-date figure."


def test_no_decision_line_when_the_named_company_has_no_data():
    no = G.guide("What do you think of Tesla shares?", {"lookup": {}})["lines"]
    assert any("NO-DATA CHECK" in x for x in no)
    have = G.guide("Is Zomato a good buy?", {"lookup": {"stocks": {"ETERNAL": {}}}})["lines"]
    assert not any("NO-DATA CHECK" in x for x in have)


RM = {"data_through": "2026-10-26", "next_session": "2026-10-27", "market": {"trend_state": "below_both"},
      "technicals": {"indices": {"NIFTY 50": {"as_of": "2026-10-27", "close": 25700.0, "vs_sma": {"50": 0.025, "200": 0.055}}}},
      "call": {"call": "BULLISH", "data_through": "2026-10-26", "hits": 1, "scored": 6, "null_hits": 3}, "sp1": {"status": "lost"},
      "decisions_today": {"chosen": [{"symbol": "AAA", "campaign": "PULL"}, {"symbol": "BBB", "campaign": "REV"}, {"symbol": "CCC", "campaign": "CTL"}]}}


def test_one_value_for_the_nifty_gap_to_its_averages():
    lc = A.latest_closes(RM)
    assert lc["newest_date"] == "2026-10-27" and lc["nifty_vs_averages"]["words"] == "on Tue 27 Oct the Nifty was 2.5% above its 50-day average and 5.5% above its 200-day"


def test_a_call_for_a_session_already_traded_and_a_call_below_a_coin_flip(monkeypatch):
    monkeypatch.setattr(G, "_holidays", lambda: set())
    s = A.call_state(RM)
    assert not s["is_for_next_session"] and s["below_coin_flip"]
    assert s["words"].startswith("No daily call has been made yet for the next session") and "for the Tue 27 Oct session" in s["words"]
    assert s["words"].endswith("worse than a coin flip, so don't act on it.")
    ok = {**RM, "technicals": {}, "call": {**RM["call"], "hits": 4}}
    assert A.call_state(ok)["words"].startswith("The daily call for the next session is bullish") and "don't act" not in A.call_state(ok)["words"]


def test_the_decision_answer_says_when_the_picks_were_already_traded(monkeypatch):
    monkeypatch.setattr(G, "_holidays", lambda: set())
    monkeypatch.setattr(A.views, "readmodel", lambda: RM)
    a = A.decide_flow("What did you decide for the next session, and why?")["answer"]
    assert "Tue 27 Oct session, already traded" in a and "Wed 28 Oct" in a and "made tonight" in a
    assert "(s)" not in a


def test_the_rupee_holdings_question_reaches_the_model_and_the_reading_is_plain(monkeypatch):
    assert MC.market_context_flow("What is the rupee doing, and does it matter for my holdings?") is None
    rm = {"market_context": {"status": "ok", "tested": "Tested 26 Oct (studies XO1, FX1 and the crude card TWT-H43): none ...",
                             "rupee_same_day": {"status": "ok", "value": 95.19, "as_of": "2026-10-26", "change_1": 0.003, "change_5": 0.001, "source": "Kite", "contract": "USDINR26OCTFUT"},
                             "macro": {"DEXINUS": {"label": "USD/INR, FRED", "status": "ok", "value": 95.05, "as_of": "2026-10-23", "lag_days": 3, "change_1": 0.001,
                                                   "change_5": 0.002, "source": "FRED"}}}}
    monkeypatch.setattr(MC.views, "readmodel", lambda: rm)
    a = MC.market_context_flow("what is the rupee doing?")["answer"]
    assert "95.19" in a and "Kite" not in a and "FRED" not in a and "USDINR" not in a and "The official daily dollar-rupee rate 95.05" in a
    assert "never to trade" in a and "XO1" not in a and "the crude" not in a


def test_an_order_naming_a_holding_shows_ananta_s_own_call(monkeypatch):
    plan = {"ready": True, "holdings": [{"symbol": "TATAPOWER", "action": "REDUCE", "weight_pct": 24.3}, {"symbol": "MARICO", "action": "HOLD", "weight_pct": 5.0}]}
    monkeypatch.setattr(A.views, "allocation_plan", lambda full=False: plan)
    assert A.order_conflict("Buy 50 more TATAPOWER for me now") == " That goes against Ananta's own call on TATAPOWER: reduce by half; it is 24.3% of your stocks."
    assert A.order_conflict("sell marico now").startswith(" That goes against Ananta's own call on MARICO: keep")
    assert A.order_conflict("buy INFY now") == ""


def test_system_carries_the_review_rules():
    s = A.SYSTEM
    for k in ("NAMED STOCKS, ETFS, FUNDS, SECTORS, GOLD, RULES", "MATCH THE HORIZON", "EVIDENCE THAT FITS", "THE PRACTICE BOOK", "SAFETY IS UNCONDITIONAL",
              "ONE NUMBER, ONE SOURCE", "INDIA PRACTICE", "FACTS.lookup", "answer_guide"):
        assert k in s, k
    assert "FACTS block in the user turn" not in s


def test_lookup_and_the_guide_go_in_this_turn(monkeypatch, tmp_path):
    """The coordinator's wiring: FACTS.lookup for the names in the question, per turn, so the cached facts block stays the same."""
    import json
    seen = {}
    monkeypatch.setattr(A.lookup, "facts_for", lambda q: {"mutual_funds": [{"name": "SBI Gold Fund Direct Plan Growth", "words": "dated"}]} if "SBI" in q else {})
    monkeypatch.setattr(A, "ASK_DIR", tmp_path)
    monkeypatch.setattr(A, "ENV_FILE", tmp_path / "no.env")
    monkeypatch.setattr(A, "facts", lambda owner=True: {"data_through": "2026-10-26", "market": {}})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    def fake_post(url, headers, body):
        seen["body"] = body
        return {"content": [{"type": "text", "text": json.dumps({"kind": "answer", "stage": "learning", "answer": "Sir, ok.", "breakdown": [], "evidence": [], "follow_ups": []})}],
                "usage": {"input_tokens": 10, "output_tokens": 5}}
    A.ask("madhav", "Is SBI Gold Fund Direct Plan Growth a good fund to hold?", post=fake_post)
    user = seen["body"]["messages"][-1]["content"]
    assert "SBI Gold Fund Direct Plan Growth" in user and '"answer_guide"' in user and '"horizon": "long_term"' in user
    assert "SBI Gold Fund" not in seen["body"]["system"][1]["text"]


def test_per_turn_keys_include_the_lookup_and_the_guide():
    import inspect
    src = inspect.getsource(A.ask)
    assert '"lookup", "answer_guide"' in src and "lookup.facts_for(text_q)" in src
