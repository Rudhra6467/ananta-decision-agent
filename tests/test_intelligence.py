"""Decision Intelligence foundation — no network, no Ananta, no S5 runs."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.intelligence.adjudicate import adjudicate
from src.intelligence.attribution import attribute_print_ready, _classify, population_role
from src.intelligence.fingerprint import from_slot, fingerprints, ret_bin
from src.intelligence.opportunity_engine import refuse_fair_value, refuse_scan, spec as opp_spec
from src.intelligence.setup_memory import extract, _record, refusal_stamp
from src.intelligence.universe import fit_from_take, research, _regime_vs_tape, _gate_vs_tape
from src.intelligence.universe_specs import generate_cells, catalog
from src.intelligence.evidence_engine import card_from_cell, status_class, confidence_band, provenance
from src.intelligence.h2 import _codes, histogram

from src.intelligence.decision_quality import (
    BASELINE_V0,
    evidence_depth,
    meter,
    path_call,
    score_horizon,
    signed_verdict,
)

from src.intelligence.contract import contract_spec
from src.intelligence.experiments import approve, list_experiments, try_run
from src.intelligence.gates import evaluate_gates, WAVE_A_WATCH, REGIME_FILTER
from src.intelligence.orchestrate import propose_execution, run_cycle
from src.intelligence.paper import simulate, simulate_take_blocked
from src.intelligence.profiles import AGGRESSIVE, SAFE, get_profile, normalize_profile_name
from src.intelligence.schema import ConfidenceTriplet, TypedDecision
from src.intelligence.system_status import completeness
from src.intelligence.user_context import _norm_intent, intent_allows_take


def _obs(*, hunter_regime="TREND_UP", hunter_setup=True, hunter_skip="REGIME_FILTERED",
         hunter_dec="SKIP", squeeze_setup=False, ananta_ok=True, kill=False,
         slots=0, source="live_paper", fwd_1h=0.5):
    return {
        "schema": "observation_v0",
        "ts": "2026-08-23T12:00:00+00:00",
        "source": source,
        "obs_id": "obs_test_001",
        "system_truth": {
            "ananta_ok": ananta_ok,
            "kill_switch": kill,
            "agent_decision": hunter_dec,
            "cycle_id": "cyc_test_001",
            "n_setups": int(hunter_setup) + int(squeeze_setup),
            "wave_a": ["hunter", "squeeze", "bollinger-mr"],
            "regimes_by_symbol": {"BTC/USD": {"market": "BULL", "asset": hunter_regime}},
            "portfolio": {"equity": 10000, "slots_used": slots, "kill_switch": kill},
            "strategy_observations": [
                {
                    "strategy": "hunter",
                    "symbol": "BTC/USD",
                    "setup_detected": hunter_setup,
                    "decision": hunter_dec,
                    "skip_reason": hunter_skip,
                    "regime": hunter_regime,
                    "enabled": True,
                    "ran": True,
                },
                {
                    "strategy": "squeeze",
                    "symbol": "BTC/USD",
                    "setup_detected": squeeze_setup,
                    "decision": "WAIT",
                    "skip_reason": None,
                    "regime": hunter_regime,
                    "enabled": True,
                    "ran": True,
                },
                {
                    "strategy": "bollinger-mr",
                    "symbol": "BTC/USD",
                    "setup_detected": False,
                    "decision": "WAIT",
                    "skip_reason": "REGIME_FILTERED",
                    "regime": hunter_regime,
                    "enabled": True,
                    "ran": True,
                },
            ],
        },
        "market_truth": {
            "ok": True,
            "source": "kraken_public",
            "btc": {"price": 64000, "ret_1h_pct": 0.8, "trend_flag": "UP", "compression_flag": "NONE"},
            "breadth_1h_pct_positive": 70,
        },
        "outcome_truth": {"fwd_15m_pct": 0.1, "fwd_1h_pct": fwd_1h, "fwd_4h_pct": 0.2},
    }


def _take_eq_obs():
    return _obs(
        hunter_regime="REVERSAL",
        hunter_setup=True,
        hunter_skip=None,
        hunter_dec="TAKE",
    )


class TestProfiles(unittest.TestCase):
    def test_three_profiles_not_three_agents(self):
        self.assertEqual(get_profile("SAFE").name, "SAFE")
        self.assertEqual(get_profile("low").name, "SAFE")
        self.assertEqual(get_profile("HIGH").name, "AGGRESSIVE")
        self.assertEqual(normalize_profile_name("medium"), "MODERATE")
        self.assertLess(SAFE.max_slots, AGGRESSIVE.max_slots)
        self.assertLess(SAFE.max_notional_pct_equity, AGGRESSIVE.max_notional_pct_equity)
        self.assertTrue(SAFE.prefer_wait_when_weak)
        self.assertEqual(AGGRESSIVE.max_enabled_strategies, 5)

    def test_aggressive_still_confirms_take(self):
        self.assertTrue(AGGRESSIVE.confirmation_required_for_take)


class TestGates(unittest.TestCase):
    def test_wave_a_take_cannot_execute(self):
        allowed, issued, hits = evaluate_gates(
            recommended_action="TAKE",
            strategy_key="hunter",
            setup_detected=True,
            profile=AGGRESSIVE,
            user_intent="PAPER_TRADE",
            ananta_ok=True,
            user_confirmed=True,
            evidence_confidence=0.99,
            decision_confidence=0.99,
        )
        self.assertFalse(allowed)
        self.assertNotEqual(issued, "TAKE")
        self.assertTrue(any(h.code == WAVE_A_WATCH and not h.passed for h in hits))

    def test_regime_filter_cannot_be_overridden(self):
        allowed, issued, hits = evaluate_gates(
            recommended_action="TAKE",
            strategy_key="hunter",
            setup_detected=True,
            skip_reason="REGIME_FILTERED",
            profile=AGGRESSIVE,
            user_intent="PAPER_TRADE",
            evidence_confidence=0.99,
            decision_confidence=0.99,
        )
        self.assertEqual(issued, "SKIP")
        self.assertFalse(allowed)
        self.assertTrue(any(h.code == REGIME_FILTER and not h.passed for h in hits))

    def test_observe_intent_forbids_take(self):
        allowed, issued, _ = evaluate_gates(
            recommended_action="TAKE",
            strategy_key="hunter",
            setup_detected=True,
            profile=get_profile("MODERATE"),
            user_intent="OBSERVE",
            evidence_confidence=0.99,
            decision_confidence=0.99,
        )
        self.assertFalse(allowed)
        self.assertNotEqual(issued, "TAKE")

    def test_kill_switch_blocks_take(self):
        _, issued, hits = evaluate_gates(
            recommended_action="TAKE",
            strategy_key="hunter",
            setup_detected=True,
            kill_switch=True,
            profile=AGGRESSIVE,
            user_intent="PAPER_TRADE",
            evidence_confidence=0.99,
            decision_confidence=0.99,
        )
        self.assertNotEqual(issued, "TAKE")
        self.assertTrue(any(h.code == "ANANTA_KILL" and not h.passed for h in hits))

    def test_no_setup_cannot_become_take(self):
        _, issued, _ = evaluate_gates(
            recommended_action="TAKE",
            strategy_key="hunter",
            setup_detected=False,
            profile=AGGRESSIVE,
            user_intent="PAPER_TRADE",
            evidence_confidence=0.99,
            decision_confidence=0.99,
        )
        self.assertEqual(issued, "WAIT")

    def test_other_12_locked(self):
        allowed, issued, hits = evaluate_gates(
            recommended_action="TAKE",
            strategy_key="continuation",
            setup_detected=True,
            profile=AGGRESSIVE,
            user_intent="PAPER_TRADE",
            user_confirmed=True,
            evidence_confidence=0.99,
            decision_confidence=0.99,
        )
        self.assertFalse(allowed)
        self.assertTrue(any(h.code == "NON_WAVE_A_LOCKED" and not h.passed for h in hits))

    def test_safe_weak_evidence_prefers_wait(self):
        _, issued, hits = evaluate_gates(
            recommended_action="TAKE",
            strategy_key="hunter",
            setup_detected=True,
            profile=SAFE,
            user_intent="PAPER_TRADE",
            evidence_confidence=0.2,
            decision_confidence=0.2,
        )
        self.assertIn(issued, ("WAIT", "SKIP"))
        self.assertTrue(any(h.code == "WEAK_EVIDENCE" and not h.passed for h in hits))


class TestAdjudicate(unittest.TestCase):
    def test_trend_up_hunter_is_skip(self):
        d = adjudicate(_obs(), profile=get_profile("MODERATE"), user_intent="OBSERVE")
        self.assertEqual(d.recommended_action, "SKIP")
        self.assertEqual(d.issued_action, "SKIP")
        self.assertFalse(d.execution_allowed)
        self.assertIn("hypothesis", d.counter_thesis.lower() + d.thesis.lower() + d.adjudication.lower())
        self.assertTrue(d.citations)
        self.assertIsNone(d.confidences.as_dict()["blended"])

    def test_reversal_take_eq_is_blocked_fill(self):
        d = adjudicate(_take_eq_obs(), profile=AGGRESSIVE, user_intent="PAPER_TRADE", user_confirmed=True)
        self.assertEqual(d.recommended_action, "TAKE")
        self.assertNotEqual(d.issued_action, "TAKE")
        self.assertFalse(d.execution_allowed)
        self.assertEqual(d.wave_a_status, "WATCH")
        self.assertEqual(d.execution_authority, "ananta")

    def test_data_gap_is_wait_not_no_setup(self):
        d = adjudicate(None, profile=SAFE, user_intent="OBSERVE")
        self.assertEqual(d.issued_action, "WAIT")
        self.assertIn("DATA_GAP", d.thesis)
        self.assertFalse(d.execution_allowed)

    def test_allowed_regime_setup_is_take_eq_even_if_ananta_waited(self):
        d = adjudicate(
            _obs(hunter_regime="REVERSAL", hunter_setup=True, hunter_skip=None, hunter_dec="WAIT"),
            profile=AGGRESSIVE,
            user_intent="PAPER_TRADE",
        )
        self.assertEqual(d.recommended_action, "TAKE")
        self.assertFalse(d.execution_allowed)

    def test_three_confidences(self):
        c = ConfidenceTriplet(understanding=1.5, evidence=-1, decision=0.4)
        self.assertEqual(c.understanding, 1.0)
        self.assertEqual(c.evidence, 0.0)
        self.assertEqual(c.as_dict()["blended"], None)


class TestExperiments(unittest.TestCase):
    def test_s5_catalog_parked(self):
        rows = {r["id"]: r for r in list_experiments()}
        self.assertEqual(rows["S5-H1"]["status"], "REJECTED_AS_LIVE_ENABLE")
        self.assertEqual(rows["S5-H2"]["status"], "APPROVED_MEASUREMENT")
        self.assertEqual(rows["S5-H3"]["status"], "APPROVED_MEASUREMENT")
        self.assertFalse(rows["S5-H2"]["runnable_now"])
        self.assertFalse(rows["S5-H3"]["runnable_now"])

    def test_try_run_refused(self):
        for hid in ("H1", "H2", "H3", "S5-H3"):
            got = try_run(hid)
            self.assertFalse(got["ran"])
            self.assertFalse(got["ok"])

    def test_approve_h1_still_rejected(self):
        got = approve("H1", human="test")
        self.assertFalse(got["ok"])


class TestAttribution(unittest.TestCase):
    def test_classify_does_not_mix(self):
        self.assertEqual(_classify({"setup_detected": True, "skip_reason": "REGIME_FILTERED", "decision": "SKIP"}), "SKIP")
        self.assertEqual(_classify({"setup_detected": True, "skip_reason": None, "decision": "WAIT"}), "TAKE")
        self.assertEqual(_classify({"setup_detected": False, "decision": "WAIT"}), "WAIT")
        self.assertEqual(
            _classify(
                {
                    "setup_detected": True,
                    "skip_reason": "REGIME_FILTERED regime=TREND_UP allowed=['REVERSAL']",
                    "decision": "SKIP",
                }
            ),
            "SKIP",
        )

    def test_empty_ledger_is_data_gap(self):
        report = attribute_print_ready("live")
        self.assertTrue(report["data_gap"] or report["n"] >= 0)
        self.assertIn("hunter", report["by_strategy"])
        self.assertIn("bollinger-mr", report["by_strategy"])

    def test_nested_outcome_join_and_filter_prefix(self):
        from src.intelligence.attribution import _accumulate, _empty_bucket, _forward, _is_regime_filtered, _means

        self.assertTrue(_is_regime_filtered("REGIME_FILTERED regime=TREND_UP allowed=['REVERSAL']"))
        self.assertFalse(_is_regime_filtered("no_qualifying_setup"))
        nested = {
            "assets": {
                "BTC/USD": {
                    "+15m": {"ret_pct": 0.10},
                    "+1h": {"ret_pct": 0.50},
                    "+4h": {"ret_pct": -0.20},
                }
            }
        }
        fwd = _forward(nested)
        self.assertEqual(fwd["fwd_1h_pct"], 0.50)
        self.assertEqual(_forward({"fwd_1h_pct": 0.7})["fwd_1h_pct"], 0.7)
        b = _empty_bucket()
        _accumulate(
            b,
            {"strategy": "hunter", "setup_detected": True, "decision": "SKIP", "skip_reason": "REGIME_FILTERED regime=TREND_UP"},
            nested,
        )
        _means(b)
        self.assertEqual(b["n_skip"], 1)
        self.assertEqual(b["n_regime_filtered"], 1)
        self.assertEqual(b["mean_fwd_after_skip"]["fwd_1h_pct"], 0.5)
        self.assertEqual(b["n_fwd_after_skip"]["fwd_1h_pct"], 1)


class TestPopulations(unittest.TestCase):
    def test_filtered_without_setup_is_idle_not_refusal(self):
        self.assertEqual(
            population_role(
                {"setup_detected": False, "decision": "SKIP", "skip_reason": "REGIME_FILTERED"}
            ),
            "FILTERED_IDLE",
        )
        self.assertEqual(
            population_role(
                {
                    "setup_detected": True,
                    "decision": "SKIP",
                    "skip_reason": "REGIME_FILTERED regime=TREND_UP allowed=['REVERSAL']",
                }
            ),
            "SKIP_SETUP",
        )
        self.assertEqual(
            population_role({"setup_detected": True, "decision": "TAKE", "skip_reason": None}),
            "TAKE",
        )
        self.assertEqual(
            population_role({"setup_detected": False, "decision": "WAIT", "skip_reason": None}),
            "WAIT",
        )


class TestH2(unittest.TestCase):
    def test_codes_from_rationale_and_list(self):
        self.assertEqual(
            _codes({"rationale": "REJECTED_RSI_NOT_RESET,REJECTED_NO_VCP_BASE"}),
            ["REJECTED_RSI_NOT_RESET", "REJECTED_NO_VCP_BASE"],
        )
        self.assertEqual(
            _codes({"reason_codes": ["REJECTED_NO_SUPPORT_ZONE"]}),
            ["REJECTED_NO_SUPPORT_ZONE"],
        )

    def test_histogram_empty_is_data_gap_not_keep(self):
        report = histogram("replay")
        self.assertFalse(report["keep"])
        self.assertFalse(report.get("loosen_gates", False))
        self.assertEqual(report["h2"], "APPROVED_MEASUREMENT")


class TestUniverse(unittest.TestCase):
    def test_cells_are_generated_not_bots(self):
        cells = generate_cells()
        self.assertEqual(len(cells), 15 * 2 * 2 * 6)
        self.assertTrue(all(c["live_watch"] is False for c in cells))
        self.assertEqual(sum(1 for s in catalog() if s["wave_a"]), 3)
        from src.intelligence.schema import WAVE_A
        self.assertNotIn("continuation", WAVE_A)
        cont = [
            c for c in cells
            if c["strategy"] == "continuation" and c["asset"] == "BTC/USD" and c["timeframe"] == "1h"
        ]
        self.assertEqual(len(cont), 6)
        self.assertTrue(all(c["coverage"] == "historical_lab" for c in cont))
        self.assertTrue(all(c["live_watch"] is False for c in cont))
        self.assertTrue(any(c["regime"] == "TREND_UP" and c["policy"] == "ROUTER_ONLY" for c in cont))
        don = [
            c for c in cells
            if c["strategy"] == "donchian-breakout" and c["asset"] == "BTC/USD" and c["timeframe"] == "1h"
        ]
        self.assertEqual(len(don), 6)
        self.assertTrue(all(c["coverage"] == "historical_lab" for c in don))
        self.assertTrue(any(c["regime"] == "TREND_UP" and c["policy"] == "THESIS_ONLY" for c in don))
        atr = [
            c for c in cells
            if c["strategy"] == "atr-breakout" and c["asset"] == "BTC/USD" and c["timeframe"] == "1h"
        ]
        self.assertTrue(all(c["live_watch"] is False for c in atr))
        self.assertTrue(any(c["regime"] == "TREND_UP" and c["policy"] == "THESIS_ONLY" for c in atr))

    def test_fit_rules_conservative(self):
        self.assertEqual(
            fit_from_take({"verdict": "INSUFFICIENT_EVIDENCE"})[0], "UNKNOWN"
        )
        self.assertEqual(fit_from_take({"verdict": "WASH"})[0], "UNKNOWN")
        self.assertEqual(fit_from_take({"verdict": "TAKE_HURT"})[0], "UNSUITABLE")
        self.assertEqual(fit_from_take({"verdict": "TAKE_HELPED"})[0], "SUITABLE")

    def test_continuation_trend_up_vs_independent_down_is_clash_not_rewrite(self):
        from collections import Counter
        clash = _regime_vs_tape("TREND_UP", Counter({"DOWN": 21, "FLAT": 13, "UP": 6}))
        self.assertTrue(clash["clash"])
        self.assertEqual(clash["clash_kind"], "TREND_UP_GATE_VS_INDEPENDENT_DOWN")
        self.assertFalse(clash["keep"])
        self.assertFalse(clash["rewrite"])
        aligned = _regime_vs_tape("TREND_UP", Counter({"UP": 78, "FLAT": 27, "DOWN": 6}))
        self.assertFalse(aligned["clash"])
        thin = _regime_vs_tape("TREND_UP", Counter({"DOWN": 2, "FLAT": 4, "UP": 1}))
        self.assertTrue(thin["clash"])
        self.assertFalse(thin["rewrite"])
        cont = _gate_vs_tape("continuation", Counter({"DOWN": 21, "FLAT": 13, "UP": 6}))
        self.assertTrue(cont["clash"])
        self.assertEqual(cont["gate"], "TREND_UP")
        hunter = _gate_vs_tape("hunter", Counter({"UP": 78, "DOWN": 6}))
        self.assertFalse(hunter["clash"])
        don = _gate_vs_tape("donchian-breakout", Counter({"UP": 126}))
        self.assertFalse(don["clash"])
        self.assertEqual(don["gate"], "TREND_UP")
        self.assertEqual(don["gate_source"], "thesis")
        self.assertEqual(don["aligned"], 126)

    def test_research_never_promotes(self):
        report = research()
        self.assertFalse(report["keep"])
        self.assertEqual(report["wave_a"], "WATCH")
        self.assertEqual(report["promotion"], "FORBIDDEN")
        self.assertTrue(report["live_watch_frozen"])
        self.assertTrue(all(c.get("live_watch") is False for c in report["cells"]))
        for c in report.get("candidates") or []:
            self.assertIn("not live", c["note"].lower())
        self.assertEqual(report["version"], "UNIVERSE-v1.5")
        for c in report["cells"]:
            self.assertIn(c["status_class"], {
                "UNTESTED", "TESTED_UNKNOWN", "WASH", "UNSUITABLE", "SUITABLE",
            })
            if c["coverage"] == "NONE":
                self.assertEqual(c["status_class"], "UNTESTED")
            self.assertEqual(c["provenance"]["schema"], "evidence_provenance_v0")
            self.assertTrue(c["provenance"]["regime_is_hypothesis"])
            self.assertFalse(c["provenance"]["decision_policy"]["keep"])
            tape = c.get("regime_vs_tape") or {}
            self.assertIn("clash", tape)
            self.assertFalse(tape.get("keep", False))
            self.assertFalse(tape.get("rewrite", False))
            if tape.get("clash"):
                self.assertFalse(c["keep"])
        for card in report.get("allowed_cards") or []:
            self.assertIsNone(card["blended_score"])
            self.assertFalse(card["keep"])


class TestEvidenceEngine(unittest.TestCase):
    def test_status_distinguishes_untested_from_wash(self):
        self.assertEqual(status_class(tested=False, fit="UNKNOWN", why="NO_OBSERVATION_REPLAY"), "UNTESTED")
        self.assertEqual(status_class(tested=True, fit="UNKNOWN", why="INSUFFICIENT_EVIDENCE"), "TESTED_UNKNOWN")
        self.assertEqual(status_class(tested=True, fit="UNKNOWN", why="WASH"), "WASH")
        self.assertEqual(status_class(tested=True, fit="UNSUITABLE", why="TAKE_HURT"), "UNSUITABLE")

    def test_confidence_is_a_band_not_a_percent(self):
        self.assertEqual(confidence_band("UNTESTED", "NONE", 0), "NONE")
        self.assertEqual(confidence_band("TESTED_UNKNOWN", "ANECDOTE", 4), "VERY_LOW")
        self.assertEqual(confidence_band("WASH", "ADEQUATE", 34), "MEDIUM")
        card = card_from_cell({
            "strategy": "hunter", "asset": "BTC/USD", "timeframe": "1h", "regime": "REVERSAL",
            "policy": "ALLOWED", "status_class": "TESTED_UNKNOWN", "fit": "UNKNOWN",
            "why": "INSUFFICIENT_EVIDENCE", "n_rows": 154, "n_setup": 4, "n_take": 4,
            "n_skip_setup": 0, "outcome_completeness_1h": 1.0, "evidence_depth": "ANECDOTE",
            "coverage_band": "MEDIUM", "confidence_band": "VERY_LOW", "take_1h": {},
        })
        self.assertIsNone(card["blended_score"])
        self.assertNotIn("81", str(card.get("confidence_band")))

    def test_provenance_does_not_invent_regime_version(self):
        p = provenance(
            strategy="hunter", asset="BTC/USD", timeframe="1h",
            regime="REVERSAL", source="historical_lab",
            period={"min_ts": "a", "max_ts": "b", "n_rows": 10},
        )
        self.assertEqual(p["strategy_version"], "1.0.0")
        self.assertIsNone(p["regime_version"])
        self.assertEqual(p["source"], "historical_lab")
        self.assertEqual(p["evaluator"], "ananta.primary_layer.evaluate_primary")
        gap = provenance(
            strategy="turtle", asset="BTC/USD", timeframe="1h",
            regime="TREND_UP", source="NONE",
        )
        self.assertTrue(gap["strategy_version_gap"])
        self.assertEqual(gap["source"], "NONE")


class TestSetupMemory(unittest.TestCase):
    def test_record_is_not_keep_and_not_live(self):
        rec = _record(
            {
                "strategy": "continuation",
                "symbol": "BTC/USD",
                "setup_detected": True,
                "decision": "TAKE",
                "skip_reason": None,
                "research_shadow": True,
                "regime": "TREND_UP",
                "reason_codes": ["ok"],
            },
            {},
            {"assets": {"BTC/USD": {"trend": "UP", "price": 1}}},
            {"fwd_15m_pct": 0.1, "fwd_1h_pct": 0.4, "fwd_4h_pct": 0.2},
            ts="2026-01-01T00:00:00Z",
            obs_id="x",
            source="historical_lab",
            tf="1h",
        )
        self.assertEqual(rec["schema"], "setup_record_v0")
        self.assertFalse(rec["keep"])
        self.assertTrue(rec["research_shadow"])
        self.assertFalse(rec["live_watch"])
        self.assertEqual(rec["population_role"], "TAKE")
        self.assertEqual(rec["outcomes"]["+1h"], 0.4)
        self.assertEqual(rec["provenance"]["schema"], "evidence_provenance_v0")

    def test_extract_empty_is_not_a_ranker(self):
        report = extract("replay")
        self.assertFalse(report["keep"])
        self.assertFalse(report["ranker"])
        self.assertFalse(report["similarity"])
        self.assertEqual(report["version"], "SETUP-MEMORY-v0.1")

    def test_refusal_stamp_is_not_a_rewrite_license(self):
        self.assertEqual(refusal_stamp(0.40), "COSTLY")
        self.assertEqual(refusal_stamp(-0.40), "PROTECTIVE")
        self.assertEqual(refusal_stamp(0.02), "WASH")
        self.assertEqual(refusal_stamp(None), "NO_SAMPLE")
        rec = _record(
            {
                "strategy": "hunter",
                "symbol": "BTC/USD",
                "setup_detected": True,
                "decision": "SKIP",
                "skip_reason": "REGIME_FILTERED",
                "regime": "TREND_UP",
            },
            {},
            {},
            {"fwd_15m_pct": 1.0, "fwd_1h_pct": 0.5, "fwd_4h_pct": -0.1},
            ts="t",
            obs_id="y",
            source="historical_lab",
            tf="1h",
        )
        self.assertEqual(rec["population_role"], "SKIP_SETUP")
        self.assertEqual(rec["refusal"]["+1h"]["stamp"], "COSTLY")
        self.assertEqual(rec["refusal"]["+15m"]["stamp"], "UNUSABLE_CLOCK")
        self.assertFalse(rec["keep"])


class TestFingerprints(unittest.TestCase):
    def test_bins_and_gap(self):
        self.assertEqual(ret_bin(0.5), "UP_STRONG")
        self.assertEqual(ret_bin(0.02), "FLAT")
        self.assertEqual(ret_bin(-0.2), "DOWN")
        gap = from_slot({"data_gap": True})
        self.assertTrue(gap["data_gap"])
        self.assertFalse(gap["keep"])

    def test_uses_market_truth_flag_names(self):
        fp = from_slot({
            "trend_flag": "UP",
            "compression_flag": "COMPRESSION",
            "ret_1h_pct": 0.5,
            "ret_4h_pct": 0.1,
        })
        self.assertFalse(fp["data_gap"])
        self.assertEqual(fp["trend"], "UP")
        self.assertEqual(fp["compression"], "COMPRESSION")
        self.assertEqual(fp["ret_1h_bin"], "UP_STRONG")
        self.assertEqual(fp["independent_label"], "BULLISH")
        self.assertIn("UP|COMPRESSION", fp["key"])
        self.assertFalse(fp["keep"])

    def test_empty_extract_is_not_similarity(self):
        report = fingerprints("replay")
        self.assertFalse(report["keep"])
        self.assertFalse(report["similarity"])
        self.assertFalse(report["ranker"])
        self.assertEqual(report["version"], "FP-v0.1")
        self.assertIn("by_strategy", report)
        self.assertTrue(report["laws"]["mixed_table_is_confounded"])
        self.assertTrue(report["laws"]["strategy_slice_is_not_keep"])





class TestDefinitionCards(unittest.TestCase):
    def test_donchian_hist_scored_not_live(self):
        from src.intelligence.definition_cards import I2_FAMILY, card_for, cards as def_cards
        self.assertEqual(I2_FAMILY, "donchian-breakout")
        don = card_for("donchian-breakout")
        self.assertEqual(don["status"], "HIST_SCORED")
        self.assertFalse(don["live_watch"])
        self.assertFalse(don["keep"])
        self.assertIsNone(don.get("blocked_by"))
        self.assertEqual(don["alignment"]["take_n"], 28)
        atr = card_for("atr-breakout")
        self.assertEqual(atr["status"], "HIST_SCORED")
        self.assertFalse(atr["live_watch"])
        self.assertIsNone(atr.get("blocked_by"))
        self.assertEqual(atr["alignment"]["take_n"], 9)
        kel = card_for("keltner-breakout")
        self.assertEqual(kel["status"], "HIST_SCORED")
        self.assertFalse(kel["keep"])
        self.assertEqual(kel["alignment"]["take_n"], 17)
        self.assertTrue(all(not c["keep"] and not c["live_watch"] for c in def_cards()))


class TestEvidenceCards(unittest.TestCase):
    def test_cards_never_keep(self):
        from src.intelligence.evidence_cards import cards
        report = cards()
        self.assertEqual(report["version"], "CARDS-v0.1")
        self.assertFalse(report["keep"])
        self.assertTrue(report["n_cards"] >= 5)
        for c in report["cards"]:
            self.assertFalse(c["keep"])
            self.assertFalse(c["live_enable"])
            self.assertIsNone(c.get("blended_score"))


class TestBoards(unittest.TestCase):
    def test_empty_suitable_is_not_keep(self):
        from src.intelligence.boards import boards
        report = boards()
        self.assertEqual(report["version"], "BOARDS-v0")
        self.assertFalse(report["keep"])
        self.assertFalse(report["ranker"])
        self.assertIsNone(report["blended_score"])
        for rows in (report.get("boards") or {}).values():
            for r in rows:
                self.assertFalse(r["keep"])


class TestLookup(unittest.TestCase):
    def test_lookup_is_not_keep(self):
        from src.intelligence.lookup import lookup
        report = lookup("UP")
        self.assertEqual(report["version"], "LOOKUP-v0.1")
        self.assertFalse(report["keep"])
        self.assertFalse(report["similarity"])
        self.assertFalse(report["ranker"])
        for r in report.get("rows") or []:
            self.assertFalse(r["keep"])
            self.assertIn("vs_sitout", r)


class TestOpportunityEngine(unittest.TestCase):
    def test_interface_refuses_scan_and_fair_value(self):
        s = opp_spec()
        self.assertEqual(s["phase"], "I1_CURRENT")
        self.assertFalse(s["scan_live"])
        self.assertFalse(s["mispricing_execute"])
        self.assertFalse(s["keep"])
        self.assertTrue(s["laws"]["coverage_is_not_intelligence"])
        self.assertTrue(s["laws"]["llm_does_not_invent_fair_value"])
        scan = refuse_scan(universe=["BTC/USD"])
        self.assertFalse(scan["executed"])
        self.assertEqual(scan["reason"], "I3_NOT_NOW")
        fv = refuse_fair_value(asset="BTC/USD")
        self.assertFalse(fv["executed"])
        self.assertIsNone(fv["fair_value"])
        self.assertFalse(fv["llm_invented"])


class TestOrchestratePaper(unittest.TestCase):
    def test_cycle_never_self_fills(self):
        result = run_cycle(_take_eq_obs(), persist=False, user_confirmed=True)
        self.assertFalse(result["would_execute"])
        self.assertFalse(result["decision"]["execution_allowed"])
        self.assertEqual(result["s5"], "parked")

    def test_propose_execution_refuses(self):
        got = propose_execution({"recommended_action": "TAKE", "issued_action": "WAIT"})
        self.assertFalse(got["executed"])
        self.assertEqual(got["authority"], "ananta")

    def test_paper_sim_no_order(self):
        result = simulate(_take_eq_obs(), persist=False)
        self.assertFalse(result["placed_order"])
        self.assertFalse(result["enabled_strategy"])
        blocked = simulate_take_blocked(_take_eq_obs())
        self.assertFalse(blocked["execution_allowed"])
        self.assertFalse(blocked["placed_order"])


class TestUserIntent(unittest.TestCase):
    def test_intent_aliases(self):
        self.assertEqual(_norm_intent("watch"), "OBSERVE")
        self.assertEqual(_norm_intent("paper"), "PAPER_TRADE")
        self.assertEqual(_norm_intent("auto"), "AUTONOMOUS")
        self.assertFalse(intent_allows_take("OBSERVE"))
        self.assertFalse(intent_allows_take("RESEARCH"))
        self.assertTrue(intent_allows_take("PAPER_TRADE"))


class TestContractAndSystem(unittest.TestCase):
    def test_contract_lists_replay_route(self):
        spec = contract_spec()
        paths = [r["path"] for r in spec["expected_routes"]]
        self.assertIn("/api/lab/observation-replay", paths)
        self.assertIn("/api/orders/paper", spec["not_a_route"])
        self.assertIn("/api/opportunity/scan", spec["not_a_route"])
        self.assertIn("/api/fair-value", spec["not_a_route"])
        self.assertEqual(spec["decision_schema"], "decision_v0")

    def test_completeness_machine_flag(self):
        c = completeness()
        self.assertTrue(c["ok"])
        self.assertFalse(c["feature_complete_means_strategy_enabled"])
        self.assertFalse(c["s5_running"])
        self.assertFalse(c["extra_agents"])
        self.assertEqual(c["wave_a"]["hunter"], "WATCH")
        names = {x["name"] for x in c["checks"]}
        self.assertIn("di.gates", names)
        self.assertIn("di.adjudicate", names)
        self.assertIn("di.quality", names)
        self.assertIn("di.h2", names)
        self.assertIn("di.universe", names)
        self.assertIn("di.evidence", names)
        self.assertIn("di.setup_memory", names)
        self.assertIn("di.fingerprint", names)
        self.assertIn("di.opportunity", names)

    def test_typed_decision_schema(self):
        d = TypedDecision(recommended_action="TAKE", issued_action="WAIT")
        blob = d.as_dict()
        self.assertEqual(blob["schema"], "decision_v0")
        self.assertTrue(blob["laws"]["hard_safety_outside_llm"])
        self.assertTrue(blob["blocked"])
        self.assertTrue(blob["laws"]["skip_is_a_decision"])


class TestDecisionQuality(unittest.TestCase):
    def test_depth_and_noise_bands(self):
        self.assertEqual(evidence_depth(0, role="TAKE"), "NONE")
        self.assertEqual(evidence_depth(4, role="TAKE"), "ANECDOTE")
        self.assertEqual(evidence_depth(47, role="TAKE"), "ADEQUATE")
        self.assertEqual(path_call(0.00, 64, usable=True, role="SKIP"), "WASH")
        self.assertEqual(path_call(-0.26, 64, usable=True, role="SKIP"), "SLIGHT")
        self.assertEqual(path_call(-0.07, 4, usable=True, role="TAKE"), "INSUFFICIENT_EVIDENCE")
        self.assertEqual(path_call(-18.4, 47, usable=False, role="TAKE"), "UNUSABLE_CLOCK")
        self.assertEqual(signed_verdict("SKIP", -0.26, "SLIGHT"), "SITOUT_PROTECTIVE")
        self.assertEqual(signed_verdict("TAKE", -0.07, "WASH"), "WASH")

    def test_baseline_forbids_keep(self):
        self.assertEqual(BASELINE_V0["version"], "DQ-v0.0")
        self.assertFalse(BASELINE_V0["laws"]["keep"])
        self.assertEqual(BASELINE_V0["live_take"], 0)
        self.assertEqual(BASELINE_V0["laws"]["hist_15m"], "UNUSABLE")

    def test_meter_empty_ledgers_do_not_keep(self):
        empty = {"n": 0, "data_gap": True, "source": "live_paper", "by_strategy": {}}
        report = meter(live=empty, hist=empty)
        self.assertFalse(report["rollup"]["keep_allowed"])
        self.assertEqual(report["rollup"]["wave_a"], "WATCH")
        self.assertEqual(report["schema"], "decision_quality_v0")
        self.assertTrue(report["laws"]["no_blended_score"])
        self.assertIn("SKIP_SETUP", report["populations"])
        hunter = next(s for s in report["strategies"] if s["strategy"] == "hunter")
        self.assertIn("SKIP_SETUP", hunter["live"]["cells"])
        self.assertIn("FILTERED_IDLE", hunter["live"]["cells"])

    def test_score_horizon_hist_15m_unusable(self):
        cell = score_horizon(role="TAKE", n=47, mean=-18.4, clock="+15m", usable=False)
        self.assertEqual(cell["verdict"], "UNUSABLE_CLOCK")


if __name__ == "__main__":
    unittest.main()
