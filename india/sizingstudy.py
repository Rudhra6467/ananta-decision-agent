"""Position sizing and risk study on history (Madhav, 20 Nov 2026 22:43 Toronto: "Let's do this in your order: sizing and risk first, then
the variable map, then one careful boosting test").

Research only: reads the unsealed years (to 2023-12-29) and changes no rule. A rule change goes through scripts/lock_door.py change with
Madhav's own yes, after he has seen this study's result.

The question: with the stock picks held fixed, does HOW MUCH goes into each name, and WHEN a name is cut by a stop, make the book safer
without giving up its return? Every result is shown in a development period (2007-2017) and a validation period (2018-2023); a method
counts as better only when both periods agree (rule below). Everything tried is listed here; nothing else was tried.

  the book       15 names from the 250 most-traded stocks, bought at a close, held 20 sessions, then picked again (one window)
  the picks      R  random: 100 random books (seeds 0-99), so sizing is judged apart from picking skill
                 M  momentum: the 15 strongest over 60 sessions among names above their own 200-day average (one book, no seed)
  the sizing     EQ  equal rupees in each name (today's managed book: each replacement gets the rupees of the stock it replaced)
                 IV  inverse volatility: each name's weight in proportion to 1 / its 14-day ATR as a share of price
                 FR  fixed risk: each name risks 0.5% of the book if it fell 2 ATRs; weight = 0.5% / (2 x ATR%), capped at 15% a
                     name, the rest in cash when the names are wild (a typical liquid name, ATR 3.6% of price, gets about 1/15).
                     Code checks with 2 seeds, before the full run: ATR% is stored as a fraction (0.036), not in percent, so the first
                     draft's FR equalled EQ and its 2-ATR stop sat a hair under the entry; both read the fraction now, and the risk was
                     set to 0.5% so a typical name gets its 1/15. The full run below is the only run counted
  the stops      none, S7 (a fixed 7% stop, as the managed book has), SA (2 ATRs under the entry); a stopped name's money waits in cash
                 until the next window. Stops are read on closes (a gap through the stop is taken at that close, not at the stop)
  the brake      DD  on top of EQ with no stop: half the money in cash while the book is 10% or more under its peak, back in full at a new
                 peak (today's India brake is a pause at 22%)
  costs          0.30% of each rupee traded (a labelled estimate: brokerage, STT and spread together), charged on every buy and sell

  Measured per period: yearly return, yearly swing (volatility), the deepest fall from a peak (max drawdown), the worst 20 sessions, and
  return per unit of drawdown. For R: the median of the 100 books and the share of books in which the method beat EQ.

  BETTER (fixed before the run): against EQ with no stop, a method is better when in BOTH periods, for BOTH R (median) and M, its max
  drawdown is at least 15% smaller (relative) AND its return per unit of drawdown is higher. SAFER-BUT-COSTLY: drawdown 15% smaller in
  both, return per drawdown not higher. Otherwise NO BETTER.

  For scale, the Nifty 50 held all along (no costs) is shown beside each period. Every window sells and buys all 15 names, so costs
  take about 7% a year from every method alike; compare methods with each other, not with the index.

  Kelly sizing is not tried: Kelly needs a measured edge per pick, and the managed book has none yet (14 sessions); with no edge, Kelly
  says bet nothing. It comes back when the book has 60 graded sessions.

  python -m india.sizingstudy     writes reports/sizingstudy_<today>.json and .md under the data folder
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
N_NAMES, HOLD, SEEDS, COST = 15, 20, 100, 0.003
SIZINGS = ("EQ", "IV", "FR")
STOPS = ("none", "S7", "SA")


def _load():
    d = paths.data_dir()
    c = duckdb.connect()
    fe = c.execute(f"""select date, sid, c, atr_pct, ret_60, dist_sma200, liq_rank from read_parquet('{d}/gold/features/daily.parquet')
                       where date >= '2006-06-01' and date <= '{VAL[1]}'""").df()
    fe["date"] = pd.to_datetime(fe["date"])
    px = fe.pivot_table(index="date", columns="sid", values="c", aggfunc="last").sort_index()
    return fe, px


def _windows(px: pd.DataFrame, p: tuple) -> list[int]:
    idx = px.index
    i0, i1 = idx.searchsorted(pd.Timestamp(p[0])), idx.searchsorted(pd.Timestamp(p[1]), side="right") - 1
    return list(range(i0, i1 - HOLD, HOLD))


def _weights(atr: np.ndarray, how: str) -> np.ndarray:
    ok = np.isfinite(atr) & (atr > 0)
    atr = np.where(ok, atr, np.median(atr[ok]) if ok.any() else 0.036)
    if how == "EQ":
        return np.full(len(atr), 1 / len(atr))
    if how == "IV":
        w = 1 / atr
        return w / w.sum()
    w = np.minimum(0.005 / (2 * atr), 0.15)                     # atr_pct is a fraction of price (0.036 = 3.6%)
    return w / w.sum() if w.sum() > 1 else w


def _window(P: np.ndarray, w: np.ndarray, atr: np.ndarray, stop: str) -> np.ndarray:
    """Book value path over one window (start 1.0), names bought at row 0's close. P: rows = sessions 0..HOLD, cols = names."""
    P = pd.DataFrame(P).ffill().to_numpy()                        # a name that stops trading keeps its last price
    rel = P / P[0]
    if stop != "none":
        a = np.where(np.isfinite(atr) & (atr > 0), atr, 0.036)
        lvl = np.full(rel.shape[1], 0.93) if stop == "S7" else 1 - 2 * a
        hit = rel[1:] <= lvl
        for k in range(rel.shape[1]):
            if hit[:, k].any():
                f = int(hit[:, k].argmax()) + 1
                rel[f:, k] = rel[f, k] * (1 - COST)               # sold at that close; the money waits in cash
    return (1 - w.sum()) + (rel * w).sum(1)


def _run(px, A, fe_by_date, wins, pick, how, stop, rng=None, brake=False) -> pd.Series:
    dates, vals, v, peak, half = [], [], 1.0, 1.0, False
    cols = px.columns
    for i in wins:
        f = fe_by_date.get(px.index[i])
        if f is None or len(f) < 50:
            continue
        if pick == "M":
            g = f[f.dist_sma200 > 0].nlargest(N_NAMES, "ret_60")
            if len(g) < N_NAMES:
                continue
        else:
            g = f.iloc[rng.choice(len(f), N_NAMES, replace=False)]
        j = cols.get_indexer(g.sid)
        P = A[i:i + HOLD + 1, j]
        if not np.all(np.isfinite(P[0])):
            continue
        atr = g.atr_pct.to_numpy(dtype=float)
        w = _weights(atr, how)
        scale = 0.5 if half else 1.0
        path = (1 - scale) + scale * _window(P, w, atr, stop)
        path = path * (1 - COST * w.sum() * scale)                # the buys
        path[-1] *= (1 - COST * w.sum() * scale)                  # the sells at the window's end
        for k in range(1, len(path)):
            dates.append(px.index[i + k])
            vals.append(v * path[k])
        v *= path[-1]
        peak = max(peak, v)
        half = bool(brake and v <= 0.9 * peak)
    return pd.Series(vals, index=dates)


def _metrics(s: pd.Series) -> dict:
    if len(s) < 60:
        return {}
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    r = s.pct_change().dropna()
    dd = float((s / s.cummax() - 1).min())
    cagr = float(s.iloc[-1] ** (1 / yrs) - 1)
    w20 = float((s / s.shift(20) - 1).min())
    return {"cagr": round(cagr * 100, 2), "vol": round(float(r.std() * np.sqrt(250)) * 100, 2), "maxdd": round(dd * 100, 2),
            "worst20": round(w20 * 100, 2), "ret_per_dd": round(cagr / abs(dd), 3) if dd < 0 else None}


def study(seeds: int = SEEDS) -> dict:
    fe, px = _load()
    A = px.to_numpy()
    elig = fe[(fe.liq_rank <= 250)].dropna(subset=["c"])
    fe_by_date = {d: g.reset_index(drop=True) for d, g in elig.groupby("date")}
    out = {"made": dt.datetime.now().isoformat(timespec="seconds"), "periods": {"dev": DEV, "val": VAL}, "names": N_NAMES, "hold": HOLD,
           "seeds": seeds, "cost": COST, "results": {}}
    methods = [(h, s, False) for h in SIZINGS for s in STOPS] + [("EQ", "none", True)]
    for pname, p in (("dev", DEV), ("val", VAL)):
        wins = _windows(px, p)
        res = {}
        for h, s, b in methods:
            key = f"{h}/{s}" + ("/DD" if b else "")
            m = _metrics(_run(px, A, fe_by_date, wins, "M", h, s, brake=b))
            rs = [_metrics(_run(px, A, fe_by_date, wins, "R", h, s, rng=np.random.default_rng(seed), brake=b)) for seed in range(seeds)]
            res[key] = {"M": m, "R_median": {k: round(float(np.median([x[k] for x in rs if x.get(k) is not None])), 3) for k in rs[0]},
                        "R_all": rs}
        base = res["EQ/none"]["R_all"]
        for key, r in res.items():
            r["R_beats_EQ_on_ret_per_dd"] = round(float(np.mean([(a.get("ret_per_dd") or -9) > (b.get("ret_per_dd") or -9)
                                                               for a, b in zip(r["R_all"], base)])), 2)
            r.pop("R_all")
        out["results"][pname] = res
    out["nifty50"] = _nifty()
    out["verdicts"] = verdicts(out["results"])
    return out


def _nifty() -> dict:
    d = paths.data_dir()
    ix = duckdb.connect().execute(f"""select date, close from read_parquet('{d}/silver/kite_index/day/day.parquet')
                                      where index_name = 'NIFTY 50' and date <= '{VAL[1]}' order by date""").df()
    ix["date"] = pd.to_datetime(ix["date"])
    s = ix.set_index("date")["close"]
    return {p: _metrics(s[(s.index >= pd.Timestamp(r[0])) & (s.index <= pd.Timestamp(r[1]))] / s[s.index >= pd.Timestamp(r[0])].iloc[0])
            for p, r in (("dev", DEV), ("val", VAL))}


def verdicts(res: dict) -> dict:
    v = {}
    for key in res["dev"]:
        if key == "EQ/none":
            continue
        safer, better = True, True
        for p in ("dev", "val"):
            for who in ("M", "R_median"):
                b, m = res[p]["EQ/none"][who], res[p][key][who]
                if not b or not m or b.get("maxdd") is None:
                    safer = better = False
                    continue
                if not abs(m["maxdd"]) <= 0.85 * abs(b["maxdd"]):
                    safer = False
                if not (m.get("ret_per_dd") or -9) > (b.get("ret_per_dd") or -9):
                    better = False
        v[key] = "BETTER" if safer and better else "SAFER-BUT-COSTLY" if safer else "NO BETTER"
    return v


def words(s: dict) -> str:
    L = [f"# Sizing and risk study ({s['made'][:10]})", "",
         f"15 names from the 250 most-traded, held {s['hold']} sessions, costs {s['cost'] * 100:.2f}% a side. Random books: median of "
         f"{s['seeds']}. Development 2007-2017, validation 2018-2023 (sealed years not read).", ""]
    for p in ("dev", "val"):
        L += [f"## {p}", "", "| method | M yearly % | M max fall % | M worst 20 | M ret/fall | R yearly % | R max fall % | R ret/fall | R beats EQ |",
              "|---|---|---|---|---|---|---|---|---|"]
        for k, r in s["results"][p].items():
            m, rm = r["M"], r["R_median"]
            L.append(f"| {k} | {m.get('cagr')} | {m.get('maxdd')} | {m.get('worst20')} | {m.get('ret_per_dd')} | {rm.get('cagr')} | "
                     f"{rm.get('maxdd')} | {rm.get('ret_per_dd')} | {r['R_beats_EQ_on_ret_per_dd']} |")
        L.append(f"\nNifty 50 held (no costs): {s.get('nifty50', {}).get(p)}")
        L.append("")
    L += ["## Verdicts (rule fixed before the run)", ""] + [f"- {k}: {v}" for k, v in s["verdicts"].items()]
    return "\n".join(L) + "\n"


def main() -> None:
    import sys

    s = study(int(sys.argv[1]) if len(sys.argv) > 1 else SEEDS)
    d = paths.data_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    day = dt.date.today().isoformat()
    (d / f"sizingstudy_{day}.json").write_text(json.dumps(s, indent=1, default=str))
    (d / f"sizingstudy_{day}.md").write_text(words(s))
    print(words(s))


if __name__ == "__main__":
    main()
