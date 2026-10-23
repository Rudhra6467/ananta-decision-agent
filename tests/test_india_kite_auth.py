"""Kite sign-in helper: secrets stay on disk, the first login pins the user, the token dies at 6 am IST, and the
service routes answer only a browser on the Mac."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from src.india import kite_auth


@pytest.fixture
def private(tmp_path, monkeypatch):
    monkeypatch.setattr(kite_auth, "PRIVATE", tmp_path)
    monkeypatch.setattr(kite_auth, "ENV_FILE", tmp_path / "kite.env")
    monkeypatch.setattr(kite_auth, "TOKEN_FILE", tmp_path / "kite_token.json")
    (tmp_path / "kite.env").write_text("KITE_API_KEY=abc123\nKITE_API_SECRET='s3cret'\n")
    return tmp_path


def test_creds_and_login_url(private):
    assert kite_auth.creds() == ("abc123", "s3cret")
    assert kite_auth.login_url() == "https://kite.zerodha.com/connect/login?v=3&api_key=abc123"


def test_missing_env_is_a_plain_error(private):
    (private / "kite.env").unlink()
    with pytest.raises(RuntimeError, match="kite.env"):
        kite_auth.creds()


def test_expires_at_next_six_am_ist():
    # 10:00 IST login -> 06:00 IST next day; 03:00 IST login -> 06:00 IST same day
    ist = kite_auth.IST
    ten = dt.datetime(2026, 10, 17, 10, 0, tzinfo=ist)
    assert kite_auth.expires_at(ten).astimezone(ist) == dt.datetime(2026, 10, 18, 6, 0, tzinfo=ist)
    three = dt.datetime(2026, 10, 17, 3, 0, tzinfo=ist)
    assert kite_auth.expires_at(three).astimezone(ist) == dt.datetime(2026, 10, 17, 6, 0, tzinfo=ist)


class _Resp:
    def __init__(self, code, data):
        self.status_code, self._d = code, data

    def json(self):
        return self._d

    text = ""


def test_exchange_stores_token_and_pins_user(private, monkeypatch):
    seen = {}

    def fake_post(url, data=None, headers=None, timeout=0):
        seen.update(data)
        return _Resp(200, {"data": {"access_token": "tok", "user_id": "AB1234", "user_name": "Madhav"}})

    monkeypatch.setattr(kite_auth.requests, "post", fake_post)
    st = kite_auth.exchange("rt9")
    assert st["connected"] and st["user_id"] == "AB1234" and "access_token" not in st
    assert seen["api_key"] == "abc123" and len(seen["checksum"]) == 64
    stored = json.loads((private / "kite_token.json").read_text())
    assert stored["access_token"] == "tok" and stored["user_id"] == "AB1234"
    assert (private / "kite_token.json").stat().st_mode & 0o777 == 0o600

    # a different Zerodha user is refused and the stored token is untouched
    monkeypatch.setattr(kite_auth.requests, "post", lambda *a, **k: _Resp(200, {"data": {"access_token": "x", "user_id": "ZZ9999"}}))
    with pytest.raises(RuntimeError, match="not the owner"):
        kite_auth.exchange("rt10")
    assert json.loads((private / "kite_token.json").read_text())["access_token"] == "tok"


def test_status_without_token(private):
    assert kite_auth.status() == {"connected": False, "why": "not signed in yet"}


def test_routes_refuse_non_local_browsers():
    from fastapi.testclient import TestClient

    from jarvis.service.app import app

    c = TestClient(app)
    assert c.get("/kite/login", follow_redirects=False).status_code == 403
    assert c.get("/kite/callback?request_token=x&status=success", follow_redirects=False).status_code == 403
    # /v3/kite/status sits behind the same owner() dependency as every other /v3 route (covered by the auth tests)



# --- automatic sign-in (22 Oct 2026) -------------------------------------------------------------------------------

class _FakeSession:
    """Plays Zerodha: the password call hands out a request_id, the two-factor call accepts a 6-digit code, and the
    connect URL redirects to the owner's callback with a request_token."""

    def __init__(self, password_ok=True, totp_ok=True):
        self.headers, self.calls, self.password_ok, self.totp_ok = {}, [], password_ok, totp_ok

    def get(self, url, allow_redirects=True, timeout=0):
        self.calls.append(("GET", url))
        r = _Resp(302, {})
        r.url = url
        r.headers = {"Location": "http://127.0.0.1:8100/kite/callback?status=success&request_token=RT77"} if "skip_session" in url else {}
        if "skip_session" not in url:
            r.status_code = 200
        return r

    def post(self, url, data=None, timeout=0):
        self.calls.append(("POST", url, dict(data)))
        if url.endswith("/api/login"):
            return _Resp(200, {"status": "success", "data": {"request_id": "req1"}} if self.password_ok else {"status": "error", "message": "Invalid username or password"})
        if url.endswith("/api/twofa"):
            ok = self.totp_ok and data.get("twofa_type") == "totp" and len(data.get("twofa_value", "")) == 6
            return _Resp(200, {"status": "success", "data": {}} if ok else {"status": "error", "message": "Invalid TOTP"})
        raise AssertionError(url)


@pytest.fixture
def login_env(private, monkeypatch):
    monkeypatch.setattr(kite_auth, "LOGIN_ENV", private / "kite_login.env")
    monkeypatch.setattr(kite_auth, "LOCK_FILE", private / "kite_autologin.lock")
    monkeypatch.setattr(kite_auth, "LOG_FILE", private / "autologin.log")
    (private / "kite_login.env").write_text("KITE_USER_ID=AB1234\nKITE_PASSWORD=pw\nKITE_TOTP_SECRET=JBSWY3DPEHPK3PXP\n")
    return private


def test_auto_signs_in_and_stores_the_token(login_env, monkeypatch):
    fake = _FakeSession()
    monkeypatch.setattr(kite_auth.requests, "Session", lambda: fake)
    exchanged = {}
    monkeypatch.setattr(kite_auth, "exchange", lambda rt: exchanged.setdefault("rt", rt) and {"connected": True, "user_id": "AB1234", "expires_at_ist": "x"})
    out = kite_auth.auto()
    assert out["auto"] == "signed in" and exchanged["rt"] == "RT77"
    posts = [c for c in fake.calls if c[0] == "POST"]
    assert posts[0][1].endswith("/api/login") and posts[0][2]["user_id"] == "AB1234"
    assert posts[1][1].endswith("/api/twofa") and posts[1][2]["request_id"] == "req1" and posts[1][2]["twofa_type"] == "totp"
    log = (login_env / "autologin.log").read_text()
    assert "pw" not in log and "JBSWY3DPEHPK3PXP" not in log and "RT77" not in log


def test_auto_skips_when_the_token_is_fresh(login_env, monkeypatch):
    now = dt.datetime.now(dt.timezone.utc)
    (login_env / "kite_token.json").write_text(json.dumps({"api_key": "abc123", "access_token": "t", "user_id": "AB1234",
                                                           "expires_at": (now + dt.timedelta(hours=5)).isoformat(timespec="seconds")}))
    monkeypatch.setattr(kite_auth.requests, "Session", lambda: (_ for _ in ()).throw(AssertionError("no network call expected")))
    assert kite_auth.auto()["auto"].startswith("skipped")


def test_auto_refuses_a_wrong_password_and_a_wrong_user(login_env, monkeypatch):
    monkeypatch.setattr(kite_auth.requests, "Session", lambda: _FakeSession(password_ok=False))
    with pytest.raises(RuntimeError, match="password step refused"):
        kite_auth.auto()
    (login_env / "kite_token.json").write_text(json.dumps({"api_key": "abc123", "access_token": "t", "user_id": "ZZ9999",
                                                           "expires_at": "2000-01-01T00:00:00+00:00"}))
    with pytest.raises(RuntimeError, match="pinned owner"):
        kite_auth.auto()


def test_auto_is_off_without_the_login_file(login_env):
    (login_env / "kite_login.env").unlink()
    with pytest.raises(RuntimeError, match="auto sign-in is off"):
        kite_auth.auto()


def test_totp_secret_accepts_messy_pastes_and_refuses_the_six_digit_code():
    key = "JBSWY3DPEHPK3PXP"
    assert kite_auth.totp_secret("jbsw y3dp-ehpk 3pxp") == key
    assert kite_auth.totp_secret(f"otpauth://totp/Zerodha:AB1234?secret={key.lower()}&issuer=Zerodha") == key
    assert kite_auth.totp_secret(key + "====") == key
    with pytest.raises(RuntimeError, match="6-digit code, not the key"):
        kite_auth.totp_secret("123456")
    with pytest.raises(RuntimeError, match="not a base32 key"):
        kite_auth.totp_secret("hello world! 018")


def test_login_creds_reports_the_pasted_code_plainly(login_env):
    (login_env / "kite_login.env").write_text("KITE_USER_ID=AB1234\nKITE_PASSWORD=pw\nKITE_TOTP_SECRET=654321\n")
    with pytest.raises(RuntimeError, match="6-digit code, not the key"):
        kite_auth.login_creds()
