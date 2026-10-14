"""Build plan 1.7: reaching an account when the app is closed (web push to its devices; email only when set up and asked for)."""
import tempfile
from pathlib import Path

import pywebpush

from jarvis.service import account, core, notify


def _g():
    d = Path(tempfile.mkdtemp())
    return core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                       now=lambda: 1_800_000_000, db_file="jarvis_guest_lee_x_com.sqlite")


def test_subscribe_and_push_to_each_device(monkeypatch, tmp_path):
    monkeypatch.setattr(notify, "KEYS", tmp_path)
    monkeypatch.setattr(notify, "PRIV", tmp_path / "p.pem")
    monkeypatch.setattr(notify, "PUB", tmp_path / "p.txt")
    g = _g()
    try:
        notify.subscribe(g, {"endpoint": "http://not-secure"})
    except ValueError:
        pass
    else:
        raise AssertionError("a bad subscription was stored")
    sub = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "x", "auth": "y"}}
    assert notify.subscribe(g, sub)["devices"] == 1
    sent = []
    monkeypatch.setattr(pywebpush, "webpush", lambda s, data, **k: sent.append((s["endpoint"], data)))
    assert notify.web_push(g, "BTC: your watch fired", "waiting for your yes") == 1
    assert sent and "your watch fired" in sent[0][1]
    assert len(notify.public_key()) > 40


def test_email_only_when_set_up_and_asked(monkeypatch):
    monkeypatch.delenv("JARVIS_SMTP_URL", raising=False)
    g = _g()
    account.update(g, {"name": "Lee"})
    assert notify.email_ready() is False
    assert notify.notify(g, "t", "b", email="lee@x.com")["email"] is False
