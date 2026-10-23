"""Sizing v2 (registrations/sz2_v1.json, frozen 19 Oct 2026). This module so far holds the pre-run step the spec requires before any selection:

  python -m india.sz2 margincheck     margin.check: the conservative margin proxy for a debit vertical against Kite's own margin calculator
                                      (POST /margins/basket, a calculation that places nothing; approved by Madhav 19 Oct 2026 21:01) for 5 baskets,
                                      both indices, both widths, at today's contracts; where the proxy is below Kite's figure it is raised to it
                                      (a per-index multiplier, recorded once in manifests/sz2_margin_check.json; the spec allows no later change)

The study run itself (structures, max loss per lot, the survival bootstraps, the selection) is built next, after this check.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

from india import kite, paths, sp1paper

STEP = {"NIFTY": 50, "BANKNIFTY": 100}
WIDTH = {"NIFTY": {"narrow": 100, "wide": 200}, "BANKNIFTY": {"narrow": 300, "wide": 500}}
SPOT = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
ELM = 0.02


def _sessions_left(trade_day: dt.date, expiry: dt.date, hol: set) -> int:
    """Sessions after the trade day up to and including the expiry session (contracts.expiry)."""
    n, d = 0, trade_day + dt.timedelta(days=1)
    while d <= expiry:
        if d.weekday() < 5 and d not in hol:
            n += 1
        d += dt.timedelta(days=1)
    return n


def expiry_for(nfo: list[dict], sym: str, trade_day: dt.date, hol: set, nextopen: bool = False, skip: int = 0) -> str:
    """contracts.expiry: NIFTY the nearest with >= 2 sessions left (3 for NEXTOPEN); BANKNIFTY monthly only, the current month's if it has enough
    sessions left, else the next month's. skip: take the next qualifying expiry instead (the fifth basket)."""
    need = 3 if nextopen else 2
    exps = sorted({r["expiry"] for r in nfo if r["name"] == sym and r["instrument_type"] in ("CE", "PE") and r["expiry"] > trade_day.isoformat()})
    if sym == "BANKNIFTY":
        by_month: dict = {}
        for e in exps:
            by_month.setdefault(e[:7], []).append(e)
        exps = sorted(max(v) for v in by_month.values())     # the last expiry of each month is the monthly
    ok = [e for e in exps if _sessions_left(trade_day, dt.date.fromisoformat(e), hol) >= need]
    return ok[skip]


def margincheck(log=print) -> dict:
    from india import dayplan

    k = kite.Kite()
    nfo = sp1paper._instruments(k, "NFO")
    hol = dayplan.holidays()
    trade_day = dayplan.next_session()
    q = k.get("/quote/ltp", params=[("i", f"NSE:{SPOT[s]}") for s in SPOT])
    spot = {s: float(q[f"NSE:{SPOT[s]}"]["last_price"]) for s in SPOT}
    baskets = [("NIFTY", "narrow", "CE", 0), ("NIFTY", "wide", "PE", 0), ("BANKNIFTY", "narrow", "PE", 0), ("BANKNIFTY", "wide", "CE", 0), ("NIFTY", "narrow", "PE", 1)]
    out = []
    for sym, wname, typ, skip in baskets:
        e = expiry_for(nfo, sym, trade_day, hol, skip=skip)
        rows = [r for r in nfo if r["name"] == sym and r["expiry"] == e and r["instrument_type"] == typ]
        strikes = sorted(float(r["strike"]) for r in rows)
        K1 = min(strikes, key=lambda x: (abs(x - spot[sym]), x))
        W = WIDTH[sym][wname]
        far = [x for x in strikes if (x >= K1 + W if typ == "CE" else x <= K1 - W)]
        K2 = min(far) if typ == "CE" else max(far)
        leg = {K: next(r for r in rows if float(r["strike"]) == K) for K in (K1, K2)}
        lot = int(leg[K1]["lot_size"])
        lq = k.get("/quote/ltp", params=[("i", f"NFO:{leg[K]['tradingsymbol']}") for K in (K1, K2)])
        p1, p2 = (float(lq[f"NFO:{leg[K]['tradingsymbol']}"]["last_price"]) for K in (K1, K2))
        orders = [{"exchange": "NFO", "tradingsymbol": leg[K1]["tradingsymbol"], "transaction_type": "BUY", "variety": "regular", "product": "NRML",
                   "order_type": "MARKET", "quantity": lot, "price": 0, "trigger_price": 0},
                  {"exchange": "NFO", "tradingsymbol": leg[K2]["tradingsymbol"], "transaction_type": "SELL", "variety": "regular", "product": "NRML",
                   "order_type": "MARKET", "quantity": lot, "price": 0, "trigger_price": 0}]
        m = k.basket_margin(orders)
        fin = m.get("final", {}) or {}
        kite_total = float(fin.get("total", 0.0))
        kite_premium = float(fin.get("option_premium", 0.0))
        span_proxy = abs(K2 - K1) * lot
        elm_proxy = ELM * lot * spot[sym]
        proxy_total = p1 * lot + span_proxy + elm_proxy
        rec = {"index": sym, "width": wname, "type": typ, "expiry": e, "sessions_left": _sessions_left(trade_day, dt.date.fromisoformat(e), hol),
               "long": leg[K1]["tradingsymbol"], "short": leg[K2]["tradingsymbol"], "lot": lot, "spot": spot[sym], "ltp_long": p1, "ltp_short": p2,
               "debit_rs": round((p1 - p2) * lot, 2),
               "proxy": {"premium_long_rs": round(p1 * lot, 2), "span_proxy_rs": round(span_proxy, 2), "elm_proxy_rs": round(elm_proxy, 2), "total_rs": round(proxy_total, 2)},
               "kite_final": {kk: (round(float(v), 2) if isinstance(v, (int, float)) else v) for kk, v in fin.items() if kk in ("span", "exposure", "option_premium", "additional", "bo", "cash", "var", "total")},
               "kite_initial_total": round(float((m.get("initial") or {}).get("total", 0.0)), 2)}
        rec["proxy_over_kite"] = round(proxy_total / kite_total, 3) if kite_total > 0 else None
        rec["kite_total_includes_premium"] = kite_premium > 0
        out.append(rec)
        log(f"{sym} {wname} {typ} {e}: proxy Rs {proxy_total:,.0f} vs Kite Rs {kite_total:,.0f} (premium in Kite total {kite_premium:,.0f})")
    mult = {}
    for sym in SPOT:
        r = [x["proxy_over_kite"] for x in out if x["index"] == sym and x["proxy_over_kite"]]
        mult[sym] = round(max(1.0, max(1.0 / v for v in r)), 4) if r else 1.0
    res = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "trade_day": trade_day.isoformat(), "baskets": out,
           "proxy_multiplier": mult, "rule": "margin.check: where the proxy is below Kite's figure it is raised to it (a per-index multiplier on the proxy); no later change",
           "approved": "Madhav 19 Oct 2026 21:01 Toronto: 'through kites margin calculator'"}
    p = paths.manifest_dir() / "sz2_margin_check.json"
    if p.exists():
        raise SystemExit(f"{p} already exists: the spec allows one check (no later change)")
    p.write_text(json.dumps(res, indent=1))
    return res





# ======================================================================================================================= the trade table
# python -m india.sz2 trades      per SP1 policy trade (2017-2023 walk-forward rows, gold/studies/SP1_policy_trades.parquet) x structure:
#                                 legs, entry and exit values, planned max loss per lot, gross R, the minute marks in R
#                                 -> gold/studies/SZ2_trades.parquet, manifests/sz2_trades.json
# The holdout-era decisions (2024-01-01..2026-10-16, the completed sp1_holdout run's own policy_trades) are the spec's selection window; they
# sit under sealed/gold and need a logged purpose in india/sealed.py before this step may read them: not added in this session.
import numpy as np
import pandas as pd

from india import costs, greeks, ocstudy, sp1

STRUCTURES = ("LONG_ATM", "LONG_OTM1", "SPREAD_NARROW", "SPREAD_WIDE", "MAPPED")
MAPPED = {"ORSTOP": "LONG_ATM", "ATRSTOP": "LONG_ATM", "TRAIL": "LONG_ATM", "T1130": "SPREAD_NARROW", "T1515": "SPREAD_NARROW", "NEXTOPEN": "SPREAD_NARROW"}
NO_STOP_EXITS = ("T1130", "T1515", "NEXTOPEN")
MIN_TURNOVER_RS = 1e7                      # contracts.liquidity: previous-session premium turnover of each leg, Rs 1 crore
HS_FLOOR = {"NIFTY": 0.5, "BANKNIFTY": 1.0}  # pricing.calibration fallback (india.spreads has fewer than 10 sessions): max(floor, 0.4% of premium)
HS_PCT = 0.004
IV_SHIFT = {"NIFTY": 0.0, "BANKNIFTY": 0.0}  # pricing.calibration (a): not yet fitted from the recorder; 0 applied and stated in the manifest
STRESS_ATR, STRESS_MIN, STRESS_IV = 0.25, 360, 0.02
NMIN = ocstudy.NMIN


def smile_iv(ks: np.ndarray, ivs: np.ndarray, fwd: float, K: float) -> float:
    """IV at the leg's moneyness (K / fwd): linear in log-moneyness between traded strikes, flat beyond (pricing.model)."""
    if len(ks) == 0:
        return float("nan")
    o = np.argsort(ks)
    x, y = np.log(ks[o] / fwd), ivs[o]
    return float(np.interp(np.log(K / fwd), x, y))


def _monthly(exps: list) -> list:
    by: dict = {}
    for e in exps:
        by.setdefault((e.year, e.month), []).append(e)
    return sorted(max(v) for v in by.values())


def choose_expiry(sym: str, day, exps: list, sessions_after, nextopen: bool):
    """contracts.expiry. sessions_after(day, expiry) counts the sessions after the trade day up to and including the expiry session."""
    need = 3 if nextopen else 2
    cands = sorted(e for e in exps if e > day)
    if sym == "BANKNIFTY":
        cands = _monthly(cands)
    ok = [e for e in cands if sessions_after(day, e) >= need]
    return ok[0] if ok else None


def leg_strikes(structure: str, typ: str, px: float, listed: np.ndarray, traded: np.ndarray, sym: str):
    """The legs of a structure from the decision price: [(strike, side)] with side +1 bought, -1 sold; None with the reason when a leg has no
    listed strike with traded IV (contracts.strikes_by_structure)."""
    step = STEP[sym]
    atm = float(listed[np.abs(listed - px).argmin()])
    up = typ == "CE"
    def otm_from(level: float, dist: float):
        c = traded[traded >= level + dist] if up else traded[traded <= level - dist]
        return float(c.min()) if (up and len(c)) else (float(c.max()) if (not up and len(c)) else None)
    if structure == "LONG_ATM":
        return ([(atm, 1)], None) if atm in traded else (None, "strike")
    if structure == "LONG_OTM1":
        k = otm_from(px, step)
        return ([(k, 1)], None) if k is not None else (None, "strike")
    w = WIDTH[sym]["narrow" if structure == "SPREAD_NARROW" else "wide"]
    k2 = otm_from(atm, w)
    if atm not in traded or k2 is None:
        return None, "strike"
    return [(atm, 1), (k2, -1)], None


def _value(legs, F: float, T: float, iv_of, call: bool, shift: float = 0.0) -> float:
    """Structure value per unit: sum of side x Black-76 price, each leg's IV from the smile at its own moneyness (+ an optional per-leg shift that
    lowers the position's value: long legs down, short legs up)."""
    v = 0.0
    for K, side in legs:
        iv = max(iv_of(F, K) - side * shift, 0.01)
        p = float(greeks.black76(np.array([F]), np.array([K]), np.array([T]), np.array([iv]), np.array([call]))[0][0])
        v += side * max(p, 0.05)
    return v


def _hs(sym: str, premium: float) -> float:
    return max(HS_FLOOR[sym], HS_PCT * abs(premium))


def leg_costs(sym: str, legs, prices_in: list, prices_out: list, lot: int, day, day_out, stop_exit: bool) -> dict:
    """Entry and exit costs in rupees per lot: half-spreads per leg per side (doubled on a stop exit) and dated option fees per order."""
    hs_in = sum(_hs(sym, p) for p in prices_in) * lot
    hs_out = sum(_hs(sym, p) for p in prices_out) * lot * (2.0 if stop_exit else 1.0)
    fees = 0.0
    for (K, side), p_in, p_out in zip(legs, prices_in, prices_out):
        fees += costs.cost("options", "buy" if side > 0 else "sell", abs(p_in) * lot, day.year, when=day)
        fees += costs.cost("options", "sell" if side > 0 else "buy", abs(p_out) * lot, day_out.year, when=day_out)
    return {"hs_in": hs_in, "hs_out": hs_out, "fees": fees}


def build_trades(log=print) -> dict:
    """The per-trade, per-structure table for the walk-forward rows (2017-2023)."""
    import datetime as dt, json, time
    from india import paths
    t0 = time.time()
    D = paths.data_dir()
    pt = pd.read_parquet(D / "gold/studies/SP1_policy_trades.parquet")
    pt["date"] = pd.to_datetime(pt["date"]).dt.date
    pt = pt[(pt["date"] >= dt.date(2017, 1, 1)) & (pt["date"] <= dt.date(2023, 12, 29))].reset_index(drop=True)
    days_all, _ = ocstudy._calendar()
    di = {d: i for i, d in enumerate(days_all)}
    prev = {days_all[i]: days_all[i - 1] for i in range(1, len(days_all))}
    nxt = {days_all[i]: days_all[i + 1] for i in range(len(days_all) - 1)}
    def sessions_after(day, exp):
        a, b = di.get(day), di.get(exp)
        if a is None or b is None:
            return sum(1 for d in days_all if day < d <= exp)
        return b - a
    import duckdb
    files = [str(D / "silver/fo_greeks" / f"year={y}" / "part.parquet") for y in range(2016, 2024) if (D / "silver/fo_greeks" / f"year={y}" / "part.parquet").exists()]
    con = duckdb.connect()
    chains = con.execute(f"""select date, symbol, expiry, strike, opt_type, fwd, iv, settle, coalesce(volume, 0) as volume from read_parquet({files!r})
                             where symbol in ('NIFTY', 'BANKNIFTY')""").df()
    con.close()
    chains["date"] = pd.to_datetime(chains["date"]).dt.date
    chains["expiry"] = pd.to_datetime(chains["expiry"]).dt.date
    by = {k: g for k, g in chains.groupby(["symbol", "date"])}
    idx = ocstudy.load_index()
    iv_shift_note = "IV shift 0 (pricing.calibration (a) not yet fitted from the recorder); half-spread = max(Rs 0.5 Nifty / 1.0 Bank Nifty, 0.4% of premium) (the spec's fallback while india.spreads has fewer than 10 sessions)"
    rows, reasons = [], {}
    for r in pt.itertuples(index=False):
        sym, day = r.index, r.date
        p = prev.get(day)
        g = by.get((sym, p)) if p else None
        if g is None or g.empty:
            reasons["no_chain"] = reasons.get("no_chain", 0) + 1
            continue
        exp = choose_expiry(sym, day, sorted(g["expiry"].unique()), sessions_after, r.exit == "NEXTOPEN")
        if exp is None:
            reasons["no_expiry"] = reasons.get("no_expiry", 0) + 1
            continue
        c = g[g["expiry"] == exp]
        fwd_prev = c["fwd"].dropna()
        name = sp1.IDX[sym]
        ix = idx[name]
        d_i = {d: i for i, d in enumerate(ix["dates"])}
        if day not in d_i or fwd_prev.empty:
            reasons["no_minutes"] = reasons.get("no_minutes", 0) + 1
            continue
        k = d_i[day]
        prev_close = ix["close"][d_i[p], NMIN - 1] if p in d_i else np.nan
        carry = float(fwd_prev.median()) / prev_close if prev_close == prev_close else 1.0
        listed = np.sort(c["strike"].unique())
        typ = "CE" if r.dir > 0 else "PE"
        x = c[(c["opt_type"] == typ) & (c["volume"] > 0) & c["iv"].notna() & (c["iv"] > 0)]
        ks, ivs = x["strike"].to_numpy(float), x["iv"].to_numpy(float) + IV_SHIFT[sym]
        # premium turnover of the previous session per strike: volume x lot x settle (fo_greeks settle)
        sett = c[c["opt_type"] == typ].groupby("strike")["settle"].max()
        e0 = sp1.POINT_ENTRY[r.point]
        decision_px = float(ix["open"][k, 0]) if r.point == "D0" else float(ix["close"][k, e0 - 1])
        m_in = e0
        if r.next_day:
            d_out = nxt.get(day)
            if d_out not in d_i:
                reasons["no_next_day"] = reasons.get("no_next_day", 0) + 1
                continue
            k_out, m_out = d_i[d_out], 1
        else:
            d_out, k_out, m_out = day, k, int(r.exit_min)
        iv_of = lambda F, K: smile_iv(ks, ivs, F, K)
        call = typ == "CE"
        F_in, F_out = float(r.entry) * carry, float(r.exit_px) * carry
        T_in, T_out = sp1._t_years(day, m_in, exp), sp1._t_years(d_out, m_out, exp)
        for structure in STRUCTURES:
            s_eff = MAPPED[r.exit] if structure == "MAPPED" else structure
            legs, why = leg_strikes(s_eff, typ, decision_px, listed, ks, sym)
            base = {"date": day, "index": sym, "point": r.point, "exit": r.exit, "dir": int(r.dir), "lot": int(r.lot), "expiry": exp, "sessions_left": sessions_after(day, exp),
                    "structure": structure, "structure_eff": s_eff, "decision_px": decision_px, "entry_idx": float(r.entry), "exit_idx": float(r.exit_px), "stopped": bool(r.stopped), "carry": carry}
            if legs is None:
                rows.append({**base, "available": False, "reason": why})
                continue
            # liquidity: previous-session premium turnover of each leg
            liq_ok = True
            for K, side in legs:
                vol = float(x.loc[x["strike"] == K, "volume"].sum()) if len(x) else 0.0
                st_ = float(sett.get(K, np.nan))
                if not (vol * r.lot * (st_ if st_ == st_ else 0.0) >= MIN_TURNOVER_RS):
                    liq_ok = False
            if not liq_ok:
                rows.append({**base, "available": False, "reason": "liquidity"})
                continue
            p_in = [float(greeks.black76(np.array([F_in]), np.array([K]), np.array([T_in]), np.array([max(iv_of(F_in, K), 0.01)]), np.array([call]))[0][0]) for K, _ in legs]
            p_out = [float(greeks.black76(np.array([F_out]), np.array([K]), np.array([T_out]), np.array([max(iv_of(F_out, K), 0.01)]), np.array([call]))[0][0]) for K, _ in legs]
            p_in, p_out = [max(v, 0.05) for v in p_in], [max(v, 0.05) for v in p_out]
            v_in = sum(side * v for (K, side), v in zip(legs, p_in))
            v_out = sum(side * v for (K, side), v in zip(legs, p_out))
            cst = leg_costs(sym, legs, p_in, p_out, int(r.lot), day, d_out, bool(r.stopped))
            gross_rs = (v_out - v_in) * r.lot                                    # GROSS per lot: no spreads, no fees (contracts.lots_and_scale)
            # planned max loss per lot (max_loss_per_lot.rule)
            full = v_in * r.lot + cst["hs_in"] + 2 * sum(_hs(sym, v) for v in p_out) * r.lot + cst["fees"]
            if r.exit in NO_STOP_EXITS or not (r.stop0 == r.stop0):
                max_loss = full
            else:
                S = float(r.stop0) - r.dir * STRESS_ATR * float(r.atr_d)
                T_s = sp1._t_years(day, STRESS_MIN, exp)
                v_s = _value(legs, S * carry, T_s, iv_of, call, shift=STRESS_IV)
                stressed = (v_in - v_s) * r.lot + cst["hs_in"] + 2 * sum(_hs(sym, abs(v)) for v in p_out) * r.lot + cst["fees"]
                max_loss = min(full, stressed)
            max_loss = max(max_loss, 1.0)
            # minute marks in R: the structure valued at each minute's close from the entry minute to the exit minute (bid side = mid minus hs)
            marks = []
            for kk, m0, m1 in ((k, m_in, NMIN - 1 if r.next_day else m_out), *(((k_out, 0, m_out),) if r.next_day else ())):
                dday = day if kk == k else d_out
                for m in range(m0, m1 + 1):
                    F = float(ix["close"][kk, m]) * carry
                    if F != F:
                        continue
                    T = sp1._t_years(dday, m, exp)
                    v = _value(legs, F, T, iv_of, call) - sum(_hs(sym, abs(pv)) for pv in p_in)
                    marks.append(float((v - v_in) * r.lot / max_loss))
            notional = r.lot * float(r.entry)
            rows.append({**base, "available": True, "reason": "", "legs": json.dumps(legs), "v_in": v_in, "v_out": v_out, "gross_rs": gross_rs, "gross_frac_notional": gross_rs / notional,
                         "max_loss_rs": max_loss, "max_loss_frac_notional": max_loss / notional, "gross_R": gross_rs / max_loss, "hs_in_rs": cst["hs_in"], "hs_out_rs": cst["hs_out"],
                         "fees_rs_dated": cst["fees"], "net_rs_dated": gross_rs - cst["hs_in"] - cst["hs_out"] - cst["fees"], "breach": (-(gross_rs - cst["hs_in"] - cst["hs_out"] - cst["fees"])) > max_loss,
                         "marks_R": np.array(marks, dtype=np.float32), "min_mark_R": float(min(marks)) if marks else float("nan")})
    out = pd.DataFrame(rows)
    out_file = paths.gold() / "studies" / "SZ2_trades.parquet"
    out.to_parquet(out_file, index=False)
    av = out[out["available"]]
    summ = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "spec_version": "sz2-v1-2026-10-19-frozen", "window": "2017-01-02..2023-12-29 (walk-forward rows; the holdout-era rows wait on a logged sealed purpose)",
            "sp1_trades": int(len(pt)), "skipped_trades": reasons, "rows": int(len(out)), "available_share_by_structure": {k: round(float(v), 3) for k, v in out.groupby("structure")["available"].mean().items()},
            "unavailable_reasons": {k: int(v) for k, v in out.loc[~out["available"], "reason"].value_counts().items()},
            "gross_R_mean_by_structure": {k: round(float(v), 4) for k, v in av.groupby("structure")["gross_R"].mean().items()},
            "max_loss_frac_notional_median_by_index_structure": {f"{i}|{s}": round(float(v), 5) for (i, s), v in av.groupby(["index", "structure"])["max_loss_frac_notional"].median().items()},
            "planned_max_loss_breaches": {"n": int(av["breach"].sum()), "share": round(float(av["breach"].mean()), 4) if len(av) else None,
                                          "by_exit": {k: int(v) for k, v in av.groupby("exit")["breach"].sum().items()},
                                          "by_sessions_left": {str(k): int(v) for k, v in av.groupby(pd.cut(av["sessions_left"], [0, 3, 7, 1000], labels=["2-3", "4-7", "8+"]), observed=True)["breach"].sum().items()}},
            "calibration": iv_shift_note, "file": str(out_file), "seconds": round(time.time() - t0, 1)}
    (paths.manifest_dir() / "sz2_trades.json").write_text(json.dumps(summ, indent=1, default=str))
    log(json.dumps({k: summ[k] for k in ("sp1_trades", "skipped_trades", "rows", "available_share_by_structure", "unavailable_reasons", "gross_R_mean_by_structure", "planned_max_loss_breaches", "seconds")}, indent=1, default=str))
    return summ


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "margincheck":
        print(json.dumps(margincheck(), indent=1))
    elif cmd == "trades":
        build_trades()
    else:
        raise SystemExit(__doc__)
