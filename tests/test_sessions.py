"""Madhav, Oct 12: sign-ins end after 3 hours without use; visitor accounts last 3 days, then a feedback form; the owner changes his
password in the app."""
import tempfile
from pathlib import Path

import pytest

from jarvis.service import core
from tests.test_jarvis_core import _j

H = 3600


def _setup():
    clock = {"t": 1_800_000_000}
    return _j(Path(tempfile.mkdtemp()), clock), clock


def test_three_hours_without_use_signs_out_but_use_keeps_it_alive():
    j, clock = _setup()
    tok = j.login("owner@x.com", "correct horse 1")
    clock["t"] += 2 * H
    assert j.check(tok, touch=True) == "owner@x.com"            # used at 2 h: the clock restarts
    clock["t"] += 2.5 * H
    assert j.check(tok) == "owner@x.com"                        # 2.5 h after the last use: still in
    clock["t"] += 1 * H                                         # quiet refreshes (touch=False) never kept it alive
    with pytest.raises(core.AuthError, match="without use"):
        j.check(tok)
    with pytest.raises(core.AuthError):
        j.check(tok, touch=True)                                # gone for good


def test_old_tokens_without_a_session_and_logout():
    j, clock = _setup()
    old = core.make_token(j.secret, j.owner, clock["t"])
    with pytest.raises(core.AuthError, match="sign in again"):
        j.check(old)
    svc = core.make_token(j.secret, j.owner, clock["t"], svc=1)   # scripts on the Mac
    assert j.check(svc) == j.owner
    tok = j.login("owner@x.com", "correct horse 1")
    assert j.logout(tok) and not j.logout(tok)
    with pytest.raises(core.AuthError):
        j.check(tok)


def test_visitor_lasts_three_days_then_gets_the_form_once():
    j, clock = _setup()
    tok = j.join(j.invite("Asha")["code"], "Asha K", "asha@example.com", "guest pass 123")
    assert j.people()["visitors"][0]["expires_t"] == clock["t"] + 3 * 86400
    clock["t"] += 3 * 86400 + 60
    with pytest.raises(core.AuthError, match="practice days are over"):
        j.check(tok)
    with pytest.raises(core.AccountExpired) as e:
        j.login("asha@example.com", "guest pass 123")
    assert e.value.form_token and not e.value.answered
    with pytest.raises(core.AuthError):
        j.login("asha@example.com", "wrong")                    # a wrong password never reaches the form
    with pytest.raises(ValueError, match="please answer"):
        j.submit_feedback(e.value.form_token, {"used_for": "looking around"})
    ans = {"used_for": "asked about Bitcoin", "easy": "4", "clear": "5", "again": "Yes", "worst": "voice was slow", "junk": "x"}
    assert j.submit_feedback(e.value.form_token, ans) == {"ok": True}
    assert j.submit_feedback(e.value.form_token, ans)["already"]
    fb = j.feedback()["responses"][0]
    assert fb["name"] == "Asha K" and fb["answers"]["worst"] == "voice was slow" and "junk" not in fb["answers"]
    with pytest.raises(core.AccountExpired) as e2:
        j.login("asha@example.com", "guest pass 123")
    assert e2.value.answered and e2.value.form_token is None
    assert j.people()["visitors"][0]["feedback"] and j.people()["visitors"][0]["expired"]
    j.extend("asha@example.com", 3)                             # Madhav gives more days
    assert j.check(j.login("asha@example.com", "guest pass 123")) == "guest:asha@example.com"


def test_a_form_token_is_not_an_app_token():
    j, clock = _setup()
    j.join(j.invite()["code"], "B", "b@example.com", "guest pass 123")
    clock["t"] += 4 * 86400
    with pytest.raises(core.AccountExpired) as e:
        j.login("b@example.com", "guest pass 123")
    with pytest.raises(core.AuthError):
        j.check(e.value.form_token)


def test_owner_changes_password_and_other_devices_sign_out():
    j, clock = _setup()
    phone = j.login("owner@x.com", "correct horse 1")
    web = j.login("owner@x.com", "correct horse 1")
    with pytest.raises(ValueError, match="current password"):
        j.change_password("wrong", "a brand new pass", keep_token=web)
    with pytest.raises(ValueError, match="10 characters"):
        j.change_password("correct horse 1", "short", keep_token=web)
    r = j.change_password("correct horse 1", "a brand new pass", keep_token=web)
    assert r["signed_out_elsewhere"] == 1
    assert j.check(web) == j.owner
    with pytest.raises(core.AuthError):
        j.check(phone)
    with pytest.raises(core.AuthError):
        j.login("owner@x.com", "correct horse 1")
    assert j.check(j.login("owner@x.com", "a brand new pass")) == j.owner


def test_routes_quiet_refresh_form_and_password(monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from jarvis.service import app as appmod

    j, clock = _setup()
    monkeypatch.setattr(appmod, "_J", j)
    monkeypatch.setattr(appmod, "_JG", {})
    c = TestClient(appmod.app)
    tok = c.post("/auth/login", json={"email": "owner@x.com", "password": "correct horse 1"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    clock["t"] += 2 * H
    assert c.get("/v3/feedback", headers={**h, "X-Ananta-Quiet": "1"}).status_code == 200      # a quiet refresh: not use
    clock["t"] += 1.5 * H
    assert c.get("/v3/feedback", headers=h).status_code == 401                                  # 3.5 h since the sign-in
    tok = c.post("/auth/login", json={"email": "owner@x.com", "password": "correct horse 1"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    # a visitor whose days are over gets the form, then a thank-you
    j.join(j.invite()["code"], "Ravi", "ravi@example.com", "guest pass 123")
    clock["t"] += 3 * 86400 + 1
    tok = c.post("/auth/login", json={"email": "owner@x.com", "password": "correct horse 1"}).json()["token"]
    h = {"Authorization": f"Bearer {tok}"}
    r = c.post("/auth/login", json={"email": "ravi@example.com", "password": "guest pass 123"}).json()
    assert r["expired"] and "token" not in r and len(r["questions"]) == len(core.FEEDBACK_QUESTIONS)
    ans = {"used_for": "x", "easy": "3", "clear": "3", "again": "Maybe"}
    assert c.post("/auth/feedback", json={"form_token": r["form_token"], "answers": ans}).json()["ok"]
    assert c.get("/v3/feedback", headers=h).json()["responses"][0]["name"] == "Ravi"
    assert c.post("/auth/login", json={"email": "ravi@example.com", "password": "guest pass 123"}).json()["answered"]
    assert c.post("/v3/people/extend", json={"email": "ravi@example.com", "days": 2}, headers=h).status_code == 200
    # password change from the app
    bad = c.post("/v3/account/password", json={"current": "nope", "new": "a brand new pass"}, headers=h)
    assert bad.status_code == 400
    ok = c.post("/v3/account/password", json={"current": "correct horse 1", "new": "a brand new pass"}, headers=h)
    assert ok.status_code == 200 and c.get("/v3/feedback", headers=h).status_code == 200
    assert c.post("/auth/logout", headers=h).json()["ok"]
    assert c.get("/v3/feedback", headers=h).status_code == 401
