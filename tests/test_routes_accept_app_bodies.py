"""Oct 13: for two days every typed question failed with 422 ("[object Object]" on the phone) because a helper slipped between a
route decorator and its function. This test sends the app's own request shapes to every route the app posts to, through the real
FastAPI app: a 422 or 404 on any of them fails the build. A real 422 now comes back as one plain sentence, never an object."""
import pytest

from tests.test_sessions import _setup

# (path, body) exactly as jarvis/app sends them (src/api.ts callers)
APP_POSTS = [
    ("/v3/ask", {"text": "ping", "thread": None, "mode": "auto", "context": {"here": {"screen": "ask"}, "about": None}}),
    ("/v3/ask", {"text": "ping", "thread": "t1", "mode": "google_auto", "context": {"here": {"screen": "ask"}, "tts": {"voice": "Deep", "speed": 1.0}, "chips": ["a"]}}),
    ("/v3/voice/transcribe", {"audio_b64": "AAAA", "mime": "audio/wav"}),
    ("/v3/voice/turn", {"audio_b64": "AAAA", "mime": "audio/wav", "thread": "t1", "mode": "auto", "context": {"here": {"screen": "ask"}}}),
    ("/v3/ask/speaker", {"thread": "t1", "who": "back"}),
    ("/v3/ask/rate", {"id": "nope", "rating": 1}),
    ("/v3/onboard", {"step": "permission", "value": "type", "tz": "America/Toronto"}),
    ("/v3/onboard/capital", {"amount": 500}),
    ("/v3/onboard/mode", {"mode": "ask"}),
    ("/v3/onboard/demo/clear", {}),
    ("/v3/book500/resume", {}),
]


def _client(monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from jarvis.service import app as appmod

    j, clock = _setup()
    monkeypatch.setattr(appmod, "_J", j)
    monkeypatch.setattr(appmod, "_JG", {})
    c = TestClient(appmod.app, raise_server_exceptions=False)      # a missing API key is a 500 here, not the point
    tok = c.post("/auth/login", json={"email": "owner@x.com", "password": "correct horse 1"}).json()["token"]
    return c, {"Authorization": f"Bearer {tok}"}


def test_every_app_post_is_accepted(monkeypatch):
    c, h = _client(monkeypatch)
    bad = []
    for path, body in APP_POSTS:
        r = c.post(path, json=body, headers=h)
        if r.status_code in (404, 405, 422):
            bad.append((path, r.status_code, r.text[:160]))
    assert not bad, f"the app's own requests are refused: {bad}"


def test_a_real_422_is_one_plain_sentence(monkeypatch):
    c, h = _client(monkeypatch)
    r = c.post("/v3/ask", json={"thread": "t1"}, headers=h)                       # no text at all
    assert r.status_code == 422
    d = r.json()["detail"]
    assert isinstance(d, str) and "text" in d and "[" not in d
