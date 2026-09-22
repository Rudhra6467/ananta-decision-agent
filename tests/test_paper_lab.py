"""G1-G7 laboratory contracts. paper_take stays false."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.intelligence.hands_funnel import LOOK_STATES, UNIVERSE, emit, from_writer
from src.intelligence.coverage_matrix import matrix
from src.intelligence.snapshot import build as build_snap
from src.intelligence.exit_engine import plan
from src.intelligence.counterfactual import open_case, close_case
from src.intelligence.comparison_abc import freeze_human, compare
from src.intelligence.paper_ledger import empty_book, refuse_fill
from src.intelligence.ranking_law import never_global_mean, explain
from src.intelligence.decision_store import persist_snapshot


class FunnelTest(unittest.TestCase):
    def test_empty_is_never_looked(self):
        row = emit({})
        self.assertEqual(row["look_class"], "NEVER_LOOKED")
        self.assertEqual(row["issued_TAKE"], 0)
        self.assertFalse(row["paper_take"])
        self.assertEqual(len(row["per_asset"]), 10)
        self.assertEqual(row["look_class_counts"]["NEVER_LOOKED"], 10)

    def test_taxonomy_is_seven(self):
        self.assertEqual(len(LOOK_STATES), 7)
        self.assertEqual(len(UNIVERSE), 10)

    def test_looked_partial_not_full_universe(self):
        row = emit(
            {
                "issued": "NO_TRADE",
                "assets_named": ["BTC"],
                "assets_evaluated": 1,
                "bars_evaluated": 64,
                "looked": True,
                "qualified_candidates": 0,
            }
        )
        self.assertEqual(row["look_class"], "LOOKED_PARTIAL")
        self.assertEqual(row["per_asset"]["BTC"]["look_class"], "LOOKED_NOTHING_VALID")
        self.assertEqual(row["look_class_counts"]["NEVER_LOOKED"], 9)
        self.assertIn("universe_not_fully_evaluated", row["coverage_gaps"])

    def test_from_writer_does_not_invent_universe(self):
        l2 = {
            "state": {"asset": "ETH", "tf": "1h"},
            "ranked": [
                {
                    "id": "card.continuation.r3.v1",
                    "family_match": "HIGH",
                    "type": "strategy",
                    "result": "REFUSE",
                    "refuse_reasons": ["BENCHED"],
                }
            ],
        }
        row = from_writer({"id": "obs1", "ts": "t"}, {"asset": "ETH/USD"}, {"candidate": {"id": "c1"}}, l2, "SHADOW_PAPER")
        self.assertEqual(row["assets_evaluated"], 1)
        self.assertNotIn("ETH", row["universe_gap"])
        self.assertGreaterEqual(len(row["universe_gap"]), 8)
        self.assertEqual(row["issued_TAKE"], 0)
        self.assertEqual(row["look_class"], "LOOKED_PARTIAL")
        self.assertEqual(row["per_asset"]["ETH"]["look_class"], "LOOKED_SHADOW")
        self.assertEqual(row["per_asset"]["BTC"]["look_class"], "NEVER_LOOKED")
        self.assertFalse(row["per_asset"]["BTC"]["invented"])


class CoverageLedgerTest(unittest.TestCase):
    def test_no_state_is_paper_eligible(self):
        m = matrix("TREND_UP")
        self.assertEqual(m["paper_eligible_states"], [])
        self.assertFalse(m["paper_take"])

    def test_ledger_closed(self):
        self.assertEqual(empty_book()["status"], "CLOSED_UNTIL_G8")
        self.assertEqual(refuse_fill()["last_refuse"], "PAPER_GATE_CLOSED")

    def test_exit_does_not_open(self):
        p = plan(family="continuation", entry=100.0, stop=97.0, target=106.0)
        self.assertFalse(p["open"])
        self.assertEqual(p["blocked_reason"], "PAPER_GATE_CLOSED")

    def test_counterfactual_labels(self):
        case = open_case({"issued": "NO_TRADE", "timestamp": "t", "market_state": {"asset": "BTC", "regime": "TREND_UP"}, "reason": "x"})
        self.assertEqual(close_case(case, fwd_return_pct=4.2, mfe_pct=4.5, mae_pct=-0.4)["label"], "MISSED_OPPORTUNITY")
        self.assertEqual(close_case(case, fwd_return_pct=-3.5, mfe_pct=0.2, mae_pct=-3.5)["label"], "CORRECT_REFUSE")
        self.assertFalse(case["counts_for_m2"])

    def test_human_frozen(self):
        h = freeze_human({"asset": "BTC", "direction": "LONG", "setup": "trend", "market_state": "TREND_UP", "reason": "hh", "timestamp": "t0"})
        self.assertTrue(h["frozen"])
        self.assertFalse(h["may_edit_ananta"])
        cmp = compare({"issued": "SHADOW_PAPER", "market_state": {"regime": "TREND_UP"}, "class_id": "AUTHORITY"}, h, None)
        self.assertIn("AUTHORITY", cmp["divergence_classes"])

    def test_no_global_average(self):
        law = never_global_mean([{"id": "a"}])
        self.assertIn("leaderboard", law["forbidden"])
        rows = explain([{"id": "a", "family_match": "HIGH", "score": 76, "type": "strategy"}, {"id": "b", "family_match": "HIGH", "score": 25, "type": "when_not"}])
        self.assertIn("family matches", rows[0]["why_above_next"])

    def test_g5_persists_sqlite_not_only_json(self):
        snap = build_snap(state={"asset": "ETH", "tf": "1h", "regime": "TREND_UP"}, issued="NO_TRADE", ts="2026-09-22T05:00:00Z")
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "agent_decisions.sqlite"
            saved = persist_snapshot(snap, funnel=emit({}), exit_plan=plan(family="continuation"), counterfactual=open_case(snap), paper_book=refuse_fill(), db_path=db)
            self.assertTrue(db.exists())
            self.assertEqual(saved["fills"], 0)
            self.assertFalse(saved["paper_take"])
            payload = json.loads(__import__("sqlite3").connect(str(db)).execute("SELECT payload_json FROM decisions").fetchone()[0])
            self.assertEqual(payload["fills"], 0)
            self.assertFalse(payload["counts_for_m2"])


if __name__ == "__main__":
    unittest.main()
