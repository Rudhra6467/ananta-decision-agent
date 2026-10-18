"""F06: Nifty puts as protection for a stock book (dev 2003-2017, validation 2018-2023, end-of-day settlement prices).

  python -m india.hedge             overlays monthly Nifty put buying on the 10-slot books of E10 (curves 'none'), marked every day at settlement

Rule: at each monthly expiry close, buy the next month's Nifty put about X% below spot for a notional equal to `ratio` x the book's equity, pay the
half-spread and charges, mark it daily at its settlement price, let it settle at expiry, roll. Variants: 5% and 10% out of the money, 50% and 100% of equity.
Registered test: quarterly return of the hedged book minus the unhedged book (the cost), with the worst drawdown and the worst quarter reported beside it
(what the cost bought). The book and the hedge are both on dev/validation rows only.
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


def _puts() -> pd.DataFrame:
    files = [str(p) for p in (paths.data_dir() / "silver/fo_bhavcopy").glob("year=*/part.parquet")]
    con = duckdb.connect()
    df = con.execute(f"select date, expiry, strike, settle, close from read_parquet({files!r}, union_by_name=true) "
                     f"where instrument = 'OPTIDX' and symbol = 'NIFTY' and opt_type = 'PE' and settle > 0").df()
    con.close()
    df["date"], df["expiry"] = pd.to_datetime(df["date"]), pd.to_datetime(df["expiry"])
    return df


BOOK_INR = 500_000.0  # the 10-slot book at Rs 50,000 a slot: charges are in rupees (flat brokerage per order), so the overlay is computed in rupees


def overlay(curve: pd.Series, puts: pd.DataFrame, monthly: list, nifty: pd.Series, otm: float, ratio: float) -> pd.Series:
    """Returns the hedged curve on the same scale as `curve` (1.0 = the starting book)."""
    curve = curve * BOOK_INR
    hedge_cash = 0.0
    pos = None  # (expiry, strike, qty, paid)
    by = {k: g.set_index("date")["settle"] for k, g in puts.groupby(["expiry", "strike"])}
    out = []
    mset = set(monthly)
    for d in curve.index:
        mark = 0.0
        if pos is not None:
            e, K, q, paid = pos
            if d >= e:
                s = nifty.get(e, np.nan)
                hedge_cash += q * max(K - s, 0.0) if s == s else 0.0
                pos = None
            else:
                px = by.get((e, K), pd.Series(dtype=float)).get(d, np.nan)
                mark = q * px if px == px else q * paid
        if pos is None and d in mset:
            nxt = [m for m in monthly if m > d]
            if nxt:
                e = nxt[0]
                s = nifty.get(d, np.nan)
                ch = puts[(puts["date"] == d) & (puts["expiry"] == e)]
                if s == s and not ch.empty:
                    k = ch.iloc[(ch["strike"] - s * (1 - otm)).abs().argsort()[:1]]
                    K, px = float(k["strike"].iloc[0]), float(k["settle"].iloc[0])
                    buy = px + max(HS_MIN, HS_PCT * px)
                    total = curve.loc[d] + hedge_cash
                    q = ratio * total / s
                    fee = costs.cost("options", "buy", buy * q, d.year)
                    hedge_cash -= buy * q + fee
                    pos = (e, K, q, buy)
                    mark = q * px
        out.append(curve.loc[d] + hedge_cash + mark)
    return pd.Series(out, index=curve.index) / BOOK_INR


def run() -> dict:
    puts = _puts()
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    nifty = ix[ix["index_name"] == "NIFTY 50"].assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")["close"].sort_index()
    cal = pd.read_parquet(paths.data_dir() / "silver/fo_calendar/expiries.parquet")
    monthly = sorted(pd.to_datetime(cal[(cal["symbol"] == "NIFTY") & (cal["instrument"] == "OPTIDX") & cal["is_monthly_last"]]["expiry"]).tolist())
    variants = {f"put{int(o*100)}otm_{int(r*100)}pct": (o, r) for o in (0.05, 0.10) for r in (0.5, 1.0)}
    out = {}
    for es in ("BRK", "PULL", "ANY"):
        p = paths.gold() / "studies" / f"E10-{es}_curves.parquet"
        if not p.exists():
            print(f"F06 {es}: no E10 curve yet, skipped", flush=True)
            continue
        curve = pd.read_parquet(p)["none"].dropna()
        curve = curve[curve.index >= "2003-01-01"]
        curve = curve / curve.iloc[0]
        reg = registry.register(f"F06-{es}", family="hedge", title=f"Nifty put protection on the 10-slot {es} book",
                                hypothesis="Buying monthly Nifty puts raises the book's quarterly return (it usually costs: the cost is the measured quantity) while cutting the worst drawdown.",
                                variants=list(variants), note="E10 'none' curve; puts marked at settlement; expect = 0 (two-sided): the verdict says whether the cost is distinguishable from zero")
        q0 = pd.concat([curve[lo:hi].resample("QE").last().pct_change().dropna() for lo, hi in (("2003-01-01", "2017-12-31"), ("2018-01-01", "2023-12-31"))])
        for vn, (o, r) in variants.items():
            # each period starts its own book at 1.0, so a costly dev hedge cannot leave the validation book near zero
            parts = []
            for lo, hi in (("2003-01-01", "2017-12-31"), ("2018-01-01", "2023-12-31")):
                c = curve[lo:hi] / curve[lo:hi].iloc[0]
                parts.append(overlay(c, puts, monthly, nifty, o, r) * curve[lo:hi].iloc[0])
            h = pd.concat(parts)
            qh = pd.concat([x.resample("QE").last().pct_change().dropna() for x in parts])
            d = (qh - q0).dropna()
            st = {}
            for per, m in (("dev", d.index.year < SPLIT), ("val", d.index.year >= SPLIT)):
                x = d[m]
                se = x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 2 else float("nan")
                st[per] = (float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x)))
            def dd(c):
                return float((c / c.cummax() - 1).min())
            ext = {}
            for per, lo, hi in (("dev", "2003-01-01", "2017-12-31"), ("val", "2018-01-01", "2023-12-31")):
                c0, c1 = curve[lo:hi], h[lo:hi]
                yrs = max((c0.index[-1] - c0.index[0]).days / 365.25, 0.5)
                ext[per] = {"dd_book": dd(c0), "dd_hedged": dd(c1), "growth_book": float((c0.iloc[-1] / c0.iloc[0]) ** (1 / yrs) - 1),
                            "growth_hedged": float((c1.iloc[-1] / c1.iloc[0]) ** (1 / yrs) - 1) if c1.iloc[-1] > 0 else -1.0,
                            "worst_q_book": float(q0[lo:hi].min()), "worst_q_hedged": float(qh[lo:hi].min())}
            line = registry.record(reg, vn, st["dev"], st["val"], extra=ext, expect=0)
            out[f"{es}|{vn}"] = line["verdict"]
            v = ext["val"]
            print(f"F06-{es} {vn:18s} {line['verdict']:12s} quarterly cost dev {st['dev'][0]*100:+.2f}% t {st['dev'][1]:+.1f} | val {st['val'][0]*100:+.2f}% t {st['val'][1]:+.1f} | "
                  f"val dd {v['dd_book']*100:.0f}% -> {v['dd_hedged']*100:.0f}%, growth {v['growth_book']*100:+.1f}% -> {v['growth_hedged']*100:+.1f}%/yr, worst quarter {v['worst_q_book']*100:.0f}% -> {v['worst_q_hedged']*100:.0f}% | "
                  f"dev dd {ext['dev']['dd_book']*100:.0f}% -> {ext['dev']['dd_hedged']*100:.0f}%", flush=True)
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    paths.ensure()
    run()
