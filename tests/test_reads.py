"""Madhav's reads (review #5): each read fires on the shape it describes, never looks ahead, and the live summary works."""
import math
import random

from src.research import reads as R

DAY = 86400


def _bars(closes, vols=None, wick=0.01, t0=1_500_000_000 // DAY * DAY):
    vols = vols or [100.0] * len(closes)
    out, prev = [], closes[0]
    for k, (c, v) in enumerate(zip(closes, vols)):
        o = prev
        out.append((t0 + k * DAY, o, max(o, c) * (1 + wick), min(o, c) * (1 - wick), c, v))
        prev = c
    return out


def _bull_then_bear(n_bear=330, start=100.0, end=30.0):
    """A year and a half of gentle rise, then a long slide to the lows."""
    up = [start * (1 + 0.002) ** k for k in range(300)]
    top = up[-1]
    down = [top * math.exp(math.log(end / top) * k / n_bear) for k in range(1, n_bear + 1)]
    return up + down


def test_m1_fires_on_capitulation_at_the_lows():
    c = _bull_then_bear()
    c += [c[-1] * 0.93, c[-1] * 0.85, c[-1] * 0.78]          # three crash days into the low
    v = [100.0] * (len(c) - 2) + [300.0, 400.0]
    D = _bars(c, v)
    S = R.Series(D)
    i = len(D) - 1
    r = R.m1(S, i, S, "M1a")
    assert R.fired(r), [x for x in r["conditions"] if not x["ok"]]
    assert r["stop"] < D[-1][3]
    # one quiet day earlier it is not capitulation yet
    assert not R.fired(R.m1(S, i - 2, S, "M1a"))


def test_m2_fires_on_a_higher_low_retest():
    c = _bull_then_bear()
    c += [c[-1] * 0.85]                                         # the first low
    low = c[-1]
    c += [low * (1 + 0.02 * k) for k in range(1, 8)]            # rally to about +14%
    c += [low * 1.10, low * 1.07, low * 1.06]                   # back down: a higher low, momentum better
    D = _bars(c)
    S = R.Series(D)
    i = len(D) - 1
    r = R.m2(S, i, S, "M2a")
    assert R.fired(r), [x for x in r["conditions"] if not x["ok"]]
    assert r["first_low"] < D[i][3]


def test_m3_fires_in_a_quiet_base_after_a_run_and_on_the_breakout():
    rnd = random.Random(3)
    c = [100.0] * 200 + [100 * (1 + 0.01 * k) for k in range(1, 41)]   # flat, then a +48% run
    v = [100.0] * len(c)
    top = c[-1]
    for k in range(30):                                         # 30 quiet days inside a 6% band, drifting up
        c.append(top * (0.95 + 0.001 * k + 0.01 * rnd.random()))
        v.append(50.0)
    D = _bars(c, v, wick=0.004)
    # before the base the days were wide; inside they are narrow
    D = [(t, o, h * (1.03 if k < len(D) - 30 else 1), l * (0.97 if k < len(D) - 30 else 1), cl, vv) for k, (t, o, h, l, cl, vv) in enumerate(D)]
    S = R.Series(D)
    i = len(D) - 1
    if (S.c[i] - min(S.l[i - 25:i + 1])) / (max(S.h[i - 25:i + 1]) - min(S.l[i - 25:i + 1])) < 0.5:
        D[-1] = (D[-1][0], D[-1][1], D[-1][2] * 1.01, D[-1][3], max(S.h[i - 25:i + 1]) * 0.995, D[-1][5])
        S = R.Series(D)
    a = R.m3(S, i, S, "M3a")
    assert R.fired(a), [x for x in a["conditions"] if not x["ok"]]
    # next day closes above the base: the classic breakout read fires
    t, o = D[-1][0] + DAY, D[-1][4]
    D2 = D + [(t, o, a["base_top"] * 1.06, o * 0.995, a["base_top"] * 1.05, 120.0)]
    S2 = R.Series(D2)
    b = R.m3(S2, len(D2) - 1, S2, "M3b")
    assert R.fired(b), [x for x in b["conditions"] if not x["ok"]]


def test_reads_never_look_ahead():
    rnd = random.Random(9)
    c = [100.0]
    for _ in range(900):
        c.append(c[-1] * math.exp(rnd.gauss(0, 0.04)))
    D = _bars(c, [100 + 50 * rnd.random() for _ in c])
    full = R.Series(D)
    for i in (500, 650, 800):
        cut = R.Series(D[:i + 1])
        for v in R.VARIANTS:
            a = R.READERS[v[:2]](full, i, full, v)
            b = R.READERS[v[:2]](cut, i, cut, v)
            assert (a is None) == (b is None)
            if a:
                assert [x["ok"] for x in a["conditions"]] == [x["ok"] for x in b["conditions"]], (v, i)
                assert abs(a["stop"] - b["stop"]) < 1e-9


def test_history_counts_events_not_coins_and_live_summary():
    c = _bull_then_bear() + [20.0] * 5
    D = _bars(c)
    rows = [{"t": D[400][0], "x30": 0.1, "r7": 0.0, "r30": 0.1, "r90": None, "mae30": -0.05, "managed30": 0.05, "stopped": False, "coin": "A"},
            {"t": D[403][0], "x30": 0.3, "r7": 0.0, "r30": 0.3, "r90": None, "mae30": -0.05, "managed30": 0.05, "stopped": True, "coin": "B"},
            {"t": D[450][0], "x30": -0.1, "r7": 0.0, "r30": -0.1, "r90": None, "mae30": -0.2, "managed30": -0.1, "stopped": True, "coin": "A"}]
    s = R.summarize(rows)
    assert s["episodes"] == 3 and s["events"] == 2
    assert abs(s["mean_excess30_pct"] - 5.0) < 1e-6                 # events: mean(0.1, 0.3) = 0.2 and -0.1
    assert R.verdict({"events": 3}, {"events": 5}) == "INSUFFICIENT"
    live = R.read_coin(D, D, {"M1a": "SUPPORTED"})
    assert [r["variant"] for r in live["reads"]] == ["M1a", "M2a", "M3a", "M3b"]
    assert all(r["state"] in ("FIRED", "CLOSE", "NO", "NO_DATA") for r in live["reads"])
    assert live["reads"][0]["history"] == "SUPPORTED"
