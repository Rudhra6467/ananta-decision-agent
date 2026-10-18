"""The exit-evaluation harness and the null engine.

One set of entries, many exit policies, the same costs, scored on what Madhav cares about: how much of the move the exit kept, how much it gave
back, the worst loss, and whether it beat doing something dumb (random exits, nothing).

  from india import exitlab
  trades = exitlab.simulate(entries, policies)        entries: DataFrame [sid, signal_date]; acts at the NEXT session's open
  exitlab.summarise(trades)                           one row per policy, split by dev and validation years

Rules baked in (so no study can break them by accident):
* Signal on the close of day t, entry at the open of t+1 (adjusted prices). Close-based exit rules fill at the next session's open.
* Every policy shares the same initial protective stop, entry - STOP_ATR x ATR14 (known at the signal date), so R is comparable across policies.
* Stop hit when the low reaches the stop; fill at the stop, or at the open if the bar gaps through it. A stop and a target in the same bar count as
  the stop (the unfavourable reading).
* Costs: delivery round trip from india.costs on a fixed notional, plus the spread estimate for the stock's liquidity rank (labelled estimate).
* Trades on the same dates move together, so the t-statistic is computed on date means, not on trades.
Prices come from the lab's adjusted bars; sealed years are never loaded here.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
import pandas as pd

from india import costs

STOP_ATR = 2.0
HORIZON = 60
NOTIONAL = 100_000.0


@dataclass(frozen=True)
class Policy:
    name: str
    kind: str          # hold, target, atr_trail, sma_close, swing_low, scale_half, random
    n: float = 0.0     # days, R multiple, ATR multiple or window depending on kind

    def __str__(self) -> str:
        return self.name


DEFAULT_POLICIES = (
    [Policy(f"hold_{d}d", "hold", d) for d in (5, 10, 20, 40, 60)]
    + [Policy(f"target_{m}R", "target", m) for m in (1, 2, 3)]
    + [Policy(f"atr_trail_{k}", "atr_trail", k) for k in (2, 3, 4)]
    + [Policy(f"sma_close_{n}", "sma_close", n) for n in (10, 20, 50)]
    + [Policy(f"swing_low_{n}", "swing_low", n) for n in (5, 10, 20)]
    + [Policy("scale_half_then_trail3", "scale_half", 3)]
)


def _exit(pol: Policy, o, h, l, c, entry: float, risk: float, rng: random.Random | None = None):
    """Walk forward over arrays that start at the entry day. Returns (exit_index, exit_price, reason, peak_high). Index 0 is the entry day."""
    stop = entry - risk
    peak = entry
    n = len(o)
    half_done = False
    realised_half = 0.0
    pending = None  # an exit decided at a close, filled at the next open
    rand_day = rng.randint(1, min(HORIZON, n - 1)) if (pol.kind == "random" and rng) else None
    for i in range(n):
        if pending is not None:
            return i, o[i], pending, peak
        # protective / trailing stop inside the bar (the entry bar counts: we are in from its open)
        if l[i] <= stop:
            return i, min(o[i], stop), "stop", max(peak, h[i])
        peak = max(peak, h[i])
        if pol.kind == "target":
            tgt = entry + pol.n * risk
            if h[i] >= tgt:
                return i, max(o[i], tgt), "target", peak
        elif pol.kind == "atr_trail":
            stop = max(stop, peak - pol.n * (risk / STOP_ATR))
        elif pol.kind == "scale_half":
            if not half_done and h[i] >= entry + risk:
                half_done = True
                realised_half = entry + risk
                stop = max(stop, entry)
            if half_done:
                stop = max(stop, peak - pol.n * (risk / STOP_ATR))
        # decisions taken at this bar's close, filled at the next open
        if pol.kind == "hold" and i + 1 >= pol.n:
            pending = "time"
        elif pol.kind == "random" and i + 1 >= rand_day:
            pending = "random"
        elif pol.kind == "sma_close" and i + 1 >= pol.n and c[i] < np.mean(c[i + 1 - int(pol.n): i + 1]):
            pending = "sma"
        elif pol.kind == "swing_low" and i >= pol.n and c[i] < np.min(l[i - int(pol.n): i]):
            pending = "swing"
        if i == n - 1 and pending is None:
            return i, c[i], "end", peak
    return n - 1, c[-1], "end", peak


def simulate(entries: pd.DataFrame, bars: dict, features: pd.DataFrame, policies=None, seed: int = 7, random_draws: int = 5) -> pd.DataFrame:
    """entries: [sid, signal_date]. bars: sid -> (dates ndarray[datetime64[D]], o, h, l, c). features: has [sid, date, atr14, liq_rank]."""
    policies = list(policies or DEFAULT_POLICIES)
    atr = features.set_index(["sid", "date"])[["atr14", "liq_rank"]].sort_index()
    rows = []
    rng = random.Random(seed)
    for sid, sig in zip(entries["sid"], pd.to_datetime(entries["signal_date"])):
        b = bars.get(sid)
        if b is None:
            continue
        dates, o, h, l, c = b
        i0 = int(np.searchsorted(dates, np.datetime64(sig.date()), side="right"))  # first session after the signal
        if i0 >= len(dates) or i0 + 2 > len(dates):
            continue
        try:
            a, rank = atr.loc[(sid, sig)]
        except KeyError:
            continue
        if not a or a <= 0:
            continue
        j1 = min(len(dates), i0 + HORIZON + 1)
        oo, hh, ll, cc = o[i0:j1], h[i0:j1], l[i0:j1], c[i0:j1]
        entry = oo[0]
        risk = STOP_ATR * a
        if risk >= entry:
            continue
        for pol in policies + [Policy("random_exit", "random")]:
            draws = random_draws if pol.kind == "random" else 1
            for _ in range(draws):
                k, px, why, peak = _exit(pol, oo, hh, ll, cc, entry, risk, rng)
                rows.append(_row(sid, sig, dates[i0], pol.name, entry, risk, k, px, why, peak, hh[: k + 1], ll[: k + 1], rank))
    return pd.DataFrame(rows)


def _row(sid, sig, entry_date, pol, entry, risk, k, px, why, peak, hh, ll, rank):
    gross = px / entry - 1
    qty = NOTIONAL / entry
    rt = costs.round_trip("delivery", NOTIONAL, px * qty, year=pd.Timestamp(sig).year, turnover_rank=int(rank) if rank == rank else None)
    net = (px * qty - NOTIONAL - rt["total"]) / NOTIONAL
    move = peak - entry
    return {"sid": sid, "signal_date": pd.Timestamp(sig), "policy": pol, "hold_days": k + 1, "reason": why, "gross_ret": gross, "net_ret": net,
            "cost_ret": gross - net, "risk_ret": risk / entry, "r_gross": (px - entry) / risk, "r_net": (net) / (risk / entry), "mfe_r": move / risk, "mae_r": (entry - ll.min()) / risk,
            "capture": float(np.clip((px - entry) / move, -1, 1)) if move > 0 else float("nan"), "giveback_r": (peak - px) / risk}


def summarise(trades: pd.DataFrame, split_year: int = 2018) -> pd.DataFrame:
    """One row per policy and period (dev: before split_year, val: from it). t_stat is on date means (trades on one date move together)."""
    t = trades.copy()
    t["period"] = np.where(t["signal_date"].dt.year < split_year, "dev", "val")
    out = []
    for (pol, per), g in t.groupby(["policy", "period"]):
        by_date = g.groupby("signal_date")["net_ret"].mean()
        se = by_date.std(ddof=1) / math.sqrt(len(by_date)) if len(by_date) > 2 else float("nan")
        out.append({"policy": pol, "period": per, "n": len(g), "dates": len(by_date), "mean_net_ret": g["net_ret"].mean(), "t_stat": by_date.mean() / se if se else float("nan"),
                    "expectancy_R": g["r_net"].mean(), "capture_median": g["capture"].median(), "giveback_R_median": g["giveback_r"].median(), "p5_net_ret": g["net_ret"].quantile(0.05),
                    "worst_net_ret": g["net_ret"].min(), "hold_days_mean": g["hold_days"].mean(), "cost_ret_mean": g["cost_ret"].mean(), "win_rate_info_only": (g["net_ret"] > 0).mean()})
    s = pd.DataFrame(out)
    # excess over the random-exit null, same period
    base = s[s["policy"] == "random_exit"].set_index("period")["mean_net_ret"]
    s["excess_vs_random_exit"] = s.apply(lambda r: r["mean_net_ret"] - base.get(r["period"], float("nan")), axis=1)
    return s.sort_values(["period", "mean_net_ret"], ascending=[True, False]).reset_index(drop=True)


def load_bars(sids=None, hi: str = "2023-12-31") -> dict:
    """Adjusted daily bars from gold/bars (built from silver; the sealed years are not in it). sid -> (dates, o, h, l, c)."""
    from india import paths
    df = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["sid", "date", "o", "h", "l", "c"])
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] <= pd.Timestamp(min(hi, "2023-12-31"))]
    if sids is not None:
        df = df[df["sid"].isin(set(sids))]
    out = {}
    for sid, g in df.groupby("sid", sort=False):
        out[sid] = (g["date"].values.astype("datetime64[D]"), g["o"].values, g["h"].values, g["l"].values, g["c"].values)
    return out
