"""Optionables cards on end-of-day F&O files (registered in india/teachers.py; this file holds the tests).

Data: silver fo_bhavcopy (open, high, low, close, settle, open interest, change in OI per contract), Nifty and Bank Nifty options and index futures,
2003-2023 (the index day file starts 2003). Strikes within 15% of the index close are loaded (OI cards: the biggest-OI strikes sit well inside that).
Settlement and close prices are not tradable quotes: every leg pays a 0.4% half-spread (at least Rs 0.05) plus Zerodha charges; one lot; P&L as a
share of a Rs 50,000 book. Expiry settlement: the expiring future's settlement for monthly expiries, the index close for weekly ones (labelled estimate,
india/fstudies._settle_at_expiry). Opens: the bhavcopy open of a contract that traded that day.
"""
from __future__ import annotations

import math
from functools import cached_property

import duckdb
import numpy as np
import pandas as pd

from india import costs, fstudies, paths
from india import teachers as T
from india import teachers_stock as ts

BOOK = 50_000.0
IDXN = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
SYMS = ("NIFTY", "BANKNIFTY")
hs = fstudies._hs


def fee(side: str, value: float, d) -> float:
    return costs.cost("options", side, float(value), pd.Timestamp(d).year)


class FO:
    @cached_property
    def ix(self) -> dict:
        ts.index_panel()
        ohl, piv = ts._P["index_ohl"], ts._P["index"]
        out = {}
        for s, n in IDXN.items():
            d = pd.DataFrame({"o": ohl["open"][n], "h": ohl["high"][n], "l": ohl["low"][n], "c": piv[n]}).dropna(subset=["c"])
            d.loc[(d["o"] <= 0) | (d["o"] == d["c"].shift(1)), "o"] = np.nan     # early Kite rows repeat the prior close as the open: not a real open
            out[s] = d
        out["VIX"] = piv["INDIA VIX"]
        return out

    @cached_property
    def fut(self) -> pd.DataFrame:
        con = duckdb.connect()
        f = con.execute(f"select date, symbol, expiry, settle, lot_est from read_parquet({fstudies._files('fo_bhavcopy')!r}, union_by_name=true) "
                        f"where instrument = 'FUTIDX' and symbol in ('NIFTY','BANKNIFTY')").df()
        con.close()
        f["date"], f["expiry"] = pd.to_datetime(f["date"]), pd.to_datetime(f["expiry"])
        return f

    @cached_property
    def se(self) -> pd.Series:
        return fstudies._settle_at_expiry(self.fut)

    @cached_property
    def lot(self) -> dict:
        lots = fstudies._lot(self.fut)
        out = {}
        for s in SYMS:
            x = lots.xs(s, level=0) if s in lots.index.get_level_values(0) else pd.Series(dtype=float)
            x.index = pd.to_datetime(x.index)
            out[s] = x[~x.index.duplicated()].reindex(self.sessions).ffill().bfill()
        return out

    @cached_property
    def ch(self) -> pd.DataFrame:
        ixc = pd.concat([pd.DataFrame({"symbol": s, "date": self.ix[s].index, "spot": self.ix[s]["c"].values}) for s in SYMS])
        con = duckdb.connect()
        con.register("ixc", ixc)
        df = con.execute(f"""select b.date, b.symbol, b.expiry, b.strike, b.opt_type, b.open, b.high, b.low, b.close, b.settle, b.open_interest as oi,
                                    b.chg_oi, b.volume
                             from read_parquet({fstudies._files('fo_bhavcopy')!r}, union_by_name=true) b
                             join ixc on ixc.symbol = b.symbol and ixc.date = cast(b.date as timestamp)
                             where b.instrument = 'OPTIDX' and b.symbol in ('NIFTY','BANKNIFTY') and abs(b.strike / ixc.spot - 1) <= 0.15
                               and cast(b.date as timestamp) <= timestamp '2023-12-31'""").df()
        con.close()
        df["date"], df["expiry"] = pd.to_datetime(df["date"]), pd.to_datetime(df["expiry"])
        df = df[df["expiry"] >= df["date"]]
        return df.sort_values(["symbol", "expiry", "date", "strike"]).reset_index(drop=True)

    @cached_property
    def groups(self) -> dict:
        return {k: v for k, v in self.ch.groupby(["symbol", "expiry", "date"], sort=False)}

    @cached_property
    def sessions(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(sorted(self.ch["date"].unique()))

    @cached_property
    def expiries(self) -> dict:
        return {s: [pd.Timestamp(x) for x in sorted(self.ch.loc[self.ch["symbol"] == s, "expiry"].unique())] for s in SYMS}

    def weekly(self, s: str) -> list:
        e = self.expiries[s]
        return [x for i, x in enumerate(e) if i > 0 and (x - e[i - 1]).days <= 8]

    def monthly(self, s: str) -> list:
        e = pd.Series(self.expiries[s])
        return list(e.groupby([e.dt.year, e.dt.month]).max())

    def chain(self, s, e, d) -> pd.DataFrame | None:
        return self.groups.get((s, pd.Timestamp(e), pd.Timestamp(d)))

    def shift(self, d, k: int = 1):
        i = self.sessions.searchsorted(pd.Timestamp(d))
        if i >= len(self.sessions) or self.sessions[i] != pd.Timestamp(d):
            return None
        j = i + k
        return self.sessions[j] if 0 <= j < len(self.sessions) else None

    def next_expiry(self, s, d, min_days: int = 1):
        for e in self.expiries[s]:
            if (e - pd.Timestamp(d)).days >= min_days:
                return e
        return None

    def spot(self, s, d, col: str = "c"):
        try:
            v = self.ix[s].at[pd.Timestamp(d), col]
            return float(v) if v == v else None
        except KeyError:
            return None

    def vix(self, d):
        try:
            v = self.ix["VIX"].at[pd.Timestamp(d)]
            return float(v) if v == v else None
        except KeyError:
            return None


_F: dict = {}


def F() -> FO:
    if "fo" not in _F:
        _F["fo"] = FO()
    return _F["fo"]


def _pair(c: pd.DataFrame, target: float, col: str):
    """Strike with both a call and a put priced (> 0 in col) nearest the target: (strike, call, put)."""
    w = c[c[col] > 0].pivot_table(index="strike", columns="opt_type", values=col, aggfunc="last").dropna()
    if w.empty or not {"CE", "PE"} <= set(w.columns):
        return None
    k = float(w.index[np.argmin(np.abs(w.index.values - target))])
    return k, float(w.loc[k, "CE"]), float(w.loc[k, "PE"])


def _leg(c: pd.DataFrame, typ: str, target: float, col: str, gt: float | None = None, lt: float | None = None):
    """One option of a type nearest the target strike, priced (> 0) in col; optionally strictly above gt or below lt: (strike, price)."""
    x = c[(c["opt_type"] == typ) & (c[col] > 0)]
    if gt is not None:
        x = x[x["strike"] > gt]
    if lt is not None:
        x = x[x["strike"] < lt]
    if x.empty:
        return None
    i = int(np.argmin(np.abs(x["strike"].values - target)))
    return float(x["strike"].values[i]), float(x[col].values[i])


def _price(c: pd.DataFrame, typ: str, k: float, col: str):
    x = c[(c["opt_type"] == typ) & (c["strike"] == k) & (c[col] > 0)]
    return float(x[col].iloc[0]) if len(x) else None


def _abs(df: pd.DataFrame, col: str = "ret") -> dict:
    df = df.dropna(subset=[col]).reset_index(drop=True)
    r = ts.absolute(df, pd.Series(True, index=df.index), col)
    if "pnl" in df and len(df):
        cum = df.sort_values("date")["pnl"].cumsum()
        r["extra"].update({"trades": int(len(df)), "win_share": float((df["pnl"] > 0).mean()), "mean_inr": float(df["pnl"].mean()),
                           "worst_inr": float(df["pnl"].min()), "max_drawdown_inr": float((cum - cum.cummax()).min()),
                           "first": str(df["date"].min().date()), "last": str(df["date"].max().date())})
    return r


def _ms(df: pd.DataFrame, on, col: str, h: int = 5, min_on: int = 1, min_off: int = 1) -> dict:
    df = df.reset_index(drop=True)
    on = pd.Series(np.asarray(on, dtype=bool), index=df.index)
    return ts.msplit(df, on, col, h=h, min_on=min_on, min_off=min_off)


def _oi_band(c: pd.DataFrame, spot: float):
    """(biggest put-OI strike below spot, biggest call-OI strike above spot) or None."""
    p = c[(c["opt_type"] == "PE") & (c["strike"] < spot) & (c["oi"] > 0)]
    q = c[(c["opt_type"] == "CE") & (c["strike"] > spot) & (c["oi"] > 0)]
    if p.empty or q.empty:
        return None
    return float(p.loc[p["oi"].idxmax(), "strike"]), float(q.loc[q["oi"].idxmax(), "strike"])


# ------------------------------------------------------------------------------------------------------------ weekly straddles (H16, H41)
def weekly_straddles(s: str) -> pd.DataFrame:
    """H16 entries: ATM straddle at the open of the first session of each weekly expiry cycle, held to settlement; naked and winged; daily marks for H41."""
    fo = F()
    key = ("wk", s)
    if key in _F:
        return _F[key]
    rows = []
    allx = fo.expiries[s]
    for e in fo.weekly(s):
        prev = allx[allx.index(e) - 1]
        start = fo.shift(prev, 1) if prev in fo.sessions else None
        if start is None or start >= e or (s, e) not in fo.se.index:
            continue
        o = fo.spot(s, start, "o")
        c0 = fo.chain(s, e, start)
        if o is None or c0 is None:
            continue
        pr = _pair(c0, o, "open")
        lot = fo.lot[s].get(start)
        if pr is None or not lot or lot != lot:
            continue
        k, ce, pe = pr
        raw = ce + pe
        credit = (ce - hs(ce)) + (pe - hs(pe))
        S = float(fo.se.loc[(s, e)])
        naked = (credit - abs(S - k)) * lot - fee("sell", raw * lot, start)
        wc, wp = _leg(c0, "CE", k + raw, "open", gt=k), _leg(c0, "PE", k - raw, "open", lt=k)
        winged = None
        if wc and wp:
            cost = (wc[1] + hs(wc[1])) + (wp[1] + hs(wp[1]))
            pay = max(S - wc[0], 0) + max(wp[0] - S, 0)
            winged = naked + (pay - cost) * lot - fee("buy", (wc[1] + wp[1]) * lot, start)
        # daily marks (settle) from the session after entry to the expiry eve, for early profit-taking
        marks = []
        d = fo.shift(start, 1)
        while d is not None and d < e:
            cd = fo.chain(s, e, d)
            if cd is not None:
                pc, pp = _price(cd, "CE", k, "settle"), _price(cd, "PE", k, "settle")
                if pc is not None and pp is not None:
                    marks.append((d, pc, pp))
            d = fo.shift(d, 1)
        rows.append({"symbol": s, "expiry": e, "date": start, "strike": k, "raw": raw, "credit": credit, "lot": lot, "S": S, "naked": naked, "winged": winged,
                     "marks": marks, "n_sess": int(((fo.sessions >= start) & (fo.sessions <= e)).sum())})
    df = pd.DataFrame(rows)
    _F[key] = df
    return df


@T.test("OPT-H16")
def _(P):
    out = {}
    for s in SYMS:
        w = weekly_straddles(s)
        if w.empty:
            continue
        a = w.assign(pnl=w["naked"], ret=w["naked"] / BOOK)
        out[f"{s}|naked"] = _abs(a)
        b = w.dropna(subset=["winged"])
        b = b.assign(pnl=b["naked"] - b["winged"], ret=(b["naked"] - b["winged"]) / BOOK)
        r = _abs(b)
        cn, cw = b["naked"].cumsum(), b["winged"].cumsum()
        r["extra"].update({"naked_total_inr": float(b["naked"].sum()), "winged_total_inr": float(b["winged"].sum()),
                           "naked_max_dd_inr": float((cn - cn.cummax()).min()), "winged_max_dd_inr": float((cw - cw.cummax()).min()),
                           "naked_worst_inr": float(b["naked"].min()), "winged_worst_inr": float(b["winged"].min())})
        out[f"{s}|naked_minus_winged"] = r
    return out


@T.test("OPT-H41")
def _(P):
    out = {}
    for s in SYMS:
        w = weekly_straddles(s)
        for f in (0.65, 0.75, 0.90):
            rows = []
            for r in w.itertuples():
                early = r.naked
                for d, pc, pp in r.marks:
                    buy = pc + pp + hs(pc) + hs(pp)
                    if buy <= (1 - f) * r.raw:
                        early = (r.credit - buy) * r.lot - fee("sell", r.raw * r.lot, r.date) - fee("buy", (pc + pp) * r.lot, d)
                        break
                rows.append({"date": r.date, "pnl": early - r.naked, "ret": (early - r.naked) / BOOK})
            if rows:
                out[f"{s}|take{int(f * 100)}"] = _abs(pd.DataFrame(rows))
    return out


# ------------------------------------------------------------------------------------------------------------ expiry eve strangle (H17)
@T.test("OPT-H17")
def _(P):
    fo, out = F(), {}
    specs = {"BANKNIFTY|200pt": ("BANKNIFTY", "pts", 200, None), "BANKNIFTY|0.7pct": ("BANKNIFTY", "pct", 0.007, None),
             "BANKNIFTY|200pt_wings550": ("BANKNIFTY", "pts", 200, 550), "NIFTY|0.7pct": ("NIFTY", "pct", 0.007, None)}
    for name, (s, kind, dist, wing) in specs.items():
        rows = []
        for e in fo.expiries[s]:
            eve = fo.shift(e, -1) if e in fo.sessions else None
            if eve is None:
                continue
            sp = fo.spot(s, eve)
            c0, c1 = fo.chain(s, e, eve), fo.chain(s, e, e)
            lot = fo.lot[s].get(eve)
            if sp is None or c0 is None or c1 is None or not lot or lot != lot:
                continue
            up, dn = (sp + dist, sp - dist) if kind == "pts" else (sp * (1 + dist), sp * (1 - dist))
            lc, lp = _leg(c0, "CE", up, "settle", gt=sp), _leg(c0, "PE", dn, "settle", lt=sp)
            if not lc or not lp:
                continue
            xc, xp = _price(c1, "CE", lc[0], "open"), _price(c1, "PE", lp[0], "open")
            if xc is None or xp is None:
                continue
            pnl = ((lc[1] - hs(lc[1])) + (lp[1] - hs(lp[1])) - (xc + hs(xc)) - (xp + hs(xp))) * lot - fee("sell", (lc[1] + lp[1]) * lot, eve) - fee("buy", (xc + xp) * lot, e)
            if wing:
                wc, wp = _leg(c0, "CE", sp + wing, "settle", gt=lc[0]), _leg(c0, "PE", sp - wing, "settle", lt=lp[0])
                if not wc or not wp:
                    continue
                o_ix = fo.spot(s, e, "o") or sp
                yc = _price(c1, "CE", wc[0], "open") or max(o_ix - wc[0], 0.05)
                yp = _price(c1, "PE", wp[0], "open") or max(wp[0] - o_ix, 0.05)
                pnl += ((yc - hs(yc)) + (yp - hs(yp)) - (wc[1] + hs(wc[1])) - (wp[1] + hs(wp[1]))) * lot - fee("buy", (wc[1] + wp[1]) * lot, eve) - fee("sell", (yc + yp) * lot, e)
            rows.append({"date": eve, "pnl": pnl, "ret": pnl / BOOK})
        df = pd.DataFrame(rows)
        if df.empty:
            continue
        r = _abs(df)
        yr = df.groupby(df["date"].dt.year)["pnl"].sum()
        r["extra"].update({"mean_inr_per_year": float(yr.mean()), "years": int(len(yr))})
        out[name] = r
    return out


# ------------------------------------------------------------------------------------------------------------ VIX and the straddle (H20, H21)
def _k5() -> pd.DataFrame:
    p = paths.gold() / "studies" / "F01_straddles.parquet"
    x = pd.read_parquet(p)
    x = x[x["k"] == 5].copy()
    x["date"] = pd.to_datetime(x["date"])
    fo = F()
    v = fo.ix["VIX"]
    x["vix"] = v.reindex(x["date"]).values
    x["vix_wk"] = (v / v.shift(5) - 1).reindex(x["date"]).values
    x["vix_5ago"] = v.shift(5).reindex(x["date"]).values
    return x.dropna(subset=["vix"])


@T.test("OPT-H20")
def _(P):
    x, out = _k5(), {}
    for s in SYMS:
        y = x[x["symbol"] == s].reset_index(drop=True)
        out[f"{s}|vix_lt14"] = _ms(y, y["vix"] < 14, "ret_on_book")
        out[f"{s}|vix_gt20"] = _ms(y, y["vix"] > 20, "ret_on_book")
    return out


@T.test("OPT-H21")
def _(P):
    x, out = _k5(), {}
    for s in SYMS:
        y = x[x["symbol"] == s].dropna(subset=["vix_wk"]).reset_index(drop=True)
        out[f"{s}|vix_rising"] = _ms(y, y["vix_wk"] > 0, "ret_on_book")
        out[f"{s}|vix_rising_from_low"] = _ms(y, (y["vix_wk"] >= 0.10) & (y["vix_5ago"] < 14), "ret_on_book")
    return out


# ------------------------------------------------------------------------------------------------------------ overnight through events (H24)
@T.test("OPT-H24")
def _(P):
    fo, out = F(), {}
    ev = pd.read_parquet(paths.data_dir() / "silver/events/events.parquet")
    ev = ev[(ev["known_beforehand"] == "scheduled") & ev["category"].isin(["rbi_policy", "election", "union_budget", "world_macro"])]
    ev_days = set(pd.to_datetime(ev["first_tradable_session"]).dropna())
    for s in SYMS:
        rows = []
        for d in fo.sessions:
            n = fo.shift(d, 1)
            if n is None:
                continue
            e = fo.next_expiry(s, n, min_days=1)
            sp = fo.spot(s, d)
            if e is None or sp is None:
                continue
            c0, c1 = fo.chain(s, e, d), fo.chain(s, e, n)
            lot = fo.lot[s].get(d)
            if c0 is None or c1 is None or not lot or lot != lot:
                continue
            pr = _pair(c0, sp, "settle")
            if pr is None:
                continue
            k, ce, pe = pr
            xc, xp = _price(c1, "CE", k, "open"), _price(c1, "PE", k, "open")
            if xc is None or xp is None:
                continue
            pnl = ((ce - hs(ce)) + (pe - hs(pe)) - (xc + hs(xc)) - (xp + hs(xp))) * lot - fee("sell", (ce + pe) * lot, d) - fee("buy", (xc + xp) * lot, n)
            rows.append({"date": d, "pnl": pnl, "ret": pnl / BOOK, "event": n in ev_days})
        df = pd.DataFrame(rows)
        r = _ms(df, df["event"], "ret", h=1, min_on=1, min_off=5)
        r["extra"].update({"event_nights": int(df["event"].sum()), "nights": int(len(df))})
        out[f"{s}|event_nights"] = r
    return out


# ------------------------------------------------------------------------------------------------------------ open interest (H25-H32)
@T.test("OPT-H25")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        for k in (5, 1):
            rows = []
            for e in fo.expiries[s]:
                if (s, e) not in fo.se.index or e not in fo.sessions:
                    continue
                d = fo.shift(e, -k)
                sp = fo.spot(s, d) if d is not None else None
                c = fo.chain(s, e, d) if d is not None else None
                if sp is None or c is None:
                    continue
                b = _oi_band(c, sp)
                if b is None:
                    continue
                S, w = float(fo.se.loc[(s, e)]), b[1] - b[0]
                inside = float(b[0] <= S <= b[1])
                eq = float(sp - w / 2 <= S <= sp + w / 2)
                rows.append({"date": d, "diff": inside - eq, "inside": inside, "eq": eq, "above_call": float(S > b[1]), "above_eq": float(S > sp + w / 2)})
            df = pd.DataFrame(rows)
            r = _abs(df, "diff")
            r["extra"].update({k2: float(df[k2].mean()) for k2 in ("inside", "eq", "above_call", "above_eq")})
            out[f"{s}|k{k}"] = r
    return out


def _daily_oi(s: str) -> pd.DataFrame:
    """Per session: the nearest expiry after today, its OI band at the close, PCR, top-strike share, near-the-money OI change, and next-day index outcomes."""
    key = ("daily", s)
    if key in _F:
        return _F[key]
    fo = F()
    ix = fo.ix[s]
    rows = []
    for d in fo.sessions:
        n = fo.shift(d, 1)
        e = fo.next_expiry(s, d, min_days=1)
        sp = fo.spot(s, d)
        c = fo.chain(s, e, d) if e is not None else None
        if n is None or sp is None or c is None:
            continue
        b = _oi_band(c, sp)
        put_oi, call_oi = c.loc[c["opt_type"] == "PE", "oi"].sum(), c.loc[c["opt_type"] == "CE", "oi"].sum()
        by_k = c.groupby("strike")["oi"].sum()
        near = c[(c["strike"] / sp - 1).abs() <= 0.02]
        rows.append({"date": d, "next": n, "spot": sp, "kp": b[0] if b else np.nan, "kc": b[1] if b else np.nan,
                     "pcr": put_oi / call_oi if call_oi > 0 else np.nan, "top_share": by_k.max() / by_k.sum() if by_k.sum() > 0 else np.nan,
                     "call_chg": near.loc[near["opt_type"] == "CE", "chg_oi"].sum(), "put_chg": near.loc[near["opt_type"] == "PE", "chg_oi"].sum()})
    df = pd.DataFrame(rows).set_index("date")
    o, h, l, c_ = ix["o"], ix["h"], ix["l"], ix["c"]
    nxt = pd.Series(df["next"].values, index=df.index)
    df["h1"], df["l1"], df["o1"], df["c1"] = h.reindex(nxt).values, l.reindex(nxt).values, o.reindex(nxt).values, c_.reindex(nxt).values
    pos = ix.index.get_indexer(nxt)
    c5 = c_.shift(-4)
    df["c5"] = c5.reindex(nxt).values
    df["h5"] = h[::-1].rolling(5, min_periods=5).max()[::-1].reindex(nxt).values
    df["l5"] = l[::-1].rolling(5, min_periods=5).min()[::-1].reindex(nxt).values
    df["r1"] = df["c1"] / df["o1"] - 1
    df["r5"] = df["c5"] / df["o1"] - 1
    df["rng1"] = (df["h1"] - df["l1"]) / df["spot"]
    df["rng5"] = (df["h5"] - df["l5"]) / df["spot"]
    w = df["kc"] - df["kp"]
    df["inside1"] = ((df["l1"] >= df["kp"]) & (df["h1"] <= df["kc"])).astype(float).where(w.notna() & df["h1"].notna())
    df["eq1"] = ((df["l1"] >= df["spot"] - w / 2) & (df["h1"] <= df["spot"] + w / 2)).astype(float).where(w.notna() & df["h1"].notna())
    df["diff1"] = df["inside1"] - df["eq1"]
    df["vix"] = fo.ix["VIX"].reindex(df.index).values
    df = df.reset_index()
    _F[key] = df
    return df


@T.test("OPT-H26")
def _(P):
    out = {}
    for s in SYMS:
        df = _daily_oi(s)
        r = _abs(df, "diff1")
        r["extra"].update({"inside": float(df["inside1"].mean()), "equal_width": float(df["eq1"].mean())})
        out[s] = r
    return out


@T.test("OPT-H27")
def _(P):
    out = {}
    for s in SYMS:
        df = _daily_oi(s).dropna(subset=["vix", "inside1"])
        out[f"{s}|vix_ge20"] = _ms(df, df["vix"] >= 20, "inside1", h=1, min_on=1, min_off=5)
    return out


@T.test("OPT-H28")
def _(P):
    out = {}
    for s in SYMS:
        df = _daily_oi(s).dropna(subset=["pcr"])
        conds = {"a_gt1.2": df["pcr"] > 1.2, "b_lt0.5": df["pcr"] < 0.5, "c_lt0.7": df["pcr"] < 0.7}
        for name, on in conds.items():
            for h in ((1, 5) if s == "NIFTY" else (5,)):
                out[f"{s}|{name}|d{h}"] = _ms(df.dropna(subset=[f"r{h}"]), on[df[f"r{h}"].notna()], f"r{h}", h=h, min_on=1, min_off=5)
    return out


@T.test("OPT-H29")
def _(P):
    out = {}
    for s in SYMS:
        df = _daily_oi(s).dropna(subset=["pcr", "top_share"]).reset_index(drop=True)
        med = df["top_share"].rolling(250, min_periods=60).median().shift(1)
        on = df["pcr"].between(0.85, 1.15) & (df["top_share"] >= med)
        for h in ((1, 5) if s == "NIFTY" else (1,)):
            ok = df[f"rng{h}"].notna()
            out[f"{s}|d{h}"] = _ms(df[ok], on[ok], f"rng{h}", h=h, min_on=1, min_off=5)
    return out


@T.test("OPT-H30")
def _(P):
    out = {}
    for s in SYMS:
        df = _daily_oi(s).reset_index(drop=True)
        bull = (df["call_chg"] < 0) & (df["put_chg"] > 0)
        bear = (df["call_chg"] > 0) & (df["put_chg"] < 0)
        for name, on in (("bull", bull), ("bear", bear)):
            for h in ((1, 5) if s == "NIFTY" else (5,)):
                ok = df[f"r{h}"].notna()
                out[f"{s}|{name}|d{h}"] = _ms(df[ok], on[ok], f"r{h}", h=h, min_on=1, min_off=5)
    return out


@T.test("OPT-H31")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        for k in (1, 3):
            rows = []
            for e in fo.expiries[s]:
                if (s, e) not in fo.se.index or e not in fo.sessions:
                    continue
                d = fo.shift(e, -k)
                sp = fo.spot(s, d) if d is not None else None
                c = fo.chain(s, e, d) if d is not None else None
                if sp is None or c is None or c["oi"].sum() <= 0:
                    continue
                by_k = c.groupby("strike")["oi"].sum()
                kmax = float(by_k.idxmax())
                katm = float(by_k.index[np.argmin(np.abs(by_k.index.values - sp))])
                S = float(fo.se.loc[(s, e)])
                rows.append({"date": d, "diff": (abs(S - kmax) - abs(S - katm)) / sp, "same_strike": float(kmax == katm)})
            df = pd.DataFrame(rows)
            r = _abs(df, "diff")
            r["extra"]["max_oi_is_atm_share"] = float(df["same_strike"].mean())
            out[f"{s}|k{k}"] = r
    return out


@T.test("OPT-H32")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        rows = []
        wk = fo.weekly(s)
        allx = fo.expiries[s]
        for e1 in wk:
            i = allx.index(e1)
            if i + 1 >= len(allx) or e1 not in fo.sessions:
                continue
            e2 = allx[i + 1]
            a = fo.shift(e1, 1)
            if (s, e2) not in fo.se.index or a is None or a >= e2:
                continue
            res = []
            for d in (e1, a):
                sp, c = fo.spot(s, d), fo.chain(s, e2, d)
                b = _oi_band(c, sp) if (sp is not None and c is not None) else None
                res.append(b)
            if None in res:
                continue
            S = float(fo.se.loc[(s, e2)])
            on_day, after = float(res[0][0] <= S <= res[0][1]), float(res[1][0] <= S <= res[1][1])
            rows.append({"date": e1, "diff": after - on_day, "after": after, "on_day": on_day})
        df = pd.DataFrame(rows)
        r = _abs(df, "diff")
        r["extra"].update({"after_rate": float(df["after"].mean()), "on_day_rate": float(df["on_day"].mean())})
        out[s] = r
    return out


# ------------------------------------------------------------------------------------------------------------ structures and pricing (H42, H45-H47, H57-H59)
@T.test("OPT-H42")
def _(P):
    fo, out = F(), {}
    frames = {}
    for s in SYMS:
        rows = []
        for e in fo.monthly(s):
            if (s, e) not in fo.se.index or e not in fo.sessions:
                continue
            d = fo.shift(e, -20)
            sp = fo.spot(s, d) if d is not None else None
            c = fo.chain(s, e, d) if d is not None else None
            lot = fo.lot[s].get(d) if d is not None else None
            if sp is None or c is None or not lot or lot != lot:
                continue
            l1 = _leg(c, "PE", sp, "settle")
            if not l1:
                continue
            l2 = _leg(c, "PE", sp * 0.987, "settle", lt=l1[0])
            if not l2:
                continue
            S = float(fo.se.loc[(s, e)])
            net = 2 * (l2[1] - hs(l2[1])) - (l1[1] + hs(l1[1]))
            pay = max(l1[0] - S, 0) - 2 * max(l2[0] - S, 0)
            pnl = (net + pay) * lot - fee("buy", l1[1] * lot, d) - fee("sell", 2 * l2[1] * lot, d)
            rows.append({"date": d, "pnl": pnl, "ret": pnl / BOOK, "credit": net > 0, "vix": fo.vix(d)})
        frames[s] = pd.DataFrame(rows)
        out[f"{s}|all"] = _abs(frames[s])
    n = frames["NIFTY"]
    out["NIFTY|credit_vs_debit"] = _ms(n, n["credit"], "ret", h=20)
    nv = n.dropna(subset=["vix"])
    out["NIFTY|vix_gt20"] = _ms(nv, nv["vix"] > 20, "ret", h=20)
    return out


@T.test("OPT-H45")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        lr = np.log(fo.ix[s]["c"]).diff()
        vol20 = lr.rolling(20).std()
        rows = []
        for e in fo.expiries[s]:
            if (s, e) not in fo.se.index or e not in fo.sessions:
                continue
            d = fo.shift(e, -5)
            sp = fo.spot(s, d) if d is not None else None
            c = fo.chain(s, e, d) if d is not None else None
            if sp is None or c is None:
                continue
            ce = c[(c["opt_type"] == "CE") & (c["settle"] > 0) & ((c["strike"] / sp - 1).abs() <= 0.05)].sort_values("strike")
            if len(ce) < 4:
                continue
            k, p = ce["strike"].values, ce["settle"].values
            mid = (k[:-1] + k[1:]) / 2
            imp = np.clip((p[:-1] - p[1:]) / np.diff(k), 0, 1)
            sig = float(vol20.get(d, np.nan)) * math.sqrt(5)
            if not sig == sig or sig <= 0:
                continue
            z = np.log(mid / sp) / sig + sig / 2
            hist = 1 - 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))
            y = (float(fo.se.loc[(s, e)]) > mid).astype(float)
            rows.append({"date": d, "diff": float(np.mean((hist - y) ** 2) - np.mean((imp - y) ** 2)), "brier_implied": float(np.mean((imp - y) ** 2)),
                         "brier_hist": float(np.mean((hist - y) ** 2))})
        df = pd.DataFrame(rows)
        r = _abs(df, "diff")
        r["extra"].update({"brier_implied": float(df["brier_implied"].mean()), "brier_hist": float(df["brier_hist"].mean())})
        out[s] = r
    return out


@T.desc("OPT-H46")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        naked, spread = [], []
        for e in fo.expiries[s]:
            if (s, e) not in fo.se.index or e not in fo.sessions:
                continue
            d = fo.shift(e, -5)
            sp = fo.spot(s, d) if d is not None else None
            c = fo.chain(s, e, d) if d is not None else None
            if sp is None or c is None:
                continue
            S = float(fo.se.loc[(s, e)])
            otm = c[(c["opt_type"] == "CE") & (c["settle"] > 0) & (c["strike"] >= sp * 1.01) & (c["strike"] <= sp * 1.03)]
            for kk, pp in zip(otm["strike"], otm["settle"]):
                naked.append(max(S - kk, 0) > pp + hs(pp))
            a, b = _leg(c, "CE", sp, "settle"), _leg(c, "CE", sp * 1.02, "settle", gt=sp)
            if a and b and b[0] > a[0]:
                cost = (a[1] + hs(a[1])) - (b[1] - hs(b[1]))
                spread.append(max(S - a[0], 0) - max(S - b[0], 0) > cost)
        out[s] = {"otm_calls_1_3pct_profitable_share": round(float(np.mean(naked)), 3) if naked else None, "otm_call_trades": len(naked),
                  "atm_to_2pct_call_spread_profitable_share": round(float(np.mean(spread)), 3) if spread else None, "spreads": len(spread)}
    return out


@T.test("OPT-H47")
def _(P):
    fo, out = F(), {}
    v = fo.ix["VIX"]
    wk = v / v.shift(5) - 1
    for name, cond in (("vix_jump25_gt30", (wk >= 0.25) & (v > 30)), ("vix_jump25", wk >= 0.25)):
        rows, last = [], None
        for d in cond[cond].index:
            if last is not None and (fo.sessions.searchsorted(d) - fo.sessions.searchsorted(last)) < 5:
                continue
            x = fo.shift(d, 3)
            e = fo.next_expiry("NIFTY", x, min_days=1) if x is not None else None
            sp = fo.spot("NIFTY", d)
            c0 = fo.chain("NIFTY", e, d) if e is not None else None
            c1 = fo.chain("NIFTY", e, x) if e is not None else None
            lot = fo.lot["NIFTY"].get(d)
            if sp is None or c0 is None or c1 is None or not lot or lot != lot:
                continue
            l0 = _leg(c0, "CE", sp, "settle")
            if not l0:
                continue
            p1 = _price(c1, "CE", l0[0], "settle")
            if p1 is None:
                continue
            last = d
            buy, sell = l0[1] + hs(l0[1]), p1 - hs(p1)
            pnl = (sell - buy) * lot - fee("buy", l0[1] * lot, d) - fee("sell", p1 * lot, x)
            rows.append({"date": d, "pnl": pnl, "ret": pnl / (buy * lot)})
        df = pd.DataFrame(rows)
        out[f"NIFTY|{name}"] = _abs(df) if len(df) else {"dev": (float("nan"), float("nan"), 0), "val": (float("nan"), float("nan"), 0), "extra": {"n_on": 0}}
    return out


@T.desc("OPT-H57")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        hit = back = n = 0
        for e in fo.expiries[s]:
            c = fo.chain(s, e, e)
            if c is None:
                continue
            x = c[(c["open"] > 0) & (c["open"] <= 5) & (c["volume"] > 0)]
            n += len(x)
            spike = x["high"] >= 8 * x["open"]
            hit += int(spike.sum())
            back += int((spike & (x["close"] < 2 * x["open"])).sum())
        out[s] = {"options_opening_at_rs5_or_less": n, "reached_8x_open": hit, "share": round(hit / n, 4) if n else None,
                  "of_those_closed_under_2x": back, "note": "strikes within 15% of spot only"}
    return out


@T.test("OPT-H58")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        rows = []
        for r in weekly_straddles(s).itertuples():
            start, e = r.date, r.expiry
            eve = fo.shift(e, -1) if e in fo.sessions else None
            if eve is None or eve <= start:
                continue
            c0, c1 = fo.chain(s, e, start), fo.chain(s, e, eve)
            sp = fo.spot(s, start)
            if c0 is None or c1 is None or sp is None:
                continue
            pr = _pair(c0, sp, "settle")
            if pr is None:
                continue
            k, ce, pe = pr
            pc, pp = _price(c1, "CE", k, "settle"), _price(c1, "PE", k, "settle")
            if pc is None or pp is None:
                continue
            n_between = int(((fo.sessions > start) & (fo.sessions <= eve)).sum())
            rows.append({"date": start, "decay": ((ce + pe) - (pc + pp)) / (ce + pe) / max(1, n_between), "holiday": r.n_sess < 5})
        df = pd.DataFrame(rows)
        rr = _ms(df, df["holiday"], "decay", h=5)
        rr["extra"]["holiday_weeks"] = int(df["holiday"].sum())
        out[s] = rr
    return out


@T.test("OPT-H59")
def _(P):
    fo, out = F(), {}
    for s in SYMS:
        allx = fo.expiries[s]
        rows = []
        for e1 in fo.weekly(s):
            i = allx.index(e1)
            if i + 1 >= len(allx) or e1 not in fo.sessions:
                continue
            e2, n = allx[i + 1], fo.shift(e1, 1)
            sp = fo.spot(s, e1)
            c0 = fo.chain(s, e2, e1)
            c1 = fo.chain(s, e2, n) if n is not None else None
            lot = fo.lot[s].get(e1)
            if sp is None or c0 is None or c1 is None or not lot or lot != lot:
                continue
            pr = _pair(c0, sp, "settle")
            if pr is None:
                continue
            k, ce, pe = pr
            sell = (ce - hs(ce)) + (pe - hs(pe))
            for how, col in (("next_open", "open"), ("next_close", "settle")):
                xc, xp = _price(c1, "CE", k, col), _price(c1, "PE", k, col)
                if xc is None or xp is None:
                    continue
                pnl = (sell - (xc + hs(xc)) - (xp + hs(xp))) * lot - fee("sell", (ce + pe) * lot, e1) - fee("buy", (xc + xp) * lot, n)
                rows.append({"how": how, "date": e1, "pnl": pnl, "ret": pnl / BOOK})
        df = pd.DataFrame(rows)
        for how in ("next_open", "next_close"):
            out[f"{s}|{how}"] = _abs(df[df["how"] == how])
    return out
