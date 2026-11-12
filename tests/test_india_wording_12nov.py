"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120), G-23 (trader's wording on India): 'uptrend' beside 'a death cross'
of 162 sessions ago for the same index, and a coin flip said to score 9 of 15 with no word that it is one seeded draw (chance alone
averages 7.5). Each check failed against the code before. No live data."""
import json

from india import morningview, readmodel, technicals

TECH = {"status": "ok", "name": "NIFTY 50", "close": 25800.0, "as_of": "2026-11-11", "change_1d": 0.004,
        "vs_sma": {"20": 0.01, "50": 0.03, "200": 0.05}, "rsi14": 61.0, "rsi_zone": "neutral",
        "cross_50_200": {"state": "below", "last_cross": "2026-03-16", "direction": "down", "sessions_ago": 162, "searched_from": "2015-01-01"},
        "macd": {"state": "above", "last_signal_cross": "2026-11-03"}, "support": {"swing_low": 25300.0}, "resistance": {"swing_high": 26100.0},
        "vs_high_52w": -0.01}


def test_an_old_cross_the_price_has_left_behind_is_said_as_what_is_still_true():
    w = technicals.words(json.loads(json.dumps(TECH)))
    assert "death cross" not in w and "the 50-day is still below the 200-day (it crossed on" in w and "the price is now above both" in w
    t = json.loads(json.dumps(TECH))
    t["vs_sma"] = {"20": -0.01, "50": -0.02, "200": -0.01}                                # below both: the cross still describes it
    assert "a death cross" in technicals.words(t)


def test_the_coin_flip_is_named_as_one_draw_beside_what_chance_averages(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper").mkdir()
    rows = [{"kind": "call", "data_through": "2026-11-11", "call": "BULLISH", "rule": "call-v0"}]
    rows += [{"kind": "score", "horizon": 1, "data_through": f"2026-10-{d:02d}", "score": 1 if d % 3 == 0 else -1, "null_score": 1 if d % 5 else -1}
             for d in range(10, 25)]
    (tmp_path / "paper" / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = readmodel.call("2026-11-11")
    assert c["scored"] == 15 and "one seeded draw (chance alone averages 7.5)" in c["words"]
    w = morningview._chances_words({}, {"scored": 15, "hits": 5, "coin_flip_hits": 9}, {}, 12)
    assert "against 9 for a coin flip, one seeded draw (chance alone averages 7.5)" in w
