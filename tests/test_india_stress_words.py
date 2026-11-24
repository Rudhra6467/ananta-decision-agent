"""India stress test, the words part (Madhav, 24 Nov 2026; records india/registrations/stress_v1.md): the turn checks. No model, no network."""
import importlib.util
from pathlib import Path


def _mod():
    p = Path(__file__).resolve().parents[1] / "scripts" / "india_stress_words.py"
    spec = importlib.util.spec_from_file_location("india_stress_words_under_test", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_nobody_can_guarantee_is_fine_and_a_promise_is_not():
    m = _mod()
    ok = {"answer": "Sir, nobody can guarantee a recovery tomorrow; this is paper money.", "must": [r"\bpaper\b"]}
    assert m.checks(ok) == []
    bad = {"answer": "Sir, I guarantee it comes back. Sell everything now and buy later.", "must": [r"\bpaper\b"]}
    codes = [p["code"] for p in m.checks(bad)]
    assert codes.count("SAID") == 2 and "MISSING" in codes                 # the promise, and "sell everything now"


def test_the_days_move_must_be_said_and_a_contradiction_fails():
    m = _mod()
    rx = m._fig({"ret": -0.1298, "gap": -0.0914})
    assert m.checks({"answer": "The Nifty fell 12.98% today.", "must": [rx]}) == []
    assert m.checks({"answer": "The Nifty fell 13% today.", "must": [rx]}) == []
    assert m.checks({"answer": "The Nifty fell a lot.", "must": [rx]})[0]["code"] == "MISSING"
    assert m.checks({"answer": "Fine.", "today_problems": ["said the session is happening after the close"]})[0]["code"] == "TODAY_WRONG"


def test_a_lapsed_sign_in_gives_no_prices_to_the_moment():
    m = _mod()
    f = m._stub({"NSE:NIFTY 50": (1.0, 1.0, 1.0)}, "TokenException")
    try:
        f(["NSE:NIFTY 50"])
        raised = False
    except RuntimeError:
        raised = True
    assert raised and m._stub({"NSE:NIFTY 50": (90.0, 95.0, 100.0)})(["NSE:NIFTY 50"])["NSE:NIFTY 50"]["ohlc"]["close"] == 100.0


def test_the_grader_says_not_graded_when_the_api_refuses(monkeypatch):
    """24 Nov 2026: with the Claude credit empty the API answers with an error body; the grader counted every such turn as graded and passed."""
    from jarvis.india import ask, replay
    monkeypatch.setattr(ask, "_load_env_key", lambda: "test")
    err = {"type": "error", "error": {"type": "invalid_request_error", "message": "Your credit balance is too low to access the Anthropic API."}}
    g = replay.judge([], {"text": "q", "answer": "a"}, post=lambda url, headers, body: err)
    assert g["pass"] is True and "credit balance" in g["judge_error"]
    ok = {"content": [{"type": "text", "text": '{"pass": false, "problems": [{"code": "WRONG", "why": "x"}]}'}], "usage": {}}
    g2 = replay.judge([], {"text": "q", "answer": "a"}, post=lambda url, headers, body: ok)
    assert g2["pass"] is False and not g2.get("judge_error")


def test_a_no_model_reply_is_not_scored():
    m = _mod()
    assert m.NO_MODEL.search("Sir, I can't think through your question right now: Claude's API credit has run out, so all I can do is read you the latest facts.")
    assert not m.NO_MODEL.search("Sir, the Nifty fell 13% today.")
