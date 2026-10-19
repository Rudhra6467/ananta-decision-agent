"""Selection-bias controls (limitation 3, 19 Oct): with ~800 registered tests, some will look strong by chance. Four checks, on top of the
registry's family threshold:

  python -m india.selection fdr       every latest result in the ledger: two-sided p in dev and in validation, joint p = the larger of the two
                                      when the signs agree (both periods must show it), Benjamini-Hochberg across ALL tests at q 5% and 10%,
                                      and Bonferroni across all tests
  python -m india.selection perm      for every notable condition result (E04, E05, C01-C09, P01: VALIDATED / CONDITIONAL / OPPOSITE): the condition
                                      flag shuffled among trades (a) within the same quarter and (b) within the same signal day (the stricter null:
                                      flagged vs unflagged stocks on the same day, so market timing cannot produce it); 400 shuffles; the family
                                      version takes the largest |t| over all conditions of that study and exit each shuffle (corrects for having
                                      picked the best condition)
  python -m india.selection robust    the same results split into five period blocks (2000-05, 2006-11, 2012-17, 2018-20, 2021-23), liquidity halves
                                      (rank 1-100 vs 101-250) and with costs doubled
  python -m india.selection report    registrations/selection_bias.md, and a frozen survivor list (manifests/holdout_candidates.json, sha recorded)
                                      that fixes in advance exactly which hypotheses the one-time holdout run may test

Nothing here touches the holdout; nothing here registers a new hypothesis.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

from india import conditions, paths, registry, studies, studies2

N = NormalDist()
NPERM = 400
BLOCKS = [(2000, 2005), (2006, 2011), (2012, 2017), (2018, 2020), (2021, 2023)]
SPLIT = studies2.SPLIT
NOTABLE = ("VALIDATED", "CONDITIONAL", "OPPOSITE")
FEAT = ["sid", "date", "ret_20", "ret_60", "dist_sma20", "dist_sma50", "vol_ratio20", "deliv_pct", "rv20"]


def _p(t) -> float:
    return 1.0 if t is None or t != t else 2 * (1 - N.cdf(abs(t)))


def latest() -> pd.DataFrame:
    lat = {}
    for r in registry._rows():
        if r["kind"] == "result":
            lat[(r["study"], r["variant"])] = r
    rows = [{"study": r["study"], "family": r["family"], "variant": r["variant"], "verdict": r["verdict"], "z": r["z"], "dev_mean": r["dev"][0], "dev_t": r["dev"][1],
             "dev_n": r["dev"][2], "val_mean": r["val"][0], "val_t": r["val"][1], "val_n": r["val"][2]} for r in lat.values()]
    return pd.DataFrame(rows)


def fdr() -> pd.DataFrame:
    df = latest()
    df["p_dev"], df["p_val"] = df["dev_t"].map(_p), df["val_t"].map(_p)
    same = np.sign(df["dev_mean"].fillna(0)) == np.sign(df["val_mean"].fillna(0))
    df["p_joint"] = np.where(same, np.maximum(df["p_dev"], df["p_val"]), 1.0)
    m = len(df)
    order = np.argsort(df["p_joint"].values)
    ranked = df["p_joint"].values[order] * m / (np.arange(m) + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    df.loc[df.index[order], "q_bh"] = np.minimum(q, 1.0)
    df["p_bonf"] = np.minimum(df["p_joint"] * m, 1.0)
    df["bh05"], df["bh10"], df["bonf05"] = df["q_bh"] < 0.05, df["q_bh"] < 0.10, df["p_bonf"] < 0.05
    df.to_parquet(paths.gold() / "studies" / "selection_fdr.parquet")
    return df


# ----------------------------------------------------------------------------------------------- condition trades, rebuilt with the studies' own code
def _cond_trades(entry: str) -> pd.DataFrame:
    f = studies.load_features()
    ctx = conditions.context_table(f)
    mc = conditions.apply_market(ctx).reset_index()
    fx = f[FEAT].copy()
    sc = conditions.apply_stock(fx)
    fx = pd.concat([f[["sid", "date", "liq_rank"]], sc], axis=1)
    tr = pd.read_parquet(paths.gold() / "studies" / f"E02-{entry}_trades.parquet", columns=["sid", "signal_date", "policy", "net_ret", "cost_ret"])
    tr = tr[tr["policy"].isin(studies2.POLS) & (tr["signal_date"] >= "2000-01-01")]
    tr = tr.merge(fx, left_on=["sid", "signal_date"], right_on=["sid", "date"], how="left").drop(columns="date")
    tr = tr.merge(mc, left_on="signal_date", right_on="date", how="left").drop(columns="date")
    ind = studies2._indicators()
    tr = tr.merge(ind, left_on=["sid", "signal_date"], right_on=["sid", "date"], how="left").drop(columns="date")
    for c, (desc, ex, rule) in studies2.P01_CONDS.items():
        src = {"rsi_lt30": "rsi14", "rsi_gt70": "rsi14", "stoch_lt20": "stoch14", "wk_outside_up": "wk_outside_up"}[c]
        tr["cond_" + c] = rule(tr).astype(float).where(tr[src].notna())
    return tr


def _group_conds(study: str) -> list[str]:
    g = study.split("-")[0]
    if g == "P01":
        return list(studies2.P01_CONDS)
    return studies2.GROUPS[g][2]


def _tstat(q: np.ndarray, y: np.ndarray, on: np.ndarray, nq: int) -> float:
    """studies2._qdiff in arrays: per quarter mean(on) - mean(off), quarters with >= MIN_SIDE a side, t across quarters."""
    n_on = np.bincount(q, weights=on, minlength=nq)
    n_all = np.bincount(q, minlength=nq).astype(float)
    s_on = np.bincount(q, weights=y * on, minlength=nq)
    s_all = np.bincount(q, weights=y, minlength=nq)
    n_off = n_all - n_on
    ok = (n_on >= studies2.MIN_SIDE) & (n_off >= studies2.MIN_SIDE)
    if ok.sum() < 3:
        return float("nan")
    d = s_on[ok] / n_on[ok] - (s_all[ok] - s_on[ok]) / n_off[ok]
    se = d.std(ddof=1) / math.sqrt(len(d))
    return float(d.mean() / se) if se else float("nan")


def _shuffle(block: np.ndarray, rng) -> tuple[np.ndarray, np.ndarray]:
    s = np.argsort(block, kind="stable")
    r = np.argsort(block + rng.random(len(block)) * 0.999)
    return s, r


def perm(nperm: int = NPERM) -> pd.DataFrame:
    df = latest()
    df = df[df["verdict"].isin(NOTABLE) & df["study"].str.match(r"^(E04|E05|C0\d|P01)-")]
    out = []
    rng = np.random.default_rng(19)
    for entry in sorted({s.split("-", 1)[1] for s in df["study"]}):
        tr = _cond_trades(entry)
        for study in sorted(df.loc[df["study"].str.endswith("-" + entry), "study"].unique()):
            conds = [c for c in _group_conds(study) if "cond_" + c in tr.columns]
            tests = df[df["study"] == study]
            for pol in sorted({v.split("|")[1] for v in tests["variant"]}):
                for per, mask in (("dev", tr["signal_date"].dt.year < SPLIT), ("val", tr["signal_date"].dt.year >= SPLIT)):
                    x = tr[(tr["policy"] == pol) & mask]
                    qcode = x["signal_date"].dt.to_period("Q").astype(str)
                    q = pd.factorize(qcode)[0]
                    day = pd.factorize(x["signal_date"])[0].astype(float)
                    qb = q.astype(float)
                    y = x["net_ret"].to_numpy()
                    F = {c: x["cond_" + c].to_numpy() for c in conds}
                    obs = {}
                    for c in conds:
                        v = ~np.isnan(F[c])
                        obs[c] = _tstat(q[v], y[v], (F[c][v] > 0.5).astype(float), q.max() + 1)
                    null = {"quarter": {c: [] for c in conds}, "day": {c: [] for c in conds}}
                    fam = {"quarter": [], "day": []}
                    market = all(c in conditions.MARKET for c in conds)
                    di = day.astype(int)
                    if market:
                        # a market condition is one value per day: shuffle whole days within the quarter (all trades of a day move together);
                        # the within-day shuffle cannot apply (the flag does not vary inside a day) and is reported as not applicable
                        nd = di.max() + 1
                        dq = np.zeros(nd)
                        dq[di] = qb
                        Fd = {}
                        for c in conds:
                            Fd[c] = np.full(nd, np.nan)
                            Fd[c][di] = F[c]
                        s_d = np.argsort(dq, kind="stable")
                    for kind, block in (("quarter", qb), ("day", day)):
                        if market and kind == "day":
                            continue
                        s = np.argsort(block, kind="stable")
                        for _ in range(nperm):
                            if market:
                                r_d = np.argsort(dq + rng.random(len(dq)) * 0.999)
                                dmap = np.empty(len(dq), dtype=int)
                                dmap[s_d] = r_d
                            else:
                                r = np.argsort(block + rng.random(len(block)) * 0.999)
                            best = 0.0
                            for c in conds:
                                if market:
                                    fp = Fd[c][dmap[di]]
                                else:
                                    fp = np.empty_like(F[c])
                                    fp[s] = F[c][r]  # one shuffle for all conditions: their correlation is kept
                                v = ~np.isnan(fp)
                                t = _tstat(q[v], y[v], (fp[v] > 0.5).astype(float), q.max() + 1)
                                null[kind][c].append(t)
                                if t == t:
                                    best = max(best, abs(t))
                            fam[kind].append(best)
                    # Standardise each condition's null by its own centre and spread: the within-day shuffle keeps how many flagged trades
                    # each day has, so its null carries the market-timing part of the effect and is not centred at zero. z measures what is
                    # left beyond that; the family maximum of |z| over all conditions of the study corrects for picking the best condition.
                    stdz = {}
                    for kind in ("quarter", "day"):
                        if market and kind == "day":
                            continue
                        M = np.array([null[kind][c] for c in conds], dtype=float)  # conds x perms
                        mu, sd = np.nanmean(M, axis=1), np.nanstd(M, axis=1, ddof=1)
                        Z = (M - mu[:, None]) / sd[:, None]
                        stdz[kind] = (mu, sd, np.nanmax(np.abs(Z), axis=0))
                    for ci, c in enumerate(conds):
                        variant = f"{c}|{pol}"
                        if variant not in set(tests["variant"]):
                            continue
                        rec = {"study": study, "variant": variant, "period": per, "t_obs": obs[c], "level": "market (days shuffled)" if market else "stock (trades shuffled)"}
                        for kind in ("quarter", "day"):
                            if market and kind == "day":
                                rec.update({"p_day": None, "p_day_family": None, "null99_day": None, "null_centre_day": None, "z_day": None})
                                continue
                            nl = np.array([t for t in null[kind][c] if t == t])
                            mu, sd, fmax = stdz[kind]
                            z = (obs[c] - mu[ci]) / sd[ci] if obs[c] == obs[c] and sd[ci] > 0 else float("nan")
                            zn = (nl - mu[ci]) / sd[ci] if sd[ci] > 0 else nl * np.nan
                            rec[f"z_{kind}"] = float(z)
                            rec[f"null_centre_{kind}"] = float(mu[ci])
                            rec[f"p_{kind}"] = float(((np.abs(zn) >= abs(z)).sum() + 1) / (len(zn) + 1)) if len(zn) and z == z else None
                            rec[f"p_{kind}_family"] = float(((fmax >= abs(z)).sum() + 1) / (len(fmax) + 1)) if z == z else None
                            rec[f"null99_{kind}"] = float(np.quantile(np.abs(nl), 0.99)) if len(nl) else None
                        out.append(rec)
                        f = lambda v: "n/a" if v is None or v != v else f"{v:.3f}"
                        print(f"{study:9s} {variant:28s} {per} t {obs[c]:+.2f} | quarter z {f(rec['z_quarter'])} p {f(rec['p_quarter'])} fam {f(rec['p_quarter_family'])} "
                              f"| day centre {f(rec['null_centre_day'])} z {f(rec['z_day'])} p {f(rec['p_day'])} fam {f(rec['p_day_family'])}", flush=True)
        del tr
    res = pd.DataFrame(out)
    res.to_parquet(paths.gold() / "studies" / "selection_perm.parquet")
    return res


def robust() -> pd.DataFrame:
    df = latest()
    df = df[df["verdict"].isin(NOTABLE) & df["study"].str.match(r"^(E04|E05|C0\d|P01)-")]
    out = []
    for entry in sorted({s.split("-", 1)[1] for s in df["study"]}):
        tr = _cond_trades(entry)
        tr["y"] = tr["signal_date"].dt.year
        for r in df[df["study"].str.endswith("-" + entry)].itertuples():
            c, pol = r.variant.split("|")
            flag = "cond_" + c
            if flag not in tr.columns:
                continue
            x = tr[tr["policy"] == pol]
            rec = {"study": r.study, "variant": r.variant, "verdict": r.verdict, "dev_mean": r.dev_mean, "val_mean": r.val_mean}
            sign = np.sign(r.dev_mean)
            same = 0
            for a, b in BLOCKS:
                m, t, n, _ = studies2._qdiff(x[(x["y"] >= a) & (x["y"] <= b)], flag)
                rec[f"blk_{a}_{b}"] = m
                rec[f"blk_{a}_{b}_t"] = t
                same += int(m == m and np.sign(m) == sign)
            rec["blocks_same_sign"] = same
            for nm, lo, hi in (("top100", 1, 100), ("rank101_250", 101, 250)):
                for per, pm in (("dev", x["y"] < SPLIT), ("val", x["y"] >= SPLIT)):
                    m, t, n, _ = studies2._qdiff(x[pm & x["liq_rank"].between(lo, hi)], flag)
                    rec[f"{nm}_{per}"], rec[f"{nm}_{per}_t"] = m, t
            x2 = x.assign(net_ret=x["net_ret"] - x["cost_ret"])
            for per, pm in (("dev", x2["y"] < SPLIT), ("val", x2["y"] >= SPLIT)):
                m, t, n, _ = studies2._qdiff(x2[pm], flag)
                rec[f"cost2x_{per}"], rec[f"cost2x_{per}_t"] = m, t
            out.append(rec)
            print(f"{r.study:9s} {r.variant:28s} blocks same sign {same}/5 | top100 val {rec['top100_val']*100:+.2f}% (t {rec['top100_val_t']:+.1f}) "
                  f"101-250 val {rec['rank101_250_val']*100:+.2f}% (t {rec['rank101_250_val_t']:+.1f}) | 2x cost val {rec['cost2x_val']*100:+.2f}% (t {rec['cost2x_val_t']:+.1f})", flush=True)
        del tr
    res = pd.DataFrame(out)
    res.to_parquet(paths.gold() / "studies" / "selection_robust.parquet")
    return res


def report() -> dict:
    from pathlib import Path
    st = paths.gold() / "studies"
    f = fdr()
    pm = pd.read_parquet(st / "selection_perm.parquet") if (st / "selection_perm.parquet").exists() else pd.DataFrame()
    rb = pd.read_parquet(st / "selection_robust.parquet") if (st / "selection_robust.parquet").exists() else pd.DataFrame()
    m = len(f)
    notable = f[f["verdict"].isin(NOTABLE)].copy()
    L = ["# Selection bias: how many results survive having run ~800 tests", "",
         f"Generated by `python -m india.selection report`. HISTORICAL BACKTEST only (dev 2000-2017, validation 2018-2023; the 2024+ holdout is untouched).", "",
         f"- Tests in the ledger (latest result per study and variant): **{m}** across {f['family'].nunique()} families; registry verdicts: "
         + ", ".join(f"{k} {v}" for k, v in f["verdict"].value_counts().items()),
         f"- Joint p = the larger of the dev and validation two-sided p-values when both periods agree in sign (otherwise 1). "
         f"Benjamini-Hochberg across all {m}: **{int(f['bh05'].sum())}** at q < 5%, {int(f['bh10'].sum())} at q < 10%; Bonferroni across all {m}: {int(f['bonf05'].sum())}.",
         f"- Of the {len(notable)} notable registry verdicts (VALIDATED / CONDITIONAL / OPPOSITE), {int(notable['bh05'].sum())} pass BH 5% across the whole ledger.", ""]
    keep = []
    for r in notable.sort_values("q_bh").itertuples():
        pr = pm[(pm["study"] == r.study) & (pm["variant"] == r.variant)] if len(pm) else pd.DataFrame()
        rr = rb[(rb["study"] == r.study) & (rb["variant"] == r.variant)] if len(rb) else pd.DataFrame()
        checks = {"bh05": bool(r.bh05)}
        if len(pr):
            checks["perm_quarter_family"] = bool((pr["p_quarter_family"] < 0.05).all())
            if pr["p_day_family"].notna().all():  # stock conditions only; market conditions have no within-day variation
                checks["perm_day_family"] = bool((pr["p_day_family"] < 0.05).all())
        if len(rr):
            x = rr.iloc[0]
            sgn = np.sign(x["dev_mean"])
            checks["blocks_4of5"] = bool(x["blocks_same_sign"] >= 4)
            checks["both_halves"] = bool(all(np.sign(x[k]) == sgn for k in ("top100_dev", "top100_val", "rank101_250_dev", "rank101_250_val") if x[k] == x[k]))
            checks["cost2x"] = bool(np.sign(x["cost2x_val"]) == sgn and abs(x["cost2x_val_t"]) >= 1.65)
        kind = "full" if len(pr) and len(rr) else "fdr only (no trade-level re-test for this study type yet)"
        survived = all(checks.values())
        keep.append({"study": r.study, "variant": r.variant, "family": r.family, "verdict": r.verdict, "q_bh": float(r.q_bh), "dev_t": r.dev_t, "val_t": r.val_t,
                     "checks": checks, "tested": kind, "survives": survived})
    L += ["## Notable results, best first", "", "| study | variant | registry | dev t | val t | BH q | checks failed | tested | survives |", "|---|---|---|---|---|---|---|---|---|"]
    for k in keep:
        failed = [c for c, ok in k["checks"].items() if not ok]
        L.append(f"| {k['study']} | {k['variant']} | {k['verdict']} | {k['dev_t']:+.1f} | {k['val_t']:+.1f} | {k['q_bh']:.2g} | {', '.join(failed) or 'none'} | {k['tested']} | "
                 f"{'**yes**' if k['survives'] else 'no'} |")
    from india import lineage
    standin_roots = {s for v in lineage.STANDIN.values() for s in v}
    for k in keep:
        k["rests_on_standin"] = k["study"].split("-")[0] in standin_roots
    surv_all = [k for k in keep if k["survives"]]
    surv = [k for k in surv_all if not k["rests_on_standin"]]
    timing = [k for k in keep if k["checks"].get("perm_quarter_family") and k["checks"].get("perm_day_family") is False]
    if len(pm):
        L += ["", "## What the shuffles say: timing, not selection", "",
              "The within-quarter shuffle asks whether flagged trades beat unflagged ones by more than chance. The within-day shuffle asks the stricter "
              "question: on the same day, did flagged stocks beat unflagged ones? It keeps how many flagged trades each day had, so its null carries "
              "the market-timing part of the effect (`day centre`, in t units); `z day` is what is left beyond timing.", "",
              "| study | variant | period | observed t | quarter-shuffle family p | day-shuffle centre | z beyond timing | family p beyond timing |", "|---|---|---|---|---|---|---|---|"]
        hp = pm[pm["level"].str.startswith("stock") & pm["variant"].str.endswith("hold_20d")]
        for r in hp.itertuples():
            L.append(f"| {r.study} | {r.variant} | {r.period} | {r.t_obs:+.2f} | {r.p_quarter_family:.3f} | {r.null_centre_day:+.2f} | {r.z_day:+.2f} | {r.p_day_family:.3f} |")
        L += ["", f"**{len(timing)} notable stock-level results pass the quarter shuffle but fail the within-day shuffle**: the E04 saturation and P01 RSI "
              "families. The flagged trades did earn what the registry says, but because of the days they fall on (oversold stocks cluster after "
              "broad sell-offs that rebound; extended stocks cluster late in rallies that fade), not because the flagged stocks beat other stocks "
              "on the same day. Consequences: (1) as stock-selection filters inside a day they add nothing measurable; (2) the effect may still be "
              "usable as a market-timing signal, which is a different hypothesis (an aggregate share of oversold or extended stocks, tested at the "
              "market level) and must be registered and tested as such; (3) the REV paper campaign (RSI under 30) is, by this evidence, a "
              "market-timing campaign and is read that way.", ""]
    L += ["", f"## Survivors: {len(surv)} (plus {len(surv_all) - len(surv)} that rest on stand-in data)", "",
          "A survivor passed every check it was given: BH 5% across the whole ledger; where trade-level re-tests exist, the family-wise shuffle null "
          "within quarters and within days (largest |t| over all conditions of that study each shuffle), the same sign in at least 4 of 5 period blocks, "
          "the same sign in both liquidity halves, and still significant with costs doubled. Survivors with 'fdr only' have not had the trade-level "
          "checks yet and are listed as such.", ""]
    L += [f"- {k['study']} {k['variant']} ({k['verdict']}; {k['tested']})" for k in surv] + [""]
    if len(surv_all) > len(surv):
        L += ["Not holdout candidates yet, because they rest on a stand-in for missing data (registrations/missing_inputs.md): "
              + "; ".join(f"{k['study']} {k['variant']}" for k in surv_all if k["rests_on_standin"]) + ". They become candidates only after the stand-in is "
              "replaced (F05: R01 calibration on recorded expiry days).", ""]
    L += ["Market-level survivors (E08 Nifty above its 50-day average, C07 small caps leading, C09 rupee) rest on few independent regimes "
          "(see the E08 limitation); their quarter count overstates the number of independent observations.", ""]
    cand = {"frozen_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "ledger_tests": m, "candidates": [{x: k[x] for x in ("study", "variant", "verdict", "tested")} for k in surv]}
    blob = json.dumps(cand["candidates"], sort_keys=True).encode()
    cand["sha256"] = hashlib.sha256(blob).hexdigest()
    (paths.manifest_dir() / "holdout_candidates.json").write_text(json.dumps(cand, indent=1, default=str))
    L += ["## Holdout protocol", "",
          f"The survivor list is frozen in manifests/holdout_candidates.json (sha256 {cand['sha256'][:16]}..., {len(surv)} candidates). The holdout (2024 onward) "
          "is scored once, for exactly these candidates, with their registered rules and the same costs; the threshold there is Bonferroni over the "
          "candidate count. A result that does not hold on the holdout is dropped, not re-tuned. New hypotheses added later get their own frozen list.", ""]
    Path(__file__).resolve().parent.joinpath("registrations", "selection_bias.md").write_text("\n".join(L) + "\n")
    return {"tests": m, "bh05": int(f["bh05"].sum()), "notable": len(notable), "survivors": len(surv), "sha": cand["sha256"][:16]}


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "fdr":
        d = fdr()
        print(f"{len(d)} tests; BH5 {int(d['bh05'].sum())}; BH10 {int(d['bh10'].sum())}; Bonferroni {int(d['bonf05'].sum())}")
        print(d[d["verdict"].isin(NOTABLE)].sort_values("q_bh")[["study", "variant", "verdict", "dev_t", "val_t", "q_bh", "bh05"]].head(60).to_string(index=False))
    elif cmd == "perm":
        perm(int(sys.argv[2]) if len(sys.argv) > 2 else NPERM)
    elif cmd == "robust":
        robust()
    else:
        print(json.dumps(report(), indent=1))
