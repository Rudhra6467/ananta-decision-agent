"""Live path (flag 239, design parts 1 and 3): the order module's shapes and refusals, with a fake Kite. Nothing reaches the network."""
import datetime as dt
import json

import pytest

from india import orders
from india.live import rules, switches
from india.live.rules import Plan
from live_fakes import FakeKite

BN = Plan("2026-12-07", "BANKNIFTY", "D0", "NEXTOPEN", "BANKNIFTY26DEC63400CE", 30, 1000.0)
STOP = Plan("2026-12-07", "BANKNIFTY", "D1", "ATRSTOP", "BANKNIFTY26DEC63400CE", 30, 1000.0,
            extra={"delta": 0.5, "index_entry": 63400.0, "index_stop": 63000.0})


@pytest.fixture(autouse=True)
def live_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_LIVE_DIR", str(tmp_path / "live_india"))


@pytest.fixture
def switched_on(monkeypatch):
    """Only for testing the shapes that would be sent: the master switch patched on, the kill switch off by Madhav, a fake Kite."""
    monkeypatch.setattr(switches, "LIVE_ORDERS", True)
    switches.turn_off(by="Madhav")


def test_limit_band_is_two_ticks_and_half_a_percent_on_the_step():
    assert orders.limit_price("BUY", 1000.0) == 1005.10
    assert orders.limit_price("SELL", 1000.0) == 994.90
    assert orders.limit_price("BUY", 101.03) == pytest.approx(101.65)
    with pytest.raises(orders.Refused):
        orders.limit_price("BUY", 0)


def test_entry_shape_is_limit_one_lot_nrml_ttl_one_minute():
    r = orders.entry_request(BN)
    d = r["data"]
    assert r["path"] == "/orders/regular" and r["method"] == "POST"
    assert (d["order_type"], d["quantity"], d["product"], d["transaction_type"], d["exchange"]) == ("LIMIT", 30, "NRML", "BUY", "NFO")
    assert d["validity"] == "TTL" and d["validity_ttl"] == 1
    orders.validate(r, BN)


@pytest.mark.parametrize("change,word", [({"order_type": "MARKET"}, "LIMIT"), ({"quantity": 60}, "1 lot"),
                                         ({"tradingsymbol": "BANKNIFTY26DEC63500CE"}, "not the contract the paper decision chose"),
                                         ({"product": "MIS"}, "NRML"), ({"price": 1005.12}, "step"),
                                         ({"transaction_type": "SELL"}, "BUY")])
def test_each_refusal(change, word):
    r = orders.entry_request(BN)
    r["data"].update(change)
    with pytest.raises(orders.Refused, match=word):
        orders.validate(r, BN)


def test_unknown_paths_and_methods_are_refused():
    with pytest.raises(orders.Refused):
        orders.validate({"what": "entry", "method": "POST", "path": "/orders/co", "data": {}}, BN)
    with pytest.raises(orders.Refused):
        orders.validate({"what": "entry", "method": "PUT", "path": "/orders/regular", "data": {}}, BN)


def test_switched_off_nothing_is_sent_and_the_ledger_says_so():
    k = FakeKite()
    out = orders.enter(k, BN, [])
    assert out["done"] is False and "refused at the gate" in out["why"]
    assert k.sent == []
    led = orders.read_ledger()
    assert [x["step"] for x in led] == ["before", "after"]
    assert led[1]["sent"] is False and "LIVE_ORDERS is off" in led[1]["answer"]


def test_rules_refuse_before_anything_is_built():
    k = FakeKite()
    big = Plan(**{**BN.__dict__, "price": 1300.0})
    assert orders.enter(k, big, [])["why"] == rules.SKIP_CAP
    assert k.calc == [] and k.sent == []
    assert orders.read_ledger()[-1]["what"] == "skip"


def test_shapes_sent_when_switched_on_with_a_fake_kite(switched_on):
    k = FakeKite()
    out = orders.enter(k, BN, [])
    assert out["done"] and out["order_id"] == "O1"
    method, url, data = k.sent[0]
    assert (method, url) == ("POST", "https://api.kite.trade/orders/regular") and data["price"] == 1005.10
    assert k.calc and k.calc[0][0]["quantity"] == 30
    led = orders.read_ledger()
    assert led[0]["step"] == "before" and led[0]["decision"]["point"] == "D0" and "margin" in led[0]["why"]
    assert led[1]["step"] == "after" and led[1]["ok"]


def test_margin_short_means_no_entry(switched_on):
    k = FakeKite(margin=90_000)
    assert "left" in orders.enter(k, BN, [])["why"] and k.sent == []


def test_never_enter_when_the_exit_cannot_be_placed(switched_on):
    k = FakeKite()
    no_stop = Plan(**{**STOP.__dict__, "extra": {}})
    assert "cannot be placed" in orders.enter(k, no_stop, [])["why"]
    timed = Plan(**{**BN.__dict__, "exit": "T1515"})
    assert "cannot be placed" in orders.enter(k, timed, [])["why"]
    assert k.sent == []


def test_unfilled_entry_is_cancelled_after_60_seconds_never_chased(switched_on):
    k = FakeKite()
    assert not orders.cancel_if_unfilled(k, BN, "O1", placed_t=1000.0, filled=False, now=1059.0)["done"]
    assert orders.cancel_if_unfilled(k, BN, "O1", placed_t=1000.0, filled=False, now=1060.0)["done"]
    assert k.sent == [("DELETE", "https://api.kite.trade/orders/regular/O1", None)]
    assert orders.read_ledger()[-1]["what"] == "not_filled_live"


def test_amo_window_for_fno():
    t = dt.time
    assert orders.amo_window_open(t(15, 45)) and orders.amo_window_open(t(23, 0)) and orders.amo_window_open(t(9, 11))
    assert not orders.amo_window_open(t(15, 44)) and not orders.amo_window_open(t(9, 12)) and not orders.amo_window_open(t(12, 0))
    assert not orders.amo_window_open(t(1, 0)) and not orders.amo_window_open(t(5, 29)) and orders.amo_window_open(t(5, 30))


def test_next_open_exit_is_an_amo_limit_sell(switched_on):
    k = FakeKite()
    assert not orders.exit_next_open(k, BN, 1100.0, dt.time(15, 30))["done"]
    out = orders.exit_next_open(k, BN, 1100.0, dt.time(15, 50))
    assert out["done"]
    method, url, data = k.sent[0]
    assert url.endswith("/orders/amo") and data["transaction_type"] == "SELL" and data["order_type"] == "LIMIT" and data["quantity"] == 30


def test_gtt_backstop_sits_wider_than_the_index_stop(switched_on):
    trig = orders.backstop_trigger(1000.0, 0.5, 63400.0, 63000.0)
    assert trig == 750.0                                       # 0.5 x 400 points x 1.25 under the fill
    k = FakeKite()
    out = orders.after_fill(k, STOP, 1000.0)
    assert out["done"] and out["trigger_id"] == 901
    method, url, data = k.sent[0]
    assert url.endswith("/gtt/triggers") and data["type"] == "single"
    cond, legs = json.loads(data["condition"]), json.loads(data["orders"])
    assert cond["trigger_values"] == [750.0] and cond["tradingsymbol"] == STOP.tradingsymbol
    assert len(legs) == 1 and legs[0]["order_type"] == "LIMIT" and legs[0]["transaction_type"] == "SELL" and legs[0]["quantity"] == 30
    with pytest.raises(orders.Refused):
        orders.gtt_request(STOP, 1200.0, 1000.0)              # a sell backstop above the price is refused


def test_failed_backstop_exits_now_and_gives_madhav_the_step(switched_on):
    k = FakeKite(fail_sends=1)
    out = orders.after_fill(k, STOP, 1000.0)
    assert not out["done"] and out["exit"]["done"] and "Positions, exit BANKNIFTY26DEC63400CE, 1 lot" in out["alert"]
    assert [u.rsplit("/", 2)[-2:] for _, u, _ in k.sent] == [["gtt", "triggers"], ["orders", "regular"]]


def test_index_stop_watch():
    assert orders.index_stop_hit("CE", 62999.0, 63000.0) and not orders.index_stop_hit("CE", 63001.0, 63000.0)
    assert orders.index_stop_hit("PE", 63000.0, 63000.0) and not orders.index_stop_hit("PE", 62000.0, 63000.0)


def test_morning_check_reprices_once_then_alerts(switched_on):
    k = FakeKite()
    assert orders.morning_check(k, BN, "A1", filled=True, t_ist=dt.time(9, 16))["done"]
    assert "waiting" in orders.morning_check(k, BN, "A1", filled=False, t_ist=dt.time(9, 17))["why"]
    out = orders.morning_check(k, BN, "A1", filled=False, t_ist=dt.time(9, 20), new_ref=980.0)
    assert out["done"] and k.sent[0][:2] == ("DELETE", "https://api.kite.trade/orders/amo/A1") and k.sent[1][1].endswith("/orders/regular")
    again = orders.morning_check(k, BN, "O2", filled=False, t_ist=dt.time(9, 25), new_ref=970.0, repriced=True)
    assert not again["done"] and "alert" in again and len(k.sent) == 2


def test_two_failed_sends_turn_the_kill_switch_on(switched_on):
    k = FakeKite(fail_sends=2)
    assert not orders.exit_now(k, BN, 1000.0, "test")["done"]
    assert not switches.kill_on()
    assert not orders.exit_now(k, BN, 1000.0, "test")["done"]
    assert switches.kill_on()
    assert "kill switch is on" in orders.exit_now(k, BN, 1000.0, "test")["why"] and len(k.sent) == 2
