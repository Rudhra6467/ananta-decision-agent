"""Request #33 (Oct 11): 'A card is waiting for your Face ID' with no card made, and plan prices no lookup backed."""
from jarvis.service.ask import keep_cards_honest

INCIDENT = ("Afternoon, sir. My pick is Bitcoin: a breakout after a quiet period just completed and the market is allowed. "
            "The plan is a hundred dollars at about 83,800, stop near 81,300, target near 87,300. A card is waiting for your Face ID. "
            "The evidence on this setup is thin.")


def test_the_incident_answer_is_corrected():
    r = keep_cards_honest({"answer": INCIDENT, "breakdown": []}, created=[], log=[{"tool": "knowledge"}])
    assert "card is waiting" not in r["answer"]
    assert "No card was made yet" in r["answer"]
    assert "The evidence on this setup is thin." in r["answer"]
    assert any("not checked" in b for b in r["breakdown"])
    assert len(r["checks"]) == 2


def test_a_real_card_and_a_price_lookup_change_nothing():
    r = keep_cards_honest({"answer": INCIDENT, "breakdown": []}, created=[{"summary": "buy BTC $100"}], log=[{"tool": "prices"}])
    assert r["answer"] == INCIDENT and not r["breakdown"] and "checks" not in r


def test_an_offer_is_not_a_claim_and_a_live_brief_backs_prices():
    a = "I can prepare a card for you to confirm with Face ID if you want: entry at about 83,800, stop near 81,300."
    r = keep_cards_honest({"answer": a}, created=[], log=[], brief_keys=["MARKET_BRIEF"])
    assert r["answer"] == a and "checks" not in r
