"""Forward evidence for the teacher cards (Madhav, 25 Oct 2026: "keep a track of them for forward evidence").

Two kinds of forward books, both paper, both mechanical, nothing can place an order:

1. Optionables' intraday straddle systems (cards marked FORWARD in india/teachers.py: OPT-H01..H13, H22, H23). They need real intraday option
   prices, which only the live recorder has (bronze/kite_1m_fo, from the first recorded session). Every system below is simulated on every complete
   recorded session, one lot, fills at the open of the decision minute worse by the labelled half-spread, per-leg stops on the minute high, full
   charges (india/optpaper's helpers). First look at 12 weeks (60 sessions), tail check at 26 weeks; no verdict before. Adjustment engines
   (OPT-H34..H40) are not simulated yet: they need a coded adjustment engine (a later build).
2. Stock and index cards that pass their backtest (VALIDATED or CONDITIONAL) get a shadow signal log in india/teacher_live.py (added once the
   backtest results are in, for the survivors only).

  python -m india.teacher_forward run       simulate every complete recorded session not yet processed -> paper/teachers/forward_options.jsonl
  python -m india.teacher_forward report    per system: sessions, total, mean, wins, worst day, drawdown, and where it stands against the 12-week look
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys

import pandas as pd

from india import catalog, optpaper, paths

LOTS = 1
STEP = optpaper.STEP
INDEX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
FIRST_LOOK = 60
TAIL_LOOK = 130
FORWARD_START = "2026-10-26"    # the first session after the cards were registered (25 Oct 2026)


def _sys(sid, card, idx, entry, stop, exit_, kind="pct", to_cost=False, expiry_only=False):
    return {"id": sid, "card": card, "index": idx, "entry": entry, "stop": stop, "stop_kind": kind, "exit": exit_, "to_cost": to_cost, "expiry_only": expiry_only}


SYSTEMS = [
    _sys("H02_bn_1300_s30_x1455", "OPT-H02", "BANKNIFTY", "13:00", 0.30, "14:55"),
    _sys("H02_bn_1300_s30_x1529", "OPT-H02/H10", "BANKNIFTY", "13:00", 0.30, "15:29"),
    _sys("H02_bn_1300_s30_cost_x1520", "OPT-H02/H07", "BANKNIFTY", "13:00", 0.30, "15:20", to_cost=True),
    _sys("H03_bn_0930_s50_x1500", "OPT-H03", "BANKNIFTY", "09:30", 0.50, "15:00"),
    _sys("H03_bn_0930_s50_cost_x1500", "OPT-H03/H07", "BANKNIFTY", "09:30", 0.50, "15:00", to_cost=True),
    _sys("H04_nf_0930_p70_x1520", "OPT-H04", "NIFTY", "09:30", 70, "15:20", kind="pts"),
    _sys("H11_bn_exp_1500_s30", "OPT-H11", "BANKNIFTY", "15:00", 0.30, "15:29", expiry_only=True),
    _sys("H11_nf_exp_1500_s30", "OPT-H11", "NIFTY", "15:00", 0.30, "15:29", expiry_only=True),
    _sys("H12_bn_exp_1300_s30", "OPT-H12", "BANKNIFTY", "13:00", 0.30, "15:29", expiry_only=True),
    _sys("H12_nf_exp_1300_s30", "OPT-H12", "NIFTY", "13:00", 0.30, "15:29", expiry_only=True),
]
# Multi-session systems whose end-of-day backtests were inconclusive (OPT-H16, H17, H59): the recorder gives the prices he actually trades at
MULTI = [
    {"id": "H17_bn_eve_200pt", "card": "OPT-H17", "index": "BANKNIFTY", "kind": "eve_strangle", "dist": 200, "wing": None},
    {"id": "H17_bn_eve_200pt_w550", "card": "OPT-H17", "index": "BANKNIFTY", "kind": "eve_strangle", "dist": 200, "wing": 550},
    {"id": "H17_nf_eve_0.7pct", "card": "OPT-H17", "index": "NIFTY", "kind": "eve_strangle", "dist": 0.007, "wing": None},
    {"id": "H16_bn_weekly_naked", "card": "OPT-H16", "index": "BANKNIFTY", "kind": "weekly_straddle"},
    {"id": "H16_nf_weekly_naked", "card": "OPT-H16", "index": "NIFTY", "kind": "weekly_straddle"},
    {"id": "H59_bn_nextweek_open", "card": "OPT-H59", "index": "BANKNIFTY", "kind": "next_week", "exit": "09:20"},
    {"id": "H59_nf_nextweek_open", "card": "OPT-H59", "index": "NIFTY", "kind": "next_week", "exit": "09:20"},
]
# OPT-H01/H05 entry-time grid and OPT-H06 stop-width grid, both indices, exit 15:15 (H08 staggering and H13 loss caps are computed from these rows)
for _ix in ("NIFTY", "BANKNIFTY"):
    for _t in ("09:20", "09:30", "09:45", "10:00", "12:30", "13:00", "14:00"):
        SYSTEMS.append(_sys(f"grid_{_ix.lower()}_{_t.replace(':', '')}_s30", "OPT-H01/H05/H08/H13", _ix, _t, 0.30, "15:15"))
    for _s in (0.25, 0.35, 0.40, 0.50, 0.75, 1.00):
        SYSTEMS.append(_sys(f"stopgrid_{_ix.lower()}_1300_s{int(_s * 100)}", "OPT-H06", _ix, "13:00", _s, "15:15"))


def pdir():
    d = paths.data_dir() / "paper" / "teachers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _t(day: str, hhmm: str) -> pd.Timestamp:
    h, m = map(int, hhmm.split(":"))
    return pd.Timestamp(day) + pd.Timedelta(hours=h, minutes=m)


def simulate(sysd: dict, day: str, ce: pd.DataFrame, pe: pd.DataFrame, lot: int) -> dict | None:
    """Short ATM straddle with per-leg stops. Stop fills at the stop level, or at the minute's open when it opens through it, plus the half-spread."""
    t0, t1 = _t(day, sysd["entry"]), _t(day, sysd["exit"])
    a, b = optpaper._at(ce, t0), optpaper._at(pe, t0)
    if a is None or b is None or a.name > t0 + pd.Timedelta(minutes=3) or b.name > t0 + pd.Timedelta(minutes=3):
        return None
    legs = {}
    for k, row in (("CE", a), ("PE", b)):
        mid = float(row["open"])
        lvl = mid * (1 + sysd["stop"]) if sysd["stop_kind"] == "pct" else mid + sysd["stop"]
        legs[k] = {"side": "sell", "mid": mid, "entry": mid - optpaper._hs(mid), "stop": lvl, "exit": None, "why": None, "at": None}
    frames = {"CE": ce, "PE": pe}
    idx = ce.index.union(pe.index)
    idx = idx[(idx >= max(a.name, b.name)) & (idx < t1)]
    for t in idx:
        for k in ("CE", "PE"):
            lg = legs[k]
            if lg["exit"] is not None or t not in frames[k].index:
                continue
            bar = frames[k].loc[t]
            if float(bar["high"]) >= lg["stop"]:
                px = max(lg["stop"], float(bar["open"]))
                lg["exit"], lg["why"], lg["at"] = px + optpaper._hs(px), "stop", str(t)
                other = legs["PE" if k == "CE" else "CE"]
                if sysd["to_cost"] and other["exit"] is None:
                    other["stop"] = other["mid"]
    for k in ("CE", "PE"):
        lg = legs[k]
        if lg["exit"] is None:
            bar = optpaper._at(frames[k], t1)
            if bar is None:
                bar = frames[k][frames[k].index < t1].iloc[-1]
                px = float(bar["close"])
            else:
                px = float(bar["open"])
            lg["exit"], lg["why"], lg["at"] = px + optpaper._hs(px), "time", str(t1)
    res = optpaper._pnl([{"side": "sell", "entry": legs[k]["entry"], "exit": legs[k]["exit"]} for k in ("CE", "PE")], lot, pd.Timestamp(day).year)
    return {"stops": sum(1 for k in legs if legs[k]["why"] == "stop"), "legs": legs, **res}


def _fill(df: pd.DataFrame, ts: pd.Timestamp, within: int = 5):
    bar = optpaper._at(df, ts)
    if bar is None or bar.name > ts + pd.Timedelta(minutes=within) or bar.name.date() != ts.date():
        return None
    return float(bar["open"])


def _trade(legs: list[tuple], t_in: pd.Timestamp, t_out: pd.Timestamp, expiry: str, lot: int) -> dict | None:
    """legs: (tradingsymbol, 'sell'|'buy'). Enter at the open of the first minute at or after t_in, leave at t_out; half-spread on both sides."""
    rows = []
    for sym, side in legs:
        df = optpaper.minutes("option", sym, expiry)
        if df.empty:
            return None
        a, b = _fill(df, t_in), _fill(df, t_out)
        if a is None or b is None:
            return None
        if side == "sell":
            rows.append({"side": "sell", "entry": a - optpaper._hs(a), "exit": b + optpaper._hs(b), "sym": sym})
        else:
            rows.append({"side": "buy", "entry": a + optpaper._hs(a), "exit": b - optpaper._hs(b), "sym": sym})
    res = optpaper._pnl([{k: r[k] for k in ("side", "entry", "exit")} for r in rows], lot, t_in.year)
    return {"legs": rows, **res, "stops": 0}


def _contract(sub: pd.DataFrame, strike: float, typ: str):
    x = sub[(sub["strike"] == strike) & (sub["instrument_type"] == typ)]
    return (x["tradingsymbol"].iloc[0], int(x["lot_size"].iloc[0])) if len(x) else (None, None)


def run_multi(ins: pd.DataFrame, done: set) -> list[dict]:
    out = []
    for name, ixname in INDEX.items():
        spot_all = optpaper.minutes("index", ixname)
        if spot_all.empty:
            continue
        days = sorted({str(t.date()) for t in spot_all.index})
        complete = [d for d in days if (spot_all.index.date == pd.Timestamp(d).date()).sum() >= 370]
        exps = sorted(optpaper.expiries_for(name))
        step = STEP[name]

        def spot_before(day, hhmm):
            x = spot_all[(spot_all.index.date == pd.Timestamp(day).date()) & (spot_all.index < _t(day, hhmm))]
            return float(x["close"].iloc[-1]) if len(x) else None

        for s in [m for m in MULTI if m["index"] == name]:
            for i, e in enumerate(exps):
                if s["kind"] == "eve_strangle":
                    prior = [d for d in complete if d < e]
                    if e not in complete or not prior or prior[-1] != days[days.index(e) - 1]:
                        continue                     # the eve must be the recorded session right before the expiry
                    d, t_in, t_out, cexp = prior[-1], _t(prior[-1], "15:15"), _t(e, "09:20"), e
                    sp = spot_before(d, "15:15")
                    if sp is None:
                        continue
                    up, dn = (sp + s["dist"], sp - s["dist"]) if s["dist"] > 1 else (sp * (1 + s["dist"]), sp * (1 - s["dist"]))
                    kc, kp = math.ceil(up / step) * step, math.floor(dn / step) * step
                    strikes = [(kc, "CE", "sell"), (kp, "PE", "sell")]
                    if s["wing"]:
                        strikes += [(math.ceil((sp + s["wing"]) / step) * step, "CE", "buy"), (math.floor((sp - s["wing"]) / step) * step, "PE", "buy")]
                elif s["kind"] == "weekly_straddle":
                    if i == 0 or e not in complete:
                        continue
                    starts = [d for d in complete if exps[i - 1] < d <= e]
                    if not starts:
                        continue
                    d, t_in, t_out, cexp = starts[0], _t(starts[0], "09:20"), _t(e, "15:25"), e
                    sp = spot_before(d, "09:20")
                    if sp is None:
                        continue
                    k = round(sp / step) * step
                    strikes = [(k, "CE", "sell"), (k, "PE", "sell")]
                else:  # next_week: sell the next expiry's ATM straddle at 15:00 on an expiry day, buy back the next morning
                    if e not in complete or i + 1 >= len(exps):
                        continue
                    nxt = [x for x in complete if x > e]
                    if not nxt:
                        continue
                    d, t_in, t_out, cexp = e, _t(e, "15:00"), _t(nxt[0], s["exit"]), exps[i + 1]
                    sp = spot_before(e, "15:00")
                    if sp is None:
                        continue
                    k = round(sp / step) * step
                    strikes = [(k, "CE", "sell"), (k, "PE", "sell")]
                if (s["id"], d) in done:
                    continue
                sub = ins[(ins["name"] == name) & (ins["expiry"] == cexp)]
                legs, lot = [], None
                for k_, typ, side in strikes:
                    sym, ls = _contract(sub, k_, typ)
                    if sym is None:
                        legs = None
                        break
                    legs.append((sym, side))
                    lot = ls * LOTS
                row = {"system": s["id"], "card": s["card"], "index": name, "day": d, "expiry": cexp, "strike": strikes[0][0]}
                r = _trade(legs, t_in, t_out, cexp, lot) if legs else None
                out.append({**row, "kind": "trade", "lot": lot, **r} if r else {**row, "kind": "skip", "note": "contracts or candles missing"})
    return out


def _done() -> set:
    p = pdir() / "forward_options.jsonl"
    if not p.exists():
        return set()
    return {(r["system"], r["day"]) for r in map(json.loads, p.read_text().splitlines())}


def run() -> dict:
    ins = optpaper.instruments()
    done = _done()
    out = []
    for name, ixname in INDEX.items():
        spot_all = optpaper.minutes("index", ixname)
        if spot_all.empty:
            continue
        days = sorted({str(t.date()) for t in spot_all.index})
        complete = [d for d in days if (spot_all.index.date == pd.Timestamp(d).date()).sum() >= 370]
        exps = sorted(e for e in optpaper.expiries_for(name))
        for d in complete:
            todo = [s for s in SYSTEMS if s["index"] == name and (s["id"], d) not in done]
            if not todo:
                continue
            e = next((x for x in exps if x >= d), None)
            if e is None:
                continue
            day_spot = spot_all[spot_all.index.date == pd.Timestamp(d).date()]
            sub = ins[(ins["name"] == name) & (ins["expiry"] == e)]
            for s in todo:
                if s["expiry_only"] and d != e:
                    continue
                t0 = _t(d, s["entry"])
                before = day_spot[day_spot.index < t0]
                if before.empty:
                    continue
                atm = round(float(before["close"].iloc[-1]) / STEP[name]) * STEP[name]
                ce_s, pe_s = sub[(sub["strike"] == atm) & (sub["instrument_type"] == "CE")], sub[(sub["strike"] == atm) & (sub["instrument_type"] == "PE")]
                row = {"system": s["id"], "card": s["card"], "index": name, "day": d, "expiry": e, "strike": atm}
                if ce_s.empty or pe_s.empty:
                    out.append({**row, "kind": "skip", "note": "ATM contract not in the instrument dump"})
                    continue
                ce, pe = optpaper.minutes("option", ce_s["tradingsymbol"].iloc[0], e), optpaper.minutes("option", pe_s["tradingsymbol"].iloc[0], e)
                lot = int(ce_s["lot_size"].iloc[0]) * LOTS
                r = simulate(s, d, ce, pe, lot) if not ce.empty and not pe.empty else None
                if r is None:
                    out.append({**row, "kind": "skip", "note": "no recorded candles for the ATM pair at entry"})
                    continue
                out.append({**row, "kind": "trade", "lot": lot, **r})
    out += run_multi(ins, done)
    trades = [r for r in out if r.get("kind") == "trade"]           # skips are not stored: a session whose candles arrive later is tried again
    if trades:
        with (pdir() / "forward_options.jsonl").open("a") as fh:
            for r in trades:
                r["logged_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                fh.write(json.dumps(r, default=str) + "\n")
    skips = pd.Series([r.get("note") for r in out if r.get("kind") == "skip"]).value_counts().to_dict()
    summary = {"trades": len(trades), "skips": int(sum(skips.values())), "skip_reasons": skips}
    try:
        catalog.heartbeat("teacher_forward.run", True, json.dumps(summary))
    except Exception:  # noqa: BLE001
        pass
    print(summary, flush=True)
    return summary


def table() -> pd.DataFrame:
    p = pdir() / "forward_options.jsonl"
    if not p.exists():
        return pd.DataFrame()
    df = pd.DataFrame(map(json.loads, p.read_text().splitlines()))
    df = df[df["kind"] == "trade"] if "kind" in df else df
    # sessions the recorder held before the cards were written (21 Sep - 22 Oct 2026) are kept apart from true forward sessions
    df["phase"] = ["forward" if d >= FORWARD_START else "before_cards" for d in df["day"]]
    return df


def report(write: bool = True) -> dict:
    df = table()
    out = {"first_look_sessions": FIRST_LOOK, "tail_look_sessions": TAIL_LOOK, "systems": {}}
    if not df.empty:
        for sid, x in df.sort_values("day").groupby("system"):
            cum = x["net_inr"].cumsum()
            fw = x[x["phase"] == "forward"]
            out["systems"][sid] = {"card": x["card"].iloc[0], "sessions": int(len(x)), "forward_sessions": int(len(fw)),
                                   "forward_total_inr": round(float(fw["net_inr"].sum()), 0), "before_cards_sessions": int(len(x) - len(fw)),
                                   "total_inr": round(float(x["net_inr"].sum()), 0),
                                   "mean_inr": round(float(x["net_inr"].mean()), 0), "win_share": round(float((x["net_inr"] > 0).mean()), 3),
                                   "worst_inr": round(float(x["net_inr"].min()), 0), "max_drawdown_inr": round(float((cum - cum.cummax()).min()), 0),
                                   "first": x["day"].min(), "last": x["day"].max(),
                                   "stage": "first look due" if len(fw) >= FIRST_LOOK else
                                   f"{len(fw)} of {FIRST_LOOK} forward sessions before the first look ({len(x) - len(fw)} recorded before the cards, shown apart)"}
        # OPT-H08: thirds at 09:30, 12:30 and 14:00 against all at 09:30 (per lot), on days all three traded
        for ix in ("NIFTY", "BANKNIFTY"):
            g = df[df["system"].str.startswith(f"grid_{ix.lower()}_")]
            w = g.pivot_table(index="day", columns="system", values="net_inr", aggfunc="last")
            cols = [f"grid_{ix.lower()}_{t}_s30" for t in ("0930", "1230", "1400")]
            if set(cols) <= set(w.columns):
                ww = w[cols].dropna()
                if len(ww):
                    st = ww.mean(axis=1)
                    one = ww[cols[0]]
                    out[f"H08_{ix}"] = {"days": int(len(ww)), "staggered_mean_inr": round(float(st.mean()), 0), "single_0930_mean_inr": round(float(one.mean()), 0),
                                        "staggered_worst": round(float(st.min()), 0), "single_worst": round(float(one.min()), 0),
                                        "corr_0930_1400": round(float(ww[cols[0]].corr(ww[cols[2]])), 3) if len(ww) > 2 else None}
    if write:
        (pdir() / "forward_options_summary.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "run":
        run()
    print(json.dumps(report(), indent=1, default=str)[:4000])
