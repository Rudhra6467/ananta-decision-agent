"""23 Nov 2026 (Madhav's cost review): "Is everything running?" is answered in code, with no model call."""
from jarvis.india import ask


def _rm(ok=True):
    jobs = [{"label": "nightly", "ok": True, "problems": []},
            {"label": "openingview", "ok": ok, "problems": [] if ok else ["exit 1 (that run ended Sun 22 Nov 23:50)"]}]
    return {"built_at": "2026-11-23T12:20:05+00:00", "jobs": {"jobs": jobs, "signin": "automatic at 20:10 Toronto"}}


def test_a_failed_job_is_named(monkeypatch):
    monkeypatch.setattr(ask.views, "readmodel", lambda: _rm(False))
    r = ask.health_flow("Is everything running? What is down, since when, and what do I do?")
    assert r and "1 of 2 India jobs" in r["answer"] and "openingview" in r["answer"] and "23 Nov, 17:50 IST" in r["answer"]


def test_all_clean(monkeypatch):
    monkeypatch.setattr(ask.views, "readmodel", lambda: _rm(True))
    import jarvis.india.selfparts as sp
    monkeypatch.setattr(sp, "scan", lambda: [])
    r = ask.health_flow("is everything running?")
    assert r and r["answer"].startswith("Sir, yes: all 2 India jobs")


def test_other_questions_still_go_to_the_model():
    assert ask.health_flow("Ananta, is everything good for you in your work? You need anything from me?") is None
    assert ask.health_flow("why keep cash, if market and stocks are in uptrend?") is None
