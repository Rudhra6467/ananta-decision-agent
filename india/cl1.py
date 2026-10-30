"""CL1 (30 Oct 2026, Phase 3.4 of the reverse-engineering plan): the combination lab, done as agreed in the blueprint.

Spec india/registrations/cl1_v1.json, written before any outcome was read. Five stock setups x five market states on the random (ANY)
entries with the 20-session hold: does both-on beat the better single (the interaction)? Plateau over the stock setup's threshold,
consistency across years, a trial penalty (one family bar over all 30 variants) and a random-flag control per market state.

  python -m india.cl1 check          quarter counts per period only (no means, no t, no verdicts)
  python -m india.cl1 run            register with the spec's frozen k, compute, record; manifests/lab5_cl1.json and registrations/cl1_results_v1.md
  python -m india.cl1 table          rewrite the results page from the manifest

Research rows only (2000-2023); nothing from 2024 on, no sealed folder.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import conditions, paths, registry, studies, studies2
from india.lab3 import _clean, _f

REG_DIR = Path(__file__).resolve().parent / "registrations"
SPLIT = 2018
MIN_SIDE = 5
MIN_YEAR_TRADES = 10
SEED = 20261030
POLICY = "hold_20d"

# stock setups: name -> {setting: rule(frame) -> bool Series}; the base setting carries the verdict, loose and tight make the plateau
SETUPS = {
    "rsi_lt30": {"loose": lambda x: x["rsi14"] < 35, "base": lambda x: x["rsi14"] < 30, "tight": lambda x: x["rsi14"] < 25},
    "not_extended": {"loose": lambda x: (x["dist_sma50"] <= 0.25) & (x["ret_20"] <= 0.30), "base": lambda x: (x["dist_sma50"] <= 0.20) & (x["ret_20"] <= 0.25),
                     "tight": lambda x: (x["dist_sma50"] <= 0.15) & (x["ret_20"] <= 0.20)},
    "pull_healthy": {"loose": lambda x: (x["dist_sma20"] >= -0.12) & (x["dist_sma20"] < -0.05) & (x["dist_sma50"] > 0) & (x["vol_ratio20"] < 1.2),
                     "base": lambda x: (x["dist_sma20"] >= -0.12) & (x["dist_sma20"] < -0.05) & (x["dist_sma50"] > 0) & (x["vol_ratio20"] < 1.0),
                     "tight": lambda x: (x["dist_sma20"] >= -0.12) & (x["dist_sma20"] < -0.05) & (x["dist_sma50"] > 0) & (x["vol_ratio20"] < 0.9)},
    "deliv_high": {"loose": lambda x: x["deliv_pct"] > 50, "base": lambda x: x["deliv_pct"] > 60, "tight": lambda x: x["deliv_pct"] > 70},
    "washout60": {"loose": lambda x: x["ret_60"] < -0.25, "base": lambda x: x["ret_60"] < -0.30, "tight": lambda x: x["ret_60"] < -0.35},
}
STATES = ["nifty_gt200d", "breadth_lt30", "vix_gt20", "small_lead", "breadth_thrust"]


def spec() -> dict:
    return json.loads((REG_DIR / "cl1_v1.json").read_text())


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = pd.Series(x).dropna()
    if len(x) < 3:
        return (float("nan"), float("nan"), int(len(x)))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return (float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x)))


def trades() -> pd.DataFrame:
    """The ANY entries with the 20-session hold, joined with the stock features, RSI and the market states on the signal day."""
    f = studies.load_features()
    ctx = conditions.context_table(f)
    mc = conditions.apply_market(ctx).reset_index()
    fx = f[["sid", "date", "ret_20", "ret_60", "dist_sma20", "dist_sma50", "vol_ratio20", "deliv_pct"]].copy()
    ind = studies2._indicators()[["sid", "date", "rsi14"]]
    tr = pd.read_parquet(paths.gold() / "studies" / "E02-ANY_trades.parquet", columns=["sid", "signal_date", "policy", "net_ret"])
    tr = tr[(tr["policy"] == POLICY) & (tr["signal_date"] >= "2000-01-01")].drop(columns="policy")
    tr = tr.merge(fx, left_on=["sid", "signal_date"], right_on=["sid", "date"], how="left").drop(columns="date")
    tr = tr.merge(ind, left_on=["sid", "signal_date"], right_on=["sid", "date"], how="left").drop(columns="date")
    tr = tr.merge(mc[["date"] + ["cond_" + s for s in STATES]], left_on="signal_date", right_on="date", how="left").drop(columns="date")
    tr["q"] = tr["signal_date"].dt.to_period("Q")
    tr["y"] = tr["signal_date"].dt.year
    return tr


def _interaction(tr: pd.DataFrame, s_on: pd.Series, m_on: pd.Series) -> tuple[pd.Series, dict]:
    """Per quarter: mean(both) - max(mean(S on), mean(M on)); quarters with under MIN_SIDE trades in any group are skipped."""
    ok = s_on.notna() & m_on.notna() & tr["net_ret"].notna()
    t = tr[ok]
    s, m = s_on[ok].astype(bool), m_on[ok].astype(bool)
    both = s & m
    g = pd.DataFrame({"q": t["q"], "y": t["y"], "r": t["net_ret"], "both": both, "s": s, "m": m})
    agg = {}
    for name, flag in (("both", both), ("s", s), ("m", m)):
        x = g[flag].groupby("q")["r"].agg(["mean", "size"])
        agg[name] = x
    idx = agg["both"].index.intersection(agg["s"].index).intersection(agg["m"].index)
    rows = []
    for q in idx:
        b, sa, ma = agg["both"].loc[q], agg["s"].loc[q], agg["m"].loc[q]
        if min(b["size"], sa["size"], ma["size"]) < MIN_SIDE:
            continue
        rows.append((q, b["mean"] - max(sa["mean"], ma["mean"])))
    ser = pd.Series({q: v for q, v in rows}, dtype=float)
    # consistency by year
    yb = g[both].groupby("y")["r"].agg(["mean", "size"])
    ys, ym = g[s].groupby("y")["r"].mean(), g[m].groupby("y")["r"].mean()
    years = [y for y in yb.index if yb.loc[y, "size"] >= MIN_YEAR_TRADES and y in ys.index and y in ym.index]
    wins = sum(1 for y in years if yb.loc[y, "mean"] > max(ys[y], ym[y]))
    info = {"n_both": int(both.sum()), "n_s": int(s.sum()), "n_m": int(m.sum()), "mean_both": float(g.loc[both, "r"].mean()) if both.any() else None,
            "mean_s": float(g.loc[s, "r"].mean()) if s.any() else None, "mean_m": float(g.loc[m, "r"].mean()) if m.any() else None,
            "years_scored": len(years), "consistency": (wins / len(years)) if years else None}
    return ser, info


def results(counts_only: bool = False) -> dict:
    tr = trades()
    rng = np.random.default_rng(SEED)
    base_share = float(SETUPS["not_extended"]["base"](tr).mean())
    rand_flag = pd.Series(rng.random(len(tr)) < base_share, index=tr.index).astype(float)
    out = {}
    for setup, settings in list(SETUPS.items()) + [("RANDOM", None)]:
        flags = {k: fn(tr).astype(float).where(tr["rsi14"].notna() | (setup != "rsi_lt30")) for k, fn in settings.items()} if settings else {"base": rand_flag}
        for st in STATES:
            m_on = tr["cond_" + st]
            key = f"{setup}|{st}"
            ser, info = _interaction(tr, flags["base"], m_on)
            if counts_only:
                out[key] = {"events_dev": int(sum(1 for q in ser.index if q.year < SPLIT)), "events_val": int(sum(1 for q in ser.index if q.year >= SPLIT)), "n_both": info["n_both"]}
                continue
            dev = ser[[q.year < SPLIT for q in ser.index]]
            val = ser[[q.year >= SPLIT for q in ser.index]]
            extra = {**info, "events_dev": int(len(dev)), "events_val": int(len(val))}
            if settings:
                plat = {}
                for k in ("loose", "tight"):
                    s2, _ = _interaction(tr, flags[k], m_on)
                    v2 = s2[[q.year >= SPLIT for q in s2.index]]
                    d2 = s2[[q.year < SPLIT for q in s2.index]]
                    plat[k] = {"val_mean": float(v2.mean()) if len(v2) else None, "val_t": _stat(v2)[1], "dev_mean": float(d2.mean()) if len(d2) else None}
                extra["plateau"] = plat
                extra["plateau_holds"] = bool(len(val) and val.mean() > 0 and all((plat[k]["val_mean"] or 0) > 0 for k in plat))
            out[key] = {"dev": _stat(dev), "val": _stat(val), "extra": extra}
    return out


def run(rerun_reason: str | None = None) -> dict:
    s = spec()
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"CL1: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register("CL1", family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note="spec india/registrations/cl1_v1.json (written before the run)", bar_families=s["bar"].get("bar_families"), union_k=k,
                            rerun_reason=rerun_reason)
    res = results()
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(r.get("extra", {})), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])), "val": _clean(list(line["val"])),
                     "extra": _clean(line["extra"])})
    out = {"study": "CL1", "registered_at": reg["at"], "k": k, "rows": rows, "shortlist": shortlist(rows)}
    (paths.manifest_dir() / "lab5_cl1.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    table(out)
    return out


def shortlist(rows: list[dict]) -> list[dict]:
    """The spec's rating: VALIDATED or CONDITIONAL, holds on the plateau, consistency >= 60%; top 10 by validation t."""
    ok = []
    for r in rows:
        e = r["extra"] or {}
        if r["verdict"] in ("VALIDATED", "CONDITIONAL") and e.get("plateau_holds") and (e.get("consistency") or 0) >= 0.6 and not r["variant"].startswith("RANDOM"):
            ok.append({"variant": r["variant"], "verdict": r["verdict"], "val_t": r["val"][1], "val_mean": r["val"][0], "consistency": e.get("consistency"), "n_both": e.get("n_both")})
    return sorted(ok, key=lambda x: -(x["val_t"] or 0))[:10]


TAKEAWAY: list[str] = []


def table(out: dict | None = None) -> Path:
    if out is None:
        out = json.loads((paths.manifest_dir() / "lab5_cl1.json").read_text())
    s = spec()
    L = [f"# CL1 results: {s['title']}", "", f"Registered {out['registered_at']} (spec `cl1_v1.json`, written before the run); family {s['family']}, "
         f"k = {out['k']}, z = {registry.threshold(out['k']):.2f}. Development 2000-2017, validation 2018-2023; nothing from 2024 on. HISTORICAL BACKTEST, paper only.", "",
         "The interaction = mean net 20-session return with both on, minus the better of the two singles, per quarter; t across quarters. Plateau = the same at the "
         "loose and tight thresholds of the stock setup (validation period). Consistency = share of years in which both-on beat the better single.", ""]
    if TAKEAWAY:
        L += ["## In plain words", ""] + TAKEAWAY + [""]
    sl = out.get("shortlist") or []
    L += ["## Shortlist (the spec's rating: a pass, a plateau, consistency 60%+)", ""]
    L += [f"- {x['variant']}: {x['verdict']}, validation {_f(x['val_mean'])} a trade (t {x['val_t']:+.1f}), consistency {_f(x['consistency'])}, both-on trades {x['n_both']}" for x in sl] or ["- none"]
    L += ["", "## The rows", "", "| pair | expected | verdict | dev mean | dev t | dev q | val mean | val t | val q | both-on trades | plateau holds | consistency |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        e = r["extra"] or {}
        d, v = r["dev"], r["val"]
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else '0'} | {r['verdict']} | {_f(d[0])} | {_f(d[1], False)} | {d[2]} | {_f(v[0])} | {_f(v[1], False)} | {v[2]} | "
                 f"{e.get('n_both', 'n/a')} | {'yes' if e.get('plateau_holds') else ('no' if 'plateau_holds' in e else '-')} | {_f(e.get('consistency')) if e.get('consistency') is not None else 'n/a'} |")
    p = REG_DIR / "cl1_results_v1.md"
    p.write_text("\n".join(L) + "\n")
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print(json.dumps(results(counts_only=True), indent=1))
    elif cmd == "run":
        out = run(rerun_reason=(sys.argv[2] if len(sys.argv) > 2 else None))
        for r in out["rows"]:
            print(r["variant"], r["verdict"], "dev", [round(x, 4) if isinstance(x, float) else x for x in r["dev"]], "val", [round(x, 4) if isinstance(x, float) else x for x in r["val"]],
                  "plateau", (r["extra"] or {}).get("plateau_holds"), "cons", (r["extra"] or {}).get("consistency"))
        print("shortlist", out["shortlist"])
    elif cmd == "table":
        print(table())
