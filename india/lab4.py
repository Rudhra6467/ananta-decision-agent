"""Lab 4 (27 Oct 2026; Madhav 18:26 Toronto: "yes please also run the three studies on the gaps the grader named"): option Greeks and time decay
(GK1), intraday breakouts (IB1) and intraday patterns (MS1). The specs (india/registrations/{gk1,ib1,ms1}_v1.json) were written before any outcome
was read; `run` registers each study with the spec's frozen k, computes, and records every variant in the ledger. Research rows only: nothing dated
2024 or later and no sealed folder (silver/kite_index minute, silver/kite_5m, silver/fo_bhavcopy, silver/fo_greeks and the SP1 research outcomes all
stop at 2023-12-29; the SP1 holdout is not touched).

  python -m india.lab4 check [gk1|ib1|ms1|all]    event counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.lab4 run gk1|ib1|ms1             register, compute, record; manifests/lab4_<study>.json and registrations/<study>_results_v1.md
  python -m india.lab4 table <study>               rewrite the results page from the manifest
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths, registry
from india.lab3 import _clean, _f

REG_DIR = Path(__file__).resolve().parent / "registrations"
CUT = pd.Timestamp("2024-01-01")
SPLIT = 2018
YEARS = list(range(2014, 2024))
SEED = 20261027
# minute index from 09:15 (index minute arrays: 0..374)
M_0930, M_1000, M_1015, M_1100, M_1330, M_1400, M_1430, M_1525 = 15, 45, 60, 105, 255, 285, 315, 370


def spec(study: str) -> dict:
    return json.loads((REG_DIR / f"{study.lower()}_v1.json").read_text())


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = pd.Series(x).dropna()
    if len(x) < 3:
        return (float("nan"), float("nan"), int(len(x)))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return (float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x)))


def _per(dates: pd.Series, freq: str) -> pd.Series:
    return pd.to_datetime(dates).dt.to_period(freq)


def _absolute(df: pd.DataFrame, col: str, freq: str = "M") -> dict:
    """Block means of the outcome itself, t across blocks."""
    d = df.dropna(subset=[col])
    p = _per(d["date"], freq)
    m = d.groupby(p)[col].mean()
    return {"dev": _stat(m[[q.year < SPLIT for q in m.index]]), "val": _stat(m[[q.year >= SPLIT for q in m.index]]),
            "extra": {"n_on": int(len(d)), "mean_on": float(d[col].mean()) if len(d) else None, "positive_share_info_only": float((d[col] > 0).mean()) if len(d) else None,
                      **_counts(d["date"])}}


def _paired(a: pd.DataFrame, b: pd.DataFrame, col: str, freq: str = "M") -> dict:
    """Per block: mean of a minus mean of b (blocks where both exist), t across blocks."""
    a, b = a.dropna(subset=[col]), b.dropna(subset=[col])
    ma = a.groupby(_per(a["date"], freq))[col].mean()
    mb = b.groupby(_per(b["date"], freq))[col].mean()
    diff = (ma - mb).dropna()
    return {"dev": _stat(diff[[q.year < SPLIT for q in diff.index]]), "val": _stat(diff[[q.year >= SPLIT for q in diff.index]]),
            "extra": {"n_on": int(len(a)), "n_base": int(len(b)), "mean_on": float(a[col].mean()) if len(a) else None,
                      "mean_base": float(b[col].mean()) if len(b) else None, **_counts(a["date"]),
                      "base_dev_val": [int((pd.to_datetime(b["date"]).dt.year < SPLIT).sum()), int((pd.to_datetime(b["date"]).dt.year >= SPLIT).sum())]}}


def _split_m(df: pd.DataFrame, on: pd.Series, col: str, min_on: int = 1, min_off: int = 3) -> dict:
    """Monthly block means of 'on' days against 'off' days, Welch t across the block means (same-day outcomes)."""
    d = df.assign(_on=on.astype(float).values).dropna(subset=[col, "_on"])
    p = _per(d["date"], "M")
    out = {}
    for name, sel in (("dev", p.dt.year < SPLIT), ("val", p.dt.year >= SPLIT)):
        x, pp = d[sel.values], p[sel.values]
        g = x.groupby([pp.values, x["_on"].values])[col].agg(["mean", "count"]).unstack()
        if ("mean", 1.0) not in g.columns or ("mean", 0.0) not in g.columns:
            out[name] = (float("nan"), float("nan"), 0)
            continue
        on_m = g[("mean", 1.0)][g[("count", 1.0)] >= min_on].dropna()
        off_m = g[("mean", 0.0)][g[("count", 0.0)] >= min_off].dropna()
        if len(on_m) < 3 or len(off_m) < 3:
            out[name] = (float("nan"), float("nan"), int(min(len(on_m), len(off_m))))
            continue
        diff = float(on_m.mean() - off_m.mean())
        se = math.sqrt(on_m.var(ddof=1) / len(on_m) + off_m.var(ddof=1) / len(off_m))
        out[name] = (diff, diff / se if se else float("nan"), int(min(len(on_m), len(off_m))))
    n_on = int((d["_on"] == 1).sum())
    out["extra"] = {"n_on": n_on, "n_off": int((d["_on"] == 0).sum()), "block": "M", "mean_on": float(d.loc[d["_on"] == 1, col].mean()) if n_on else None,
                    "mean_off": float(d.loc[d["_on"] == 0, col].mean()) if len(d) - n_on else None, **_counts(d.loc[d["_on"] == 1, "date"])}
    return out


def _counts(dates: pd.Series) -> dict:
    y = pd.to_datetime(dates).dt.year
    return {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())}


def _days() -> list[dt.date]:
    from india import ocstudy
    days, _sp = ocstudy._calendar()
    return [d for d in days if d.year >= 2014]


def _expiries(sym: str) -> list[dt.date]:
    c = pd.read_parquet(paths.data_dir() / "silver/fo_calendar/expiries.parquet")
    c = c[(c["symbol"] == sym) & (c["instrument"] == "OPTIDX")]
    e = sorted(pd.to_datetime(c["expiry"]).dt.date.unique())
    return [x for x in e if dt.date(2014, 1, 1) <= x <= dt.date(2023, 12, 29)]


def _index_day() -> pd.DataFrame:
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet", columns=["index_name", "date", "open", "close"])
    ix["date"] = pd.to_datetime(ix["date"]).dt.date
    ix = ix[(ix["date"] < CUT.date()) & (ix["close"] > 0)].drop_duplicates(["index_name", "date"], keep="last")
    return ix


# =============================================================================================================================== GK1: option Greeks, time decay

SYM_IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
TAG = {"NIFTY": "NIFTY", "BANKNIFTY": "BANK"}


def _straddle_targets() -> pd.DataFrame:
    days = _days()
    pos = {d: i for i, d in enumerate(days)}
    rows = []
    for sym in SYM_IDX:
        for e in _expiries(sym):
            if e not in pos:
                continue
            i = pos[e]
            rows.append({"symbol": sym, "date": e, "expiry": e, "kind": "exp0"})
            if i - 3 >= 0:
                d3 = days[i - 3]
                # the same series must be the nearest expiry on that day (no other expiry in between)
                rows.append({"symbol": sym, "date": d3, "expiry": e, "kind": "exp3"})
    T = pd.DataFrame(rows)
    nearest_ok = []
    for sym, g in T.groupby("symbol"):
        ex = _expiries(sym)
        for r in g.itertuples():
            nxt = [x for x in ex if x >= r.date]
            nearest_ok.append(bool(nxt) and nxt[0] == r.expiry)
    T = pd.concat([g for _s, g in T.groupby("symbol")]).assign(nearest=nearest_ok)
    return T[T["nearest"]].drop(columns="nearest").reset_index(drop=True)


def _straddles() -> pd.DataFrame:
    import duckdb
    from india import costs, sp1
    D = paths.data_dir()
    T = _straddle_targets()
    files = [str(D / "silver/fo_bhavcopy" / f"year={y}" / "part.parquet") for y in YEARS if (D / "silver/fo_bhavcopy" / f"year={y}" / "part.parquet").exists()]
    con = duckdb.connect()
    t = T.assign(date=pd.to_datetime(T["date"]), expiry=pd.to_datetime(T["expiry"]))
    con.register("t", t)
    o = con.execute(f"""select b.symbol, b.date, b.expiry, b.strike, b.opt_type, b.open, b.close, b.volume, t.kind
                        from read_parquet({files!r}, union_by_name=true) b join t on b.symbol = t.symbol and b.date = t.date and b.expiry = t.expiry
                        where b.instrument = 'OPTIDX' and b.date < DATE '2024-01-01'""").df()
    # the option rows carry no lot size: the nearest index future's lot that day (as india.ocstudy.load_lots does)
    lots = con.execute(f"""select symbol, date, arg_min(coalesce(lot_size, lot_est), expiry) as lot
                           from read_parquet({files!r}, union_by_name=true) where instrument = 'FUTIDX' and symbol in ('NIFTY', 'BANKNIFTY')
                           and date < DATE '2024-01-01' group by 1, 2""").df()
    con.close()
    lots["date"] = pd.to_datetime(lots["date"]).dt.date
    o["date"] = pd.to_datetime(o["date"]).dt.date
    o = o.merge(lots, on=["symbol", "date"], how="left")
    ix = _index_day()
    opn = {(r.index_name, r.date): float(r.open) for r in ix.itertuples()}
    out = []
    for (sym, day, kind), g in o.groupby(["symbol", "date", "kind"]):
        spot = opn.get((SYM_IDX[sym], day))
        if spot is None or not (spot > 0):
            continue
        ok = g[(g["open"] > 0) & (g["close"] > 0) & (g["volume"] > 0)]
        ce, pe = ok[ok["opt_type"] == "CE"].set_index("strike"), ok[ok["opt_type"] == "PE"].set_index("strike")
        both = sorted(set(ce.index) & set(pe.index))
        if not both:
            continue
        K = min(both, key=lambda k: abs(k - spot))
        if abs(K / spot - 1) > 0.02:
            continue
        lot = float(ce.loc[K, "lot"]) if ce.loc[K, "lot"] == ce.loc[K, "lot"] else float(pe.loc[K, "lot"])
        if not (lot > 0):
            continue
        net, prem = 0.0, 0.0
        for leg in (ce.loc[K], pe.loc[K]):
            p_in, p_out = float(leg["open"]), float(leg["close"])
            h_in, h_out = max(sp1.OPT_HALF[sym], 0.0025 * p_in), max(sp1.OPT_HALF[sym], 0.0025 * p_out)
            buy, sell = p_in + h_in, max(p_out - h_out, 0.0)
            fees = costs.cost("options", "buy", buy * lot, day.year, when=day) + costs.cost("options", "sell", sell * lot, day.year, when=day)
            net += (sell - buy) * lot - fees
            prem += p_in * lot
        out.append({"date": pd.Timestamp(day), "symbol": sym, "kind": kind, "strike": K, "spot_open": spot, "premium_rs": prem, "net_rs": net,
                    "ret": net / prem if prem > 0 else np.nan, "gross_ret": float((ce.loc[K, "close"] + pe.loc[K, "close"]) / (ce.loc[K, "open"] + pe.loc[K, "open"]) - 1)})
    return pd.DataFrame(out)


def _realised_vs_implied() -> pd.DataFrame:
    import duckdb
    D = paths.data_dir()
    files = [str(D / "silver/fo_greeks" / f"year={y}" / "part.parquet") for y in YEARS if (D / "silver/fo_greeks" / f"year={y}" / "part.parquet").exists()]
    con = duckdb.connect()
    g = con.execute(f"""select symbol, date, expiry, opt_type, arg_min(iv, abs(moneyness)) as iv, arg_min("T", abs(moneyness)) as T
                        from read_parquet({files!r}, union_by_name=true)
                        where symbol in ('NIFTY', 'BANKNIFTY') and flag = 'ok' and iv > 0 and expiry > date and date < DATE '2024-01-01'
                        group by 1, 2, 3, 4""").df()
    con.close()
    g["date"] = pd.to_datetime(g["date"]).dt.date
    g["expiry"] = pd.to_datetime(g["expiry"]).dt.date
    near = g.groupby(["symbol", "date"])["expiry"].transform("min")
    g = g[g["expiry"] == near]
    a = g.groupby(["symbol", "date", "expiry"]).agg(iv=("iv", "mean"), T=("T", "mean"), legs=("iv", "size")).reset_index()
    a = a[a["legs"] == 2]
    days = _days()
    pos = {d: i for i, d in enumerate(days)}
    ix = _index_day()
    cl = {(r.index_name, r.date): float(r.close) for r in ix.itertuples()}
    rows = []
    for r in a.itertuples():
        if r.date not in pos or r.expiry not in pos:
            continue
        dte = pos[r.expiry] - pos[r.date]
        c0, c1 = cl.get((SYM_IDX[r.symbol], r.date)), cl.get((SYM_IDX[r.symbol], r.expiry))
        if not (c0 and c1) or not (r.T > 0):
            continue
        exp_abs = r.iv * math.sqrt(r.T) * math.sqrt(2 / math.pi)
        rows.append({"date": pd.Timestamp(r.date), "symbol": r.symbol, "dte": dte, "iv": r.iv, "T": r.T, "realised_abs": abs(math.log(c1 / c0)),
                     "implied_abs": exp_abs, "ratio_m1": abs(math.log(c1 / c0)) / exp_abs - 1 if exp_abs > 0 else np.nan})
    return pd.DataFrame(rows)


def _next_vs_near() -> pd.DataFrame:
    from india import sp1
    from india.lab3 import _os_book
    D = paths.data_dir()
    O = pd.read_parquet(D / "gold/studies/SP1_outcomes.parquet")
    O = O[O["point"].isin(["D1", "D2"]) & O["exit"].isin(["ATRSTOP", "T1515"]) & O["opt_net_rs"].notna()]
    O = O[pd.to_datetime(O["date"]) < CUT]
    ob, nxt = _os_book()
    cache = {}

    def setup2(sym, day):
        p = ob.prev.get(day)
        g = ob.by.get((sym, p)) if p else None
        if g is None or g.empty:
            return None
        ex = sorted(e for e in g["expiry"].unique() if e > day)
        if len(ex) < 2:
            return None
        e = ex[1]
        c = g[g["expiry"] == e]
        spot_prev = ob.pc.get((sym, p))
        fwd = c["fwd"].dropna()
        if spot_prev is None or fwd.empty:
            return None
        out = {"expiry": e, "carry": float(fwd.median()) / spot_prev, "listed": np.sort(c["strike"].unique())}
        for t in ("CE", "PE"):
            x = c[(c["opt_type"] == t) & (c["volume"] > 0) & c["iv"].notna() & (c["iv"] > 0)]
            out[t] = (x["strike"].to_numpy(), x["iv"].to_numpy())
        return out

    rows = []
    for r in O.itertuples(index=False):
        day = r.date if isinstance(r.date, dt.date) else pd.Timestamp(r.date).date()
        key = (r.index, day)
        if key not in cache:
            cache[key] = setup2(r.index, day)
        s2 = cache[key]
        if s2 is None or not (r.opt_prem_in == r.opt_prem_in) or r.opt_prem_in <= 0:
            continue
        day_out = nxt.get(day) if r.next_day else day
        if day_out is None:
            continue
        m_in = sp1.POINT_ENTRY[r.point]
        m_out = 1 if r.next_day else int(r.exit_min)
        leg = sp1.option_leg(r.index, day, s2, int(r.dir), float(r.entry), m_in, float(r.exit_px), day_out, m_out, bool(r.stopped), float(r.lot))
        if leg is None or not (leg["opt_ret"] == leg["opt_ret"]):
            continue
        near = float(r.opt_net_rs) / (float(r.opt_prem_in) * float(r.lot))
        rows.append({"date": pd.Timestamp(day), "index": r.index, "near_ret": near, "next_ret": float(leg["opt_ret"]), "diff": float(leg["opt_ret"]) - near,
                     "near_rs": float(r.opt_net_rs), "next_rs": float(leg["opt_net_rs"]), "near_dte": float(r.opt_dte), "next_dte": float(leg["opt_dte"])})
    return pd.DataFrame(rows)


def gk1_results(counts_only: bool = False) -> dict:
    out = {}
    S = _straddles()
    for sym in SYM_IDX:
        tag = TAG[sym]
        e0, e3 = S[(S["symbol"] == sym) & (S["kind"] == "exp0")], S[(S["symbol"] == sym) & (S["kind"] == "exp3")]
        if counts_only:
            out[f"{tag}|exp0|straddle_oc"] = _counts(e0["date"])
            out[f"{tag}|exp0_vs_exp3|straddle_oc"] = {**_counts(e0["date"]), "exp3": _counts(e3["date"])}
            continue
        r = _absolute(e0, "ret", "Q")
        r["extra"].update({"gross_mean": float(e0["gross_ret"].mean()) if len(e0) else None, "mean_net_rs_per_straddle": float(e0["net_rs"].mean()) if len(e0) else None,
                           "dev_val_mean": [float(e0.loc[e0["date"].dt.year < SPLIT, "ret"].mean()), float(e0.loc[e0["date"].dt.year >= SPLIT, "ret"].mean())]})
        out[f"{tag}|exp0|straddle_oc"] = r
        p = _paired(e0, e3, "ret", "Q")
        p["extra"].update({"exp3_dev_val_mean": [float(e3.loc[e3["date"].dt.year < SPLIT, "ret"].mean()), float(e3.loc[e3["date"].dt.year >= SPLIT, "ret"].mean())]})
        out[f"{tag}|exp0_vs_exp3|straddle_oc"] = p
    R = _realised_vs_implied()
    for key, lo, hi in (("ALL|dte1|realised_vs_implied", 1, 1), ("ALL|dte2_3|realised_vs_implied", 2, 3), ("ALL|dte4_7|realised_vs_implied", 4, 7)):
        x = R[(R["dte"] >= lo) & (R["dte"] <= hi)]
        if counts_only:
            out[key] = _counts(x["date"])
            continue
        r = _absolute(x, "ratio_m1", "Q")
        r["extra"].update({"mean_realised_abs": float(x["realised_abs"].mean()), "mean_implied_abs": float(x["implied_abs"].mean()),
                           "median_ratio": float((x["ratio_m1"] + 1).median()), "by_index": {s: float(g["ratio_m1"].mean()) for s, g in x.groupby("symbol")}})
        out[key] = r
    if counts_only:
        O = pd.read_parquet(paths.data_dir() / "gold/studies/SP1_outcomes.parquet", columns=["date", "point", "exit", "opt_net_rs"])
        O = O[O["point"].isin(["D1", "D2"]) & O["exit"].isin(["ATRSTOP", "T1515"]) & O["opt_net_rs"].notna() & (pd.to_datetime(O["date"]) < CUT)]
        out["SP1|next_vs_near|ret"] = {"candidate_rows": _counts(O["date"])}
        return out
    N = _next_vs_near()
    m = N.groupby(_per(N["date"], "M"))["diff"].mean()
    out["SP1|next_vs_near|ret"] = {"dev": _stat(m[[q.year < SPLIT for q in m.index]]), "val": _stat(m[[q.year >= SPLIT for q in m.index]]),
                                   "extra": {**_counts(N["date"]), "mean_near_ret": float(N["near_ret"].mean()), "mean_next_ret": float(N["next_ret"].mean()),
                                             "mean_near_rs": float(N["near_rs"].mean()), "mean_next_rs": float(N["next_rs"].mean()),
                                             "win_near": float((N["near_ret"] > 0).mean()), "win_next": float((N["next_ret"] > 0).mean()),
                                             "median_dte_near_next": [float(N["near_dte"].median()), float(N["next_dte"].median())]}}
    return out


# =============================================================================================================================== IB1 / MS1: index minutes, stock 5-minute bars

_IDX_CACHE: dict = {}


def _index_minutes() -> dict:
    if not _IDX_CACHE:
        from india import ocstudy
        a = ocstudy.load_index()
        for name in ("NIFTY 50", "NIFTY BANK"):
            x = a[name]
            keep = np.array([d < CUT.date() for d in x["dates"]]) & x["ok"]
            _IDX_CACHE[name] = {"dates": [d for d, k in zip(x["dates"], keep) if k], **{f: x[f][keep] for f in ("open", "high", "low", "close")}}
    return _IDX_CACHE


_COST: dict = {}


def _idx_cost(day: dt.date) -> float:
    from india import costs
    if day.year not in _COST:
        V = 1_000_000.0
        _COST[day.year] = costs.round_trip("futures", V, V, day.year, turnover_rank=1, when=dt.date(day.year, 7, 1))["total"] / V
    return _COST[day.year]


def _stk_cost(day: dt.date, rank: int) -> float:
    from india import costs
    k = (day.year, int(rank))
    if k not in _COST:
        V = 50_000.0
        _COST[k] = costs.round_trip("intraday", V, V, day.year, turnover_rank=int(rank), when=dt.date(day.year, 7, 1))["total"] / V
    return _COST[k]


def _break_trades(O, H, L, C, rh, rl, start, last, exit_bar, long_only=False):
    """First break of the range [rl, rh] between bars start..last: entry at the level (or the bar's open past it), stop at the other side, exit at
    exit_bar's close. Returns a list of (row, dir, entry, exit, stopped)."""
    out = []
    n = O.shape[0]
    up = H[:, start:last + 1] > rh[:, None]
    dn = L[:, start:last + 1] < rl[:, None]
    for i in range(n):
        if not (rh[i] > rl[i]):
            continue
        iu = int(np.argmax(up[i])) if up[i].any() else None
        idn = int(np.argmax(dn[i])) if (dn[i].any() and not long_only) else None
        if long_only and dn[i].any() and iu is not None and dn[i][iu]:
            continue
        if iu is None and idn is None:
            continue
        if iu is not None and idn is not None:
            if iu == idn:
                continue
            d, m = (1, iu) if iu < idn else (-1, idn)
        elif iu is not None:
            d, m = 1, iu
        else:
            d, m = -1, idn
        m += start
        if d > 0:
            entry, stop = max(rh[i], O[i, m]), rl[i]
            hit = np.nonzero(L[i, m + 1:exit_bar + 1] <= stop)[0]
            if len(hit):
                j = m + 1 + hit[0]
                ex, st = min(stop, O[i, j]), True
            else:
                ex, st = C[i, exit_bar], False
        else:
            entry, stop = min(rl[i], O[i, m]), rh[i]
            hit = np.nonzero(H[i, m + 1:exit_bar + 1] >= stop)[0]
            if len(hit):
                j = m + 1 + hit[0]
                ex, st = max(stop, O[i, j]), True
            else:
                ex, st = C[i, exit_bar], False
        out.append((i, d, float(entry), float(ex), st))
    return out


def _control(O, C, lo, hi, exit_bar, long_only, salt):
    rng = np.random.default_rng(SEED + salt)
    n = O.shape[0]
    mm = rng.integers(lo, hi + 1, size=n)
    dd = np.ones(n) if long_only else rng.choice([-1.0, 1.0], size=n)
    e = O[np.arange(n), mm]
    return dd * (C[:, exit_bar] / e - 1)


def _index_ib(name: str, n_or: int, fh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = _index_minutes()[name]
    O, H, L, C = x["open"], x["high"], x["low"], x["close"]
    dates = x["dates"]
    if fh:
        rh, rl, start = H[:, :M_1015].max(1), L[:, :M_1015].min(1), M_1100
    else:
        rh, rl, start = H[:, :n_or].max(1), L[:, :n_or].min(1), n_or
    tr = _break_trades(O, H, L, C, rh, rl, start, M_1400, M_1525 - 1)
    T = pd.DataFrame([{"date": pd.Timestamp(dates[i]), "dir": d, "gross": d * (ex / en - 1), "stopped": st} for i, d, en, ex, st in tr])
    T["net"] = T["gross"] - [_idx_cost(t.date()) for t in T["date"]]
    cg = _control(O, C, M_1000, M_1400, M_1525 - 1, False, salt={"NIFTY 50": 100, "NIFTY BANK": 200}[name] + n_or + (7 if fh else 0))
    Ct = pd.DataFrame({"date": pd.to_datetime(dates), "gross": cg})
    Ct["net"] = Ct["gross"] - [_idx_cost(t.date()) for t in Ct["date"]]
    return T, Ct


_STK: dict = {}


def _stock_days() -> dict:
    """The 50 most liquid stocks of each day: 5-minute bars as day x bar arrays (75 bars from 09:15), with liq_rank."""
    if _STK:
        return _STK
    import duckdb
    D = paths.data_dir()
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet", columns=["sid", "symbol", "date", "n", "liq_rank"])
    P["date"] = pd.to_datetime(P["date"])
    P = P[P["date"] < CUT].sort_values(["sid", "date"]).reset_index(drop=True)
    # the universe is chosen on the PREVIOUS session's liquidity rank: liq_rank is the rank of a 60-day median turnover that includes the day
    # itself, so the same-day rank would let a stock's own intraday move help it into the list (27 Oct re-run, see the results page)
    consec = (P["sid"] == P["sid"].shift(1)) & (P["n"] == P["n"].shift(1) + 1)
    P["liq_rank"] = P["liq_rank"].shift(1).where(consec)
    P = P[(P["date"] >= "2015-01-01") & (P["liq_rank"] <= 50)][["symbol", "date", "liq_rank"]]
    files = [str(D / "silver/kite_5m" / f"year={y}" / "part.parquet") for y in range(2015, 2024) if (D / "silver/kite_5m" / f"year={y}" / "part.parquet").exists()]
    con = duckdb.connect()
    con.register("p", P)
    df = con.execute(f"""select k.symbol, k.date, (hour(k.ts) * 60 + minute(k.ts) - 555) // 5 as b, k.kite_open as o, k.kite_high as h, k.kite_low as l,
                                k.kite_close as c, k.kite_volume as v, p.liq_rank
                         from read_parquet({files!r}, union_by_name=true) k join p on k.symbol = p.symbol and k.date = p.date
                         where k.date < DATE '2024-01-01' and k.kite_close > 0""").df()
    con.close()
    df = df[(df["b"] >= 0) & (df["b"] < 75)]
    df["key"] = df["symbol"] + "|" + pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    cnt = df.groupby("key")["b"].transform("size")
    df = df[cnt >= 70]
    keys = df["key"].unique()
    ki = {k: i for i, k in enumerate(keys)}
    r = df["key"].map(ki).to_numpy()
    b = df["b"].to_numpy().astype(int)
    arr = {}
    for f in ("o", "h", "l", "c", "v"):
        a = np.full((len(keys), 75), np.nan, dtype=np.float64)
        a[r, b] = df[f].to_numpy(float)
        arr[f] = a
    # fill gaps: price fields with the last close, volume with 0
    c = pd.DataFrame(arr["c"]).ffill(axis=1).bfill(axis=1).to_numpy()
    for f in ("o", "h", "l"):
        arr[f] = np.where(np.isnan(arr[f]), c, arr[f])
    arr["c"] = c
    arr["v"] = np.nan_to_num(arr["v"])
    meta = df.drop_duplicates("key").set_index("key").loc[keys]
    _STK.update(arr)
    _STK["dates"] = pd.to_datetime(meta["date"]).to_numpy()
    _STK["rank"] = meta["liq_rank"].to_numpy()
    _STK["symbol"] = meta["symbol"].to_numpy()
    # bad rows: a bar more than 20% away from the day's median (a broken print)
    med = np.nanmedian(c, axis=1)
    bad = (np.abs(arr["h"] / med[:, None] - 1) > 0.2).any(1) | (np.abs(arr["l"] / med[:, None] - 1) > 0.2).any(1)
    _STK["ok"] = ~bad
    return _STK


B_1000, B_1400, B_1525 = 9, 57, 73


def _stk_net(dates, ranks, gross) -> np.ndarray:
    return np.array([g - _stk_cost(pd.Timestamp(d).date(), r) for d, r, g in zip(dates, ranks, gross)])


def _stock_ib(kind: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = _stock_days()
    ok = s["ok"]
    O, H, L, C, V = (s[f][ok] for f in ("o", "h", "l", "c", "v"))
    dates, ranks = s["dates"][ok], s["rank"][ok]
    if kind in ("orb15", "orb30"):
        nb = 3 if kind == "orb15" else 6
        rh, rl = H[:, :nb].max(1), L[:, :nb].min(1)
        tr = _break_trades(O, H, L, C, rh, rl, nb, B_1400, B_1525, long_only=True)
        rows = [(i, en, ex, st) for i, d, en, ex, st in tr if d > 0]
    else:   # vwap reclaim
        tp = (H + L + C) / 3
        cv = np.cumsum(V, axis=1)
        vw = np.where(cv > 0, np.cumsum(tp * V, axis=1) / np.where(cv > 0, cv, 1), np.nan)
        below = C < vw
        rows = []
        for i in range(O.shape[0]):
            for j in range(B_1000, B_1400 + 1):
                if C[i, j] > vw[i, j] and below[i, j - 1] and below[i, j - 2]:
                    stop = np.nanmin(L[i, :j + 1])
                    en = C[i, j]
                    hit = np.nonzero(L[i, j + 1:B_1525 + 1] <= stop)[0]
                    if len(hit):
                        k = j + 1 + hit[0]
                        rows.append((i, en, min(stop, O[i, k]), True))
                    else:
                        rows.append((i, en, C[i, B_1525], False))
                    break
    idx = np.array([r[0] for r in rows], dtype=int)
    gross = np.array([r[2] / r[1] - 1 for r in rows])
    T = pd.DataFrame({"date": pd.to_datetime(dates[idx]), "gross": gross, "stopped": [r[3] for r in rows], "rank": ranks[idx]})
    T["net"] = _stk_net(dates[idx], ranks[idx], gross)
    cg = _control(O, C, B_1000, B_1400, B_1525, True, salt={"orb15": 1, "orb30": 2, "vwap_reclaim": 3}[kind])
    Ct = pd.DataFrame({"date": pd.to_datetime(dates), "gross": cg, "rank": ranks})
    Ct["net"] = _stk_net(dates, ranks, cg)
    return T, Ct


def _ib_row(T: pd.DataFrame, Ct: pd.DataFrame) -> dict:
    r = _paired(T, Ct, "net", "M")
    r["extra"].update({"mean_gross": float(T["gross"].mean()) if len(T) else None, "win_rate_info_only": float((T["net"] > 0).mean()) if len(T) else None,
                       "stopped_share": float(T["stopped"].mean()) if len(T) else None, "control_mean_net": float(Ct["net"].mean()),
                       "dev_val_mean_net": [float(T.loc[T["date"].dt.year < SPLIT, "net"].mean()), float(T.loc[T["date"].dt.year >= SPLIT, "net"].mean())]})
    return r


def ib1_results(counts_only: bool = False) -> dict:
    out = {}
    plan = [("NIFTY|orb15|net", "NIFTY 50", 15, False), ("NIFTY|orb30|net", "NIFTY 50", 30, False),
            ("BANK|orb15|net", "NIFTY BANK", 15, False), ("BANK|orb30|net", "NIFTY BANK", 30, False)]
    for key, name, n_or, fh in plan:
        T, Ct = _index_ib(name, n_or, fh)
        out[key] = _counts(T["date"]) if counts_only else _ib_row(T, Ct)
    TT, CC = [], []
    for name in ("NIFTY 50", "NIFTY BANK"):
        T, Ct = _index_ib(name, 60, True)
        TT.append(T)
        CC.append(Ct)
    T, Ct = pd.concat(TT), pd.concat(CC)
    out["IDX|fh_break|net"] = _counts(T["date"]) if counts_only else _ib_row(T, Ct)
    for kind in ("orb15", "orb30", "vwap_reclaim"):
        T, Ct = _stock_ib(kind)
        out[f"STK|{kind}|net"] = _counts(T["date"]) if counts_only else _ib_row(T, Ct)
    return out


def _ms_index_frame() -> pd.DataFrame:
    rows = []
    for name, sym in (("NIFTY 50", "NIFTY"), ("NIFTY BANK", "BANKNIFTY")):
        x = _index_minutes()[name]
        O, H, L, C = x["open"], x["high"], x["low"], x["close"]
        exp = set(_expiries(sym))
        o0 = O[:, 0]
        r15 = C[:, M_0930 - 1] / o0 - 1
        rest = C[:, -1] / C[:, M_0930 - 1] - 1
        r_to1430 = C[:, M_1430 - 1] / o0 - 1
        r_last = C[:, -1] / C[:, M_1430 - 1] - 1
        orr = (H[:, :M_0930].max(1) - L[:, :M_0930].min(1)) / o0
        rest_rng = (H[:, M_0930:].max(1) - L[:, M_0930:].min(1)) / C[:, M_0930 - 1]
        pm = np.abs(C[:, -1] / C[:, M_1330 - 1] - 1)
        f = pd.DataFrame({"date": pd.to_datetime(x["dates"]), "index": sym, "r15": r15, "rest": rest, "r_to1430": r_to1430, "r_last": r_last,
                          "orr": orr, "rest_range": rest_rng, "pm_abs": pm, "expiry": [d in exp for d in x["dates"]]})
        q_hi = f["orr"].shift(1).rolling(250, min_periods=120).quantile(2 / 3)
        q_lo = f["orr"].shift(1).rolling(250, min_periods=120).quantile(1 / 3)
        f["or_top"] = np.where(q_hi.notna(), f["orr"] >= q_hi, np.nan)
        f["or_bottom"] = np.where(q_lo.notna(), f["orr"] <= q_lo, np.nan)
        rows.append(f)
    F = pd.concat(rows, ignore_index=True)
    F["first15_signed"] = np.where(F["r15"] != 0, np.sign(F["r15"]) * F["rest"], np.nan)
    F["last_signed"] = np.where(F["r_to1430"] != 0, np.sign(F["r_to1430"]) * F["r_last"], np.nan)
    return F


def _ms_profile() -> dict:
    x = _index_minutes()["NIFTY 50"]
    O, C = x["open"], x["close"]
    out = []
    for b in range(25):
        a = O[:, 0] if b == 0 else C[:, 15 * b - 1]
        z = C[:, min(15 * b + 14, 374)]
        r = z / a - 1
        t = (dt.datetime(2000, 1, 1, 9, 15) + dt.timedelta(minutes=15 * b)).strftime("%H:%M")
        out.append({"bucket": t, "mean_bp": float(np.nanmean(r) * 1e4), "mean_abs_bp": float(np.nanmean(np.abs(r)) * 1e4)})
    return {"nifty_15min_profile_2015_2023": out}


def ms1_results(counts_only: bool = False) -> dict:
    out = {}
    F = _ms_index_frame()
    for key, sym in (("NIFTY|first15|rest_signed", "NIFTY"), ("BANK|first15|rest_signed", "BANKNIFTY")):
        x = F[F["index"] == sym]
        out[key] = _counts(x.dropna(subset=["first15_signed"])["date"]) if counts_only else _absolute(x, "first15_signed", "M")
    s = _stock_days()
    ok = s["ok"]
    O, C = s["o"][ok], s["c"][ok]
    r15 = C[:, 2] / O[:, 0] - 1
    rest = C[:, -1] / C[:, 2] - 1
    S = pd.DataFrame({"date": pd.to_datetime(s["dates"][ok]), "y": np.where(r15 != 0, np.sign(r15) * rest, np.nan)})
    out["STK|first15|rest_signed"] = _counts(S.dropna()["date"]) if counts_only else _absolute(S, "y", "M")
    out["IDX|lasthour|extends"] = _counts(F.dropna(subset=["last_signed"])["date"]) if counts_only else _absolute(F, "last_signed", "M")
    base = (F["or_top"] == 1) | (F["or_bottom"] == 1)
    G = F[base].copy()
    out["IDX|or15_top|dayrange"] = _counts(G.loc[G["or_top"] == 1, "date"]) if counts_only else _split_m(G, (G["or_top"] == 1), "rest_range")
    out["IDX|expiry_pm|absmove"] = _counts(F.loc[F["expiry"], "date"]) if counts_only else _split_m(F, F["expiry"], "pm_abs")
    if not counts_only:
        out["NIFTY|first15|rest_signed"]["extra"].update(_ms_profile())
    return out


# =============================================================================================================================== run, results pages

FUNCS = {"GK1": gk1_results, "IB1": ib1_results, "MS1": ms1_results}


def check(study: str) -> dict:
    return FUNCS[study](counts_only=True)


def run(study: str, rerun_reason: str | None = None) -> dict:
    s = spec(study)
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"{study}: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register(study, family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note=f"spec india/registrations/{study.lower()}_v1.json (written before the run)", bar_families=s["bar"].get("bar_families"), union_k=k,
                            rerun_reason=rerun_reason)
    res = FUNCS[study]()
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(r.get("extra", {})), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])), "val": _clean(list(line["val"])),
                     "extra": _clean(line["extra"])})
    out = {"study": study, "registered_at": reg["at"], "k": k, "rows": rows}
    (paths.manifest_dir() / f"lab4_{study.lower()}.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    table(study, out)
    return out


TAKEAWAY: dict[str, list[str]] = {      # written after the runs of 27 Oct 2026, from the numbers in the tables below
    "GK1": [
        "**Time decay is real and brutal on expiry day, but it did not pass the strict bar in both periods; and for Ananta's same-day trades the nearest "
        "expiry still beat a longer-dated option (OPPOSITE). Options did not systematically imply bigger moves than the index then made.**",
        "- **Buying an at-the-money straddle (call + put) at the open on expiry day, sold at the close, after costs:** Nifty lost 14.7% of the premium on "
        "average (315 expiry days), Bank Nifty 16.5% (424). In 2018-23 the loss was 16% and 19% (t -4.7 and -6.2, strong); in 2014-17 about 8% (t -0.7 and "
        "-0.6, monthly expiries only for Nifty, too noisy). REJECTED only because the early period is weak. Only about a third of these days were winners.",
        "- **The same straddle three sessions before expiry:** about +0% to +1% a day on average, so expiry day was 12-14% worse in 2014-17 and 20% worse in "
        "2018-23 (t -3.8 and -5.3); REJECTED for the same reason.",
        "- **Nearest against next expiry on the options line's research trades (11,552 in 2015-17, about 23,124 in 2018-23):** the nearest-expiry option made "
        "+4.1% of its premium a trade (Rs 164 a lot), the next expiry only +0.8% (Rs 43). OPPOSITE: for a move inside one day, the nearest option's bigger "
        "response to the index outweighs its faster decay.",
        "- **Implied against realised moves:** one session before expiry the index moved 3.5% less than the options implied on average, 2-3 sessions out 4.5% "
        "less, 4-7 sessions out 4.9% more: no consistent overpricing (all REJECTED). The typical day moved less than implied (median 0.78-0.87 of it), but "
        "the occasional big move makes up the average.",
        "- **What Ananta does with this:** never buy options on expiry day to hold for the day; that is the clearest loss in the data. For a same-day trade "
        "the options line's nearest-expiry lot stays. No rule changes.",
    ],
    "IB1": [
        "**Intraday breakouts beat a random entry on the same days, often strongly, but almost none of them make money after costs on their own: they lose "
        "less than random entries do. VALIDATED here means 'better than random', not 'profitable'.**",
        "- **Liquid stocks, buy the break above the first 15 or 30 minutes' high (stop at the range low, out at 15:25), 17,590 and 15,377 trades in 2015-17, "
        "38,153 and 33,420 in 2018-23:** about 0.10-0.14% a trade better than a random entry (t 7-9, VALIDATED), but the trades themselves averaged -0.07% and "
        "-0.06% after costs, against -0.18% for random entries. Stopped out on 38% and 29% of trades; win rate about 40%.",
        "- **Stocks reclaiming VWAP:** 0.04-0.05% better than random (CONDITIONAL), but -0.14% a trade after costs.",
        "- **Nifty opening-range breakout, both directions:** 15 minutes REJECTED; 30 minutes VALIDATED against random (+0.13% and +0.08% a trade better) "
        "yet about -0.005% a trade after costs. **Bank Nifty:** 15 and 30 minutes CONDITIONAL; the 30-minute version earned +0.02% a trade after costs.",
        "- **Breaking the first hour's range after 11:00 (both indices, 3,910 trades):** VALIDATED against random (+0.08% and +0.11%); +0.03% a trade after "
        "costs: the only version clearly above zero, and small next to realistic slippage on a stop order.",
        "- **Caveats:** fills at the breakout level and at the stop are assumed with only the half-spread cost model; a fast breakout usually slips a few "
        "basis points more, which is about the whole edge. The stock universe was re-run on the previous session's liquidity rank (a same-day rank leaked "
        "slightly); the results barely changed.",
        "- **What Ananta does with this:** a breakout is better timing than a random entry, but not a money-maker by itself after costs. It could be tested "
        "as a shadow paper book, never traded on this alone.",
    ],
    "MS1": [
        "**The opening and the close are the busy parts of the Indian day, a wide first 15 minutes comes before a wide rest of the day (CONDITIONAL), but "
        "the first 15 minutes do not tell you the day's direction, and expiry afternoons are not wilder than other afternoons.**",
        "- **First 15 minutes' direction carrying to the close:** Nifty +0.07% in 2015-17 (t 2.8) and -0.01% in 2018-23; Bank Nifty and liquid stocks the "
        "same story. REJECTED: the opening direction is no guide to the close.",
        "- **Last hour extending the move made by 14:30 (both indices, 4,411 days):** +0.03% (t 2.9 and 3.2), a slight lean, below the strict bar: INCONCLUSIVE.",
        "- **A wide 09:15-09:30 range (top third of the last year):** the rest of the day's range averaged 1.64% against 0.96% after a narrow open; held "
        "strongly in 2018-23 (t 4.4), weaker in 2015-17 (t 2.0): CONDITIONAL. It predicts how much the day will move, not which way.",
        "- **Expiry-day afternoons (13:30-15:30):** an average 0.40% move, the same as other afternoons: REJECTED.",
        "- **The shape of the day (Nifty 2015-2023, descriptive):** the first 15 minutes move most (22 bp on average) and lean slightly down (-4.7 bp); "
        "midday is quietest (7-8 bp per 15 minutes); activity picks up after 14:00 and peaks at 15:00-15:15 (16 bp).",
        "- **What Ananta does with this:** it can say a wide open usually means a wide day, and that the first quarter-hour's direction is not a forecast. "
        "No rule changes.",
    ],
}


def table(study: str, out: dict | None = None) -> Path:
    if out is None:
        out = json.loads((paths.manifest_dir() / f"lab4_{study.lower()}.json").read_text())
    s = spec(study)
    L = [f"# {study} results: {s['title']}", "", f"Registered {out['registered_at']} (spec `{study.lower()}_v1.json`, written before the run); family {s['family']}, "
         f"k = {out['k']}, z = {registry.threshold(out['k']):.2f}. Development to 2017, validation 2018-2023; nothing from 2024 on.", ""]
    if TAKEAWAY.get(study):
        L += ["## In plain words", ""] + TAKEAWAY[study] + ["", "## The rows", ""]
    L += ["Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent "
          "blocks (16 needed per period) or a reading below the bar.", "",
          "| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        e = r["extra"] or {}
        d, v = r["dev"], r["val"]
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else '-'} | {r['verdict']} | {_f(d[0])} | {_f(d[1], False)} | {d[2]} | {_f(v[0])} | {_f(v[1], False)} | {v[2]} | "
                 f"{e.get('events_dev', 'n/a')} / {e.get('events_val', 'n/a')} |")
    if study == "MS1":
        prof = ((out["rows"][0].get("extra") or {}).get("nifty_15min_profile_2015_2023")) or []
        if prof:
            L += ["", "## Nifty through the day, 2015-2023 (descriptive, no verdict)", "", "| 15 minutes from | mean move (bp) | mean absolute move (bp) |", "|---|---|---|"]
            L += [f"| {p['bucket']} | {p['mean_bp']:+.2f} | {p['mean_abs_bp']:.1f} |" for p in prof]
    p = REG_DIR / f"{study.lower()}_results_v1.md"
    p.write_text("\n".join(L) + "\n")
    return p


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    arg = (sys.argv[2] if len(sys.argv) > 2 else "all").upper()
    studies_ = list(FUNCS) if arg == "ALL" else [arg]
    if cmd == "check":
        for st in studies_:
            print(st, json.dumps(_clean(check(st)), indent=1, default=str), flush=True)
    elif cmd == "run":
        why = sys.argv[sys.argv.index("--rerun") + 1] if "--rerun" in sys.argv else None
        for st in studies_:
            o = run(st, rerun_reason=why)
            for r in o["rows"]:
                print(st, r["variant"], r["verdict"], r["dev"], r["val"], (r["extra"] or {}).get("events_dev"), (r["extra"] or {}).get("events_val"), flush=True)
    elif cmd == "table":
        for st in studies_:
            print(table(st))
    else:
        print(__doc__)
