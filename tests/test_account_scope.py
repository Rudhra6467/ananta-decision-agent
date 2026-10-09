"""Build plan Phase 1 (2026-10-08): each account is its own. A visitor's personal lookups read only their account; Ananta's
research is labelled and never handed over as theirs; the owner's profile says 'sir'; trades carry stamps."""
import tempfile
from pathlib import Path

from jarvis.service import account, books, briefs, core
from jarvis.service.ask import Lookups
from jarvis.service.manual import Manual


def _j(d, db="jarvis.sqlite"):
    return core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                       now=lambda: 1_800_000_000, db_file=db)


def test_visitor_lookups_read_only_their_account():
    d = Path(tempfile.mkdtemp())
    g = _j(d, "jarvis_guest_asha_x_com.sqlite")
    account.update(g, {"name": "Asha", "coins": ["SOL"], "tour_done": True, "capital": 2000, "experience": "never", "risk": "careful"})
    L = Lookups(g, guest=True)
    p = L.call("portfolio", {})
    assert "VISITOR'S OWN" in p["whose"] and p["capital"] == 2000 and p["risk"] == "careful"
    assert "error" in L.call("report", {})                              # Madhav's reports are not theirs
    assert "not in this visitor's account" in L.call("trade", {"id": "BCH-1791504000-E6-86"})["error"]
    m = L.call("mandate", {})
    assert m["risk"] == "careful" and "no mandate of its own" in m["note"]
    b = briefs.briefs_for(g, "portfolio", guest=True)["PORTFOLIO_BRIEF"]
    assert "VISITOR'S OWN" in b["whose"] and b["level"] == "beginner"
    note = account.prompt_note(g, "Asha")
    assert "never traded" in note and "0.5%" in note and "plain words" in note


def test_owner_profile_and_settings():
    d = Path(tempfile.mkdtemp())
    j = _j(d)
    p = account.owner_profile(j)
    assert p["call"] == "sir" and p["voice"] == "Deep" and p["tz"] == "America/Toronto"
    account.update(j, {"theme": "bat", "tz": "Asia/Kolkata"})
    p = account.owner_profile(j)
    assert p["theme"] == "bat" and p["tz"] == "Asia/Kolkata"
    try:
        account.update(j, {"tz": "Mars/Base"})
    except ValueError:
        pass
    else:
        raise AssertionError("bad time zone accepted")


def test_books_stamp_manual_trades_with_initials():
    assert books.initials("Vamsi Madhav") == "VM" and books.initials("Mahi") == "MA"
    d = Path(tempfile.mkdtemp())
    g = _j(d, "jarvis_guest_asha_x_com.sqlite")
    account.update(g, {"capital": 2000})
    Manual(g.db, g.now).execute("guest:asha@x.com", {"side": "buy", "coin": "SOL", "usd": 100}, {"SOL": 120.0}, trigger="direct")
    g.prices = lambda: {"SOL": 126.0}
    v = books.view(g, "Asha Rao", owner=False)
    assert v["summary"]["open_count"] == 1 and v["trades"][0]["stamp"] == {"who": "you", "label": "AR", "source": "manual"}
    assert v["books"] == [{"name": "Your trades", "value": v["books"][0]["value"], "start": 2000}]


def test_sign_in_with_a_name_or_a_gmail_without_dots():
    d = Path(tempfile.mkdtemp())
    j = core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                    now=lambda: 1_800_000_000)
    inv = j.invite("Mahi")
    j.join(inv["code"], "Mahi K", "mahikittu@gmail.com", "guest pass 123")
    for typed in ("mahikittu@gmail.com", "Mahi.Kittu@gmail.com", "mahikittu+ananta@gmail.com", "mahi k"):
        assert j.check(j.login(typed, "guest pass 123")) == "guest:mahikittu@gmail.com", typed
    try:
        j.login("nobody", "x")
    except core.AuthError as exc:
        assert "email you joined with" in str(exc)
