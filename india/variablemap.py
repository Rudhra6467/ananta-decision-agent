"""The variable map: what moves Indian stocks, and how much (Madhav, 20 Nov 2026 22:39 Toronto: "Can we find the most effective variables
of the market. Or see how many variables are influencing the market or a stock or a sector"; 22:43: "Let's do this in your order").

Research only: reads the unsealed years (to 2023-12-29), predicts nothing and changes no rule. It describes; it is not a trading signal.
Everything is shown for a development period (2007-2017, macro part from 2007) and a validation period (2018-2023). Everything tried is
listed here; nothing else was tried.

  A  How many forces. For each year, the daily returns of the liquid 250 (names with prices on 90% of that year's sessions), turned into
     their principal components (PCA on the correlation matrix): the share of all movement the first force explains, the first three,
     and how many forces it takes to explain half and four fifths of it.
  B  What moves each stock and each sector. For each liquid stock with an industry label, its daily return regressed on, in steps:
       1 the market            the Nifty 50's return the same day
       2 + its sector          the equal-weight return of the other liquid names in its industry the same day, with the market taken out
       3 + the world           the day before's (US markets close after India's): Brent oil % change, the rupee per dollar % change,
                               the broad dollar index % change, the US 10-year yield change, the Nasdaq's return, the US fear gauge
                               (VIX) change; and the same day's India VIX change
     Shown: how much of a stock's daily movement each step explains (R squared, the median over stocks and per industry), and per
     industry the outside forces that matter: a force is listed for an industry when its median t across the industry's stocks is beyond
     3 in both periods with the same sign.

  Caveats, said here once: the industry labels are today's (a stock's industry in 2009 may have differed; delisted names have no label and
  sit out of part B); the macro series are FRED's (the rupee rate is New York's noon rate, taken the day before to be safe); gold is not
  in the data.

  python -m india.variablemap     writes reports/variablemap_<today>.json and .md under the data folder
"""
from __future__ import annotations

import datetime as dt
import json

import duckdb
import numpy as np
import pandas as pd

from india import paths

DEV = ("2007-01-01", "2017-12-31")
VAL = ("2018-01-01", "2023-12-29")
WORLD = {"DCOILBRENTEU": ("oil", "pct"), "DEXINUS": ("rupee per dollar", "pct"), "DTWEXBGS": ("dollar index", "pct"),
         "DGS10": ("US 10-year yield", "diff"), "NASDAQCOM": ("Nasdaq", "pct"), "VIXCLS": ("US fear gauge", "diff")}


def _load():
    d = paths.data_dir()
    c = duckdb.connect()
    fe = c.execute(f"""select date, sid, symbol, ret_1, liq_rank from read_parquet('{d}/gold/features/daily.parquet')
                       where date >= '2006-12-01' and date <= '{VAL[1]}' and liq_rank <= 250""").df()
    ix = c.execute(f"""select date, close from read_parquet('{d}/silver/kite_index/day/day.parquet')
                       where index_name = 'NIFTY 50' and date <= '{VAL[1]}' order by date""").df()
    ma = c.execute(f"select date, series, value from read_parquet('{d}/silver/macro/macro.parquet') where date <= '{VAL[1]}'").df()
    lab = c.execute(f"select symbol, industry from read_parquet('{d}/silver/reference/industry_labels.parquet')").df()
    vix = None
    try:
        vix = c.execute(f"""select date, close from read_parquet('{d}/silver/kite_index/day/day.parquet')
                            where index_name = 'INDIA VIX' and date <= '{VAL[1]}' order by date""").df()
    except Exception:  # noqa: BLE001
        pass
    for x in (fe, ix, ma) + ((vix,) if vix is not None else ()):
        x["date"] = pd.to_datetime(x["date"])
    return fe, ix, ma, lab, vix


def forces(fe: pd.DataFrame) -> list[dict]:
    out = []
    R = fe.pivot_table(index="date", columns="sid", values="ret_1", aggfunc="last")
    for y in range(2007, 2024):
        r = R[(R.index >= f"{y}-01-01") & (R.index <= f"{y}-12-31")]
        r = r.loc[:, r.notna().mean() >= 0.9]
        r = r.loc[:, fe[(fe.date.dt.year == y)].groupby("sid").liq_rank.min().reindex(r.columns).le(250)]
        if r.shape[1] < 50:
            continue
        z = ((r - r.mean()) / r.std()).fillna(0).clip(-8, 8)
        ev = np.sort(np.linalg.eigvalsh(np.corrcoef(z.T.to_numpy())))[::-1]
        share = ev / ev.sum()
        cum = np.cumsum(share)
        out.append({"year": y, "stocks": int(r.shape[1]), "first": round(float(share[0]) * 100, 1), "first3": round(float(cum[2]) * 100, 1),
                    "for_half": int(np.searchsorted(cum, 0.5) + 1), "for_four_fifths": int(np.searchsorted(cum, 0.8) + 1)})
    return out


def _world(ma: pd.DataFrame, vix, dates: pd.DatetimeIndex) -> pd.DataFrame:
    w = ma.pivot_table(index="date", columns="series", values="value", aggfunc="last").sort_index()
    cols = {}
    for k, (name, how) in WORLD.items():
        if k not in w:
            continue
        s = w[k].dropna()
        ch = s.pct_change() if how == "pct" else s.diff()
        cols[name] = ch.reindex(dates, method="ffill").shift(1)        # the day before, as of India's session
    out = pd.DataFrame(cols, index=dates)
    if vix is not None and len(vix):
        out["India VIX"] = vix.set_index("date")["close"].pct_change().reindex(dates)
    return out


def _ols(y: np.ndarray, X: np.ndarray) -> tuple[float, np.ndarray]:
    X = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    r2 = 1 - e.var() / y.var() if y.var() > 0 else np.nan
    dof = max(len(y) - X.shape[1], 1)
    s2 = (e @ e) / dof
    try:
        se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    except np.linalg.LinAlgError:
        se = np.full(X.shape[1], np.nan)
    return float(r2), (b / se)[1:]


def drivers(fe, ix, ma, lab, vix, p: tuple) -> dict:
    f = fe[(fe.date >= p[0]) & (fe.date <= p[1])].merge(lab, on="symbol", how="inner")
    R = f.pivot_table(index="date", columns="sid", values="ret_1", aggfunc="last")
    ind = f.groupby("sid").industry.last()
    m = ix.set_index("date")["close"].pct_change().reindex(R.index)
    W = _world(ma, vix, R.index)
    names = list(W.columns)
    rows = []
    for sid in R.columns:
        y = R[sid]
        peers = [s for s in ind.index[ind == ind[sid]] if s != sid and s in R.columns]
        if len(peers) < 3:
            continue
        sec = R[peers].mean(axis=1)
        sec_x = sec - m * (np.nansum(sec * m) / np.nansum(m * m))     # the sector with the market taken out
        df = pd.concat([y.rename("y"), m.rename("m"), sec_x.rename("s"), W], axis=1).dropna()
        if len(df) < 250:
            continue
        r1, _ = _ols(df.y.to_numpy(), df[["m"]].to_numpy())
        r2, _ = _ols(df.y.to_numpy(), df[["m", "s"]].to_numpy())
        r3, t3 = _ols(df.y.to_numpy(), df[["m", "s"] + names].to_numpy())
        rows.append({"sid": sid, "industry": ind[sid], "r2_market": r1, "r2_sector": r2, "r2_world": r3,
                     **{f"t_{n}": float(t) for n, t in zip(names, t3[2:])}})
    d = pd.DataFrame(rows)
    by = d.groupby("industry").median(numeric_only=True)
    return {"stocks": len(d), "median": {k: round(float(d[k].median()) * 100, 1) for k in ("r2_market", "r2_sector", "r2_world")},
            "by_industry": {i: {"stocks": int((d.industry == i).sum()),
                                "market": round(float(r.r2_market) * 100, 1), "with_sector": round(float(r.r2_sector) * 100, 1),
                                "with_world": round(float(r.r2_world) * 100, 1),
                                "t": {n: round(float(r[f"t_{n}"]), 2) for n in names}} for i, r in by.iterrows()},
            "forces": names}


def study() -> dict:
    fe, ix, ma, lab, vix = _load()
    out = {"made": dt.datetime.now().isoformat(timespec="seconds"), "periods": {"dev": DEV, "val": VAL}, "how_many": forces(fe),
           "drivers": {p: drivers(fe, ix, ma, lab, vix, r) for p, r in (("dev", DEV), ("val", VAL))}}
    keep = {}
    for i, v in out["drivers"]["dev"]["by_industry"].items():
        w = out["drivers"]["val"]["by_industry"].get(i)
        if not w:
            continue
        both = [n for n in v["t"] if abs(v["t"][n]) > 3 and abs(w["t"].get(n, 0)) > 3 and np.sign(v["t"][n]) == np.sign(w["t"][n])]
        keep[i] = {n: ("up with it" if v["t"][n] > 0 else "down with it") for n in both}
    out["outside_forces_that_hold"] = keep
    return out


def words(s: dict) -> str:
    L = [f"# The variable map ({s['made'][:10]})", "", "## A. How many forces move the liquid 250", "",
         "| year | stocks | first force % | first three % | forces for half | forces for four fifths |", "|---|---|---|---|---|---|"]
    L += [f"| {r['year']} | {r['stocks']} | {r['first']} | {r['first3']} | {r['for_half']} | {r['for_four_fifths']} |" for r in s["how_many"]]
    for p in ("dev", "val"):
        d = s["drivers"][p]
        L += ["", f"## B. What moves each stock ({p}: {d['stocks']} stocks)", "",
              f"Median share of a stock's daily movement explained: market {d['median']['r2_market']}%, with its sector "
              f"{d['median']['r2_sector']}%, with the world {d['median']['r2_world']}%.", "",
              "| industry | stocks | market % | + sector % | + world % |", "|---|---|---|---|---|"]
        L += [f"| {i} | {v['stocks']} | {v['market']} | {v['with_sector']} | {v['with_world']} |"
              for i, v in sorted(d["by_industry"].items(), key=lambda x: -x[1]["with_world"])]
    L += ["", "## Outside forces that hold in both periods (median t beyond 3, same sign)", ""]
    L += [f"- {i}: " + (", ".join(f"{n} ({how})" for n, how in v.items()) or "none") for i, v in sorted(s["outside_forces_that_hold"].items())]
    return "\n".join(L) + "\n"


def main() -> None:
    s = study()
    d = paths.data_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    day = dt.date.today().isoformat()
    (d / f"variablemap_{day}.json").write_text(json.dumps(s, indent=1, default=str))
    (d / f"variablemap_{day}.md").write_text(words(s))
    print(words(s))


if __name__ == "__main__":
    main()
