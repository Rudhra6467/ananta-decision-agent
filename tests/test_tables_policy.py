"""Tape-independent tables + policy contract. No network. No live enable."""
from __future__ import annotations

import unittest

from src.intelligence.knowledge_tables import snapshot, VERSION as TABLES_V
from src.intelligence.opportunity_engine import make_candidate, make_fair_value, spec as opp_spec
from src.intelligence.policy_contract import evaluate_stub, spec as policy_spec, LIVE_WIRED


class TestKnowledgeTables(unittest.TestCase):
    def test_missing_artifacts_are_gaps_not_keep(self):
        report = snapshot()
        self.assertEqual(report["version"], TABLES_V)
        self.assertFalse(report["keep"])
        self.assertFalse(report["ranker"])
        self.assertFalse(report["scan"])
        self.assertFalse(report["live_enable"])
        self.assertTrue(report["laws"]["missing_file_is_data_gap"])
        self.assertIn("memory", report["tables"])


class TestPolicyContract(unittest.TestCase):
    def test_not_wired_and_cannot_take(self):
        self.assertFalse(LIVE_WIRED)
        s = policy_spec()
        self.assertFalse(s["keep"])
        self.assertFalse(s["live_wired"])
        self.assertEqual(s["wave_a"], "WATCH")
        self.assertTrue(s["veto"]["can_only_block"])
        self.assertFalse(s["veto"]["can_create_take"])
        stub = evaluate_stub(fingerprint={"n": 2})
        self.assertEqual(stub["issued_action"], "UNKNOWN")
        self.assertFalse(stub["take"])
        wide = evaluate_stub(fingerprint={"n": 20})
        self.assertEqual(wide["issued_action"], "WAIT")
        self.assertFalse(wide["take"])


class TestOpportunityBuilders(unittest.TestCase):
    def test_incomplete_candidate_and_llm_fair_value_refuse(self):
        self.assertEqual(opp_spec()["version"], "OPP-v0.2")
        c = make_candidate({"asset": "BTC/USD"})
        self.assertFalse(c["ok"])
        self.assertFalse(c["live"])
        self.assertIn("strategy", c["missing"])
        fv = make_fair_value({"asset": "BTC/USD", "model": "llm", "llm_invented": True})
        self.assertFalse(fv["execute"])
        self.assertTrue(fv["llm_invented"])
        self.assertEqual(fv["reason"], "LLM_INVENTED_FAIR_VALUE")
        self.assertIsNone(fv["fair_value"])


if __name__ == "__main__":
    unittest.main()
