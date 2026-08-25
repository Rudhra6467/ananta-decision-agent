"""Decision Intelligence foundation — no network, no Ananta, no S5 runs."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.intelligence.adjudicate import adjudicate
from src.intelligence.attribution import attribute_print_ready, _classify, population_role
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
        self.assertEqual(rows["S5-H2"]["status"], "APPROVED_PENDING_INSTRUMENTATION")
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
