"""Green-run journal v1: run counting, no lookahead, pessimistic fills/exits, costs, holdout never loaded."""
import sqlite3
import tempfile
from pathlib import Path

try:
    import numpy as np
    import pandas as pd

    from src.research import green_runs as gr
except ImportError:  # the agent venv has no numpy; these run where the research stack exists
    np = None

T0 = 1_600_000_000 - (1_600_000_000 % 86400)


def _bars(n, seed=1):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.0005, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    v = rng.uniform(5, 15, n)
    return {"t": T0 + 300 * np.arange(n, dtype=np.int64), "o": o, "h": h, "l": lo, "c": c, "v": v}


def test_run_length():
    if np is None:
        return
    o = np.array([1, 1, 1, 1, 1, 1.0])
    c = np.array([2, 2, 0, 2, 2, 2.0])
    assert list(gr.run_length(o, c)) == [1, 2, 0, 1, 2, 3]


def test_no_lookahead_in_event_context():
    if np is None:
        return
    b = _bars(70 * 288)
    full = gr.events_for(b, None)
    full = full[full["k"] > 0]
    pick = full.iloc[[len(full) // 2, len(full) - 50]]
    for _, row in pick.iterrows():
        i = int(row["i"])
        cut = {k: v[: i + 2].copy() for k, v in b.items()}  # everything after bar i+1 removed
        cut["c"][-1] *= 1.5  # and the next bar changed: context at i must not move
        part = gr.events_for(cut, None)
        r2 = part[(part["i"] == i) & (part["k"] == row["k"])]
        assert len(r2) == 1
        for f in gr.FEAT + ["s"]:
            assert int(r2.iloc[0][f]) == int(row[f]), f


def _sim(o, h, lo, c, i, s, entry, ex, rl=0.0):
    return gr._sim_one(np.array(o, float), np.array(h, float), np.array(lo, float), np.array(c, float), i, s, entry, ex, rl)


def test_stop_first_when_both_touched_and_gap_fills_at_open():
    if np is None:
        return
    n = 60
    o, h, lo, c = [100.0] * n, [100.2] * n, [99.8] * n, [100.0] * n
    h[3], lo[3] = 102.0, 98.0  # both B1 levels inside one bar after entry at o[2]=100
    g, ek, xk, f = _sim(o, h, lo, c, 1, 0, 0, 0)
    assert xk == gr.KIND_STOP and abs(g - (-0.01)) < 1e-12 and ek == 0
    o2, h2, lo2 = list(o), list(h), list(lo)
    h2[3], lo2[3] = 100.2, 99.8
    o2[4], h2[4], lo2[4] = 97.0, 97.1, 96.9  # gap below the stop: fill at the open
    g, ek, xk, f = _sim(o2, h2, lo2, c, 1, 0, 0, 0)
    assert xk == gr.KIND_STOP and abs(g - (-0.03)) < 1e-12


def test_limit_fill_bar_cannot_take_the_target_and_unfilled_is_no_trade():
    if np is None:
        return
    n = 60
    o, h, lo, c = [100.0] * n, [100.1] * n, [99.9] * n, [100.0] * n
    o[0], c[0], o[1], c[1] = 98.0, 99.0, 99.0, 100.0  # 2 greens: run 98 -> 100; PB50 limit = 99
    lo[3], h[3] = 98.9, 101.0  # fills at 99 intrabar; the same bar reaches +1.5% (100.485) -> not allowed
    g, ek, xk, f = _sim(o, h, lo, c, 1, 0, 2, 0)
    assert f == 1 and ek == 1 and xk == gr.KIND_TIME  # not a target on the fill bar; flat to the time exit
    o3, lo3 = list(o), [99.95] * n
    g, ek, xk, f = _sim(o3, h, lo3, c, 1, 0, 2, 0)
    assert f == 0 and np.isnan(g)


def test_costs_arithmetic():
    if np is None:
        return
    g, ek, xk = np.array([0.03]), np.array([0], np.int8), np.array([gr.KIND_TARGET], np.int8)
    n = gr.net_of(g, ek, xk, "BTC", "NDAX_NOW")[0]
    assert abs(n - (0.03 - (0.002 + 0.00178) - 1.03 * 0.002)) < 1e-6
    assert abs(gr.net_of(g, ek, xk, "BTC", "ZERO_FEE")[0] - (0.03 - 0.00178)) < 1e-6


def test_holdout_is_never_loaded():
    if np is None:
        return
    d = Path(tempfile.mkdtemp()) / "x.sqlite"
    con = sqlite3.connect(d)
    con.execute("CREATE TABLE bars (instrument TEXT, event_unix INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    for t in (gr.CONF_END - 600, gr.CONF_END - 300, gr.CONF_END, gr.CONF_END + 300):
        con.execute("INSERT INTO bars VALUES ('BTC-USD-SPOT', ?, 1, 1, 1, 1, 1)", (t,))
    con.commit()
    con.close()
    b = gr.load_5m(str(d), "BTC")
    assert b["t"].max() < gr.CONF_END and len(b["t"]) == 2


def test_cells_pipeline_smoke():
    if np is None:
        return
    out = Path(tempfile.mkdtemp())
    for k, coin in enumerate(("AAA", "BBB")):
        b = _bars(70 * 288, seed=k + 3)
        df = gr.events_for(b, None)
        I, S, K = df["i"].to_numpy(np.int64), df["s"].to_numpy(np.int64), df["k"].to_numpy(np.int64)
        RL = gr._run_lows(b["l"], S, I)
        for ei, en in enumerate(gr.ENTRIES):
            for xi, xn in enumerate(gr.EXITS):
                g, ek, xk = gr._sim_all(b["o"], b["h"], b["l"], b["c"], I, S, K, RL, ei, xi)
                for cost in gr.COSTS:
                    df[f"{en}_{xn}_{cost}"] = gr.net_of(g, ek, xk, coin, cost)
        df["coin"], df["year"], df["day"] = coin, 2020, (df["t_close"] // 86400).astype(int)
        df.to_pickle(out / f"events_{coin}.pkl")
    c = gr.cells_for_combo(str(out), "NOW", "B1")
    assert set(c["cost"]) == set(gr.COSTS) and (c["n"] > 0).all()
    w = gr.wide(c.assign(split=0))
    assert "pass_discovery" in w and not w["pass_confirm"].any()


if __name__ == "__main__":
    import inspect

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn) and not inspect.signature(fn).parameters:
            fn()
            print("ok", name)
