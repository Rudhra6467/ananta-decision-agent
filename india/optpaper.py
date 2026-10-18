"""Paper book for index options, built on the recorder's 1-minute candles. Mechanical rules only; every run records every shadow variant ("everything on").

  python -m india.optpaper run          simulate every completed session that has not been processed, append to paper/options_trades.jsonl, write marks
  python -m india.optpaper report       what the options book looks like now
  python -m india.optpaper selftest     synthetic-day unit check of the O-04 and O-03 engines

Strategies (Madhav's list, library/madhav/02_option_strategies_2026-10-18.md):
O-04 (his own): on a weekly expiry day, at 13:30 IST buy the at-the-money call and put (same strike, ATM from the spot close of 13:29). The opening range is the spot high-low of
    13:00-13:29. A close outside that range after entry is the level break ("the market clearly moves"): the losing leg is closed at the next minute's open, the winner is
    trailed by a fixed percentage from its peak close. Stop: both legs out at the next open if the combined premium (sum of both leg closes) falls to STOP of what was paid.
    No break by 14:45: both legs out at 14:45. Everything out at 15:15. Variants run in parallel: STOP 0.5 / 0.6, TRAIL 0.25 / 0.35, no-break exit 14:45 / 15:15.
O-03 (YouTube, expiry-eve strangle): at 15:00 on the session before an expiry, sell the call and put about 1.5% away from spot and buy the far hedges priced near Rs 1; exit at 50% of the
    net credit decayed, or 11:00 the next morning, or if the position loses 1% of the Rs 50,000 book (Rs 500). Max loss at expiry is reported with it (strike gap less credit, times lot).
Fills: the open of the minute after the decision, worse by a labelled half-spread estimate (HALF_SPREAD). Costs: india.costs option charges per order, STT on sells.
Index expiry days and lot sizes come from the recorder's own instrument dump, never an assumed weekday. Nothing here can place an order.
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import gzip
import io
import json
import math
import sys
from functools import lru_cache

import numpy as np
import pandas as pd

from india import catalog, costs, paths

BOOK_INR = 50_000.0
HALF_SPREAD_PCT = 0.004   # labelled estimate: 0.4% of premium per side on near-the-money index options near expiry
HALF_SPREAD_MIN = 0.05    # one tick
INDEX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK", "FINNIFTY": "NIFTY FIN SERVICE", "MIDCPNIFTY": "NIFTY MID SELECT"}
STEP = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50, "MIDCPNIFTY": 25}
VARIANTS_O4 = [{"stop": s, "trail": t, "nobreak": nb} for s in (0.5, 0.6) for t in (0.25, 0.35) for nb in ("14:45", "15:15")]


def pdir():
    d = paths.data_dir() / "paper"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _hs(price: float) -> float:
    return max(HALF_SPREAD_MIN, HALF_SPREAD_PCT * price)


# ----------------------------------------------------------------------------------------------- data
def _minutes_file(path: str) -> pd.DataFrame:
    rows = {}
    with gzip.open(path, "rt") as gz:
        for line in gz:
            for c in json.loads(line)["candles"]:
                rows[c[0][:19]] = c  # later fetches overwrite earlier ones: the last window is the most complete
    if not rows:
        return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])
    df = pd.DataFrame([(pd.Timestamp(k), v[1], v[2], v[3], v[4], v[5]) for k, v in rows.items()], columns=["ts", "open", "high", "low", "close", "volume"])
    return df.sort_values("ts").set_index("ts")


@lru_cache(maxsize=512)
def minutes(kind: str, name: str, expiry: str = "") -> pd.DataFrame:
    root = paths.bronze("kite_1m_fo")
    p = root / ("indices" if kind == "index" else expiry) / f"{name}.jsonl.gz"
    return _minutes_file(str(p)) if p.exists() else pd.DataFrame()


def instruments() -> pd.DataFrame:
    files = sorted(glob.glob(str(paths.bronze("kite_instruments") / "NFO_*.csv")))
    frames = [pd.read_csv(f, dtype=str) for f in files[-3:]]
    df = pd.concat(frames).drop_duplicates(["tradingsymbol", "expiry"], keep="last")
    df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
    df["lot_size"] = pd.to_numeric(df["lot_size"], errors="coerce")
    return df[df["instrument_type"].isin(["CE", "PE"])]


def expiries_for(name: str) -> list[str]:
    ins = instruments()
    return sorted(ins[ins["name"] == name]["expiry"].unique())


# ----------------------------------------------------------------------------------------------- order costs
def _leg_cost(side: str, value: float, year: int) -> float:
    return costs.cost("options", side, value, year)


def _pnl(legs: list[dict], lot: int, year: int) -> dict:
    """legs: {side: buy/sell, entry, exit}. Premium P&L plus charges for every order (entry and exit), spread already inside the fills."""
    gross = 0.0
    fees = 0.0
    for lg in legs:
        q = lot
        if lg["side"] == "buy":
            gross += (lg["exit"] - lg["entry"]) * q
            fees += _leg_cost("buy", lg["entry"] * q, year) + _leg_cost("sell", lg["exit"] * q, year)
        else:
            gross += (lg["entry"] - lg["exit"]) * q
            fees += _leg_cost("sell", lg["entry"] * q, year) + _leg_cost("buy", lg["exit"] * q, year)
    return {"gross_inr": gross, "fees_inr": fees, "net_inr": gross - fees}


# ----------------------------------------------------------------------------------------------- O-04
def _at(df: pd.DataFrame, ts: pd.Timestamp):
    """The first candle at or after ts."""
    x = df[df.index >= ts]
    return None if x.empty else x.iloc[0]


def sim_o4(name: str, day: str, v: dict, ce: pd.DataFrame, pe: pd.DataFrame, spot: pd.DataFrame, lot: int) -> dict | None:
    d = pd.Timestamp(day)
    t_entry = d + pd.Timedelta(hours=13, minutes=30)
    s_prev = spot[(spot.index >= d + pd.Timedelta(hours=13)) & (spot.index < t_entry)]
    if len(s_prev) < 20:
        return None
    hi, lo = s_prev["high"].max(), s_prev["low"].min()
    ce_e, pe_e = _at(ce, t_entry), _at(pe, t_entry)
    if ce_e is None or pe_e is None or ce_e.name > t_entry + pd.Timedelta(minutes=3) or pe_e.name > t_entry + pd.Timedelta(minutes=3):
        return None
    ce_in, pe_in = ce_e["open"] + _hs(ce_e["open"]), pe_e["open"] + _hs(pe_e["open"])
    paid_mid = ce_e["open"] + pe_e["open"]
    legs = {"CE": {"entry": ce_in, "exit": None}, "PE": {"entry": pe_in, "exit": None}}
    t_end = d + pd.Timedelta(hours=15, minutes=15)
    t_nb = d + pd.Timedelta(hours=14, minutes=45) if v["nobreak"] == "14:45" else t_end
    side, peak, broke_at = None, 0.0, None
    reason = "time"
    idx = ce.index.intersection(pe.index)
    idx = idx[(idx >= t_entry) & (idx <= t_end)]
    exit_at = t_end
    for i, t in enumerate(idx):
        c_c, p_c = ce.at[t, "close"], pe.at[t, "close"]
        nxt = idx[i + 1] if i + 1 < len(idx) else None
        if nxt is None:
            break
        if side is None and (c_c + p_c) <= v["stop"] * paid_mid:
            reason, exit_at = "stop", nxt
            break
        if side is None and t >= t_nb:
            reason, exit_at = "no_break", nxt
            break
        sp = spot.at[t, "close"] if t in spot.index else None
        if side is None and sp is not None and (sp > hi or sp < lo):
            side = "CE" if sp > hi else "PE"
            loser = "PE" if side == "CE" else "CE"
            lo_df = pe if loser == "PE" else ce
            legs[loser]["exit"] = float(lo_df.at[nxt, "open"] - _hs(lo_df.at[nxt, "open"]))
            broke_at = nxt
            w_df = ce if side == "CE" else pe
            peak = float(w_df.at[t, "close"])
            continue
        if side is not None:
            w_df = ce if side == "CE" else pe
            wc = float(w_df.at[t, "close"])
            peak = max(peak, wc)
            if wc <= peak * (1 - v["trail"]):
                reason, exit_at = "trail", nxt
                break
    if exit_at is None or exit_at not in ce.index or exit_at not in pe.index:
        exit_at = idx[-1] if len(idx) else None
        if exit_at is None:
            return None
    for k, df_ in (("CE", ce), ("PE", pe)):
        if legs[k]["exit"] is None:
            legs[k]["exit"] = float(df_.at[exit_at, "open"] - _hs(df_.at[exit_at, "open"]))
    legs_l = [{"side": "buy", "entry": legs[k]["entry"], "exit": max(legs[k]["exit"], 0.0)} for k in ("CE", "PE")]
    res = _pnl(legs_l, lot, d.year)
    return {"strategy": "O-04", "index": name, "day": day, "variant": f"stop{v['stop']}_trail{v['trail']}_nb{v['nobreak']}", "lot": lot, "paid_mid": float(paid_mid),
            "ce_in": float(ce_in), "pe_in": float(pe_in), "ce_out": float(legs["CE"]["exit"]), "pe_out": float(legs["PE"]["exit"]), "broke": side, "broke_at": str(broke_at) if broke_at is not None else None,
            "exit_reason": reason, "exit_at": str(exit_at), "range_hi": float(hi), "range_lo": float(lo), **res, "net_ret_on_book": res["net_inr"] / BOOK_INR}


# ----------------------------------------------------------------------------------------------- O-03
def sim_o3(name: str, eve: str, expiry_day: str, ins_day: pd.DataFrame, spot_eve: pd.DataFrame, spot_exp: pd.DataFrame) -> list[dict]:
    d0 = pd.Timestamp(eve)
    t_in = d0 + pd.Timedelta(hours=15)
    s = spot_eve[spot_eve.index < t_in]
    if s.empty:
        return []
    spot = float(s["close"].iloc[-1])
    step = STEP[name]
    k_call, k_put = round(spot * 1.015 / step) * step, round(spot * 0.985 / step) * step

    def load(strike, typ):
        r = ins_day[(ins_day["strike"] == strike) & (ins_day["instrument_type"] == typ)]
        if r.empty:
            return None, None, None
        sym = r["tradingsymbol"].iloc[0]
        return sym, minutes("option", sym, expiry_day), int(r["lot_size"].iloc[0])

    sc, dfc, lot = load(k_call, "CE")
    sp_, dfp, _ = load(k_put, "PE")
    if dfc is None or dfp is None or dfc.empty or dfp.empty:
        return []
    # hedges: the listed strikes beyond the short ones whose price at the entry minute is nearest to Rs 1 (and at least 0.5)
    def hedge(typ, beyond):
        best = None
        cand = ins_day[ins_day["instrument_type"] == typ]
        cand = cand[cand["strike"] > beyond] if typ == "CE" else cand[cand["strike"] < beyond]
        for _, r in cand.iterrows():
            df_ = minutes("option", r["tradingsymbol"], expiry_day)
            if df_.empty:
                continue
            e = _at(df_, t_in)
            if e is None:
                continue
            px = float(e["open"])
            if px >= 0.5 and (best is None or abs(px - 1.0) < abs(best[1] - 1.0)):
                best = (r["tradingsymbol"], px, df_, float(r["strike"]))
        return best

    hc, hp = hedge("CE", k_call), hedge("PE", k_put)
    if hc is None or hp is None:
        return []
    ec, ep = _at(dfc, t_in), _at(dfp, t_in)
    if ec is None or ep is None:
        return []
    sell_c, sell_p = float(ec["open"]) - _hs(ec["open"]), float(ep["open"]) - _hs(ep["open"])
    buy_hc, buy_hp = hc[1] + _hs(hc[1]), hp[1] + _hs(hp[1])
    credit = sell_c + sell_p - buy_hc - buy_hp
    if credit <= 0:
        return []
    width = max(hc[3] - k_call, k_put - hp[3])
    max_loss = (width - credit) * lot
    t_cut = pd.Timestamp(expiry_day) + pd.Timedelta(hours=11)
    series = []
    legs = [(dfc, "sell"), (dfp, "sell"), (hc[2], "buy"), (hp[2], "buy")]
    idx = dfc.index.intersection(dfp.index).intersection(hc[2].index).intersection(hp[2].index)
    idx = idx[(idx >= t_in) & (idx <= t_cut)]
    exit_at, reason = None, "time_11"
    for i, t in enumerate(idx):
        val = dfc.at[t, "close"] + dfp.at[t, "close"] - hc[2].at[t, "close"] - hp[2].at[t, "close"]  # cost to close at mid
        pnl_now = (credit - val) * lot
        nxt = idx[i + 1] if i + 1 < len(idx) else None
        if nxt is None:
            break
        if val <= 0.5 * credit:
            exit_at, reason = nxt, "decayed_50"
            break
        if pnl_now <= -0.01 * BOOK_INR:
            exit_at, reason = nxt, "stop_1pct"
            break
    if exit_at is None:
        exit_at = idx[-1] if len(idx) else None
        if exit_at is None:
            return []
    out_c, out_p = float(dfc.at[exit_at, "open"]) + _hs(dfc.at[exit_at, "open"]), float(dfp.at[exit_at, "open"]) + _hs(dfp.at[exit_at, "open"])
    out_hc, out_hp = max(float(hc[2].at[exit_at, "open"]) - _hs(hc[2].at[exit_at, "open"]), 0.0), max(float(hp[2].at[exit_at, "open"]) - _hs(hp[2].at[exit_at, "open"]), 0.0)
    legs_l = [{"side": "sell", "entry": sell_c, "exit": out_c}, {"side": "sell", "entry": sell_p, "exit": out_p}, {"side": "buy", "entry": buy_hc, "exit": out_hc}, {"side": "buy", "entry": buy_hp, "exit": out_hp}]
    res = _pnl(legs_l, lot, d0.year)
    return [{"strategy": "O-03", "index": name, "day": eve, "expiry": expiry_day, "variant": "exit50_or_11am_stop1pct", "lot": lot, "spot": spot, "short_call": k_call, "short_put": k_put,
             "hedge_call": hc[3], "hedge_put": hp[3], "credit": float(credit), "max_loss_at_expiry_inr": float(max_loss), "exit_reason": reason, "exit_at": str(exit_at), **res,
             "net_ret_on_book": res["net_inr"] / BOOK_INR}]


# ----------------------------------------------------------------------------------------------- driver
def _done() -> set:
    p = pdir() / "options_trades.jsonl"
    if not p.exists():
        return set()
    return {(r["strategy"], r["index"], r["day"], r["variant"]) for r in map(json.loads, p.read_text().splitlines()) if r.get("kind") != "skip"}


def _skipped() -> set:
    p = pdir() / "options_trades.jsonl"
    if not p.exists():
        return set()
    return {(r["strategy"], r["index"], r["day"]) for r in map(json.loads, p.read_text().splitlines()) if r.get("kind") == "skip"}


def run() -> dict:
    paths.ensure()
    ins = instruments()
    done, skipped = _done(), _skipped()
    out, new = [], 0
    for name in INDEX:
        spot_all = minutes("index", INDEX[name])
        if spot_all.empty:
            continue
        days = sorted({str(t.date()) for t in spot_all.index})
        complete = [d for d in days if len(spot_all[spot_all.index.date == pd.Timestamp(d).date()]) >= 370]
        exps = [e for e in expiries_for(name)]
        for d in complete:
            # O-04 on expiry days
            if d in exps and ("O-04", name, d) not in skipped:
                sub = ins[(ins["name"] == name) & (ins["expiry"] == d)]
                day_spot = spot_all[spot_all.index.date == pd.Timestamp(d).date()]
                s13 = day_spot[(day_spot.index >= pd.Timestamp(d) + pd.Timedelta(hours=13, minutes=29)) & (day_spot.index < pd.Timestamp(d) + pd.Timedelta(hours=13, minutes=30))]
                if s13.empty:
                    continue
                atm = round(float(s13["close"].iloc[0]) / STEP[name]) * STEP[name]
                ce_s = sub[(sub["strike"] == atm) & (sub["instrument_type"] == "CE")]
                pe_s = sub[(sub["strike"] == atm) & (sub["instrument_type"] == "PE")]
                recs = []
                if not ce_s.empty and not pe_s.empty:
                    ce, pe = minutes("option", ce_s["tradingsymbol"].iloc[0], d), minutes("option", pe_s["tradingsymbol"].iloc[0], d)
                    lot = int(ce_s["lot_size"].iloc[0])
                    for v in VARIANTS_O4:
                        key = ("O-04", name, d, f"stop{v['stop']}_trail{v['trail']}_nb{v['nobreak']}")
                        if key in done:
                            continue
                        r = sim_o4(name, d, v, ce, pe, day_spot, lot) if not ce.empty and not pe.empty else None
                        if r:
                            recs.append(r)
                if recs:
                    out += recs
                else:
                    out.append({"kind": "skip", "strategy": "O-04", "index": name, "day": d, "variant": "-", "note": "no recorded candles for the at-the-money pair"})
            # O-03: the session before an expiry (entry at 15:00, exit the next morning, needs the expiry day candles too)
            nxt_exp = [e for e in exps if e > d]
            if nxt_exp:
                e = nxt_exp[0]
                nxt_days = [x for x in days if x > d]
                if nxt_days and nxt_days[0] == e and ("O-03", name, d) not in skipped and ("O-03", name, d, "exit50_or_11am_stop1pct") not in done:
                    day_ins = ins[(ins["name"] == name) & (ins["expiry"] == e)]
                    sp_e = spot_all[spot_all.index.date == pd.Timestamp(d).date()]
                    sp_x = spot_all[spot_all.index.date == pd.Timestamp(e).date()]
                    r = sim_o3(name, d, e, day_ins, sp_e, sp_x)
                    out += r if r else [{"kind": "skip", "strategy": "O-03", "index": name, "day": d, "variant": "-", "note": "no recorded candles for strikes/hedges"}]
    if out:
        with (pdir() / "options_trades.jsonl").open("a") as fh:
            for r in out:
                r["logged_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                fh.write(json.dumps(r, default=str) + "\n")
        new = sum(1 for r in out if r.get("kind") != "skip")
    summary = {"new_trades": new, "skips": sum(1 for r in out if r.get("kind") == "skip")}
    catalog.heartbeat("optpaper.run", True, json.dumps(summary))
    print(summary, flush=True)
    return summary


def report() -> None:
    p = pdir() / "options_trades.jsonl"
    if not p.exists():
        print("no options paper trades yet")
        return
    df = pd.DataFrame([r for r in map(json.loads, p.read_text().splitlines()) if r.get("kind") != "skip"])
    if df.empty:
        print("no completed options paper trades yet")
        return
    g = df.groupby(["strategy", "index", "variant"]).agg(n=("net_inr", "size"), net_inr=("net_inr", "sum"), mean=("net_inr", "mean"), worst=("net_inr", "min"), win=("net_inr", lambda x: (x > 0).mean()))
    print(g.round(1).to_string())


def selftest() -> bool:
    """Synthetic expiry afternoon: spot trends up through the opening range at 14:00; the call doubles, the put halves."""
    d = "2026-01-06"
    ts = pd.date_range(f"{d} 09:15", f"{d} 15:29", freq="min")
    spot = pd.DataFrame({"open": 25000.0, "high": 25005.0, "low": 24995.0, "close": 25000.0, "volume": 0}, index=ts)
    up = ts >= pd.Timestamp(f"{d} 14:00")
    spot.loc[up, "close"] = 25000 + np.asarray((ts[up] - pd.Timestamp(f"{d} 14:00")).total_seconds()) / 60 * 1.0
    spot["high"] = spot["close"] + 3
    spot["low"] = spot["close"] - 3
    ce = pd.DataFrame({"open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1}, index=ts)
    pe = pd.DataFrame({"open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0, "volume": 1}, index=ts)
    ce.loc[up, "close"] = 50 + np.asarray((ts[up] - pd.Timestamp(f"{d} 14:00")).total_seconds()) / 60 * 0.6
    pe.loc[up, "close"] = np.clip(50 - np.asarray((ts[up] - pd.Timestamp(f"{d} 14:00")).total_seconds()) / 60 * 0.6, 1, None)
    ce["open"], pe["open"] = ce["close"].shift(1).fillna(50), pe["close"].shift(1).fillna(50)
    r = sim_o4("NIFTY", d, {"stop": 0.5, "trail": 0.25, "nobreak": "14:45"}, ce, pe, spot, 75)
    ok = r is not None and r["broke"] == "CE" and r["pe_out"] < 49 and r["ce_out"] > 55 and r["exit_reason"] in ("trail", "time")
    print("selftest O-04:", "PASS" if ok else "FAIL", r)
    return ok


if __name__ == "__main__":
    paths.ensure()
    {"run": run, "report": report, "selftest": selftest}[sys.argv[1] if len(sys.argv) > 1 else "report"]()
