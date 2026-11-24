"""India stress test (Madhav, 24 Nov 2026: "Some moments are too rare to wait for ... We are testing in environments where we can fail and
nothing happens still. I want to perform some fail tests on Ananta India"; then "We will do it twice. Once now, and the next one is after 30
sessions before live ... keep that as benchmark performance ... Even if it didn't improve, it shouldn't drop the performance").

Scenarios, replay rules and pass marks: india/registrations/stress_v1.md, written and committed before any run (records e670f4e).

  python -m india.stress money [run]       the managed stock book through each scenario        -> reports/stress/<run>/money.json
  python -m india.stress options [run]     the options line's worst nights                       -> options.json
  python -m india.stress machine [run]     the named failure-path tests in both repos            -> machine.json
  python -m india.stress fixture [run]     the crash moments for the words test (app repo)       -> docs/repair_shop/stress/fixture_<run>.json
      (then, in the app repo: scripts/india_stress_words.py <run>                                 -> docs/repair_shop/stress/words_<run>.json)
  python -m india.stress summary [run]     the numbers a later run is compared with              -> summary.json
  python -m india.stress compare B N       run 2's summary against the benchmark's (the no-drop rule); exit 1 on a drop
  Run 2 also replays the benchmark's own book under the code of its day: money [run] --book registrations/stress_v1_benchmark.json

Paper and research only. Reads 2000-2023 bars (gold/bars/adj_daily, silver/kite_index), the managed book's state (copied into memory; no book is
ever written) and the industry labels; never the sealed tree. Nothing here changes a rule.
"""
from __future__ import annotations

import copy
import datetime as dt
import functools
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import costs, managed, paths

SEED = 20261124
MAX_MOVE = 0.40                    # a one-day move past this is a data fault (unrecorded splits; data audit of 29 Oct 2026)
MIN_PEERS = 5
START_DAY = "2026-11-23"           # the managed book as it stood after this session is the benchmark's book
HIST = {
    "H1": ("2020-02-20", "2020-04-07", "COVID crash and first rebound"),
    "H2": ("2020-03-23", "2020-03-23", "the worst day: Nifty -13.0%, opened -9.1%"),
    "H3": ("2008-09-29", "2008-10-27", "after Lehman; 24 Oct 2008 -12.2%"),
    "H4": ("2008-01-14", "2008-01-25", "the January 2008 crash"),
    "H5": ("2004-05-13", "2004-05-18", "the 2004 election shock"),
    "H6": ("2016-11-08", "2016-11-21", "demonetisation and the US election night"),
    "H7": ("2008-01-07", "2008-11-20", "the slow bleed of 2008"),
    "H8": ("2018-08-28", "2018-10-26", "IL&FS: financial stocks crash, the Nifty far less"),
    "H9": ("2009-05-18", "2009-05-18", "the up shock: Nifty +17.7% in a day"),
    "H10": ("2015-08-10", "2015-08-28", "China devaluation, a moderate fall"),
}
C1_DAYS = ["2020-03-23", "2008-10-24"]
BOOT_PATHS, BOOT_BLOCKS, BOOT_LEN = 2000, 4, 5
OPT_FROM = "2008-01-01"                                  # index opens before 2008 are not reliable in our index file
OPT_EXCLUDE = {("NIFTY BANK", "2009-02-27")}             # the bank stocks rose that day: the index row is a data fault
OPT_T0, OPT_T1, OPT_R = 7 / 365, 6 / 365, 0.065          # an option a week from expiry, held one night (assumption, said on the page)
RECORDS_TESTS = ["tests/test_india_audit_fixes.py", "tests/test_india_managed.py", "tests/test_india_managed_mark_12nov.py",
                 "tests/test_india_data_gaps.py", "tests/test_india_lock.py", "tests/test_india_sealed_crosses.py", "tests/test_india_stress.py"]
APP_TESTS = ["tests/test_india_livesession.py", "tests/test_india_opening_without_model_23nov.py", "tests/test_india_live_voice.py",
             "tests/test_india_stress_words.py"]
APP = Path.home() / "code" / "ananta-agent-research"
RECORDS = Path(__file__).resolve().parents[1]


def run_dir(run: str | None = None) -> Path:
    d = paths.data_dir() / "reports" / "stress" / (run or dt.date.today().isoformat())
    d.mkdir(parents=True, exist_ok=True)
    return d


# ------------------------------------------------------------------------------------------------------------------------------ the data
@functools.lru_cache(maxsize=1)
def index_bars() -> pd.DataFrame:
    """Index day bars to 2023 (silver): index_name, date, open, close."""
    f = paths.data_dir() / "silver" / "kite_index" / "day" / "day.parquet"
    d = pd.read_parquet(f, columns=["index_name", "date", "open", "close"])
    d["date"] = pd.to_datetime(d["date"])
    return d[d["date"] <= "2023-12-31"].sort_values(["index_name", "date"])


@functools.lru_cache(maxsize=8)
def index_moves(name: str) -> pd.DataFrame:
    s = index_bars()
    s = s[s["index_name"] == name].set_index("date")
    return pd.DataFrame({"ret": s["close"].pct_change(), "gap": s["open"] / s["close"].shift(1), "close": s["close"], "open": s["open"]})


@functools.lru_cache(maxsize=1)
def sessions() -> list[pd.Timestamp]:
    return list(index_moves("NIFTY 500").index)


@functools.lru_cache(maxsize=1)
def _pos() -> dict:
    return {d: i for i, d in enumerate(sessions())}


def window(a: str, b: str) -> list[pd.Timestamp]:
    return [d for d in sessions() if pd.Timestamp(a) <= d <= pd.Timestamp(b)]


def next_session(d: pd.Timestamp) -> pd.Timestamp | None:
    s, i = sessions(), _pos().get(d)
    return s[i + 1] if i is not None and i + 1 < len(s) else None


def labels() -> pd.DataFrame:
    return pd.read_parquet(paths.data_dir() / "silver" / "reference" / "industry_labels.parquet", columns=["symbol", "isin", "industry"])


def _sids(symbol: str, isin: str | None, names: pd.DataFrame) -> set:
    """Our bars carry the trading symbol before 22 Jun 2011 and the ISIN after; one company is both, plus any older symbol of its ISIN."""
    out = {symbol}
    isins = set(names.loc[names["symbol"] == symbol, "isin"].dropna())      # a split gives a new ISIN: every ISIN the symbol traded under
    if isinstance(isin, str) and isin:
        isins.add(isin)
    if "entity" in names.columns:
        ents = set(names.loc[names["isin"].isin(isins), "entity"].dropna())
        isins |= set(names.loc[names["entity"].isin(ents), "isin"].dropna())
    out |= isins
    out |= set(names.loc[names["isin"].isin(isins), "symbol"].dropna())
    return out


def _clean(x: pd.DataFrame) -> pd.DataFrame:
    x = x.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
    out = pd.DataFrame({"ret": x["c"] / x["c"].shift(1) - 1, "gap": x["o"] / x["c"].shift(1)})
    bad = (out["ret"].abs() > MAX_MOVE) | ~out["gap"].between(1 - MAX_MOVE, 1 + MAX_MOVE)
    out.loc[bad, ["ret", "gap"]] = np.nan
    return out


class Moves:
    """Each holding's own real move on a historical day, with the stand-ins written in stress_v1.md: its industry's median (5 or more peers),
    else the Nifty 500; NIFTYBEES takes the Nifty 50; a move over 40% either way is a data fault and is stood in for the same way."""

    def __init__(self, symbols: list[str]):
        lab = labels()
        names = pd.read_parquet(paths.data_dir() / "silver" / "security_master" / "names.parquet", columns=["isin", "symbol", "entity"])
        self.industry = {s: (lab.loc[lab["symbol"] == s, "industry"].iloc[0] if (lab["symbol"] == s).any() else None) for s in symbols}
        wanted = {i for i in self.industry.values() if i}
        members = lab[lab["industry"].isin(wanted)]
        ent = {}                                                   # entity key -> sids
        for s in symbols:
            isin = lab.loc[lab["symbol"] == s, "isin"].iloc[0] if (lab["symbol"] == s).any() else None
            ent[("own", s)] = _sids(s, isin, names)
        for r in members.itertuples():
            ent[("peer", r.symbol)] = _sids(r.symbol, r.isin, names)
        allsids = sorted(set().union(*ent.values()))
        adj = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["date", "sid", "o", "c"], filters=[("sid", "in", allsids)])
        adj["date"] = pd.to_datetime(adj["date"])
        by = dict(tuple(adj.groupby("sid")))
        def series(sids):
            parts = [by[x] for x in sids if x in by]
            return _clean(pd.concat(parts)) if parts else None
        self.own = {s: series(ent[("own", s)]) for s in symbols}
        rows = []
        for r in members.itertuples():
            x = series(ent[("peer", r.symbol)])
            if x is not None:
                rows.append(x.assign(industry=r.industry))
        peers = pd.concat(rows).reset_index() if rows else pd.DataFrame(columns=["date", "ret", "gap", "industry"])
        g = peers.dropna(subset=["ret"]).groupby(["date", "industry"])
        self.peer = pd.DataFrame({"ret": g["ret"].median(), "gap": g["gap"].median(), "n": g["ret"].size()})
        self.n500, self.n50 = index_moves("NIFTY 500"), index_moves("NIFTY 50")

    def day(self, d: pd.Timestamp) -> dict:
        if not hasattr(self, "_seen"):
            self._seen = {}
        if d not in self._seen:
            self._seen[d] = self._day(d)
        return self._seen[d]

    def _day(self, d: pd.Timestamp) -> dict:
        out = {}
        n500 = self.n500.loc[d] if d in self.n500.index else None
        for s, own in self.own.items():
            if s.endswith("BEES") and d in self.n50.index:
                r = self.n50.loc[d]
                out[s] = {"ret": float(r["ret"]), "gap": float(r["gap"]) if pd.notna(r["gap"]) else 1.0, "src": "nifty50"}
                continue
            ind = self.industry.get(s)
            pr = self.peer.loc[(d, ind)] if ind and (d, ind) in self.peer.index else None
            pr = pr if pr is not None and pr["n"] >= MIN_PEERS else None
            o = own.loc[d] if own is not None and d in own.index else None
            if o is not None and pd.notna(o["ret"]):
                gap = o["gap"] if pd.notna(o["gap"]) else (pr["gap"] if pr is not None else 1.0)
                out[s] = {"ret": float(o["ret"]), "gap": float(gap), "src": "own"}
            elif pr is not None:
                out[s] = {"ret": float(pr["ret"]), "gap": float(pr["gap"]) if pd.notna(pr["gap"]) else 1.0, "src": "industry"}
            else:
                ok = n500 is not None
                out[s] = {"ret": float(n500["ret"]) if ok else 0.0, "gap": float(n500["gap"]) if ok and pd.notna(n500["gap"]) else 1.0, "src": "nifty500"}
        return out


# ------------------------------------------------------------------------------------------------------------------------- the book
def book_now() -> dict:
    """The managed book as it stands (a deep copy: nothing is ever written back)."""
    return copy.deepcopy(json.loads((paths.data_dir() / "paper" / "managed" / "state.json").read_text()))


def _value(pos: dict, cash: float, mult: dict | None = None) -> float:
    return cash + sum(p["qty"] * p["last"] * ((mult or {}).get(s, 1.0)) for s, p in pos.items())


@functools.lru_cache(maxsize=1)
def _synthetic_days(n: int = 400) -> tuple:
    """The sessions after START_DAY on the book's own calendar: scenario day k is played as if it were the k-th session from now, so the
    book's exit code counts its holding days as it would."""
    out, d = [], dt.date.fromisoformat(START_DAY)
    for _ in range(n):
        d = managed.next_session(d)
        out.append(d.isoformat())
    return tuple(out)


def replay(book: dict, days: list[pd.Timestamp], mv, c: dict, after: pd.Timestamp | None = None) -> dict:
    """Plays the book's stocks and cash through the given historical days. Exits are the book's own code (managed.exits on the close); a sale
    fills at the next session's real open less slippage and delivery costs. The options money is left out (stressed by options())."""
    pos = {s: dict(p) for s, p in book["positions"].items() if p.get("qty", 0) > 0}
    cash = float(book["cash_inr"])
    slip = c["slippage_pct"] / 100
    syn = _synthetic_days()
    path = [_value(pos, cash)]
    peak, pending, stops, limit_days, pause_at, srcs, day_rows = path[0], [], [], [], None, {}, []

    def fill_open(m: dict, label: str):
        nonlocal cash
        for s in pending:
            p = pos.pop(s, None)
            if not p:
                continue
            price = p["last"] * m[s]["gap"] * (1 - slip)
            value = p["qty"] * price
            k = costs.cost("delivery", "sell", value)
            cash += value - k
            stops.append({"symbol": s, "stop": p.get("stop"), "fill": round(price, 2), "on": label,
                          "past_stop_pct": round(100 * (price / p["stop"] - 1), 2) if p.get("stop") else None, "cost_inr": round(k, 2)})

    for k, d in enumerate(days):
        m = mv(d)
        for s, x in m.items():
            srcs[x["src"]] = srcs.get(x["src"], 0) + (1 if s in pos else 0)
        start = path[-1]
        fill_open(m, d.date().isoformat())
        pending = []
        at_open = _value(pos, cash, {s: m[s]["gap"] for s in pos})
        for s, p in pos.items():
            p["last"] = p["last"] * (1 + m[s]["ret"])
        eq = _value(pos, cash)
        day_ret, open_ret = eq / start - 1, at_open / start - 1
        day_rows.append({"day": d.date().isoformat(), "ret_pct": round(100 * day_ret, 2), "open_pct": round(100 * open_ret, 2)})
        if day_ret <= -0.05:
            limit_days.append({"day": d.date().isoformat(), "loss_pct": round(100 * day_ret, 2), "at_open_pct": round(100 * open_ret, 2),
                               "open_alone_past_limit": open_ret <= -0.05})
        peak = max(peak, eq)
        if pause_at is None and eq <= peak * 0.78:
            pause_at = {"session": k + 1, "day": d.date().isoformat()}
        pending = [e["symbol"] for e in managed.exits({"positions": pos}, syn[k], pd.DataFrame({"symbol": []}), c) if e["symbol"] in pos]
        path.append(eq)
    next_open = None
    if pending and after is not None:
        m = mv(after)
        fill_open(m, after.date().isoformat() + " (next open)")
        path.append(_value(pos, cash, {s: m[s]["gap"] for s in pos}))
        next_open = after
    arr = np.array(path)
    dd = float(np.max(1 - arr / np.maximum.accumulate(arr)))
    return {"start_inr": round(path[0], 2), "end_inr": round(path[-1], 2), "total_pct": round(100 * (path[-1] / path[0] - 1), 2),
            "deepest_fall_pct": round(100 * dd, 2), "worst_day_pct": min((r["ret_pct"] for r in day_rows), default=0.0),
            "stops": stops, "limit_days": limit_days, "pause": pause_at, "moves_by_source": srcs, "days": day_rows if len(day_rows) <= 60 else None,
            "next_open": next_open}


def market(days: list[pd.Timestamp], after: pd.Timestamp | None = None, name: str = "NIFTY 500") -> dict:
    """The index over the same sessions (with the next open when the book had a sale waiting, so both are measured alike)."""
    ix = index_moves(name)
    path = [1.0]
    for d in days:
        path.append(path[-1] * (1 + float(ix.loc[d, "ret"])))
    if after is not None and pd.notna(ix.loc[after, "gap"]):
        path.append(path[-1] * float(ix.loc[after, "gap"]))
    arr = np.array(path)
    return {"total_pct": round(100 * (arr[-1] - 1), 2), "deepest_fall_pct": round(100 * float(np.max(1 - arr / np.maximum.accumulate(arr))), 2),
            "worst_day_pct": round(100 * min(float(ix.loc[d, "ret"]) for d in days), 2)}


# -------------------------------------------------------------------------------------------------------------------- money: the scenarios
def _fast() -> None:
    """The book's exit code asks for the holiday list on every call; within this run it does not change, so it is read once (run-time only)."""
    if not hasattr(managed.holidays, "cache_info"):
        managed.holidays = functools.lru_cache(maxsize=1)(managed.holidays)


def snapshot(book: dict) -> dict:
    pos = {s: {k: p.get(k) for k in ("qty", "last", "stop", "source", "entered", "last_on")} for s, p in book["positions"].items() if p.get("qty", 0) > 0}
    return {"positions": pos, "cash_inr": round(float(book["cash_inr"]), 2), "options_inr": book.get("options_inr"),
            "stocks_and_cash_inr": round(_value(pos, float(book["cash_inr"])), 2),
            "last_marked": max((p.get("last_on") or "" for p in pos.values()), default=None)}


def crisis_blocks() -> list[list[pd.Timestamp]]:
    """Every run of 5 consecutive sessions that starts while the Nifty 50 is more than 10% under its 60-session high (2003-2023)."""
    n = index_moves("NIFTY 50")["close"].dropna()
    crisis = n < 0.9 * n.rolling(60, min_periods=20).max()
    s = sessions()
    pos = _pos()
    out = []
    for d in n.index[crisis.values]:
        i = pos.get(d)
        if i is not None and i + BOOT_LEN <= len(s):
            out.append(s[i:i + BOOT_LEN])
    return out


def _ratio(book_dd: float, mk_dd: float) -> float | None:
    return round(book_dd / mk_dd, 2) if mk_dd >= 0.5 else None


def money(book: dict | None = None, paths_n: int = BOOT_PATHS) -> dict:
    _fast()
    book = book or book_now()
    c = managed.cfg()
    snap = snapshot(book)
    mv = Moves(sorted(snap["positions"])).day
    out = {"book": snap, "config_version": c.get("version"), "scenarios": {}}
    for hid, (a, b, what) in HIST.items():
        days = window(a, b)
        r = replay(book, days, mv, c, next_session(days[-1]))
        mk = market(days, r["next_open"])
        ratio = _ratio(r["deepest_fall_pct"], mk["deepest_fall_pct"])
        out["scenarios"][hid] = {"what": what, "from": a, "to": b, "sessions": len(days), "book": r, "nifty500": mk, "ratio": ratio,
                                 "M1": None if ratio is None else ratio <= 1.25}
    days = [pd.Timestamp(x) for x in C1_DAYS]
    r = replay(book, days, mv, c, next_session(days[-1]))
    mk = market(days, r["next_open"])
    out["scenarios"]["C1"] = {"what": "the two worst days back to back (23 Mar 2020, then 24 Oct 2008)", "sessions": 2, "book": r, "nifty500": mk,
                              "M3": r["deepest_fall_pct"] <= mk["deepest_fall_pct"] + 5.0}
    blocks = crisis_blocks()
    rng = np.random.default_rng(SEED)
    rows = []
    for _ in range(paths_n):
        pick = rng.integers(0, len(blocks), BOOT_BLOCKS)
        days = [d for i in pick for d in blocks[i]]
        r = replay(book, days, mv, c, next_session(days[-1]))
        mk = market(days, r["next_open"])
        rows.append((r["deepest_fall_pct"], mk["deepest_fall_pct"], r["total_pct"], bool(r["pause"]), bool(r["limit_days"]), len(r["stops"])))
    a = np.array(rows, dtype=float)
    q = lambda col, p: round(float(np.percentile(a[:, col], p)), 2)  # noqa: E731
    out["scenarios"]["B1"] = {"what": f"{paths_n} made-up 20-session paths from {len(blocks)} real crisis blocks (seed {SEED})", "paths": paths_n,
                              "book_fall_p95": q(0, 95), "book_fall_p99": q(0, 99), "nifty500_fall_p95": q(1, 95), "nifty500_fall_p99": q(1, 99),
                              "book_total_median": q(2, 50), "pause_share": round(float(a[:, 3].mean()), 3), "limit_day_share": round(float(a[:, 4].mean()), 3),
                              "stops_median": q(5, 50)}
    b1 = out["scenarios"]["B1"]
    b1["ratio_p99"] = _ratio(b1["book_fall_p99"], b1["nifty500_fall_p99"])
    b1["M2"] = b1["ratio_p99"] is None or b1["ratio_p99"] <= 1.25
    m1 = [v["M1"] for k, v in out["scenarios"].items() if k.startswith("H") and v["M1"] is not None]
    out["marks"] = {"M1": all(m1), "M1_failed": [k for k, v in out["scenarios"].items() if k.startswith("H") and v["M1"] is False],
                    "M2": b1["M2"], "M3": out["scenarios"]["C1"]["M3"]}
    return out


# --------------------------------------------------------------------------------------------------------------------------- options
def _bs(S: float, K: float, T: float, sig: float, call: bool, r: float = OPT_R) -> float:
    N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))  # noqa: E731
    if T <= 0 or sig <= 0:
        return max(0.0, S - K) if call else max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    return S * N(d1) - K * math.exp(-r * T) * N(d2) if call else K * math.exp(-r * T) * N(-d2) - S * N(-d1)


def premiums() -> dict:
    """The options line's own premiums (realistic fills) from its scored record, and the nights both indices were held at once."""
    rows = [json.loads(x) for x in (paths.data_dir() / "paper" / "sp1" / "outcomes.jsonl").read_text().splitlines() if x.strip()]
    by, nights = {}, {}
    for r in rows:
        o = ((r.get("legs") or {}).get("option") or {})
        p = o.get("premium_rs_realistic") or o.get("premium_rs_study")
        if p:
            by.setdefault(r["index"], []).append(float(p))
            if r.get("exit_day") and r.get("exit_day") > r.get("date"):
                nights.setdefault(r["date"], set()).add(r["index"])
    allp = [p for v in by.values() for p in v]
    return {"max": max(allp) if allp else None, "median": float(np.median(allp)) if allp else None, "n": len(allp),
            "max_by_index": {k: max(v) for k, v in by.items()}, "both_held_overnight": sorted(d for d, s in nights.items() if len(s) > 1)}


def options() -> dict:
    pr = premiums()
    vix = index_moves("INDIA VIX")["close"]
    rows = []
    for name, key in (("NIFTY 50", "NIFTY"), ("NIFTY BANK", "BANKNIFTY")):
        ix = index_moves(name)
        ix = ix[(ix.index >= OPT_FROM) & ix["gap"].notna()]
        ix = ix[[(name, d.date().isoformat()) not in OPT_EXCLUDE for d in ix.index]]
        for side, sel in (("down", ix.nsmallest(5, "gap")), ("up", ix.nlargest(5, "gap"))):
            for d, row in sel.iterrows():
                g = float(row["gap"]) - 1
                prev = next((x for x in reversed(sessions()) if x < d), None)
                sig0 = float(vix.loc[prev]) / 100 if prev is not None and prev in vix.index and pd.notna(vix.loc[prev]) else 0.25
                sig1 = max(sig0, float(vix.loc[d]) / 100) if d in vix.index and pd.notna(vix.loc[d]) else max(sig0, 0.40)
                call = side == "down"                     # a long call held into a fall; a long put held into a jump
                v0, v1 = _bs(1.0, 1.0, OPT_T0, sig0, call), _bs(1.0 + g, 1.0, OPT_T1, sig1, call)
                share = max(0.0, 1 - v1 / v0)
                rows.append({"index": key, "day": d.date().isoformat(), "gap_pct": round(100 * g, 2), "held": "call" if call else "put",
                             "vol_before": round(sig0, 3), "vol_after": round(sig1, 3), "premium_lost_share": round(share, 3),
                             "rs_at_max": round(share * (pr["max"] or 0)), "rs_at_median": round(share * (pr["median"] or 0)),
                             "rs_at_own_max": round(share * (pr["max_by_index"].get(key) or pr["max"] or 0))})
    single_max = max(r["rs_at_max"] for r in rows)
    single_med = max(r["rs_at_median"] for r in rows)
    joint = {}
    for r in rows:                                          # the same night, both indices, the same way
        joint.setdefault((r["day"], r["held"]), []).append(r)
    joint_rows = [{"day": d, "held": h, "indices": [x["index"] for x in v], "rs_at_own_max": sum(x["rs_at_own_max"] for x in v),
                   "rs_at_median": sum(x["rs_at_median"] for x in v)} for (d, h), v in joint.items() if len(v) > 1]
    worst_joint = max((j["rs_at_own_max"] for j in joint_rows), default=0)
    worst_joint_med = max((j["rs_at_median"] for j in joint_rows), default=0)
    o1_night = max(single_max, worst_joint)
    o2_night = max(single_med, worst_joint_med)
    return {"premiums": pr, "assumption": "an at-the-money option a week from expiry, bought the day before, valued at the next open with the "
            "fear gauge of that day (Black-Scholes); before Mar 2009 there is no fear gauge, so 40% is used",
            "nights": rows, "joint_nights": joint_rows, "worst_single_at_max": single_max, "worst_single_at_median": single_med,
            "worst_joint_at_own_max": worst_joint, "worst_joint_at_median": worst_joint_med,
            "O1_worst_night": o1_night, "O1": o1_night <= 25000, "O2_worst_night": o2_night, "O2": o2_night <= 12500}


# --------------------------------------------------------------------------------------------------------------------------- machine
def _pytest(repo: Path, python: str, files: list[str]) -> dict:
    out = {}
    for f in files:
        try:
            r = subprocess.run([python, "-m", "pytest", "-q", "-p", "no:cacheprovider", f], cwd=repo, capture_output=True, text=True, timeout=900)
            tail = (r.stdout or r.stderr).strip().splitlines()[-1:] or [""]
            out[f] = {"ok": r.returncode == 0, "line": tail[0][:160]}
        except Exception as e:  # noqa: BLE001
            out[f] = {"ok": False, "line": f"{type(e).__name__}: {str(e)[:120]}"}
    return out


def machine() -> dict:
    """The named failure-path tests in both repos, and last night's leak check and firewall (read, never re-run here)."""
    app_py = str(Path.home() / "ananta_venvs" / "jarvis" / "bin" / "python")
    out = {"records": _pytest(RECORDS, sys.executable, RECORDS_TESTS), "app": _pytest(APP, app_py, APP_TESTS), "manifests": {}}
    for name in ("leakcheck", "firewall"):
        try:
            m = json.loads((paths.manifest_dir() / f"{name}.json").read_text())
            checks = {k: (v.get("ok") if isinstance(v, dict) else v) for k, v in m.items() if not k.startswith("_")}
            out["manifests"][name] = {"ok": all(bool(v) for v in checks.values()), "checks": len(checks), "at": m.get("_at")}
        except Exception as e:  # noqa: BLE001
            out["manifests"][name] = {"ok": False, "at": None, "error": f"{type(e).__name__}"}
    out["X"] = all(v["ok"] for part in ("records", "app", "manifests") for v in out[part].values())
    return out


# --------------------------------------------------------------------------------------------------------------- words: the crash moments
def _move_words(mv: dict, pos: dict) -> str:
    rows = sorted(((s, 100 * mv[s]["ret"]) for s in pos if s in mv), key=lambda x: x[1])
    return ", ".join(f"{s} {r:+.1f}%" for s, r in rows)


def fixture(m: dict) -> dict:
    """The stand-in moments for the words test (W1-W4), from this run's own money replay; read by the app's scripts/india_stress_words.py."""
    snap = m["book"]
    mv = Moves(sorted(snap["positions"])).day
    def ix(name, d):
        r = index_moves(name).loc[pd.Timestamp(d)]
        return {"ret": round(float(r["ret"]), 4), "gap": round(float(r["gap"]) - 1, 4) if pd.notna(r["gap"]) else None}
    def vix(d):
        v = index_moves("INDIA VIX")["close"]
        return round(float(v.loc[pd.Timestamp(d)]), 2) if pd.Timestamp(d) in v.index else None
    h2, h9, h7 = (m["scenarios"][k]["book"] for k in ("H2", "H9", "H7"))
    d2, d9 = pd.Timestamp("2020-03-23"), pd.Timestamp("2009-05-18")
    stops2 = ", ".join(s["symbol"] for s in h2["stops"]) or "none"
    out = {
        "note": "stand-in moments built from real days of 2004-2020 applied to today's books; not real prices",
        "W1": {"nifty": ix("NIFTY 50", d2), "bank": ix("NIFTY BANK", d2), "vix": vix(d2),
               "holdings_words": f"Stand-in moment: your stocks (the managed book's) moved {h2['worst_day_pct']:+.1f}% today: {_move_words(mv(d2), snap['positions'])}.",
               "managed_words": f"Stops hit at today's close: {stops2}; a stop is sold at the next session's open, which can be below the stop."},
        "W2": {"nifty": ix("NIFTY 50", d2), "bank": ix("NIFTY BANK", d2), "vix": vix(d2), "no_prices": True},
        "W3": {"nifty": ix("NIFTY 50", d9), "bank": ix("NIFTY BANK", d9), "vix": vix(d9),
               "holdings_words": f"Stand-in moment: your stocks (the managed book's) moved {h9['worst_day_pct']:+.1f}% today: {_move_words(mv(d9), snap['positions'])}."},
        "W4": {"nifty": {"ret": -0.021, "gap": -0.006}, "bank": {"ret": -0.026, "gap": -0.008}, "vix": 38.0,
               "holdings_words": (f"Stand-in moment: over the last {m['scenarios']['H7']['sessions']} sessions the managed book's stocks and cash have fallen "
                                  f"{h7['deepest_fall_pct']:.0f}% from their high and the Nifty 500 {m['scenarios']['H7']['nifty500']['deepest_fall_pct']:.0f}%; "
                                  + (f"the 22% pause line was crossed on session {h7['pause']['session']} (on paper it is recorded, not acted on)."
                                     if h7.get("pause") else "the 22% pause line was not crossed."))},
    }
    return out


# -------------------------------------------------------------------------------------------------------------------------- the page
def _pct(x) -> str:
    return "-" if x is None else f"{x:+.1f}%"


def _yes(x) -> str:
    return "n/a" if x is None else ("PASS" if x else "FAIL")


def summary(m: dict, o: dict, x: dict, w: dict | None) -> dict:
    """The benchmark's numbers: what run 2 is compared with."""
    sc = m["scenarios"]
    return {"book": m["book"], "money": {k: ({"book_fall": v["book"]["deepest_fall_pct"], "market_fall": v["nifty500"]["deepest_fall_pct"],
                                              "book_total": v["book"]["total_pct"], "ratio": v.get("ratio")} if "book" in v else
                                             {"book_fall_p99": v["book_fall_p99"], "nifty500_fall_p99": v["nifty500_fall_p99"], "ratio_p99": v["ratio_p99"]})
                                         for k, v in sc.items()},
            "marks": {**m["marks"], "O1": o["O1"], "O2": o["O2"], "X": x["X"],
                      "W_a": None if not w else w.get("W_a"), "W_b": None if not w else w.get("W_b")},
            "options": {"O1_worst_night": o["O1_worst_night"], "O2_worst_night": o["O2_worst_night"]},
            "words": None if not w else {"turns": w.get("turns"), "passed": w.get("passed"), "grader_passed": w.get("grader_passed")}}


def compare(bench: dict, new: dict, tol: float = 0.5) -> list[str]:
    """The no-drop rule (stress_v1.md): a figure worse than the benchmark by more than tol points, or a pass that turned to a fail."""
    out = []
    for k, b in bench["money"].items():
        n = new["money"].get(k) or {}
        for f in ("book_fall", "book_fall_p99"):
            if f in b and f in n and n[f] - b[f] > tol:
                out.append(f"{k}: the book's deepest fall {b[f]:.1f}% -> {n[f]:.1f}%")
    for mk, b in bench["marks"].items():
        if b is True and new["marks"].get(mk) is False:
            out.append(f"{mk}: PASS -> FAIL")
    bw, nw = bench.get("words") or {}, new.get("words") or {}
    if bw.get("passed") is not None and (nw.get("passed") or 0) < bw["passed"]:
        out.append(f"words: {bw['passed']} turns passed -> {nw.get('passed')}")
    for f in ("O1_worst_night", "O2_worst_night"):
        if new["options"][f] > bench["options"][f] * 1.02:
            out.append(f"options {f}: Rs {bench['options'][f]:,} -> Rs {new['options'][f]:,}")
    return out


def _load(d: Path, name: str):
    p = d / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _save(d: Path, name: str, obj) -> Path:
    p = d / f"{name}.json"
    p.write_text(json.dumps(obj, indent=1, default=str))
    return p


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "help"
    if cmd == "compare":
        b, n = (json.loads(Path(x).read_text()) for x in argv[1:3])
        drops = compare(b, n)
        print("\n".join(drops) or "no drop against the benchmark")
        return 1 if drops else 0
    run = argv[1] if len(argv) > 1 and not argv[1].startswith("-") else None
    d = run_dir(run)
    if cmd == "money":
        book = None
        if "--book" in argv:
            book = json.loads(Path(argv[argv.index("--book") + 1]).read_text())["book"]
        print(_save(d, "money", money(book)))
    elif cmd == "options":
        print(_save(d, "options", options()))
    elif cmd == "machine":
        print(_save(d, "machine", machine()))
    elif cmd == "fixture":
        out = APP / "docs" / "repair_shop" / "stress"
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"fixture_{d.name}.json"
        p.write_text(json.dumps(fixture(_load(d, "money")), indent=1))
        print(p)
    elif cmd == "summary":
        w = APP / "docs" / "repair_shop" / "stress" / f"words_{d.name}.json"
        s = summary(_load(d, "money"), _load(d, "options"), _load(d, "machine"), json.loads(w.read_text()) if w.exists() else None)
        print(_save(d, "summary", {"run": d.name, **s}))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
