"""Review #20: a lower-turnover T3 (docs/research/REVIEW_20.md). Same signal as review #4; only how the book is re-sized changes.

  T3    control: weekly reset to equal shares, and every change re-sizes all held coins (portfolio_trend.simulate)
  T3-N  entries buy the new coin to its target, exits sell that coin; nothing else trades
  T3-B  T3-N + on Mondays a held coin outside 0.5x-1.5x of its target is re-sized
  T3-M  T3-N + a full reset on the first Monday of each month

Entries never borrow: a buy is capped by the cash on hand. Run: python -m src.research.t3_turnover
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src.research import portfolio_trend as P

VARIANTS = ("T3", "T3-N", "T3-B", "T3-M")
BAND = (0.5, 1.5)


def simulate(data: dict, days: pd.DatetimeIndex, on: pd.DataFrame, avail: pd.DataFrame, mode: str, cost_mult: float = 1.0,
             disaster: float | None = None) -> dict:
    """disaster (review #18): a held coin closing this fraction or more under its average entry price is sold at the next open and
    not bought again until the signal has turned it off and on again."""
    O = pd.DataFrame({k: v["o"] for k, v in data.items()}).reindex(days).ffill()
    C = pd.DataFrame({k: v["c"] for k, v in data.items()}).reindex(days).ffill()
    coins = list(C.columns)
    hs = cost_mult * np.array([P.FEE + P.HALF_SPREAD.get(c, 0.004) for c in coins])
    units = np.zeros(len(coins))
    cash, costs, trades = 1.0, 0.0, 0
    eq = np.full(len(days), np.nan)
    exposure = np.zeros(len(days))
    costd = np.zeros(len(days))
    prev_on = np.zeros(len(coins), dtype=bool)
    basis = np.full(len(coins), np.nan)
    blocked = np.zeros(len(coins), dtype=bool)
    stops = 0
    ON, AV, OP, CL = on.to_numpy(dtype=bool), avail.to_numpy(dtype=bool), O.to_numpy(), C.to_numpy()
    for d in range(len(days)):
        if d > 0:
            sig, av, px = ON[d - 1].copy(), AV[d - 1], OP[d]
            if disaster is not None:
                blocked &= ON[d - 1]                       # the signal turned the coin off: it may be bought again later
                sig &= ~blocked
            ok = ~np.isnan(px)
            sig &= ok
            n_av = int((av & ok).sum())
            value = units * np.nan_to_num(px)
            equity = cash + value.sum()
            monday = days[d].weekday() == 0
            delta = np.zeros(len(coins))
            if n_av:
                tgt = equity / n_av
                full = (mode == "T3" and (monday or (sig != prev_on).any())) or (mode == "T3-M" and monday and days[d].day <= 7)
                if full:
                    delta = np.where(sig, tgt, 0.0) - value
                else:
                    exits = prev_on & ~sig & ok
                    delta[exits] = -value[exits]
                    if mode == "T3-B" and monday:
                        held = prev_on & sig
                        off = held & ((value < BAND[0] * tgt) | (value > BAND[1] * tgt))
                        delta[off] = tgt - value[off]
                    free = cash - delta[delta < 0].sum() * 1.0 - (np.abs(delta[delta < 0]) * hs[delta < 0]).sum() - (delta[delta > 0] * (1 + hs[delta > 0])).sum()
                    for i in np.where(sig & ~prev_on)[0]:
                        buy = max(0.0, min(tgt - value[i], free / (1 + hs[i])))
                        delta[i] = buy
                        free -= buy * (1 + hs[i])
                delta[~ok] = 0.0
                if np.abs(delta).sum() > 0:
                    c = (np.abs(delta) * hs).sum()
                    trades += int((np.abs(delta) > 1e-9).sum())
                    costs += c
                    costd[d] = c
                    cash -= delta.sum() + c
                    new_units = np.where(ok, (value + delta) / np.where(ok, px, 1.0), units)
                    if disaster is not None:
                        buy = (delta > 1e-12) & ok
                        old = np.where(np.isnan(basis), 0.0, basis) * units
                        basis = np.where(buy, (old + delta) / np.where(new_units > 0, new_units, 1.0), basis)
                        basis = np.where(new_units * np.nan_to_num(px) < 1e-9, np.nan, basis)
                    units = new_units
            prev_on = sig
        val = units * np.nan_to_num(CL[d])
        if disaster is not None:
            hit = (units > 0) & ~np.isnan(basis) & ~np.isnan(CL[d]) & (CL[d] <= (1 - disaster) * np.nan_to_num(basis, nan=0.0)) & ~blocked
            stops += int(hit.sum())
            blocked |= hit
        eq[d] = cash + val.sum()
        exposure[d] = val.sum() / eq[d] if eq[d] > 0 else 0.0
    return {"equity": pd.Series(eq, index=days), "trades": trades, "costs": costs, "exposure": pd.Series(exposure, index=days),
            "costs_by_day": pd.Series(costd, index=days), "disaster_stops": stops}


def frames(D: dict) -> tuple[dict, pd.DatetimeIndex]:
    data = {}
    for c, bars in D.items():
        df = pd.DataFrame(bars, columns=["t", "o", "h", "l", "c", "v"])
        df.index = pd.to_datetime(df["t"], unit="s")
        data[c] = df[["o", "c"]]
    days = pd.date_range(min(v.index.min() for v in data.values()), max(v.index.max() for v in data.values()), freq="D")
    return data, days


def split(sim: dict) -> dict:
    eq, exp = sim["equity"], sim["exposure"]
    eq = eq[eq.index >= eq.index[0] + pd.Timedelta(days=50)]
    out = {"DISCOVERY": P.metrics(eq[eq.index < P.DISC_END], exp), "CONFIRM": P.metrics(eq[eq.index >= P.DISC_END], exp)}
    for sp in out:                                   # costs paid inside each period, as % of that period's start equity
        s = sim["costs_by_day"]
        m = (s.index < P.DISC_END) if sp == "DISCOVERY" else (s.index >= P.DISC_END)
        out[sp]["costs_pct_of_start"] = round(100 * float((s[m] / sim["equity"].shift(1)[m]).sum()), 2)
    out["trades"] = sim["trades"]
    return out


def run_tier(D: dict, cost_mult: float = 1.0) -> dict:
    data, days = frames(D)
    sig = P.signals(data, days)
    bh = simulate(data, days, sig["BH"], sig["_avail"], "T3", cost_mult)       # buy-and-hold: always on, same sizing as review #4
    res = {"BH": split(bh)}
    for v in VARIANTS:
        res[v] = split(simulate(data, days, sig["T3"], sig["_avail"], v, cost_mult))
    return res


def verdicts(res: dict) -> dict:
    out = {}
    for v in VARIANTS[1:]:
        checks = {}
        for sp in ("DISCOVERY", "CONFIRM"):
            a, t, b = res[v][sp], res["T3"][sp], res["BH"][sp]
            checks[sp] = {"return>0": a["total_return_pct"] > 0, "dd<BH": a["max_dd_pct"] < b["max_dd_pct"],
                          "mar>BH": (a["mar"] or -9) > (b["mar"] or -9), "costs<T3": a["costs_pct_of_start"] < t["costs_pct_of_start"],
                          "mar>=0.9*T3": (a["mar"] or -9) >= 0.9 * (t["mar"] or 0) if (t["mar"] or 0) > 0 else (a["mar"] or -9) >= (t["mar"] or -9)}
        out[v] = {"checks": checks, "PASS": all(all(c.values()) for c in checks.values())}
    return out


def t3_rules_pass(res: dict, v: str) -> bool:
    for sp in ("DISCOVERY", "CONFIRM"):
        a, b = res[v][sp], res["BH"][sp]
        if not (a["total_return_pct"] > 0 and a["max_dd_pct"] < b["max_dd_pct"] and (a["mar"] or -9) > (b["mar"] or -9)):
            return False
    return True


def main() -> None:
    from src.lake import research as L
    from src.lake import root

    t0 = time.time()
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())
    D_all = L.load(u["chosen"][:30])
    tiers = {"LAB10": [c for c in L.LAB10 if c in D_all], "TOP30": list(D_all)}
    rep = {"version": "review20.v1", "pre_registration": "docs/research/REVIEW_20.md", "tiers": {}}
    for name, coins in tiers.items():
        D = {c: D_all[c] for c in coins}
        base, dbl = run_tier(D, 1.0), run_tier(D, 2.0)
        ver = verdicts(base)
        for v in VARIANTS:
            if v in ver:
                ver[v]["ROBUST"] = t3_rules_pass(dbl, v)
        rep["tiers"][name] = {"coins": sorted(D), "results": base, "double_costs": dbl, "verdicts": ver,
                              "T3_double_costs_passes": t3_rules_pass(dbl, "T3")}
    rep["seconds"] = round(time.time() - t0)
    out = root() / "reports" / "review20_results.json"
    out.write_text(json.dumps(rep, indent=1, default=str))
    for name, t in rep["tiers"].items():
        print("==", name, len(t["coins"]), "coins | T3 at double costs passes:", t["T3_double_costs_passes"])
        for v in VARIANTS:
            r = t["results"][v]
            print(f"  {v:5s}", {sp: (r[sp]["total_return_pct"], r[sp]["max_dd_pct"], r[sp]["mar"], r[sp]["costs_pct_of_start"]) for sp in ("DISCOVERY", "CONFIRM")},
                  "trades", r["trades"], t["verdicts"].get(v, {}).get("PASS", "control"), "robust" if t["verdicts"].get(v, {}).get("ROBUST") else "")
        b = t["results"]["BH"]
        print("  BH   ", {sp: (b[sp]["total_return_pct"], b[sp]["max_dd_pct"], b[sp]["mar"]) for sp in ("DISCOVERY", "CONFIRM")})


if __name__ == "__main__":
    main()
