"""26 Oct: Madhav's Nifty questions reached the crypto Ananta, which said India research was never done. An owner question about the Indian
market now moves him to the India Ananta; talk about the app itself, guests and handovers are left alone; repair news is told per market."""
from jarvis.service import ask


def test_india_questions_move_to_the_india_side():
    for q in ("What is the current state of the Indian market? Nifty, Sensex, and the main sectors.", "For Nifty, what's your 50 over 200 trigger?",
              "How is TATAPOWER doing in my Zerodha account?"):
        r = ask.india_redirect(q)
        assert r and r["ui"][0]["target"] == "market:india" and "India Ananta" in r["say"], q
    assert ask.india_redirect("What is Bitcoin doing today?") is None
    assert ask.india_redirect("flag this: the Indian market switch is hard to find") is None     # about the app: the repair shop handles it
    assert ask.india_redirect("Kitesurfing weather?") is None


def test_repair_news_is_per_market(monkeypatch):
    from jarvis.service import requests_log

    rows = [{"num": 1, "status": "DONE", "text": "[Indian market · Home] x", "about": "flag:india:Home", "note": "n", "told": 0},
            {"num": 2, "status": "DONE", "text": "[Crypto · Home] y", "about": "flag:crypto:Home", "note": "n", "told": 0}]
    monkeypatch.setattr(requests_log, "_select", lambda j, where: rows)
    monkeypatch.setattr(requests_log, "_sentence", lambda r: f"request {r['num']} fixed")
    assert [n["num"] for n in requests_log.news(None, market="crypto", limit=None)] == [2]
    assert [n["num"] for n in requests_log.news(None, market="india", limit=None)] == [1]
    assert [n["num"] for n in requests_log.news(None)] == [1, 2]
