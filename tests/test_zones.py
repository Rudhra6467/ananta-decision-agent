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
    assert c["in_zone"] == bool(c["inside"]) and (c["lookout"] is not None) == bool(c["in_zone"] or c["tested"])
    assert c["attention"]["level"] in ("HIGH", "WATCH", "LOW") and isinstance(c["attention"]["why"], list)
    if c["lookout"]:
        assert {x["id"] for x in c["lookout"]["reactions"]} == set(Z.REACTIONS)
        assert next(x for x in c["lookout"]["reactions"] if x["id"] == "F6")["history"] == "PASS"
    import json as _json
    _json.dumps(b)
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


def test_news_recorder_checks_each_coin_once_a_day_and_stops_when_ai_is_off(tmp_path):
    from jarvis.service import news_watch as N
    from jarvis.service import zones_watch as W
    from tests.test_reads import _fake_jarvis

    W._CACHE.clear()
    D = _walk(700, seed=31)
    j = _fake_jarvis(tmp_path, {"BTC": D, "SOL": D, "ETH": D}, {})
    calls = []
    ok = lambda j_, c: calls.append(c) or {"verdict": "CLEAR", "why": "nothing about the coin itself"}          # noqa: E731
    first = N.watch(j, check=ok, max_per_run=2)
    second = N.watch(j, check=ok, max_per_run=20)
    assert len(first) == 2 and {x["coin"] for x in first + second} >= {"BTC", "SOL", "ETH"}
    assert len(calls) == len(set(calls))                                   # never the same coin twice a day
    assert N.watch(j, check=ok) == []
    off = lambda j_, c: {"verdict": "NOT_CHECKED", "why": "off"}            # noqa: E731
    j.now = lambda: D[-1][0] + 5 * 86400                                   # a new day, AI switched off
    assert N.watch(j, check=off) == [] and N.latest(j, "SOL", 30)[0]["verdict"] == "CLEAR"


def test_review9_context_uses_only_earlier_days():
    from src.research import zone_splits as ZS

    D = _walk(700, seed=41)
    c1 = ZS.Context(D, D)
    c2 = ZS.Context(D[:601], D[:601])
    t = D[600][0] + 3600                                  # an entry during day 600
    assert c1.at(t, D[600][4]) == c2.at(t, D[600][4])     # what happens after day 600 never matters
    assert ZS.welch([1.0, 2.0, 3.0], [0.0, 0.5, 1.0]) > 0


def test_review10_exits_follow_their_rules():
    # flat at 100, entry at 100; the zone 95-98; next zone above at 110; price rises to 112 on day 5
    c = [100.0] * 450 + [100.0, 101, 103, 106, 112, 112] + [112.0] * 50
    D = _bars(c, wick=0.002)
    A = Z.Arr(R.Series(D))
    e = {"i": 450, "bot": 95.0, "top": 98.0, "atr": 2.0, "next_up": 110.0}
    x = Z.exits(A, e, 0.0)
    assert x["X2"].get("target") and abs(x["X2"]["net"] - 0.10) < 0.02          # sold at the next zone (+10%)
    assert not x["X4"]["stopped"] and x["X1"]["days"] == 20
    # a fall through the zone stops X2 at the next open after the close below 94
    c2 = [100.0] * 450 + [100.0, 97, 93, 90, 90] + [90.0] * 50
    x2 = Z.exits(Z.Arr(R.Series(_bars(c2, wick=0.002))), e, 0.0)
    assert x2["X2"]["stopped"] and x2["X4"]["stopped"] and x2["X2"]["net"] < 0


def test_credit_records_once_a_day_and_scores_twenty_days_later(tmp_path):
    from jarvis.service import credit as CR
    from jarvis.service import zones_watch as W
    from tests.test_reads import _fake_jarvis

    W._CACHE.clear()
    D = _walk(700, seed=51)
    j = _fake_jarvis(tmp_path, {"BTC": D[:670], "SOL": D[:670]}, {})
    assert CR.record(j) == 2 and CR.record(j) == 0                 # once per coin per day
    assert CR.settle(j) == 0                                        # not 20 days old yet
    con = __import__("sqlite3").connect(tmp_path / "explorer_bars.sqlite")
    con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?,?)", [(c, "1d", *b) for c in ("BTC", "SOL") for b in D[670:]])
    con.commit()
    assert CR.settle(j) == 2
    rep = CR.report(j)
    assert rep["settled"] == 2 and {x["signal"] for x in rep["by_signal"]} == set(CR.SIGNALS)
