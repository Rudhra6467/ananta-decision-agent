"""Who is listening (Madhav, Oct 11): brutal truth for Madhav; honest and hopeful during a showcase on his account; approved options
for visitors; Indian-market knowledge for a visitor in India."""
import json
import tempfile
import time
from pathlib import Path

from jarvis.service import account, ask, core


def _j(email="owner@x.com", db="jarvis.sqlite", t=None):
    d = Path(tempfile.mkdtemp())
    t = t or time.time()
    return core.Jarvis(d, owner_email=email, password_hash=core.hash_password("correct horse 1"), secret="s" * 40, now=lambda: t, db_file=db)


def test_owner_showcase_then_brutal(monkeypatch):
    cfg = json.loads((Path(core.docs_dir(".")) / "knowledge" / "audience.json").read_text())
    until = time.mktime(time.strptime(cfg["showcase_until"], "%Y-%m-%d"))
    assert "HONEST AND HOPEFUL" in ask._audience(_j(t=until - 86400), "owner")
    assert "MARKETS PLAN" in ask._audience(_j(t=until - 86400), "owner")
    assert "BRUTAL TRUTH" in ask._audience(_j(t=until + 3 * 86400), "owner")


def test_guest_tone_and_india():
    g = _j(db="jarvis_guest_kim_x_com.sqlite")
    a = ask._audience(g, "guest:kim@x.com")
    assert "approved" in a and "BRUTAL" not in a and "This visitor is in India" not in a
    account.update(g, {"tz": "Asia/Kolkata"}, "kim@x.com")
    a = ask._audience(g, "guest:kim@x.com")
    assert "This visitor is in India" in a and "Nifty 50" in a
