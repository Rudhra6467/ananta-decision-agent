"""Phone notes through Apple's push (Madhav made the Apple push key on 10 Nov, 18:05 Toronto): every phone note that goes
to ntfy also goes to the Ananta app on the owner's iPhone, through Expo's push service. No real network in these tests."""
import json
from pathlib import Path

import pytest

from jarvis.service import core
from src.intelligence import paper_watch as w

TOKEN = "ExponentPushToken[test-only-token]"


class _Resp:
    def __init__(self, data):
        self.data = data

    def read(self):
        return json.dumps(self.data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def phone(tmp_path, monkeypatch):
    f = tmp_path / "expo_push_tokens.json"
    f.write_text(json.dumps([TOKEN]))
    monkeypatch.setenv("ANANTA_APPLE_PUSH", "1")
    monkeypatch.setenv("ANANTA_EXPO_TOKENS", str(f))
    monkeypatch.setattr(w, "APPLE_LOG", tmp_path / "apple_push.jsonl")
    sent = []

    def urlopen(req, timeout=0):
        sent.append((req.full_url, json.loads(req.data.decode())))
        return _Resp({"data": [{"status": "ok", "id": "x"}]})

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return sent, tmp_path


def test_a_note_reaches_the_app(phone):
    sent, tmp = phone
    assert w.apple_push("Ananta's night test", "Asked 5, marked 5.", level="EVENT") == "sent"
    url, msgs = sent[0]
    assert url == "https://exp.host/--/api/v2/push/send" and msgs[0]["to"] == TOKEN and msgs[0]["title"] == "Ananta's night test"
    assert json.loads((tmp / "apple_push.jsonl").read_text().splitlines()[-1])["result"] == "sent"


def test_the_phone_path_sends_to_the_app_even_without_ntfy(phone, monkeypatch):
    sent, _ = phone
    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "")
    assert w.push_phone("Pre-open · 11-11", "No change.", level="EVENT") == "sent" and len(sent) == 1
    assert w.push_phone("routine", "x", level="INFO") == "off" and len(sent) == 1        # routine noise stays off the phone


def test_off_without_a_phone_or_in_tests(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANTA_APPLE_PUSH", "1")
    monkeypatch.setenv("ANANTA_EXPO_TOKENS", str(tmp_path / "none.json"))
    assert w.apple_push("t", "b") == "off"
    monkeypatch.setenv("ANANTA_APPLE_PUSH", "0")
    assert w.apple_push("t", "b") == "off"


def test_a_failure_is_said_and_never_raised(phone, monkeypatch):
    def broken(req, timeout=0):
        raise OSError("no network")

    monkeypatch.setattr("urllib.request.urlopen", broken)
    assert w.apple_push("t", "b").startswith("failed: OSError")
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=0: _Resp({"data": [{"status": "error", "message": "InvalidCredentials"}]}))
    assert w.apple_push("t", "b") == "failed: InvalidCredentials"


def test_signing_in_on_the_phone_writes_the_token_file(tmp_path, monkeypatch):
    f = tmp_path / "keys" / "expo_push_tokens.json"
    monkeypatch.setenv("ANANTA_EXPO_TOKENS", str(f))
    j = core.Jarvis(tmp_path, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                    now=lambda: 1_800_000_000)
    j.register_push("owner@x.com", TOKEN, "iPhone")
    assert json.loads(f.read_text()) == [TOKEN] and oct(f.stat().st_mode & 0o777) == "0o600"
    with pytest.raises(ValueError):
        j.register_push("owner@x.com", "not-a-token", "iPhone")
    assert Path(f).exists()
