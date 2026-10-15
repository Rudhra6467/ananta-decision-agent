"""Worker stage S2: the $500 backtest rerun with the cost each coin really has on NDAX (src/research/book500_s2.py). It only reports."""
import json
import sqlite3
import types

import pytest

from src.research import book500 as B
from src.research import book500_s2 as S

DAY = 86400


def _tab(rows):
    return {"days": [f"2026-10-{d:02d}" for d in range(12, 26)], "coins": [
        {"coin": c, "minutes": m, "half_spread_p75_pct": p} for c, m, p in rows]}


def test_only_a_coin_with_enough_quotes_gets_its_measured_cost():
    assumed = {"BTC": 0.0038, "SOL": 0.0049, "ZZZ": 0.006}
    cost, seen = S.measured_costs(_tab([("BTC", 20000, 0.150), ("SOL", 500, 0.9)]), assumed)
    assert cost["BTC"] == pytest.approx(0.0020 + 0.0015) and seen["BTC"]["measured"] and seen["BTC"]["s2_pct"] == 0.35
    assert cost["SOL"] == 0.0049 and not seen["SOL"]["measured"] and seen["SOL"]["minutes"] == 500          # too few quotes: the assumption stays
    assert cost["ZZZ"] == 0.006 and seen["ZZZ"]["minutes"] == 0 and "s2_pct" not in seen["ZZZ"]            # not measured at all


def test_a_coin_is_flagged_only_when_the_real_cost_erases_a_real_edge():
    run = lambda avg, n=12: {"setup_avg_pct": avg, "setup_trades": n, "setup_win_rate": 0.5}  # noqa: E731
    assert S.judge_coin(run(1.2), run(-0.1))["verdict"] == "FLAGGED"
    assert S.judge_coin(run(1.2), run(0.0))["verdict"] == "FLAGGED"                 # zero is not an edge
    assert S.judge_coin(run(1.2), run(0.8))["verdict"] == "HOLDS"
    assert S.judge_coin(run(-0.5), run(-1.5))["verdict"] == "NEVER_HAD_EDGE"
    assert S.judge_coin(run(1.2, 4), run(-0.1, 4))["verdict"] == "TOO_FEW_TRADES"   # under 5 trades nothing is judged
    assert S.judge_coin(run(None, 0), run(None, 0))["verdict"] == "TOO_FEW_TRADES"


def test_a_dearer_cost_gives_a_lower_end_value_in_the_real_backtest():
    """The cost dict is what book500.simulate charges; S2 relies on that. Two rising coins, the dial opens, the core is bought."""
    t0 = 1_600_000_000 - 1_600_000_000 % DAY
    bars = [(t0 + k * DAY, 100 + k * 0.5, 100 + k * 0.5, 100 + k * 0.5, 100 + k * 0.5, 1.0) for k in range(320)]
    C = {"BTC": B.Coin(bars), "ETH": B.Coin(bars)}
    lo = B.simulate(C, [], {}, {"BTC": 0.002, "ETH": 0.002}, t0, t0 + 400 * DAY)
    hi = B.simulate(C, [], {}, {"BTC": 0.020, "ETH": 0.020}, t0, t0 + 400 * DAY)
    assert lo["end_cad"] > hi["end_cad"] > 0 and lo["core_days_pct"] > 0


def _run_with_fakes(tmp_path, monkeypatch, request=False):
    from jarvis.service import core, ndax_spreads, registry

    j = types.SimpleNamespace(dir=str(tmp_path), db=sqlite3.connect(":memory:"), now=lambda: 1_792_000_000)
    reg = {"coins": {"BTC": {"ndax": True, "tier": "A"}, "ETH": {"ndax": True, "tier": "A"}, "SOL": {"ndax": True, "tier": "A"},
                     "ADA": {"ndax": True, "tier": "A"}, "XYZ": {"ndax": False, "tier": "A"}}}
    assumed = {"BTC": 0.0038, "ETH": 0.0029, "SOL": 0.0049, "ADA": 0.0047}
    monkeypatch.setattr(core, "from_env", lambda: j)
    monkeypatch.setattr(registry, "load", lambda j_: reg)
    monkeypatch.setattr(registry, "cost", lambda c, r=None: assumed[c])
    monkeypatch.setattr(B, "instruments", lambda get=None: {})
    monkeypatch.setattr(B, "load", lambda coins, fx: {c: object() for c in ("BTC", "ETH", "SOL", "ADA")})
    monkeypatch.setattr(B, "bench", lambda btc, cost, t0, t1: {"HOLD": {"end_cad": 600.0}})
    calls = []

    def fake_simulate(C, tier_a, inst, cost, t0, t1, **kw):
        calls.append((tuple(tier_a), dict(cost)))
        if len(tier_a) == 1:                            # a coin alone: 1.0% a trade at the assumed cost, less 2 x the extra cost per trade
            c = tier_a[0]
            return {"setup_trades": 12, "setup_win_rate": 0.5, "setup_avg_pct": round(1.0 - 200 * (cost[c] - assumed[c]), 3)}
        return {"from": "2018-01-01", "to": "2026-07-31", "end_cad": round(700 - 1000 * sum(cost.values()), 2), "return_pct": 1.0, "max_fall_pct": -5.0,
                "setup_trades": 30, "setup_win_rate": 0.5, "setup_avg_pct": 0.5, "brakes_fired": {}, "sizes_ok": True}

    monkeypatch.setattr(B, "simulate", fake_simulate)
    quotes = _tab([("BTC", 20000, 0.150), ("ETH", 20000, 0.100), ("SOL", 20000, 0.90), ("ADA", 300, 0.70)])    # SOL real cost 1.10% a side against 0.49% assumed
    rep = S.run(tmp_path / "out", table_fn=lambda days: quotes, request=request)
    return rep, j, calls


def test_the_rerun_reports_both_costs_flags_the_coin_whose_edge_goes_and_changes_nothing(tmp_path, monkeypatch):
    rep, _, calls = _run_with_fakes(tmp_path, monkeypatch)
    assert rep["measured"] == ["BTC", "ETH", "SOL"] and rep["not_measured"] == ["ADA"]
    for split in ("DISCOVERY", "CONFIRM"):
        b = rep["book"][split]
        assert b["assumed"]["end_cad"] > b["measured"]["end_cad"] or b["assumed"]["end_cad"] != b["measured"]["end_cad"]
    by = {r["coin"]: r for r in rep["coins"]}
    assert by["ADA"]["verdict"] == "NOT_MEASURED"                      # 300 quotes: its assumed cost stays
    assert by["SOL"]["verdict"] == "FLAGGED" and by["SOL"]["avg_pct_assumed"] == 1.0 and by["SOL"]["avg_pct_measured"] < 0
    assert by["BTC"]["verdict"] in ("HOLDS", "NEVER_HAD_EDGE") and rep["flagged"] == ["SOL"]
    assert "SOL" in rep["line"] and "Nothing was changed" in rep["line"]
    assert json.loads((tmp_path / "out" / "s2_result.json").read_text())["flagged"] == ["SOL"]
    assert all(set(cost) == {"BTC", "ETH", "SOL", "ADA"} for _, cost in calls)               # every coin always has a cost


def test_the_request_to_madhav_is_filed_once_and_the_due_item_is_ticked(tmp_path, monkeypatch):
    from jarvis.service import core, due_list, strategy_status

    k = tmp_path / "docs" / "knowledge"
    k.mkdir(parents=True)
    (k / "due_list.json").write_text(json.dumps({"version": 1, "items": [
        {"id": "S2-SPREADS", "what": "worker stage S2: the measured costs", "how": "run the S2 script and read it", "due": "2026-10-26"}]}))
    monkeypatch.setattr(core, "docs_dir", lambda base: __import__("pathlib").Path(base) / "docs")
    monkeypatch.setattr(strategy_status, "load", lambda *a, **kw: {"evidence_window": {"start": "2026-10-15", "days": 60}})
    rep, j, _ = _run_with_fakes(tmp_path, monkeypatch, request=True)
    rows = j.db.execute("SELECT by, kind, about, text FROM owner_requests").fetchall()
    assert len(rows) == 1 and rows[0][:3] == ("ananta-auto", "data", "worker stage S2") and "SOL" in rows[0][3]
    assert S.file_request(j, rep) is False and len(j.db.execute("SELECT * FROM owner_requests").fetchall()) == 1       # once per run date
    assert due_list.check(j, today="2026-10-27")["done"] == ["S2-SPREADS"] and "due_list_error" not in rep
