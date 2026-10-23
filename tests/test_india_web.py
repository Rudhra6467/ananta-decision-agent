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


def test_india_voice_routes_use_the_local_voice_server(lake, monkeypatch):
    from jarvis.india import ask as ia, views, voice as iv

    monkeypatch.setattr(views, "DATA", lake)
    monkeypatch.setattr(views, "REG", lake / "registrations")
    monkeypatch.setattr(ia, "ASK_DIR", lake / "ask")
    monkeypatch.setattr(ia, "ENV_FILE", lake / "no.env")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls = []

    def fake_post(url, json=None, timeout=0):
        calls.append((url, json))

        class R:
            def json(self):
                if url.endswith("/stt"):
                    return {"text": "what did you decide", "ms": 10}
                return {"audio_b64": "AAAA", "mime": "audio/mpeg", "offsets": [0.0], "duration": 1.5, "ms": 20}
        return R()

    monkeypatch.setattr(iv.requests, "post", fake_post)
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    assert c.post("/v3/voice/transcribe", json={"audio_b64": "x", "mime": "audio/webm"}).json()["text"] == "what did you decide"
    t = c.post("/india/v3/voice/turn", json={"audio_b64": "x", "mime": "audio/webm"}).json()
    assert t["heard"] == "what did you decide" and "Nifty 22,811" in t["answer"] and t["thread"]
    a = c.post("/v3/voice/answer", json={"sentences": ["Nifty is down. The call was wrong."], "voice": "Calm", "speed": 1.0}).json()
    assert a["id"] and a["duration"] == 1.5 and a["voice"] == iv.INDIA_VOICE and calls[-1][1]["voice"] == iv.INDIA_VOICE and len(calls[-1][1]["sentences"]) == 2
    assert c.get(f"/v3/voice/answer/{a['id']}").json()["id"] == a["id"]
    au = c.get(f"/v3/voice/answer/{a['id']}/audio")
    assert au.status_code == 200 and au.headers["content-type"].startswith("audio/mpeg") and au.content == b"\x00\x00\x00"
    assert c.get("/v3/voice/answer/nope").status_code == 404
    p = c.post("/v3/voice/prepare", json={"sentences": ["One. Two."]}).json()
    assert len(p["ids"]) == 2 and c.get(f"/v3/voice/clip/{p['ids'][0]}").status_code == 200
    assert c.post("/v3/voice/ui_result", json={"answer_id": "x"}).json()["ok"] is True


def test_india_ask_fix_flow_files_offers_and_queues_by_words(lake, monkeypatch):
    from jarvis.india import ask as ia, views

    monkeypatch.setattr(views, "DATA", lake)
    monkeypatch.setattr(views, "REG", lake / "registrations")
    monkeypatch.setattr(ia, "ASK_DIR", lake / "ask")
    sent = []

    class R:
        def __init__(self, j):
            self._j = j

        def json(self):
            return self._j

    def fpost(url, body):
        sent.append((url, body))
        if url.endswith("/v3/flags"):
            return R({"num": 83, "diagnosis": "The Options card shows a stale plan.", "options": [{"title": "Refresh the plan every minute", "lane": "SAFE"}, {"title": "Change the plan's sizing", "lane": "DECISION"}]})
        return R({"state": "queued"})

    def fget(url):
        return R({"flags": [{"num": 83, "state": "queued", "market": "india", "text": "[Indian market · Home] the options card is stale"}]})

    th = "t1"
    r = ia.ask("madhav", "the options card on home is not working, the plan is stale", thread=th, token="tok", flag_post=fpost, flag_get=fget)
    assert r["provider"] == "rule" and "request number 83" in r["answer"] and r["follow_ups"][0].startswith("Fix 1:") and sent[0][1]["market"] == "india"
    r2 = ia.ask("madhav", "the first", thread=th, token="tok", flag_post=fpost, flag_get=fget)
    assert "queued" in r2["answer"] and sent[-1][0].endswith("/v3/flags/83/choose") and sent[-1][1]["option"] == 0
    r3 = ia.ask("madhav", "what happened to my flag?", thread=th, token="tok", flag_post=fpost, flag_get=fget)
    assert "request 83: queued" in r3["answer"]
    assert ia.fix_flow("what did you decide?", th, "tok", None, post=fpost, get=fget) is None          # an ordinary question goes to the model
    assert ia.fix_flow("fix it", th, None, None) is None                                                  # no token: nothing is filed


def _plan(tmp):
    d = tmp / "paper"
    d.mkdir(exist_ok=True)
    (d / "allocation_view.json").write_text(json.dumps({
        "mode": "advisory", "day": "2026-10-22", "headline": "Advisory: options fixed at 50,000", "sleeves": {"now": {"stocks": 100, "options": 50, "cash": 1}}, "paper": True,
        "holdings": [{"rank": 1, "symbol": "TATAPOWER", "grade": "B", "score": 56, "action": "HOLD", "value_inr": 27573, "weight_pct": 24.8, "pnl_pct": 27.0, "suggest_inr": 0, "why": "w", "wrong_if": "x"}],
        "suggestions": [{"symbol": "JIOFIN", "action": "REDUCE"}], "moves": [{"kind": "sleeve", "from": "options", "to": "cash", "inr": 16300, "why": "w"}], "moves_applied": False, "watch": [{"what": "k"}]}))


def test_allocation_plan_holdings_are_the_owners_only(lake, monkeypatch):
    from jarvis.india import views
    monkeypatch.setattr(views, "DATA", lake)
    _plan(lake)
    full = views.allocation_plan(full=True)
    assert full["holdings"][0]["symbol"] == "TATAPOWER" and full["suggestions"]
    guest = views.allocation_plan(full=False)
    assert "holdings" not in guest and "suggestions" not in guest and guest["watch"] == [] and guest["counts"]["holdings"] == 1
    assert "symbol" not in json.dumps(guest["moves"]), "a guest sees amounts only, never a name"
    assert views._allocation().get("snapshot") is None


def test_allocation_mode_by_words_is_owner_only_and_paper(lake, monkeypatch):
    from jarvis.india import ask, views
    monkeypatch.setattr(ask, "DATA", lake)
    r = ask.allocation_flow("everything is autonomous", "owner")
    assert r and "autonomous" in r["answer"] and "Nothing is sent to your broker" in r["answer"]
    assert json.loads((lake / "paper" / "allocation.json").read_text())["mode"] == "autonomous"
    r = ask.allocation_flow("go back to advisory", "owner")
    assert json.loads((lake / "paper" / "allocation.json").read_text())["mode"] == "advisory"
    assert ask.allocation_flow("what does autonomous mean?", "owner") is None, "a question is answered, not obeyed"
    assert "Only Madhav" in ask.allocation_flow("everything is autonomous", "guest:abc")["answer"]
    assert json.loads((lake / "paper" / "allocation.json").read_text())["mode"] == "advisory", "a guest changed nothing"


def test_reconstruction_card_staircase_and_filing(lake, monkeypatch):
    from jarvis.india import views
    monkeypatch.setattr(views, "DATA", lake)
    monkeypatch.setattr(views, "REG", lake / "registrations")
    rxd = lake / "paper" / "reconstruction"
    rxd.mkdir(parents=True, exist_ok=True)
    card = {"day": "2026-10-22", "rules": "rx-in-v1", "built_at": "2026-10-23T18:38:00+00:00", "headline": "2026-10-22: a card", "market": {"words": "m"}, "people": {"words": "p", "league": {"words": "l"}},
            "ananta": {"words": "a"}, "not_done": {"words": "n"}, "reviews": {"count": 0, "tags": {}},
            "findings": [{"type": "DATA_GAP", "key": "DATA_GAP:announcements", "lane": "SAFE", "state": "to_file", "words": "no announcements", "day": "2026-10-22"}]}
    (rxd / "2026-10-22.json").write_text(json.dumps(card))
    (rxd / "latest.json").write_text(json.dumps(card))
    (lake / "registrations" / "reconstruction_queue.jsonl").write_text(json.dumps(card["findings"][0]) + "\n" + json.dumps({"type": "MISS_PATTERN", "key": "MISS_PATTERN:x", "lane": "DECISION", "state": "DRAFT", "words": "q", "day": "2026-10-22"}) + "\n")
    rm = json.loads(service.READMODEL.read_text())
    rm["reconstruction"] = {"status": "ok", "headline": "2026-10-22: a card", "built_at": card["built_at"], "league_words": "l", "reviews": {"count": 0}, "findings": card["findings"],
                            "staircase": {"words": "Nothing is ADMITTED yet.", "rules": {"stock:BRK": {"step": "SHADOW", "shadow_sessions": 3, "shadow_bar": 20, "beats": 2, "beats_bar": 10}}, "admitted": [], "queue": {"to_file": 1, "DRAFT": 1}}}
    service.READMODEL.write_text(json.dumps(rm))
    c = TestClient(service.app, client=("127.0.0.1", 50000))
    r = c.get("/v3/reconstruction").json()
    assert r["ready"] and r["headline"] == "2026-10-22: a card" and r["findings"][0]["lane"] == "SAFE" and r["cards"] == 1
    ev = c.get("/v3/evidence/live").json()["rebuild"]
    assert ev["nightly"]["runs"] == 1 and ev["chain"][0]["step"] == "SHADOW" and ev["findings"][0]["type"] == "DATA_GAP"
    col = c.get("/v3/evidence/collected").json()
    assert col["shop"]["running"][0]["status"] == "SHADOW" and {w["status"] for w in col["shop"]["waiting"]} == {"to_file", "DRAFT"} and col["shop"]["done"] == []
    assert col["forwarded"][-1]["id"] == "DATA_GAP:announcements" and "filing tonight" in col["forwarded"][-1]["question"]
    q = c.get("/v3/reconstruction/queue").json()
    assert len(q["rows"]) == 2 and q["safe_per_night"] == 3
    f = c.post("/v3/reconstruction/filed", json={"key": "DATA_GAP:announcements", "num": 41, "day": "2026-10-22"}).json()
    assert f["num"] == 41 and (rxd / "forwarded.jsonl").exists()
    q = c.get("/v3/reconstruction/queue").json()
    assert next(x for x in q["rows"] if x["key"] == "DATA_GAP:announcements")["state"] == "filed"
    col = c.get("/v3/evidence/collected").json()
    assert "#41" in col["forwarded"][-1]["question"]
