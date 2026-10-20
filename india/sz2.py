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


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "margincheck":
        print(json.dumps(margincheck(), indent=1))
    else:
        raise SystemExit(__doc__)
