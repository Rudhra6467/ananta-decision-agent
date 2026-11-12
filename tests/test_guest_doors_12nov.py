"""The guest doors (the keen outside audit of 11-12 Nov 2026, findings G-51, G-52, G-53; open-list flag 117).

The guide promised "guests cannot see the owner's numbers". The audit found it false as built: on India a signed-in guest could read the
read model, the history, the options record, the account's value at every close and the people list, and could list, read, export and
delete Madhav's conversations; on crypto a guest could open More, Proof and Why, built from his account. A caller's own thread text was
used as a file path. And any caller on the Mac was the owner, whatever name or origin it came under. Now: a guest passes one gate that
lets through the market pages only; a thread's name is checked; a local call must name this Mac and come from Ananta's own pages."""
import types

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from jarvis.india import ask as india_ask
from jarvis.india import places as india_places
from jarvis.india import service
from jarvis.india import views as india_views
from jarvis.service import app as crypto_app

WHO = {"guest-token": "guest:visitor", "owner-token": "owner"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    def fake_me(url, headers=None, timeout=None):
        who = WHO.get((headers or {}).get("Authorization", "").removeprefix("Bearer "))
        return types.SimpleNamespace(status_code=200 if who else 401, json=lambda: {"who": who})

    monkeypatch.setattr(service.requests, "get", fake_me)
    monkeypatch.setattr(india_ask, "ASK_DIR", tmp_path)             # never the live conversations
    service._TOKENS.clear()
    return TestClient(service.app)


def _get(client, path, token):
    return client.get(path, headers={"Authorization": f"Bearer {token}"})


@pytest.mark.parametrize("path", ["/india/api/readmodel", "/india/api/brief", "/india/history", "/india/v3/ask/threads", "/india/v3/ask/last",
                                  "/india/v3/ask/stats", "/india/v3/ask/thread/abc123/export", "/india/v3/ask/thread/abc123",
                                  "/india/v3/money", "/india/v3/proof", "/india/v3/people", "/india/v3/allocation/plan",
                                  "/india/v3/chart/PORTFOLIO", "/india/v3/chart/RELIANCE", "/api/readmodel", "/v3/ask/threads"])
def test_a_guest_is_refused_everything_that_is_madhavs(client, path):
    r = _get(client, path, "guest-token")
    assert r.status_code == 403 and "Madhav's own paper account" in r.json()["detail"]


@pytest.mark.parametrize("path", ["/india/v3/ask", "/india/v3/ask/thread/abc123/delete", "/india/v3/voice/prepare", "/india/v3/allocation"])
def test_a_guest_cannot_ask_delete_or_change_anything(client, path):
    r = client.post(path, json={"text": "what is my account worth"}, headers={"Authorization": "Bearer guest-token"})
    assert r.status_code == 403


def test_a_guest_cannot_delete_a_conversation_and_the_owner_can(client, tmp_path):
    (tmp_path / "abc123.jsonl").write_text('{"role": "user", "text": "hello"}\n')
    assert client.post("/india/v3/ask/thread/abc123/delete", headers={"Authorization": "Bearer guest-token"}).status_code == 403
    assert (tmp_path / "abc123.jsonl").exists()
    assert client.post("/india/v3/ask/thread/abc123/delete", headers={"Authorization": "Bearer owner-token"}).status_code == 200
    assert not (tmp_path / "abc123.jsonl").exists()


def test_the_owners_token_still_opens_his_conversations(client):
    assert _get(client, "/india/v3/ask/threads", "owner-token").status_code == 200
    assert _get(client, "/india/v3/ask/threads", "no-such-token").status_code == 401


def test_a_guest_opens_the_three_index_pages_and_no_other_place(monkeypatch):
    for name in india_places.PLACES:
        monkeypatch.setitem(india_places.PLACES, name, lambda full=True, n=name: {"ready": True, "name": n, "full": full})
    for name in india_places.PLACES:
        out = india_views.ROUTES[f"place/{name}"](full=False)
        if name in ("nifty", "banknifty", "vix"):
            assert out == {"ready": True, "name": name, "full": False}
        else:
            assert out["ready"] is False and "Madhav's account" in out["words"], name
        assert india_views.ROUTES[f"place/{name}"](full=True)["ready"] is True          # the owner opens every place


def test_a_guest_on_crypto_cannot_open_more_proof_or_why():
    for name in ("more", "proof", "why", "home", "account", "markets", "activity", "cash", "coins"):
        out = crypto_app.place(name, "crypto", who="guest:visitor")
        assert out["ready"] is False and "Madhav's account" in out["words"], name


def test_an_empty_thread_name_is_not_a_path():
    with pytest.raises(ValueError):
        india_ask._tpath("")                                           # (the Ask gives a new conversation its own name instead)


@pytest.mark.parametrize("name", ["../paper/managed/plans", "..", "a/b", "a.b", "threads", "x" * 65, "-lead", "a b"])
def test_a_thread_name_that_is_not_a_conversations_is_refused(name, tmp_path, monkeypatch):
    monkeypatch.setattr(india_ask, "ASK_DIR", tmp_path)
    with pytest.raises(ValueError):
        india_ask._tpath(name)
    with pytest.raises(ValueError):
        india_ask.delete_thread(name)
    assert india_ask.thread_messages(name) == []                       # reading one is empty, never a path
    with pytest.raises(ValueError, match="not a conversation's name"):
        india_ask.ask("owner", "how is my account", thread=name)       # refused before anything is written
    assert list(tmp_path.glob("**/*.jsonl")) == [] and list(tmp_path.parent.glob("*.jsonl")) == []


@pytest.mark.parametrize("name", ["a1b2c3d4e5f6", "ot-trials-1", "forkh-live-q1", "audit1", "keen1731340000", "ot_map_check"])
def test_real_thread_names_still_pass(name, tmp_path, monkeypatch):
    monkeypatch.setattr(india_ask, "ASK_DIR", tmp_path)
    assert india_ask._tpath(name) == tmp_path / f"{name}.jsonl"


def test_a_bad_thread_name_from_the_owner_is_a_400_not_a_path(client):
    r = client.post("/india/v3/ask/thread/a.b/delete", headers={"Authorization": "Bearer owner-token"})
    assert r.status_code == 400


def _req(client_host="127.0.0.1", **headers):
    scope = {"type": "http", "method": "GET", "path": "/v3/place/home", "query_string": b"", "client": (client_host, 50000),
             "headers": [(k.replace("_", "-").encode(), v.encode()) for k, v in headers.items()]}
    return Request(scope)


@pytest.mark.parametrize("headers, local", [
    ({"host": "127.0.0.1:8110"}, True),                                              # curl and the scheduled jobs
    ({"host": "localhost:8110"}, True),
    ({"host": "[::1]:8110"}, True),
    ({"host": "127.0.0.1:8110", "origin": "http://127.0.0.1:8110"}, True),           # the local page's own POST
    ({"host": "127.0.0.1:8110", "origin": "http://localhost:8081"}, True),           # the app's local build
    ({"host": "127.0.0.1:8110", "origin": "https://livetrading247.com"}, True),      # Ananta's own site
    ({"host": "evil.example:8110"}, False),                                          # a page that points its own name at this Mac
    ({"host": "127.0.0.1:8110", "origin": "https://evil.example"}, False),           # a post across origins
    ({"host": "127.0.0.1:8110", "origin": "null"}, False),
    ({"host": "127.0.0.1:8110", "cf_connecting_ip": "203.0.113.9"}, False),          # it came through the tunnel
    ({"host": "127.0.0.1:8110", "x_forwarded_for": "203.0.113.9"}, False),
    ({}, False),
])
def test_only_a_call_made_on_this_mac_under_its_own_name_is_the_owner(headers, local):
    assert service._from_this_mac(_req(**headers)) is local


def test_a_call_from_another_machine_is_never_the_owner_by_address():
    assert service._from_this_mac(_req(client_host="192.168.1.20", host="127.0.0.1:8110")) is False
