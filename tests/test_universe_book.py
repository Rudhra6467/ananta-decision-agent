from __future__ import annotations

import unittest

from src.intelligence.books import artifact, ledger_path
from src.tools.observation_log import REPLAY_LOG


class TestUniverseBookPaths(unittest.TestCase):
    def test_eth_artifact_suffix(self):
        self.assertEqual(str(artifact("universe_knowledge", "replay")), "universe_knowledge.json")
        self.assertEqual(str(artifact("universe_knowledge", "eth")), "universe_knowledge_eth.json")
        self.assertEqual(str(artifact("fingerprint_report", "eth")), "fingerprint_report_eth.json")
        self.assertNotEqual(ledger_path("eth"), REPLAY_LOG)


if __name__ == "__main__":
    unittest.main()
