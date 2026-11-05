"""Lab 7 (5 Nov 2026; Madhav 11:08 Toronto: "yes to all"): PH1, the market's phase (trend up, trend down, range, squeeze), and SP1R, the
options line's 20-session review questions tested on its own walk-forward history. Both specs (india/registrations/ph1_v1.json,
sp1r_v1.json) were committed before any outcome was read. Research rows only: everything stops at 2023; nothing dated 2024 or later and no
sealed folder.

  python -m india.lab7 check      signal counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.lab7 run        register both, compute, record; manifests/lab7.json and registrations/ph1_results_v1.md, sp1r_results_v1.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths, registry
from india import teachers_stock as ts
from india.lab3 import _clean

REG_DIR = Path(__file__).resolve().parent / "registrations"
CUT = pd.Timestamp("2024-01-01")
SPLIT = 2018
IDX = {"NIFTY 50": "nifty", "NIFTY BANK": "banknifty"}
SP1_IDX = {"NIFTY": "nifty", "BANKNIFTY": "banknifty"}


def spec(name: str) -> dict:
    return json.loads((REG_DIR / f"{name}_v1.json").read_text())


def phases() -> pd.DataFrame:
    """One row per index per day with its phase at the close (known that day) and the forward outcomes after the close."""
    D = pd.read_parquet(paths.silver("kite_index") / "day" / "day.parquet", columns=["index_name", "date", "high", "low", "close"])
    D["date"] = pd.to_datetime(D["date"])
    D = D[D["date"] < CUT]
    vix = D[D["index_name"] == "INDIA VIX"].set_index("date")["close"].sort_index()
    vix_lo = vix <= vix.rolling(252, min_periods=200).quantile(0.30)
    out = []
    for name, key in IDX.items():
        x = D[D["index_name"] == name].sort_values("date").drop_duplicates("date").set_index("date")
        c = x["close"]
        s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
        rng20 = (x["high"].rolling(20).max() - x["low"].rolling(20).min()) / c
        sq = rng20 <= rng20.rolling(252, min_periods=200).quantile(0.20)
        f = pd.DataFrame({"index": key, "close": c})
        f["trend_up"] = (c > s50) & (c > s200)
        f["trend_down"] = (c < s50) & (c < s200)
        f["range"] = s200.notna() & ~f["trend_up"] & ~f["trend_down"]
        f["squeeze"] = sq.fillna(False)
        f["low_vix"] = vix_lo.reindex(f.index).fillna(False)
        f["fwd10"] = c.shift(-10) / c - 1
        f["fwd20"] = c.shift(-20) / c - 1
        f["abs_fwd10"] = f["fwd10"].abs()
        f = f[s200.notna()]
        out.append(f.reset_index())
    return pd.concat(out, ignore_index=True)


def sp1_rows(P: pd.DataFrame) -> pd.DataFrame:
    """The options line's walk-forward trades, each with its index's phase at the previous session's close and the opening gap."""
    T = pd.read_parquet(paths.gold() / "studies" / "SP1_policy_trades.parquet")
    T["date"] = pd.to_datetime(T["date"])
    T = T[T["date"] < CUT].copy()
    T["key"] = T["index"].map(SP1_IDX)
    prev = P.sort_values("date").copy()
    prev["next_date"] = prev.groupby("index")["date"].shift(-1)       # the phase known at the close before the trade's session
    T = T.merge(prev[["index", "next_date", "squeeze", "range", "trend_up", "trend_down"]].rename(columns={"index": "key", "next_date": "date"}),
                on=["key", "date"], how="left")
    S = pd.read_parquet(paths.gold() / "scenario" / "index_states.parquet", columns=["date", "index", "gap"])
    S["date"] = pd.to_datetime(S["date"])
    T = T.merge(S, on=["date", "index"], how="left")
    T["premium_rs"] = T["opt_prem_in"] * T["lot"]
    return T


def plan_ph1(P: pd.DataFrame, T: pd.DataFrame) -> dict:
    n, b = P[P["index"] == "nifty"], P[P["index"] == "banknifty"]
    return {
        "nifty|squeeze|abs_fwd10": ("level", n, n["squeeze"], "abs_fwd10"),
        "nifty|squeeze|fwd10": ("level", n, n["squeeze"], "fwd10"),
        "nifty|trend_up|fwd20": ("level", n, n["trend_up"], "fwd20"),
        "nifty|trend_down|fwd20": ("level", n, n["trend_down"], "fwd20"),
        "nifty|range|abs_fwd10": ("level", n, n["range"], "abs_fwd10"),
        "banknifty|squeeze|abs_fwd10": ("level", b, b["squeeze"], "abs_fwd10"),
        "nifty|squeeze_low_vix|abs_fwd10": ("level", n[n["date"] >= "2010-03-01"], (n["squeeze"] & n["low_vix"])[n["date"] >= "2010-03-01"], "abs_fwd10"),
        "options_line|after_squeeze|net_bps": ("absolute", T, T["squeeze"].fillna(False).astype(bool), "net_bps"),
        "options_line|after_range|net_bps": ("absolute", T, T["range"].fillna(False).astype(bool), "net_bps"),
    }


def plan_sp1r(T: pd.DataFrame) -> dict:
    bn = T["index"] == "BANKNIFTY"
    fade = (T["point"] == "D0") & (T["gap"].abs() >= 0.01) & (np.sign(T["gap"]) * T["dir"] < 0)
    return {
        "banknifty|below_nifty_bar|net_bps": ("absolute", T, bn & (T["pred_net"] <= 2.5 * T["se"]), "net_bps"),
        "both|d0_gap_fade_1pct|net_bps": ("absolute", T, fade.fillna(False), "net_bps"),
        "both|edge_below_1se|net_bps": ("absolute", T, T["pred_net"] < 1.0 * T["se"], "net_bps"),
    }


def _counts(d: pd.DataFrame, on: pd.Series, col: str) -> dict:
    x = d[on.reindex(d.index).fillna(False).astype(bool)].dropna(subset=[col])
    y = x["date"].dt.year
    return {"signals_dev": int((y < SPLIT).sum()), "signals_val": int((y >= SPLIT).sum()), "sessions": int(x["date"].nunique())}


def check() -> dict:
    P = phases()
    T = sp1_rows(P)
    return {"ph1": {k: _counts(d, on, col) for k, (_, d, on, col) in plan_ph1(P, T).items()},
            "sp1r": {k: _counts(d, on, col) for k, (_, d, on, col) in plan_sp1r(T).items()},
            "trades": int(len(T)), "trades_with_phase": int(T["squeeze"].notna().sum()), "trades_with_gap": int(T["gap"].notna().sum())}


def _option(d: pd.DataFrame, on: pd.Series) -> dict:
    x = d[on.reindex(d.index).fillna(False).astype(bool)]
    v = x[x["date"].dt.year >= SPLIT]
    return {"trades_all_years": int(len(x)), "option_rs_mean_2018_23": float(v["opt_net_rs"].mean()) if len(v) else None,
            "option_rs_sum_2018_23": float(v["opt_net_rs"].sum()) if len(v) else None}


def _study(name: str, s: dict, plan: dict, rerun_reason: str | None, option_rows: bool = False) -> dict:
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"{name}: the spec's z {s['bar']['z']} does not match k {k}")
    variants = s["variants"] if "variants" in s else s["historical_test"]["variants"]
    reg = registry.register(name, family=s["family"], title=s["title"], hypothesis=s.get("hypothesis") or s.get("why", ""), variants=list(variants),
                            note=f"spec india/registrations/{name.lower()}_v1.json (written and committed before the run)",
                            bar_families=s["bar"].get("bar_families"), union_k=k, rerun_reason=rerun_reason)
    rows = []
    for var, (how, d, on, col) in plan.items():
        expect = int(variants[var])
        r = ts.level(d, on, col) if how == "level" else ts.absolute(d, on, col)
        extra = {**r["extra"], **_counts(d, on, col), **(_option(d, on) if how == "absolute" else {})}
        rule = "seen_val_only" if how == "absolute" else "standard"
        line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(extra), expect=expect, rule=rule)
        rows.append({"variant": var, "expect": expect, "rule": rule, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])),
                     "val": _clean(list(line["val"])), "extra": _clean(line["extra"])})
    return {"study": name, "registered_at": reg["at"], "k": k, "rows": rows}


def sizing(T: pd.DataFrame) -> dict:
    v = T[T["date"].dt.year >= SPLIT].dropna(subset=["premium_rs"])
    out = {}
    for ix, g in v.groupby("index"):
        out[ix] = {"trades": int(len(g)), "premium_median_rs": float(g["premium_rs"].median()),
                   "share_over_12500": float((g["premium_rs"] > 12500).mean()),
                   "worst_option_loss_rs": float(g["opt_net_rs"].min()), "worst_as_share_of_50000": float(-g["opt_net_rs"].min() / 50000)}
    return out


def run(rerun_reason: str | None = None) -> dict:
    P = phases()
    T = sp1_rows(P)
    ph1 = _study("PH1", spec("ph1"), plan_ph1(P, T), rerun_reason)
    sp1r = _study("SP1R", spec("sp1r"), plan_sp1r(T), rerun_reason)
    sp1r["sizing"] = sizing(T)
    sp1r["note"] = ("sizing uses each era's own lot size and option price; today's one Bank Nifty lot (30) of a near-the-money option costs about "
                    "Rs 24,000, about half of the Rs 50,000 options money")
    out = {"ph1": ph1, "sp1r": sp1r, "phase_shares_nifty": {k: float(P.loc[P["index"] == "nifty", k].mean()) for k in ("trend_up", "trend_down", "range", "squeeze")}}
    (paths.manifest_dir() / "lab7.json").write_text(json.dumps(out, indent=1, default=str))
    _pages(out)
    registry.mirror_to_catalog()
    return out


def _f(x, pct=True) -> str:
    if x is None or x != x:
        return "n/a"
    return f"{100 * x:+.2f}%" if pct else f"{x:+.2f}"


def _t(x) -> str:
    return "n/a" if x is None or x != x else f"{x:.2f}"


def _pages(out: dict) -> None:
    p = out["ph1"]
    L = ["# PH1 results: the market's phase (Nifty and Bank Nifty, 2003-2023)", "",
         f"Registered {p['registered_at']}; k {p['k']}, bar z {registry.threshold(p['k']):.2f}. Spec: `india/registrations/ph1_v1.json`.",
         "Index rows: the signal days' mean minus all days' mean in the same quarter (t across quarters). Options-line rows: their own mean "
         "net basis points, 2018-2023 scored only (seen years).", "",
         "| variant | verdict | 2003-17 (t) | 2018-23 (t) | days or trades (dev / val) |", "|---|---|---|---|---|"]
    for r in p["rows"]:
        d, v, e = r["dev"], r["val"], r["extra"]
        bps = r["variant"].endswith("net_bps")
        L.append(f"| {r['variant']} | {r['verdict']} | {_f(d[0], not bps)} ({_t(d[1])}) | {_f(v[0], not bps)} ({_t(v[1])}) | "
                 f"{e.get('signals_dev')} / {e.get('signals_val')} |")
    L += ["", "Share of Nifty days in each phase: " + ", ".join(f"{k} {100 * v:.0f}%" for k, v in out["phase_shares_nifty"].items())]
    (REG_DIR / "ph1_results_v1.md").write_text("\n".join(L) + "\n")
    s = out["sp1r"]
    L = ["# SP1R results: the options line's review questions on its own history (2017-2023)", "",
         f"Registered {s['registered_at']}; k {s['k']}, bar z {registry.threshold(s['k']):.2f}. Spec: `india/registrations/sp1r_v1.json`. "
         "Seen years: 2018-2023 scored only; support is never confirmation.", "",
         "| question | verdict | 2018-23 mean net bps (t) | trades (2017 / 2018-23) | one-lot option, 2018-23 sum |", "|---|---|---|---|---|"]
    for r in s["rows"]:
        v, e = r["val"], r["extra"]
        L.append(f"| {r['variant']} | {r['verdict']} | {_f(v[0], False)} ({_t(v[1])}) | {e.get('signals_dev')} / {e.get('signals_val')} | "
                 f"Rs {e.get('option_rs_sum_2018_23') or 0:,.0f} |")
    L += ["", "Sizing (2018-2023, each era's own lot and price):"]
    for ix, z in s["sizing"].items():
        L.append(f"- {ix}: {z['trades']} trades; median premium Rs {z['premium_median_rs']:,.0f}; {100 * z['share_over_12500']:.0f}% above Rs 12,500; "
                 f"worst one-trade option loss Rs {z['worst_option_loss_rs']:,.0f} ({100 * z['worst_as_share_of_50000']:.0f}% of Rs 50,000)")
    L += ["", s["note"] + "."]
    (REG_DIR / "sp1r_results_v1.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["check"])[0]
    print(json.dumps(check() if cmd == "check" else run(), indent=1, default=str))
