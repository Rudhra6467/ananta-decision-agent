"""India Ananta V1 service: serves the read model and nothing else; read-only; names a missing read model plainly."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from jarvis.india import service


@pytest.fixture
def lake(tmp_path, monkeypatch):
    rm = tmp_path / "readmodel"
    rm.mkdir()
    reg = tmp_path / "registrations"
    reg.mkdir()
    (rm / "latest.json").write_text(json.dumps({"rules": "readmodel-v0", "built_at": "2026-10-23T00:26:01+00:00", "data_through": "2026-10-21", "next_session": "2026-10-22",
                                                 "market": {"status": "ok", "nifty_close": 22811.35, "trend_state": "below_both", "data_through": "2026-10-21"},
                                                 "call": {"status": "ok", "call": "BULLISH", "scored": 3, "hits": 0}, "stock_book": {"status": "ok", "open_positions": 45, "by_campaign": {}},
                                                 "decisions_today": {"status": "ok", "chosen": []}, "sp1": {"status": "lost", "words": "session lost"},
                                                 "brief": ["Through 2026-10-21: Nifty 22,811."], "missing": []}))
    (reg / "exit_policy_book.md").write_text("# Exit policy book\n")
    monkeypatch.setattr(service, "READMODEL", rm / "latest.json")
    monkeypatch.setattr(service, "REG", reg)
    return tmp_path


def test_readmodel_brief_page_and_health(lake):
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    assert c.get("/health").json()["data_through"] == "2026-10-21"
    j = c.get("/api/readmodel").json()
    assert j["market"]["nifty_close"] == 22811.35 and "served_at" in j and j["age_hours"] is not None
    assert c.get("/api/brief").json()["sentences"] == ["Through 2026-10-21: Nifty 22,811."]
    te = c.get("/api/brief?lang=te").json()
    assert te["lang"] == "te" and te["sentences"][0].startswith("నమస్కారం ") and "22,811" in te["sentences"][1]
    assert c.get("/api/page/exit_policy_book").text.startswith("# Exit policy book")
    assert c.get("/api/page/others_league").status_code == 404           # not written in this fixture
    assert c.get("/api/page/../secrets").status_code in (404, 422)
    html = c.get("/").text
    assert "Ananta · Indian market" in html and "/api/readmodel" in html


def test_missing_read_model_is_named_not_guessed(lake):
    service.READMODEL.unlink()
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    r = c.get("/api/readmodel")
    assert r.status_code == 503 and "no India read model yet" in r.json()["detail"]
    assert c.get("/health").json()["ok"] is False


def test_speak_refuses_empty_and_caps_sentences(lake, monkeypatch):
    seen = {}

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"audio_b64": "x", "duration": 1.0}

    def fake_post(url, json=None, timeout=0):
        seen["url"], seen["body"] = url, json
        return R()

    monkeypatch.setattr(service.requests, "post", fake_post)
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    assert c.post("/api/speak", json={"sentences": ["", "  "]}).status_code == 400
    out = c.post("/api/speak", json={"sentences": [f"s{i}" for i in range(30)], "lang": "en"}).json()
    assert out["duration"] == 1.0 and seen["url"].endswith("8200/speak") and len(seen["body"]["sentences"]) == service.MAX_SENTENCES and seen["body"]["voice"] == service.INDIA_VOICE
    c.post("/api/speak", json={"sentences": ["నమస్కారం"], "lang": "te"})
    assert seen["url"].endswith("8210/speak") and "voice" not in seen["body"]


def test_through_the_tunnel_needs_the_app_token(lake, monkeypatch):
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    cf = {"CF-Connecting-IP": "1.2.3.4"}
    assert c.get("/india/api/readmodel", headers=cf).status_code == 401                     # came through Cloudflare, no token
    calls = []

    class R:
        status_code = 200

        def json(self):
            return {"who": "madhav", "guest": False}

    def fake_get(url, headers=None, timeout=0):
        calls.append((url, headers))
        return R()

    monkeypatch.setattr(service.requests, "get", fake_get)
    service._TOKENS.clear()
    ok = c.get("/india/api/readmodel", headers={**cf, "Authorization": "Bearer tok"})
    assert ok.status_code == 200 and ok.json()["data_through"] == "2026-10-21"
    assert calls[0][0].endswith("/v3/me") and calls[0][1]["X-Ananta-Quiet"] == "1"
    c.get("/india/api/brief", headers={**cf, "Authorization": "Bearer tok"})
    assert len(calls) == 1                                                                   # the second call is remembered, not re-checked
    assert c.get("/india/health", headers=cf).status_code == 200                              # health never needs a token
    assert "Ananta · Indian market" in c.get("/india/").text
