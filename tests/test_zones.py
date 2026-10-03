"""Zones (review #6 engine): built only from earlier bars, find a support that held twice, judge visits honestly."""
import math
import random

from src.research import reads as R
from src.research import zones as Z
from tests.test_reads import _bars


def _walk(n=900, seed=4):
    rnd = random.Random(seed)
    c = [100.0]
    for _ in range(n):
        c.append(c[-1] * math.exp(rnd.gauss(0, 0.03)))
    return _bars(c, [100 + 30 * rnd.random() for _ in c])


def test_zone_map_never_looks_ahead():
    D = _walk()
    full = Z.Arr(R.Series(D))
    for i in (450, 600, 750):
        cut = Z.Arr(R.Series(D[:i]))
        a = [(round(z["bot"], 9), round(z["top"], 9), sorted(z["kinds"]), z.get("tier")) for z in Z.zone_map(full, i)]
        b = [(round(z["bot"], 9), round(z["top"], 9), sorted(z["kinds"]), z.get("tier")) for z in Z.zone_map(cut, i)]
        assert a == b, i


def test_a_level_that_held_twice_is_strong_and_outcomes_are_judged_in_order():
    # a floor near 100 visited and held twice (each time a rally of 30%), then price above it
    c = [130.0] * 450
    for _ in range(2):
        c += [130 - 6 * k for k in range(1, 6)] + [101.0, 100.0, 101.0] + [100 + 6 * k for k in range(1, 8)] + [142.0] * 40
    c += [140.0] * 30
    D = _bars(c, wick=0.005)
    A = Z.Arr(R.Series(D))
    zs = [z for z in Z.zone_map(A, len(D)) if "SWING" in z["kinds"] and z["bot"] <= 100.0 <= z["top"] + 1]
    assert zs and zs[0]["tier"] == "STRONG" and zs[0]["held"] >= 2, zs
    # a visit that closes far below the band is BROKEN even if the day opened high
    D2 = D + [(D[-1][0] + 86400, 140.0, 140.0, 80.0, 82.0, 100.0)]
    A2 = Z.Arr(R.Series(D2))
    z = zs[0]
    atr = A2.atr[len(D2) - 2]
    assert Z.touch_outcome(A2, len(D2) - 1, z["bot"], z["top"], atr, len(D2)) == "BROKEN"


def test_summary_counts_market_events_and_live_zones_run():
    D = _walk()
    live = Z.live_zones(D)
    assert live["zones"] and all(r["state"] in ("INSIDE", "TESTED", "APPROACHING", "FAR") for r in live["zones"])
    import json as _json
    _json.dumps(live)                                                # plain numbers only (the API returns it)
    evs = [{"t": 0, "result": "HELD", "r10": 0.01, "w_atr": 1.0},
           {"t": 86400, "result": "HELD", "r10": 0.02, "w_atr": 1.0},
           {"t": 30 * 86400, "result": "BROKEN", "r10": -0.01, "w_atr": 1.0}]
    s = Z.summarize(evs, {0: 0.5, 1: 0.5, 2: 0.5, 3: 0.5})
    assert s["market_events"] == 2 and s["held"] == 2 and s["broken"] == 1
    assert s["edge_pts"] == 0.0                                       # events: +0.5 and -0.5 over the 50% random rate


def test_no_zone_group_passes_on_pure_noise():
    """Amendments 1-2: on the frozen 10-walk calibration no group passes the bar, and the review uses that bias."""
    import json as _json
    import pathlib

    cal = _json.loads((pathlib.Path(__file__).resolve().parents[1] / "docs" / "research" / "zones_rw_calibration.json").read_text())
    for g, s in cal["groups"].items():
        assert not (s["edge_pts"] >= 8 and (s["z"] or 0) >= 2.5 and s["market_events"] >= 30), (g, s)
    assert set(Z.rw_bias()) >= set(Z.GROUPS)
    d = Z.corrected({"edge_pts": 10.0, "z": 2.0}, -5.0)
    assert d["edge_corrected_pts"] == 15.0 and d["z_corrected"] == 3.0


def test_live_zone_board_lookout_and_visit_record(tmp_path):
    from jarvis.service import zones_watch as W
    from tests.test_reads import _fake_jarvis

    W._CACHE.clear()
    D = _walk(700, seed=11)
    j = _fake_jarvis(tmp_path, {"BTC": D, "SOL": D}, {})
    b = W.board(j)
    assert {r["coin"] for r in b["coins"]} == {"BTC", "SOL"}
    for r in b["coins"]:
        assert all(z["history"] in ("SUPPORTED", "NOT_SUPPORTED", "UNTESTED") for z in r["zones"])
    c = W.coin(j, "SOL")
    assert c["in_zone"] == bool(c["inside"]) and (c["lookout"] is not None) == c["in_zone"]
    w1 = W.watch(j)
    w2 = W.watch(j)
    assert w2["new"] == [] and len(W.recent(j, 10 ** 5)) == len(w1["new"])           # each entry recorded once


def test_lookout_reactions_have_a_frozen_noise_calibration_and_never_look_ahead():
    D = _walk(700, seed=21)
    S = R.Series(D)
    full = Z.Arr(S)
    cut = Z.Arr(R.Series(D[:601]))
    z = {"bot": 90.0, "top": 95.0, "kinds": {"SWING"}, "tier": "NEW"}
    assert Z.reactions(S, full, S, 600, z) == Z.reactions(R.Series(D[:601]), cut, R.Series(D[:601]), 600, z)
    assert set(Z.lookout_bias()) == set(Z.REACTIONS)
    d = Z._corr({"diff_pts": 30.0, "z": 3.0}, 30.0)
    assert d["diff_corrected_pts"] == 0.0 and d["z_corrected"] == 0.0
