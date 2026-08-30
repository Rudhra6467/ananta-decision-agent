from __future__ import annotations

import unittest

from src.intelligence.research_pipeline import ADAPTERS, refuse_bulk_score, spec


class TestResearchPipeline(unittest.TestCase):
    def test_lock_is_process_not_dump(self):
        s = spec()
        self.assertEqual(s["version"], "PIPELINE-v1")
        self.assertFalse(s["keep"])
        self.assertFalse(s["run_everything"])
        self.assertTrue(s["laws"]["point_in_time_only"])
        self.assertTrue(s["laws"]["india_after_trust"])
        self.assertTrue(ADAPTERS["crypto"]["now"])
        self.assertFalse(ADAPTERS["india"]["now"])
        self.assertFalse(ADAPTERS["canada"]["now"])
        bulk = refuse_bulk_score(years=4, assets=10)
        self.assertFalse(bulk["ran"])
        self.assertEqual(bulk["reason"], "NO_RUN_EVERYTHING")


if __name__ == "__main__":
    unittest.main()
