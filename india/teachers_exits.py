"""Trade With Trend exit cards on breakout entries (registered in india/teachers.py): TWT-H22 staged stop, H23 structure exits, H24 three-step exit.

Entries: the teachers' 60-session breakouts (india/teachers.Ctx.brk), bought at the next session's open. Paths come from the full daily history of each
stock (gold/features: adjusted bars), so a stock that later leaves the liquid 500 is still followed. A stop fills at the stop price, or at the open when
the open is already through it; a close-based exit fills at the next open. Every comparison is per trade (rule A minus rule B, gross: both rules pay
the same delivery round trip, the extra partial sells cost no brokerage at Zerodha), with t across calendar-quarter means. A trade whose window holds
a one-day move over 50% (an unadjusted corporate action) is skipped.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from india import paths
from india import teachers as T

_X: dict = {}


def _paths() -> dict:
    if "p" in _X:
        return _X["p"]
    f = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=["sid", "date", "o", "h", "l", "c"])
    f["date"] = pd.to_datetime(f["date"])
    f = f[f["date"] < "2024-01-01"].sort_values(["sid", "date"])
    out = {}
    for sid, g in f.groupby("sid", sort=False):
        o, h, l, c = (g[k].to_numpy(float) for k in ("o", "h", "l", "c"))
        ls = pd.Series(l)
        piv = (ls.shift(2) < ls.shift(3)) & (ls.shift(2) < ls.shift(4)) & (ls.shift(2) < ls.shift(1)) & (ls.shift(2) < ls)
        lpl = ls.shift(2).where(piv).ffill().to_numpy(float)          # latest confirmed swing low, known at each close
        sma50 = pd.Series(c).rolling(50, min_periods=50).mean().to_numpy(float)
        jump = np.r_[False, np.abs(c[1:] / c[:-1] - 1) > 0.5]
        out[sid] = {"d": g["date"].to_numpy(), "o": o, "h": h, "l": l, "c": c, "lpl": lpl, "sma50": sma50, "jump": jump}
    _X["p"] = out
    return out


def _entries(P) -> pd.DataFrame:
    s = P.s
    e = s.loc[P.brk, ["sid", "date", "breadth200"]].copy()
    return e


def _first(mask: np.ndarray) -> int:
    """Index of the first True, or -1."""
    i = int(np.argmax(mask)) if mask.size else 0
    return i if mask.size and mask[i] else -1


def _stop_exit(o, l, entry, lvl, end_close):
    """Exit price of a stop at lvl over the window (o, l arrays from day 1), or the end close."""
    i = _first(l <= lvl)
    if i < 0:
        return end_close
    return min(o[i], lvl)


def _walk(P, horizon: int):
    """Yield (row, arrays sliced from the entry day [day 1 .. day horizon], entry price) for each breakout with a clean full window."""
    pp = _paths()
    for r in _entries(P).itertuples(index=False):
        a = pp.get(r.sid)
        if a is None:
            continue
        j = int(np.searchsorted(a["d"], np.datetime64(r.date)))
        if j >= len(a["d"]) or a["d"][j] != np.datetime64(r.date) or j + horizon + 1 >= len(a["d"]):
            continue
        sl = slice(j + 1, j + horizon + 1)
        if a["jump"][sl].any():
            continue
        entry = a["o"][j + 1]
        if not entry > 0:
            continue
        yield r, a, j, sl, entry


@T.test("TWT-H22")
def _(P):
    rows = []
    for r, a, j, sl, E in _walk(P, 60):
        o, l, c = a["o"][sl], a["l"][sl], a["c"][sl]
        res = {"date": r.date, "weak": r.breadth200 < 0.40 if r.breadth200 == r.breadth200 else False}
        for H in (20, 60):
            oo, ll, end = o[:H], l[:H], c[H - 1]
            single = _stop_exit(oo, ll, E, E * 0.93, end) / E - 1
            staged = np.mean([_stop_exit(oo, ll, E, E * (1 - x), end) for x in (0.03, 0.05, 0.07)]) / E - 1
            res[f"st_vs_si_{H}"] = staged - single
            if H == 60:
                res["si_vs_none_60"] = single - (end / E - 1)
        rows.append(res)
    df = pd.DataFrame(rows)
    out = {"staged_vs_single|hold20": T.ts.absolute(df, pd.Series(True, index=df.index), "st_vs_si_20"),
           "staged_vs_single|hold60": T.ts.absolute(df, pd.Series(True, index=df.index), "st_vs_si_60"),
           "single7_vs_none|hold60": T.ts.absolute(df, pd.Series(True, index=df.index), "si_vs_none_60")}
    w = df[df["weak"]].reset_index(drop=True)
    out["staged_vs_single|hold60|weak_breadth"] = T.ts.absolute(w, pd.Series(True, index=w.index), "st_vs_si_60")
    return out


@T.test("TWT-H23")
def _(P):
    rows = []
    for r, a, j, sl, E in _walk(P, 121):
        o, h, l, c, lpl = a["o"][sl], a["h"][sl], a["l"][sl], a["c"][sl], a["lpl"][sl]
        stop0 = a["lpl"][j]
        if not (stop0 == stop0) or stop0 >= E:
            continue
        # structure: initial stop at the swing low below entry (intraday), then exit at the next open after a close below the latest swing low
        hit0 = _first(l[:120] <= stop0)
        brk = _first(c[:119] < lpl[:119])
        if hit0 >= 0 and (brk < 0 or hit0 <= brk):
            px = min(o[hit0], stop0)
        elif brk >= 0:
            px = o[brk + 1]
        else:
            px = c[119]
        structure = px / E - 1
        # (a) +15% target, -7% stop, stop first when both touch the same day
        t_hit, s_hit = _first(h[:120] >= E * 1.15), _first(l[:120] <= E * 0.93)
        if s_hit >= 0 and (t_hit < 0 or s_hit <= t_hit):
            pa = min(o[s_hit], E * 0.93)
        elif t_hit >= 0:
            pa = max(o[t_hit], E * 1.15)
        else:
            pa = c[119]
        # (b) tight -3% stop, otherwise held to day 60
        pb = _stop_exit(o[:60], l[:60], E, E * 0.97, c[59])
        rows.append({"date": r.date, "vs_a": structure - (pa / E - 1), "vs_b": structure - (pb / E - 1)})
    df = pd.DataFrame(rows)
    allm = pd.Series(True, index=df.index)
    return {"vs_target15_stop7": T.ts.absolute(df, allm, "vs_a"), "vs_tight3": T.ts.absolute(df, allm, "vs_b")}


@T.test("TWT-H24")
def _(P):
    rows = []
    for r, a, j, sl, E in _walk(P, 251):
        o, h, c, lpl, sma = a["o"][sl], a["h"][sl], a["c"][sl], a["lpl"][sl], a["sma50"][sl]
        s0 = _first(c[:250] >= 1.30 * E)
        if s0 < 0 or s0 >= 248:
            continue
        end = c[249]
        idx = np.arange(250)
        after = idx > s0

        def first_after(mask):
            m = mask & after
            m[249] = False
            return _first(m)
        k50 = first_after(c[:250] < sma[:250])
        kpl = first_after(c[:250] < lpl[:250])
        k40 = _first((h[:250] >= 1.40 * E) & (idx >= s0))
        p40 = max(o[k40], 1.40 * E) if k40 >= 0 else end
        p50 = o[k50 + 1] if k50 >= 0 else end
        ppl = o[kpl + 1] if kpl >= 0 else end
        three = 0.30 * p40 + 0.35 * p50 + 0.35 * ppl
        rows.append({"date": r.date, "vs_hold": (three - end) / E, "vs_50": (three - p50) / E})
    df = pd.DataFrame(rows)
    allm = pd.Series(True, index=df.index)
    return {"vs_hold250": T.ts.absolute(df, allm, "vs_hold"), "vs_full_50dma": T.ts.absolute(df, allm, "vs_50")}
