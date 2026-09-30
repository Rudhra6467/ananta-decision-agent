"""Study v3 — implements docs/research/STUDY_V3_FRESH.md exactly.

Regime-adaptive exits on the v2 entry, a trend-filtered hold reference, and equal-weight
buy-and-hold, judged at book level (mark-to-market daily equity) with real costs.

    python -m src.research.study_v3 run --db ~/ananta_runs/fresh10/fresh10_5m.sqlite --coins fresh --out ~/ananta_runs/study_v3_fresh
    python -m src.research.study_v3 run --db <lab5_5m.sqlite> --coins lab10 --out ~/ananta_runs/study_v3_lab10_reference
The fresh run writes a marker and refuses a second run.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from src.research import entry_v2 as v2
from src.research import mtf_entry as v1

VERSION = "study.v3"
FRESH10 = ["DOT", "ATOM", "ETC", "XLM", "TRX", "UNI", "FIL", "NEAR", "ALGO", "AAVE"]
LAB10 = v1.COINS
VARIANTS = ("V0_CANDIDATE", "V1_RIDE", "V2_ADAPTIVE", "V3_TREND_HOLD")
BPD = 288  # 5m bars per day
DAY = 86400
ERAS = (("E1_to_2021", 0, 1640995200), ("E2_2022_2023", 1640995200, 1704067200), ("E3_2024_on", 1704067200, 10**11))
NDAX_HS_LAB = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
FRESH_HS = 0.0040


def costs(coin: str, venue: str) -> dict[str, float]:
    if venue == "NDAX":
        hs = NDAX_HS_LAB.get(coin, FRESH_HS)
        return {"limit": 0.0020, "market": 0.0020 + hs}
    return {"limit": 0.0040, "market": 0.0080 + 0.0005}  # KRAKEN_T1


# ---------------------------------------------------------------------------
# Exits beyond v2
# ---------------------------------------------------------------------------
def first_daily_exit(t5: np.ndarray, t_entry: int, d_tc: np.ndarray, flag: np.ndarray) -> int | None:
    """Index of the 5m bar opening at/after the first daily close AFTER t_entry where flag is True."""
    d0 = int(np.searchsorted(d_tc, t_entry, side="right"))
    hits = np.flatnonzero(flag[d0:])
    if not hits.size:
        return None
    x = int(np.searchsorted(t5, d_tc[d0 + hits[0]], side="left"))
    return x if x < len(t5) else None


def sim_ride(o, h, lo, c, t5, j, e, A, partial, d_tc, below20) -> tuple[float, str, int]:
    n = len(t5)
    s0 = e - 2.5 * A
    last = min(n - 1, j + 60 * BPD - 1)
    xd = first_daily_exit(t5, int(t5[j]), d_tc, below20)
    stop_end = min(last, (xd - 1) if xd is not None else last)
    seg = lo[j:stop_end + 1]
    if partial and seg.size and seg[0] <= s0:
        return (s0 - e) / e, "STOP", j
    hs = np.flatnonzero(seg <= s0)
    if hs.size:
        k = j + int(hs[0])
        return (min(s0, o[k]) - e) / e, "STOP", k
    if xd is not None and xd <= last:
        return (o[xd] - e) / e, "DAILY_EMA20", xd
    kind = "TIME_60D" if last == j + 60 * BPD - 1 else "END"
    return (c[last] - e) / e, kind, last


# ---------------------------------------------------------------------------
# Per coin
# ---------------------------------------------------------------------------
def run_coin(db: str, coin: str) -> dict[str, Any]:
    t0 = time.time()
    b = v1.load_5m(db, coin)
    t5, o, h, lo, c = b["t"], b["o"], b["h"], b["l"], b["c"]
    n = len(t5)
    if n < 400 * BPD // 4:
        return {"coin": coin, "skipped": "insufficient_history", "bars": int(n)}
    S = v2.setups(b)
    d = v1.resample(b, "1d")
    dc = d["c"]
    e20, e50 = v1.ema(dc, 20), v1.ema(dc, 50)
    below20 = dc < e20
    e50_10 = np.r_[np.full(10, np.nan), e50[:-10]]
    strong = (dc > e20) & (e50 > e50_10)
    d_up = (dc > e50) & (e20 > e50)
    flag = S["flags"][("S3_TREND_CONTROL", "LONG")]
    ks = np.flatnonzero(flag)
    out: dict[str, Any] = {"coin": coin, "bars": int(n), "trades": {}, "first_ts": int(t5[0]), "last_ts": int(t5[-1]),
                           "daily_tc": d["tc"].tolist(), "daily_close": dc.tolist(),
                           "bh_entry": float(o[0]), "bh_exit": float(c[-1])}
    for var in VARIANTS:
        trades, last_exit = [], -1
        for k in ks:
            T = S["tc"][k]
            j0 = int(np.searchsorted(t5, T, side="left"))
            if j0 >= n - 1 or t5[j0] - T >= 3600 or j0 <= last_exit:
                continue
            A = S["A"][k]
            if var == "V3_TREND_HOLD":
                j, e, entry_kind = j0, o[j0], "market"
                xd = first_daily_exit(t5, int(t5[j]), d["tc"], ~d_up)
                if xd is None:
                    g, kind, x = (c[n - 1] - e) / e, "END", n - 1
                else:
                    g, kind, x = (o[xd] - e) / e, "DAILY_TREND_OFF", xd
            else:
                jw = min(n - 1, j0 + 24 * v2.BPH - 1)
                L = S["c"][k] - 0.5 * A
                hits = np.flatnonzero(lo[j0:jw + 1] < L)
                if not hits.size:
                    continue
                j = j0 + int(hits[0])
                e, partial, entry_kind = min(L, o[j]), not (o[j] < L), "limit"
                if 3.0 * A / e < v2.MIN_TARGET:
                    continue
                use_ride = var == "V1_RIDE"
                if var == "V2_ADAPTIVE":
                    di = int(np.searchsorted(d["tc"], t5[j], side="right")) - 1  # last daily bar closed before the fill
                    use_ride = bool(di >= 0 and strong[di])
                if use_ride:
                    g, kind, x = sim_ride(o, h, lo, c, t5, j, e, A, partial, d["tc"], below20)
                else:
                    g, kg, x = v2.sim(o, h, lo, c, j, e, n - 1, A, "X_TRAIL", partial)
                    kind = {v2.K_STOP: "STOP_TRAIL", v2.K_TIME: "TIME_14D", v2.K_SPLIT: "END", v2.K_TARGET: "TARGET"}[kg]
            trades.append({"entry_ts": int(t5[j]), "exit_ts": int(t5[x]) + 300, "entry": float(e), "gross": float(g),
                           "entry_kind": entry_kind, "exit_kind": kind})
            last_exit = x
        out["trades"][var] = trades
    out["seconds"] = round(time.time() - t0, 1)
    return out


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------
def net_usd(t: dict, cst: dict) -> float:
    ec = cst["limit"] if t["entry_kind"] == "limit" else cst["market"]
    return 100.0 * t["gross"] - 100.0 * ec - 100.0 * (1 + t["gross"]) * cst["market"]


def _ffill_from(values: np.ndarray, start: int) -> np.ndarray:
    out = values.copy()
    last = np.nan
    for i in range(len(out)):
        if i < start:
            out[i] = np.nan
        elif np.isnan(out[i]):
            out[i] = last
        else:
            last = out[i]
    return out


def book(coins: list[dict], var: str | None, venue: str) -> dict[str, Any]:
    """Daily mark-to-market equity of a $1000 book ($100 per coin slot). var=None -> buy-and-hold."""
    days = np.array(sorted({int(x) for cd in coins for x in cd["daily_tc"]}), dtype=np.int64)
    eq = np.zeros(len(days))
    in_mkt = np.zeros(len(days))
    live = np.zeros(len(days))
    nets = []
    for cd in coins:
        cst = costs(cd["coin"], venue)
        tc = np.array(cd["daily_tc"], dtype=np.int64)
        raw = np.full(len(days), np.nan)
        raw[np.searchsorted(days, tc)] = np.array(cd["daily_close"])
        first = int(np.searchsorted(days, tc[0]))
        px = _ffill_from(raw, first)  # last known daily close, NaN before the coin exists
        have = ~np.isnan(px)
        live += have
        if var is None:
            qty = 100.0 / cd["bh_entry"]
            mark = np.where(have, qty * (px - cd["bh_entry"]) - 100.0 * cst["market"], 0.0)
            mark[-1] = qty * (cd["bh_exit"] - cd["bh_entry"]) - 100.0 * cst["market"] - qty * cd["bh_exit"] * cst["market"]
            eq += mark
            in_mkt += have
            continue
        for t in cd["trades"][var]:
            qty = 100.0 / t["entry"]
            ec = cst["limit"] if t["entry_kind"] == "limit" else cst["market"]
            nt = net_usd(t, cst)
            nets.append(nt)
            open_d = (days >= t["entry_ts"]) & (days < t["exit_ts"]) & have
            after = days >= t["exit_ts"]
            mtm = np.where(open_d, qty * (np.nan_to_num(px) - t["entry"]) - 100.0 * ec, 0.0)
            eq += mtm + np.where(after, nt, 0.0)
            in_mkt += open_d
    equity = 1000.0 + eq
    peak = np.maximum.accumulate(equity)
    dd = float(np.max((peak - equity) / peak)) if len(equity) else 0.0
    tot = float(equity[-1] / 1000.0 - 1.0)
    eras = {}
    for name, lo_, hi_ in ERAS:
        m = (days >= lo_) & (days < hi_)
        if m.any():
            idx = np.flatnonzero(m)
            i0 = max(0, int(idx[0]) - 1)
            eras[name] = round(100 * (equity[int(idx[-1])] / equity[i0] - 1), 2)
    x = np.array(nets)
    res = {"total_return_pct": round(100 * tot, 2), "max_dd_pct": round(100 * dd, 2),
           "mar": round(tot / dd, 3) if dd > 0 else None, "eras_pct": eras,
           "time_in_market_pct": round(100 * in_mkt.sum() / max(1, live.sum()), 1),
           "first_day": time.strftime("%Y-%m-%d", time.gmtime(int(days[0]))), "last_day": time.strftime("%Y-%m-%d", time.gmtime(int(days[-1])))}
    if var is not None:
        res.update({"n": int(x.size), "win_rate": round(float((x > 0).mean()), 3) if x.size else None,
                    "mean_net_pct_per_trade": round(float(x.mean()), 3) if x.size else None})
    return res


def passes(r: dict, bh: dict) -> dict[str, bool]:
    checks = {
        "n>=50": (r.get("n") or 0) >= 50,
        "return>0": r["total_return_pct"] > 0,
        "MAR>BH": (r["mar"] or -9) > (bh["mar"] or -9),
        "DD<=0.6*BH": r["max_dd_pct"] <= 0.6 * bh["max_dd_pct"],
        "2of3_eras_positive": sum(1 for v in r["eras_pct"].values() if v > 0) >= 2,
    }
    checks["PASS"] = all(checks.values())
    return checks


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--coins", choices=["fresh", "lab10"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "run_done.json"
    if a.coins == "fresh" and marker.exists():
        raise SystemExit(f"fresh-coin test already run once: {marker.read_text()}")
    names = FRESH10 if a.coins == "fresh" else LAB10
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        coins = list(ex.map(run_coin, [os.path.expanduser(a.db)] * len(names), names))
    skipped = [c["coin"] for c in coins if c.get("skipped")]
    coins = [c for c in coins if not c.get("skipped")]
    report: dict[str, Any] = {"version": VERSION, "set": a.coins, "coins": [c["coin"] for c in coins], "skipped": skipped,
                              "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for venue in ("NDAX", "KRAKEN_T1"):
        bh = book(coins, None, venue)
        rows = {"BH": bh}
        for var in VARIANTS:
            r = book(coins, var, venue)
            r["checks"] = passes(r, bh)
            rows[var] = r
        report[venue] = rows
    report["exit_kinds"] = {var: _count(t["exit_kind"] for cd in coins for t in cd["trades"][var]) for var in VARIANTS}
    report["passing_ndax"] = [v for v in VARIANTS if report["NDAX"][v]["checks"]["PASS"]] if a.coins == "fresh" else "reference only"
    (out / "report.json").write_text(json.dumps(report, indent=1))
    (out / "trades.json").write_text(json.dumps({c["coin"]: c["trades"] for c in coins}))
    if a.coins == "fresh":
        marker.write_text(json.dumps({"ran_at": report["ran_at"], "passing_ndax": report["passing_ndax"]}))
    print(json.dumps({k: v for k, v in report.items()}, indent=1))


def _count(xs) -> dict[str, int]:
    d: dict[str, int] = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return d


if __name__ == "__main__":
    main()
