"""Live path (flag 239, design part 5): the master switch and enforce are off in code; the kill switch is on unless Madhav wrote 'off'."""
import json

import pytest

from india.live import switches


@pytest.fixture(autouse=True)
def live_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_LIVE_DIR", str(tmp_path / "live_india"))
    return tmp_path / "live_india"


def test_master_switch_and_enforce_are_off_in_code():
    assert switches.LIVE_ORDERS is False
    assert switches.ENFORCE is False
    src = open(switches.__file__).read()
    assert "\nLIVE_ORDERS = False\n" in src and "\nENFORCE = False\n" in src


def test_gate_refuses_while_the_master_switch_is_off_even_with_the_kill_switch_off():
    switches.turn_off(by="Madhav")
    ok, why = switches.may_send()
    assert not ok and "LIVE_ORDERS is off" in why
    with pytest.raises(switches.OrdersOff):
        switches.require_send()


def test_kill_switch_missing_or_unreadable_counts_as_on(live_tmp):
    assert switches.kill_on()                                   # no file: on
    live_tmp.mkdir(parents=True, exist_ok=True)
    (live_tmp / "kill_switch.json").write_text("{not json")
    assert switches.kill_on()
    (live_tmp / "kill_switch.json").write_text(json.dumps({"state": "maybe"}))
    assert switches.kill_on()
    (live_tmp / "kill_switch.json").write_text(json.dumps({"state": "off", "by": "ananta"}))
    assert switches.kill_on(), "only Madhav's off counts"


def test_only_madhav_turns_it_off():
    with pytest.raises(PermissionError):
        switches.turn_off(by="ananta")
    switches.turn_off(by="Madhav")
    assert not switches.kill_on()
    switches.turn_on("test", by="ananta")
    assert switches.kill_on()


def test_two_failed_calls_in_a_row_turn_it_on():
    switches.turn_off(by="Madhav")
    switches.note_failure("one")
    assert not switches.kill_on()
    switches.note_success()
    switches.note_failure("one again")
    assert not switches.kill_on(), "a success in between resets the count"
    switches.note_failure("two")
    assert switches.kill_on()


def test_kill_switch_blocks_the_gate_even_if_the_master_switch_were_on(monkeypatch):
    monkeypatch.setattr(switches, "LIVE_ORDERS", True)
    switches.turn_on("test")
    assert not switches.may_send()[0]
    switches.turn_off(by="Madhav")
    assert switches.may_send()[0]


def test_live_folder_may_not_sit_inside_the_india_data(monkeypatch, tmp_path):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("INDIA_LIVE_DIR", str(tmp_path / "data" / "live"))
    with pytest.raises(RuntimeError, match="refused"):
        switches.live_dir()
