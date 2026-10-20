"""SP3 infrastructure (20 Oct 2026): the registry's pinned bars, cost model v1.2 dated STT, the manifest-based coverage check."""
from __future__ import annotations

import datetime as dt
import json

import pandas as pd
import pytest

from india import costs, paths, registry


@pytest.fixture()
def lake(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path / "india"))
    paths.ensure()
    return tmp_path / "india"


def _seed_ledger(n_exit=5, n_ctx=3):
    with (paths.manifest_dir() / "test_ledger.jsonl").open("w") as fh:
        for i in range(n_exit):
            fh.write(json.dumps({"kind": "result", "study": "E99", "family": "exit", "variant": f"v{i}"}) + "\n")
        for i in range(n_ctx):
            fh.write(json.dumps({"kind": "result", "study": "C99", "family": "context", "variant": f"v{i}"}) + "\n")


def test_union_and_holdout_k_are_pinned(lake):
    _seed_ledger()
    reg = registry.register("SP3T", "SP3", "t", "h", ["a"], bar_families=["exit", "context"], union_k=742, holdout_k=7)
    a = registry.record(reg, "a", (0.1, 2.0, 100), (0.1, 5.0, 100), expect=1, rule="seen_val_only")
    b = registry.record(reg, "b", (0.1, 2.0, 100), (0.1, 5.0, 100), expect=1, rule="seen_val_only")
    h = registry.record(reg, "c", (float("nan"), float("nan"), 0), (0.1, 3.0, 100), expect=1, rule="holdout_one_sided")
    assert a["k_in_family"] == b["k_in_family"] == 742 and a["k_source"] == "union_k"
    assert h["k_in_family"] == 7 and h["k_source"] == "holdout_k" and h["z"] == pytest.approx(2.69, abs=0.01)
    assert h["verdict"] == "CONFIRMED"


def test_bar_families_count_without_pinned_k(lake):
    _seed_ledger(5, 3)
    reg = registry.register("SP3U", "SP3", "t", "h", ["a"], bar_families=["exit", "context"])
    r = registry.record(reg, "a", (0.1, 2.0, 100), (0.1, 2.0, 100), expect=1)
    assert r["k_in_family"] == 5 + 3 + 1 and r["k_source"] == "bar_families"


def test_old_registrations_unchanged(lake):
    _seed_ledger(5, 3)
    reg = registry.register("E98", "exit", "t", "h", ["a"])
    r = registry.record(reg, "a", (0.1, 2.0, 100), (0.1, 2.0, 100), expect=1)
    assert r["k_in_family"] == 6 and r["k_source"] == "family"


def test_dated_stt():
    d = lambda y, m, dd: dt.date(y, m, dd)
    assert costs.stt_rate("delivery", "buy", 2005, d(2005, 5, 31)) == pytest.approx(0.00075)
    assert costs.stt_rate("delivery", "sell", 2005, d(2005, 6, 1)) == pytest.approx(0.001)
    assert costs.stt_rate("delivery", "buy", 2010, d(2010, 1, 4)) == pytest.approx(0.00125)
    assert costs.stt_rate("delivery", "buy", 2013, d(2013, 6, 1)) == pytest.approx(0.001)
    assert costs.stt_rate("futures", "sell", 2010, d(2010, 1, 4)) == pytest.approx(0.00017)
    assert costs.stt_rate("futures", "sell", 2026, d(2026, 10, 1)) == pytest.approx(0.0005)
    assert costs.stt_rate("intraday", "sell", 2005, d(2005, 1, 3)) == pytest.approx(0.00015)
    old = costs.round_trip("delivery", 12000, 12000, 2026, 80)
    dated = costs.round_trip("delivery", 12000, 12000, 2026, 80, when=d(2010, 3, 1))
    # STT 0.125% vs 0.1% on both legs, plus the pre-Oct-2024 exchange charge (with GST on it)
    assert dated["fees"] - old["fees"] == pytest.approx(24000 * 0.00025 + 24000 * (0.0000325 - 0.0000307) * 1.18, rel=1e-6)


def test_coverage_reads_manifests_only(lake):
    from india import sealed

    days = pd.bdate_range("2024-01-01", "2024-01-31")
    (paths.data_dir() / "silver" / "calendar").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": days.date, "is_trading_day": True}).to_parquet(paths.data_dir() / "silver" / "calendar" / "calendar.parquet")
    with (paths.manifest_dir() / "daily_src.jsonl").open("w") as fh:
        for x in days[:-3]:
            fh.write(json.dumps({"date": str(x.date()), "status": 200}) + "\n")
        fh.write(json.dumps({"date": str(days[-1].date()), "status": 404}) + "\n")
    with (paths.manifest_dir() / "window_src.jsonl").open("w") as fh:
        fh.write(json.dumps({"from": "2024-01-01", "to": "2024-01-31", "status": 200, "n": 0}) + "\n")
    s = sealed.coverage_summary("daily_src", "2024-01-01", "2024-01-31")
    assert s["longest_gap"] == 3 and s["verdict"] == "FAIL"
    w = sealed.coverage_summary("window_src", "2024-01-01", "2024-01-31")
    assert w["share_present"] == 1.0 and w["verdict"] == "PASS"
    log = (paths.manifest_dir() / "sealed_access.jsonl").read_text()
    assert '"purpose": "coverage"' in log
