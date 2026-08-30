from __future__ import annotations

import unittest

from src.intelligence.books import book, ledger_path
from src.tools.observation_log import REPLAY_LOG


class TestBooks(unittest.TestCase):
    def test_eth_is_sibling(self):
        self.assertEqual(book("eth"), "eth")
        self.assertEqual(book("replay-eth"), "eth")
        self.assertEqual(book("historical_lab"), "replay")
        self.assertEqual(ledger_path("replay"), REPLAY_LOG)
        self.assertNotEqual(ledger_path("eth"), REPLAY_LOG)
        self.assertTrue(str(ledger_path("eth")).endswith("ETHUSD.jsonl"))


if __name__ == "__main__":
    unittest.main()
