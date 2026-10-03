"""Review #12 (docs/research/REVIEW_12.md): T3's exit vs trailing exits, on the review #4 simulator.

    python -m src.research.t3_exits --db .../lab5_5m.sqlite --out ~/ananta_runs/t3_exits

Every variant enters with T3's rule; only the exit differs. The decision for day d+1 uses closes up to day d only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.research import portfolio_trend as PT
from src.research import reads as R
from src.research import zones as Z

VARIANTS = ("T3", "T3Z", "T3A", "T3W")


def _zone_stop(A: Z.Arr, i: int, swing: list[dict], close: float) -> float | None:
    """Bottom of the highest zone below the close, minus 0.5 daily range (zones from bars before day i+1)."""
    below = [z for z in Z.zone_map(A, i + 1, swing) if z["top"] < close]
    if not below or math.isnan(A.atr[i]):
        return None
    return max(z["bot"] for z in below) - 0.5 * float(A.atr[i])


def exit_signals(data: dict[str, pd.DataFrame], days: pd.DatetimeIndex, full: dict[str, list[tuple]]) -> dict[str, pd.DataFrame]:
    base = PT.signals(data, days)
    entry = base["T3"].fillna(False)
    C = pd.DataFrame({k: v["c"] for k, v in data.items()}).reindex(days)
    e50 = pd.DataFrame({k: PT.ema(v["c"], 50).reindex(days) for k, v in data.items()})
    gate = (C["BTC"] > e50["BTC"]).fillna(False)
    out = {"T3": entry, "_avail": base["_avail"]}
    for v in ("T3Z", "T3A", "T3W"):
        on = pd.DataFrame(False, index=days, columns=C.columns)
        for coin in C.columns:
            S = R.Series(full[coin])
            A = Z.Arr(S)
            ix = {pd.Timestamp(t, unit="s"): k for k, t in enumerate(S.t)}
            holding, stop, peak = False, None, None
            swing, swing_at = None, -999
            for d, day in enumerate(days):
                c = C.at[day, coin]
                if not np.isfinite(c):
                    holding = False
                    continue
                if not holding:
                    if entry.at[day, coin]:
                        holding, stop, peak = True, None, c
                    else:
                        continue
                if not gate.at[day]:
                    holding = False
                    continue
                k = ix.get(day)
                if v == "T3W":
                    if c < e50.at[day, coin]:
                        holding = False
                        continue
                elif v == "T3A":
                    peak = max(peak, c)
                    atr = A.atr[k] if k is not None else float("nan")
                    if k is not None and not math.isnan(atr) and c < peak - 3 * atr:
                        holding = False
                        continue
                else:                                                   # T3Z
                    if k is not None and k >= 400:
                        if k - swing_at >= Z.REFRESH:
                            swing, swing_at = Z.swing_zones(A, k + 1), k
                        if stop is not None and c < stop:
                            holding = False
                            continue
                        s = _zone_stop(A, k, swing, c)
                        if s is not None:
                            stop = s if stop is None else max(stop, s)
                on.at[day, coin] = True
        out[v] = on & base["_avail"]
    return out


def run(db: str, out: Path) -> dict:
    data = {c: PT.daily(db, c) for c in PT.COINS}
    data = {k: v for k, v in data.items() if len(v)}
    cache = Path(os.path.expanduser("~/ananta_runs/reads"))
    full = {c: R.cached_daily(db, c, cache, R.CONF_END) for c in data}
    days = pd.date_range(min(v.index.min() for v in data.values()), max(v.index.max() for v in data.values()), freq="D")
    sig = exit_signals(data, days, full)
    rep: dict = {"review": "docs/research/REVIEW_12.md", "variants": {}}
    for v in VARIANTS:
        sim = PT.simulate(data, days, sig[v], sig["_avail"])
        eq, exp = sim["equity"], sim["exposure"]
        start = eq.index[eq.index >= eq.index[0] + pd.Timedelta(days=50)][0]
        eq = eq[eq.index >= start]
        crisis = {}
        for k, (a, b) in PT.CRISES.items():
            w = eq[(eq.index >= pd.Timestamp(a) - pd.Timedelta(days=1)) & (eq.index <= pd.Timestamp(b))]
            crisis[k] = round(100 * (w.iloc[-1] / w.iloc[0] - 1), 1) if len(w) > 1 else None
        rep["variants"][v] = {"DISCOVERY": PT.metrics(eq[eq.index < PT.DISC_END], exp), "CONFIRM": PT.metrics(eq[eq.index >= PT.DISC_END], exp),
                              "trades": sim["trades"], "costs_paid_pct_of_start": round(100 * sim["costs"], 2), "crisis_pct": crisis}
    t3 = rep["variants"]["T3"]
    for v in VARIANTS[1:]:
        x = rep["variants"][v]
        x["beats_T3_mar"] = {sp: (x[sp].get("mar") or -9) > (t3[sp].get("mar") or -9) for sp in ("DISCOVERY", "CONFIRM")}
        x["status"] = "PASS" if all(x["beats_T3_mar"].values()) else "FAIL"
    (out / "review12_results.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", default="~/ananta_runs/t3_exits")
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r = run(a.db, out)
    for v, x in r["variants"].items():
        print(v, x.get("status", "CONTROL"), json.dumps({k: x[k] for k in ("DISCOVERY", "CONFIRM", "trades", "costs_paid_pct_of_start", "crisis_pct")}))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
