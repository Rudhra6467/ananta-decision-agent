"""Options realism (limitation 2, 19 Oct): how much of each options result survives wider bid-ask, and the spread at which it disappears.

  python -m india.optreal          reads the per-trade rows the studies saved (gold/studies F01, F02, F05-O04), re-prices every trade at
                                   0x, 1x, 2x and 4x the assumed half-spread, finds the breakeven multiple, and, once india.spreads has real
                                   Kite order books, sets the measured half-spread next to it. Writes registrations/options_realism.md and
                                   manifests/options_realism.json.

Every options number here is RECONSTRUCTED, never observed: F01/F02 use NSE settlement prices (not tradable quotes), F05 uses Black-76
prices made from the index minute path (no smile, no intraday IV change). The 1x spread is an assumption (0.4% of premium, at least
Rs 0.05 a leg). A result counts as "spread-robust" only if it is still positive at 2x AND the breakeven multiple is above the measured one;
until measured spreads exist the verdict is "unproven: spread not measured". These checks are robustness reads of studies already
registered; they are not new hypotheses and add nothing to the registry's test count.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from india import optpaper, paths

HERE = paths.Path(__file__).resolve().parent if hasattr(paths, "Path") else None
SPLIT = 2018
MULTS = (0.0, 1.0, 2.0, 4.0)
HS_PCT, HS_MIN = 0.004, 0.05


def _exit_hs(out: pd.Series) -> pd.Series:
    """The exit half-spread the sim charged, recovered from the stored exit price (exit = open - max(0.05, 0.4% of open))."""
    open_pct = out / (1 - HS_PCT)
    open_ = np.where(open_pct * HS_PCT >= HS_MIN, open_pct, out + HS_MIN)
    return pd.Series(open_ - np.maximum(out, 0.0), index=out.index)


def load() -> dict[str, pd.DataFrame]:
    st = paths.gold() / "studies"
    out = {}
    f1 = pd.read_parquet(st / "F01_straddles.parquet")
    f1["group"] = "F01 k" + f1["k"].astype(str) + "|" + f1["symbol"]
    f1["day"] = pd.to_datetime(f1["date"])
    f1["premium_leg"] = (f1["ce"] + f1["pe"]) / 2
    out["F01"] = f1
    f2 = pd.read_parquet(st / "F02_strangles.parquet")
    f2["group"] = "F02 eve_strangle|" + f2["symbol"]
    f2["day"] = pd.to_datetime(f2["date"])
    f2["premium_leg"] = (f2["sc"] + f2["sp"]) / 2
    out["F02"] = f2
    f5 = pd.read_parquet(st / "F05-O04_trades.parquet")
    entry_hs = f5["ce_in"] + f5["pe_in"] - f5["paid_mid"]
    f5["spread_inr"] = (entry_hs + _exit_hs(f5["ce_out"]) + _exit_hs(f5["pe_out"])) * f5["lot"]
    f5["pnl_inr"] = f5["net_inr"]
    f5["ret_on_book"] = f5["net_ret_on_book"]
    f5["group"] = "F05 " + f5["variant"]
    f5["day"] = pd.to_datetime(f5["day"])
    f5["premium_leg"] = f5["paid_mid"] / 2
    out["F05"] = f5
    return out


def _t(x: pd.Series, days: pd.Series, by_quarter: bool) -> tuple[float, float, int]:
    if by_quarter:
        x = x.groupby(days.dt.to_period("Q")).mean()
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), n
    se = x.std(ddof=1) / math.sqrt(n)
    return float(x.mean()), float(x.mean() / se) if se else float("nan"), n


def measured_multiple(premium_leg: pd.Series) -> float | None:
    """Median of (measured half-spread / study half-spread) across the premium sizes these trades actually had; None until spreads exist."""
    p = paths.data_dir() / "silver" / "option_spreads" / "spreads.parquet"
    if not p.exists():
        return None
    s = pd.read_parquet(p)
    s = s[s["two_sided"]]
    if len(s) < 500:
        return None
    s["study_hs"] = np.maximum(HS_MIN, HS_PCT * s["mid"])
    bins = [0, 2, 5, 20, 50, 150, 1e9]
    s["b"] = pd.cut(s["mid"], bins)
    ratio = (s.groupby("b", observed=True)["half_spread"].median() / s.groupby("b", observed=True)["study_hs"].median())
    tb = pd.cut(premium_leg, bins).value_counts(normalize=True)
    w = tb.reindex(ratio.index).fillna(0)
    return float((ratio * w).sum() / w.sum()) if w.sum() else None


def run() -> dict:
    data = load()
    rows = []
    for study, df in data.items():
        by_q = study in ("F01", "F02")  # overlapping-in-a-quarter expiries: quarter blocks, as in the registry; F05 one trade a day: days
        book = df["pnl_inr"] / df["ret_on_book"].replace(0, np.nan)
        book = float(book.dropna().median())
        for g, x in df.groupby("group"):
            x = x.sort_values("day")
            mm = measured_multiple(x["premium_leg"])
            for per, m in (("dev", x["day"].dt.year < SPLIT), ("val", x["day"].dt.year >= SPLIT)):
                y = x[m]
                if len(y) < 5:
                    continue
                r = {"study": study, "group": g, "period": per, "trades": int(len(y)), "years": f"{y['day'].dt.year.min()}-{y['day'].dt.year.max()}",
                     "mean_pnl_inr": float(y["pnl_inr"].mean()), "mean_spread_inr": float(y["spread_inr"].mean()),
                     "spread_share_of_gross": float(y["spread_inr"].mean() / (y["pnl_inr"].mean() + y["spread_inr"].mean()))
                     if (y["pnl_inr"].mean() + y["spread_inr"].mean()) > 0 else None}
                for k in MULTS:
                    adj = (y["pnl_inr"] - (k - 1) * y["spread_inr"]) / book
                    mean, t, n = _t(adj, y["day"], by_q)
                    r[f"ret_{k:g}x"], r[f"t_{k:g}x"] = mean, t
                r["breakeven_multiple"] = float(1 + y["pnl_inr"].mean() / y["spread_inr"].mean()) if y["spread_inr"].mean() > 0 else None
                r["breakeven_half_spread_pct"] = r["breakeven_multiple"] * HS_PCT if r["breakeven_multiple"] is not None else None
                r["measured_multiple"] = mm
                be = r["breakeven_multiple"]
                if r["ret_0x"] <= 0:
                    v = "no edge even with zero spread"
                elif r["ret_1x"] <= 0:
                    v = "edge exists only below the assumed spread"
                elif r["ret_2x"] <= 0:
                    v = "fragile: gone at 2x the assumed spread"
                elif mm is None:
                    v = "survives 2x; unproven: spread not measured"
                elif be is not None and be > mm * 1.5:
                    v = "spread-robust (breakeven > 1.5x measured)"
                else:
                    v = "fails at the measured spread"
                r["realism_verdict"] = v
                rows.append(r)
    df = pd.DataFrame(rows)
    (paths.manifest_dir() / "options_realism.json").write_text(df.to_json(orient="records", indent=1))
    _report(df)
    return {"rows": len(df), "verdicts": df["realism_verdict"].value_counts().to_dict()}


def _report(df: pd.DataFrame) -> None:
    from pathlib import Path
    L = ["# Options realism: spread sensitivity of every options result", "",
         "Generated by `python -m india.optreal`. **All options results are reconstructed, not observed.** F01/F02 price at NSE settlement prices; "
         "F05 prices with Black-76 from the index minute path (no smile, no intraday IV change). The 1x spread is an assumption: 0.4% of premium per leg "
         "per side, at least Rs 0.05. `ret_kx` is the mean return on the book per trade with the half-spread multiplied by k (dev t is across quarter means "
         "for F01/F02, across days for F05). `breakeven` is the multiple of the assumed spread at which the mean trade is zero; "
         "`measured` is the real Kite order-book spread as a multiple of the assumption (blank until india.spreads has recorded sessions).", "",
         "Rule: an options result can feed a decision only if it is positive at 2x, and its breakeven multiple is at least 1.5x the measured multiple.", "",
         "| study | group | period | trades | ret 0x | ret 1x (t) | ret 2x (t) | ret 4x | spread share of gross | breakeven x (half-spread %) | measured x | verdict |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    def ok(v):
        return v is not None and v == v
    for r in df.to_dict(orient="records"):
        be = r["breakeven_multiple"]
        be = f"{be:.1f}x ({r['breakeven_half_spread_pct']*100:.2f}%)" if ok(be) and be > 0 else "below zero"
        sh = f"{r['spread_share_of_gross']:.0%}" if ok(r["spread_share_of_gross"]) else "n/a"
        mm = f"{r['measured_multiple']:.2f}" if ok(r["measured_multiple"]) else "not measured"
        L.append(f"| {r['study']} | {r['group']} | {r['period']} {r['years']} | {r['trades']} | {r['ret_0x']*100:+.3f}% | {r['ret_1x']*100:+.3f}% ({r['t_1x']:+.1f}) | "
                 f"{r['ret_2x']*100:+.3f}% ({r['t_2x']:+.1f}) | {r['ret_4x']*100:+.3f}% | {sh} | {be} | {mm} | {r['realism_verdict']} |")
    L += ["", "## What this means", ""]
    vc = df[df["period"] == "val"]["realism_verdict"].value_counts()
    L += [f"- validation-period groups: " + "; ".join(f"{k}: {v}" for k, v in vc.items()),
          "- Spread is not what decides F01/F02: where they are positive, the assumed spread is 3-15% of the gross edge and the breakeven is 6-35x the "
          "assumption. What decides them is whether the settlement price was a price anyone could trade, and the tail (worst days in the F01/F02 study notes).",
          "- F05 (O-04 synthetic) loses even with zero spread, so spread realism cannot rescue it; its doubt is the synthetic price itself (flat IV through the "
          "afternoon, which if anything flatters a long straddle, since implied volatility usually falls into expiry). R01 on recorded expiry days settles it.",
          "- Nothing options-related feeds a decision until (a) measured spreads exist (india.spreads, needs a Kite sign-in after 20:30 Toronto) and "
          "(b) the expiry-eve settle check below has rows.", ""]
    sp = paths.manifest_dir() / "settle_vs_tradable.json"
    if sp.exists():
        s = json.loads(sp.read_text())
        L += [f"## Were settlement prices tradable? (recorded live contracts {s['window']}, {s['contract_days']} contract-days, {s['days']} sessions)", "",
              "Settle (NSE bhavcopy, sealed 2026 rows read for calibration; no rule scored) against the volume-weighted price actually traded in the last "
              "30 minutes (Kite minutes from the recorder). Signed gap > 0: settle above what traded (overstates a seller's credit).", "",
              "| index | expiry eve/day | premium Rs | contract-days | no trade in last 30 min | median signed gap | median abs gap | p90 abs gap |", "|---|---|---|---|---|---|---|---|"]
        for r in s["table"]:
            L.append(f"| {r['name']} | {'yes' if r['eve_or_expiry'] else 'no'} | {r['premium']} | {r['contract_days']} | {r['no_trade_last30']:.1%} | "
                     f"{r['median_signed_gap']:+.2%} | {r['median_abs_gap']:.2%} | {r['p90_abs_gap']:.2%} |")
        if not any(r["eve_or_expiry"] for r in s["table"]):
            L += ["", "No expiry-eve or expiry-day rows yet: the recorder's mapped contracts all expire after the window. F02 (expiry eve) and F05 (expiry day) "
                  "stay unmeasured until this week's expiries are recorded."]
        L += [""]
    Path(__file__).resolve().parent.joinpath("registrations", "options_realism.md").write_text("\n".join(L) + "\n")


def settle_vs_tradable() -> dict:
    """Were NSE settlement prices tradable? For every recorded live contract-day (the recorder's real Kite minutes), compare the bhavcopy settle
    (sealed 2026 rows, purpose calibration: a data check, no rule is scored) with what actually traded: the last 30 minutes' volume-weighted price,
    whether the contract traded at all in that window, and how stale its last trade was. Grouped by premium size, the axis that separates F01's
    at-the-money legs from F02's cheap hedges."""
    import csv
    import glob
    import gzip

    from india import sealed
    inst = {}
    for f in sorted(glob.glob(str(paths.bronze("kite_instruments") / "NFO_*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["segment"] == "NFO-OPT":
                inst[r["tradingsymbol"]] = (r["name"], r["expiry"], float(r["strike"]), r["instrument_type"])
    rows = []
    for f in glob.glob(str(paths.bronze("kite_1m_fo") / "*" / "*.jsonl.gz")):
        sym = f.rsplit("/", 1)[1].replace(".jsonl.gz", "")
        if sym not in inst:
            continue
        candles = {}
        with gzip.open(f, "rt") as fh:
            for line in fh:
                for c in json.loads(line).get("candles") or []:
                    candles[c[0]] = c  # later fetches overwrite earlier ones (the last window is still growing)
        if not candles:
            continue
        c = pd.DataFrame(list(candles.values()), columns=["ts", "o", "h", "l", "c", "v"])
        c["ts"] = pd.to_datetime(c["ts"])
        c["date"] = c["ts"].dt.tz_localize(None).dt.normalize()
        c["mins_to_close"] = (c["date"] + pd.Timedelta(hours=15, minutes=30) - c["ts"].dt.tz_localize(None)).dt.total_seconds() / 60
        c = c[c["mins_to_close"] >= 0]  # Kite serves a few candles after 15:30; the session ends at 15:30
        for d, x in c.groupby("date"):
            last30 = x[(x["mins_to_close"] <= 30) & (x["v"] > 0)]
            traded = x[x["v"] > 0]
            vwap = float((last30["c"] * last30["v"]).sum() / last30["v"].sum()) if len(last30) else None
            rows.append({"tradingsymbol": sym, "date": d, "name": inst[sym][0], "expiry": pd.Timestamp(inst[sym][1]), "strike": inst[sym][2], "opt_type": inst[sym][3],
                         "vwap30": vwap, "last_close": float(x["c"].iloc[-1]), "vol_day": float(x["v"].sum()), "vol_last30": float(last30["v"].sum()),
                         "mins_since_last_trade": float(traded["mins_to_close"].min()) if len(traded) else None})
    m = pd.DataFrame(rows)
    if m.empty:
        return {"rows": 0}
    since = str(m["date"].min().date())
    b = sealed.read_cols("calibration", "silver/fo_bhavcopy", ["date", "symbol", "expiry", "strike", "opt_type", "close", "settle", "volume"], since,
                         "instrument = 'OPTIDX' and symbol in ('NIFTY', 'BANKNIFTY')")
    b["date"], b["expiry"] = pd.to_datetime(b["date"]), pd.to_datetime(b["expiry"])
    j = m.merge(b.rename(columns={"symbol": "name", "volume": "nse_volume"}), on=["name", "date", "expiry", "strike", "opt_type"], how="inner")
    j = j[j["settle"] > 0]
    j["gap_vs_vwap30"] = j["settle"] / j["vwap30"] - 1
    j["no_trade_last30"] = j["vwap30"].isna()
    j["premium"] = pd.cut(j["settle"], [0, 2, 5, 20, 50, 150, 1e9], labels=["<2", "2-5", "5-20", "20-50", "50-150", "150+"])
    j["dte"] = (j["expiry"] - j["date"]).dt.days
    j["eve_or_expiry"] = j["dte"] <= 1
    g = j.groupby(["name", "eve_or_expiry", "premium"], observed=True).agg(contract_days=("settle", "size"), no_trade_last30=("no_trade_last30", "mean"),
                                                         median_signed_gap=("gap_vs_vwap30", "median"),
                                                         median_abs_gap=("gap_vs_vwap30", lambda x: x.abs().median()),
                                                         p90_abs_gap=("gap_vs_vwap30", lambda x: x.abs().quantile(0.9)),
                                                         median_mins_since_trade=("mins_since_last_trade", "median")).reset_index()
    j.to_parquet(paths.gold() / "studies" / "settle_vs_tradable.parquet")
    out = {"contract_days": int(len(j)), "days": int(j["date"].nunique()), "window": f"{j['date'].min().date()}..{j['date'].max().date()}",
           "table": g.round(4).to_dict(orient="records")}
    (paths.manifest_dir() / "settle_vs_tradable.json").write_text(json.dumps(out, indent=1, default=str))
    print(g.round(4).to_string(index=False), flush=True)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "settle":
        r = settle_vs_tradable()
        print(json.dumps({k: v for k, v in r.items() if k != "table"}), flush=True)
    else:
        print(json.dumps(run(), indent=1))
