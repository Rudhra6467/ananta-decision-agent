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
    assert [r["variant"] for r in live["reads"]] == ["M1a", "M2a", "M2a-G", "M3a", "M3b"]
    assert all(r["state"] in ("FIRED", "CLOSE", "NO", "NO_DATA") for r in live["reads"])
    assert live["reads"][0]["history"] == "SUPPORTED"


def _fake_jarvis(tmp_path, D_by_coin, status):
    import json as _json
    import sqlite3
    import types

    con = sqlite3.connect(tmp_path / "explorer_bars.sqlite")
    con.execute("CREATE TABLE bars (coin TEXT, tf TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, tf, t))")
    for coin, D in D_by_coin.items():
        con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?,?)", [(coin, "1d", *b) for b in D])
    con.commit()
    (tmp_path / "docs" / "knowledge").mkdir(parents=True)
    (tmp_path / "docs" / "knowledge" / "reads_status.json").write_text(_json.dumps({"variants": {k: {"status": v} for k, v in status.items()}}))
    last = max(D[-1][0] for D in D_by_coin.values())
    return types.SimpleNamespace(dir=tmp_path, db=sqlite3.connect(":memory:"), now=lambda: last + 2 * DAY)


def test_watch_records_each_fire_once_and_rings_only_supported_reads(tmp_path):
    from jarvis.service import reads_watch as W

    c = _bull_then_bear()
    c += [c[-1] * 0.93, c[-1] * 0.85, c[-1] * 0.78]
    D = _bars(c, [100.0] * (len(c) - 2) + [300.0, 400.0])
    for st, rings in (("NOT_SUPPORTED", False), ("SUPPORTED", True)):
        W._CACHE.clear()
        sub = tmp_path / st
        sub.mkdir()
        j = _fake_jarvis(sub, {"BTC": D, "SOL": D}, {"M1a": st})
        orig, W._status = W._status, (lambda j_, st=st: {"M1a": st})      # the review's status for this run
        pushed, asked = [], []
        news = lambda j_, coin: asked.append(coin) or {"verdict": "CLEAR", "why": "nothing about the coin itself"}   # noqa: E731
        b = W.board(j)
        assert {f["coin"] for f in b["fired"] if f["variant"] == "M1a"} == {"BTC", "SOL"}
        out = W.watch(j, push=lambda t, m: pushed.append((t, m)), check_news=news)
        assert {o["coin"] for o in out if o["variant"] == "M1a"} == {"BTC", "SOL"}
        assert bool(pushed) == rings and bool(asked) == rings
        assert all("Evidence, not an order" in o["message"] for o in out)
        assert W.watch(j, push=lambda t, m: pushed.append((t, m)), check_news=news) == []      # same fire: not again
        assert len(W.recent(j)) == len(out)
        W._status = orig


def test_layer_map_is_consistent_and_the_switch_works():
    import json as _json
    import pathlib

    from jarvis.service import layers as LY

    root = pathlib.Path(__file__).resolve().parents[1]
    m = _json.loads((root / "docs" / "knowledge" / "layers.json").read_text())
    ids = {c["id"] for c in m["components"]}
    assert len(ids) == len(m["components"]), "duplicate ids"
    status = set(m["meaning"]["status"])
    for c in m["components"]:
        assert 0 <= c["layer"] <= 8 and c["status"] in status, c["id"]
        for k in ("depends_on", "feeds"):
            assert set(c[k]) <= ids, (c["id"], k, set(c[k]) - ids)
        for f in c["files"]:
            assert (root / f).exists(), (c["id"], f)
        if c["status"] in ("DROPPED", "PLANNED", "EVIDENCE_ONLY"):
            assert not c["acts"], f"{c['id']} is {c['status']} but marked as acting"
    assert LY.allowed("T3", root) and not LY.allowed("READS", root) and not LY.allowed("ZONES", root) and not LY.allowed("NOPE", root)
    t3 = LY.component("T3", root)
    assert "REGIME" in t3["everything_it_rests_on"] and "DATA_5M" in t3["everything_it_rests_on"]
    assert "CHAIN" in LY.component("REGIME", root)["everything_that_would_feel_a_failure"]
    assert [l["n"] for l in LY.board(root)["layers"]] == list(range(9))


def test_every_code_file_is_on_the_layer_map_and_nothing_running_is_archived():
    """Madhav: map them all. Every module belongs to a part of the layer map, and no module a running program imports
    (Jarvis, voice, Explorer, hourly watch, portfolio layer) may sit only in the ARCHIVED part."""
    import glob
    import json as _json
    import os
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1]
    os.chdir(root)
    m = _json.loads((root / "docs" / "knowledge" / "layers.json").read_text())
    where: dict = {}
    for c in m["components"]:
        for f in c["files"]:
            where.setdefault(f, set()).add(c["status"])
    code = [f for f in glob.glob("src/**/*.py", recursive=True) + glob.glob("jarvis/**/*.py", recursive=True) + ["main.py"]
            if "__pycache__" not in f and "node_modules" not in f and not f.endswith(("__init__.py", "__main__.py"))]
    missing = sorted(f for f in code if f not in where)
    assert not missing, f"not on the layer map: {missing}"

    def mod(mn: str):
        p = mn.replace(".", "/")
        return next((x for x in (p + ".py", p + "/__init__.py") if os.path.exists(x)), None)

    def imports(f: str) -> set:
        t, out = open(f).read(), set()
        for line in t.splitlines():
            a = re.match(r"\s*from\s+((?:src|jarvis)(?:\.\w+)*)\s+import\s+([\w, ]+)", line)
            b = re.match(r"\s*import\s+((?:src|jarvis)(?:\.\w+)*)", line)
            if a:
                out |= {x for x in [mod(a.group(1))] + [mod(a.group(1) + "." + n.strip().split(" as ")[0]) for n in a.group(2).split(",")] if x}
            elif b and mod(b.group(1)):
                out.add(mod(b.group(1)))
        return out

    seen, todo = set(), ["jarvis/service/app.py", "jarvis/voice/server.py", "src/intelligence/explorer_live.py",
                         "src/intelligence/paper_watch.py", "src/intelligence/portfolio_layer.py"]
    while todo:
        f = todo.pop()
        if f not in seen:
            seen.add(f)
            todo += list(imports(f) - seen)
    archived_only = sorted(f for f in seen if not f.endswith("__init__.py") and where.get(f) == {"ARCHIVED"})
    assert not archived_only, f"running code marked ARCHIVED: {archived_only}"


def test_review8_filters_only_remove_fires():
    c = _bull_then_bear()
    c += [c[-1] * 0.93, c[-1] * 0.85, c[-1] * 0.78] + [c[-1] * 0.8] * 40
    D = _bars(c, [100.0] * (len(c) - 42) + [300.0, 400.0] + [100.0] * 40)
    S = R.Series(D)
    base = R.signals(S, S, "M1a")
    for f in ("Z", "G", "ZG"):
        keep = R.review8_filter(f"M1a-{f}", "X", S, S)
        assert set(R.signals(S, S, "M1a", keep)) <= {i for i in range(len(D)) if R.fired(R.m1(S, i, S, "M1a"))}
    assert R.signals(S, S, "M1a", lambda i: False) == [] and base
