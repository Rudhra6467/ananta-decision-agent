"""Cut-rule study on history (Madhav, 14 Nov 2026 22:17 Toronto, after the managed book's 2 Nov cuts went 0 of 10: "All these need to
addressed right, and your recommendations sound good. Let's set it up.").

Research only: reads the unsealed years (to 2023-12-29) and changes no rule. A rule change goes through scripts/lock_door.py change with
Madhav's own yes, after he has seen this study's result.

Three questions, each answered in a development period (2007-2017) and a validation period (2018-2023); a finding counts only when
both periods agree.

  A  Which cut signal is right more often? A "cut" is right when the stock then does WORSE than the average liquid stock over the
     next 5 and 20 sessions (the market's own move taken out). Variants, all counted (nothing else was tried):
       V1  today's rule: allocator.rate_holding grades the holding D (REDUCE), run on the real code, holding neutral in size and result
       V2a V1, and the stock is also in the weakest third of the liquid 250 over 60 sessions (weak against the market, not only weak)
       V2b weakest fifth of the liquid 250 over 60 sessions and under its own 200-day average, whatever the market does
  B  Crowded days. When many holdings are flagged at once (the market fell, not the stocks), are those cuts worse? This is the case for
     a weekly cap on cuts.
  C  Idle cash. What did the Nifty 500 do over the next 20 and 60 sessions when the Nifty 50 was above both its 50- and 200-day
     averages, against the other states? This is the case for parking freed cash in the index in an uptrend.

  python -m india.cutstudy            writes reports/cutstudy_<today>.json and .md under the data folder
"""
from __future__ import annotations

import datetime as dt
import json
import math

import duckdb
import numpy as np
import pandas as pd

from india import allocator, paths

DEV = ("2007-01-01", "2017-12-31")
VAL = ("2018-01-01", "2023-12-29")
VARIANTS = ("V1", "V2a", "V2b")
TRIED = {"V1": "today's grade D (REDUCE), the real allocator code", "V2a": "V1 and weakest third over 60 sessions against the liquid 250",
         "V2b": "weakest fifth over 60 sessions and under its own 200-day, any market"}


def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = paths.data_dir()
    c = duckdb.connect()
    px = c.execute(f"""
        with liq as (select distinct sid from read_parquet('{d}/gold/universe/u_liq_in.parquet') where top250 and date >= '2006-01-01')
        select b.date, b.sid, b.c from read_parquet('{d}/gold/bars/adj_daily.parquet') b join liq using (sid)
        where b.date >= '2005-01-01' and b.date <= '{VAL[1]}' order by b.sid, b.date""").df()
    fe = c.execute(f"""select date, sid, symbol, liq_rank, atr_pct from read_parquet('{d}/gold/features/daily.parquet')
                       where date >= '2006-06-01' and date <= '{VAL[1]}' and liq_rank <= 250""").df()
    ix = c.execute(f"""select date, index_name, close from read_parquet('{d}/silver/kite_index/day/day.parquet')
                       where index_name in ('NIFTY 50', 'NIFTY 500') and date <= '{VAL[1]}' order by date""").df()
    px["date"], fe["date"], ix["date"] = pd.to_datetime(px["date"]), pd.to_datetime(fe["date"]), pd.to_datetime(ix["date"])
    g = px.groupby("sid")["c"]
    px["sma20"] = g.transform(lambda s: s.rolling(20).mean())
    px["sma200"] = g.transform(lambda s: s.rolling(200).mean())
    delta = g.diff()
    up, dn = delta.clip(lower=0), -delta.clip(upper=0)
    au = up.groupby(px["sid"]).transform(lambda s: s.ewm(alpha=1 / 14, adjust=False).mean())
    ad = dn.groupby(px["sid"]).transform(lambda s: s.ewm(alpha=1 / 14, adjust=False).mean())
    px["rsi14"] = np.where(ad > 0, 100 - 100 / (1 + au / ad.replace(0, np.nan)), 100.0)
    px["ret_60"] = g.transform(lambda s: s / s.shift(60) - 1)
    for h in (5, 20):
        px[f"fwd_{h}"] = g.transform(lambda s, h=h: s.shift(-h) / s - 1)
    df = px.merge(fe, on=["date", "sid"], how="inner").dropna(subset=["sma200", "ret_60", "fwd_20"])
    return df, ix


def _regimes(ix: pd.DataFrame) -> pd.DataFrame:
    n50 = ix[ix["index_name"] == "NIFTY 50"].set_index("date")["close"].sort_index()
    n500 = ix[ix["index_name"] == "NIFTY 500"].set_index("date")["close"].sort_index()
    r = pd.DataFrame({"n50": n50, "sma50": n50.rolling(50).mean(), "sma200": n50.rolling(200).mean()})
    r["trend"] = np.where((r["n50"] > r["sma50"]) & (r["n50"] > r["sma200"]), "above_both",
                          np.where((r["n50"] < r["sma50"]) & (r["n50"] < r["sma200"]), "below_both", "mixed"))
    r = r.join(n500.rename("n500"), how="left")
    for h in (20, 60):
        r[f"n500_fwd_{h}"] = r["n500"].shift(-h) / r["n500"] - 1
    r["n500_min_20"] = r["n500"][::-1].rolling(20, min_periods=1).min()[::-1].shift(-1) / r["n500"] - 1
    return r.dropna(subset=["sma200"])


def _flags(df: pd.DataFrame, reg: pd.DataFrame) -> pd.DataFrame:
    """Weekly (each week's last session): every liquid-250 stock, its grade by the real code, the three flags and its forward results."""
    df = df.merge(reg[["trend"]], left_on="date", right_index=True, how="inner")
    last_of_week = df.groupby(df["date"].dt.to_period("W"))["date"].transform("max")
    w = df[df["date"] == last_of_week].copy()
    rule = allocator.rule()
    grades = []
    for r in w.itertuples(index=False):
        qty = 10000 / r.c if r.c else 0
        h = {"tradingsymbol": r.symbol, "last_price": r.c, "average_price": r.c, "quantity": qty, "pnl": 0}
        row = {"dist_sma20": r.c / r.sma20 - 1, "dist_sma200": r.c / r.sma200 - 1, "rsi14": r.rsi14, "atr_pct": r.atr_pct, "liq_rank": r.liq_rank}
        grades.append(allocator.rate_holding(h, 0.08, row, r.trend, rule)["action"])
    w["action"] = grades
    w["rel60_rank"] = w.groupby("date")["ret_60"].rank(pct=True)
    for h in (5, 20):
        w[f"rel_{h}"] = w[f"fwd_{h}"] - w.groupby("date")[f"fwd_{h}"].transform("mean")
    w["V1"] = w["action"] == "REDUCE"
    w["V2a"] = w["V1"] & (w["rel60_rank"] <= 1 / 3)
    w["V2b"] = (w["rel60_rank"] <= 0.2) & (w["c"] < w["sma200"])
    w["crowd_v1"] = w.groupby("date")["V1"].transform("mean")
    return w


def _summ(x: pd.DataFrame) -> dict:
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "weeks": int(x["date"].nunique()),
            "right_5_pct": round(100 * float((x["rel_5"] < 0).mean()), 1), "right_20_pct": round(100 * float((x["rel_20"] < 0).mean()), 1),
            "rel_5_mean_pct": round(100 * float(x["rel_5"].mean()), 2), "rel_20_mean_pct": round(100 * float(x["rel_20"].mean()), 2),
            "raw_20_mean_pct": round(100 * float(x["fwd_20"].mean()), 2)}


def _period(x: pd.DataFrame, p: tuple) -> pd.DataFrame:
    return x[(x["date"] >= pd.Timestamp(p[0])) & (x["date"] <= pd.Timestamp(p[1]))]


def study() -> dict:
    df, ix = _load()
    reg = _regimes(ix)
    w = _flags(df, reg)
    out: dict = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "research_only": True, "tried": TRIED,
                 "periods": {"dev": DEV, "val": VAL}, "universe": "liquid 250, each week's last session", "A": {}, "B": {}, "C": {}}
    for name, p in (("dev", DEV), ("val", VAL)):
        x = _period(w, p)
        out["A"][name] = {"all_stocks": _summ(x), **{v: _summ(x[x[v]]) for v in VARIANTS},
                          "by_market": {t: {v: _summ(x[x[v] & (x["trend"] == t)]) for v in VARIANTS} for t in ("above_both", "mixed", "below_both")}}
        f = x[x["V1"]].copy()
        cuts = pd.qcut(f["crowd_v1"].rank(method="first"), 5, labels=["least crowded", "2", "3", "4", "most crowded"])
        out["B"][name] = {"V1_by_crowding": {str(k): {**_summ(g), "flagged_share_pct": round(100 * float(g["crowd_v1"].mean()), 1)} for k, g in f.groupby(cuts, observed=True)}}
        # a weekly cap of 3 against the whole liquid 250 is not the book's cap; what the book can learn is whether crowded-week cuts are worse
        r = reg[(reg.index >= pd.Timestamp(p[0])) & (reg.index <= pd.Timestamp(p[1]))].dropna(subset=["n500_fwd_60"])
        out["C"][name] = {t: {"sessions": int(len(g)), "share_pct": round(100 * len(g) / len(r), 1),
                              "n500_fwd_20_mean_pct": round(100 * float(g["n500_fwd_20"].mean()), 2), "n500_fwd_20_up_pct": round(100 * float((g["n500_fwd_20"] > 0).mean()), 1),
                              "n500_fwd_60_mean_pct": round(100 * float(g["n500_fwd_60"].mean()), 2),
                              "n500_worst_dip_20_p05_pct": round(100 * float(g["n500_min_20"].quantile(0.05)), 2)}
                          for t, g in r.groupby("trend")}
    return out


def words(s: dict) -> str:
    L = ["# Cut-rule study on history (research only, no rule changed)", "",
         f"Built {s['built_at'][:16]} UTC. Liquid 250 each week; development {DEV[0][:4]}-{DEV[1][:4]}, validation {VAL[0][:4]}-{VAL[1][:4]} (the sealed years are not read).",
         "A cut is **right** when the stock then does worse than the average liquid stock. 50% is a coin toss.", "",
         "## A. Which cut signal is right more often", "", "| signal | period | cuts | right after 5 | right after 20 | vs average after 20 |", "|---|---|---|---|---|---|"]
    for v in ("all_stocks",) + VARIANTS:
        for p in ("dev", "val"):
            r = s["A"][p][v]
            L.append(f"| {TRIED.get(v, 'every stock (baseline)')} | {p} | {r['n']:,} | {r.get('right_5_pct', '-')}% | {r.get('right_20_pct', '-')}% | {r.get('rel_20_mean_pct', '-')}% |")
    L += ["", "By market state (right after 20 sessions):", "", "| signal | period | uptrend | mixed | downtrend |", "|---|---|---|---|---|"]
    for v in VARIANTS:
        for p in ("dev", "val"):
            b = s["A"][p]["by_market"]
            L.append(f"| {v} | {p} | " + " | ".join(f"{b[t][v].get('right_20_pct', '-')}% (n {b[t][v]['n']:,})" for t in ("above_both", "mixed", "below_both")) + " |")
    L += ["", "## B. Cuts in crowded weeks (today's rule)", "", "| crowding | period | share flagged | right after 20 | vs average after 20 | raw after 20 |", "|---|---|---|---|---|---|"]
    for p in ("dev", "val"):
        for k, r in s["B"][p]["V1_by_crowding"].items():
            L.append(f"| {k} | {p} | {r['flagged_share_pct']}% | {r.get('right_20_pct', '-')}% | {r.get('rel_20_mean_pct', '-')}% | {r.get('raw_20_mean_pct', '-')}% |")
    L += ["", "## C. Cash against the Nifty 500, by market state", "", "| state | period | time in state | next 20 sessions | up after 20 | next 60 | bad dip (1 in 20) |", "|---|---|---|---|---|---|---|"]
    for p in ("dev", "val"):
        for t, r in s["C"][p].items():
            L.append(f"| {t} | {p} | {r['share_pct']}% | {r['n500_fwd_20_mean_pct']}% | {r['n500_fwd_20_up_pct']}% | {r['n500_fwd_60_mean_pct']}% | {r['n500_worst_dip_20_p05_pct']}% |")
    L += ["", "Everything tried is listed in A; nothing else was run."]
    return "\n".join(L) + "\n"


def main() -> None:
    s = study()
    d = paths.data_dir() / "reports"
    day = dt.date.today().isoformat()
    (d / f"cutstudy_{day}.json").write_text(json.dumps(s, indent=1, default=lambda o: None if isinstance(o, float) and math.isnan(o) else str(o)))
    (d / f"cutstudy_{day}.md").write_text(words(s))
    print(words(s))


if __name__ == "__main__":
    main()
