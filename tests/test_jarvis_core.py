"""Jarvis service core: owner-only login with lockout, tokens, reading the Agent's data, audited actions."""
import tempfile
import time
from pathlib import Path

from jarvis.service import core


class FakeHands:
    def __init__(self):
        self.kill = False

    def kill_switch_on(self):
        return self.kill


def _j(d, clock):
    return core.Jarvis(d, owner_email="Owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                       hands=FakeHands(), now=lambda: clock["t"])


def test_login_lockout_and_tokens():
    d = Path(tempfile.mkdtemp())
    clock = {"t": 1_800_000_000}
    j = _j(d, clock)
    tok = j.login("owner@x.com", "correct horse 1")
    assert j.check(tok) == "owner@x.com"
    for _ in range(5):
        try:
            j.login("owner@x.com", "wrong")
        except core.AuthError:
            pass
    try:
        j.login("owner@x.com", "correct horse 1")
    except core.AuthError as e:
        assert "too many" in str(e)
    else:
        raise AssertionError("must lock after 5 failures")
    clock["t"] += 16 * 60
    j.login("owner@x.com", "correct horse 1")          # the lock lifts
    try:
        j.check(tok[:-2] + "xx")
    except core.AuthError:
        pass
    else:
        raise AssertionError("tampered token accepted")
    clock["t"] += 13 * 3600
    try:
        j.check(tok)
    except core.AuthError as e:
        assert "expired" in str(e)
    try:
        core.Jarvis(d, owner_email="a", password_hash="x", secret="short")
    except ValueError:
        pass
    else:
        raise AssertionError("weak secret accepted")


def test_reads_agent_data_and_audits_actions():
    from tests.test_explorer_live import _advance, _mk

    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 4 * 24 * 2)                     # two days: Explorer steps + portfolio decisions
    j = core.Jarvis(d, owner_email="o@x.com", password_hash=core.hash_password("pw pw pw pw 1"), secret="k" * 40,
                    hands=FakeHands(), now=lambda: clock["now"])
    t = j.today()
    assert t["paper_only"] and t["explorer"]["equity"] > 0 and t["portfolio"]["mode"] == "SUGGEST"
    p = j.portfolio()
    assert p["ratings"] and {r["rating"] for r in p["ratings"]} <= {"STRONG", "OK", "WEAK", "OUT"}
    e = j.evidence()
    assert "open_trades" in e and "recent_closed" in e
    s = j.safety()
    assert s["kill_switch_on"] is False and s["hands_reachable"]
    try:
        j.set_mode("o@x.com", "auto", confirm=False)
    except core.ConfirmRequired:
        pass
    else:
        raise AssertionError("mode change without confirmation")
    if p["pending"]:
        fills = j.approve("o@x.com", "all")
        assert isinstance(fills, list) and not j.portfolio()["pending"]
    assert j.set_mode("o@x.com", "auto", confirm=True) == "AUTO"
    j.register_push("o@x.com", "ExponentPushToken[abc]", "iPhone")
    assert j.push_tokens() == ["ExponentPushToken[abc]"]
    snap = j.record_snapshot()
    assert snap and snap["explorer"] > 0 and j.history(1)["points"]
    c = j.coin("BTC")
    assert len(c["daily"]) > 20 and {"c", "ema20", "ema50"} <= set(c["daily"][-1]) and c["price"]
    assert "by_setup" in j.evidence() or j.evidence()["recent_closed"] == []
    try:
        j.coin("NOPE")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown coin accepted")
    actions = [a["action"] for a in j.safety()["recent_actions"]]
    assert "portfolio.mode" in actions and "push.register" in actions


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)


def test_visitor_accounts_invite_join_remove_and_per_account_lockout():
    """Madhav, 2026-10-06: one main account; visitors join with a one-time invite link, choose their own name and password,
    and can be removed (sign-in stops at once). A visitor's wrong passwords never lock the owner out."""
    d = Path(tempfile.mkdtemp())
    clock = {"t": 1_800_000_000}
    j = _j(d, clock)
    inv = j.invite("Asha")
    assert j.invite_info(inv["code"])["name"] == "Asha"
    tok = j.join(inv["code"], "Asha K", "Asha@Example.com", "guest pass 123")
    assert j.check(tok) == "guest:asha@example.com" and j.name_of("guest:asha@example.com") == "Asha K"
    for bad in (lambda: j.join(inv["code"], "X", "x@y.com", "another pass 1"),       # one use only
                lambda: j.invite_info("nope")):
        try:
            bad()
        except core.AuthError:
            pass
        else:
            raise AssertionError("invite reused or unknown code accepted")
    try:
        j.join(j.invite()["code"], "Owner", "owner@x.com", "whatever 123")             # nobody can take the owner's email
    except ValueError:
        pass
    else:
        raise AssertionError("owner email taken by a visitor")
    assert j.login("asha@example.com", "guest pass 123")
    for _ in range(6):
        try:
            j.login("asha@example.com", "wrong")
        except core.AuthError:
            pass
    assert j.check(j.login("owner@x.com", "correct horse 1")) == "owner@x.com"       # the owner is not locked out
    p = j.people()
    assert p["owner"]["email"] == "owner@x.com" and [v["name"] for v in p["visitors"]] == ["Asha K"]
    assert j.remove_person("asha@example.com")
    try:
        j.check(tok)
    except core.AuthError as e:
        assert "removed" in str(e)
    else:
        raise AssertionError("a removed visitor's token still works")
    clock["t"] += 8 * 86400
    try:
        j.invite_info(j.people()["invites"][0]["code"] if j.people()["invites"] else j.invite(days=7)["code"])
    except core.AuthError:
        pass
