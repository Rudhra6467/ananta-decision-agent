"""Ananta Canada stays a separate research lab (Madhav, Oct 14): no shared code paths, files or data with
crypto, the holdout sealed, registrations frozen only with approval, thresholds as pre-registered."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _py(globs):
    return [p for g in globs for p in ROOT.glob(g) if "__pycache__" not in p.parts and "node_modules" not in p.parts]


def test_crypto_code_never_imports_canada():
    pat = re.compile(r"^\s*(from\s+canada[\s.]|import\s+canada\b)", re.M)
    bad = [str(p.relative_to(ROOT)) for p in _py(["jarvis/**/*.py", "src/**/*.py", "*.py"]) if pat.search(p.read_text(errors="ignore"))]
    assert not bad, f"crypto code imports canada: {bad}"


def test_canada_never_imports_crypto():
    pat = re.compile(r"^\s*(from\s+(jarvis|src)[\s.]|import\s+(jarvis|src)\b)", re.M)
    bad = [str(p.relative_to(ROOT)) for p in _py(["canada/**/*.py"]) if pat.search(p.read_text(errors="ignore"))]
    assert not bad, f"canada imports crypto code: {bad}"


def test_canada_is_outside_the_agents_reading_folders():
    assert not (ROOT / "docs" / "canada").exists() and not (ROOT / "docs" / "research" / "canada").exists()
    for f in (ROOT / "docs" / "knowledge").glob("*.json"):
        t = f.read_text(errors="ignore")
        assert "canada_lake" not in t and '"CA1"' not in t, f"{f.name} mentions Canada"


def test_data_folder_must_sit_outside_crypto(tmp_path, monkeypatch):
    from canada import paths

    monkeypatch.setenv("CANADA_DATA_DIR", str(tmp_path / "canada"))
    assert paths.check_isolated() == (tmp_path / "canada").resolve()
    monkeypatch.setenv("CANADA_DATA_DIR", str(ROOT / "canada_data"))
    with pytest.raises(RuntimeError):
        paths.check_isolated()


def test_registry_is_research_only_and_holdout_sealed():
    from canada import registry

    d = registry.load()
    assert d["namespace"] == "CA" and d["holdout"]["sealed"] is True and d["holdout"]["start"] == "2024-01-01"
    assert set(d["reviews"]) == {"CA1", "CA2", "CA3", "CA4", "CA5"}, "no reviews beyond CA1-CA5"
    for r in d["reviews"].values():
        assert r["finding_status"] == "RESEARCH" and r["status"] in registry.STATUSES
    assert d["budget"]["approved_recurring"] == [] and d["budget"]["target_cad_month"] == 55
    assert registry.verify() == []


def test_holdout_dates_refused_while_sealed():
    from canada import registry

    registry.assert_research_dates("2000-01-01", "2023-12-31")
    for a, b in (("2020-01-01", "2024-01-02"), ("2024-03-01", "2024-06-01")):
        with pytest.raises(registry.HoldoutSealed):
            registry.assert_research_dates(a, b)


def test_freeze_needs_approval_and_detects_tampering(tmp_path, monkeypatch):
    from canada import registry

    repo = tmp_path
    reg = repo / "canada" / "registry" / "canada_status.json"
    reg.parent.mkdir(parents=True)
    reg.write_text(registry.REG_PATH.read_text())
    for rel in registry.RULE_CODE:                                            # a private copy of the rule code
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text((registry.REPO / rel).read_text())
    monkeypatch.setattr(registry, "ROOT", repo / "canada")
    monkeypatch.setattr(registry, "REPO", repo)
    monkeypatch.setattr(registry, "REG_PATH", reg)
    monkeypatch.setattr(registry, "REG_DIR", repo / "canada" / "registrations")
    regs = {rid: f"{rid} frozen text" for rid in registry.REVIEWS}
    with pytest.raises(PermissionError):
        registry.freeze_bundle(regs, "doc", approved="", day="2026-10-15")
    with pytest.raises(ValueError):
        registry.freeze_bundle({"CA1": "x"}, "doc", approved="Madhav", day="2026-10-15")
    b = registry.freeze_bundle(regs, "the whole C0 document", approved="Madhav, in the C0 doc", day="2026-10-15")
    d = registry.load()
    assert d["bundle"]["sha256"] == b and len(d["bundle"]["files"]) == 9 and registry.verify() == []
    assert all(r["status"] == "FROZEN" and r["bundle_sha256"] == b for r in d["reviews"].values())
    with pytest.raises(PermissionError):
        registry.freeze_bundle(regs, "edited doc", approved="Madhav", day="2026-10-16")
    (repo / "canada" / "registrations" / "CA1.md").write_text("CA1 quietly edited")
    (repo / "canada" / "costs.py").write_text("FLOOR = 0.0  # a cheaper cost, quietly")
    assert set(registry.verify()) == {"canada/registrations/CA1.md", "canada/costs.py"}


def test_schema_creates_lake_and_sealed_holdout(tmp_path):
    from canada import schema

    lake = schema.create_lake(tmp_path / "lake.sqlite")
    names = {r[0] for r in lake.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"manifests", "manifest_files", "securities", "calendar", "bars", "index_spans",
            "classification_snapshots", "macro", "cost_estimates", "validation_runs"} <= names
    hold = schema.create_holdout(tmp_path / "sealed" / "holdout.sqlite", "2026-10-15 00:00:00")
    assert hold.execute("SELECT COUNT(*) FROM seal").fetchone()[0] == 1


def test_thresholds_match_the_preregistration():
    from canada.validation import THRESHOLDS as T

    assert T["XV_agree_min"] == 0.995 and T["XV_tol_pct"] == 0.005 and T["XV_tol_abs_cad"] == 0.01
    assert T["V3_missing_member_days_max_frac"] == 0.005 and T["V8_sector_partition_min"] == 0.995
    assert T["gap_short_max_days"] == 5 and T["gap_exclusion_days"] == 60
    assert T["V9_spot_checks"] == 300 and T["V9_min_match"] == 297 and T["V9_tolerance"] == 0.005
    assert T["V4_second_record_tol"] == 0.05 and T["V6_reconcile_min"] == 0.95 and T["V6_sample_years"] == 5
    from canada.validation import sector_count

    assert sector_count("2016-08-31") == 10 and sector_count("2016-09-01") == 11


def test_cross_vendor_test_and_gap_rules():
    from canada.validation import close_agrees, cross_vendor, gap_rule, ohlc_ok

    assert close_agrees(100.4, 100.0) and not close_agrees(100.6, 100.0)     # 0.5% band
    assert close_agrees(0.51, 0.50) and not close_agrees(0.52, 0.50)         # C$0.01 floor on cheap stocks
    good = [(f"S{i % 10}", 10.0, 10.0) for i in range(996)] + [(f"S{i}", 11.0, 10.0) for i in range(4)]
    assert cross_vendor(good)["passed"]                                      # 99.6% agree
    bad = [(f"S{i % 10}", 10.0, 10.0) for i in range(994)] + [(f"S{i}", 11.0, 10.0) for i in range(6)]
    assert not cross_vendor(bad)["passed"]                                   # 99.4% agree
    lone = [("A", 10.0, 10.0)] * 900 + [("B", 10.0, 10.0)] * 95 + [("B", 11.0, 10.0)] * 5
    assert cross_vendor(lone)["passed"]                                      # B at exactly 95.0%: allowed
    worse = [("A", 10.0, 10.0)] * 960 + [("B", 10.0, 10.0)] * 36 + [("B", 11.0, 10.0)] * 4
    assert cross_vendor(worse)["stocks_below_95pct"] == ["B"] and not cross_vendor(worse)["passed"]
    assert gap_rule(0) == "none" and gap_rule(5) == "keep_unfilled" and gap_rule(6) == "no_new_signals_60_days"
    assert ohlc_ok(10, 11, 9, 10.5, 0) and not ohlc_ok(10, 9.5, 9, 10.5, 100)


def test_cost_estimate_is_labelled_and_never_negative():
    from canada import costs

    assert costs.LABEL == "ESTIMATE"
    assert costs.corwin_schultz(10, 10, 10, 10) == 0.0
    s = costs.corwin_schultz(10.10, 9.90, 10.12, 9.92)
    assert 0.0 <= s < 0.05
    assert costs.one_way_cost([0.0] * 21) == pytest.approx(0.001)            # floor 0.05% + slippage 0.05%
    assert costs.one_way_cost([0.004] * 21) == pytest.approx(0.0025)         # half of 0.4% + 0.05%
    assert costs.one_way_cost([0.004] * 21, stress=2.0) == pytest.approx(0.005)  # 2x doubles floor and slippage too
    assert costs.one_way_cost([0.0] * 21, stress=2.0) == pytest.approx(0.002)
    # overnight adjustment: a day-2 range wholly above day 1's close is shifted down by the gap
    gapped = costs.corwin_schultz(10.10, 9.90, 11.10, 10.90)
    adjusted = costs.corwin_schultz(10.10, 9.90, 11.10, 10.90, c0=10.0)
    assert adjusted == pytest.approx(costs.corwin_schultz(10.10, 9.90, 10.20, 10.0)) and adjusted >= gapped
    # the window for a fill on day f ends on f-5: the dip's own days never set its cost
    est = list(range(40))
    w = costs.fill_window(est, 30)
    assert len(w) == 21 and w[-1] == 25 and w[0] == 5
    with pytest.raises(ValueError):
        costs.fill_window(est, 24)
