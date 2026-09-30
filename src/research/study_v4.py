"""Study v4 — implements docs/research/STUDY_V4.md exactly (BTC market filter, honest drawdown).

    python -m src.research.study_v4 run --db ~/ananta_runs/fresh2/fresh2_5m.sqlite --set fresh2 --out ~/ananta_runs/study_v4_fresh2
    python -m src.research.study_v4 run --db ~/ananta_runs/fresh10/fresh10_5m.sqlite --set fresh10 --out ~/ananta_runs/study_v4_ref_fresh10
The fresh2 run writes a marker and refuses a second run. Other sets are references only.
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
from src.research import study_v3 as s3

VERSION = "study.v4"
SETS = {
    "fresh2": ["EOS", "HOT", "MATIC", "NEO", "OMG", "TCT", "TFUEL", "THETA", "VITE", "WTC", "XMR", "XTZ"],
    "fresh10": s3.FRESH10,
    "lab10": s3.LAB10,
}
VARIANTS = ("V1_CONTROL", "V4A_BTC_GATE", "V4B_BTC_GATE_EXIT", "V4C_HOLD_BTC_GATE")
BPD = s3.BPD
LAB_DB = os.path.expanduser("~/code/ananta-decision-agent/ananta-quant-research-db/lab5_5m.sqlite")


def btc_daily(db: str = LAB_DB) -> dict[str, list]:
    b = v1.load_5m(db, "BTC")
    d = v1.resample(b, "1d")
    c = d["c"]
    e20, e50 = v1.ema(c, 20), v1.ema(c, 50)
    up = (c > e50) & (e20 > e50) & (np.arange(len(c)) >= 50)
    return {"tc": d["tc"].tolist(), "up": up.tolist()}


def first_exit(t5, t_entry, pairs) -> int | None:
    """Earliest 5m index at/after the first flagged daily close after t_entry, across several (tc, flag) series."""
    best = None
    for tc, flag in pairs:
        x = s3.first_daily_exit(t5, t_entry, tc, flag)
        if x is not None and (best is None or x < best):
            best = x
    return best


def sim_ride_multi(o, lo, c, t5, j, e, A, partial, pairs) -> tuple[float, str, int]:
    """V1 ride exit (stop 2.5A, daily exits, 60d) where the daily exit is the earliest of several flags."""
    n = len(t5)
    s0 = e - 2.5 * A
    last = min(n - 1, j + 60 * BPD - 1)
    xd = first_exit(t5, int(t5[j]), pairs)
    stop_end = min(last, (xd - 1) if xd is not None else last)
    seg = lo[j:stop_end + 1]
    if partial and seg.size and seg[0] <= s0:
        return (s0 - e) / e, "STOP", j
    hs = np.flatnonzero(seg <= s0)
    if hs.size:
        k = j + int(hs[0])
        return (min(s0, o[k]) - e) / e, "STOP", k
    if xd is not None and xd <= last:
        return (o[xd] - e) / e, "DAILY_EXIT", xd
    kind = "TIME_60D" if last == j + 60 * BPD - 1 else "END"
    return (c[last] - e) / e, kind, last


def run_coin(db: str, coin: str, btc: dict) -> dict[str, Any]:
    t0 = time.time()
    b = v1.load_5m(db, coin)
    t5, o, lo, c = b["t"], b["o"], b["l"], b["c"]
    n = len(t5)
    if n < 100 * BPD:
        return {"coin": coin, "skipped": "insufficient_history", "bars": int(n)}
    S = v2.setups(b)
    d = v1.resample(b, "1d")
    dc = d["c"]
    e20, e50 = v1.ema(dc, 20), v1.ema(dc, 50)
    below20 = dc < e20
    coin_off = ~((dc > e50) & (e20 > e50))
    btc_tc = np.array(btc["tc"], dtype=np.int64)
    btc_up = np.array(btc["up"], dtype=bool)
    btc_off = ~btc_up
    ks = np.flatnonzero(S["flags"][("S3_TREND_CONTROL", "LONG")])
    out: dict[str, Any] = {"coin": coin, "bars": int(n), "trades": {}, "first_ts": int(t5[0]), "last_ts": int(t5[-1]),
                           "daily_tc": d["tc"].tolist(), "daily_close": dc.tolist(),
                           "bh_entry": float(o[0]), "bh_exit": float(c[-1])}

    def btc_up_at(T: float) -> bool:
        i = int(np.searchsorted(btc_tc, T, side="right")) - 1
        return bool(i >= 0 and btc_up[i] and T - btc_tc[i] <= 2 * 86400)

    for var in VARIANTS:
        trades, last_exit = [], -1
        for k in ks:
            T = S["tc"][k]
            j0 = int(np.searchsorted(t5, T, side="left"))
            if j0 >= n - 1 or t5[j0] - T >= 3600 or j0 <= last_exit:
                continue
            if var != "V1_CONTROL" and not btc_up_at(T):
                continue
            A = S["A"][k]
            if var == "V4C_HOLD_BTC_GATE":
                j, e, ek = j0, o[j0], "market"
                x = first_exit(t5, int(t5[j]), [(d["tc"], coin_off), (btc_tc, btc_off)])
                g, kind, x = ((c[n - 1] - e) / e, "END", n - 1) if x is None else ((o[x] - e) / e, "DAILY_TREND_OFF", x)
            else:
                jw = min(n - 1, j0 + 24 * v2.BPH - 1)
                L = S["c"][k] - 0.5 * A
                hits = np.flatnonzero(lo[j0:jw + 1] < L)
                if not hits.size:
                    continue
                j = j0 + int(hits[0])
                e, partial, ek = min(L, o[j]), not (o[j] < L), "limit"
                if 3.0 * A / e < v2.MIN_TARGET:
                    continue
                pairs = [(d["tc"], below20)] + ([(btc_tc, btc_off)] if var == "V4B_BTC_GATE_EXIT" else [])
                g, kind, x = sim_ride_multi(o, lo, c, t5, j, e, A, partial, pairs)
            trades.append({"entry_ts": int(t5[j]), "exit_ts": int(t5[x]) + 300, "entry": float(e), "gross": float(g),
                           "entry_kind": ek, "exit_kind": kind})
            last_exit = x
        out["trades"][var] = trades
    out["seconds"] = round(time.time() - t0, 1)
    return out


# ---------------------------------------------------------------------------
# Book with honest drawdown
# ---------------------------------------------------------------------------
def pnl_curve(coins: list[dict], var: str | None, venue: str) -> tuple[np.ndarray, np.ndarray, list]:
    days = np.array(sorted({int(x) for cd in coins for x in cd["daily_tc"]}), dtype=np.int64)
    eq = np.zeros(len(days))
    nets = []
    for cd in coins:
        cst = s3.costs(cd["coin"], venue)
        tc = np.array(cd["daily_tc"], dtype=np.int64)
        raw = np.full(len(days), np.nan)
        raw[np.searchsorted(days, tc)] = np.array(cd["daily_close"])
        px = s3._ffill_from(raw, int(np.searchsorted(days, tc[0])))
        have = ~np.isnan(px)
        if var is None:
            qty = 100.0 / cd["bh_entry"]
            end_i = int(np.searchsorted(days, tc[-1]))
            mark = np.where(have, qty * (np.nan_to_num(px) - cd["bh_entry"]) - 100.0 * cst["market"], 0.0)
            final = qty * (cd["bh_exit"] - cd["bh_entry"]) - 100.0 * cst["market"] - qty * cd["bh_exit"] * cst["market"]
            mark[end_i:] = final  # after the coin's last bar (e.g. delisting) the position is closed
            eq += mark
            continue
        for t in cd["trades"][var]:
            qty = 100.0 / t["entry"]
            ec = cst["limit"] if t["entry_kind"] == "limit" else cst["market"]
            nt = s3.net_usd(t, cst)
            nets.append(nt)
            op = (days >= t["entry_ts"]) & (days < t["exit_ts"]) & have
            eq += np.where(op, qty * (np.nan_to_num(px) - t["entry"]) - 100.0 * ec, 0.0) + np.where(days >= t["exit_ts"], nt, 0.0)
    return days, eq, nets


def metrics(coins: list[dict], var: str | None, venue: str) -> dict[str, Any]:
    cap = 100.0 * len(coins)
    days, eq, nets = pnl_curve(coins, var, venue)
    peak = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    dd_usd = float(np.max(peak - eq))
    tot = float(eq[-1])
    fresh = []
    for y in range(2019, 2027):
        for mth in (1, 4, 7, 10):
            ts = time.mktime(time.strptime(f"{y}-{mth:02d}-01", "%Y-%m-%d")) - time.timezone
            i0 = int(np.searchsorted(days, ts))
            i1 = int(np.searchsorted(days, ts + 365 * 86400))
            if i0 < len(days) and i1 < len(days) and days[i0] - ts < 7 * 86400:
                fresh.append((f"{y}Q{(mth - 1) // 3 + 1}", round(100 * (eq[i1] - eq[i0]) / cap, 2)))
    eras = {}
    for name, lo_, hi_ in s3.ERAS:
        m = (days >= lo_) & (days < hi_)
        if m.any():
            idx = np.flatnonzero(m)
            base = eq[idx[0] - 1] if idx[0] > 0 else 0.0
            eras[name] = round(100 * (eq[idx[-1]] - base) / cap, 2)
    x = np.array(nets)
    ret = 100 * tot / cap
    ddp = 100 * dd_usd / cap
    worst = min(fresh, key=lambda z: z[1]) if fresh else None
    res = {"start_capital": cap, "total_return_pct": round(ret, 2), "dd_vs_start_pct": round(ddp, 2),
           "score": round(ret / ddp, 3) if ddp > 0 else None, "eras_pct": eras,
           "fresh_start_12m_worst": worst, "fresh_start_12m_median": round(float(np.median([f[1] for f in fresh])), 2) if fresh else None,
           "fresh_starts": fresh}
    if var is not None:
        res.update({"n": int(x.size), "win_rate": round(float((x > 0).mean()), 3) if x.size else None,
                    "mean_net_usd_per_trade": round(float(x.mean()), 3) if x.size else None})
    return res


def passes(r: dict, bh: dict) -> dict[str, bool]:
    ch = {
        "n>=50": (r.get("n") or 0) >= 50,
        "return>0": r["total_return_pct"] > 0,
        "dd<=35%": r["dd_vs_start_pct"] <= 35.0,
        "worst12m>=-20%": (r["fresh_start_12m_worst"] or ("", -999))[1] >= -20.0,
        "score>BH": (r["score"] or -9) > (bh["score"] or -9),
        "2of3_eras_positive": sum(1 for v in r["eras_pct"].values() if v > 0) >= 2,
    }
    ch["PASS"] = all(ch.values())
    return ch


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--set", choices=list(SETS), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "run_done.json"
    if a.set == "fresh2" and marker.exists():
        raise SystemExit(f"fresh set #2 already run once: {marker.read_text()}")
    btc = btc_daily()
    names = SETS[a.set]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        coins = list(ex.map(run_coin, [os.path.expanduser(a.db)] * len(names), names, [btc] * len(names)))
    skipped = [c["coin"] for c in coins if c.get("skipped")]
    coins = [c for c in coins if not c.get("skipped")]
    rep: dict[str, Any] = {"version": VERSION, "set": a.set, "evidence": a.set == "fresh2", "coins": [c["coin"] for c in coins],
                           "skipped": skipped, "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                           "coin_spans": {c["coin"]: [time.strftime("%Y-%m-%d", time.gmtime(c["first_ts"])), time.strftime("%Y-%m-%d", time.gmtime(c["last_ts"]))] for c in coins}}
    for venue in ("NDAX", "KRAKEN_T1"):
        bh = metrics(coins, None, venue)
        rows = {"BH": bh}
        for var in VARIANTS:
            r = metrics(coins, var, venue)
            r["checks"] = passes(r, bh)
            rows[var] = r
        rep[venue] = rows
    rep["passing_ndax"] = [v for v in VARIANTS if rep["NDAX"][v]["checks"]["PASS"]]
    rep["exit_kinds"] = {v: s3._count(t["exit_kind"] for cd in coins for t in cd["trades"][v]) for v in VARIANTS}
    (out / "report.json").write_text(json.dumps(rep, indent=1))
    (out / "trades.json").write_text(json.dumps({c["coin"]: c["trades"] for c in coins}))
    if a.set == "fresh2":
        marker.write_text(json.dumps({"ran_at": rep["ran_at"], "passing_ndax": rep["passing_ndax"]}))
    print(json.dumps({k: rep[k] for k in ("set", "coins", "skipped", "passing_ndax")}, indent=1))


if __name__ == "__main__":
    main()
