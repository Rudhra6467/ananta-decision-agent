"""GP1 (the opening gap), TS1 (trailing against fixed stops) and HG1 (hedging a long basket when the Nifty is below its 200-day): three registered studies,
one module. Madhav's yes of 26 Oct 2026 20:26 Toronto to the recommendations that followed the review of his Ask conversation (Ananta had "no tested gap
rule", "no direct test" of trailing against fixed stops, and "no tested hedge"). The specs (india/registrations/{gp1,ts1,hg1}_v1.json) were written
before any outcome was read; `run` registers each study with the spec's frozen k, computes, and records every variant in the ledger. Research rows only:
nothing dated 2024 or later is used and no sealed purpose is opened (the stock panel, the bars and silver/fo_bhavcopy stop at 2023-12-29).

  python -m india.gaplab check [gp1|ts1|hg1|all]    event or entry counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.gaplab run gp1|ts1|hg1             register, compute, record; manifests/gaplab_<study>.json and registrations/<study>_results_v1.md
  python -m india.gaplab table gp1|ts1|hg1           rewrite the results page from the manifest
"""
from __future__ import annotations

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
IDX_COST = 0.0010            # index round trip (futures or ETF: charges plus slippage), fixed in the GP1 spec
GAP_COOL_STOCK, GAP_COOL_INDEX = 10, 5


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
    return x


def _cool(on: pd.Series, days: int) -> pd.Series:
    """First True, then none for `days` sessions (one event per gap on a single series)."""
    out = np.zeros(len(on), dtype=bool)
    last = -10 ** 9
    for i, v in enumerate(on.fillna(False).to_numpy(bool)):
        if v and i - last >= days:
            out[i] = True
            last = i
    return pd.Series(out, index=on.index)


def _counts(dates: pd.Series, mask: pd.Series) -> dict:
    y = pd.to_datetime(dates[mask.fillna(False).astype(bool)]).dt.year
    return {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())}


# =============================================================================================================================== GP1: the opening gap

def _gap_stock_frame() -> pd.DataFrame:
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet", columns=["sid", "symbol", "date", "n", "liq_rank", "o", "c", "cost"])
    P["date"] = pd.to_datetime(P["date"])
    P = P[P["date"] < CUT].sort_values(["sid", "date"]).reset_index(drop=True)
    consec = (P["sid"] == P["sid"].shift(1)) & (P["n"] == P["n"].shift(1) + 1)
    seg = (~consec).cumsum()
    o, c = P["o"].astype(float), P["c"].astype(float)
    cprev = c.shift(1).where(consec)
    gap = o / cprev - 1
    jump = ((c / cprev - 1).abs() > 0.5).fillna(False).astype(int)
    cs = jump.groupby(seg).cumsum()
    win5 = cs.groupby(seg).shift(-4) - (cs - jump)                # one-day moves over 50% on days t .. t+4: an artefact, not a trade
    c4 = c.groupby(seg).shift(-4)                                  # close of the fifth session counting the entry session
    P["g1"] = (c / o - 1 - P["cost"]).where(jump == 0)
    P["g5"] = (c4 / o - 1 - P["cost"]).where(win5 == 0)
    P["gap"] = gap
    liq = (P["liq_rank"] <= 250)
    P["liq"] = liq
    gv = gap.to_numpy(float)
    ok = pd.Series(np.isfinite(gv) & (np.abs(gv) < 0.5) & liq.to_numpy(), index=P.index)
    with np.errstate(invalid="ignore"):
        masks = {"gd2": gv <= -0.02, "gd1": gv <= -0.01, "gu2": gv >= 0.02}
    for k, m in masks.items():
        P[k] = ts._cooldown(P, ok & pd.Series(m, index=P.index), GAP_COOL_STOCK)
    P["gu2next"] = P["gu2"].astype(int).groupby(seg).shift(1).fillna(0).astype(bool)      # the session after a gap-up day (same continuous run)
    P["s5"] = ts.sample5(P)
    return P


STK_PLAN = [("STK|gapdown2|open|hold1", "gd2", "g1"), ("STK|gapdown2|open|hold5", "gd2", "g5"), ("STK|gapdown1|open|hold5", "gd1", "g5"),
            ("STK|gapup2|open|hold5", "gu2", "g5"), ("STK|gapup2|next|hold5", "gu2next", "g5")]
IDX_PLAN = [("NIFTY|gapdown1|open|hold5", "NIFTY 50", "dn1", False), ("NIFTY|gapup1|open|hold5", "NIFTY 50", "up1", False),
            ("BANK|gapdown1|open|hold5", "NIFTY BANK", "dn1", False), ("BANK|gapup1|open|hold5", "NIFTY BANK", "up1", False),
            ("NIFTY|gapdown1|wait30|hold5", "NIFTY 50", "dn1", True)]


def _idx_day(name: str) -> pd.DataFrame:
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet", columns=["index_name", "date", "open", "close"])
    ix = ix[ix["index_name"] == name].assign(date=lambda d: pd.to_datetime(d["date"]))
    ix = ix[(ix["date"] < CUT) & (ix["open"] > 0) & (ix["close"] > 0)].drop_duplicates("date").set_index("date").sort_index()
    return ix


def _idx_0945(name: str) -> pd.Series:
    """Open of the 09:45 five-minute bar (30 minutes after the open) per session, 2015-2023."""
    parts = []
    for y in range(2015, 2024):
        f = paths.data_dir() / f"silver/kite_index/5minute/year={y}/part.parquet"
        if not f.exists():
            continue
        d = pd.read_parquet(f, columns=["index_name", "ts", "open"])
        d = d[d["index_name"] == name]
        t = pd.to_datetime(d["ts"])
        d = d[(t.dt.hour == 9) & (t.dt.minute == 45)]
        parts.append(pd.Series(d["open"].to_numpy(float), index=pd.to_datetime(d["ts"]).dt.normalize()))
    s = pd.concat(parts) if parts else pd.Series(dtype=float)
    return s[~s.index.duplicated()].sort_index()


def _gap_index_frame(name: str, wait30: bool = False) -> pd.DataFrame:
    x = _idx_day(name)
    M = pd.DataFrame(index=x.index)
    M["date"] = x.index
    gap = x["open"] / x["close"].shift(1) - 1
    entry = x["open"]
    if wait30:
        entry = _idx_0945(name).reindex(x.index)
    M["g5"] = x["close"].shift(-4) / entry - 1 - IDX_COST
    M["gap"] = gap
    M["ok"] = gap.notna() & M["g5"].notna()
    with np.errstate(invalid="ignore"):
        M["dn1"] = _cool((gap <= -0.01) & gap.notna(), GAP_COOL_INDEX) & M["ok"]
        M["up1"] = _cool((gap >= 0.01) & gap.notna(), GAP_COOL_INDEX) & M["ok"]
    return M


def gp1_results(counts_only: bool = False) -> dict:
    out = {}
    P = _gap_stock_frame()
    for key, ev, col in STK_PLAN:
        cnt = {**_counts(P["date"], P[ev] & P["liq"]), "base_rows": int((P["liq"] & P["s5"]).sum())}
        if counts_only:
            out[key] = cnt
            continue
        d = P[P["liq"] & (P["s5"] | P[ev])]
        r = ts.level(d, d[ev], col)
        a = ts.absolute(P[P["liq"]], P[ev] & P["liq"], col)
        r["extra"] = {**r["extra"], **cnt, "trade_after_costs_dev": a["dev"], "trade_after_costs_val": a["val"], "mean_net_per_trade": a["extra"]["mean_on"],
                      "win_rate_info_only": a["extra"]["win_rate_info_only"]}
        out[key] = r
    for key, name, ev, w30 in IDX_PLAN:
        M = _gap_index_frame(name, w30)
        cnt = _counts(M["date"], M[ev])
        if counts_only:
            out[key] = {**cnt, "base_sessions": int(M["ok"].sum())}
            continue
        r = ts.msplit(M, M[ev], "g5", h=5, base=M["ok"])
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


# --------------------------------------------------------------------------------------------- GP1 diagnostic (after the run; not registered, no verdict)

def gp1_diagnostic() -> dict:
    """Two descriptive checks written after the GP1 verdicts, because the open-price versions cannot be traded as defined (the gap is only known once the
    market has opened, and an order placed then does not fill at the opening print): (a) the stock gap-down results by calendar year; (b) the same gap-down
    days (gapdown2, liquid 250, 2015-2023, stocks in silver/kite_5m) entered at the open of the SECOND five-minute bar (09:20) and of the 09:45 bar and sold at the
    close of the same day, against every 5th session of the same stocks, quarter by quarter. Reported with numbers only: no verdict, not counted in k."""
    P = _gap_stock_frame()
    base = P[P["liq"] & P["s5"]]
    ev = P[P["gd2"] & P["liq"]]
    yearly = {}
    for y in range(2000, 2024):
        e, b = ev[ev["date"].dt.year == y], base[base["date"].dt.year == y]
        if len(e) >= 30 and len(b):
            yearly[int(y)] = {"events": int(len(e)), "event_mean_hold1": float(e["g1"].mean()), "ordinary_mean_hold1": float(b["g1"].mean()),
                              "event_mean_hold5": float(e["g5"].mean()), "ordinary_mean_hold5": float(b["g5"].mean())}
    rows = []
    for y in range(2015, 2024):
        f = paths.data_dir() / f"silver/kite_5m/year={y}/part.parquet"
        if not f.exists():
            continue
        d = pd.read_parquet(f, columns=["symbol", "ts", "date", "kite_open", "kite_close"])
        d["date"] = pd.to_datetime(d["date"])
        hm = d["ts"].dt.hour * 100 + d["ts"].dt.minute
        g = d.assign(hm=hm).sort_values(["symbol", "date", "ts"])
        last = g.groupby(["symbol", "date"])["kite_close"].last().rename("day_close")
        o0920 = g[g["hm"] == 920].set_index(["symbol", "date"])["kite_open"].rename("o0920")
        o0945 = g[g["hm"] == 945].set_index(["symbol", "date"])["kite_open"].rename("o0945")
        rows.append(pd.concat([last, o0920, o0945], axis=1).reset_index())
        del d, g
    I = pd.concat(rows, ignore_index=True)
    m = P[P["liq"] & (P["date"] >= "2015-01-01")].merge(I, on=["symbol", "date"], how="inner")
    m["i0920"] = m["day_close"] / m["o0920"] - 1 - m["cost"]
    m["i0945"] = m["day_close"] / m["o0945"] - 1 - m["cost"]
    d = m[m["s5"] | m["gd2"]]
    out = {"yearly_open_entries": yearly, "executable_5m": {}}
    for col in ("i0920", "i0945"):
        r = ts.level(d, d["gd2"], col)
        out["executable_5m"][col] = {"vs_ordinary_days_dev_2015_17": r["dev"], "vs_ordinary_days_val_2018_23": r["val"], "events": r["extra"]["n_on"],
                                     "mean_net_per_trade": r["extra"]["mean_on"], "ordinary_mean": r["extra"]["mean_all"]}
    out["note"] = "after the run; descriptive only; not registered; stocks in silver/kite_5m only (about 360 a year); development holds 12 quarters only"
    (paths.manifest_dir() / "gaplab_gp1_diag.json").write_text(json.dumps(_clean(out), indent=1, default=str))
    return out


# =============================================================================================================================== TS1: trailing against fixed stops

SETS = ("ANY", "BRK", "PULL")
RULES = ("fixed7", "fixed2atr", "trail2atr", "trail10", "hold20")


def _ts_entries() -> dict:
    out = {}
    for name in SETS:
        t = pd.read_parquet(paths.gold() / "studies" / f"E02-{name}_trades.parquet", columns=["sid", "signal_date"]).drop_duplicates()
        t["signal_date"] = pd.to_datetime(t["signal_date"])
        out[name] = t[(t["signal_date"] >= "2000-01-01") & (t["signal_date"] < CUT)].reset_index(drop=True)
    return out


def _walk(rule: str, o, h, l, c, entry: float, atr: float, horizon: int = 60):
    """One trade from the entry day (index 0). Returns (exit_index, exit_price, reason, peak_high). The exitlab rules (india/exitlab.py _exit): in from the
    entry bar's open; a stop fills at the stop price or at the open if it gapped through; a close-based exit fills at the next open; the stop is only ever raised."""
    if rule == "fixed7":
        stop, trail_atr, trail_pct, cap = entry * 0.93, 0.0, 0.0, horizon
    elif rule == "fixed2atr":
        stop, trail_atr, trail_pct, cap = entry - 2.0 * atr, 0.0, 0.0, horizon
    elif rule == "trail2atr":
        stop, trail_atr, trail_pct, cap = entry - 2.0 * atr, 2.0 * atr, 0.0, 0
    elif rule == "trail10":
        stop, trail_atr, trail_pct, cap = entry * 0.90, 0.0, 0.10, 0
    elif rule == "hold20":
        stop, trail_atr, trail_pct, cap = entry - 2.0 * atr, 0.0, 0.0, 20
    else:
        raise ValueError(rule)
    peak = entry
    n = len(o)
    pending = False
    for i in range(n):
        if pending:
            return i, o[i], "time", peak
        if l[i] <= stop:
            return i, min(o[i], stop), "stop", max(peak, h[i])
        peak = max(peak, h[i])
        if trail_atr:
            stop = max(stop, peak - trail_atr)
        elif trail_pct:
            stop = max(stop, peak * (1.0 - trail_pct))
        if cap and i + 1 >= cap:
            pending = True
        if i == n - 1 and not pending:
            return i, c[i], "end", peak
    return n - 1, c[-1], "end", peak


def _simulate(entries: pd.DataFrame, bars: dict, feat: pd.DataFrame, rules=RULES) -> pd.DataFrame:
    """Same windows, hygiene skips, corporate-action skips and cost model as india.exitlab.simulate; only the exit walk differs."""
    from india import exitlab as X

    atr = feat.set_index(["sid", "date"])[["atr14", "liq_rank"]].sort_index()
    caf = X.ca_flags()
    rows = []
    skipped = skipped_ca = 0
    for sid, sig in zip(entries["sid"], pd.to_datetime(entries["signal_date"])):
        b = bars.get(sid)
        if b is None:
            continue
        dates, o, h, l, c, v = b
        i0 = int(np.searchsorted(dates, np.datetime64(sig.date()), side="right"))
        if i0 >= len(dates) or i0 + 2 > len(dates):
            continue
        try:
            a, rank = atr.loc[(sid, sig)]
        except KeyError:
            continue
        if not a or a <= 0:
            continue
        j1 = min(len(dates), i0 + X.HORIZON + 1)
        oo, hh, ll, cc = o[i0:j1], h[i0:j1], l[i0:j1], c[i0:j1]
        dd = np.diff(dates[i0:j1]).astype("timedelta64[D]").astype(int)
        jump = np.abs(cc[1:] / cc[:-1] - 1) if len(cc) > 1 else np.array([0.0])
        if (len(dd) and dd.max() > 10) or jump.max() > 0.5:
            skipped += 1
            continue
        if sid in caf:
            lo_d, hi_d = dates[max(0, i0 - 200)], dates[j1 - 1]
            ev = caf[sid]
            if ((ev > lo_d) & (ev <= hi_d)).any():
                skipped_ca += 1
                continue
        entry = oo[0]
        if 2.0 * a >= entry:
            continue
        for rule in rules:
            k, px, why, peak = _walk(rule, oo, hh, ll, cc, entry, a)
            risk = {"fixed7": 0.07 * entry, "trail10": 0.10 * entry}.get(rule, 2.0 * a)
            r = X._row(sid, sig, dates[i0], rule, entry, risk, k, px, why, peak, hh[: k + 1], ll[: k + 1], rank)
            rows.append(r)
    out = pd.DataFrame(rows)
    out.attrs["skipped_data_hygiene"] = skipped
    out.attrs["skipped_ambiguous_ca"] = skipped_ca
    return out


def _ts_trades(force: bool = False) -> dict:
    """The TS1 trades per entry set, cached in gold/studies/TS1-<set>_trades.parquet (research rows only)."""
    from india import exitlab as X
    from india import studies

    ent = _ts_entries()
    out = {}
    feat = bars = None
    for name, e in ent.items():
        p = paths.gold() / "studies" / f"TS1-{name}_trades.parquet"
        if p.exists() and not force:
            out[name] = pd.read_parquet(p)
            continue
        if feat is None:
            feat = studies.load_features()
            bars = X.load_bars()
        tr = _simulate(e, bars, feat)
        (paths.gold() / "studies").mkdir(parents=True, exist_ok=True)
        tr.to_parquet(p)
        out[name] = tr
    return out


def _pair(tr: pd.DataFrame, a: str, b: str) -> pd.DataFrame:
    x = tr[tr["policy"] == a].set_index(["sid", "signal_date"])
    y = tr[tr["policy"] == b].set_index(["sid", "signal_date"])
    j = x[["net_ret", "hold_days", "reason"]].join(y[["net_ret", "hold_days", "reason"]], lsuffix="_a", rsuffix="_b", how="inner").reset_index()
    j["diff"] = j["net_ret_a"] - j["net_ret_b"]
    return j


def _rule_extras(tr: pd.DataFrame, rule: str) -> dict:
    g = tr[tr["policy"] == rule]
    out = {}
    for per, m in (("dev", g["signal_date"].dt.year < SPLIT), ("val", g["signal_date"].dt.year >= SPLIT)):
        x = g[m]
        out[per] = {"trades": int(len(x)), "mean_net": float(x["net_ret"].mean()), "p5": float(x["net_ret"].quantile(0.05)) if len(x) else None,
                    "worst": float(x["net_ret"].min()) if len(x) else None, "stopped_share": float((x["reason"] == "stop").mean()) if len(x) else None,
                    "mean_days": float(x["hold_days"].mean()) if len(x) else None}
    return out


def ts1_results(counts_only: bool = False) -> dict:
    s = spec("TS1")
    ent = _ts_entries()
    if counts_only:
        out = {}
        for var in s["variants"]:
            name = var.split("|")[0]
            y = ent[name]["signal_date"].dt.year
            out[var] = {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())}
        return out
    trades = _ts_trades()
    out = {}
    for var in s["variants"]:
        name, pair = var.split("|")
        a, b = pair.split("_vs_")
        tr = trades[name]
        j = _pair(tr, a, b)
        q = j.groupby(j["signal_date"].dt.to_period("Q"))["diff"].mean()
        r = {"dev": ts._stat(q[[p.year < SPLIT for p in q.index]]), "val": ts._stat(q[[p.year >= SPLIT for p in q.index]])}
        y = j["signal_date"].dt.year
        r["extra"] = {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum()), "entry_set": name, "rule_a": a, "rule_b": b,
                      "mean_diff_per_trade": float(j["diff"].mean()), "a": _rule_extras(tr, a), "b": _rule_extras(tr, b),
                      "skipped_data_hygiene": int(tr.attrs.get("skipped_data_hygiene", 0) or 0)}
        out[var] = r
    return out


# =============================================================================================================================== HG1: hedging a long basket

HG_START = pd.Timestamp("2003-01-02")
HG_PERIODS = (("dev", "2003-01-01", "2017-12-31"), ("val", "2018-01-01", "2023-12-31"))


def _basket() -> pd.Series:
    """Equal-weight daily return of every stock ranked 1-250 by liquidity on the previous session; one-day moves over 50% dropped."""
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet", columns=["sid", "date", "n", "liq_rank", "c"])
    P["date"] = pd.to_datetime(P["date"])
    P = P[P["date"] < CUT].sort_values(["sid", "date"]).reset_index(drop=True)
    consec = (P["sid"] == P["sid"].shift(1)) & (P["n"] == P["n"].shift(1) + 1)
    c = P["c"].astype(float)
    ret = (c / c.shift(1) - 1).where(consec)
    prev_rank = P["liq_rank"].shift(1).where(consec)
    sel = (prev_rank <= 250) & ret.notna() & (ret.abs() < 0.5)
    g = ret[sel].groupby(P.loc[sel, "date"])
    b, cnt = g.mean(), g.count()
    return b[(cnt >= 30) & (b.index >= HG_START)].sort_index()


def _fut_returns(dates: pd.DatetimeIndex, index_ret: pd.Series) -> tuple[pd.Series, int]:
    """Daily return of the Nifty future held overnight: yesterday's nearest contract that does not expire on yesterday, settlement to settlement.
    A missing settlement falls back to the index return (counted)."""
    import duckdb

    files = [str(p) for p in (paths.data_dir() / "silver/fo_bhavcopy").glob("year=*/part.parquet") if int(p.parent.name.split("=")[1]) < 2024]
    con = duckdb.connect()
    df = con.execute(f"select date, expiry, settle from read_parquet({files!r}, union_by_name=true) where instrument = 'FUTIDX' and symbol = 'NIFTY' and settle > 0").df()
    con.close()
    df["date"], df["expiry"] = pd.to_datetime(df["date"]), pd.to_datetime(df["expiry"])
    df = df.groupby(["date", "expiry"], as_index=False)["settle"].mean()
    px = {(d, e): s for d, e, s in zip(df["date"], df["expiry"], df["settle"])}
    by_date = df.groupby("date")["expiry"].apply(list).to_dict()
    out, fallback = [], 0
    for i, d in enumerate(dates):
        if i == 0:
            out.append(0.0)
            continue
        prev = dates[i - 1]
        cands = [e for e in by_date.get(prev, []) if e > prev]
        r = float("nan")
        if cands:
            e = min(cands)
            s0, s1 = px.get((e, prev)), px.get((e, d))
            if s0 and s1:
                r = s1 / s0 - 1
        if r != r or abs(r) > 0.3:
            r = float(index_ret.get(d, 0.0))
            fallback += 1
        out.append(r)
    return pd.Series(out, index=dates), fallback


def _qret(r: pd.Series) -> pd.Series:
    return (1.0 + r).groupby(r.index.to_period("Q")).prod() - 1.0


def _w20_by_quarter(r: pd.Series) -> pd.Series:
    eq = (1.0 + r).cumprod()
    w = eq / eq.shift(20) - 1.0
    return w.groupby(w.index.to_period("Q")).min()


def _period_metrics(r: pd.Series, lo: str, hi: str) -> dict:
    x = r[lo:hi]
    eq = (1.0 + x).cumprod()
    yrs = max(len(x) / 252.0, 0.5)
    cagr = float(eq.iloc[-1] ** (1.0 / yrs) - 1.0) if eq.iloc[-1] > 0 else -1.0
    dd = float((eq / eq.cummax() - 1.0).min())
    w20 = float((eq / eq.shift(20) - 1.0).min())
    q = _qret(x)
    return {"cagr": cagr, "max_drawdown": dd, "return_per_drawdown": float(cagr / abs(dd)) if dd < 0 else None, "worst_20_session": w20, "worst_quarter": float(q.min())}


def _hg1_arms() -> tuple[pd.Series, dict, pd.Series, dict]:
    from india import hedge

    b = _basket()
    nifty = _idx_day("NIFTY 50")["close"].astype(float)
    dates = b.index.intersection(nifty.index)
    b = b.reindex(dates)
    nifty = nifty.reindex(dates)
    # the first session of each period is zero so every arm and the unhedged basket start each period at 1.0, as F06 does
    unh = b.copy()
    for _, lo, hi in HG_PERIODS:
        idx = unh[lo:hi].index
        if len(idx):
            unh.loc[idx[0]] = 0.0
    full_close = _idx_day("NIFTY 50")["close"].astype(float)
    sma = full_close.rolling(200, min_periods=200).mean()
    on = (full_close < sma).shift(1).reindex(dates).fillna(False).astype(float)
    nret = nifty.pct_change().fillna(0.0)
    fut, fallback = _fut_returns(dates, nret)
    chg = on.diff().abs().fillna(0.0)
    arms = {
        "short_futures": unh - on * fut - 0.0003 * chg,
        "cash20": (1.0 - 0.2 * on) * unh - 0.001 * 0.2 * chg,
    }
    puts = hedge._puts()
    cal = pd.read_parquet(paths.data_dir() / "silver/fo_calendar/expiries.parquet")
    monthly = sorted(pd.to_datetime(cal[(cal["symbol"] == "NIFTY") & (cal["instrument"] == "OPTIDX") & cal["is_monthly_last"]]["expiry"]).tolist())
    parts = []
    for _, lo, hi in HG_PERIODS:
        c = (1.0 + unh[lo:hi]).cumprod()
        c = c / c.iloc[0]
        h = hedge.overlay(c, puts, monthly, full_close, 0.05, 1.0)
        parts.append(h.pct_change().fillna(0.0))
    arms["put5otm"] = pd.concat(parts)
    return unh, arms, on, {"futures_fallback_days": int(fallback), "sessions": int(len(dates)), "signal_on_share": float(on.mean())}


def hg1_results(counts_only: bool = False) -> dict:
    s = spec("HG1")
    if counts_only:
        b = _basket()
        y = b.index.year
        return {"basket_sessions": {"events_dev": int((y < SPLIT).sum()), "events_val": int((y >= SPLIT).sum())},
                "variants": list(s["variants"]), "first_session": str(b.index[0].date()), "last_session": str(b.index[-1].date())}
    unh, arms, on, info = _hg1_arms()
    qu, wu = _qret(unh), _w20_by_quarter(unh)
    out = {}
    for var in s["variants"]:
        arm, kind = var.split("|")
        r = arms[arm]
        d = (_qret(r) - qu) if kind == "return" else (_w20_by_quarter(r) - wu)
        d = d.dropna()
        res = {"dev": ts._stat(d[[p.year < SPLIT for p in d.index]]), "val": ts._stat(d[[p.year >= SPLIT for p in d.index]])}
        ext = {"events_dev": res["dev"][2], "events_val": res["val"][2], "arm": arm, "measure": kind, **info}
        for per, lo, hi in HG_PERIODS:
            ext[per] = {"hedged": _period_metrics(r, lo, hi), "unhedged": _period_metrics(unh, lo, hi)}
            ext[per]["signal_on_share"] = float(on[lo:hi].mean())
        res["extra"] = ext
        out[var] = res
    return out


# =============================================================================================================================== run, results pages

FUNCS = {"GP1": gp1_results, "TS1": ts1_results, "HG1": hg1_results}


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
    (paths.manifest_dir() / f"gaplab_{study.lower()}.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    table(study, out)
    return out


TAKEAWAY: dict[str, list[str]] = {      # written after the run of 26 Oct 2026, from the numbers in the tables below
    "GP1": [
        "**The gap rule is not a usable buy call. The stock \"buy the open after a gap-down\" rows pass the bar on paper (bar z 2.81), but they cannot be traded "
        "as defined, and the edge has faded to nothing in the last three years.**",
        "- **Stocks, gap-down of 2% or more at the open (31,064 events in 2000-17, 5,901 in 2018-23):** buying that open and selling the same close beat an "
        "ordinary day by 2.26% in 2000-17 (t 14.7) and by 0.44% in 2018-23 (t 3.0): VALIDATED. Held five sessions: +2.22% and +0.64%; gap-down of 1% or more: "
        "+1.22% and +0.41% (both CONDITIONAL).",
        "- **Why this is not trusted:** the gap is only known once the market has opened, and an order placed then does not fill at the opening price; the "
        "open is often the low of a panic. By year the edge was about +2.6% to +3.2% a trade after costs in 2002-07, about +0.1% to +1.2% in 2015-20, and "
        "zero or negative in 2021-23 (-0.5%, -0.2%, -0.1%). Checked after the run (not registered, no verdict) with an order at the open of the second "
        "five-minute bar (09:20), 2015-23: the gap-down days beat ordinary days by +0.63% in 2015-17 (t 1.6) and +0.17% in 2018-23 (t 1.4), and the trade "
        "itself lost 0.08% after costs; entering at 09:45 the difference is +0.15% and +0.04%. Nothing is left once the price is one a person could get.",
        "- **Gap-ups:** buying the open of a stock that gapped up 2% or more did worse than ordinary days (-1.03%, t -8.2, in 2000-17; -0.07% in 2018-23): OPPOSITE; "
        "the opening print is the high. Buying the next session's open instead did nothing (+0.03% and +0.15%): REJECTED.",
        "- **Nifty and Bank Nifty:** gap-downs of 1% or more were followed by slightly better five-session returns, but not significantly (Bank Nifty "
        "+0.11% and +0.75%, 198 and 62 events: REJECTED); the Nifty has only 38 and 37 such days (INCONCLUSIVE). Gap-ups of 1% or more: no difference. "
        "A 2% gap is too rare on the indices to test. Waiting 30 minutes after the open on the Nifty: 12 events in 2015-17 and 37 in 2018-23, "
        "+0.22% and +0.44%, INCONCLUSIVE (the 5-minute history only starts in 2015).",
        "- **What Ananta does with this:** nothing changes in the paper rules. There is still no gap rule it can use: a gap-down used to bounce at the open, "
        "that was an opening-price effect, it has faded, and it is not available to a person placing an order.",
    ],
    "TS1": [
        "**A trailing stop did not beat a fixed stop. It lost to it in every comparison, and nothing passed the strict bar (z 3.52).**",
        "- **2 ATR trailing against 2 ATR fixed, same entries (114,128 entries in 2000-17, 37,513 in 2018-23):** the trailing stop earned 2.38% less per trade "
        "in 2000-17 (t -2.6) and 1.77% less in 2018-23 (t -1.8): OPPOSITE. On breakout entries: -1.51% and -1.55%; on pullback entries: -2.49% and -3.04% "
        "(t -3.0 and -2.6). A 10% trailing stop against a fixed 7% stop: -1.60% and -0.93%. (The campaigns have breakout, pullback and any-day entries; there is no reversal set.)",
        "- **Why:** a trailing stop is hit almost every time (99% of trades) and the trade ends after 11 days on average, selling strength after the first pullback; "
        "the fixed 2 ATR stop is hit on 64% and holds about 32 days. Net per trade: trailing about zero (-0.05% and +0.06%), fixed 2 ATR +2.21% and +1.83%, "
        "fixed 7% +1.91% and +1.54%. Part of the fixed stops' lead is simply more time invested in a market that rose; the earlier exit test (E02) found no exit rule "
        "beats a time-matched hold, and this does not change that.",
        "- **Against simply selling after 20 sessions:** fixed 7% was +1.24% and +1.20% a trade better (t 2.4 and 1.6) and fixed 2 ATR +1.65% and +1.49% (t 2.2 and 1.8): "
        "INCONCLUSIVE, positive but under the strict bar, and they hold twice as long (28-33 days against 15). Trailing 2 ATR against the 20-session sale: "
        "-0.73% and -0.28%, OPPOSITE; 10% trailing: -0.36% and +0.27%, REJECTED.",
        "- **The tail:** the 7% fixed stop kept the 5th-percentile trade at -8.3% and -7.4%, against -17.0% and -11.8% for the 2 ATR fixed stop, for a similar average. "
        "That is a risk-control argument for a hard stop, not a return edge.",
        "- **What Ananta does with this:** nothing changes in the paper rules (a fixed stop). 'Trail the stop to lock in profit' has no support in 24 years of data "
        "here: on these entries it gave back more than it saved. The stored E02 trade files predate the current data and cost settings, so TS1 recomputed all five "
        "rules on the same entries with current code; the walk was checked to match the exitlab rules.",
    ],
    "HG1": [
        "**None of the three hedges is free. Only holding 20% more cash in a downtrend passes the bar, and it is small; the futures hedge protects most but costs the "
        "most, and the put protected only in 2018-23.**",
        "- **The basket:** an equal-weight daily average of the 250 most liquid stocks, a proxy for a long book (not the paper slots). The Nifty was below its 200-day "
        "average on 22.6% of sessions in 2003-17 and 21.1% in 2018-23. The unhedged basket's worst 20 sessions were -43.8% and -40.7%, its maximum "
        "drawdown -74.2% and -55.1%.",
        "- **20% more cash below the 200-day (CONDITIONAL):** the worst 20-session stretch in a quarter was 0.66% shallower (t 3.7 in 2003-17, t 1.9 in 2018-23); the "
        "return given up was 0.21% and 0.40% a quarter (not significant): growth 22.5% to 22.4% a year and 11.0% to 10.0%. The maximum drawdown only moved from -74.2% "
        "to -68.1% and from -55.1% to -52.8%: a little protection for a little cost.",
        "- **Short Nifty futures equal to the basket below the 200-day (INCONCLUSIVE):** the worst 20 sessions fell from -43.8% to -31.7% (2003-17) and from -40.7% "
        "to -16.1% (2018-23), the maximum drawdown from -74.2% to -55.1% and from -55.1% to -45.0%. It cost 1.09% and 1.70% a quarter (growth 22.5% to 19.1% and "
        "11.0% to 5.6% a year): return per unit of drawdown improved in 2003-17 (0.30 to 0.35) and worsened in 2018-23 (0.20 to 0.12). The development quarter test passed "
        "(t 3.0) but 2018-23 did not (t 1.5).",
        "- **Monthly 5%-out-of-the-money Nifty put (REJECTED):** in 2018-23 it cut the worst 20 sessions to -15.2% and the maximum drawdown to -39.0% and raised return per "
        "drawdown (0.20 to 0.25), but in 2003-17 it did not help the average quarter (-0.42%, t -1.2) and the maximum drawdown stayed -74.0%; it cost 0.10% and 0.68% a quarter. "
        "That is F06's result again (always-on puts rejected).",
        "- **What Ananta does with this:** nothing changes in the paper rules. If a hedge is ever added, the cash version is the only one that earned its place on this "
        "evidence, and it should be tested on the real slots on the forward paper book first. The futures proxy used the actual nearest-month settlement prices.",
    ],
}


def _f(x, pct: bool = True) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{100 * x:+.2f}%" if pct else f"{x:+.2f}"


def table(study: str, out: dict | None = None) -> Path:
    if out is None:
        out = json.loads((paths.manifest_dir() / f"gaplab_{study.lower()}.json").read_text())
    s = spec(study)
    L = [f"# {study} results: {s['title']}", "", f"Registered {out['registered_at']} (spec `{study.lower()}_v1.json`, written before the run); family {s['family']}, "
         f"k = {out['k']}, z = {registry.threshold(out['k']):.2f}. Development to 2017, validation 2018-2023; nothing from 2024 on.", ""]
    if TAKEAWAY.get(study):
        L += ["## In plain words", ""] + TAKEAWAY[study] + ["", "## The rows", ""]
    L += ["Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in development and the same way in "
          "2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.", "",
          "| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        e = r["extra"] or {}
        d, v = r["dev"], r["val"]
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else '-'} | {r['verdict']} | {_f(d[0])} | {_f(d[1], False)} | {d[2]} | {_f(v[0])} | {_f(v[1], False)} | {v[2]} | "
                 f"{e.get('events_dev', 'n/a')} / {e.get('events_val', 'n/a')} |")
    if study == "GP1":
        L += ["", "## The trade itself after costs (stocks)", "", "| variant | mean net per trade, all years | dev: quarter-mean t | val: quarter-mean t |", "|---|---|---|---|"]
        for r in out["rows"]:
            e = r["extra"] or {}
            if r["variant"].startswith("STK") and e.get("trade_after_costs_dev"):
                L.append(f"| {r['variant']} | {_f(e.get('mean_net_per_trade'))} | {_f(e['trade_after_costs_dev'][0])} (t {_f(e['trade_after_costs_dev'][1], False)}) | "
                         f"{_f(e['trade_after_costs_val'][0])} (t {_f(e['trade_after_costs_val'][1], False)}) |")
        dg = paths.manifest_dir() / "gaplab_gp1_diag.json"
        if dg.exists():
            D = json.loads(dg.read_text())
            L += ["", "## Diagnostic after the run (not registered, no verdict): is the open-price edge tradable?", "",
                  "Stock gap-down of 2% or more, liquid 250, bought at the open and sold at the close of the same day, after costs, by year:", "",
                  "| year | events | event mean (hold 1) | ordinary day mean | event mean (hold 5) | ordinary mean (hold 5) |", "|---|---|---|---|---|---|"]
            for y, v in sorted(D["yearly_open_entries"].items()):
                L.append(f"| {y} | {v['events']} | {_f(v['event_mean_hold1'])} | {_f(v['ordinary_mean_hold1'])} | {_f(v['event_mean_hold5'])} | {_f(v['ordinary_mean_hold5'])} |")
            L += ["", "The same days entered at the open of the second five-minute bar (09:20) or of the 09:45 bar and sold at the close, stocks in the 5-minute history only, "
                  "against every 5th session of the same stocks (quarters; development 2015-17 holds 12 quarters):", "",
                  "| entry | events | mean net per trade | ordinary day mean | vs ordinary 2015-17 (t) | vs ordinary 2018-23 (t) |", "|---|---|---|---|---|---|"]
            for k, lab in (("i0920", "09:20 bar open"), ("i0945", "09:45 bar open")):
                e = D["executable_5m"][k]
                dv, vl = e["vs_ordinary_days_dev_2015_17"], e["vs_ordinary_days_val_2018_23"]
                L.append(f"| {lab} | {e['events']} | {_f(e['mean_net_per_trade'])} | {_f(e['ordinary_mean'])} | {_f(dv[0])} ({_f(dv[1], False)}) | {_f(vl[0])} ({_f(vl[1], False)}) |")
    elif study == "TS1":
        L += ["", "## Mean net return per trade, by rule (same entries)", "", "| variant | rule | dev mean | dev stopped | dev days | dev p5 | val mean | val stopped | val days | val p5 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for r in out["rows"]:
            e = r["extra"] or {}
            for key in ("a", "b"):
                x = e.get(key)
                if not x:
                    continue
                dv, vl = x["dev"], x["val"]
                L.append(f"| {r['variant']} | {e['rule_' + key]} | {_f(dv['mean_net'])} | {_f(dv['stopped_share'], True)} | {dv['mean_days']:.1f} | {_f(dv['p5'])} | "
                         f"{_f(vl['mean_net'])} | {_f(vl['stopped_share'], True)} | {vl['mean_days']:.1f} | {_f(vl['p5'])} |")
    elif study == "HG1":
        L += ["", "## The whole-period picture (unhedged basket against each arm)", "",
              "| arm | period | signal on | CAGR unhedged | CAGR hedged | max drawdown unhedged | max drawdown hedged | worst 20 sessions unhedged | worst 20 sessions hedged | CAGR / max drawdown unhedged | hedged |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in out["rows"]:
            e = r["extra"] or {}
            if e.get("measure") != "return":
                continue
            for per in ("dev", "val"):
                x = e[per]
                h, u = x["hedged"], x["unhedged"]
                L.append(f"| {e['arm']} | {per} | {_f(x['signal_on_share'])} | {_f(u['cagr'])} | {_f(h['cagr'])} | {_f(u['max_drawdown'])} | {_f(h['max_drawdown'])} | "
                         f"{_f(u['worst_20_session'])} | {_f(h['worst_20_session'])} | {_f(u['return_per_drawdown'], False)} | {_f(h['return_per_drawdown'], False)} |")
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
            print(st, json.dumps(check(st), indent=1, default=str))
    elif cmd == "run":
        for st in studies_:
            o = run(st)
            for r in o["rows"]:
                print(st, r["variant"], r["verdict"], r["dev"], r["val"], (r["extra"] or {}).get("events_dev"), (r["extra"] or {}).get("events_val"), flush=True)
    elif cmd == "diag":
        print(json.dumps(_clean(gp1_diagnostic()), indent=1))
    elif cmd == "table":
        for st in studies_:
            print(table(st))
    else:
        print(__doc__)
