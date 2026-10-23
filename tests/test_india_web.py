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


def test_v3_contract_routes_fill_from_the_read_model(lake, monkeypatch):
    from jarvis.india import views

    monkeypatch.setattr(views, "DATA", lake)
    monkeypatch.setattr(views, "REG", lake / "registrations")
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    h = c.get("/v3/home").json()
    assert set(h) >= {"summary", "feed", "mission"} and h["mission"]["account"]["start_cad"] == 60000.0 and h["mission"]["market"]["btc"] == 22811.35
    assert h["mission"]["market"]["regime"] == "DOWNTREND" and h["summary"]["portfolio"]["mode"] == "PAPER"
    b = c.get("/india/v3/books").json()
    assert b["account"]["book"]["currency"] == "INR" and isinstance(b["trades"], list) and isinstance(b["closed"], list)
    assert c.get("/v3/coins").json()["coins"] == []                                   # no universe file in the fixture: empty, never invented
    assert c.get("/v3/no/such/view").status_code == 404
    assert c.get("/history?days=7").json()["points"] == []
    for name in views.ROUTES:
        assert c.get(f"/v3/{name}").status_code == 200, name


def test_india_ask_is_grounded_threaded_and_honest_offline(lake, monkeypatch):
    from jarvis.india import ask as ia, views

    monkeypatch.setattr(views, "DATA", lake)
    monkeypatch.setattr(views, "REG", lake / "registrations")
    monkeypatch.setattr(ia, "ASK_DIR", lake / "ask")
    monkeypatch.setattr(ia, "ENV_FILE", lake / "no.env")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    r = c.post("/v3/ask", json={"text": "What did you decide?"}).json()                 # no key: the read model's own words, said so
    assert r["kind"] == "answer" and "Nifty 22,811" in r["answer"] and r["provider"] == "none" and "read model only" in r["note"]
    assert r["thread"] and r["id"] and isinstance(r["follow_ups"], list)
    th = r["thread"]
    sent = {}

    def fake_post(url, headers, body):
        sent["body"] = body
        return {"content": [{"type": "text", "text": json.dumps({"kind": "answer", "stage": "outcome", "answer": "The call was BULLISH and wrong, sir.", "breakdown": ["0 of 3"], "evidence": ["daily_call"], "follow_ups": ["Why?"]})}],
                "usage": {"input_tokens": 1000, "output_tokens": 50}}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    r2 = ia.ask("madhav", "Was the call right?", thread=th, post=fake_post)
    assert r2["answer"].startswith("The call was BULLISH") and r2["provider"] == "claude" and r2["cost_usd"] > 0
    assert "FACTS" in sent["body"]["messages"][-1]["content"] and "22811.35" in sent["body"]["messages"][-1]["content"]   # grounded on the read model
    assert sent["body"]["messages"][0]["role"] == "user" and len(sent["body"]["messages"]) == 3                               # the thread's history travels with it
    assert "no real money" in sent["body"]["system"][0]["text"].lower() or "paper only" in sent["body"]["system"][0]["text"].lower()
    r3 = ia.ask("madhav", "buy it now", thread=th, post=fake_post)
    assert "Paper only" in r3["answer"] and r3["provider"] == "rule"                                                         # no actions from chat
    msgs = c.get(f"/v3/ask/thread/{th}").json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"] * 3 and msgs[1]["answer"]
    assert c.get("/v3/ask/threads").json()["threads"][0]["thread"] == th and c.get("/v3/ask/last").json()["last"]["thread"] == th
    assert c.post("/v3/ask/rate", json={"id": r2["id"], "rating": 1}).json()["ok"] is True
    assert "You: Was the call right?" in c.get(f"/v3/ask/thread/{th}/export").json()["text"]
    assert c.post(f"/v3/ask/thread/{th}/delete").json()["ok"] and c.get("/v3/ask/threads").json()["threads"] == []
