"""27 Nov 2026 (flag 291, Madhav 26 Nov 22:22: "Yes, let's set it up"): the holding grade shown in two parts, outlook and fit, with the
result on what was paid shown and not counted, and the holdings where the grade and the weak-against-the-market check disagree. Shown only."""
from india import gradesplit as G

W = {"above_200d": 15, "above_20d": 10, "rsi_healthy": 10, "regime_fit": 20, "volatility": 10, "liquidity": 10, "concentration": 10, "result": 15}
H = [
    {"symbol": "AAA", "grade": "A", "score": 91, "action": "ADD", "rated": True, "weight_pct": 10, "pnl_pct": 295,
     "parts": {"trend": 35, "regime": 20, "volatility": 5, "liquidity": 6, "concentration": 10, "result": 15}},
    {"symbol": "BBB", "grade": "B", "score": 56, "action": "HOLD", "rated": True, "weight_pct": 6, "pnl_pct": 8,
     "parts": {"trend": 10, "regime": 10, "volatility": 5, "liquidity": 6, "concentration": 10, "result": 15}},
    {"symbol": "CCC", "grade": "C", "score": 41, "action": "TRIM", "rated": True, "weight_pct": 22, "pnl_pct": 16,
     "parts": {"trend": 0, "regime": 10, "volatility": 5, "liquidity": 6, "concentration": 5, "result": 15}},
    {"symbol": "DDD", "grade": "not graded", "score": 13, "action": "HOLD", "rated": False, "weight_pct": 2, "pnl_pct": -54, "parts": {}},
]


def test_outlook_leaves_out_result_and_size():
    rows = {r["symbol"]: r for r in G.split(H, W)}
    assert rows["AAA"]["outlook"] == round(100 * 66 / 75)      # 35+20+5+6 of 75; the 15 result points and 10 size points are not in it
    assert rows["CCC"]["outlook"] == round(100 * 21 / 75)
    assert rows["CCC"]["fit"] == "large" and rows["AAA"]["fit"] == "within size"
    assert rows["AAA"]["result_pct"] == 295                      # shown as a fact
    assert rows["DDD"]["outlook"] is None and rows["DDD"]["rated"] is False


def test_disagreement_with_the_weak_check():
    rows = {r["symbol"]: r for r in G.split(H, W, weak={"BBB"})}
    assert rows["BBB"]["disagree"] is True                       # weak against the market, yet the grade says keep
    assert rows["AAA"]["disagree"] is False and rows["CCC"]["disagree"] is False
    assert "disagree on BBB" in G.words(list(rows.values()))


def test_words_say_shown_only():
    w = G.words(G.split(H, W))
    assert "shown only" in w and "not counted" in w and "CCC" in w
