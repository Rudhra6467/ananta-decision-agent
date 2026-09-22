"""M1-C L2 pathway. Family first. Sample size is not applicability. No paper_take."""
from __future__ import annotations

import unittest

from src.intelligence.l2_pathway import (
    LEGAL_ISSUED,
    issued_from_decision,
    rank,
    run_pathway,
    select,
    state_from_observation,
)


BTC = {
    "id": "btc.trend_up.2026-09-21",
    "asset": "BTC",
    "tf": "1h",
    "regime": "TREND_UP",
    "direction": "LONG",
    "volatility": "EXPANDING",
    "momentum": "POSITIVE",
    "structure": "INTACT",
    "liquidity": "NORMAL",
    "continuation_would_qualify": True,
    "hunter_qualifying": False,
    "squeeze_qualifying": False,
    "observer_match": None,
}

ADA = {
    "id": "ada.set16.2026-09-20",
    "asset": "ADA",
    "tf": "15m",
    "regime": "LAG",
    "direction": "LONG",
    "volatility": "LOW",
    "momentum": "LOW",
    "structure": "LAG",
    "liquidity": "NORMAL",
    "continuation_would_qualify": False,
    "hunter_qualifying": False,
    "squeeze_qualifying": False,
    "observer_match": "set16",
}

HUNTER = {
    "id": "btc.hunter.hypothetical",
    "asset": "BTC",
    "tf": "1h",
    "regime": "REVERSAL",
    "direction": "LONG",
    "volatility": "UNKNOWN",
    "momentum": "UNKNOWN",
    "structure": "REVERSAL",
    "liquidity": "NORMAL",
    "continuation_would_qualify": False,
    "hunter_qualifying": True,
    "squeeze_qualifying": False,
    "observer_match": None,
}


class L2PathwayTest(unittest.TestCase):
    def test_btc_trend_up_is_shadow_paper_not_take(self):
        out = run_pathway(BTC)
        d = out["decision"]
        self.assertEqual(d["label"], "SHADOW_PAPER")
        self.assertEqual(d["action"], "NO_TRADE")
        self.assertEqual(d["reason"], "BEST_AVAILABLE_STRATEGY_HAS_NO_PAPER_AUTHORITY")
        self.assertEqual(d["best_id"], "card.continuation.r3.v1")
        self.assertFalse(d["paper_take"])
        self.assertFalse(d["keep"])
        self.assertFalse(d["exec"])
        self.assertFalse(d["counts_for_m2"])
        self.assertEqual(issued_from_decision(d), "SHADOW_PAPER")
        self.assertNotEqual(issued_from_decision(d), "TAKE")

    def test_seq2_sample_does_not_beat_continuation(self):
        rows = rank(BTC)
        ids = [r["id"] for r in rows]
        self.assertLess(ids.index("card.continuation.r3.v1"), ids.index("card.seq2.two_candle.10m.v0"))
        seq = next(r for r in rows if r["id"] == "card.seq2.two_candle.10m.v0")
        cont = next(r for r in rows if r["id"] == "card.continuation.r3.v1")
        self.assertEqual(cont["family_match"], "HIGH")
        self.assertEqual(seq["type"], "when_not")
        self.assertLess(seq["score"], cont["score"])
        hunter = next(r for r in rows if r["id"] == "card.hunter.r3.v1")
        self.assertEqual(hunter["family_match"], "LOW")
        self.assertLess(ids.index("card.continuation.r3.v1"), ids.index("card.hunter.r3.v1"))

    def test_ada_set16_is_watch_not_take(self):
        out = run_pathway(ADA)
        d = out["decision"]
        self.assertEqual(d["label"], "WATCH")
        self.assertEqual(d["action"], "WATCH")
        self.assertEqual(d["reason"], "MATCH_NOT_TAKE")
        self.assertEqual(d["best_id"], "card.set16.move_cold_lag.v1")
        self.assertFalse(d["paper_take"])
        self.assertFalse(d["counts_for_m2"])

    def test_hunter_qualifying_is_wait_not_school_take(self):
        out = run_pathway(HUNTER)
        d = out["decision"]
        self.assertEqual(d["label"], "WAIT")
        self.assertEqual(d["reason"], "SCHOOL_CORE_NO_NAMED_VARIANT")
        self.assertEqual(issued_from_decision(d), "WAIT")
        self.assertFalse(d["counts_for_m2"])

    def test_state_from_observation_maps_trend_up(self):
        obs = {
            "id": "obs_btc",
            "regime": "TREND_UP",
            "system_truth": {
                "strategy_observations": [
                    {"strategy": "hunter", "setup_detected": False},
                    {"strategy": "squeeze", "setup_detected": False},
                ]
            },
        }
        st = {"asset": "BTC/USD", "fingerprint": "UP|EXPANSION|UP_STRONG|BULLISH", "trend_flag": "UP", "regime": "TREND_UP"}
        s = state_from_observation(obs, st, {})
        self.assertEqual(s["regime"], "TREND_UP")
        self.assertTrue(s["continuation_would_qualify"])
        self.assertFalse(s["hunter_qualifying"])

    def test_legal_issued_never_includes_take(self):
        self.assertNotIn("TAKE", LEGAL_ISSUED)
        fake = {"label": "TAKE", "action": "TAKE", "paper_take": False}
        self.assertEqual(issued_from_decision(fake), "NO_TRADE")


if __name__ == "__main__":
    unittest.main()
