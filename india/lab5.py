"""Lab 5 (28 Oct 2026; Madhav 12:23 Toronto: "i approve all"): RX1, the 12 reconstruction drafts of 26-27 Oct. The spec
(india/registrations/rx1_v1.json) was written and committed before any outcome was read; `run` registers the study with the spec's frozen k,
computes, and records every variant in the ledger. Research rows only: the stock panel, the E02 pullback entries and gold/bars all stop at 2023;
nothing dated 2024 or later and no sealed folder.

  python -m india.lab5 check      event counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.lab5 run        register, compute, record; manifests/lab5_rx1.json and registrations/rx1_results_v1.md
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import exitlab, paths, registry
from india import teachers_stock as ts
from india.lab3 import _clean, _f

REG_DIR = Path(__file__).resolve().parent / "registrations"
CUT = pd.Timestamp("2024-01-01")
SPLIT = 2018
SEED = 20261028
IC = 0.0010                     # intraday round trip, information only


def spec() -> dict:
    return json.loads((REG_DIR / "rx1_v1.json").read_text())


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = pd.Series(x).dropna()
    if len(x) < 3:
        return (float("nan"), float("nan"), int(len(x)))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return (float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x)))


def frame() -> pd.DataFrame:
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet",
                        columns=["sid", "symbol", "date", "n", "liq_rank", "o", "h", "l", "c", "ret_1", "dist_sma200", "breakout20", "pos20", "fwd5", "atr14"])
    P["date"] = pd.to_datetime(P["date"])
    P = P[P["date"] < CUT].sort_values(["sid", "date"]).reset_index(drop=True)
    g = P.groupby("sid", sort=False)
    nxt = (g["n"].shift(-1) == P["n"] + 1)
    no, nc = g["o"].shift(-1).where(nxt), g["c"].shift(-1).where(nxt)
    P["next_oc"] = nc / no - 1
    P["next_cc"] = nc / P["c"] - 1
    P["next_gap"] = no / P["c"] - 1
    for col in ("next_oc", "next_cc"):
        P.loc[P[col].abs() > 0.5, col] = np.nan
    prev = (g["n"].shift(1) == P["n"] - 1)
    low20 = g["l"].transform(lambda s: s.shift(1).rolling(20, min_periods=20).min())
    low250 = g["l"].transform(lambda s: s.shift(1).rolling(250, min_periods=250).min())
    P["breakdown20"] = (P["c"] < low20) & prev
    P["newlow252"] = (P["c"] < low250) & prev
    below, above = P["dist_sma200"] < 0, P["dist_sma200"] > 0
    down2, up2 = P["ret_1"] <= -0.02, P["ret_1"] >= 0.02
    P["downtrend_fall"] = below & down2 & ~P["breakdown20"] & ~P["newlow252"]
    P["uptrend_pullback"] = above & down2 & ~P["breakdown20"]
    P["downtrend_rise"] = below & up2
    P["inside_range"] = above & ~P["breakout20"].fillna(False).astype(bool) & P["pos20"].between(0.2, 0.8) & up2
    P["liq"] = P["liq_rank"] <= 250
    # information only: the drafted day shapes on the next session
    P["shape_gap_down_held"] = (P["next_gap"] <= -0.02) & (P["next_oc"] <= 0)
    P["shape_selloff"] = (P["next_gap"] > -0.02) & (P["next_oc"] <= -0.02)
    P["shape_run"] = (P["next_gap"] < 0.02) & (P["next_oc"] >= 0.02)
    return P


LEVEL_PLAN = [("D|breakdown20|next_oc", "breakdown20", "next_oc", -1, "shape_selloff"), ("D|breakdown20|next_cc", "breakdown20", "next_cc", -1, None),
              ("D|newlow252|next_oc", "newlow252", "next_oc", -1, "shape_selloff"), ("D|downtrend_fall|next_oc", "downtrend_fall", "next_oc", -1, "shape_selloff"),
              ("D|uptrend_pullback|next_oc", "uptrend_pullback", "next_oc", -1, "shape_selloff"), ("U|downtrend_rise|next_oc", "downtrend_rise", "next_oc", 1, "shape_run"),
              ("U|inside_range|next_oc", "inside_range", "next_oc", 1, "shape_run"), ("L|downtrend_rise|fwd5", "downtrend_rise", "fwd5", 1, None),
              ("L|inside_range|fwd5", "inside_range", "fwd5", 1, None)]


def _counts(dates: pd.Series) -> dict:
    y = pd.to_datetime(dates).dt.year
    return {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())}


def level_results(P: pd.DataFrame, counts_only: bool = False) -> dict:
    out = {}
    L = P[P["liq"]]
    for key, ev, col, sign, shape in LEVEL_PLAN:
        d = L.dropna(subset=[col])
        on = d[ev].fillna(False).astype(bool)
        cnt = _counts(d.loc[on, "date"])
        if counts_only:
            out[key] = cnt
            continue
        r = ts.level(d, on, col)
        sig = d.loc[on, col]
        extra = {**r["extra"], **cnt, "mean_signal": float(sig.mean()) if len(sig) else None}
        if col == "next_oc":
            extra["mean_after_intraday_cost_in_drafted_direction"] = float((sign * sig - IC).mean()) if len(sig) else None
        if shape:
            extra[f"{shape}_share_signal"] = float(d.loc[on, shape].mean()) if on.any() else None
            extra[f"{shape}_share_all"] = float(d[shape].mean())
        r["extra"] = extra
        out[key] = r
    return out


def _ctl_entries(P: pd.DataFrame) -> pd.DataFrame:
    L = P[P["liq"]][["sid", "date"]]
    rng = np.random.default_rng(SEED)
    picks = []
    for day, g in L.groupby("date", sort=True):
        k = min(5, len(g))
        picks.append(g.iloc[rng.choice(len(g), size=k, replace=False)])
    e = pd.concat(picks).rename(columns={"date": "signal_date"})
    return e


def _nifty_below200() -> pd.Series:
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet", columns=["index_name", "date", "close"])
    ix = ix[ix["index_name"] == "NIFTY 50"].assign(date=lambda d: pd.to_datetime(d["date"]))
    s = ix[(ix["date"] < CUT) & (ix["close"] > 0)].drop_duplicates("date", keep="last").set_index("date").sort_index()["close"].astype(float)
    return s < s.rolling(200, min_periods=200).mean()


def _overlay(entries: pd.DataFrame, bars: dict, feats: pd.DataFrame) -> pd.DataFrame:
    """A = hold_20d through exitlab.simulate (its hygiene and costs); B = A, but out at the 4th session's open when the first 3 highs never reached
    entry + 0.25 risk. Returns per trade: sid, signal_date, net_A, net_B."""
    pol = exitlab.Policy("hold_20d", "hold", 20)
    T = exitlab.simulate(entries, bars, feats, policies=[pol], random_draws=1)
    T = T[T["policy"] == "hold_20d"].drop_duplicates(["sid", "signal_date"])
    rk = feats.set_index(["sid", "date"])["liq_rank"]
    rk = rk[~rk.index.duplicated()]
    rows = []
    for r in T.itertuples():
        dates, o, h, l, c, v = bars[r.sid]
        i0 = int(np.searchsorted(dates, np.datetime64(pd.Timestamp(r.signal_date).date()), side="right"))
        entry = o[i0]
        risk = r.risk_ret * entry
        net_b = r.net_ret
        if r.hold_days > 3 and i0 + 3 < len(o) and np.max(h[i0:i0 + 3]) < entry + 0.25 * risk:
            rank = rk.get((r.sid, pd.Timestamp(r.signal_date)), float("nan"))          # the same spread estimate as A
            net_b = exitlab._row(r.sid, r.signal_date, dates[i0], "u3", entry, risk, 3, o[i0 + 3], "unproven3", entry, h[i0:i0 + 4], l[i0:i0 + 4], rank)["net_ret"]
        rows.append({"sid": r.sid, "signal_date": pd.Timestamp(r.signal_date), "net_A": r.net_ret, "net_B": net_b, "changed": net_b != r.net_ret})
    return pd.DataFrame(rows)


def _paired(D: pd.DataFrame) -> dict:
    d = D.assign(diff=D["net_B"] - D["net_A"])
    m = d.groupby(d["signal_date"].dt.to_period("M"))["diff"].mean()
    y = d["signal_date"].dt.year
    return {"dev": _stat(m[[p.year < SPLIT for p in m.index]]), "val": _stat(m[[p.year >= SPLIT for p in m.index]]),
            "extra": {"n": int(len(d)), "changed_share": float(d["changed"].mean()) if len(d) else None, "mean_A": float(d["net_A"].mean()),
                      "mean_B": float(d["net_B"].mean()), "events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())}}


def exit_results(P: pd.DataFrame, counts_only: bool = False) -> dict:
    pull = pd.read_parquet(paths.gold() / "studies" / "E02-PULL_trades.parquet", columns=["sid", "signal_date"]).drop_duplicates()
    pull["signal_date"] = pd.to_datetime(pull["signal_date"])
    pull = pull[pull["signal_date"] < CUT]
    ctl = _ctl_entries(P)
    b200 = _nifty_below200()
    ctl_dn = ctl[ctl["signal_date"].map(b200).fillna(False).astype(bool)]
    sets = {"X|PULL|unproven3_vs_hold20": pull, "X|CTL|unproven3_vs_hold20": ctl, "X|CTL_downtrend|unproven3_vs_hold20": ctl_dn}
    if counts_only:
        return {k: _counts(v["signal_date"]) for k, v in sets.items()}
    feats = P[["sid", "date", "atr14", "liq_rank"]]
    sids = set(pull["sid"]) | set(ctl["sid"])
    bars = exitlab.load_bars(sids)
    out = {}
    done_ctl = None
    for k, e in sets.items():
        if k == "X|CTL_downtrend|unproven3_vs_hold20" and done_ctl is not None:
            D = done_ctl[done_ctl["signal_date"].map(b200).fillna(False).astype(bool)]
        else:
            D = _overlay(e, bars, feats)
            if k == "X|CTL|unproven3_vs_hold20":
                done_ctl = D
        out[k] = _paired(D)
    return out


def check() -> dict:
    P = frame()
    return {**level_results(P, counts_only=True), **exit_results(P, counts_only=True)}


def run(rerun_reason: str | None = None) -> dict:
    s = spec()
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"RX1: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register("RX1", family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note="spec india/registrations/rx1_v1.json (written and committed before the run)", bar_families=s["bar"].get("bar_families"),
                            union_k=k, rerun_reason=rerun_reason)
    P = frame()
    res = {**level_results(P), **exit_results(P)}
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(r.get("extra", {})), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])),
                     "val": _clean(list(line["val"])), "extra": _clean(line["extra"])})
    out = {"study": "RX1", "registered_at": reg["at"], "k": k, "rows": rows}
    (paths.manifest_dir() / "lab5_rx1.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    print(json.dumps(_clean(check() if cmd == "check" else run()), indent=1, default=str)[:6000])
