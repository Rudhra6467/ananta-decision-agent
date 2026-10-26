"""Father mode's Telugu layer: glossary completeness and the spoken states, built from the read model only."""
from __future__ import annotations

from india import telugu

RM = {"data_through": "2026-10-21",
      "market": {"status": "ok", "data_through": "2026-10-21", "nifty_close": 22811.35, "trend_state": "below_both"},
      "call": {"status": "ok", "call": "BULLISH", "scored": 3, "hits": 0},
      "stock_book": {"status": "ok", "open_positions": 45, "by_campaign": {"BRK": {"realised_inr": -3899.0}, "PULL": {"realised_inr": -6490.0}}},
      "decisions_today": {"status": "ok", "chosen": [{"symbol": "MPHASIS", "campaign": "BRK", "why": "x"}, {"symbol": "NYKAA", "campaign": "CTL", "why": "control"}]},
      "sp1": {"status": "lost", "words": "session lost"}}


def test_glossary_has_the_words_the_states_use():
    assert len(telugu.GLOSSARY) >= 50
    for k, (te, plain_te, plain_en) in telugu.GLOSSARY.items():
        assert te and plain_te and plain_en, k
    for needed in ("nifty", "stop loss", "paper trading", "breakout", "pullback", "reversal", "guardrail", "drawdown", "premium", "lot", "consent", "random", "hindsight"):
        assert needed in telugu.GLOSSARY


def test_brief_addresses_father_and_shows_every_number(tmp_path, monkeypatch):
    monkeypatch.setattr(telugu, "PEOPLE", tmp_path / "none.json")          # no private people file: the respectful generic address
    s = telugu.brief_te(RM)
    assert s[0] == "నమస్కారం నాన్నగారు."
    (tmp_path / "p.json").write_text('{"father": {"address": "ABC గారు"}}')
    monkeypatch.setattr(telugu, "PEOPLE", tmp_path / "p.json")             # with it: the name Madhav put there, never one in git
    assert telugu.brief_te(RM)[0] == "నమస్కారం ABC గారు."
    text = " ".join(s)
    assert "22,811" in text and "తగ్గుదల దిశ" in text                      # Nifty and the downtrend, in words
    assert "MPHASIS" in text and "NYKAA" not in text                        # the random control is never offered as a pick
    assert "45 స్టాక్‌లు" in text and "₹-10,389" in text                    # open positions and realised across campaigns
    assert "3 అంచనాల్లో 0 సరైనవి" in text                                  # the call record, honestly
    assert "లాగిన్ సమస్య" in text                                           # the lost SP1 session is said, not hidden
    assert s[-1] == "ఏదైనా అడగాలంటే చెప్పండి." and 3 <= len(s) <= 8


def test_brief_without_data_says_so():
    s = telugu.brief_te({})
    assert "సమాచారం అందలేదు" in s[1]


def test_trade_confirm_guardrail_and_dont_know():
    t = telugu.trade_te({"symbol": "MPHASIS", "campaign": "BRK", "why": "volume 2.1x"}, size_inr=50000, risk_inr=1000)
    assert "MPHASIS" in t and "₹50,000" in t and "₹1,000" in t and "కాగితంపై మాత్రమే" in t and "బ్రేక్అవుట్" in t
    c = telugu.confirm_te("MPHASIS", 19, 48925.0)
    assert "19 షేర్లు" in c and "₹48,925" in c and "పేపర్ ట్రేడ్" in c
    assert "మళ్లీ ఒకసారి 'అవును'" in telugu.confirm_te("MPHASIS", 19, 48925.0, live=True)
    g = telugu.guardrail_te(5.0, 22.0)
    assert "5%" in g and "22%" in g and "మాధవ్ గారు" in g
    assert telugu.dont_know_te("నిఫ్టీ 22,811").endswith("నిఫ్టీ 22,811")
    assert "| stop loss | స్టాప్ లాస్ |" in telugu.glossary_md()


def test_brief_says_the_close_is_missing_instead_of_crashing(tmp_path, monkeypatch):
    monkeypatch.setattr(telugu, "PEOPLE", tmp_path / "none.json")
    rm = dict(RM, market=dict(RM["market"], nifty_close=None))
    s = telugu.brief_te(rm)
    assert "2026-10-21 నాటి నిఫ్టీ ముగింపు సమాచారం అందలేదు." in s
