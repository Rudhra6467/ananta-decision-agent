"""Dump-fix regressions. Warehouse rank must not become evidence_ids."""
from __future__ import annotations

import json
import unittest

from src.intelligence.cite_allowlist import (
    CONTEXT_CITES_DEPLOYED,
    apply_new_row,
    filter_evidence_ids,
)

CATALOG = [
    "card.continuation.r3.v1",
    "card.seq2.two_candle.10m.v0",
    "card.hunter.r3.v1",
    "s2.hunter.sync",
    "card.squeeze.r3.v1",
    "card.set16.move_cold_lag.v1",
    "card.set14.lag_birth.v1",
    "card.h1.volume_shock.v1",
    "card.mrd.sync_after_vol.v0",
    "card.mrd.size_after_vol.v0",
    "card.hot.birth.set15.v1",
]


class CiteAllowlistTest(unittest.TestCase):
    def test_empty_cited_does_not_inherit_catalog(self):
        out = filter_evidence_ids([], knowledge_ids=CATALOG)
        self.assertEqual(out["evidence_ids"], ["NOT_MEASURED"])
        self.assertEqual(out["stripped"], [])
        self.assertTrue(out["knowledge_ids_ignored"])
        self.assertNotIn("card.set14.lag_birth.v1", out["evidence_ids"])

    def test_range_family_dump_is_stripped(self):
        proposed = [
            "card.set14.lag_birth.v1",
            "card.hot.birth.set15.v1",
            "card.seq2.two_candle.10m.v0",
            "card.continuation.r3.v1",
            "s2.squeeze.sync",
        ]
        out = filter_evidence_ids(proposed, knowledge_ids=CATALOG)
        self.assertEqual(out["evidence_ids"], ["NOT_MEASURED"])
        self.assertIn("card.set14.lag_birth.v1", out["stripped"])
        self.assertIn("card.continuation.r3.v1", out["stripped"])
        self.assertIn("card.hot.birth.set15.v1", out["stripped"])

    def test_live_five_kept_and_aliased(self):
        out = filter_evidence_ids(
            ["h1.volume_shock.v1", "card.hunter.r3.v1", "card.set14.lag_birth.v1"]
        )
        self.assertEqual(
            out["evidence_ids"],
            ["card.h1.volume_shock.v1", "card.hunter.r3.v1"],
        )
        self.assertEqual(out["stripped"], ["card.set14.lag_birth.v1"])

    def test_context_cites_not_deployed(self):
        self.assertFalse(CONTEXT_CITES_DEPLOYED)
        out = filter_evidence_ids(
            ["card.set16.move_cold_lag.v1", "runtime.guardrails.v1"]
        )
        self.assertEqual(out["evidence_ids"], ["NOT_MEASURED"])
        self.assertIn("card.set16.move_cold_lag.v1", out["stripped"])
        self.assertFalse(out["context_cites_deployed"])

    def test_apply_new_row_does_not_touch_bar_open(self):
        row = {
            "last_bar_open": "2026-09-27T07:00:00+00:00",
            "evidence_ids_json": "[]",
        }
        payload = {}
        snap = {
            "cited": [],
            "knowledge_ids": CATALOG,
            "selected_strategy": "card.continuation.r3.v1",
        }
        apply_new_row(
            row, payload, snap, agent_version="DI-LOOP-v1-l2-g1g7-persist"
        )
        self.assertEqual(row["last_bar_open"], "2026-09-27T07:00:00+00:00")
        self.assertEqual(json.loads(row["evidence_ids_json"]), ["NOT_MEASURED"])
        self.assertFalse(payload["versions"]["backfill"])
        self.assertEqual(payload["versions"]["card_version"], "UNKNOWN")
        self.assertFalse(payload["counts_for_m2"])
        self.assertNotIn("set14", row["evidence_ids_json"])


if __name__ == "__main__":
    unittest.main()
