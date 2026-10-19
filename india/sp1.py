"""SP1: Scenario Playbook phase 1, index intraday playbook (registrations/sp1_v2.json, frozen 19 Oct 2026).

  python -m india.sp1 selftest      hand-built paths for the exits and the option leg
  python -m india.sp1 outcomes      every action's outcome per index, day and decision point, 2015-2023 (silver/gold only):
                                    gold/studies/SP1_outcomes.parquet (no learning, no policy, no ledger)
  python -m india.sp1 run           learning, policy, tests, nulls, book, ledger rows, report (needs outcomes)

Outcomes: for each of NIFTY / BANKNIFTY, each session in gold/scenario/index_states.parquet, each decision point (D0 09:15 -> fill at the 09:16
open +2 ticks; D1 09:30; D2 09:45; D3 10:15) and each of the 12 actions (2 directions x 6 exits; ORSTOP not at D0 and only when its stop is on the
right side of the entry by >= 0.1 daily ATR14): the future-proxy gross bps, its dated cost in bps, and the synthetic option leg (EXPLORATORY).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import costs, greeks, ocstudy, paths

HERE = Path(__file__).parent
SPEC = HERE / "registrations" / "sp1_v2.json"
IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
TICK = 0.05
NMIN = 375
POINT_ENTRY = {"D0": 1, "D1": 15, "D2": 30, "D3": 60}      # entry bar (minutes after 09:15) per decision point
EXIT_1130, EXIT_1515 = 135, 360
EXITS = ("T1130", "T1515", "ORSTOP", "ATRSTOP", "TRAIL", "NEXTOPEN")
ACTIONS = [(x, d) for x in EXITS for d in (1, -1)]           # fixed order: the action id is the position (tie-break: lower id)
OPT_HALF = {"NIFTY": 0.5, "BANKNIFTY": 1.0}
WEEKLY_FROM = {"NIFTY": dt.date(2019, 2, 11), "BANKNIFTY": dt.date(2016, 5, 27)}
MIN_PER_YEAR = 365 * 24 * 60
YEARS = list(range(2015, 2024))


def spec_sha() -> str:
    return hashlib.sha256(SPEC.read_bytes()).hexdigest()[:16]


# ----------------------------------------------------------------------------------------------------------------------------- exits
def trail_exit(O, H, L, e, d, k, X):
    """Chandelier trail: level = best price since entry (entry price included, bars before t) -/+ k; checked from the entry bar; a bar that
    opens beyond the level fills at its open. Time exit at the open of bar X. Returns exit price, exit bar, stopped."""
    n, T = O.shape
    rows = np.arange(n)
    cols = np.arange(T)[None, :]
    has = (e >= 0) & (e < X)
    ee = np.where(has, e, X)
    live = (cols >= ee[:, None]) & (cols < X) & has[:, None]
    entry = O[rows, np.clip(ee, 0, T - 1)]
    if True:
        hi = np.where(cols >= ee[:, None], H, -np.inf)
        lo = np.where(cols >= ee[:, None], L, np.inf)
        run_hi = np.maximum.accumulate(hi, axis=1)
        run_lo = np.minimum.accumulate(lo, axis=1)
        prev_hi = np.concatenate([np.full((n, 1), -np.inf), run_hi[:, :-1]], axis=1)
        prev_lo = np.concatenate([np.full((n, 1), np.inf), run_lo[:, :-1]], axis=1)
        best_l = np.maximum(prev_hi, entry[:, None])
        best_s = np.minimum(prev_lo, entry[:, None])
        lvl = np.where(d[:, None] > 0, best_l - k[:, None], best_s + k[:, None])
    hit = live & np.where(d[:, None] > 0, L <= lvl, H >= lvl)
    th = ocstudy.first_true(hit)
    stopped = th >= 0
    tc = np.clip(th, 0, T - 1)
    lv = lvl[rows, tc]
    ot = O[rows, tc]
    fill = np.where(d > 0, np.minimum(ot, lv), np.maximum(ot, lv))
    px = np.where(stopped, fill, O[rows, min(X, T - 1)])
    tx = np.where(stopped, th, X)
    return np.where(has, px, np.nan), np.where(has, tx, -1), stopped & has


# ----------------------------------------------------------------------------------------------------------------------------- data
def _chains(syms=("NIFTY", "BANKNIFTY")) -> pd.DataFrame:
    D = paths.data_dir()
    files = [str(D / "silver/fo_greeks" / f"year={y}" / "part.parquet") for y in range(2014, 2024) if (D / "silver/fo_greeks" / f"year={y}" / "part.parquet").exists()]
    con = duckdb.connect()
    df = con.execute(f"""select date, symbol, expiry, strike, opt_type, fwd, iv, coalesce(volume, 0) as volume
                         from read_parquet({files!r}) where list_contains(?, symbol)""", [list(syms)]).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["expiry"] = pd.to_datetime(df["expiry"]).dt.date
    return df


class OptionBook:
    """Previous-session chain per (symbol, trade date): the expiry (nearest strictly after the trade date), listed strikes, traded IVs, carry."""

    def __init__(self, chains: pd.DataFrame, prev_session: dict, prev_close: dict):
        self.by = {k: g for k, g in chains.groupby(["symbol", "date"])}
        self.prev = prev_session
        self.pc = prev_close  # (symbol, date) -> index close of that date

    def setup(self, sym: str, day: dt.date):
        p = self.prev.get(day)
        g = self.by.get((sym, p)) if p else None
        if g is None or g.empty:
            return None
        ex = sorted(e for e in g["expiry"].unique() if e > day)
        if not ex:
            return None
        e = ex[0]
        c = g[g["expiry"] == e]
        spot_prev = self.pc.get((sym, p))
        fwd = c["fwd"].dropna()
        if spot_prev is None or fwd.empty:
            return None
        out = {"expiry": e, "carry": float(fwd.median()) / spot_prev, "listed": np.sort(c["strike"].unique())}
        for t in ("CE", "PE"):
            x = c[(c["opt_type"] == t) & (c["volume"] > 0) & c["iv"].notna() & (c["iv"] > 0)]
            out[t] = (x["strike"].to_numpy(), x["iv"].to_numpy())
        return out


def _t_years(day: dt.date, minute: int, expiry: dt.date) -> float:
    now = dt.datetime.combine(day, dt.time(9, 15)) + dt.timedelta(minutes=int(minute))
    end = dt.datetime.combine(expiry, dt.time(15, 30))
    return max((end - now).total_seconds() / 60.0, 1.0) / MIN_PER_YEAR


def option_leg(sym, day, setup, d, spot_in, m_in, spot_out, day_out, m_out, stopped, lot, spread_mult=1.0):
    """Synthetic ATM option bought at entry, sold at the index exit. Returns dict or None (no chain / no traded IV)."""
    if setup is None or not (spot_in == spot_in and spot_out == spot_out):
        return None
    typ = "CE" if d > 0 else "PE"
    K = float(setup["listed"][np.abs(setup["listed"] - spot_in).argmin()])
    ks, ivs = setup[typ]
    if len(ks) == 0:
        return None
    iv = float(ivs[np.abs(ks - K).argmin()]) if K not in ks else float(ivs[ks == K][0])
    e = setup["expiry"]
    car = setup["carry"]
    p_in = float(greeks.black76(np.array([spot_in * car]), np.array([K]), np.array([_t_years(day, m_in, e)]), np.array([iv]), np.array([typ == "CE"]))[0][0])
    p_out = float(greeks.black76(np.array([spot_out * car]), np.array([K]), np.array([_t_years(day_out, m_out, e)]), np.array([iv]), np.array([typ == "CE"]))[0][0])
    p_in, p_out = max(p_in, 0.05), max(p_out, 0.05)
    h_in = max(OPT_HALF[sym], 0.0025 * p_in) * spread_mult
    h_out = max(OPT_HALF[sym], 0.0025 * p_out) * spread_mult * (2.0 if stopped else 1.0)
    buy, sell = (p_in + h_in), max(p_out - h_out, 0.0)
    fees = costs.cost("options", "buy", buy * lot, day.year, when=day) + costs.cost("options", "sell", sell * lot, day_out.year, when=day_out)
    net = (sell - buy) * lot - fees
    return {"opt_K": K, "opt_iv": iv, "opt_expiry": e, "opt_dte": (e - day).days, "opt_prem_in": p_in, "opt_prem_out": p_out,
            "opt_net_rs": net, "opt_ret": net / (p_in * lot) if p_in > 0 else np.nan}


# ----------------------------------------------------------------------------------------------------------------------------- outcomes
def outcomes(log=print) -> pd.DataFrame:
    D = paths.data_dir()
    days_all, specials = ocstudy._calendar()
    nxt = {days_all[i]: days_all[i + 1] for i in range(len(days_all) - 1)}
    prv = {days_all[i]: days_all[i - 1] for i in range(1, len(days_all))}
    st = pd.read_parquet(D / "gold/scenario/index_states.parquet")
    index = ocstudy.load_index()
    lots = ocstudy.load_lots()
    lot = lots.set_index(["date", "symbol"])["lot"].to_dict()
    log("loading option chains (previous-session IV, silver/fo_greeks 2014-2023)")
    chains = _chains()
    pc = {}
    for sym, name in IDX.items():
        a = index[name]
        for i, d in enumerate(a["dates"]):
            pc[(sym, d)] = float(a["close"][i, -1])
    ob = OptionBook(chains, prv, pc)
    rows = []
    for sym, name in IDX.items():
        a = index[name]
        pos = {d: i for i, d in enumerate(a["dates"])}
        s = st[st["index"] == sym].sort_values("date").reset_index(drop=True)
        dd = list(s["date"])
        sel = np.array([pos[d] for d in dd])
        O, H, L, C = (a[f][sel] for f in ("open", "high", "low", "close"))
        nd = len(dd)
        atr = s["atr14_prev"].to_numpy(float)
        # next session's 09:16 open for NEXTOPEN (only when the calendar's next session is a usable session for this index)
        nx_open = np.array([a["open"][pos[nxt[d]], 1] if (d in nxt and nxt[d] in pos and a["ok"][pos[nxt[d]]] and nxt[d] not in specials) else np.nan for d in dd])
        nx_day = [nxt.get(d) for d in dd]
        orh, orl = H[:, :15].max(1), L[:, :15].min(1)
        h5 = H.reshape(nd, 75, 5).max(2)
        l5 = L.reshape(nd, 75, 5).min(2)
        c5 = C.reshape(nd, 75, 5)[:, :, -1]
        tr = ocstudy.tr5(h5, l5, c5)
        prev_tail = np.vstack([np.full((1, 14), np.nan), tr[:-1, -14:]])
        setups = [ob.setup(sym, d) for d in dd]
        lots_d = np.array([lot.get((d, sym), np.nan) for d in dd])
        for P, e0 in POINT_ENTRY.items():
            e = np.full(nd, e0)
            entry = O[:, e0]
            atr5 = ocstudy.atr_at(tr, prev_tail, e // 5)
            for aid, (X, dirc) in enumerate(ACTIONS):
                d = np.full(nd, dirc)
                avail = np.ones(nd, bool)
                if X == "ORSTOP":
                    if P == "D0":
                        continue
                    stop = np.where(d > 0, orl, orh)
                    dist = np.where(d > 0, entry - stop, stop - entry)
                    avail = dist >= 0.1 * atr
                    px, tx, stp, _, _ = ocstudy.simulate(O, H, L, np.where(avail, e, -1), d, stop, EXIT_1515)
                elif X in ("T1130", "T1515"):
                    stop = np.where(d > 0, -np.inf, np.inf)
                    px, tx, stp, _, _ = ocstudy.simulate(O, H, L, e, d, stop, EXIT_1130 if X == "T1130" else EXIT_1515)
                elif X == "ATRSTOP":
                    stop = entry - d * 0.5 * atr
                    px, tx, stp, _, _ = ocstudy.simulate(O, H, L, e, d, stop, EXIT_1515)
                elif X == "TRAIL":
                    px, tx, stp = trail_exit(O, H, L, e, d, 3.0 * atr5, EXIT_1515)
                else:  # NEXTOPEN: intraday stop 1 x ATR to the close, else the next session's 09:16 open
                    pad = lambda A, v: np.concatenate([A, v[:, None]], axis=1)
                    stop = entry - d * 1.0 * atr
                    Op, Hp, Lp = pad(O, nx_open), pad(H, nx_open), pad(L, nx_open)
                    px, tx, stp, _, _ = ocstudy.simulate(Op, Hp, Lp, e, d, stop, NMIN)
                    avail = avail & (stp | ~np.isnan(nx_open))
                ok = avail & ~np.isnan(px) & ~np.isnan(atr)
                gross = d * (px - entry) / entry * 1e4
                ticks = 2 + (2 if P == "D0" else 0) + (2 if (X == "NEXTOPEN") else 0) * (~stp)
                for i in np.where(ok)[0]:
                    day = dd[i]
                    nextday = (X == "NEXTOPEN") and not stp[i]
                    day_out = nx_day[i] if nextday else day
                    m_out = 1 if nextday else int(tx[i])
                    lt = lots_d[i]
                    bv, sv = (entry[i] * lt, px[i] * lt) if dirc > 0 else (px[i] * lt, entry[i] * lt)
                    fees = costs.cost("futures", "buy", bv, day.year, when=day) + costs.cost("futures", "sell", sv, day.year, when=day)
                    cost_bps = (fees / lt + ticks[i] * TICK) / entry[i] * 1e4
                    r = {"date": day, "year": day.year, "index": sym, "point": P, "action": aid, "exit": X, "dir": dirc, "entry": float(entry[i]),
                         "exit_px": float(px[i]), "exit_min": int(tx[i]), "next_day": bool(nextday), "stopped": bool(stp[i]), "gross_bps": float(gross[i]),
                         "cost_bps": float(cost_bps), "lot": float(lt), "era": "weekly" if day >= WEEKLY_FROM[sym] else "monthly"}
                    leg = option_leg(sym, day, setups[i], dirc, float(entry[i]), e0, float(px[i]), day_out, m_out, bool(stp[i]), lt)
                    if leg:
                        r.update(leg)
                        leg2 = option_leg(sym, day, setups[i], dirc, float(entry[i]), e0, float(px[i]), day_out, m_out, bool(stp[i]), lt, spread_mult=2.0)
                        r["opt_net_rs_x2"], r["opt_ret_x2"] = leg2["opt_net_rs"], leg2["opt_ret"]
                    rows.append(r)
            log(f"{sym} {P}: {len(rows):,} outcome rows")
    out = pd.DataFrame(rows)
    out["net_bps"] = out["gross_bps"] - out["cost_bps"]
    out.to_parquet(D / "gold/studies/SP1_outcomes.parquet", index=False)
    summ = {"rows": len(out), "spec_sha": spec_sha(), "by_index_point": out.groupby(["index", "point"]).size().to_dict(),
            "option_leg_share": round(float(out["opt_ret"].notna().mean()), 4) if "opt_ret" in out else 0.0,
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (D / "manifests/sp1_outcomes.json").write_text(json.dumps({k: (str(v) if isinstance(v, dict) else v) for k, v in summ.items()}, indent=1))
    return out


# ----------------------------------------------------------------------------------------------------------------------------- selftest
def selftest() -> dict:
    T = 30
    O = np.full((1, T), 100.0); H = O + 0.2; L = O - 0.2
    # long trail with k=1: entry 100 at bar 2; highs rise to 103 by bar 6 (best 103), bar 8 low 101.9 <= 102 -> stopped at 102
    for t, v in zip(range(3, 7), (101, 102, 102.5, 103)):
        O[0, t] = v; H[0, t] = v; L[0, t] = v - 0.1
    O[0, 7] = 102.6; H[0, 7] = 102.7; L[0, 7] = 102.4
    O[0, 8] = 102.3; H[0, 8] = 102.4; L[0, 8] = 101.9
    px, tx, st = trail_exit(O, H, L, np.array([2]), np.array([1]), np.array([1.0]), 20)
    assert st[0] and tx[0] == 8 and abs(px[0] - 102.0) < 1e-9, (px, tx, st)
    # gap below the trail fills at the open
    O2, L2 = O.copy(), L.copy()
    O2[0, 8] = 101.5; L2[0, 8] = 101.4
    px, tx, st = trail_exit(O2, H, L2, np.array([2]), np.array([1]), np.array([1.0]), 20)
    assert st[0] and abs(px[0] - 101.5) < 1e-9
    # short mirror
    px, tx, st = trail_exit(200 - O, 200 - L, 200 - H, np.array([2]), np.array([-1]), np.array([1.0]), 20)
    assert st[0] and tx[0] == 8 and abs(px[0] - 98.0) < 1e-9, (px, tx)
    # no hit -> time exit at the open of X
    px, tx, st = trail_exit(O, H, L, np.array([2]), np.array([1]), np.array([50.0]), 20)
    assert (not st[0]) and tx[0] == 20 and abs(px[0] - O[0, 20]) < 1e-9
    # option: ATM call ~ 0.4 F sigma sqrt(T) (r small), and a long call gains when the index rises
    F, sig, Tt = 20000.0, 0.15, 7 / 365
    c = float(greeks.black76(np.array([F]), np.array([F]), np.array([Tt]), np.array([sig]), np.array([True]))[0][0])
    assert abs(c - 0.3989 * F * sig * math.sqrt(Tt)) / c < 0.02, c
    setup = {"expiry": dt.date(2023, 1, 12), "carry": 1.0, "listed": np.array([17900.0, 18000.0, 18100.0]),
             "CE": (np.array([18000.0]), np.array([0.14])), "PE": (np.array([18000.0]), np.array([0.15]))}
    up = option_leg("NIFTY", dt.date(2023, 1, 9), setup, 1, 18010.0, 15, 18150.0, dt.date(2023, 1, 9), 360, False, 50)
    dn = option_leg("NIFTY", dt.date(2023, 1, 9), setup, 1, 18010.0, 15, 17900.0, dt.date(2023, 1, 9), 360, True, 50)
    assert up["opt_K"] == 18000.0 and up["opt_net_rs"] > 0 > dn["opt_net_rs"], (up, dn)
    # time decay: an unchanged index loses value over the day
    fl = option_leg("NIFTY", dt.date(2023, 1, 9), setup, 1, 18010.0, 15, 18010.0, dt.date(2023, 1, 9), 360, False, 50)
    assert fl["opt_prem_out"] < fl["opt_prem_in"]
    # action list: 12 actions, the fixed order
    assert len(ACTIONS) == 12 and ACTIONS[0] == ("T1130", 1) and ACTIONS[-1] == ("NEXTOPEN", -1)
    return {"selftest": "PASS", "spec_sha": spec_sha()}


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        print(selftest())
    elif cmd == "outcomes":
        o = outcomes(lambda s: print(f"[{dt.datetime.now():%H:%M:%S}] {s}", flush=True))
        print(len(o))
    else:
        raise SystemExit(__doc__)
