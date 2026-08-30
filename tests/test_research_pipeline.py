from __future__ import annotations

import unittest

from src.intelligence.laws import LAWS
from src.intelligence.research_pipeline import ADAPTERS, NEXT_SLICE, refuse_bulk_score, spec


class TestResearchPipeline(unittest.TestCase):
    def test_lock_is_process_not_dump(self):
        s = spec()
        self.assertEqual(s["version"], "PIPELINE-v1.1")
        self.assertFalse(s["keep"])
        self.assertFalse(s["run_everything"])
        self.assertTrue(s["acquire_years"])
        self.assertEqual(s["stance"]["discovery"], "aggressive")
        self.assertEqual(s["stance"]["capital"], "conservative")
        self.assertEqual(NEXT_SLICE["asset"], "ETH/USD")
        self.assertFalse(NEXT_SLICE["live"])
        self.assertTrue(ADAPTERS["crypto"]["now"])
        self.assertFalse(ADAPTERS["india"]["now"])
        self.assertTrue(LAWS["aggressive_discovery"])
        self.assertTrue(LAWS["conservative_capital"])
        bulk = refuse_bulk_score(years=4, assets=10)
        self.assertFalse(bulk["ran"])
        self.assertTrue(bulk["acquire_years"])


if __name__ == "__main__":
    unittest.main()
