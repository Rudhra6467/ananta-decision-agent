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
