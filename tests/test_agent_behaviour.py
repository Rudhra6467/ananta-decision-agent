"""Build plan 3.7-4.5 (2026-10-09): spoken chips act like taps, a one-word "why" explains the last answer, risk comfort filters
the setup kinds (and says so only when it did), a visitor can pause Ananta and switch auto mode, capital goes to $10,000, and
concepts are introduced once each."""
import json
import tempfile
from pathlib import Path

from jarvis.service import account, ask, concepts, core, watches


def _g(clock):
    d = Path(tempfile.mkdtemp())
    g = core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                    now=lambda: clock["t"], db_file="jarvis_guest_bo_x_com.sqlite")
    g.prices = lambda: {"BTC": 100.0, "SOL": 50.0}
    account.update(g, {"name": "Bo", "coins": ["BTC", "SOL"], "tour_done": True, "capital": 6000, "risk": "careful"})
    return g


def test_spoken_chip_words_act_like_taps():
    ch = {"next": {"label": "Pull the BTC setup", "ask": "Show me the BTC setup", "say": "pull BTC"},
          "follow": ["What are you watching right now?", "Rate my open positions"]}
    assert ask.spoken_chip("Yes please.", ch) == "Show me the BTC setup"
    assert ask.spoken_chip("Ananta, yes", ch) == "Show me the BTC setup"
    assert ask.spoken_chip("pull BTC", ch) == "Show me the BTC setup"
    assert ask.spoken_chip("what are you watching right now", ch) == "What are you watching right now?"
    assert ask.spoken_chip("what is the weather like", ch) is None
    assert ask.spoken_chip("yes", None) is None


def test_why_alone_is_a_question():
    for t in ("why", "Why?", "but why", "how come", "why not?"):
        assert ask.WHY.match(t), t
    assert not ask.WHY.match("why did bitcoin drop today")


def test_capital_up_to_ten_thousand():
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    assert account.profile(g.db)["capital"] == 6000
    for bad in (500, 6500, 11000):
        try:
            account.update(g, {"capital": bad})
        except ValueError:
            continue
        raise AssertionError(f"capital {bad} was accepted")


def test_visitor_pause_and_auto_mode():
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    w = watches.create(g, ["BTC"], mode="ask")
    account.update(g, {"auto": True})
    assert watches.get(g, w["id"])["mode"] == "auto"
    account.update(g, {"auto": False})
    assert watches.get(g, w["id"])["mode"] == "ask"
    account.update(g, {"paused": True})
    gates = {k: {"status": "PASS", "why": "x", "values": {"stop": 95.0}} for k in ("REGIME", "TREND", "LOCATION", "INVALIDATION")}
    snap = {"BTC": {"chain": {"price": 100.0, "summary": "BTC ready", "observations": {"zone": {}}}, "gates": gates, "market": {"price": 100.0}}}
    assert watches.check_account(g, snap) == []                 # paused: no watch acts
    assert account.me(g)["profile"]["paused"] is True


def test_careful_risk_filters_kinds_and_says_so_only_then():
    ks, filtered = watches.kinds_for("balanced")
    assert filtered == []
    ks2, filtered2 = watches.kinds_for("careful")
    assert all(k["evidence"] == "supported" for k in ks2)
    assert set(filtered2) == {k["name"] for k in ks if k not in ks2}


def test_concepts_once_each():
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    assert concepts.due(g) is None or concepts.due(g)["id"] in concepts.CONCEPTS
    from jarvis.service.manual import Manual
    Manual(g.db, g.now).execute("bo", {"side": "buy", "coin": "BTC", "usd": 100}, g.prices(), trigger="owner")
    c = concepts.due(g)
    assert c and c["id"] == "monitoring"
    concepts.seen(g, "monitoring")
    c2 = concepts.due(g)
    assert c2 is None or c2["id"] != "monitoring"
    assert json.loads(g.db.execute("SELECT v FROM visitor_profile WHERE k='concepts_seen'").fetchone()[0]) == ["monitoring"]
