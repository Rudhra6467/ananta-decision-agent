"""Build plan 1.4-1.8 (2026-10-08): watches that act for an account, approvals that expire, manual positions watched but never
sold by Ananta, and the account's own activity log ("what changed since this morning")."""
import tempfile
from pathlib import Path

from jarvis.service import account, core, watches
from jarvis.service.mandate import Mandate
from jarvis.service.manual import Manual


def _g(clock):
    d = Path(tempfile.mkdtemp())
    g = core.Jarvis(d, owner_email="owner@x.com", password_hash=core.hash_password("correct horse 1"), secret="s" * 40,
                    now=lambda: clock["t"], db_file="jarvis_guest_asha_x_com.sqlite")
    g.prices = lambda: {"BTC": 100.0, "SOL": 50.0}
    account.update(g, {"name": "Asha", "coins": ["BTC", "SOL"], "tour_done": True, "capital": 2000, "risk": "balanced"})
    g.db.execute("UPDATE visitor_profile SET v='10000' WHERE k='capital'")      # $10,000 arrives with step 5.4
    g.db.commit()
    return g


def _snap(fire: bool, trend: bool = True, regime: bool = True):
    def gate(ok, **v):
        return {"status": "PASS" if ok else "FAIL", "why": "x", "values": v}
    gates = {"REGIME": gate(regime), "TREND": gate(trend), "LOCATION": gate(fire), "INVALIDATION": gate(True, stop=95.0)}
    btc = {"chain": {"price": 100.0, "summary": "BTC: candidate", "observations": {"zone": {"next_resistance_pct": 6.0}}},
           "gates": gates, "market": {"price": 100.0, "closest": {"name": "Pullback", "met": 2, "of": 4, "missing": []}}}
    return {"BTC": btc}


def test_watch_fires_and_asks_first_with_expiry():
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    try:
        watches.create(g, ["BTC"], kind="volume_breakout")           # not an evidence-allowed kind
    except ValueError as exc:
        assert "evidence" in str(exc)
    else:
        raise AssertionError("a disallowed kind was accepted")
    w = watches.create(g, ["BTC"], mode="ask")
    watches.check_account(g, _snap(fire=False))
    assert watches.get(g, w["id"])["state"] == "CLOSE"                 # 3 of 4: location missing
    watches.check_account(g, _snap(fire=True))
    assert watches.get(g, w["id"])["state"] == "FIRED"
    p = Mandate(g.db, g.now).pending()
    assert len(p) == 1 and p[0]["card"]["found"].startswith("Bitcoin") and p[0]["payload"]["stop"] == 95.0
    # balanced = 1% of $10,000 at a 5% stop = $2,000, under the cap of a quarter of capital ($2,500)
    assert p[0]["payload"]["usd"] == 2000.0
    clock["t"] += 31 * 60                                              # D3: 30 minutes later it is gone
    assert Mandate(g.db, g.now).pending() == []
    acts = watches.activity(g)
    assert any(a["kind"] == "ask" for a in acts) and any(a["kind"] == "close" for a in acts)


def test_auto_mode_buys_in_their_book_and_logs_a_card():
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    watches.create(g, ["BTC"], mode="auto")
    watches.check_account(g, _snap(fire=True))
    st = Manual(g.db, g.now).state(g.prices())
    assert [p["coin"] for p in st["positions"]] == ["BTC"]
    a = watches.activity(g)[0]
    assert a["kind"] == "trade" and set(a["card"]) == {"found", "why", "wrong_if", "doing"}
    s = watches.state(g)
    assert s["positions"] and any(x["text"] == "Monitoring 1 position" for x in s["lines"])


def test_manual_positions_get_one_warning_and_an_exit_card_never_a_sale():
    clock = {"t": 1_800_000_000}
    g = _g(clock)
    Manual(g.db, g.now).execute("guest:asha@x.com", {"side": "buy", "coin": "BTC", "usd": 500}, {"BTC": 100.0}, trigger="direct")
    g.prices = lambda: {"BTC": 90.0, "SOL": 50.0}
    w1 = watches.monitor_manual(g, _snap(fire=False, trend=False, regime=False))
    w2 = watches.monitor_manual(g, _snap(fire=False, trend=False, regime=False))
    assert len(w1) == 3 and w2 == []                                   # deep, risk-off, trend: once each
    assert Manual(g.db, g.now).state(g.prices())["positions"]         # still held: Ananta never sells it
    assert all(p["payload"]["side"] == "sell" for p in Mandate(g.db, g.now).pending())
