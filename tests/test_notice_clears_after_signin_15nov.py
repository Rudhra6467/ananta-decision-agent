"""15 Nov 2026 (Madhav: the Zerodha notice stayed after the sign-in was sorted): a missed job whose cause was a dead Zerodha token stops
showing as down once a later sign-in has worked; other failures keep showing."""
import datetime as dt

from jarvis.india import views

BUILT = "2026-11-16T01:10:00+00:00"
TOKEN = {"label": "evening_zerodha", "ok": False, "problems": ["steps failed inside the job (india.recorder): token dead; next sign-in 21:00"]}
OTHER = {"label": "paper", "ok": False, "problems": ["empty run: 0 rows"]}
GOOD = {"label": "morning", "ok": True, "problems": []}


def _rm(*jobs):
    return {"built_at": BUILT, "jobs": {"jobs": list(jobs)}}


def _login(monkeypatch, connected, when):
    from src.india import kite_auth
    monkeypatch.setattr(kite_auth, "status", lambda: {"connected": connected, "login_time": when})


def test_a_dead_token_failure_clears_after_a_later_sign_in(monkeypatch):
    _login(monkeypatch, True, "2026-11-16T01:19:00+00:00")
    h = views._health(_rm(TOKEN, GOOD))
    assert h["all_ok"] and h["down"] == []


def test_it_stays_when_no_sign_in_has_worked_since(monkeypatch):
    _login(monkeypatch, True, "2026-11-16T00:35:00+00:00")           # signed in before the record was built
    assert views._health(_rm(TOKEN, GOOD))["down"]
    _login(monkeypatch, False, "2026-11-16T01:19:00+00:00")          # not connected now
    assert views._health(_rm(TOKEN, GOOD))["down"]


def test_other_failures_always_stay(monkeypatch):
    _login(monkeypatch, True, "2026-11-16T01:19:00+00:00")
    h = views._health(_rm(TOKEN, OTHER, GOOD))
    assert not h["all_ok"] and "paper" in " ".join(h["down"])
