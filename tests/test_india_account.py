"""The account book (india/account.py): opens from the snapshot, applies only final autonomous days once, fills sells with costs, never buys
outside ADMITTED families, conserves value apart from costs, and lists where the twin differs from the real account."""
from __future__ import annotations

import json

import pytest

from india import account, allocator


@pytest.fixture
def lake(tmp_path, monkeypatch):
    data = tmp_path / "india"
    (data / "paper").mkdir(parents=True)
    (data / "bronze" / "ledger").mkdir(parents=True)
    monkeypatch.setattr(allocator.paths, "data_dir", lambda: data)
    monkeypatch.setattr(account.paths, "data_dir", lambda: data)
    (data / "bronze" / "ledger" / "2026-10-22.json").write_text(json.dumps({"taken_at": "2026-10-22T16:36:22+00:00", "margins": {"equity": {"available": {"live_balance": 1500}}},
        "holdings": [{"tradingsymbol": "JIOFIN", "quantity": 119, "average_price": 271.9, "last_price": 211.0}, {"tradingsymbol": "IDEA", "quantity": 110, "average_price": 11.2, "last_price": 11.54}]}))
    (data / "paper" / "allocation.json").write_text(json.dumps({"mode": "autonomous", "options_inr": 50000}))
    return data


def _ledger(data, rows):
    (data / "paper" / "allocation_ledger.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_opens_from_the_snapshot_and_waits_for_the_day_to_be_final(lake):
    _ledger(lake, [{"day": "2026-10-22", "mode": "autonomous", "moves": [{"kind": "sleeve", "from": "options", "to": "cash", "inr": 16300}]}])
    v = account.run()
    assert v["options_inr"] == 50000 and v["pending_days"] == ["2026-10-22"] and v["trades_count"] == 0
    assert {p["symbol"] for p in v["positions"]} == {"JIOFIN", "IDEA"}


def test_applies_final_days_once_with_costs_and_never_buys_unadmitted(lake):
    rows = [{"day": "2026-10-22", "mode": "autonomous", "moves": [{"kind": "sleeve", "from": "options", "to": "cash", "inr": 16300},
                                                               {"kind": "stock_sell", "symbol": "JIOFIN", "inr": 12000, "from": "stocks", "to": "cash"},
                                                               {"kind": "stock_buy", "symbol": "KAYNES", "inr": 5000, "family": "BRK", "from": "cash", "to": "stocks"}]},
            {"day": "2026-10-23", "mode": "autonomous", "moves": []}]
    _ledger(lake, rows)
    before = 119 * 211.0 + 110 * 11.54 + 1500 + 50000
    v = account.run()
    assert v["options_inr"] == 33700 and v["applied_days"] == ["2026-10-22"]
    sell = next(t for t in v["trades"] if t.get("side") == "SELL")
    assert sell["qty"] == 56 and sell["cost_inr"] > 0
    buy = next(t for t in v["trades"] if t.get("kind") == "stock_buy")
    assert "not ADMITTED" in buy["skipped"]
    assert abs(v["value_inr"] - (before - sell["cost_inr"])) <= 1, "moves shift value; only costs leave"
    assert next(d for d in v["differs_from_real"] if d["symbol"] == "JIOFIN") == {"symbol": "JIOFIN", "twin_qty": 63, "real_qty": 119}
    again = account.run()
    assert again["trades_count"] == v["trades_count"], "a day is applied once"


def test_an_advisory_day_trades_nothing(lake):
    _ledger(lake, [{"day": "2026-10-22", "mode": "advisory", "moves": [{"kind": "sleeve", "from": "options", "to": "cash", "inr": 16300}]}, {"day": "2026-10-23", "mode": "advisory", "moves": []}])
    v = account.run()
    assert v["trades_count"] == 0 and v["options_inr"] == 50000
