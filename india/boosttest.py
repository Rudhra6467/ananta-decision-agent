"""One careful boosting test (Madhav, 20 Nov 2026 22:43 Toronto: "Let's do this in your order: sizing and risk first, then the variable map,
then one careful boosting test").

Research only: reads the unsealed years (to 2023-12-29), trades nothing and changes no rule. One run is the result: the settings below
were fixed before it, and nothing was tuned on the validation years.

The question: can gradient boosting (many small decision trees, each fixing the last one's errors) find combinations in the daily
features that tell which of the 250 most-traded stocks will do better than the others over the next 20 sessions, beyond what a straight
line or plain momentum already tells?

  the rows       every 20th session (no overlapping windows), each of the liquid 250 that day
  the target     the stock's return over the next 20 sessions minus the average of the liquid 250 over the same sessions
  the features   as of that day's close only: ret_5, ret_20, ret_60, atr_pct, rv20, vol_ratio20, dist_sma20, dist_sma50, dist_sma200,
                 pos20, deliv_pct, gap_pct, range_pct, liq_rank, breakout20, breakdown20, and the market's state (the Nifty 50's
                 distance from its 200-day average and its 20-session return) so the trees can find "this kind of stock in this market"
  the model      sklearn HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=200, seed 0),
                 fixed, not tuned
  the years      trained on 2007-2017 (rows whose 20 sessions end by 2017-12-31), judged once on 2018-2023; no training window ends after validation starts
  the rivals     LIN  a straight line on the same features (least squares)
                 MOM  plain momentum: rank by ret_60
                 SHUF the same boosting trained on targets shuffled within each day (what pure chance looks like)
  the scores     per day, the rank correlation between the model's order and what happened (the IC); its mean and t over the days;
                 and the top-15 book: the 15 names the model ranks highest, their average excess return over 20 sessions, after 0.6%
                 for the round trip

  USEFUL (fixed before the run): in 2018-2023 boosting's mean IC has t above 3, is higher than both LIN's and MOM's, SHUF's t is under 2,
  and the top-15 book earns more than 0 after costs. Otherwise NOT USEFUL. Either way the result is reported as it comes.

  python -m india.boosttest     writes reports/boosttest_<today>.json and .md under the data folder
"""
from __future__ import annotations

import datetime as dt
import json

import duckdb
import numpy as np
import pandas as pd

from india import paths

TRAIN = ("2007-01-01", "2017-12-31")
VAL = ("2018-01-01", "2023-12-29")
H, COST, TOP = 20, 0.006, 15
FEATS = ["ret_5", "ret_20", "ret_60", "atr_pct", "rv20", "vol_ratio20", "dist_sma20", "dist_sma50", "dist_sma200", "pos20", "deliv_pct",
         "gap_pct", "range_pct", "liq_rank", "breakout20", "breakdown20", "mkt_dist200", "mkt_ret20"]


def _rows() -> pd.DataFrame:
    d = paths.data_dir()
    c = duckdb.connect()
    fe = c.execute(f"""select * from read_parquet('{d}/gold/features/daily.parquet') where date >= '2006-06-01' and date <= '{VAL[1]}'""").df()
    fe["date"] = pd.to_datetime(fe["date"])
    ix = c.execute(f"""select date, close from read_parquet('{d}/silver/kite_index/day/day.parquet')
                       where index_name = 'NIFTY 50' and date <= '{VAL[1]}' order by date""").df()
    ix["date"] = pd.to_datetime(ix["date"])
    n = ix.set_index("date")["close"]
    mk = pd.DataFrame({"mkt_dist200": n / n.rolling(200).mean() - 1, "mkt_ret20": n.pct_change(20)})
    px = fe.pivot_table(index="date", columns="sid", values="c", aggfunc="last").sort_index()
    fwd = px.shift(-H) / px - 1                                     # the next 20 sessions, close to close
    days = px.index[(px.index >= TRAIN[0])][::H]
    out = []
    for t in days:
        f = fe[(fe.date == t) & (fe.liq_rank <= 250)].copy()
        if len(f) < 100:
            continue
        f["fwd"] = fwd.loc[t].reindex(f.sid).to_numpy()
        f = f.dropna(subset=["fwd"])
        f["target"] = f.fwd - f.fwd.mean()
        f["end"] = px.index[min(px.index.get_loc(t) + H, len(px.index) - 1)]
        out.append(f)
    r = pd.concat(out).join(mk, on="date")
    for b in ("breakout20", "breakdown20"):
        r[b] = r[b].astype(float)
    return r


def _ic(df: pd.DataFrame, col: str) -> dict:
    ics, tops = [], []
    for _, g in df.groupby("date"):
        if g[col].nunique() < 10:
            continue
        ics.append(g[col].rank().corr(g.target.rank()))
        tops.append(g.nlargest(TOP, col).target.mean() - COST)
    ics = np.array(ics)
    return {"days": len(ics), "mean_ic": round(float(ics.mean()), 4), "t": round(float(ics.mean() / ics.std() * np.sqrt(len(ics))), 2),
            "top15_excess_after_costs_pct": round(float(np.mean(tops)) * 100, 3), "top15_hit": round(float(np.mean(np.array(tops) > 0)), 2)}


def study() -> dict:
    from sklearn.ensemble import HistGradientBoostingRegressor

    r = _rows()
    tr = r[(r.date >= TRAIN[0]) & (r.end <= TRAIN[1])].copy()
    va = r[(r.date >= VAL[0]) & (r.end <= VAL[1])].copy()
    gap_ok = tr.end.max() < va.date.min()
    X, y = tr[FEATS].to_numpy(float), tr.target.to_numpy(float)

    def gbm():
        return HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_depth=3, min_samples_leaf=200, random_state=0)

    m = gbm().fit(X, y)
    va["GBM"] = m.predict(va[FEATS].to_numpy(float))
    tr["GBM"] = m.predict(X)
    Xl = np.column_stack([np.ones(len(tr)), np.nan_to_num(X)])
    b, *_ = np.linalg.lstsq(Xl, y, rcond=None)
    va["LIN"] = np.column_stack([np.ones(len(va)), np.nan_to_num(va[FEATS].to_numpy(float))]) @ b
    va["MOM"] = va.ret_60
    rng = np.random.default_rng(0)
    ys = tr.groupby("date").target.transform(lambda s: rng.permutation(s.to_numpy()))
    va["SHUF"] = gbm().fit(X, ys.to_numpy(float)).predict(va[FEATS].to_numpy(float))
    res = {k: _ic(va, k) for k in ("GBM", "LIN", "MOM", "SHUF")}
    g = res["GBM"]
    useful = (g["t"] > 3 and g["mean_ic"] > res["LIN"]["mean_ic"] and g["mean_ic"] > res["MOM"]["mean_ic"] and abs(res["SHUF"]["t"]) < 2
              and g["top15_excess_after_costs_pct"] > 0)
    from sklearn.inspection import permutation_importance

    pi = permutation_importance(m, va[FEATS].to_numpy(float), va.target.to_numpy(float), n_repeats=3, random_state=0)
    imp = sorted(zip(FEATS, pi.importances_mean), key=lambda x: -x[1])
    return {"made": dt.datetime.now().isoformat(timespec="seconds"), "train_rows": len(tr), "val_rows": len(va), "gap_ok": bool(gap_ok),
            "train_fit_GBM": _ic(tr, "GBM"), "validation": res, "verdict": "USEFUL" if useful else "NOT USEFUL",
            "importance_in_validation": [(k, round(float(v) * 1e4, 3)) for k, v in imp]}


def words(s: dict) -> str:
    L = [f"# One careful boosting test ({s['made'][:10]})", "", f"Trained on {s['train_rows']:,} rows (2007-2017), judged once on "
         f"{s['val_rows']:,} rows (2018-2023); the windows do not overlap ({s['gap_ok']}).", "",
         f"In training the model scored {s['train_fit_GBM']} (on the rows it learned from; not a result).", "",
         "| model | days | mean IC | t | top-15 excess after costs % | top-15 beat the average |", "|---|---|---|---|---|---|"]
    for k, v in s["validation"].items():
        L.append(f"| {k} | {v['days']} | {v['mean_ic']} | {v['t']} | {v['top15_excess_after_costs_pct']} | {v['top15_hit']} |")
    L += ["", f"**Verdict (rule fixed before the run): {s['verdict']}**", "", "What the model leaned on in 2018-2023 (drop in fit when the "
          "feature is shuffled, x 10,000):", ""] + [f"- {k}: {v}" for k, v in s["importance_in_validation"][:8]]
    return "\n".join(L) + "\n"


def main() -> None:
    s = study()
    d = paths.data_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    day = dt.date.today().isoformat()
    (d / f"boosttest_{day}.json").write_text(json.dumps(s, indent=1, default=str))
    (d / f"boosttest_{day}.md").write_text(words(s))
    print(words(s))


if __name__ == "__main__":
    main()
