"""The allocator (Madhav, 23 Oct 2026): advisory moves nothing, autonomous moves capital on paper and conserves the pool, the regime table binds,
a re-run of the same day is idempotent, no order path is touched, and the rule file says what Madhav said."""
from __future__ import annotations

import json

import pytest

from india import allocator

DAY = "2026-10-22"


def _h(sym, qty, avg, last, isin="X"):
    return {"tradingsymbol": sym, "exchange": "NSE", "quantity": qty, "average_price": avg, "last_price": last, "pnl": (last - avg) * qty, "isin": isin}


def _row(sym, d20, d200, rsi=50, atr=0.02, liq=10):
    return {"symbol": sym, "isin": "I" + sym, "liq_rank": liq, "dist_sma20": d20, "dist_sma200": d200, "rsi14": rsi, "atr_pct": atr}


@pytest.fixture
def lake(tmp_path, monkeypatch):
    data = tmp_path / "india"
    (data / "paper" / "decisions").mkdir(parents=True)
    (data / "readmodel").mkdir()
    (data / "bronze" / "ledger").mkdir(parents=True)
    monkeypatch.setattr(allocator.paths, "data_dir", lambda: data)
    (data / "readmodel" / "latest.json").write_text(json.dumps({
        "data_through": DAY, "next_session": "2026-10-23",
        "market": {"trend_state": "below_both", "nifty_vs_sma50": -0.03, "nifty_vs_sma200": -0.06, "vix_close": 15.7, "vix_vs_sma50": 0.25},
        "sp1": {"status": "lost", "book": {"sessions": 0}}, "guardrails": {}, "decisions_today": []}))
    (data / "paper" / "decisions" / f"{DAY}.universe.json").write_text(json.dumps({"rows": [
        _row("STRONG", 0.03, 0.12), _row("WEAK", -0.06, -0.20, rsi=33, atr=0.04), _row("BIG", -0.03, -0.14, rsi=34)]}))
    holdings = [_h("STRONG", 100, 100, 120), _h("WEAK", 100, 100, 70), _h("BIG", 200, 100, 90), _h("DUST", 1, 50, 40)]
    (data / "bronze" / "ledger" / f"{DAY}.json").write_text(json.dumps({
        "taken_at": "2026-10-22T16:36:22+00:00", "holdings": holdings, "margins": {"equity": {"available": {"live_balance": 1500}}}}))
    return data


def _mode(data, mode):
    (data / "paper" / "allocation.json").write_text(json.dumps({"mode": mode, "options_inr": 50000}))


def test_advisory_rates_ranks_and_moves_nothing(lake):
    _mode(lake, "advisory")
    v = allocator.run()
    assert v["mode"] == "advisory" and v["moves_applied"] is False
    assert v["sleeves"]["after"] == v["sleeves"]["now"], "advisory must not change the sleeves"
    names = [x["symbol"] for x in v["holdings"]]
    assert names[0] == "STRONG" and [x["rank"] for x in v["holdings"]] == list(range(1, 5))
    by = {x["symbol"]: x for x in v["holdings"]}
    assert by["STRONG"]["grade"] in ("A", "B") and by["WEAK"]["grade"] == "D" and by["WEAK"]["action"] == "REDUCE"
    assert by["DUST"]["action"] == "TIDY", "a holding under the tiny limit is tidied, whatever its grade"
    for x in v["holdings"]:
        assert x["wrong_if"] and x["why"], "every holding names its reason and what would make the suggestion wrong"
    assert v["sleeves"]["now"]["options"] == 50000 and v["sleeves"]["now"]["stocks"] == 100 * 120 + 100 * 70 + 200 * 90 + 40


def test_autonomous_moves_on_paper_conserves_the_pool_and_obeys_the_table(lake):
    _mode(lake, "autonomous")
    v = allocator.run()
    s = v["sleeves"]
    assert v["moves_applied"] is True and v["moves"], "an unproven options sleeve over its ceiling must release capital"
    assert sum(s["after"].values()) == sum(s["now"].values()), "moves shift capital, they never create or destroy it"
    pool = sum(s["now"].values())
    moved = sum(m["inr"] for m in v["moves"])
    assert moved <= 0.10 * pool + 100, "no more than 10% of the pool moves in a session"
    assert all(m["inr"] >= 2000 for m in v["moves"])
    assert s["after"]["options"] < s["now"]["options"]
    assert v["regime"]["options"] == 0.2, "below both averages, with too few sessions: options at most 20%"


def test_rerunning_the_same_day_is_idempotent_and_next_day_builds_on_it(lake):
    _mode(lake, "autonomous")
    a = allocator.run()
    b = allocator.run()
    assert a["sleeves"]["after"] == b["sleeves"]["after"]
    rows = [json.loads(x) for x in (lake / "paper" / "allocation_ledger.jsonl").read_text().splitlines()]
    assert len(rows) == 1, "one ledger row a day"
    rm = json.loads((lake / "readmodel" / "latest.json").read_text())
    rm["data_through"] = "2026-10-23"
    (lake / "readmodel" / "latest.json").write_text(json.dumps(rm))
    c = allocator.run()
    assert c["sleeves"]["now"]["options"] == a["sleeves"]["after"]["options"], "tomorrow starts where today's paper moves left off"
    assert c["sleeves"]["now"]["options"] < 50000


def test_switching_back_to_advisory_drops_todays_moves(lake):
    _mode(lake, "autonomous")
    allocator.run()
    _mode(lake, "advisory")
    v = allocator.run()
    assert v["sleeves"]["after"] == v["sleeves"]["now"] and v["sleeves"]["now"]["options"] == 50000


def test_a_fired_guardrail_buys_nothing(lake):
    rm = json.loads((lake / "readmodel" / "latest.json").read_text())
    rm["market"]["trend_state"] = "above_both"
    rm["guardrails"] = {"fired": True}
    (lake / "readmodel" / "latest.json").write_text(json.dumps(rm))
    # lots of cash and a stock sleeve under target: the only thing that would happen is a buy
    (lake / "bronze" / "ledger" / f"{DAY}.json").write_text(json.dumps({"taken_at": "2026-10-22T16:36:22+00:00", "holdings": [_h("STRONG", 10, 100, 120)],
                                                                          "margins": {"equity": {"available": {"live_balance": 90000}}}}))
    _mode(lake, "autonomous")
    v = allocator.run()
    assert not [m for m in v["moves"] if m["kind"] == "stock_buy"]


def test_the_rule_file_carries_madhavs_decision_and_the_fixed_options_amount():
    r = allocator.rule()
    assert r["options_inr"] == 50000 and r["default_mode"] == "advisory" and r["paper_only"] is True
    assert "50000" in r["decided"] and "autonomous" not in r["default_mode"]
    assert sum(r["rating_weights"].values()) == 100


def test_the_allocator_places_no_order_and_calls_no_broker():
    import ast
    from pathlib import Path
    src = Path(allocator.__file__).read_text()
    names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Attribute)}
    assert not names & {"Kite", "place_order", "orders", "requests", "post"}, "the allocator only reads files"


def test_wrong_if_is_never_a_line_already_crossed():
    """27 Oct: TMPV (WATCH) said "wrong if it closes under ₹338, its long-term average" while it was at ₹263.70."""
    from india import allocator as al
    w = al.wrong_down(263.70, [(338.0, "its long-term average"), (270.0, "its one-month average")])
    assert "338" not in w and "270" not in w and "another 10%" in w and "237" in w
    assert al.wrong_down(300.0, [(338.0, "its long-term average"), (290.0, "its one-month average")]) == "it closes under ₹290, its one-month average"
    assert al.wrong_up(300.0, [(280.0, "its one-month average"), (320.0, "its long-term average")], " on good volume") == \
        "it climbs back above ₹320, its long-term average on good volume"
    assert "330" in al.wrong_up(300.0, [(280.0, "a"), (290.0, "b")])
    assert al.wrong_if_already_true({"wrong_if": "it closes under ₹338, its long-term average", "last": 263.7})
    assert not al.wrong_if_already_true({"wrong_if": al.wrong_down(263.7, [(338.0, "x")]), "last": 263.7})
    for last, lv in ((100.0, 120.0), (100.0, 80.0)):
        for f in (al.wrong_down, al.wrong_up):
            assert not al.wrong_if_already_true({"wrong_if": f(last, [(lv, "an average")]), "last": last})
