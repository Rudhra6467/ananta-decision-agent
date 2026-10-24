"""Picking a fix by voice in the India Ask (24 Oct, from Madhav's own chat), and the portfolio review in code (request 95)."""
from jarvis.india import ask

OPTS = [{"title": "Wait longer before deciding you're done", "lane": "DECISION"},
        {"title": "Show a clear listening indicator with Done button", "lane": "DECISION"},
        {"title": "Keep listening if you resume speaking", "lane": "DECISION"}]


def test_real_picks_are_caught():
    assert ask._picks("2", OPTS) == [2]
    assert ask._picks("fix 1", OPTS) == [1]
    assert ask._picks("the second one", OPTS) == [2]
    assert ask._picks("Yeah, maybe two will do good. Show you listen, clear indicator with done button, near trading, so you plan. I'll do yes for that.", OPTS) == [2]
    assert ask._picks("Yeah. Thanks for flagging and Pixels 1 and 2 sounds good. We will go with the Pixels 1 and 2.", OPTS) == [1, 2]
    assert ask._picks("let's go with option three", OPTS) == [3]
    assert ask._picks("clear listening indicator with a done button please", OPTS) == [2]


def test_casual_words_are_not_picks():
    assert ask._picks("Second bot's answer is basically the same. Review, solid on the course. No, there is...", OPTS) == []
    assert ask._picks("Question one.", OPTS) == []
    assert ask._picks("One more thing, what is the Nifty doing today?", OPTS) == []
    assert ask._picks("fix 7", OPTS) == []


def test_portfolio_review_needs_the_owner_and_skips_flags(monkeypatch):
    plan = {"ready": True, "snapshot": {"taken_at": "2026-10-22T16:36:22+00:00", "stale_days": 2},
            "holdings": [{"symbol": "TATAPOWER", "grade": "C", "score": 46.0, "rank": 1, "value_inr": 27573, "weight_pct": 24.8, "pnl_pct": 27.1, "action": "TRIM", "suggest_inr": 10900,
                          "why": "Middling.", "wrong_if": "it climbs back above Rs 357", "avg": 278.15, "qty": 78},
                         {"symbol": "TMPV", "grade": "C", "score": 41.0, "rank": 2, "value_inr": 9000, "weight_pct": 8.0, "pnl_pct": -5.0, "action": "WATCH", "suggest_inr": 0,
                          "why": "Weak but not weak enough.", "wrong_if": "it closes under Rs 346", "avg": 400.0, "qty": 24}]}
    monkeypatch.setattr(ask.views, "allocation_plan", lambda full=False: plan)
    r = ask.portfolio_flow("Analyze my whole portfolio", "owner")
    assert r and "2 stocks" in r["answer"] and "2 days old" in r["answer"] and any("TATAPOWER" in b for b in r["breakdown"])
    one = ask.portfolio_flow("Analyze TATAPOWER", "owner")
    assert one and "grade C" in one["answer"] and "Wrong if" in one["answer"]
    assert ask.portfolio_flow("So flag this issue: if I ask you to analyze my portfolio you should pull it up", "owner") is None
    assert ask.portfolio_flow("Why is my portfolio down?", "owner") is None
    assert ask.portfolio_flow("Analyze my whole portfolio", "guest:sunny") is None
    assert ask.portfolio_flow("Check how many stocks are healthy", "owner") is None
