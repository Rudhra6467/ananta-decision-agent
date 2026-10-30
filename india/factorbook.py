"""The fourth paper book (Madhav, 30 Oct 2026, one-yes list item 5: "Yes to all your recommendations"): the long-term money's tilt from FP1,
run forward as a shadow book. No money moves; nothing here can place an order; judged over 12 months on drawdown as much as return.

  python -m india.factorbook run       decide (on the first session of a new month), fill, mark; paper/factorbook/state.json, marks.jsonl, view.json
  python -m india.factorbook show

Two lines and their benchmark, each Rs 10,00,000 of paper notional, equal weight, rebalanced monthly:
  LOWVOL   the 50 calmest of the 500 most traded (lowest 252-session volatility)      FP1: the same return as the universe with a third of the drawdown
  COMBO    the 50 best by the average of the momentum rank (12-1) and the calm rank    FP1: 16.6% / 18.7% a year, drawdown -61% / -21%
  EW       every eligible name, equal weight (the fair control for a stock-picking tilt)
Eligibility as FP1 (india/registrations/fp1_v1.json): top 500 by 60-session median turnover, close >= Rs 10, 252 sessions of history, no one-day
move over 40% in the past 252 sessions. Decided on the close of the last session of a month (or of the first run), filled at the next session's
close, costs from india.costs (delivery charges and the half-spread by turnover rank) on every name that enters or leaves.
Data: the stock paper engine's own adjusted rows (india.paper.load_adjusted, the logged paper_lookback purpose).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import costs, paths

RULES = "factorbook-v1-2026-10-30"
NOTIONAL = 1_000_000
N = 50
JUMP = 0.40
LINES = ("LOWVOL", "COMBO", "EW")


def _dir() -> Path:
    d = paths.data_dir() / "paper" / "factorbook"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _load(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _rows() -> pd.DataFrame:
    from india import paper
    since = (dt.date.today() - dt.timedelta(days=paper.LOOKBACK_CAL_DAYS)).isoformat()
    df = paper.load_adjusted(since=since)
    df = df[~df["is_fund"]] if "is_fund" in df else df
    return df[["date", "symbol", "close", "adj_close", "turnover"]].dropna(subset=["adj_close"]).sort_values(["symbol", "date"])


def pick(df: pd.DataFrame, day: pd.Timestamp) -> dict:
    """The three lines' names on the close of `day`."""
    d = df[df["date"] <= day]
    g = d.groupby("symbol")
    last = g.tail(1).set_index("symbol")
    n = g.size()
    med60 = g["turnover"].apply(lambda s: float(s.tail(60).median()))
    rank = med60.rank(ascending=False, method="first")
    r1 = g["adj_close"].pct_change()
    d = d.assign(r1=r1.values)
    g2 = d.groupby("symbol")
    vol = g2["r1"].apply(lambda s: float(s.tail(252).std()))
    jump = g2["r1"].apply(lambda s: float(s.tail(252).abs().max()))

    def mom(s: pd.Series) -> float:
        a = s["adj_close"].values
        return float(a[-22] / a[-253] - 1) if len(a) >= 253 else np.nan   # month t-12 to t-1, in sessions
    mo = g2.apply(mom)
    t = pd.DataFrame({"n": n, "rank": rank, "vol": vol, "jump": jump, "mom": mo, "close": last["close"]})
    t = t[(t["rank"] <= 500) & (t["close"] >= 10) & (t["n"] >= 253) & (t["jump"] <= JUMP) & t["vol"].notna() & t["mom"].notna()]
    t["r_mom"] = t["mom"].rank(pct=True)
    t["r_calm"] = (-t["vol"]).rank(pct=True)
    t["r_combo"] = (t["r_mom"] + t["r_calm"]) / 2
    return {"LOWVOL": list(t.nsmallest(N, "vol").index), "COMBO": list(t.nlargest(N, "r_combo").index), "EW": list(t.index),
            "eligible": int(len(t)), "ranks": {s: int(r) for s, r in t["rank"].items()}}


def _rebalance(line: dict, names: list[str], px: dict, ranks: dict, when: dt.date) -> dict:
    """Sell names that left, buy names that entered, equal weight of the line's value at the fill closes; costs charged on every leg."""
    value = line["cash"] + sum(q * px.get(s, line["last"].get(s, 0)) for s, q in line["qty"].items())
    target = value / max(len(names), 1)
    cost = 0.0
    new_qty = {}
    for s in names:
        p = px.get(s)
        if not p:
            continue
        new_qty[s] = target / p
    for s in set(line["qty"]) | set(new_qty):
        old_v = line["qty"].get(s, 0) * px.get(s, line["last"].get(s, 0))
        new_v = new_qty.get(s, 0) * px.get(s, 0)
        traded = abs(new_v - old_v)
        if traded <= 1:
            continue
        side = "buy" if new_v > old_v else "sell"
        cost += costs.half_spread_bps(ranks.get(s)) / 1e4 * traded + costs.cost("delivery", side, traded, when.year, when=when)
    invested = sum(new_qty[s] * px[s] for s in new_qty)
    return {"qty": new_qty, "cash": value - invested - cost, "last": {s: px[s] for s in new_qty}, "costs": line.get("costs", 0.0) + cost,
            "rebalanced": when.isoformat(), "names": len(new_qty)}


def run() -> dict:
    df = _rows()
    days = sorted(df["date"].unique())
    if not days:
        return {"status": "no data"}
    last_day = pd.Timestamp(days[-1])
    st = _load(_dir() / "state.json") or {"rules": RULES, "started": None, "lines": {k: {"qty": {}, "cash": float(NOTIONAL), "last": {}, "costs": 0.0} for k in LINES},
                                         "pending": None, "decided_months": []}
    closes = df[df["date"] == last_day].set_index("symbol")["close"].to_dict()
    # 1. fill a pending decision at this session's close (decided on an earlier close)
    pend = st.get("pending")
    if pend and pd.Timestamp(pend["decided_on"]) < last_day:
        for k in LINES:
            st["lines"][k] = _rebalance(st["lines"][k], pend["names"][k], closes, pend["ranks"], last_day.date())
        st["started"] = st["started"] or last_day.date().isoformat()
        st.setdefault("fills", []).append({"decided_on": pend["decided_on"], "filled_on": last_day.date().isoformat(), "eligible": pend["eligible"]})
        st["pending"] = None
    # 2. decide on the last session of a month (the next session is in a new month) or on the very first run
    month = last_day.strftime("%Y-%m")
    first = not st["decided_months"]
    month_end = (last_day + pd.offsets.BDay(1)).month != last_day.month
    if (first or month_end) and month not in st["decided_months"] and not st.get("pending"):
        p = pick(df, last_day)
        st["pending"] = {"decided_on": last_day.date().isoformat(), "names": {k: p[k] for k in LINES}, "ranks": p["ranks"], "eligible": p["eligible"]}
        st["decided_months"].append(month)
    # 3. mark
    out_lines = {}
    for k in LINES:
        ln = st["lines"][k]
        for s in ln["qty"]:
            if closes.get(s):
                ln["last"][s] = closes[s]
        v = ln["cash"] + sum(q * ln["last"].get(s, 0) for s, q in ln["qty"].items())
        out_lines[k] = {"value": round(v), "ret_pct": round(100 * (v / NOTIONAL - 1), 2), "names": len(ln["qty"]), "costs": round(ln.get("costs", 0.0))}
    (_dir() / "state.json").write_text(json.dumps(st, indent=1, default=str))
    mk = {"day": last_day.date().isoformat(), "at": _now(), **{k: out_lines[k]["value"] for k in LINES}}
    mp = _dir() / "marks.jsonl"
    rows = [json.loads(x) for x in mp.read_text().splitlines() if x.strip()] if mp.exists() else []
    rows = [r for r in rows if r.get("day") != mk["day"]] + [mk]
    mp.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def dd(key: str) -> float | None:
        vals = [r[key] for r in rows if r.get(key)]
        if len(vals) < 2:
            return None
        peak, worst = vals[0], 0.0
        for v in vals:
            peak = max(peak, v)
            worst = min(worst, v / peak - 1)
        return round(100 * worst, 2)
    started = st.get("started")
    view = {"rules": RULES, "built_at": _now(), "paper": True, "started": started, "data_through": last_day.date().isoformat(), "lines": out_lines,
            "drawdown_pct": {k: dd(k) for k in LINES}, "sessions": len([r for r in rows if started and r["day"] >= started]),
            "pending": {"decided_on": st["pending"]["decided_on"], "fills_on": "the next session's close"} if st.get("pending") else None,
            "words": ((f"The long-term tilt book (paper, Rs 10 lakh each, started {started}): the calm 50 {out_lines['LOWVOL']['ret_pct']:+.2f}%, "
                       f"momentum-plus-calm 50 {out_lines['COMBO']['ret_pct']:+.2f}%, every eligible stock equal-weight {out_lines['EW']['ret_pct']:+.2f}%. "
                       "Judged over 12 months on drawdown as much as return; nothing is read into it before then.") if started else
                      "The long-term tilt book has decided its first portfolio; it fills at the next session's close and is judged over 12 months.")}
    (_dir() / "view.json").write_text(json.dumps(view, indent=1))
    return view


if __name__ == "__main__":
    v = run() if (sys.argv[1:] or ["run"])[0] == "run" else (_load(_dir() / "view.json") or {})
    print(json.dumps(v, indent=1, default=str)[:1500])
