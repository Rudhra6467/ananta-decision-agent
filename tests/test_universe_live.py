"""The whole-universe engine (engine plan U1-U6, Universe Rule v2): registry, feed, universe watches, the brain's ranking."""
import time
from pathlib import Path

import pytest


class J:
    def __init__(self, d, now=None):
        import sqlite3

        from jarvis.service.core import SafeDB

        self.dir = Path(d)
        self.db = SafeDB(sqlite3.connect(str(self.dir / "jarvis.sqlite"), check_same_thread=False))
        self._now = now or time.time()

    def now(self):
        return self._now


def _fake_get():
    def get(url, *a, **k):
        if "exchangeInfo" in url:
            syms = ["BTC", "ETH", "USDC", "BTCUP", "WBTC", "XAUT", "NEWCOIN", "AAPLB", "币安"]
            return {"symbols": [{"symbol": s + "USDT", "baseAsset": s, "quoteAsset": "USDT", "status": "TRADING"} for s in syms]
                    + [{"symbol": "ETHBTC", "baseAsset": "ETH", "quoteAsset": "BTC", "status": "TRADING"}]}
        if "get-products" in url:
            return {"data": [{"b": "AAPLB", "q": "USDT", "an": "Apple (bStocks)", "tags": ["bStocks"]},
                             {"b": "BTC", "q": "USDT", "an": "Bitcoin", "tags": []}]}
        if "ndax" in url:
            return [{"Product1Symbol": "BTC", "Product2Symbol": "CAD", "IsDisable": False}]
        if "kraken" in url:
            return {"result": {"XXBTZUSD": {"wsname": "XBT/USD"}, "XETHZUSD": {"wsname": "ETH/USD"}}}
        if "bookTicker" in url:
            return [{"symbol": "ETHUSDT", "bidPrice": "99.9", "askPrice": "100.1"}]
        raise AssertionError(url)
    return get


def test_registry_membership_tiers_and_flags(tmp_path):
    from jarvis.service import registry

    j = J(tmp_path)
    qv = {"BTC": [(i, 50e6) for i in range(40)], "ETH": [(i, 5e6) for i in range(40)], "NEWCOIN": [(i, 9e9) for i in range(5)]}
    r = registry.build(j, get=_fake_get(), daily_qv=lambda c: qv.get(c, []))
    reg = registry.load(j)
    assert set(registry.members(j)) == {"BTC", "ETH", "NEWCOIN"}          # stablecoin, leveraged, wrapped, gold, shares, odd names out
    assert reg["coins"]["BTC"]["tier"] == "A" and reg["coins"]["ETH"]["tier"] == "B"
    assert reg["coins"]["NEWCOIN"]["tier"] == "C"                          # under 30 days of history is never judged
    assert reg["coins"]["BTC"]["ndax"] and reg["coins"]["BTC"]["kraken"] and reg["coins"]["ETH"]["kraken"] and not reg["coins"]["ETH"]["ndax"]
    assert "LAB10" in reg["coins"]["BTC"]["groups"] and r["counts"]["listed"] == 3
    assert registry.members(j, "AB") == ["BTC", "ETH"]


def test_registry_marks_a_coin_that_stops_trading(tmp_path):
    from jarvis.service import registry

    j = J(tmp_path)
    registry.build(j, get=_fake_get())
    g = _fake_get()

    def gone(url, *a, **k):
        out = g(url)
        if "exchangeInfo" in url:
            out["symbols"] = [s for s in out["symbols"] if s["baseAsset"] != "NEWCOIN"]
        return out
    registry.build(j, get=gone)
    assert registry.load(j)["coins"]["NEWCOIN"]["status"] == "DELISTED"
    assert "NEWCOIN" not in registry.members(j)


def test_universe_costs_follow_rule_v2():
    from jarvis.service import registry, watch_engine

    reg = {"coins": {"ETH": {"tier": "B", "ndax": False, "binance_half_spread": 0.0001},
                     "ZZZ": {"tier": "C", "ndax": True, "binance_half_spread": 0.01}}}
    assert registry.cost("ZZZ", reg) == pytest.approx(0.0020 + 0.03)       # three times the measured spread beats the tier floor
    assert registry.cost("SOL", reg) < 0.006                                 # the 10 keep their measured NDAX costs
    old = registry._CACHE.get("reg")
    registry._CACHE["reg"] = reg
    try:
        assert watch_engine._cost("ZZZ", "H07-UC") == pytest.approx(0.032)
        assert watch_engine._cost("ZZZ", "H07-T30") == pytest.approx(0.006)  # the 30-coin tier keeps review #15's cost (control)
    finally:
        registry._CACHE["reg"] = old


def test_lab10_lists_never_drift():
    """The 10 are one named group: every module that still names them must agree with the registry's."""
    from jarvis.service import account, pricebook, registry
    from src.intelligence import explorer_engine as xe

    ten = set(registry.lab10())
    assert len(ten) == 10
    for lst in (account.COINS, pricebook.COINS, xe.COINS):
        assert set(lst) == ten


def test_feed_builds_higher_timeframes_from_5m(tmp_path):
    from jarvis.service import feed

    j = J(tmp_path)
    con = feed._con(j)
    t0 = 1_800_000_000 // 3600 * 3600
    rows = [("X", t0 + 300 * k, 10 + k, 11 + k, 9 + k, 10.5 + k, 1.0) for k in range(24)]   # two full hours
    con.executemany("INSERT INTO m5 VALUES (?,?,?,?,?,?,?)", rows)
    con.commit()
    h = feed.bars(j, "X", "1h", 5)
    assert len(h) == 2
    assert h[0] == (t0, 10, 22, 9, 21.5, 12.0)
    assert len(feed.bars(j, "X", "15m", 100)) == 8


def test_universe_watches_are_registered_per_tier():
    from jarvis.service import universe_watch as U
    from jarvis.service import watch_engine as W

    for t in "ABC":
        assert W.DAILY[f"H07-U{t}"]["tier"] == f"U{t}" and W.DAILY[f"RANDOM_20D-U{t}"]["kind"] == "random"
        assert f"ZONE_TOUCH-U{t}" in W.EYE
    assert U.split("M2a-G-UB") == ("M2a-G", "B") and U.split("H07-T30") is None and U.split("JARVIS") is None
    # the 10-coin run never picks them up (D7: the control group is untouched)
    assert not any(w.endswith(("-UA", "-UB", "-UC")) for w, sp in W.DAILY.items() if not sp.get("tier"))


def test_brain_ranks_evidence_and_tier(tmp_path, monkeypatch):
    from jarvis.service import brain, registry

    j = J(tmp_path)
    brain._table(j)
    registry.build(j, get=_fake_get(), daily_qv=lambda c: [(i, 50e6 if c == "BTC" else 5e6) for i in range(40)] if c != "NEWCOIN" else [])
    monkeypatch.setattr(brain, "_coin_daily", lambda jj, c: [])
    monkeypatch.setattr(brain, "_regime_now", lambda jj: "ALLOWED")
    hi, _ = brain.score(j, "ETH", "zone_entry|setup:H07-UB", {"zone_entry": {"history": "SUPPORTED"}})
    lo, _ = brain.score(j, "NEWCOIN", "zone_entry", {"zone_entry": {"history": "SUPPORTED"}})
    ex, _ = brain.score(j, "BTC", "explorer:E5", {})
    assert hi > ex >= brain.MIN_SCORE > lo                                   # tier C never reaches the AI


def test_brain_budget_paces_and_logs_unreviewed(tmp_path, monkeypatch):
    from jarvis.service import brain

    t_mid = brain._today0(J(tmp_path)) + 2 * 3600                            # 2 am Toronto: about a third of the budget unlocked
    j = J(tmp_path, now=t_mid)
    brain._table(j)
    assert brain.paced_budget(j) == pytest.approx(brain.DAILY_USD * (0.25 + 0.75 * 2 / 24), abs=1e-3)
    monkeypatch.setattr(brain, "score", lambda jj, c, t, d: (1.0, ["low"]) if c == "LOW" else (6.0, ["high"]))
    monkeypatch.setattr(brain, "can_decide", lambda jj: (True, ""))
    monkeypatch.setattr(brain, "_live_px", lambda jj, c: 1.0)
    done = []
    monkeypatch.setattr(brain, "decide", lambda jj, c, trig, call=None, push=None: done.append(c) or {"action": "PASS"})
    brain.wake(j, "LOW", "explorer:E1")
    brain.wake(j, "GOOD", "zone_entry")
    brain.process(j)
    assert done == ["GOOD"]
    st = dict(j.db.execute("SELECT coin, state FROM brain_queue").fetchall())
    assert st["LOW"].startswith("NOT_REVIEWED") and st["GOOD"] == "DONE"
    assert j.db.execute("SELECT COUNT(*) FROM brain_unreviewed").fetchone()[0] == 1


def test_ladder_needs_evidence_and_moves_one_step(tmp_path, monkeypatch):
    from jarvis.service import universe_watch as U

    j = J(tmp_path)
    board = {"watches": [{"watch": "H07-UA", "rule": "H07", "tier": "A", "verdict": "too early: 3 of 10 market days"},
                         {"watch": "H07-UC", "rule": "H07", "tier": "C", "verdict": "watched only (tier C)"}]}
    monkeypatch.setattr(U, "scoreboard", lambda jj: board)
    rows = {r["watch"]: r for r in U.ladder(j)["rows"]}
    assert rows["H07-UA"]["step"] == "EVIDENCE" and not rows["H07-UA"]["next_allowed"]
    assert rows["H07-UC"]["step"] == "SHADOW"
    with pytest.raises(ValueError):
        U.set_step(j, "H07-UA", "PROMOTED", "madhav")              # the evidence is not there yet
    board["watches"][0]["verdict"] = "ahead of random"
    board["watches"][0]["avg_usd"] = -0.5
    with pytest.raises(ValueError):
        U.set_step(j, "H07-UA", "PROMOTED", "madhav")              # ahead of random but losing money: not an edge (engine fix 4)
    board["watches"][0]["avg_usd"] = 1.2
    with pytest.raises(ValueError):
        U.set_step(j, "H07-UA", "LIVE_CANDIDATE", "madhav")        # one step at a time
    assert U.set_step(j, "H07-UA", "PROMOTED", "madhav")["to"] == "PROMOTED"
    assert U.promoted(j) == {"H07-UA"}
    board["would_be_account"] = {"beats_hurdle": False, "positive_expectancy": True}
    with pytest.raises(ValueError):
        U.set_step(j, "H07-UA", "LIVE_CANDIDATE", "madhav")        # the account has not beaten the benchmark
    board["would_be_account"] = {"beats_hurdle": True, "positive_expectancy": True}
    assert U.ladder(j)["rows"][0]["next_allowed"]
    assert U.set_step(j, "H07-UA", "EVIDENCE", "madhav")["to"] == "EVIDENCE"   # down is always allowed


def test_a_registered_version_runs_beside_its_parent(monkeypatch):
    from jarvis.service import universe_watch as U
    from jarvis.service import watch_engine as W

    monkeypatch.setattr(U, "versions", lambda: [{"rule": "H07", "version": "v2", "changes": {"rsi_exit": 50}, "since": "2026-10-09"},
                                                {"rule": "H07", "version": "bad", "changes": {"stop": 1}}])      # unknown change: refused
    U.register()
    try:
        assert W.DAILY["H07.v2-UB"]["rsi_exit"] == 50 and W.DAILY["H07.v2-UB"]["parent"] == "H07-UB"
        assert "H07.bad-UB" not in W.DAILY and "H07.v2" in U.RULES_ALL and U.split("H07.v2-UB") == ("H07.v2", "B")
    finally:
        for t in "ABC":
            W.DAILY.pop(f"H07.v2-U{t}", None)
        monkeypatch.undo()
        U.register()
