"""Review 42, pre-registered in docs/research/REVIEW_42.md (11 Nov 2026): after an extreme 15-minute drop, does a resting limit buy below
the price beat costs? Review 41's data, periods and frozen cut-offs; NDAX30 decides, PIT30 and PIT10 beside. One look.

    ~/ananta_venvs/lake/bin/python -m src.research.review42

Light on the Mac: two DuckDB threads, one coin at a time."""
from __future__ import annotations

import json
import math
import subprocess
import time
import zlib

import numpy as np

from src.research import review41 as R

OUT = R.OUT.parent / "review42"
CUT_IDX = (1, 2)                          # review 41's frozen worst 0.2% and 0.05%
DEPTHS = (0.25, 0.5)                      # the order rests k x |the coin's cut-off| below the detection close
HOLDS = (60, 240)                         # minutes after the fill
WINDOW = 3600                             # the order rests 60 minutes
THROUGH = 0.999                           # a fill needs a low at or below L x 0.999 (a touch is not a fill)
RANDOM_PER_EVENT = 10


def bars(con, symbol: str):
    """(t, o, l, c) per minute, complete days only, review 41's range, BREAKS and ENDS applied."""
    from src.lake.research import BREAKS, ENDS

    p = R.ONE_MIN / f"symbol={symbol}" / "**" / "*.parquet"
    lo, hi = max(R.START, BREAKS.get(symbol, 0)), min(R.CONF_END, ENDS.get(symbol, R.CONF_END))
    r = con.execute(f"SELECT t, o, l, c FROM read_parquet('{p}', hive_partitioning=true) WHERE t >= {lo} AND t < {hi} AND o > 0 AND l > 0 "
                    "AND c > 0 ORDER BY t").fetchnumpy()
    t = np.asarray(r["t"], dtype=np.int64)
    o, low, c = (np.asarray(r[k], dtype=np.float64) for k in ("o", "l", "c"))
    if t.size:
        keep = np.r_[True, t[1:] != t[:-1]]
        t, o, low, c = t[keep], o[keep], low[keep], c[keep]
    if not t.size:
        return t, o, low, c, 0
    _days, inv, cnt = np.unique(t // R.DAY, return_inverse=True, return_counts=True)
    full = cnt[inv] >= R.FULL_DAY
    return t[full], o[full], low[full], c[full], int((cnt < R.FULL_DAY).sum())


def fill(t, low, i: int, limit: float) -> int:
    """Index of the first minute after t[i] (within the 60-minute rest) whose low trades through the order; -1 if none."""
    a = np.searchsorted(t, t[i] + 60)
    b = np.searchsorted(t, t[i] + WINDOW, side="right")
    if a >= b:
        return -1
    hit = np.flatnonzero(low[a:b] <= limit * THROUGH)
    return int(a + hit[0]) if hit.size else -1


def trade(t, o, low, c, i: int, depth: float, hold: int) -> tuple[float, int] | None:
    """(gross return from the fill to the exit, fill index) for an order placed at minute i; None if it did not fill or no exit price."""
    limit = c[i] * (1 - depth)
    f = fill(t, low, i, limit)
    if f < 0:
        return None
    ex = R.at(t, o, np.array([t[f] + hold * 60]))[0]
    if not math.isfinite(ex):
        return None
    return ex / limit - 1.0, f


class AccL(R.Acc):
    """Review 41's day and month sums, with the excess counted only over events whose random orders filled."""

    def __init__(self):
        super().__init__()
        self.n_ex = np.zeros(R.ND)
        self.netm = np.zeros(R.ND)
        self.placed = {"discovery": 0, "confirm": 0}
        self.no_base = {"discovery": 0, "confirm": 0}

    def add_l(self, coin, day, mon, gross, ex, hc, dc, hm):
        ok = np.isfinite(ex)
        super().add(coin, day, mon, gross, np.where(ok, ex, 0.0), hc, dc)
        np.add.at(self.n_ex, day[ok], 1)
        np.add.at(self.netm, day, gross - hm)                         # beside: a market buy on the same fills
        d0 = (R.DISC_END - R.START) // R.DAY
        for per, m in (("discovery", day < d0), ("confirm", day >= d0)):
            self.no_base[per] += int((~ok & m).sum())

    def period(self, per: str) -> dict:
        r = super().period(per)
        d0 = (R.DISC_END - R.START) // R.DAY
        sl = slice(0, d0) if per == "discovery" else slice(d0, R.ND)
        on = self.n_ex[sl] > 0
        exm = self.ex[sl][on] / self.n_ex[sl][on]
        k = int(on.sum())
        z = float(exm.mean() / (exm.std(ddof=1) / math.sqrt(k))) if k > 2 and exm.std(ddof=1) > 0 else None
        n = self.n[sl]
        r["mean_net_market"] = float(np.mean(self.netm[sl][n > 0] / n[n > 0])) if (n > 0).any() else None
        r.update(mean_excess=float(exm.mean()) if k else None, z_excess=z, days_with_baseline=k, orders_placed=self.placed[per],
                 events_without_baseline=self.no_base[per], fill_rate=(r["events"] / self.placed[per]) if self.placed[per] else None)
        r["pass"]["z"] = (z or 0) >= R.Z_BAR
        r["passes"] = all(r["pass"].values())
        return r


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    cut = json.loads((R.OUT / "review41_cutoffs.json").read_text())
    drop = json.loads(R.DROP_COSTS.read_text())
    reg = json.loads(R.REGISTRY.read_text())
    p30, p10 = R.pit(30), R.pit(10)
    con = R._con()
    cells = [(k, d, h) for k in CUT_IDX for d in DEPTHS for h in HOLDS]
    acc = {tier: {cell: AccL() for cell in cells} for tier in ("NDAX30", "PIT30", "PIT10")}
    header = {"coins_read": 0, "days_dropped": 0, "ndax_listed_read": 0, "range": "2018-01-01 to 2026-07-31 UTC"}
    t0 = time.time()
    d0 = (R.DISC_END - R.START) // R.DAY
    for s in R.symbols():
        base = s[:-4]
        t, o, low, c, dropped = bars(con, s)
        header["days_dropped"] += dropped
        if not t.size:
            continue
        header["coins_read"] += 1
        on_ndax = bool((reg.get("coins", {}).get(base) or {}).get("ndax"))
        header["ndax_listed_read"] += int(on_ndax)
        mon = t.astype("datetime64[s]").astype("datetime64[M]").astype(np.int64)
        hour = (t // 3600) % 24
        key = (mon - mon.min()) * 24 + hour
        order = np.argsort(key, kind="stable")
        starts = np.searchsorted(key[order], np.arange(int(key.max()) + 2))
        rng = np.random.default_rng(zlib.crc32(s.encode()))
        x = R.r15(t, c)
        rec = cut["coins"].get(s) or {}
        cuts = rec["cuts"] if rec.get("own") else cut["pooled"]
        hc = R.NDAX_FEE + R._house_cost(base, reg)                       # in: the fee only (a resting order); out: the house cost
        dk = drop.get("coins", {}).get(base) or {}
        spread = dk.get("spread_at_drop_median") if (dk.get("drops") or 0) >= 5 else None
        dc = 2 * R.NDAX_FEE + (spread if spread is not None else R.DROP_SPREAD_DEFAULT)
        hm = 2 * R._house_cost(base, reg)                               # beside: the market round trip on the same fills
        member = {"NDAX30": np.isin(mon, list(p30.get(s, ()))) & on_ndax, "PIT30": np.isin(mon, list(p30.get(s, ()))),
                  "PIT10": np.isin(mon, list(p10.get(s, ())))}
        for ki in CUT_IDX:
            cu = cuts[ki]
            cand = np.flatnonzero(np.isfinite(x) & (x <= cu))
            picks, last = [], -(10 ** 12)
            for i in cand:
                if t[i] - last >= R.GAP:
                    picks.append(int(i))
                    last = t[i]
            if not picks:
                continue
            for dep in DEPTHS:
                depth = dep * abs(cu)
                for h in HOLDS:
                    rows = []
                    for i in picks:
                        tiers = [tier for tier, m in member.items() if m[i]]
                        if not tiers:
                            continue
                        got = trade(t, o, low, c, i, depth, h)
                        g = k = None
                        pool = order[starts[key[i]]:starts[key[i] + 1]]
                        sample = rng.choice(pool, size=min(RANDOM_PER_EVENT, pool.size), replace=False) if pool.size else []
                        base_r = [r[0] for r in (trade(t, o, low, c, int(j), depth, h) for j in sample) if r is not None]
                        if got is not None:
                            g, f = got
                            k = (g - float(np.mean(base_r))) if base_r else float("nan")
                        rows.append((tiers, i, g, k))
                    for tier in acc:
                        a = acc[tier][(ki, dep, h)]
                        mine = [(i, g, k) for tiers, i, g, k in rows if tier in tiers]
                        for i, g, k in mine:
                            a.placed["discovery" if (t[i] - R.START) // R.DAY < d0 else "confirm"] += 1
                        filled = [(i, g, k) for i, g, k in mine if g is not None]
                        if not filled:
                            continue
                        idx = np.array([i for i, _g, _k in filled], dtype=np.int64)
                        a.add_l(s, (t[idx] - R.START) // R.DAY, mon[idx] - R.M0, np.array([g for _i, g, _k in filled]),
                                np.array([k for _i, _g, k in filled]), hc, dc, hm)
        print(f"{s}: done ({time.time() - t0:.0f}s)", flush=True)
    out_cells = {tier: {f"cut{R.CUTS[k]}_depth{d}_hold{h}": {"discovery": a.period("discovery"), "confirm": a.period("confirm")}
                        for (k, d, h), a in cells_.items()} for tier, cells_ in acc.items()}
    for tier in out_cells:
        for v in out_cells[tier].values():
            v["passes"] = v["discovery"]["passes"] and v["confirm"]["passes"]
    try:
        prereg = subprocess.run(["git", "-C", str(R.ROOT), "log", "-1", "--format=%H %cI", "--", "docs/research/REVIEW_42.md"],
                                capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        prereg = ""
    res = {"review": 42, "prereg_commit": prereg, "ran": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "header": header,
           "deciding_tier": "NDAX30", "cells": out_cells, "passed": [c for c, v in out_cells["NDAX30"].items() if v["passes"]],
           "look_count_added": len(cells)}
    (OUT / "review42_results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"passed": res["passed"], "header": header}, indent=1))
    return res


if __name__ == "__main__":
    run()
