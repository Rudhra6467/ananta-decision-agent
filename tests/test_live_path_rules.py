"""Live path (flag 239, design part 2): the live options rules in code, with pre-live T1's 23 decisions as fixtures
(tests/data/live_t1_rows.json, copied from ~/ananta_runs/prelive/t1_rows.json; records india/registrations/prelive/T1_2026-11-25.md)."""
import json
from pathlib import Path

from india.live import rules
from india.live.rules import Plan

ROWS = json.loads((Path(__file__).parent / "data" / "live_t1_rows.json").read_text())


def _plan(r, **extra):
    return Plan(date=r["date"], index=r["index"], point=r["point"], exit=r["exit"], tradingsymbol=r["sym"], lot=r["lot"],
                price=r["premium_at_decision"] / r["lot"], expiry=r["expiry"], extra=extra)


def test_the_rules_give_t1s_verdict_for_every_decision():
    got = rules.walk([_plan(r) for r in ROWS])
    assert len(got) == 23
    for (p, v, why), r in zip(got, ROWS):
        want = r["verdict_37_5k"]
        assert (v if v != "skip" else why) == want, (r["date"], r["index"], v, why, want)


def test_18_of_22_scored_trades_trade_and_the_rest_skip_with_t1s_reason():
    got = rules.walk([_plan(r) for r in ROWS])
    scored = [(v, why) for (p, v, why), r in zip(got, ROWS) if r["pnl"] is not None]
    assert len(scored) == 22
    assert sum(v == "trade" for v, _ in scored) == 18
    assert {why for v, why in scored if v == "skip"} == {rules.SKIP_OVERNIGHT}
    last = got[-1]
    assert last[0].date == "2026-11-25" and last[2] == rules.SKIP_CAP


def test_cap_money_and_contract():
    p = Plan("2026-12-07", "BANKNIFTY", "D0", "NEXTOPEN", "BANKNIFTY26DEC63400CE", 30, 1250.0)      # Rs 37,500 exactly: allowed
    assert rules.verdict(p, []) == ("trade", "")
    assert rules.verdict(Plan(**{**p.__dict__, "price": 1250.05}), [])[1] == rules.SKIP_CAP
    assert rules.verdict(Plan(**{**p.__dict__, "tradingsymbol": ""}), [])[1] == rules.SKIP_NO_CONTRACT
    held = [Plan("2026-12-07", "NIFTY", "D0", "ORSTOP", "NIFTY26D0826000CE", 65, 600.0)]           # Rs 39,000 intraday already in
    assert rules.verdict(p, held)[1] == rules.SKIP_MONEY


def test_yesterdays_next_open_position_does_not_block_today():
    y = Plan("2026-12-07", "BANKNIFTY", "D3", "NEXTOPEN", "BANKNIFTY26DEC63400CE", 30, 700.0)
    t = Plan("2026-12-08", "NIFTY", "D0", "NEXTOPEN", "NIFTY26D1026000CE", 65, 150.0)
    assert rules.verdict(t, [y]) == ("trade", "")
    assert rules.verdict(Plan(**{**t.__dict__, "date": "2026-12-07"}), [y])[1] == rules.SKIP_OVERNIGHT


class FakeCalc:
    def __init__(self, total=None, fail=False):
        self.total, self.fail, self.asked = total, fail, []

    def basket_margin(self, orders):
        self.asked.append(orders)
        if self.fail:
            raise RuntimeError("no answer")
        return {"initial": {"total": self.total}, "final": {"total": self.total}} if self.total is not None else {}


def test_margin_check_needs_a_clear_yes():
    p = Plan("2026-12-07", "BANKNIFTY", "D0", "NEXTOPEN", "BANKNIFTY26DEC63400CE", 30, 1000.0)
    k = FakeCalc(30_045.6)
    assert rules.margin_check(k, p, [])[0]
    assert k.asked[0][0]["quantity"] == 30 and k.asked[0][0]["order_type"] == "LIMIT"
    assert not rules.margin_check(FakeCalc(80_000), p, [])[0]
    assert not rules.margin_check(FakeCalc(fail=True), p, [])[0]
    assert not rules.margin_check(FakeCalc(None), p, [])[0]
