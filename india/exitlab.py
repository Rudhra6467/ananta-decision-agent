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
from india import settings as _settings
NOTIONAL = float(_settings.load()["stock"]["notional_inr"])  # same as the paper book (india/paper_config.json); the fixed DP charge makes cost % depend on it


@dataclass(frozen=True)
class Policy:
    name: str
    kind: str          # hold, target, atr_trail, sma_close, swing_low, scale_half, random
    n: float = 0.0     # days, R multiple, ATR multiple or window depending on kind
    sig: tuple = ()    # turn-warning / level-break signals that also trigger an exit (decided at the close, filled at the next open)

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


# --- exit signals: each looks only at bars up to and including bar i (aux arrays are built from history up to that bar) ---------------------------------------
def _sig_vol_climax(i, o, h, l, c, a, entry, peak):
    return a["vol_ratio"][i] > 3 and c[i] > o[i] and (h[i] - l[i]) > 1.5 * a["atr"][i]


def _sig_extended(i, o, h, l, c, a, entry, peak):
    return a["dist20"][i] > 0.15


def _sig_three_down(i, o, h, l, c, a, entry, peak):
    return i >= 3 and c[i] < c[i - 1] < c[i - 2] < c[i - 3]


def _sig_gap_down(i, o, h, l, c, a, entry, peak):
    return i >= 1 and o[i] / c[i - 1] - 1 < -0.03


def _sig_range_down(i, o, h, l, c, a, entry, peak):
    return (h[i] - l[i]) > 2 * a["atr"][i] and c[i] < o[i]


def _sig_prev_low(i, o, h, l, c, a, entry, peak):
    return i >= 1 and c[i] < l[i - 1]


def _sig_low20(i, o, h, l, c, a, entry, peak):
    return c[i] < a["ll20"][i]


def _sig_giveback(i, o, h, l, c, a, entry, peak):
    gain = peak - entry
    return gain > 2 * a["atr"][i] and (peak - c[i]) > 0.5 * gain


SIGS = {"vol_climax": _sig_vol_climax, "extended20": _sig_extended, "three_down": _sig_three_down, "gap_down": _sig_gap_down, "range_down": _sig_range_down,
        "prev_low": _sig_prev_low, "low20": _sig_low20, "giveback50": _sig_giveback}


def aux_arrays(o, h, l, c, v) -> dict:
    """Indicator arrays over the whole history of one stock (each value uses data up to and including that bar)."""
    n = len(c)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    cs = np.cumsum(np.r_[0.0, tr])
    atr = np.full(n, np.nan)
    k = 14
    atr[k - 1:] = (cs[k:] - cs[:-k]) / k
    vs = np.cumsum(np.r_[0.0, v.astype(float)])
    vavg_prev = np.full(n, np.nan)
    vavg_prev[20:] = (vs[20:n] - vs[0:n - 20]) / 20  # mean of the 20 sessions before bar i
    cc = np.cumsum(np.r_[0.0, c])
    sma20 = np.full(n, np.nan)
    sma20[19:] = (cc[20:] - cc[:-20]) / 20
    ll20 = np.full(n, np.nan)
    if n > 20:
        win = np.lib.stride_tricks.sliding_window_view(l, 20)  # window ending at j covers j..j+19; the 20 sessions before bar i end at i-1
        ll20[20:] = win[:n - 20].min(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return {"atr": atr, "vol_ratio": v / vavg_prev, "dist20": c / sma20 - 1, "ll20": ll20}


def _exit(pol: Policy, o, h, l, c, entry: float, risk: float, rng: random.Random | None = None, live: bool = False, rand_day: int | None = None, aux: dict | None = None):
    """Walk forward over arrays that start at the entry day. Returns (exit_index, exit_price, reason, peak_high). Index 0 is the entry day."""
    stop = entry - risk
    peak = entry
    n = len(o)
    half_done = False
    realised_half = 0.0
    pending = None  # an exit decided at a close, filled at the next open
    if rand_day is None and pol.kind == "random" and rng:
        rand_day = rng.randint(1, min(HORIZON, n - 1))
    still_open = live and n < HORIZON + 1  # live: the data simply has not arrived yet, so no exit is not the same as the 60-session horizon
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
        if pending is None and pol.sig and aux is not None:
            for sname in pol.sig:
                if SIGS[sname](i, o, h, l, c, aux, entry, peak):
                    pending = "sig_" + sname
                    break
        if i == n - 1 and pending is None and not still_open:
            return i, c[i], "end", peak
    if still_open:
        return n - 1, c[-1], ("pending" if pending else "open"), peak
    return n - 1, c[-1], "end", peak


_CA = None


def ca_flags() -> dict:
    """sid -> sorted dates of corporate-action events left unapplied because the price does not confirm them (gold/ca_flags, from india.lab)."""
    global _CA
    if _CA is None:
        from india import paths
        f = paths.gold() / "ca_flags" / "ca_flags.parquet"
        _CA = {}
        if f.exists():
            d = pd.read_parquet(f)
            for sid, g in d.groupby("sid"):
                _CA[sid] = np.sort(pd.to_datetime(g["date"]).values.astype("datetime64[D]"))
    return _CA


def simulate(entries: pd.DataFrame, bars: dict, features: pd.DataFrame, policies=None, seed: int = 7, random_draws: int = 5) -> pd.DataFrame:
    """entries: [sid, signal_date]. bars: sid -> (dates ndarray[datetime64[D]], o, h, l, c). features: has [sid, date, atr14, liq_rank]."""
    policies = list(policies or DEFAULT_POLICIES)
    atr = features.set_index(["sid", "date"])[["atr14", "liq_rank"]].sort_index()
    rows = []
    skipped = 0
    skipped_ca = 0
    caf = ca_flags()
    aux_cache: dict = {}
    rng = random.Random(seed)
    for sid, sig in zip(entries["sid"], pd.to_datetime(entries["signal_date"])):
        b = bars.get(sid)
        if b is None:
            continue
        dates, o, h, l, c, v = b
        if sid not in aux_cache:
            aux_cache[sid] = aux_arrays(o, h, l, c, v)
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
        ax = {k_: arr[i0:j1] for k_, arr in aux_cache[sid].items()}
        # data hygiene (not a forward-looking selection on returns): a window with a trading halt of more than 10 calendar days, or a one-day move above 50% in the adjusted
        # bars, is a corporate-action or suspension artefact we cannot trade through; it is skipped and counted
        dd = np.diff(dates[i0:j1]).astype("timedelta64[D]").astype(int)
        jump = np.abs(cc[1:] / cc[:-1] - 1) if len(cc) > 1 else np.array([0.0])
        if (len(dd) and dd.max() > 10) or jump.max() > 0.5:
            skipped += 1
            continue
        # an unconfirmed corporate action in the 200 sessions before the signal (it would bend the indicators) or inside the holding window: skipped and counted
        if sid in caf:
            lo_d, hi_d = dates[max(0, i0 - 200)], dates[j1 - 1]
            ev = caf[sid]
            if ((ev > lo_d) & (ev <= hi_d)).any():
                skipped_ca += 1
                continue
        entry = oo[0]
        risk = STOP_ATR * a
        if risk >= entry:
            continue
        for pol in policies + [Policy("random_exit", "random")]:
            draws = random_draws if pol.kind == "random" else 1
            for _ in range(draws):
                k, px, why, peak = _exit(pol, oo, hh, ll, cc, entry, risk, rng, aux=ax)
                r = _row(sid, sig, dates[i0], pol.name, entry, risk, k, px, why, peak, hh[: k + 1], ll[: k + 1], rank)
                # time-matched null: same entry, same stop, held exactly as long, no exit skill -> isolates what the exit rule adds beyond exposure time
                # an intraday exit (stop, target) happened during day k, so the null must live through day k: it leaves at the next open. A close-based exit already left at the open of day k.
                nh = k + 1 if why in ("stop", "target") else k  # signal exits are close-based like the moving-average ones: they leave at the next open
                kn, pxn, _, _ = _exit(Policy("null", "hold", max(nh, 1)), oo, hh, ll, cc, entry, risk)
                r["null_net_ret"] = _row(sid, sig, dates[i0], "null", entry, risk, kn, pxn, "", peak, hh[: kn + 1], ll[: kn + 1], rank)["net_ret"]
                rows.append(r)
    out = pd.DataFrame(rows)
    out.attrs["skipped_data_hygiene"] = skipped
    out.attrs["skipped_ambiguous_ca"] = skipped_ca
    return out


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
        by_date = g.groupby(g["signal_date"].dt.to_period("Q"))["net_ret"].mean()  # quarter blocks: neighbouring dates share overlapping holds
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
    df = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["sid", "date", "o", "h", "l", "c", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] <= pd.Timestamp(min(hi, "2023-12-31"))]
    if sids is not None:
        df = df[df["sid"].isin(set(sids))]
    out = {}
    for sid, g in df.groupby("sid", sort=False):
        out[sid] = (g["date"].values.astype("datetime64[D]"), g["o"].values, g["h"].values, g["l"].values, g["c"].values, g["volume"].values)
    return out


# Turn-warning variants for E03/E07: the loose 4-ATR trail alone, and the same trail with one extra signal that can end the trade earlier.
TRAIL = Policy("trail4", "atr_trail", 4)
TURN_POLICIES = [TRAIL] + [Policy(f"trail4+{n}", "atr_trail", 4, sig=(n,)) for n in SIGS] + [Policy("hold60+low20", "hold", 60, sig=("low20",)), Policy("hold60+prev_low", "hold", 60, sig=("prev_low",))]
