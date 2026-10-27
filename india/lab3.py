"""Lab 3 (27 Oct 2026): five registered studies of the topics Ananta could only answer from the textbook. Madhav's yes of 27 Oct 2026 09:17 Toronto
to the recommendations that followed his 25-question Ask session: candlestick patterns (CP1), Nifty valuation (VL1), low beta / low volatility (BT1),
option spreads against a single option (OS1) and corporate actions (CA1). The specs (india/registrations/{cp1,vl1,bt1,os1,ca1}_v1.json) were written
before any outcome was read; `run` registers each study with the spec's frozen k, computes, and records every variant in the ledger. Research rows only:
nothing dated 2024 or later and no sealed folder (the stock panel, silver/valuation, silver/kite_index, silver/fo_greeks, silver/cm_bhavcopy and the
SP1 research outcomes all stop at 2023-12-29; the SP1 holdout is not touched).

  python -m india.lab3 check [cp1|vl1|bt1|os1|ca1|all]    event counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.lab3 run cp1|vl1|bt1|os1|ca1             register, compute, record; manifests/lab3_<study>.json and registrations/<study>_results_v1.md
  python -m india.lab3 table <study>                        rewrite the results page from the manifest
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
from india import teachers_stock as ts

REG_DIR = Path(__file__).resolve().parent / "registrations"
CUT = pd.Timestamp("2024-01-01")
SPLIT = ts.SPLIT
COOL = 10
PANEL = None


def spec(study: str) -> dict:
    return json.loads((REG_DIR / f"{study.lower()}_v1.json").read_text())


def _clean(x):
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if (x != x or math.isinf(x)) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, (pd.Timestamp, dt.date)):
        return str(x)[:10]
    return x


def _counts(dates: pd.Series, mask: pd.Series) -> dict:
    y = pd.to_datetime(dates[mask.fillna(False).astype(bool)]).dt.year
    return {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())}


def _panel(cols: list[str]) -> pd.DataFrame:
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet", columns=sorted(set(["sid", "symbol", "date", "n", "liq_rank"] + cols)))
    P["date"] = pd.to_datetime(P["date"])
    return P[P["date"] < CUT].sort_values(["sid", "date"]).reset_index(drop=True)


def _nifty_close() -> pd.Series:
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet", columns=["index_name", "date", "close"])
    ix = ix[ix["index_name"] == "NIFTY 50"].assign(date=lambda d: pd.to_datetime(d["date"]))
    ix = ix[(ix["date"] < CUT) & (ix["close"] > 0)].drop_duplicates("date", keep="last").set_index("date").sort_index()
    return ix["close"].astype(float)


# =============================================================================================================================== CP1: candlestick patterns

def _cp_frame() -> pd.DataFrame:
    P = _panel(["o", "h", "l", "c", "fwd5", "fwd20", "net20"])
    consec = (P["sid"] == P["sid"].shift(1)) & (P["n"] == P["n"].shift(1) + 1)
    o, h, l, c = (P[k].astype(float) for k in ("o", "h", "l", "c"))
    o1, c1 = o.shift(1).where(consec), c.shift(1).where(consec)
    same6 = (P["sid"] == P["sid"].shift(6)) & (P["n"] == P["n"].shift(6) + 6)
    prior = (c.shift(1) / c.shift(6) - 1).where(same6)          # 5-session move to yesterday's close
    body, rng = (c - o).abs(), h - l
    lower, upper = np.minimum(o, c) - l, h - np.maximum(o, c)
    body1 = (c1 - o1).abs()
    liq = (P["liq_rank"] <= 250)
    ok = liq & (rng > 0) & np.isfinite(o) & np.isfinite(c) & ((c / c1 - 1).abs() < 0.5).fillna(False)
    with np.errstate(invalid="ignore"):
        dec, ris = prior <= -0.03, prior >= 0.03
        raw = {
            "hammer": ok & dec & (lower >= 2 * body) & (upper <= 0.25 * rng),
            "bullengulf": ok & dec & (c1 < o1) & (c > o) & (o <= c1) & (c >= o1) & (body > body1),
            "bearengulf": ok & ris & (c1 > o1) & (c < o) & (o >= c1) & (c <= o1) & (body > body1),
            "doji_rise": ok & ris & (body <= 0.10 * rng),
        }
    for k, m in raw.items():
        P[k] = ts._cooldown(P, m.fillna(False), COOL)
    P["liq"] = liq
    P["s5"] = ts.sample5(P)
    return P


CP_PLAN = [("STK|hammer|fwd5", "hammer", "fwd5", "level"), ("STK|hammer|fwd20", "hammer", "fwd20", "level"),
           ("STK|bullengulf|fwd5", "bullengulf", "fwd5", "level"), ("STK|bullengulf|fwd20", "bullengulf", "fwd20", "level"),
           ("STK|bearengulf|fwd20", "bearengulf", "fwd20", "level"), ("STK|doji_rise|fwd20", "doji_rise", "fwd20", "level"),
           ("STK|hammer|trade20", "hammer", "net20", "absolute"), ("STK|bullengulf|trade20", "bullengulf", "net20", "absolute")]


def cp1_results(counts_only: bool = False) -> dict:
    P = _cp_frame()
    out = {}
    for key, ev, col, how in CP_PLAN:
        cnt = _counts(P["date"], P[ev] & P["liq"])
        if counts_only:
            out[key] = cnt
            continue
        if how == "level":
            d = P[P["liq"] & (P["s5"] | P[ev])]
            r = ts.level(d, d[ev], col)
        else:
            r = ts.absolute(P[P["liq"]], P[ev] & P["liq"], col)
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


# =============================================================================================================================== VL1: Nifty valuation

def _expanding_pct(x: pd.Series, min_prior: int = 750) -> pd.Series:
    v = x.to_numpy(float)
    out = np.full(len(v), np.nan)
    srt: list[float] = []
    import bisect
    for i, val in enumerate(v):
        if val == val:
            if len(srt) >= min_prior:
                out[i] = bisect.bisect_left(srt, val) / len(srt)
            bisect.insort(srt, val)
    return pd.Series(out, index=x.index)


def _vl_frame() -> pd.DataFrame:
    v = pd.read_parquet(paths.data_dir() / "silver/valuation/index_pepb.parquet")
    v["date"] = pd.to_datetime(v["date"])
    v = v[(v["index_name"] == "NIFTY 50") & (v["date"] < CUT)].drop_duplicates("date", keep="last").set_index("date").sort_index()
    std = v["pe_basis"] == "standalone"
    pct = {"pe": _expanding_pct(v["pe"].where(std)), "pb": _expanding_pct(v["pb"].where(std)), "dy": _expanding_pct(v["div_yield"])}
    nc = _nifty_close()
    M = pd.DataFrame(index=nc.index)
    M["date"] = nc.index
    for k, s in pct.items():
        M[k] = s.reindex(nc.index)
    M["f60"] = nc.shift(-61) / nc.shift(-1) - 1
    M["f250"] = nc.shift(-251) / nc.shift(-1) - 1
    return M


VL_PLAN = [("NIFTY|pe_top10|fwd60", "pe", "top", "f60", 60), ("NIFTY|pe_bottom10|fwd60", "pe", "bottom", "f60", 60),
           ("NIFTY|pb_top10|fwd60", "pb", "top", "f60", 60), ("NIFTY|dy_top10|fwd60", "dy", "top", "f60", 60),
           ("NIFTY|dy_bottom10|fwd60", "dy", "bottom", "f60", 60), ("NIFTY|pe_top10|fwd250", "pe", "top", "f250", 250)]


def vl1_results(counts_only: bool = False) -> dict:
    M = _vl_frame()
    out = {}
    for key, m, side, col, h in VL_PLAN:
        base = M[m].notna() & M[col].notna()
        on = (M[m] >= 0.9) if side == "top" else (M[m] <= 0.1)
        on = on & base
        cnt = {**_counts(M["date"], on), "base_dev": int((base & (M.index.year < SPLIT)).sum()), "base_val": int((base & (M.index.year >= SPLIT)).sum()),
               "first_day": str(M.index[base][0].date()) if base.any() else None, "last_day": str(M.index[base][-1].date()) if base.any() else None}
        if counts_only:
            out[key] = cnt
            continue
        r = ts.msplit(M, on, col, h=h, base=base)
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


# =============================================================================================================================== BT1: low beta, low volatility

def _bt_monthly() -> tuple[pd.DataFrame, dict]:
    P = _panel(["c", "cost"])
    consec = (P["sid"] == P["sid"].shift(1)) & (P["n"] == P["n"].shift(1) + 1)
    c = P["c"].astype(float)
    ret = (c / c.shift(1) - 1).where(consec)
    ret = ret.where(ret.abs() < 0.5)
    nc = _nifty_close()
    nret = (nc / nc.shift(1) - 1)
    P["ret"] = ret
    P["nret"] = P["date"].map(nret)
    P = P[P["date"] >= "2002-01-01"].reset_index(drop=True)
    x, y = P["ret"], P["nret"]
    both = x.notna() & y.notna()
    P["xy"], P["xx"], P["yy"], P["yv"] = (x * y).where(both), x.where(both), (y * y).where(both), y.where(both)
    g = P.groupby("sid", sort=False)
    roll = lambda col, w, mp: g[col].transform(lambda s: s.rolling(w, min_periods=mp).mean())
    mxy, mx, my, myy = roll("xy", 250, 200), roll("xx", 250, 200), roll("yv", 250, 200), roll("yy", 250, 200)
    P["beta"] = (mxy - mx * my) / (myy - my * my)
    P["vol60"] = g["ret"].transform(lambda s: s.rolling(60, min_periods=50).std())
    P["ym"] = P["date"].dt.to_period("M")
    days = np.sort(P["date"].unique())
    month_end = pd.Series(days).groupby(pd.Series(days).dt.to_period("M")).max()
    R = P.pivot_table(index="date", columns="sid", values="ret", aggfunc="last").sort_index()
    costs_ = P.pivot_table(index="date", columns="sid", values="cost", aggfunc="last").sort_index()
    rows, prev = [], {}
    months = list(month_end.index)
    rp = R.index.to_period("M")
    form = P[P["liq_rank"] <= 250].groupby("date")
    for i in range(len(months) - 1):
        d0 = month_end[months[i]]
        if pd.Timestamp(d0) < pd.Timestamp("2003-12-01"):
            continue
        f = form.get_group(d0) if d0 in form.groups else P.iloc[0:0]
        nxt = R[rp == months[i + 1]]
        if nxt.empty:
            continue
        cst = costs_.loc[d0]
        row = {"month": str(months[i + 1])}
        sets = {}
        fb, fv = f.dropna(subset=["beta"]), f.dropna(subset=["vol60"])
        if len(fb) >= 100 and len(fv) >= 100:
            qb, qv = fb["beta"].quantile([0.2, 0.8]), fv["vol60"].quantile([0.2, 0.8])
            sets["LOWBETA"] = set(fb.loc[fb["beta"] <= qb[0.2], "sid"])
            sets["HIGHBETA"] = set(fb.loc[fb["beta"] >= qb[0.8], "sid"])
            sets["LOWVOL"] = set(fv.loc[fv["vol60"] <= qv[0.2], "sid"])
            sets["HIGHVOL"] = set(fv.loc[fv["vol60"] >= qv[0.8], "sid"])
            sets["ALL"] = set(fb["sid"])
        else:
            continue
        for k, s in sets.items():
            cols = [x for x in s if x in nxt.columns]
            daily = nxt[cols].mean(axis=1, skipna=True).fillna(0.0)
            gross = float((1 + daily).prod() - 1)
            old = prev.get(k, set())
            turnover = 1.0 if not old else len(s - old) / max(len(s), 1)
            cmean = float(pd.to_numeric(cst.reindex(list(s)), errors="coerce").mean()) if len(s) else 0.0
            cmean = 0.0 if cmean != cmean else cmean
            row[k] = gross - turnover * cmean
            row[k + "_n"] = len(cols)
            row[k + "_turnover"] = turnover
            row[k + "_beta"] = float(fb.loc[fb["sid"].isin(s), "beta"].mean()) if k != "ALL" else float(fb["beta"].mean())
            prev[k] = s
        rows.append(row)
    M = pd.DataFrame(rows)
    M["date"] = pd.PeriodIndex(M["month"], freq="M").to_timestamp()
    return M, {"months": int(len(M)), "first_month": M["month"].iloc[0] if len(M) else None, "last_month": M["month"].iloc[-1] if len(M) else None}


def _basket_stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 6:
        return {}
    eq = (1 + r).cumprod()
    yrs = len(r) / 12.0
    cagr = float(eq.iloc[-1] ** (1 / yrs) - 1) if eq.iloc[-1] > 0 else -1.0
    vol = float(r.std(ddof=1) * math.sqrt(12))
    dd = float((eq / eq.cummax() - 1).min())
    return {"cagr": cagr, "vol": vol, "return_per_vol": cagr / vol if vol else None, "max_drawdown": dd, "months": int(len(r))}


BT_PLAN = [("LOWBETA-HIGHBETA|monthly", "LOWBETA", "HIGHBETA"), ("LOWBETA-ALL|monthly", "LOWBETA", "ALL"),
           ("LOWVOL-HIGHVOL|monthly", "LOWVOL", "HIGHVOL"), ("LOWVOL-ALL|monthly", "LOWVOL", "ALL")]


def bt1_results(counts_only: bool = False) -> dict:
    M, info = _bt_monthly()
    yr = M["date"].dt.year
    out = {}
    for key, a, b in BT_PLAN:
        d = (M[a] - M[b])
        cnt = {"events_dev": int((yr < SPLIT).sum()), "events_val": int((yr >= SPLIT).sum()), **info}
        if counts_only:
            out[key] = cnt
            continue
        res = {"dev": ts._stat(d[yr < SPLIT]), "val": ts._stat(d[yr >= SPLIT])}
        ext = dict(cnt)
        for per, sel in (("dev", yr < SPLIT), ("val", yr >= SPLIT)):
            ext[per] = {a: _basket_stats(M.loc[sel, a]), b: _basket_stats(M.loc[sel, b]),
                        "avg_beta_" + a: float(M.loc[sel, a + "_beta"].mean()), "avg_beta_" + b: float(M.loc[sel, b + "_beta"].mean()),
                        "avg_turnover_" + a: float(M.loc[sel, a + "_turnover"].mean())}
        res["extra"] = ext
        out[key] = res
    return out


# =============================================================================================================================== OS1: option spreads

def _short_leg(sp1, greeks, costs, sym, day, setup, d, K, steps, spot_in, m_in, spot_out, day_out, m_out, stopped, lot):
    """The SOLD further-out option of a debit spread: same type and expiry as the long ATM leg, `steps` listed strikes further out, its own previous-session
    IV, sold at entry and bought back at the exit, with sp1's half-spread model and india.costs option charges. Returns (net rupees, entry premium) or None."""
    typ = "CE" if d > 0 else "PE"
    listed = setup["listed"]
    i = int(np.abs(listed - K).argmin())
    j = i + steps if d > 0 else i - steps
    if j < 0 or j >= len(listed):
        return None
    K2 = float(listed[j])
    ks, ivs = setup[typ]
    if len(ks) == 0:
        return None
    iv = float(ivs[np.abs(ks - K2).argmin()])
    e, car = setup["expiry"], setup["carry"]
    bl = lambda S, t: float(greeks.black76(np.array([S * car]), np.array([K2]), np.array([t]), np.array([iv]), np.array([typ == "CE"]))[0][0])
    p_in = max(bl(spot_in, sp1._t_years(day, m_in, e)), 0.05)
    p_out = max(bl(spot_out, sp1._t_years(day_out, m_out, e)), 0.05)
    h_in = max(sp1.OPT_HALF[sym], 0.0025 * p_in)
    h_out = max(sp1.OPT_HALF[sym], 0.0025 * p_out) * (2.0 if stopped else 1.0)
    sell, buy = max(p_in - h_in, 0.0), p_out + h_out
    fees = costs.cost("options", "sell", sell * lot, day.year, when=day) + costs.cost("options", "buy", buy * lot, day_out.year, when=day_out)
    return (sell - buy) * lot - fees, p_in, K2


def _os_book():
    from india import ocstudy, sp1
    days_all, _specials = ocstudy._calendar()
    prv = {days_all[i]: days_all[i - 1] for i in range(1, len(days_all))}
    nxt = {days_all[i]: days_all[i + 1] for i in range(len(days_all) - 1)}
    index = ocstudy.load_index()
    pc = {}
    for sym, name in sp1.IDX.items():
        a = index[name]
        for i, d in enumerate(a["dates"]):
            pc[(sym, d)] = float(a["close"][i, -1])
    return sp1.OptionBook(sp1._chains(), prv, pc), nxt


def _os_compare(rows: pd.DataFrame, ob, nxt) -> pd.DataFrame:
    from india import costs, greeks, sp1
    out = []
    cache = {}
    for r in rows.itertuples(index=False):
        day = r.date if isinstance(r.date, dt.date) else pd.Timestamp(r.date).date()
        key = (r.index, day)
        if key not in cache:
            cache[key] = ob.setup(r.index, day)
        setup = cache[key]
        if setup is None or not (r.opt_prem_in == r.opt_prem_in):
            continue
        m_in = sp1.POINT_ENTRY[r.point]
        day_out = nxt.get(day) if r.next_day else day
        if day_out is None:
            continue
        m_out = 1 if r.next_day else int(r.exit_min)
        lot = float(r.lot)
        long_net, long_prem = float(r.opt_net_rs), float(r.opt_prem_in)
        rec = {"date": pd.Timestamp(day), "index": r.index, "point": r.point, "exit": r.exit, "dir": int(r.dir), "single_rs": long_net,
               "single_ret": long_net / (long_prem * lot) if long_prem > 0 else np.nan}
        for steps in (1, 2):
            s = _short_leg(sp1, greeks, costs, r.index, day, setup, int(r.dir), float(r.opt_K), steps, float(r.entry), m_in, float(r.exit_px), day_out, m_out,
                           bool(r.stopped), lot)
            if s is None:
                rec[f"spread{steps}_rs"] = rec[f"spread{steps}_ret"] = np.nan
                continue
            net_s, p2_in, _k2 = s
            debit = long_prem - p2_in
            rec[f"spread{steps}_rs"] = long_net + net_s
            rec[f"spread{steps}_ret"] = (long_net + net_s) / (debit * lot) if debit > 0 else np.nan
        out.append(rec)
    return pd.DataFrame(out)


def _os_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
    D = paths.data_dir()
    O = pd.read_parquet(D / "gold/studies/SP1_outcomes.parquet")
    O = O[O["point"].isin(["D1", "D2"]) & O["exit"].isin(["ATRSTOP", "T1515"]) & O["opt_net_rs"].notna()]
    O = O[pd.to_datetime(O["date"]) < CUT]
    st = pd.read_parquet(D / "gold/scenario/index_states.parquet", columns=["date", "index", "vix_prev"])
    st["date"] = pd.to_datetime(st["date"])
    ob, nxt = _os_book()
    C = _os_compare(O, ob, nxt)
    C = C.merge(st, on=["date", "index"], how="left")
    pt = pd.read_parquet(D / "gold/studies/SP1_policy_trades.parquet")
    pt = pt[pt["opt_net_rs"].notna() & (pd.to_datetime(pt["date"]) < CUT)]
    CP = _os_compare(pt, ob, nxt)
    return C, CP


def _monthly_diff(C: pd.DataFrame, a: str, b: str, sel: pd.Series) -> dict:
    x = C[sel].dropna(subset=[a, b])
    m = (x[a] - x[b]).groupby(x["date"].dt.to_period("M")).mean()
    return {"dev": ts._stat(m[[p.year < SPLIT for p in m.index]]), "val": ts._stat(m[[p.year >= SPLIT for p in m.index]]),
            "n_dev": int((x["date"].dt.year < SPLIT).sum()), "n_val": int((x["date"].dt.year >= SPLIT).sum())}


OS_PLAN = [("ALL|spread1|ret", "spread1_ret", "single_ret", False), ("ALL|spread2|ret", "spread2_ret", "single_ret", False),
           ("HIVIX|spread1|ret", "spread1_ret", "single_ret", True), ("HIVIX|spread2|ret", "spread2_ret", "single_ret", True),
           ("ALL|spread1|rs", "spread1_rs", "single_rs", False), ("HIVIX|spread1|rs", "spread1_rs", "single_rs", True)]


def os1_results(counts_only: bool = False) -> dict:
    if counts_only:
        O = pd.read_parquet(paths.data_dir() / "gold/studies/SP1_outcomes.parquet", columns=["date", "point", "exit", "opt_net_rs"])
        O = O[O["point"].isin(["D1", "D2"]) & O["exit"].isin(["ATRSTOP", "T1515"]) & O["opt_net_rs"].notna()]
        y = pd.to_datetime(O["date"]).dt.year
        return {"candidate_rows": {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())}}
    C, CP = _os_frame()
    out = {}
    for key, a, b, hv in OS_PLAN:
        sel = (C["vix_prev"] > 18) if hv else pd.Series(True, index=C.index)
        r = _monthly_diff(C, a, b, sel.fillna(False))
        x = C[sel.fillna(False)].dropna(subset=[a, b])
        ext = {"events_dev": r["n_dev"], "events_val": r["n_val"], "mean_" + a: float(x[a].mean()), "mean_" + b: float(x[b].mean()),
               "win_rate_" + a: float((x[a] > 0).mean()), "win_rate_" + b: float((x[b] > 0).mean())}
        xp = CP.dropna(subset=[a, b])
        ext["policy_trades_2017_2023"] = {"n": int(len(xp)), "mean_" + a: float(xp[a].mean()) if len(xp) else None, "mean_" + b: float(xp[b].mean()) if len(xp) else None,
                                          "sum_" + a: float(xp[a].sum()) if len(xp) else None, "sum_" + b: float(xp[b].sum()) if len(xp) else None}
        out[key] = {"dev": r["dev"], "val": r["val"], "extra": ext}
    return out


# =============================================================================================================================== CA1: corporate actions

def _ca_frame() -> pd.DataFrame:
    import duckdb
    P = _panel(["fwd20", "fwd60", "c"])
    b = pd.read_parquet(paths.data_dir() / "silver/corporate_actions/record_b.parquet", columns=["symbol", "ex_date", "kind", "amount"])
    b["ex_date"] = pd.to_datetime(b["ex_date"], errors="coerce")
    b = b[b["ex_date"].notna() & (b["ex_date"] < CUT)]
    files = [str(p) for p in (paths.data_dir() / "silver/cm_bhavcopy").glob("year=*/part.parquet") if int(p.parent.name.split("=")[1]) < 2024]
    div = b[b["kind"] == "DIVIDEND"].dropna(subset=["amount"])
    con = duckdb.connect()
    con.register("dv", div[["symbol", "ex_date"]].drop_duplicates())
    pcl = con.execute(f"""select c.symbol, c.date as ex_date, c.prev_close from read_parquet({files!r}, union_by_name=true) c
                          join dv on c.symbol = dv.symbol and cast(c.date as date) = cast(dv.ex_date as date) where c.series = 'EQ' and c.prev_close > 0""").df()
    con.close()
    pcl["ex_date"] = pd.to_datetime(pcl["ex_date"])
    div = div.merge(pcl.drop_duplicates(["symbol", "ex_date"]), on=["symbol", "ex_date"], how="inner")
    div = div[div["amount"] / div["prev_close"] >= 0.02]
    kinds = {"bonus_split": b[b["kind"].isin(["BONUS", "SPLIT", "BONUS+SPLIT"])], "buyback": b[b["kind"] == "BUYBACK"], "dividend_y2": div}
    key = pd.MultiIndex.from_frame(P[["symbol", "date"]])
    for k, e in kinds.items():
        ek = pd.MultiIndex.from_frame(e[["symbol", "ex_date"]].rename(columns={"ex_date": "date"}).drop_duplicates())
        P[k] = ts._cooldown(P, pd.Series(key.isin(ek), index=P.index), COOL)
    P["s5"] = ts.sample5(P)
    P["all"] = P["liq_rank"] <= 500
    return P


CA_PLAN = [("STK|bonus_split|fwd20", "bonus_split", "fwd20"), ("STK|bonus_split|fwd60", "bonus_split", "fwd60"),
           ("STK|buyback|fwd20", "buyback", "fwd20"), ("STK|buyback|fwd60", "buyback", "fwd60"), ("STK|dividend_y2|fwd20", "dividend_y2", "fwd20")]


def ca1_results(counts_only: bool = False) -> dict:
    P = _ca_frame()
    out = {}
    for key, ev, col in CA_PLAN:
        cnt = _counts(P["date"], P[ev] & P["all"])
        if counts_only:
            out[key] = cnt
            continue
        d = P[P["all"] & (P["s5"] | P[ev])]
        r = ts.level(d, d[ev], col)
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


# =============================================================================================================================== run, results pages

FUNCS = {"CP1": cp1_results, "VL1": vl1_results, "BT1": bt1_results, "OS1": os1_results, "CA1": ca1_results}


def check(study: str) -> dict:
    return FUNCS[study](counts_only=True)


def run(study: str) -> dict:
    s = spec(study)
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"{study}: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register(study, family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note=f"spec india/registrations/{study.lower()}_v1.json (written before the run)", bar_families=s["bar"].get("bar_families"), union_k=k)
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
    (paths.manifest_dir() / f"lab3_{study.lower()}.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    table(study, out)
    return out


TAKEAWAY: dict[str, list[str]] = {      # written after the runs of 27 Oct 2026, from the numbers in the tables below
    "CP1": [
        "**No candlestick pattern is a usable signal on liquid Indian stocks. Nothing passed the bar (z 3.27); the directions mostly match the textbook, but the "
        "effects are small and do not hold in both periods.**",
        "- **Hammer after a fall (14,079 events in 2000-17, 4,381 in 2018-23):** next 5 sessions +0.11% and +0.20% against ordinary days (REJECTED); next 20 sessions "
        "+0.62% (t 2.4) and +0.31% (t 0.8): INCONCLUSIVE, under the bar and fading.",
        "- **Bullish engulfing after a fall (9,052 / 3,046):** -0.13% and +0.16% over 5 sessions, +0.28% and +0.63% over 20: REJECTED.",
        "- **Bearish engulfing after a rise (19,498 / 6,478):** -0.42% (t -2.4) and -0.17% over 20 sessions: INCONCLUSIVE. **Doji after a rise (24,125 / 7,676):** "
        "-0.28% and -0.30%: INCONCLUSIVE. Both lean the textbook way, too weakly to use.",
        "- **As trades after costs (buy the next open, sell 20 sessions later):** hammer +1.56% and +0.93% a trade, bullish engulfing +1.21% and +1.28%, both "
        "INCONCLUSIVE; most of that is the market's own rise over 20 sessions, as the rows against ordinary days show.",
        "- **What Ananta does with this:** nothing changes. A hammer or an engulfing candle can be described on a chart; it is not a reason to buy or sell.",
    ],
    "VL1": [
        "**An expensive Nifty did come before weaker returns in 2003-2017, but there are too few independent periods to call it proven, and the P/E history has a "
        "method break in 2021. Every row is INCONCLUSIVE.**",
        "- **P/E in the top tenth of its history (705 days in 2003-17, 717 in Apr 2018-Mar 2021):** the next 60 sessions were 6.7% weaker than at other times in "
        "2003-17 (t -3.0, 21 quarters) and 9.1% weaker in 2018-21 (only 3 quarters). Over the next 250 sessions: 31.9% weaker in 2003-17 (8 years, dominated by the 2008 crash).",
        "- **Cheap Nifty:** bottom-tenth P/E +13.6% over 60 sessions (7 quarters, all before 2018); top-tenth dividend yield +6.8% (4 quarters); neither happened in 2018-23.",
        "- **P/B top tenth:** -2.0% (t -0.5); **dividend yield bottom tenth:** -3.1% (t -0.9).",
        "- **Why no verdict:** valuation regimes last months to years, so 20 years hold only a handful of independent episodes; P/E and P/B switched to consolidated "
        "earnings in March 2021, so they are used only to then.",
        "- **What Ananta does with this:** it can say where the Nifty's P/E sits against its history and that expensive markets have tended to do worse, without "
        "calling it a tested signal. No rule changes.",
    ],
    "BT1": [
        "**Low-beta and low-volatility stocks did not earn more per month on average (all four rows REJECTED), but they compounded better with about half the "
        "swings and much smaller falls (reported, not tested).**",
        "- **Monthly net difference (153 months in 2004-17, 72 in 2018-23):** low beta minus high beta -0.05% and +0.62% a month; low beta minus the whole liquid 250 "
        "+0.00% and +0.25%; low volatility minus high volatility +0.11% and +0.84%; low volatility minus all -0.28% and +0.12%. None significant.",
        "- **Whole-period picture, net of costs:** the low-beta fifth (average beta 0.55) grew 19.0% a year in 2004-17 and 15.7% in 2018-23, against 12.3% and 2.3% "
        "for the high-beta fifth (beta 1.6) and 16.5% and 10.6% for the whole liquid 250; volatility 23% and 16% against 44% and 35%; worst fall -64% and -21% "
        "against -76% and -73%. The low-volatility fifth: 15.7% and 14.0% a year, worst fall -56% and -24%.",
        "- **Why the two pictures differ:** the high-risk baskets' big swings drag their compounded growth down even when their average month is similar.",
        "- **What Ananta does with this:** beta is a risk measure, not a return signal. It can say a holding is high-beta (swings harder than the Nifty) and that the calm "
        "fifth compounded better here; no rule changes.",
    ],
    "OS1": [
        "**For Ananta's kind of trade (an intraday index move), a debit spread was much worse than buying the single option: OPPOSITE in development and validation.**",
        "- **Candidate SP1 trades, entry 15 or 30 minutes after the open, ATR-stop or 15:15 exit (11,552 in 2015-17, about 23,450 in 2018-23):** the single at-the-money "
        "option made +4.1% a trade on its premium; selling the next strike out made it -18.5% a trade on the net debit (spread1), selling two strikes out -8.6% (spread2). "
        "In rupees per lot: -232 against +172 (2015-17 difference -283, t -15.5; 2018-23 -470, t -12.0). Win rate 25% against 44%.",
        "- **When India VIX was above 18:** the same, -19.5% against +4.5% a trade; INCONCLUSIVE only because 2015-17 holds just 15 high-VIX months.",
        "- **Why:** on a same-day index trade the option moves only a little, so the sold option takes away much of the gain while adding a second set of bid-ask "
        "spreads and charges on a smaller debit. The cheaper premium does not make up for it. SP1's own policy trades 2017-23 (descriptive): single +4.7%, spread1 "
        "-19.0%, spread2 -7.9% a trade.",
        "- **What Ananta does with this:** the options line keeps one plain lot. A spread is a tool for multi-day views with a target, which this study did not test.",
    ],
    "CA1": [
        "**Corporate actions did not come before better returns. After a bonus or split ex-date, stocks did WORSE than ordinary days (OPPOSITE); large dividends and "
        "buybacks showed nothing.**",
        "- **Bonus or split (321 ex-dates in 2000-17, 119 in 2018-23, panel stocks):** the next 20 sessions from the day after the ex-date were 3.8% (t -3.9) and 6.0% "
        "(t -6.2) weaker than ordinary days; the next 60 sessions 4.1% and 3.3% weaker: OPPOSITE. The stock had typically run up into the event (median +1.4% at the "
        "ex-date open). The price adjustment was checked: no artificial jumps.",
        "- **Buyback (32 / 95 ex-dates):** -1.3% and -0.4% over 20 sessions, -4.4% and -1.1% over 60: INCONCLUSIVE (too few in 2000-17).",
        "- **Dividend of 2% or more of the price (715 / 429):** +1.1% and +0.2% over 20 sessions: REJECTED.",
        "- **The limit:** the free history has ex-dates, not announcement dates, so the reaction to the news itself is untested.",
        "- **What Ananta does with this:** a bonus or split is no reason to buy; the record says the run-up tends to reverse after the ex-date. No rule changes.",
    ],
}


def _f(x, pct: bool = True) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{100 * x:+.2f}%" if pct else f"{x:+.2f}"


def table(study: str, out: dict | None = None) -> Path:
    if out is None:
        out = json.loads((paths.manifest_dir() / f"lab3_{study.lower()}.json").read_text())
    s = spec(study)
    rs = study == "OS1"
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
        pct = not (rs and r["variant"].endswith("|rs"))
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else '-'} | {r['verdict']} | {_f(d[0], pct)} | {_f(d[1], False)} | {d[2]} | {_f(v[0], pct)} | {_f(v[1], False)} | {v[2]} | "
                 f"{e.get('events_dev', 'n/a')} / {e.get('events_val', 'n/a')} |")
    if study == "BT1":
        L += ["", "## The baskets, whole period (net of costs)", "", "| comparison | period | basket | CAGR | volatility | CAGR / volatility | max drawdown | avg beta |", "|---|---|---|---|---|---|---|---|"]
        for r in out["rows"]:
            e = r["extra"] or {}
            a, b = r["variant"].split("|")[0].split("-")
            for per in ("dev", "val"):
                for k in (a, b):
                    x = (e.get(per) or {}).get(k) or {}
                    L.append(f"| {r['variant']} | {per} | {k} | {_f(x.get('cagr'))} | {_f(x.get('vol'))} | {_f(x.get('return_per_vol'), False)} | {_f(x.get('max_drawdown'))} | "
                             f"{_f((e.get(per) or {}).get('avg_beta_' + k), False)} |")
    if study == "OS1":
        L += ["", "## Means per trade and SP1's policy trades (descriptive)", "", "| variant | spread mean | single mean | spread win rate | single win rate | policy trades n | policy spread mean | policy single mean |",
              "|---|---|---|---|---|---|---|---|"]
        for r in out["rows"]:
            e = r["extra"] or {}
            a = r["variant"].split("|")[1] + ("_ret" if r["variant"].endswith("ret") else "_rs")
            b = "single_ret" if r["variant"].endswith("ret") else "single_rs"
            pct = r["variant"].endswith("ret")
            p = e.get("policy_trades_2017_2023") or {}
            L.append(f"| {r['variant']} | {_f(e.get('mean_' + a), pct)} | {_f(e.get('mean_' + b), pct)} | {_f(e.get('win_rate_' + a))} | {_f(e.get('win_rate_' + b))} | "
                     f"{p.get('n')} | {_f(p.get('mean_' + a), pct)} | {_f(p.get('mean_' + b), pct)} |")
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
        for st in studies_:
            o = run(st)
            for r in o["rows"]:
                print(st, r["variant"], r["verdict"], r["dev"], r["val"], (r["extra"] or {}).get("events_dev"), (r["extra"] or {}).get("events_val"), flush=True)
    elif cmd == "table":
        for st in studies_:
            print(table(st))
    else:
        print(__doc__)
