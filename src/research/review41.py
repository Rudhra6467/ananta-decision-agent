"""Review 41, pre-registered in docs/research/REVIEW_41.md (11 Nov 2026): after an extreme 15-minute drop on one-minute candles, does the
price bounce enough to beat costs? History only (2018-01-01 to 2026-07-31); PIT30 decides, PIT10 is reported beside. One look.

    ~/ananta_venvs/lake/bin/python -m src.research.review41 cutoffs   # 1: freeze each coin's discovery cut-offs (reads no outcome)
    ~/ananta_venvs/lake/bin/python -m src.research.review41 run       # 2: the replay, the pass marks and the result file

Light on the Mac: two DuckDB threads, one coin at a time."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LAKE = Path.home() / "ananta_lake"
ONE_MIN = LAKE / "clean" / "binance" / "spot" / "1m"
OUT = Path.home() / "ananta_runs" / "review41"
REGISTRY = Path.home() / "code" / "ananta-decision-agent" / "universe_live.json"
DROP_COSTS = ROOT / "docs" / "research" / "REVIEW_41_ndax_drop_costs.json"
START, DISC_END, CONF_END = 1514764800, 1704067200, 1785542400      # 2018-01-01, 2024-01-01, 2026-08-01 UTC
DAY = 86400
CUTS = (0.01, 0.002, 0.0005)              # a coin's own worst 1%, 0.2% and 0.05% of 15-minute moves (discovery)
HOLDS = (15, 60, 240)                     # minutes after the entry: the drop window x1, x4, x16
GAP = 3600                                # at most one entry per coin per hour
MIN_DISC = 100_000                        # discovery minutes a coin needs for its own cut-offs
FULL_DAY = 1397                           # 97% of 1,440 minutes
NDAX_FEE = 0.0020
DROP_SPREAD_DEFAULT = 0.025               # NDAX spread at a fast drop where a coin had fewer than 5 drops (11 Oct-10 Nov 2026)
Z_BAR, MIN_DAYS = 2.5, 30
ND = (CONF_END - START) // DAY
M0 = (2018 - 1970) * 12                   # month index of 2018-01 (months since 1970-01)
NM = ((2026 - 1970) * 12 + 7) - M0        # months 2018-01 .. 2026-07


def _con():
    con = duckdb.connect()
    con.execute("SET threads=2")
    return con


def _excluded(base: str) -> bool:
    import re

    from jarvis.service.registry import PEGGED
    from src.lake.universe import LEVERAGED, STABLE, WRAPPED

    return (not base) or base in STABLE or base in WRAPPED or base in PEGGED or bool(LEVERAGED.search(base)) or not re.fullmatch(r"[A-Z0-9]+", base)


def pit(n: int) -> dict[str, set[int]]:
    """symbol -> the months (as month indexes since 1970-01) it was on the point-in-time top-n list."""
    d = json.loads((LAKE / "reports" / f"pit_top{n}.json").read_text())["months"]
    out: dict[str, set[int]] = {}
    for m, syms in d.items():
        y, mo = int(m[:4]), int(m[5:7])
        for s in syms:
            out.setdefault(s, set()).add((y - 1970) * 12 + mo - 1)
    return out


def symbols() -> list[str]:
    have = {p.name.split("=", 1)[1] for p in ONE_MIN.iterdir() if p.name.startswith("symbol=")}
    return sorted(s for s in set(pit(30)) | set(pit(10)) if s in have and s.endswith("USDT") and not _excluded(s[:-4]))


def bars(con, symbol: str):
    """(t, o, c) per minute, complete days only (97% of minutes), 2018-01-01 to before 2026-08-01, BREAKS and ENDS applied."""
    from src.lake.research import BREAKS, ENDS

    p = ONE_MIN / f"symbol={symbol}" / "**" / "*.parquet"
    lo, hi = max(START, BREAKS.get(symbol, 0)), min(CONF_END, ENDS.get(symbol, CONF_END))
    r = con.execute(f"SELECT t, o, c FROM read_parquet('{p}', hive_partitioning=true) WHERE t >= {lo} AND t < {hi} AND o > 0 AND c > 0 "
                    "ORDER BY t").fetchnumpy()
    t = np.asarray(r["t"], dtype=np.int64)
    o = np.asarray(r["o"], dtype=np.float64)
    c = np.asarray(r["c"], dtype=np.float64)
    if t.size:
        keep = np.r_[True, t[1:] != t[:-1]]                      # one row per minute
        t, o, c = t[keep], o[keep], c[keep]
    if not t.size:
        return t, o, c, 0, 0
    days, inv, cnt = np.unique(t // DAY, return_inverse=True, return_counts=True)
    full = cnt[inv] >= FULL_DAY
    return t[full], o[full], c[full], int((cnt < FULL_DAY).sum()), int(days.size)


def at(t: np.ndarray, x: np.ndarray, want: np.ndarray) -> np.ndarray:
    """x at exactly the clock times `want`; NaN where that minute is missing (clock time, never row offset)."""
    out = np.full(want.shape, np.nan)
    if not t.size:
        return out
    i = np.clip(np.searchsorted(t, want), 0, t.size - 1)
    hit = t[i] == want
    out[hit] = x[i[hit]]
    return out


def r15(t, c) -> np.ndarray:
    return c / at(t, c, t - 900) - 1.0


# ---------------------------------------------------------------------------------------------------- step 1: the cut-offs
def cutoffs() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / "review41_cutoffs.json"
    if dst.exists():
        raise SystemExit(f"{dst} exists: the cut-offs are frozen once")
    con = _con()
    coins, own = {}, []
    for s in symbols():
        t, o, c, _drop, _days = bars(con, s)
        x = r15(t, c)
        x = x[(t < DISC_END) & np.isfinite(x)]
        rec = {"minutes": int(x.size), "own": bool(x.size >= MIN_DISC)}
        if rec["own"]:
            rec["cuts"] = [float(np.quantile(x, q)) for q in CUTS]
            own.append(rec["cuts"])
        coins[s] = rec
    pooled = [float(np.median([v[k] for v in own])) for k in range(len(CUTS))]
    res = {"written": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "cuts": CUTS, "pooled": pooled, "coins": coins,
           "from": "discovery 2018-01-01 to 2023-12-31, each coin's own 15-minute returns only (no outcome read)"}
    dst.write_text(json.dumps(res, indent=1))
    print(f"cut-offs frozen for {len(coins)} coins ({sum(1 for v in coins.values() if v['own'])} with their own); pooled {pooled}")
    return res


# ---------------------------------------------------------------------------------------------------- step 2: the replay
def _house_cost(base: str, reg: dict) -> float:
    from jarvis.service.registry import FLOOR, KRAKEN_FEE
    from src.intelligence.ndax_costs import HALF_SPREAD

    if base in HALF_SPREAD:
        return NDAX_FEE + HALF_SPREAD[base]
    k = reg.get("coins", {}).get(base) or {}
    hs = max(3 * (k.get("binance_half_spread") or 0.0), FLOOR[k.get("tier") or "C"])
    return (NDAX_FEE if k.get("ndax") else KRAKEN_FEE) + hs


def _drop_cost(base: str, drop: dict) -> float:
    k = drop.get("coins", {}).get(base) or {}
    spread = k.get("spread_at_drop_median") if (k.get("drops") or 0) >= 5 else None
    return 2 * NDAX_FEE + (spread if spread is not None else DROP_SPREAD_DEFAULT)


class Acc:
    """One cell in one tier: day sums (for day means and z) and month sums (for the no-burst check)."""

    def __init__(self):
        self.n = np.zeros(ND)
        self.gross = np.zeros(ND)
        self.net = np.zeros(ND)
        self.net2 = np.zeros(ND)
        self.netd = np.zeros(ND)
        self.ex = np.zeros(ND)
        self.month_net = np.zeros(NM)
        self.coins: dict[str, set] = {"discovery": set(), "confirm": set()}
        self.events = {"discovery": 0, "confirm": 0}

    def add(self, coin, day, mon, gross, ex, hc, dc):
        np.add.at(self.n, day, 1)
        np.add.at(self.gross, day, gross)
        np.add.at(self.net, day, gross - hc)
        np.add.at(self.net2, day, gross - 2 * hc)
        np.add.at(self.netd, day, gross - dc)
        np.add.at(self.ex, day, ex)
        np.add.at(self.month_net, mon, gross - hc)
        d0 = (DISC_END - START) // DAY
        for per, m in (("discovery", day < d0), ("confirm", day >= d0)):
            k = int(m.sum())
            if k:
                self.coins[per].add(coin)
                self.events[per] += k

    def period(self, per: str) -> dict:
        d0 = (DISC_END - START) // DAY
        sl = slice(0, d0) if per == "discovery" else slice(d0, ND)
        n = self.n[sl]
        on = n > 0
        days = int(on.sum())

        def mean(x):
            return float(np.mean(x[sl][on] / n[on])) if days else None

        exm = self.ex[sl][on] / n[on] if days else np.array([])
        z = float(exm.mean() / (exm.std(ddof=1) / math.sqrt(days))) if days > 2 and exm.std(ddof=1) > 0 else None
        m0 = 0 if per == "discovery" else (2024 - 2018) * 12
        mm = self.month_net[m0:] if per == "confirm" else self.month_net[:(2024 - 2018) * 12]
        total = float(mm.sum())
        burst = float(mm.max() / total) if total > 0 else None
        r = {"events": self.events[per], "days": days, "coins": len(self.coins[per]),
             "mean_gross": mean(self.gross), "mean_net": mean(self.net), "mean_net_2x": mean(self.net2), "mean_net_ndax_drop": mean(self.netd),
             "mean_excess": float(exm.mean()) if days else None, "z_excess": z, "largest_month_share": burst}
        r["pass"] = {"days": days >= MIN_DAYS, "net_above_zero": (r["mean_net"] or -1) > 0, "z": (z or 0) >= Z_BAR,
                     "2x_cost": (r["mean_net_2x"] or -1) > 0, "no_burst": burst is not None and burst <= 0.5}
        r["passes"] = all(r["pass"].values())
        return r


def run() -> dict:
    cut = json.loads((OUT / "review41_cutoffs.json").read_text())
    drop = json.loads(DROP_COSTS.read_text())
    reg = json.loads(REGISTRY.read_text())
    p30, p10 = pit(30), pit(10)
    con = _con()
    acc = {tier: {(k, h): Acc() for k in range(len(CUTS)) for h in HOLDS} for tier in ("PIT30", "PIT10")}
    header = {"coins_read": 0, "days_kept": 0, "days_dropped": 0, "coins_alive_per_year": {}, "breaks_ends": ["COCOSUSDT", "BNXUSDT", "LUNAUSDT"],
              "range": "2018-01-01 to 2026-07-31 UTC", "costs_assumed": 0}
    t0 = time.time()
    for s in symbols():
        base = s[:-4]
        t, o, c, dropped, days = bars(con, s)
        header["days_dropped"] += dropped
        if not t.size:
            continue
        header["coins_read"] += 1
        header["days_kept"] += int(np.unique(t // DAY).size)
        for y in np.unique(t.astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970):
            header["coins_alive_per_year"][str(y)] = header["coins_alive_per_year"].get(str(y), 0) + 1
        if base not in reg.get("coins", {}):
            header["costs_assumed"] += 1
        mon = t.astype("datetime64[s]").astype("datetime64[M]").astype(np.int64)        # months since 1970-01
        hour = (t // 3600) % 24
        key = (mon - mon.min()) * 24 + hour
        entry = at(t, o, t + 60)
        rets = {h: at(t, o, t + 60 + h * 60) / entry - 1.0 for h in HOLDS}
        base_mean = {}
        for h, r in rets.items():
            ok = np.isfinite(r)
            sums = np.bincount(key[ok], weights=r[ok], minlength=int(key.max()) + 1)
            cnts = np.bincount(key[ok], minlength=int(key.max()) + 1)
            base_mean[h] = sums / np.maximum(cnts, 1)
        rec = cut["coins"].get(s) or {}
        cuts = rec["cuts"] if rec.get("own") else cut["pooled"]
        x = r15(t, c)
        hc, dc = 2 * _house_cost(base, reg), _drop_cost(base, drop)
        tiers = {"PIT30": np.isin(mon, list(p30.get(s, ()))), "PIT10": np.isin(mon, list(p10.get(s, ())))}
        for k, cu in enumerate(cuts):
            cand = np.flatnonzero(np.isfinite(x) & (x <= cu))
            picks, last = [], -(10 ** 12)
            for i in cand:                                       # the first crossing, then nothing in that coin for an hour
                if t[i] - last >= GAP:
                    picks.append(i)
                    last = t[i]
            if not picks:
                continue
            pk = np.asarray(picks, dtype=np.int64)
            for h in HOLDS:
                g = rets[h][pk]
                ok = np.isfinite(g)
                idx, g = pk[ok], g[ok]
                ex = g - base_mean[h][key[idx]]
                day = (t[idx] - START) // DAY
                mi = mon[idx] - M0
                for tier, member in tiers.items():
                    m = member[idx]
                    if m.any():
                        acc[tier][(k, h)].add(s, day[m], mi[m], g[m], ex[m], hc, dc)
        print(f"{s}: done ({time.time() - t0:.0f}s)", flush=True)
    cells = {tier: {f"cut{CUTS[k]}_hold{h}": {"discovery": a.period("discovery"), "confirm": a.period("confirm")} for (k, h), a in cells_.items()}
             for tier, cells_ in acc.items()}
    for tier in cells:
        for v in cells[tier].values():
            v["passes"] = v["discovery"]["passes"] and v["confirm"]["passes"]
    try:
        prereg = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%H %cI", "--", "docs/research/REVIEW_41.md"],
                                capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        prereg = ""
    res = {"review": 41, "prereg_commit": prereg, "ran": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "header": header,
           "deciding_tier": "PIT30", "cells": cells,
           "passed": [c for c, v in cells["PIT30"].items() if v["passes"]],
           "look_count_added": len(CUTS) * len(HOLDS)}
    (OUT / "review41_results.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"passed": res["passed"], "header": header}, indent=1))
    return res


if __name__ == "__main__":
    {"cutoffs": cutoffs, "run": run}[sys.argv[1] if len(sys.argv) > 1 else "run"]()
