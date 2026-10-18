"""F&O studies on end-of-day data (silver fo_bhavcopy and fo_greeks; dev 2001-2017, validation 2018-2023). Settlement prices, not tradable quotes:
every entry pays a labelled half-spread (0.4% of premium, at least Rs 0.05 per leg) on top of Zerodha charges.

  python -m india.fstudies f01    short ATM straddle held to expiry from k sessions before (M-07/M-08 premium decay), NIFTY and BANKNIFTY
  python -m india.fstudies f02    O-03 closing-price version: short 1.5% strangle on the expiry eve, held to expiry; the tail first
  python -m india.fstudies f04    stock futures: price and open-interest quadrants (long build-up, short build-up, short covering, long unwinding) and the next 5 days
"""
from __future__ import annotations

import math
import sys

import duckdb
import numpy as np
import pandas as pd

from india import costs, paths, registry

SPLIT = 2018
HS_PCT, HS_MIN = 0.004, 0.05
BOOK = 50_000.0


def _files(name: str) -> list[str]:
    return [str(p) for p in (paths.data_dir() / "silver" / name).glob("year=*/part.parquet")]


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = x.dropna()
    if len(x) < 3:
        return float("nan"), float("nan"), int(len(x))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x))


def _qstat(df: pd.DataFrame, col: str, date_col: str = "date") -> tuple[float, float, int]:
    q = df.groupby(pd.to_datetime(df[date_col]).dt.to_period("Q"))[col].mean()
    return _stat(q)


def _hs(p):
    return np.maximum(HS_MIN, HS_PCT * p)


def _chains(symbols=("NIFTY", "BANKNIFTY")) -> tuple[pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect()
    g = con.execute(f"select date, symbol, expiry, strike, opt_type, settle, fwd from read_parquet({_files('fo_greeks')!r}) where list_contains(?, symbol) and settle > 0 and fwd > 0",
                    [list(symbols)]).df()
    fut = con.execute(f"select date, symbol, expiry, settle, lot_est from read_parquet({_files('fo_bhavcopy')!r}, union_by_name=true) "
                      f"where instrument = 'FUTIDX' and list_contains(?, symbol)", [list(symbols)]).df()
    con.close()
    for d in (g, fut):
        d["date"], d["expiry"] = pd.to_datetime(d["date"]), pd.to_datetime(d["expiry"])
    return g, fut


IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}


def _settle_at_expiry(fut: pd.DataFrame) -> pd.Series:
    """Monthly expiries: the expiring future's settlement price. Weekly expiries have no future: the index close that day (labelled: the official
    settlement is the average of the last 30 minutes, so this is an estimate)."""
    x = fut[fut["date"] == fut["expiry"]]
    s = x.groupby(["symbol", "expiry"])["settle"].last()
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    ix = ix[ix["index_name"].isin(IDX.values())]
    inv = {v: k for k, v in IDX.items()}
    ix_s = pd.Series(ix["close"].values, index=pd.MultiIndex.from_arrays([ix["index_name"].map(inv), pd.to_datetime(ix["date"])], names=["symbol", "expiry"]))
    ix_s = ix_s[~ix_s.index.duplicated(keep="last")]
    return pd.concat([s, ix_s[~ix_s.index.isin(s.index)]])


def _lot(fut: pd.DataFrame) -> pd.Series:
    return fut[fut["lot_est"] > 0].groupby(["symbol", "date"])["lot_est"].median().round()


def f01() -> dict:
    g, fut = _chains()
    s_exp = _settle_at_expiry(fut)
    lots = _lot(fut)
    sessions = np.array(sorted(g["date"].unique()))
    rows = []
    for (sym, exp), x in g.groupby(["symbol", "expiry"]):
        if (sym, exp) not in s_exp.index:
            continue
        se = float(s_exp.loc[(sym, exp)])
        i_e = np.searchsorted(sessions, np.datetime64(exp))
        for k in (1, 2, 3, 5):
            if i_e - k < 0:
                continue
            d = pd.Timestamp(sessions[i_e - k])
            y = x[x["date"] == d]
            if y.empty:
                continue
            f = float(y["fwd"].iloc[0])
            both = y.pivot_table(index="strike", columns="opt_type", values="settle", aggfunc="last").dropna()
            if both.empty or not {"CE", "PE"} <= set(both.columns):
                continue
            K = float(both.index[np.argmin(np.abs(both.index.values - f))])
            ce, pe = float(both.loc[K, "CE"]), float(both.loc[K, "PE"])
            lot = lots.get((sym, d))
            if lot is None or not lot == lot:
                continue
            credit = (ce - _hs(ce)) + (pe - _hs(pe))
            payoff = abs(se - K)
            fees = costs.cost("options", "sell", (ce + pe) * lot, d.year) + 0.0  # expiry settlement in cash; no closing order
            pnl = (credit - payoff) * lot - fees
            rows.append({"symbol": sym, "expiry": exp, "date": d, "k": k, "strike": K, "fwd": f, "credit": credit, "payoff": payoff, "lot": lot, "pnl_inr": pnl,
                         "ret_on_book": pnl / BOOK, "premium_pct": (ce + pe) / f, "move_pct": abs(se / f - 1)})
    df = pd.DataFrame(rows)
    df.to_parquet(paths.gold() / "studies" / "F01_straddles.parquet")
    reg = registry.register("F01", family="options_eod", title="Short ATM straddle held to expiry, from k sessions before (NIFTY, BANKNIFTY)",
                            hypothesis="Premium decays faster than the index moves: selling the at-the-money straddle k sessions before expiry and holding to expiry earns more than zero "
                                       "net of costs and a half-spread (M-07/M-08).", variants=[f"k{k}|{s}" for k in (1, 2, 3, 5) for s in ("NIFTY", "BANKNIFTY")],
                            note="settlement prices; one trade per expiry and k; t across quarter means (several weekly expiries share a quarter)")
    out = {}
    for (k, s), x in df.groupby(["k", "symbol"]):
        x = x.copy()
        x["y"] = x["date"].dt.year
        dev, val = _qstat(x[x["y"] < SPLIT], "ret_on_book"), _qstat(x[x["y"] >= SPLIT], "ret_on_book")
        v = x[x["y"] >= SPLIT]
        extra = {"val_trades": int(len(v)), "val_win_share": float((v["pnl_inr"] > 0).mean()) if len(v) else None, "val_worst_inr": float(v["pnl_inr"].min()) if len(v) else None,
                 "val_p5_inr": float(v["pnl_inr"].quantile(0.05)) if len(v) else None, "val_mean_inr": float(v["pnl_inr"].mean()) if len(v) else None,
                 "val_premium_pct_median": float(v["premium_pct"].median()) if len(v) else None, "val_move_pct_median": float(v["move_pct"].median()) if len(v) else None}
        line = registry.record(reg, f"k{k}|{s}", dev, val, extra=extra, expect=1)
        out[f"k{k}|{s}"] = line["verdict"]
        print(f"F01 k{k} {s:9s} {line['verdict']:12s} dev {dev[0]*100:+.2f}% t {dev[1]:+.1f} q{dev[2]} | val {val[0]*100:+.2f}% t {val[1]:+.1f} q{val[2]} | val trades {extra['val_trades']}, "
              f"win {extra['val_win_share'] or 0:.0%}, mean Rs {extra['val_mean_inr'] or 0:,.0f}, p5 Rs {extra['val_p5_inr'] or 0:,.0f}, worst Rs {extra['val_worst_inr'] or 0:,.0f}", flush=True)
    registry.mirror_to_catalog()
    return out


def f02() -> dict:
    """O-03 on closing prices: on the session before each expiry, sell the call and put about 1.5% from the forward and buy the strikes about 3% away as hedges
    (the live version buys hedges near Rs 1 at 15:00; settlement data has no 15:00 price, so the hedge rule here is distance). Held to expiry settlement."""
    g, fut = _chains()
    s_exp = _settle_at_expiry(fut)
    lots = _lot(fut)
    sessions = np.array(sorted(g["date"].unique()))
    rows = []
    for (sym, exp), x in g.groupby(["symbol", "expiry"]):
        if (sym, exp) not in s_exp.index:
            continue
        i_e = np.searchsorted(sessions, np.datetime64(exp))
        if i_e < 1:
            continue
        d = pd.Timestamp(sessions[i_e - 1])
        y = x[x["date"] == d]
        if y.empty:
            continue
        f = float(y["fwd"].iloc[0])
        se = float(s_exp.loc[(sym, exp)])
        ce, pe = y[y["opt_type"] == "CE"].set_index("strike")["settle"], y[y["opt_type"] == "PE"].set_index("strike")["settle"]

        def pick(s, target):
            return float(s.index[np.argmin(np.abs(s.index.values - target))]) if len(s) else None
        kc, kp = pick(ce, f * 1.015), pick(pe, f * 0.985)
        hc, hp = pick(ce[ce.index > (kc or 0)], f * 1.03), pick(pe[pe.index < (kp or 0)], f * 0.97)
        lot = lots.get((sym, d))
        if None in (kc, kp, hc, hp) or lot is None or not lot == lot:
            continue
        sc, sp, bc, bp = float(ce[kc]), float(pe[kp]), float(ce[hc]), float(pe[hp])
        credit = (sc - _hs(sc)) + (sp - _hs(sp)) - (bc + _hs(bc)) - (bp + _hs(bp))
        pay = max(se - kc, 0) + max(kp - se, 0) - max(se - hc, 0) - max(hp - se, 0)
        fees = costs.cost("options", "sell", (sc + sp) * lot, d.year) + costs.cost("options", "buy", (bc + bp) * lot, d.year)
        pnl = (credit - pay) * lot - fees
        rows.append({"symbol": sym, "expiry": exp, "date": d, "credit": credit, "pay": pay, "lot": lot, "pnl_inr": pnl, "ret_on_book": pnl / BOOK,
                     "max_loss_inr": (max(hc - kc, kp - hp) - credit) * lot, "move_pct": se / f - 1})
    df = pd.DataFrame(rows).sort_values("expiry")
    df.to_parquet(paths.gold() / "studies" / "F02_strangles.parquet")
    reg = registry.register("F02", family="options_eod", title="O-03 closing-price version: expiry-eve short strangle with hedges, held to expiry",
                            hypothesis="Selling the 1.5% strangle on the expiry eve with 3% hedges earns more than zero net of costs and spread; the tail is reported first.",
                            variants=["eve_strangle|NIFTY", "eve_strangle|BANKNIFTY"], note="settlement prices; hedges by distance (live version: price near Rs 1); t across quarter means")
    out = {}
    for s, x in df.groupby("symbol"):
        x = x.copy()
        x["y"] = x["date"].dt.year
        dev, val = _qstat(x[x["y"] < SPLIT], "ret_on_book"), _qstat(x[x["y"] >= SPLIT], "ret_on_book")
        cum = x["pnl_inr"].cumsum()
        dd = float((cum - cum.cummax()).min())
        worst_run = int((x["pnl_inr"] < 0).astype(int).groupby((x["pnl_inr"] >= 0).cumsum()).sum().max())
        extra = {"trades": int(len(x)), "worst_inr": float(x["pnl_inr"].min()), "worst_day": str(x.loc[x["pnl_inr"].idxmin(), "expiry"].date()), "max_drawdown_inr": dd,
                 "longest_losing_run": worst_run, "win_share": float((x["pnl_inr"] > 0).mean()), "mean_inr": float(x["pnl_inr"].mean())}
        line = registry.record(reg, f"eve_strangle|{s}", dev, val, extra=extra, expect=1)
        out[s] = line["verdict"]
        print(f"F02 {s:9s} {line['verdict']:12s} dev {dev[0]*100:+.3f}% t {dev[1]:+.1f} | val {val[0]*100:+.3f}% t {val[1]:+.1f} | trades {extra['trades']}, win {extra['win_share']:.0%}, "
              f"mean Rs {extra['mean_inr']:,.0f}, worst Rs {extra['worst_inr']:,.0f} ({extra['worst_day']}), max drawdown Rs {dd:,.0f}, longest losing run {worst_run}", flush=True)
    registry.mirror_to_catalog()
    return out


def f04() -> dict:
    con = duckdb.connect()
    fut = con.execute(f"""select date, symbol, expiry, close, open_interest, chg_oi from read_parquet({_files('fo_bhavcopy')!r}, union_by_name=true)
                          where instrument = 'FUTSTK' and close > 0 and open_interest > 0""").df()
    con.close()
    fut["date"], fut["expiry"] = pd.to_datetime(fut["date"]), pd.to_datetime(fut["expiry"])
    near = fut.sort_values(["symbol", "date", "expiry"]).groupby(["symbol", "date"]).head(1).copy()  # near month
    # day-on-day change on the same contract; the roll day (contract changes) is left out
    near = near.sort_values(["symbol", "date"])
    near["prev_close"] = near.groupby(["symbol", "expiry"])["close"].shift(1)
    near["prev_oi"] = near.groupby(["symbol", "expiry"])["open_interest"].shift(1)
    near = near.dropna(subset=["prev_close", "prev_oi"])
    near["dp"] = near["close"] / near["prev_close"] - 1
    near["doi"] = near["open_interest"] / near["prev_oi"] - 1
    # forward 5-session return of the same contract: known only after the signal day, it is the outcome (entry next session's close as a proxy for the open)
    near["fwd5"] = near.groupby(["symbol", "expiry"])["close"].shift(-5) / near.groupby(["symbol", "expiry"])["close"].shift(-1) - 1
    near = near.dropna(subset=["fwd5"])
    big = (near["dp"].abs() > 0.02) & (near["doi"].abs() > 0.05)
    q = np.select([(near["dp"] > 0) & (near["doi"] > 0), (near["dp"] < 0) & (near["doi"] > 0), (near["dp"] > 0) & (near["doi"] < 0), (near["dp"] < 0) & (near["doi"] < 0)],
                  ["long_buildup", "short_buildup", "short_covering", "long_unwinding"], "none")
    near["quad"] = np.where(big, q, "none")
    near["y"] = near["date"].dt.year
    expect = {"long_buildup": 1, "short_buildup": -1, "short_covering": 1, "long_unwinding": -1}
    reg = registry.register("F04", family="futures", title="Stock futures price/open-interest quadrants and the next 5 sessions",
                            hypothesis="After a day with price and open interest both moving more than 2% / 5%, the next 5 sessions move the way the quadrant says (build-ups continue).",
                            variants=list(expect), note="near-month stock futures; outcome = close of session t+5 over close of t+1 (no fill at the signal close); on minus 'none' days within quarters")
    out = {}
    for name, e in expect.items():
        x = near[near["quad"].isin([name, "none"])].copy()
        x["on"] = x["quad"] == name
        st = {}
        for per, m in (("dev", x["y"] < SPLIT), ("val", x["y"] >= SPLIT)):
            z = x[m]
            qm = z.groupby([z["date"].dt.to_period("Q"), "on"])["fwd5"].mean().unstack().dropna()
            st[per] = _stat(qm[True] - qm[False]) if len(qm) and True in qm and False in qm else (float("nan"), float("nan"), 0)
        line = registry.record(reg, name, st["dev"], st["val"], extra={"n_on": int(x["on"].sum())}, expect=e)
        out[name] = line["verdict"]
        print(f"F04 {name:15s} {line['verdict']:12s} dev {st['dev'][0]*100:+.2f}% t {st['dev'][1]:+.1f} q{st['dev'][2]} | val {st['val'][0]*100:+.2f}% t {st['val'][1]:+.1f} q{st['val'][2]} | n {int(x['on'].sum())}", flush=True)
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k, f in (("f01", f01), ("f02", f02), ("f04", f04)):
        if w in (k, "all"):
            f()
