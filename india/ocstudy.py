"""OC v1: Madhav's Opening Decision Protocol V1, the primary tests exactly as approved and frozen (registrations/oc_v1.json).

  python -m india.ocstudy notes     write registrations/oc_v1_implementation.json: every interpretation the code makes, frozen BEFORE any result
  python -m india.ocstudy run       decisions and trades 2015-2023 (silver and gold only), the primary tests into the ledger (family OC), the report
  python -m india.ocstudy report    rewrite registrations/oc_v1_results.md from the saved tables (no new ledger rows)

Reads silver/gold only: dev 2015-2017, validation 2018-2023. sealed/ is never read. Outputs:
  gold/studies/OC1_index_trades.parquet   one row per index-day x variant x version (FILTERED = the protocol, BASELINE = same entries/exits, no filters)
  gold/studies/OC1_index_days.parquet     one row per index-day x k: the protocol's state by 10:15 (CONFIRMED_LONG / CONFIRMED_SHORT / WAIT) and why
  gold/studies/OC1_stock_trades.parquet   one row per stock trade x variant x version
  gold/studies/OC1_breadth.parquet        breadth of the eligible top 50 per day and 5-minute bar (09:15-10:15)
  manifests/oc_v1_results.json, registrations/oc_v1_results.md

Unit of account for the tests is net basis points of the entry price per trade (one unit), after costs; the Rs 1,000 sizing layer is reported
separately (engine first, sizing configurable: 18 Oct directive).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import costs, paths, registry

HERE = Path(__file__).parent
SPEC = HERE / "registrations" / "oc_v1.json"
NOTES = HERE / "registrations" / "oc_v1_implementation.json"
REPORT = HERE / "registrations" / "oc_v1_results.md"
YEARS = list(range(2015, 2024))
DEV_LAST = 2017
IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
TICK = 0.05
NMIN, NB5 = 375, 75          # 1-minute bars 09:15..15:29, 5-minute bars 09:15..15:25
DEC_MIN, DEC_B5 = 59, 11     # last bar whose close is at or before 10:15 (1-minute bar 10:14, 5-minute bar 10:10)
EXIT_MIN, EXIT_B5 = 360, 72  # the 15:15 bar: time exit at its open
B_LONG, B_SHORT, RVOL_MIN, AGREE = 0.60, 0.40, 1.5, 0.0005
MIN_BREADTH_NAMES = 20
RETEST = {"index": (0.0010, 30), "stock": (0.0020, 6)}   # band, window in bars (30 minutes)
VARIANTS = [f"k{k}|{e}|{x}" for k in (15, 30) for e in ("E1", "E2") for x in ("X1", "X2")]
ETF_RE = re.compile(r"(?:BEES|ETF|IETF)$|^(?:N100|MON100|MAFANG|LIQUID[A-Z0-9]*|SETF[A-Z0-9]*)$")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _git() -> str:
    try:
        return subprocess.run(["git", "-C", str(HERE.parent), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        return "?"


def _max_risk() -> float:
    cfg = json.loads((HERE / "paper_config.json").read_text())
    v = cfg["intraday"].get("max_risk_per_trade_inr")
    return float(v) if v else float("nan")  # withdrawn 19 Oct (risk is a research output): the sizing layer is then skipped


# ----------------------------------------------------------------------------------------------------------------------------- notes
INTERPRETATIONS = {
    "bar_timing": "bars are labelled by their start time; a 1-minute bar starting at t closes at t+1, a 5-minute bar starting at s closes at s+5. A decision is made at a bar's close and filled at the next bar's open.",
    "deadline": "the confirming bar must close by 10:15 IST: index 1-minute bars starting 09:15+k .. 10:14, stock 5-minute bars starting 09:15+k .. 10:10. No confirmed state by then = WAIT, and the day ends NO_TRADE.",
    "filtered_entry": "the protocol (FILTERED) takes the first bar before the deadline at which the break AND every filter hold together (a break that fails the filters can still confirm on a later bar). BASELINE takes the first break bar, no filters. Long or short, whichever confirms first; one trade per index per day, one per stock per day.",
    "agreement": "index: Nifty 50 and Nifty Bank have both moved at least 0.05% since their 09:15 open in the trade's direction at the decision bar's close. Stocks: the stock and Nifty 50 both moved at least 0.05% since 09:15 in the trade's direction, Nifty read at the close of the minute that ends the stock's bar.",
    "breadth": "share of eligible top-50 names (same eligibility rule, rank <= 50) whose last closed 5-minute bar is above their own 09:15 open. For an index decision at a minute's close, only stock bars that had closed by then are used. Fewer than 20 eligible names = breadth undefined; such days are excluded from the index tests (both versions) and counted.",
    "rvol": "cumulative volume 09:15 to the end of the decision bar over the median of the same window in the previous 20 regular sessions; at least 15 of those 20 sessions with valid data for the stock, else not eligible that day; special sessions are left out of the baseline and of the study.",
    "vwap": "stocks: cumulative (high+low+close)/3 x volume over cumulative volume from 09:15 to the decision bar's close (NSE-scaled prices).",
    "retest_E2": "after the confirming bar, within the next 30 minutes (index 30 bars, stocks 6 bars): a bar whose low (long) comes within 0.10% (index) / 0.20% (stocks) of the broken OR edge without going more than that band through it, followed by a bar that closes beyond the band on the break side and does not go through the band; entry at the open of the bar after. A bar that goes through the band first = failed retest, no trade (counted). The confirmation is still by 10:15; the E2 fill can come up to 30 minutes later. Short mirrored.",
    "stops_X1": "E1/E3: the opposite OR edge. E2: the retest extreme (lowest low from the bar after the break to the closing-away bar, long). Checked from the entry bar on; a bar that opens beyond the stop fills at its open, else at the stop. Time exit at the open of the 15:15 bar.",
    "stops_X2": "distance = min(invalidation distance, max(m x OR width, floor)); floor = max(2 ticks, 0.5 x ATR14 of 5-minute bars at entry). m = 80th percentile of MAE / OR width of the dev-period (2015-2017) winners (net > 0) of the same instrument, k and entry under X1, FILTERED version; BASELINE uses the same m (same exits). Walk-forward folds refit m on all years before the test year.",
    "atr5": "ATR14 over the 14 most recent closed 5-minute bars, the previous session's tail included when today has fewer; true range within a session uses the previous bar's close, the first bar of a session uses its own range. Stocks use Kite's adjusted prices as a percentage (no corporate-action jumps), applied to the NSE-scaled price.",
    "index_proxy": "Nifty 50 / Nifty Bank spot minutes stand in for the near-month future (basis ignored, labelled). Costs: Zerodha futures fees of that year on one lot of that date (lot size from the F&O bhavcopy, nearest expiry), plus 1 tick of slippage on entry and 1 on exit.",
    "stock_costs": "intraday equity fees of that year; half-spread by turnover rank (costs.HALF_SPREAD_BPS, an estimate) on both legs; slippage of half the half-spread again on the entry and on a stop exit (costs.py convention). Per-unit bps are computed on a Rs 1 lakh order per leg (brokerage at the Rs 20 cap = 0.02%); the sizing layer recomputes on the real order value.",
    "eligibility": "stocks: rank <= 100 in gold/universe on the previous session; kite symbol linked to the universe entity through silver/security_master/kite.parquet; at least 70 of 75 bars with NSE-scaled prices including 09:15; not ETF-like by symbol; no gold/ca_flags row (any status) within 5 sessions either side; a decision bar with high == low (circuit or no trade) cannot confirm. Missing bars inside a valid day are filled flat from the previous close.",
    "index_days": "regular sessions with the 09:15 bar and at least 360 of 375 minutes for both Nifty 50 and Nifty Bank; special (weekend / Muhurat) sessions excluded.",
    "statistics": "metric: net bps of entry price per trade (1 unit). Index NET: t across trade-days of the FILTERED trades. Index VS_BASE: across days on which BASELINE traded, FILTERED day result (0 if no trade) minus BASELINE day result; positive = the confirmation improves on the plain rule. BASE_NET: the plain rule's own trades. Stocks: per-day mean over the day's trades, then t across days; VS_BASE per day over the union of names traded by either version (0 for no trade). Dev 2015-2017, validation 2018-2023; ledger family OC; expected sign + for NET, VS_BASE, BASE_NET.",
    "event_day_test": "scheduled event days = verified (OFFICIAL / TWO_SOURCES) registry events of category rbi_policy, union_budget or election whose first tradable session is the event date. Each falls after 09:45 (RBI and Budget announcements; counting trends run all session), so standing down until 30 minutes after the event means no OC entry under the 10:15 deadline on those days. Test: k30|E1|X1 FILTERED net bps on event days; hypothesis: negative (stand-down beats trading through), expected sign -.",
    "folds": "expanding walk-forward, test years 2016..2023: per test year, the variant's mean net bps (X2 with m refit on earlier years). Robust if at least 5 of 8 folds are positive.",
    "shuffle_stocks": "within each day, the FILTERED set is replaced by a random set of the same size from that day's BASELINE trades (their baseline results); 500 draws; p = share of draws whose mean is at or above the FILTERED mean. Tests selection, not timing.",
    "sizing": "Rs max risk from paper_config.json (intraday.max_risk_per_trade_inr). Index: lots = floor(max_risk / ((stop distance + per-unit cost) x lot size)); 0 lots = NO_TRADE with reason risk_cap. Stocks: shares = floor(max_risk / (stop distance + per-share cost)); notional above 5x the Rs 50,000 book flagged (intraday margin).",
    "wait_counterfactual": "the plain rule's own result on the trades the filters rejected (per trade, dev and validation): negative means waiting saved money, positive means it cost money.",
    "ledger_rows": "74 rows in family OC: for each of 3 instruments x 8 variants, NET (the protocol), VS_BASE (does confirmation improve on the plain rule) and BASE_NET (the plain rule itself), plus the 2 event-day tests. Every row raises the family bar (Bonferroni over all rows ever tried in OC).",
    "exploratory_not_in_this_run": "secondary grid (k5, B 0.55/0.70, rvol 1.2/2.0, VWAP off, tight consolidation, X3-X5, reversal, E4 10:15-11:30) and the synthetic options mapping run next, labelled EXPLORATORY.",
}


def notes() -> dict:
    spec = json.loads(SPEC.read_text())
    assert spec["status"].startswith("APPROVED"), "OC v1 is not approved"
    if NOTES.exists():
        old = json.loads(NOTES.read_text())
        if old.get("spec_sha") == _sha(SPEC) and old.get("interpretations") == INTERPRETATIONS:
            return old
        raise SystemExit("implementation notes already frozen with different content: changes need a new version (oc_v1_implementation_v2)")
    out = {"family": "OC", "spec": SPEC.name, "spec_sha": _sha(SPEC), "spec_version": spec["version"], "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "code": _git(), "max_risk_inr": _max_risk(), "interpretations": INTERPRETATIONS,
           "note": "written before any OC v1 result existed; the run refuses to start if the spec or these notes change"}
    NOTES.write_text(json.dumps(out, indent=1) + "\n")
    return out


# ----------------------------------------------------------------------------------------------------------------------------- helpers
def first_true(m: np.ndarray) -> np.ndarray:
    """Column of the first True per row, -1 if none."""
    any_ = m.any(1)
    return np.where(any_, m.argmax(1), -1)


def ffill_rows(a: np.ndarray) -> np.ndarray:
    """Forward fill NaNs along axis 1 (rows independent)."""
    n, t = a.shape
    idx = np.where(~np.isnan(a), np.arange(t)[None, :], 0)
    np.maximum.accumulate(idx, axis=1, out=idx)
    return a[np.arange(n)[:, None], idx]


def retest_entry(H, L, C, j, d, edge, band, window):
    """E2. Rows are independent instruments/days. j = confirming bar (-1 none), d = +1/-1. Returns entry bar (-1 none) and retest extreme."""
    n, T = H.shape
    entry = np.full(n, -1)
    ext = np.full(n, np.nan)
    failed = np.zeros(n, bool)
    run = np.where(d > 0, np.inf, -np.inf).astype(float)
    rows = np.arange(n)
    act = j >= 0
    up, dn = edge * (1 + band), edge * (1 - band)
    for off in range(1, window + 1):
        t = j + off
        ok = act & ~failed & (entry < 0) & (t + 2 < T)
        if not ok.any():
            break
        tt = np.clip(t, 0, T - 1)
        t1 = np.clip(t + 1, 0, T - 1)
        lo, hi = L[rows, tt], H[rows, tt]
        run = np.where(ok, np.where(d > 0, np.minimum(run, lo), np.maximum(run, hi)), run)
        through = np.where(d > 0, lo < dn, hi > up)
        failed |= ok & through
        ok &= ~through
        touch = np.where(d > 0, lo <= up, hi >= dn)
        conf = np.where(d > 0, (C[rows, t1] > up) & (L[rows, t1] >= dn), (C[rows, t1] < dn) & (H[rows, t1] <= up))
        hit = ok & touch & conf
        ext = np.where(hit, np.where(d > 0, np.minimum(run, L[rows, t1]), np.maximum(run, H[rows, t1])), ext)
        entry = np.where(hit, t + 2, entry)
    return entry, ext, failed


def simulate(O, H, L, e, d, stop, X):
    """Exit from entry bar e (-1 = none) with direction d and stop level; time exit at the open of bar X.
    Returns exit price, exit bar, stopped flag, MAE and MFE (price units, >= 0)."""
    n, T = O.shape
    rows = np.arange(n)
    cols = np.arange(T)[None, :]
    has = (e >= 0) & (e < X)
    ee = np.where(has, e, X)
    live = (cols >= ee[:, None]) & (cols < X) & has[:, None]
    hit = live & np.where(d[:, None] > 0, L <= stop[:, None], H >= stop[:, None])
    th = first_true(hit)
    stopped = th >= 0
    ot = O[rows, np.clip(th, 0, T - 1)]
    fill = np.where(d > 0, np.minimum(ot, stop), np.maximum(ot, stop))
    px = np.where(stopped, fill, O[rows, X])
    tx = np.where(stopped, th, X)
    upto = live & (cols <= np.where(stopped, th, X - 1)[:, None])
    entry = O[rows, np.clip(ee, 0, T - 1)]
    lo = np.where(upto, L, np.inf).min(1)
    hi = np.where(upto, H, -np.inf).max(1)
    mae = np.where(d > 0, entry - np.where(stopped, fill, lo), np.where(stopped, fill, hi) - entry)  # a stopped trade's worst is its fill
    mfe = np.where(d > 0, hi - entry, entry - lo)
    mae = np.where(has, np.maximum(mae, 0), np.nan)
    mfe = np.where(has, np.maximum(mfe, 0), np.nan)
    return np.where(has, px, np.nan), np.where(has, tx, -1), stopped & has, mae, mfe


def atr_at(tr: np.ndarray, prev_tail: np.ndarray, e: np.ndarray) -> np.ndarray:
    """tr: (n, 75) true ranges of today's 5-minute bars; prev_tail: (n, 14) previous session's last 14 (NaN if none); e: entry 5-minute bar
    (bars 0..e-1 have closed). Mean of the 14 most recent."""
    n = tr.shape[0]
    full = np.concatenate([prev_tail, tr], axis=1)  # columns: 14 tail + 75 today
    end = 14 + np.clip(e, 0, NB5)
    out = np.full(n, np.nan)
    for i in range(n):
        if e[i] < 0:
            continue
        w = full[i, max(0, end[i] - 14):end[i]]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = w[-14:].mean()
    return out


def tr5(h, l, c):
    pc = np.concatenate([np.full((h.shape[0], 1), np.nan), c[:, :-1]], axis=1)
    tr = np.fmax(h, pc) - np.fmin(l, pc)
    tr[:, 0] = h[:, 0] - l[:, 0]
    return tr


class Cols:
    """Column-wise collector: each add() takes arrays (or scalars, broadcast) of one length."""

    def __init__(self):
        self.parts: dict[str, list] = {}
        self.n = 0

    def add(self, **kw):
        n = next(len(v) for v in kw.values() if not np.isscalar(v) and not isinstance(v, str))
        for key, v in kw.items():
            self.parts.setdefault(key, []).append(np.full(n, v, dtype=object if isinstance(v, str) else None) if (np.isscalar(v) or isinstance(v, str)) else np.asarray(v))
        self.n += n

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame({key: np.concatenate(v) for key, v in self.parts.items()}) if self.parts else pd.DataFrame()


def leg_fees(kind: str, side: str, value: np.ndarray, years: np.ndarray) -> np.ndarray:
    """Vectorised costs.cost (same formula; checked against it in selftest)."""
    value = np.asarray(value, dtype=float)
    brok = np.minimum(20.0, 0.0003 * value)
    txn = pd.Series(years).map({int(y): costs.txn_rate(kind, int(y)) for y in np.unique(years)}).to_numpy(dtype=float) * value
    sebi = costs.SEBI * value
    gst = costs.GST * (brok + txn + sebi)
    stamp = costs.STAMP[kind] * value if side == "buy" else 0.0
    rate = pd.Series(years).map({int(y): costs.stt_rate(kind, side, int(y)) for y in np.unique(years)}).to_numpy(dtype=float)
    return brok + txn + sebi + gst + stamp + rate * value


def tstat(x) -> tuple[float, float, int]:
    x = pd.Series(x, dtype=float).dropna()
    n = len(x)
    if n < 3:
        return (float("nan"), float("nan"), n)
    sd = x.std(ddof=1)
    return (float(x.mean()), float(x.mean() / (sd / math.sqrt(n))) if sd > 0 else float("nan"), n)


# ----------------------------------------------------------------------------------------------------------------------------- data
def _calendar() -> tuple[list[dt.date], set[dt.date]]:
    D = paths.data_dir()
    cal = pd.read_parquet(D / "silver/calendar/calendar.parquet")
    days = sorted(pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]).dt.date)
    sp = json.loads((D / "manifests/special_sessions.json").read_text())["dates"]
    return [d for d in days if d.year <= 2023], {dt.date.fromisoformat(x) for x in sp}


def _silver(rel: str) -> list[str]:
    """Silver files for 2015-2023 only (sealed/ is a different tree and is never listed here)."""
    D = paths.data_dir()
    out = [str(D / rel / f"year={y}" / "part.parquet") for y in YEARS]
    return [p for p in out if Path(p).exists()]


def load_index() -> dict:
    con = duckdb.connect()
    df = con.execute(f"""select index_name, date, (hour(ts) * 60 + minute(ts) - 555) as m, open, high, low, close
                         from read_parquet({_silver('silver/kite_index/minute')!r})
                         where index_name in ('NIFTY 50', 'NIFTY BANK', 'INDIA VIX')""").df()
    con.close()
    df = df[(df.m >= 0) & (df.m < NMIN)]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    out = {}
    for name, g in df.groupby("index_name"):
        dates = sorted(g["date"].unique())
        di = {d: i for i, d in enumerate(dates)}
        arr = {f: np.full((len(dates), NMIN), np.nan) for f in ("open", "high", "low", "close")}
        r = g["date"].map(di).to_numpy()
        m = g["m"].to_numpy().astype(int)
        for f in arr:
            arr[f][r, m] = g[f].to_numpy()
        cnt = (~np.isnan(arr["close"])).sum(1)
        has0 = ~np.isnan(arr["open"][:, 0])
        pc = ffill_rows(arr["close"])
        for f in ("open", "high", "low"):
            arr[f] = np.where(np.isnan(arr[f]), pc, arr[f])
        arr["close"] = pc
        out[name] = {"dates": dates, "ok": (cnt >= 360) & has0, "count": cnt, **arr}
    return out


def load_lots() -> pd.DataFrame:
    con = duckdb.connect()
    df = con.execute(f"""select date, symbol, expiry, coalesce(lot_size, lot_est) as lot from read_parquet({_silver('silver/fo_bhavcopy')!r})
                         where instrument = 'FUTIDX' and symbol in ('NIFTY', 'BANKNIFTY')""").df()
    con.close()
    df = df.sort_values(["date", "symbol", "expiry"]).groupby(["date", "symbol"]).first().reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["lot_source"] = "fo_bhavcopy"
    # a session whose F&O file NSE does not have (both archive addresses 404, e.g. 2021-03-30): the lot is carried from the neighbouring
    # sessions only when the session before and the session after agree; labelled, counted in the results
    days, _ = _calendar()
    have = set(zip(df["date"], df["symbol"]))
    lot = dict(zip(zip(df["date"], df["symbol"]), df["lot"]))
    add = []
    for i in range(1, len(days) - 1):
        d = days[i]
        if d.year < YEARS[0] or d.year > YEARS[-1]:
            continue
        for sym in ("NIFTY", "BANKNIFTY"):
            if (d, sym) not in have:
                a_, b_ = lot.get((days[i - 1], sym)), lot.get((days[i + 1], sym))
                if a_ is not None and a_ == b_:
                    add.append({"date": d, "symbol": sym, "lot": a_, "lot_source": "carried: F&O file missing at NSE, neighbours agree"})
    if add:
        df = pd.concat([df, pd.DataFrame(add)], ignore_index=True)
    return df[["date", "symbol", "lot", "lot_source"]]


def load_universe(days: list[dt.date]) -> pd.DataFrame:
    """rank on the previous session for each trading day 2015-2023."""
    D = paths.data_dir()
    con = duckdb.connect()
    u = con.execute(f"select date, sid, symbol, rank from read_parquet('{D}/gold/universe/u_liq_in.parquet') where date >= '2014-11-01' and date <= '2023-12-31' and rank <= 100").df()
    con.close()
    u["date"] = pd.to_datetime(u["date"]).dt.date
    prev = {days[i]: days[i - 1] for i in range(1, len(days))}
    nxt = {v: k for k, v in prev.items()}
    u["day"] = u["date"].map(nxt)
    return u.dropna(subset=["day"]).rename(columns={"symbol": "u_symbol"})[["day", "sid", "u_symbol", "rank"]]


def load_ca_block(days: list[dt.date]) -> set[tuple[dt.date, str]]:
    D = paths.data_dir()
    f = pd.read_parquet(D / "gold/ca_flags/ca_flags.parquet")
    f["date"] = pd.to_datetime(f["date"]).dt.date
    pos = {d: i for i, d in enumerate(days)}
    out = set()
    for sid, d in zip(f["sid"], f["date"]):
        i = pos.get(d)
        if i is None:
            # a flag on a non-session date blocks the sessions around it
            i = int(np.searchsorted(np.array(days), d))
        for k in range(max(0, i - 5), min(len(days), i + 6)):
            out.add((days[k], sid))
    return out


def load_link() -> pd.DataFrame:
    D = paths.data_dir()
    k = pd.read_parquet(D / "silver/security_master/kite.parquet", columns=["kite_symbol", "entity"])
    return k.dropna(subset=["entity"]).drop_duplicates()


def load_stock_year(y: int, symbols: list[str]) -> pd.DataFrame:
    D = paths.data_dir()
    p = D / "silver/kite_5m" / f"year={y}" / "part.parquet"
    if not p.exists():
        return pd.DataFrame()
    con = duckdb.connect()
    con.execute("set threads to 6")
    df = con.execute(f"""select symbol, date, (hour(ts) * 60 + minute(ts) - 555) // 5 as j, (hour(ts) * 60 + minute(ts) - 555) % 5 as rem,
                                raw_open as o, raw_high as h, raw_low as l, raw_close as c, coalesce(kite_volume, 0) as v,
                                kite_high as kh, kite_low as kl, kite_close as kc
                         from read_parquet('{p}') where list_contains(?, symbol)""", [symbols]).df()
    con.close()
    df = df[(df.rem == 0) & (df.j >= 0) & (df.j < NB5)].drop(columns="rem")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


# ----------------------------------------------------------------------------------------------------------------------------- stocks
def _cumvol_table(link: pd.DataFrame, syms: list[str], specials: set) -> pd.DataFrame:
    """cumulative volume 09:15..bar j for j = 0..11 on every valid regular stock-day; entity-keyed."""
    D = paths.data_dir()
    con = duckdb.connect()
    con.execute("set threads to 6")
    files = _silver("silver/kite_5m")
    df = con.execute(f"""with b as (select symbol, date, (hour(ts) * 60 + minute(ts) - 555) as mm, raw_close, coalesce(kite_volume, 0) as v
                                    from read_parquet({files!r}) where list_contains(?, symbol)),
                              day as (select symbol, date, count(*) filter (where mm % 5 = 0 and mm >= 0 and mm < 375) as nb,
                                             count(*) filter (where mm = 0) as h0, count(*) filter (where raw_close is null) as nraw, sum(v) as dv
                                      from b group by 1, 2)
                         select b.symbol, b.date, d.dv, {", ".join(f"sum(v) filter (where mm <= {5 * j}) as cv{j}" for j in range(12))}
                         from b join day d using (symbol, date)
                         where d.nb >= 70 and d.h0 = 1 and d.nraw = 0 and b.mm >= 0 and b.mm < 60
                         group by 1, 2, 3""", [syms]).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[~df["date"].isin(specials)]
    df = df.merge(link, left_on="symbol", right_on="kite_symbol").sort_values("dv", ascending=False).drop_duplicates(["entity", "date"])
    return df


def _rvol_baseline(cv: pd.DataFrame, regular: list[dt.date]) -> dict:
    """median of the previous 20 regular sessions (>= 15 with data) per entity and bar j: dict j -> DataFrame (dates x entity)."""
    out = {}
    for j in range(12):
        p = cv.pivot_table(index="date", columns="entity", values=f"cv{j}", aggfunc="first").reindex(regular)
        out[j] = p.rolling(20, min_periods=15).median().shift(1)
    return out


def stock_pass(index: dict, days: list[dt.date], specials: set, m_table: dict | None, log) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """One pass over every stock-day 2015-2023. m_table None: X1 only (pass 1, also breadth); else X2 with the given m values
    {(k, E): {'dev': m, 2016: m, ...}}. Returns trades, breadth, counters."""
    link = load_link()
    regular = [d for d in days if d not in specials and d.year >= 2014]
    uni = load_universe(days)
    etf = uni["u_symbol"].str.contains(ETF_RE)
    log(f"ETF-like symbols left out of the top 100: {sorted(set(uni.loc[etf, 'u_symbol']))}")
    uni = uni[~etf]
    sids = set(uni["sid"])
    lk = link[link["entity"].isin(sids)]
    syms = sorted(lk["kite_symbol"].unique())
    log(f"stocks: {len(sids)} entities ever in the top 100, {len(syms)} kite symbols linked")
    cv = _cumvol_table(lk, syms, specials)
    base = _rvol_baseline(cv, regular)
    cvi = cv.set_index(["date", "entity"])
    ca = load_ca_block(days)
    nifty = index["NIFTY 50"]
    ndi = {d: i for i, d in enumerate(nifty["dates"])}
    rank_by_day = {d: g.set_index("sid")["rank"].to_dict() for d, g in uni.groupby("day")}
    tails: dict[str, np.ndarray] = {}
    col, breadth = Cols(), []
    cnt = {"stock_days_ranked": 0, "no_link_or_data": 0, "ca_block": 0, "no_rvol_base": 0, "eligible": 0, "breadth_days": 0, "breadth_undefined_days": 0}
    for y in YEARS:
        bars = load_stock_year(y, syms)
        if bars.empty:
            continue
        bars = bars.merge(lk, left_on="symbol", right_on="kite_symbol")
        for d, g in bars.groupby("date"):
            if d in specials:
                continue
            ranks = rank_by_day.get(d, {})
            # one kite symbol per entity: the one with most bars that day
            nb = g.groupby(["entity", "symbol"]).size().reset_index(name="n").sort_values("n", ascending=False).drop_duplicates("entity")
            g = g.merge(nb[["entity", "symbol"]], on=["entity", "symbol"])
            ents = sorted(g["entity"].unique())
            ei = {e: i for i, e in enumerate(ents)}
            n = len(ents)
            A = {f: np.full((n, NB5), np.nan) for f in ("o", "h", "l", "c", "v", "kh", "kl", "kc")}
            r = g["entity"].map(ei).to_numpy()
            jj = g["j"].to_numpy().astype(int)
            for f in A:
                A[f][r, jj] = g[f].to_numpy()
            nbar = (~np.isnan(A["kc"])).sum(1)
            rawok = ~(np.isnan(A["c"]) & ~np.isnan(A["kc"])).any(1)
            valid = (nbar >= 70) & ~np.isnan(A["o"][:, 0]) & rawok
            for f in ("c", "kc"):
                A[f] = ffill_rows(A[f])
            for f, src in (("o", "c"), ("h", "c"), ("l", "c"), ("kh", "kc"), ("kl", "kc")):
                A[f] = np.where(np.isnan(A[f]), A[src], A[f])
            A["v"] = np.nan_to_num(A["v"])
            # adjusted true range as a fraction, for the ATR floor; tails carried to tomorrow for every valid name
            trp = tr5(A["kh"], A["kl"], A["kc"]) / A["kc"]
            prev_tail = np.vstack([tails.get(e, np.full(14, np.nan)) for e in ents])
            for i, e in enumerate(ents):
                if valid[i]:
                    tails[e] = trp[i, -14:].copy()
            # eligibility
            rk = np.array([ranks.get(e, 10**9) for e in ents])
            in100 = rk <= 100
            cnt["stock_days_ranked"] += int(sum(1 for e in ranks if ranks[e] <= 100))
            blocked = np.array([(d, e) in ca for e in ents])
            bj = {}
            has_base = np.ones(n, bool)
            for j in range(12):
                bt = base[j]
                row = bt.loc[d] if d in bt.index else None
                bj[j] = np.array([row.get(e, np.nan) if row is not None else np.nan for e in ents])
                has_base &= ~np.isnan(bj[j]) & (bj[j] > 0)
            elig = valid & in100 & ~blocked & has_base
            cnt["no_link_or_data"] += int(sum(1 for e, rr in ranks.items() if rr <= 100) - int((valid & in100).sum()))
            cnt["ca_block"] += int((valid & in100 & blocked).sum())
            cnt["no_rvol_base"] += int((valid & in100 & ~blocked & ~has_base).sum())
            cnt["eligible"] += int(elig.sum())
            # breadth from the eligible top 50
            b50 = elig & (rk <= 50)
            nb50 = int(b50.sum())
            if nb50 >= MIN_BREADTH_NAMES:
                B5 = (A["c"][b50, :12] > A["o"][b50, 0:1]).mean(0)
                cnt["breadth_days"] += 1
            else:
                B5 = np.full(12, np.nan)
                cnt["breadth_undefined_days"] += 1
            if m_table is None:
                breadth.append({"date": d, "names": nb50, **{f"b{j}": float(B5[j]) for j in range(12)}})
            if not elig.any():
                continue
            ix = np.where(elig)[0]
            o, h, l, c, v = (A[f][ix] for f in ("o", "h", "l", "c", "v"))
            cvol = np.cumsum(v, axis=1)
            tp = (h + l + c) / 3
            vw = np.cumsum(tp * v, axis=1) / np.where(cvol > 0, cvol, np.nan)
            rv = np.column_stack([cvol[:, j] / bj[j][ix] for j in range(12)])
            ni = ndi.get(d)
            if ni is None or not nifty["ok"][ni]:
                continue
            nmv = np.array([nifty["close"][ni, 5 * j + 4] / nifty["open"][ni, 0] - 1 for j in range(12)])
            smv = c[:, :12] / o[:, 0:1] - 1
            circuit = h[:, :12] == l[:, :12]
            for k in (15, 30):
                nk = k // 5
                orh, orl = h[:, :nk].max(1), l[:, :nk].min(1)
                cols = slice(nk, DEC_B5 + 1)
                brL = (c[:, cols] > orh[:, None]) & ~circuit[:, cols]
                brS = (c[:, cols] < orl[:, None]) & ~circuit[:, cols]
                Bw = B5[cols][None, :]
                agL = (smv[:, cols] >= AGREE) & (nmv[cols][None, :] >= AGREE)
                agS = (smv[:, cols] <= -AGREE) & (nmv[cols][None, :] <= -AGREE)
                okL = brL & (Bw >= B_LONG) & agL & (rv[:, cols] >= RVOL_MIN) & (c[:, cols] > vw[:, cols])
                okS = brS & (Bw <= B_SHORT) & agS & (rv[:, cols] >= RVOL_MIN) & (c[:, cols] < vw[:, cols])
                for ver, mL, mS in (("BASELINE", brL, brS), ("FILTERED", okL, okS)):
                    jf = first_true(mL | mS)
                    dirn = np.where(jf >= 0, np.where(mL[np.arange(len(ix)), np.clip(jf, 0, None)], 1, -1), 0)
                    jabs = np.where(jf >= 0, jf + nk, -1)
                    edge = np.where(dirn > 0, orh, orl)
                    for E in ("E1", "E2"):
                        if E == "E1":
                            e = np.where(jabs >= 0, jabs + 1, -1)
                            inv = np.where(dirn > 0, orl, orh)
                            failed = np.zeros(len(ix), bool)
                        else:
                            e, ext, failed = retest_entry(h, l, c, jabs, dirn, edge, *RETEST["stock"])
                            inv = ext
                        entry = np.where(e >= 0, o[np.arange(len(ix)), np.clip(e, 0, NB5 - 1)], np.nan)
                        invd = np.where(dirn > 0, entry - inv, inv - entry)
                        if m_table is None:
                            xs = {"X1": invd}
                        else:
                            atrp = atr_at(trp[ix], prev_tail[ix], e)
                            floor = np.fmax(2 * TICK, 0.5 * atrp * entry)
                            width = orh - orl
                            xs = {}
                            for key, mv in m_table.get((k, E), {}).items():
                                xs[f"X2@{key}"] = np.fmin(invd, np.fmax(mv * width, floor))
                        for xname, dist in xs.items():
                            if ver == "BASELINE" and xname not in ("X1", "X2@dev"):
                                continue  # folds are scored on the protocol (FILTERED) version only
                            stop = np.where(dirn > 0, entry - dist, entry + dist)
                            px, tx, stp, mae, mfe = simulate(o, h, l, e, dirn, stop, EXIT_B5)
                            w = np.where(e >= 0)[0]
                            if len(w):
                                col.add(date=[d] * len(w), year=y, entity=np.array(ents, dtype=object)[ix[w]], rank=rk[ix[w]], k=k, E=E, X=xname, version=ver,
                                        dir=dirn[w], conf_bar=jabs[w], entry_bar=e[w], entry=entry[w], stop_dist=dist[w], inv_dist=invd[w],
                                        or_width=(orh - orl)[w], exit=px[w], exit_bar=tx[w], stopped=stp[w], mae=mae[w], mfe=mfe[w])
                        if E == "E2" and m_table is None:
                            cnt[f"e2_failed_{ver}_k{k}"] = cnt.get(f"e2_failed_{ver}_k{k}", 0) + int((failed & (jabs >= 0)).sum())
                    if m_table is None:
                        cnt[f"confirmed_{ver}_k{k}"] = cnt.get(f"confirmed_{ver}_k{k}", 0) + int((jabs >= 0).sum())
        log(f"stocks {y}: {col.n:,} trade rows so far")
    return col.frame(), pd.DataFrame(breadth), cnt


def stock_costs(t: pd.DataFrame, cost_mult: float = 1.0) -> pd.DataFrame:
    t = t.copy()
    hs = t["rank"].map(lambda r: costs.half_spread_bps(int(r))) / 1e4
    ratio = t["exit"] / t["entry"]
    gross = t["dir"] * (ratio - 1)
    notional = 100_000.0
    yrs = t["year"].to_numpy()
    lg = (t["dir"] > 0).to_numpy()
    bv = np.where(lg, notional, notional * ratio)
    sv = np.where(lg, notional * ratio, notional)
    fees = (leg_fees("intraday", "buy", bv, yrs) + leg_fees("intraday", "sell", sv, yrs)) / notional
    spread = hs * (1 + ratio) + 0.5 * hs * (1 + np.where(t["stopped"], ratio, 0))
    t["cost_bps"] = (fees + spread.to_numpy()) * 1e4 * cost_mult
    t["gross_bps"] = gross * 1e4
    t["net_bps"] = t["gross_bps"] - t["cost_bps"]
    t["R"] = (t["net_bps"] / 1e4 * t["entry"]) / t["stop_dist"].where(t["stop_dist"] > 0)
    return t


# ----------------------------------------------------------------------------------------------------------------------------- index
def index_pass(index: dict, breadth: pd.DataFrame, specials: set, lots: pd.DataFrame, m_table: dict | None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    nf, nb = index["NIFTY 50"], index["NIFTY BANK"]
    common = sorted(set(nf["dates"]) & set(nb["dates"]))
    fi = {d: i for i, d in enumerate(nf["dates"])}
    bi = {d: i for i, d in enumerate(nb["dates"])}
    bmap = breadth.set_index("date")
    keep, cnt = [], {"index_days_both": len(common), "special": 0, "incomplete": 0, "breadth_undefined": 0}
    for d in common:
        if d in specials:
            cnt["special"] += 1
        elif not (nf["ok"][fi[d]] and nb["ok"][bi[d]]):
            cnt["incomplete"] += 1
        elif d not in bmap.index or np.isnan(bmap.loc[d, "b0"]):
            cnt["breadth_undefined"] += 1
        else:
            keep.append(d)
    cnt["index_days_used"] = len(keep)
    nd = len(keep)
    # breadth per minute: last closed 5-minute bar j = floor((i+1)/5)-1
    Bm = np.full((nd, NMIN), np.nan)
    bcols = np.array([bmap.loc[d, [f"b{j}" for j in range(12)]].to_numpy(dtype=float) for d in keep])
    for i in range(DEC_MIN + 1):
        j = (i + 1) // 5 - 1
        if 0 <= j < 12:
            Bm[:, i] = bcols[:, j]
    sel = {name: np.array([src_i[d] for d in keep]) for name, src_i in (("NIFTY 50", fi), ("NIFTY BANK", bi))}
    arrs = {name: {f: index[name][f][sel[name]] for f in ("open", "high", "low", "close")} for name in sel}
    # 5-minute true ranges for the ATR floor (points), previous day's tail carried
    tails = {}
    for name in sel:
        a = arrs[name]
        h5 = a["high"].reshape(nd, NB5, 5).max(2)
        l5 = a["low"].reshape(nd, NB5, 5).min(2)
        c5 = a["close"].reshape(nd, NB5, 5)[:, :, -1]
        tr = tr5(h5, l5, c5)
        prev = np.vstack([np.full((1, 14), np.nan), tr[:-1, -14:]])
        tails[name] = (tr, prev)
    lot = lots.set_index(["date", "symbol"])["lot"].to_dict()
    col, states = Cols(), []
    for sym, name in IDX.items():
        other = "NIFTY BANK" if name == "NIFTY 50" else "NIFTY 50"
        O, H, L, C = (arrs[name][f] for f in ("open", "high", "low", "close"))
        mv = C / O[:, 0:1] - 1
        mvo = arrs[other]["close"] / arrs[other]["open"][:, 0:1] - 1
        agL = (mv >= AGREE) & (mvo >= AGREE)
        agS = (mv <= -AGREE) & (mvo <= -AGREE)
        for k in (15, 30):
            orh, orl = H[:, :k].max(1), L[:, :k].min(1)
            cols = slice(k, DEC_MIN + 1)
            brL = C[:, cols] > orh[:, None]
            brS = C[:, cols] < orl[:, None]
            Bw = Bm[:, cols]
            okL = brL & (Bw >= B_LONG) & agL[:, cols]
            okS = brS & (Bw <= B_SHORT) & agS[:, cols]
            if m_table is None:
                anyb = (brL | brS).any(1)
                bOK = ((brL & (Bw >= B_LONG)) | (brS & (Bw <= B_SHORT))).any(1)
                aOK = ((brL & agL[:, cols]) | (brS & agS[:, cols])).any(1)
                jf0 = first_true(okL | okS)
                for i, d in enumerate(keep):
                    if jf0[i] >= 0:
                        st = "CONFIRMED_LONG" if okL[i, jf0[i]] else "CONFIRMED_SHORT"
                        why = ""
                    else:
                        st = "WAIT"
                        why = "no_break" if not anyb[i] else ("breadth" if not bOK[i] and aOK[i] else ("agreement" if bOK[i] and not aOK[i] else ("breadth_and_agreement" if not bOK[i] else "never_together")))
                    states.append((d, sym, k, st, why, (k + jf0[i]) if jf0[i] >= 0 else -1))
            for ver, mL, mS in (("BASELINE", brL, brS), ("FILTERED", okL, okS)):
                jf = first_true(mL | mS)
                dirn = np.where(jf >= 0, np.where(mL[np.arange(nd), np.clip(jf, 0, None)], 1, -1), 0)
                jabs = np.where(jf >= 0, jf + k, -1)
                edge = np.where(dirn > 0, orh, orl)
                for E in ("E1", "E2"):
                    if E == "E1":
                        e = np.where(jabs >= 0, jabs + 1, -1)
                        inv = np.where(dirn > 0, orl, orh)
                    else:
                        e, ext, failed = retest_entry(H, L, C, jabs, dirn, edge, *RETEST["index"])
                        inv = ext
                    entry = np.where(e >= 0, O[np.arange(nd), np.clip(e, 0, NMIN - 1)], np.nan)
                    invd = np.where(dirn > 0, entry - inv, inv - entry)
                    if m_table is None:
                        xs = {"X1": invd}
                    else:
                        tr, prev = tails[name]
                        e5 = np.where(e >= 0, e // 5, -1)
                        atr = atr_at(tr, prev, e5)
                        floor = np.fmax(2 * TICK, 0.5 * atr)
                        xs = {f"X2@{key}": np.fmin(invd, np.fmax(mvv * (orh - orl), floor)) for key, mvv in m_table.get((sym, k, E), {}).items()}
                    for xname, dist in xs.items():
                        if ver == "BASELINE" and xname not in ("X1", "X2@dev"):
                            continue
                        stop = np.where(dirn > 0, entry - dist, entry + dist)
                        px, tx, stp, mae, mfe = simulate(O, H, L, e, dirn, stop, EXIT_MIN)
                        w = np.where(e >= 0)[0]
                        if len(w):
                            dd = [keep[i] for i in w]
                            col.add(date=dd, year=np.array([x.year for x in dd]), instrument=sym, k=k, E=E, X=xname, version=ver, dir=dirn[w], conf_min=jabs[w],
                                    entry_min=e[w], entry=entry[w], stop_dist=dist[w], inv_dist=invd[w], or_width=(orh - orl)[w], exit=px[w], exit_min=tx[w],
                                    stopped=stp[w], mae=mae[w], mfe=mfe[w], lot=np.array([lot.get((x, sym), np.nan) for x in dd]))
                    if m_table is None and E == "E2":
                        cnt[f"e2_failed_{sym}_{ver}_k{k}"] = int((failed & (jabs >= 0)).sum())
                if m_table is None:
                    cnt[f"confirmed_{sym}_{ver}_k{k}"] = int((jabs >= 0).sum())
    st = pd.DataFrame(states, columns=["date", "instrument", "k", "state", "wait_reason", "confirm_min"])
    return col.frame(), st, cnt


def index_costs(t: pd.DataFrame, cost_mult: float = 1.0) -> pd.DataFrame:
    t = t.copy()
    lt = t["lot"].to_numpy(dtype=float)
    if np.isnan(lt).any() or (lt <= 0).any():
        raise ValueError(f"{int(np.isnan(lt).sum())} index trades without a lot size")
    yrs = t["year"].to_numpy()
    lg = (t["dir"] > 0).to_numpy()
    ent, ex = t["entry"].to_numpy(), t["exit"].to_numpy()
    bv = np.where(lg, ent, ex) * lt
    sv = np.where(lg, ex, ent) * lt
    fees = (leg_fees("futures", "buy", bv, yrs) + leg_fees("futures", "sell", sv, yrs)) / lt
    t["cost_pts"] = (fees + 2 * TICK) * cost_mult
    t["gross_pts"] = t["dir"] * (t["exit"] - t["entry"])
    t["net_pts"] = t["gross_pts"] - t["cost_pts"]
    t["gross_bps"] = t["gross_pts"] / t["entry"] * 1e4
    t["cost_bps"] = t["cost_pts"] / t["entry"] * 1e4
    t["net_bps"] = t["net_pts"] / t["entry"] * 1e4
    t["R"] = t["net_pts"] / t["stop_dist"].where(t["stop_dist"] > 0)
    return t


# ----------------------------------------------------------------------------------------------------------------------------- m for X2
def fit_m(t: pd.DataFrame, keys: list[str]) -> dict:
    """80th percentile of MAE / OR width of FILTERED X1 winners; per key in `keys`: dev and each fold's training years."""
    out = {}
    w = t[(t["version"] == "FILTERED") & (t["X"] == "X1") & (t["net_bps"] > 0) & (t["or_width"] > 0)].copy()
    w["mr"] = w["mae"] / w["or_width"]
    for key, g in w.groupby(keys):
        dd = {"dev": float(g.loc[g["year"] <= DEV_LAST, "mr"].quantile(0.8)) if (g["year"] <= DEV_LAST).sum() >= 10 else float("nan")}
        for y in range(2016, 2024):
            gy = g[g["year"] < y]
            dd[y] = float(gy["mr"].quantile(0.8)) if len(gy) >= 10 else float("nan")
        out[key if isinstance(key, tuple) else (key,)] = {kk: vv for kk, vv in dd.items() if vv == vv}
    return out


# ----------------------------------------------------------------------------------------------------------------------------- scoring
def _period(df: pd.DataFrame, col: str = "year") -> pd.Series:
    return np.where(df[col] <= DEV_LAST, "dev", "val")


def x2_select(t: pd.DataFrame) -> pd.DataFrame:
    """X2 rows used for the primary test: m from dev (labelled X2). Fold rows stay as X2@<year> for the walk-forward."""
    x = t[t["X"] == "X2@dev"].copy()
    x["X"] = "X2"
    return x


def day_series(t: pd.DataFrame, unit: str) -> pd.DataFrame:
    """per date: mean net bps over that date's trades (stocks) or the single trade (index)."""
    return t.groupby("date").agg(net=("net_bps", "mean"), n=("net_bps", "size"), year=("year", "first")).reset_index()


def vs_base(tf: pd.DataFrame, tb: pd.DataFrame, key: list[str]) -> pd.DataFrame:
    """per date: mean over the union of keys traded by either version of (FILTERED - BASELINE), 0 when a version did not trade."""
    a = tf.set_index(key)["net_bps"].rename("f")
    b = tb.set_index(key)["net_bps"].rename("b")
    u = pd.concat([a, b], axis=1).fillna(0.0).reset_index()
    u["diff"] = u["f"] - u["b"]
    g = u.groupby("date")["diff"].mean().reset_index()
    g["year"] = pd.to_datetime(g["date"]).dt.year
    return g


def summarize(t: pd.DataFrame) -> dict:
    if t.empty:
        return {"trades": 0}
    w = t[t["net_bps"] > 0]["net_bps"]
    lo = t[t["net_bps"] <= 0]["net_bps"]
    ds = t.groupby("date")["net_bps"].mean().sort_index()
    eq = ds.cumsum()
    yrs = t["year"].nunique()
    return {"trades": int(len(t)), "trades_per_year": round(len(t) / max(yrs, 1), 1), "win_rate": round(float((t["net_bps"] > 0).mean()), 3),
            "avg_win_bps": round(float(w.mean()), 2) if len(w) else None, "avg_loss_bps": round(float(lo.mean()), 2) if len(lo) else None,
            "profit_factor": round(float(w.sum() / -lo.sum()), 3) if len(lo) and lo.sum() < 0 else None,
            "expectancy_bps": round(float(t["net_bps"].mean()), 2), "expectancy_R": round(float(t["R"].mean()), 3),
            "cost_share": round(float(t["cost_bps"].sum() / max(t["gross_bps"].abs().sum(), 1e-9)), 3),
            "stopped_share": round(float(t["stopped"].mean()), 3),
            "max_dd_bps_daily_equity": round(float((eq - eq.cummax()).min()), 1) if len(eq) else None,
            "mae_bps_p50_p80": [round(float(x), 1) for x in (t["mae"] / t["entry"] * 1e4).quantile([0.5, 0.8])],
            "mfe_bps_p50_p80": [round(float(x), 1) for x in (t["mfe"] / t["entry"] * 1e4).quantile([0.5, 0.8])]}


def sizing_index(t: pd.DataFrame, max_risk: float) -> dict:
    if t.empty or max_risk != max_risk:
        return {}
    lots = np.floor(max_risk / ((t["stop_dist"] + t["cost_pts"]) * t["lot"]))
    ok = lots >= 1
    pnl = (lots * t["lot"] * t["net_pts"]).where(ok, 0.0)
    return {"risk_cap_share": round(float((~ok).mean()), 3), "feasible_trades": int(ok.sum()), "rupees_total": round(float(pnl.sum()), 0),
            "rupees_per_feasible_trade": round(float(pnl[ok].mean()), 1) if ok.any() else None,
            "median_one_lot_risk_rs": round(float(((t["stop_dist"] + t["cost_pts"]) * t["lot"]).median()), 0)}


def sizing_stock(t: pd.DataFrame, max_risk: float) -> dict:
    if t.empty or max_risk != max_risk:
        return {}
    per_share_cost = t["cost_bps"] / 1e4 * t["entry"]
    sh = np.floor(max_risk / (t["stop_dist"] + per_share_cost))
    ok = sh >= 1
    pnl = (sh * t["net_bps"] / 1e4 * t["entry"]).where(ok, 0.0)
    notional = sh * t["entry"]
    daily = pnl.groupby(t["date"]).sum()
    return {"risk_cap_share": round(float((~ok).mean()), 3), "rupees_per_trade": round(float(pnl[ok].mean()), 1) if ok.any() else None,
            "rupees_per_day_mean": round(float(daily.mean()), 1), "worst_day_rs": round(float(daily.min()), 0),
            "trades_per_traded_day": round(float(t.groupby("date").size().mean()), 1),
            "notional_over_5x_book_share": round(float((notional > 250_000).mean()), 3), "median_notional_rs": round(float(notional.median()), 0)}


def folds(t: pd.DataFrame, fold_rows: pd.DataFrame | None, unit: str) -> dict:
    """8 expanding folds, test years 2016-2023: mean of the day series in each test year."""
    out = {}
    for y in range(2016, 2024):
        if fold_rows is not None:
            g = fold_rows[(fold_rows["X"] == f"X2@{y}") & (fold_rows["year"] == y)]
        else:
            g = t[t["year"] == y]
        if len(g):
            out[y] = round(float(day_series(g, unit)["net"].mean()), 2)
    pos = sum(1 for v in out.values() if v > 0)
    return {"by_year": out, "positive_folds": pos, "of": len(out), "robust": pos >= 5}


def shuffle_p(tf: pd.DataFrame, tb: pd.DataFrame, period_mask_years, draws: int = 500, seed: int = 7) -> float | None:
    rng = np.random.default_rng(seed)
    obs_days = tf[tf["year"].isin(period_mask_years)].groupby("date")["net_bps"].mean()
    if obs_days.empty:
        return None
    obs = obs_days.mean()
    nf = tf[tf["year"].isin(period_mask_years)].groupby("date").size()
    bb = {d: g["net_bps"].to_numpy() for d, g in tb[tb["year"].isin(period_mask_years)].groupby("date")}
    sims = np.zeros(draws)
    used = 0
    for d, k in nf.items():
        x = bb.get(d)
        if x is None or len(x) < k:
            continue
        idx = np.argsort(rng.random((draws, len(x))), axis=1)[:, :k]
        sims += x[idx].mean(1)
        used += 1
    if not used:
        return None
    sims /= used
    obs_used = obs_days[[d for d in nf.index if d in bb and len(bb[d]) >= nf[d]]].mean()
    return round(float((sims >= obs_used).mean()), 4)


# ----------------------------------------------------------------------------------------------------------------------------- strata
def strata(index: dict, days: list[dt.date]) -> pd.DataFrame:
    D = paths.data_dir()
    nf = index["NIFTY 50"]
    vix = index.get("INDIA VIX")
    rows = []
    vclose = {d: vix["close"][i, -1] for i, d in enumerate(vix["dates"])} if vix else {}
    dl = sorted(nf["dates"])
    dc = {d: nf["close"][i, -1] for i, d in enumerate(nf["dates"])}
    day = pd.read_parquet(D / "silver/kite_index/day/" / next(p.name for p in (D / "silver/kite_index/day").iterdir() if p.suffix == ".parquet"))
    day = day[day["index_name"] == "NIFTY 50"].copy()
    day["date"] = pd.to_datetime(day["date"]).dt.date
    day = day[day["date"] <= dt.date(2023, 12, 31)].sort_values("date")
    day["sma50"] = day["close"].rolling(50).mean()
    above = dict(zip(day["date"], day["close"] > day["sma50"]))
    fc = pd.read_parquet(D / "silver/fo_calendar/" / next(p.name for p in (D / "silver/fo_calendar").iterdir() if p.suffix == ".parquet"))
    fc = fc[(fc["instrument"] == "OPTIDX") & fc["symbol"].isin(["NIFTY", "BANKNIFTY"])]
    fc["expiry"] = pd.to_datetime(fc["expiry"]).dt.date
    expiry = {(s, e) for s, e in zip(fc["symbol"], fc["expiry"]) if e.year <= 2023}
    ev = pd.read_parquet(D / "silver/events/events.parquet")
    ev = ev[ev["status"].isin(["OFFICIAL", "TWO_SOURCES"])]
    evd = set(pd.to_datetime(ev["first_tradable_session"]).dt.date)
    sched = ev[ev["category"].isin(["rbi_policy", "union_budget", "election"]) & (pd.to_datetime(ev["first_tradable_session"]).dt.date == pd.to_datetime(ev["event_date"]).dt.date)]
    sched_d = set(pd.to_datetime(sched["first_tradable_session"]).dt.date)
    pos = {d: i for i, d in enumerate(dl)}
    vt = pd.Series({d: vclose.get(dl[pos[d] - 1]) if pos[d] > 0 else np.nan for d in dl}, dtype=float)
    q = vt.quantile([1 / 3, 2 / 3]).to_list()
    for d in dl:
        i = pos[d]
        pc = dc.get(dl[i - 1]) if i > 0 else np.nan
        g = nf["open"][i, 0] / pc - 1 if pc == pc and pc else np.nan
        prevd = dl[i - 1] if i > 0 else None
        v = vt.get(d)
        rows.append({"date": d, "gap": g, "gap_bucket": None if g != g else ("flat" if abs(g) < 0.0025 else ("small" if abs(g) < 0.0075 else "large")) + ("" if abs(g) < 0.0025 else ("_up" if g > 0 else "_down")),
                     "vix_tercile": None if v != v else ("low" if v <= q[0] else ("mid" if v <= q[1] else "high")),
                     "nifty_above_50d": above.get(prevd), "event_day": d in evd, "scheduled_event_day": d in sched_d,
                     "expiry_NIFTY": ("NIFTY", d) in expiry, "expiry_BANKNIFTY": ("BANKNIFTY", d) in expiry,
                     "era": "2015-2019" if d.year <= 2019 else "2020-2023", "weekday": d.strftime("%a")})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------------------------------------- run
def run(log=print, smoke: bool = False) -> dict:
    """smoke: 2016 only, nothing written to the ledger or gold (outputs to ~/ananta_runs/oc_smoke)."""
    global YEARS
    if smoke:
        YEARS = [2016]
    nt = notes() if not smoke else {"spec_sha": _sha(SPEC)}
    if nt["spec_sha"] != _sha(SPEC):
        raise SystemExit("spec changed since the implementation notes were frozen")
    D = paths.data_dir()
    days, specials = _calendar()
    max_risk = _max_risk()
    log("loading index minutes 2015-2023 (silver)")
    index = load_index()
    lots = load_lots()
    carried = lots[lots["lot_source"] != "fo_bhavcopy"]
    log(f"lot sizes carried from neighbouring sessions (F&O file missing at NSE): {sorted(set(carried['date'].astype(str)))}")
    log("stock pass 1 (breadth, X1)")
    st1, breadth, scnt = stock_pass(index, days, specials, None, log)
    st1 = stock_costs(st1)
    out_dir = (Path.home() / "ananta_runs/oc_smoke") if smoke else D / "gold/studies"
    out_dir.mkdir(parents=True, exist_ok=True)
    breadth.to_parquet(out_dir / "OC1_breadth.parquet")
    log("index pass 1 (states, X1)")
    it1, states, icnt = index_pass(index, breadth, specials, lots, None)
    it1 = index_costs(it1)
    states.to_parquet(out_dir / "OC1_index_days.parquet")
    m_i = fit_m(it1, ["instrument", "k", "E"])
    m_s = fit_m(st1, ["k", "E"])
    log(f"X2 m (index): { {str(k): round(v.get('dev', float('nan')), 3) for k, v in m_i.items()} }")
    log(f"X2 m (stocks): { {str(k): round(v.get('dev', float('nan')), 3) for k, v in m_s.items()} }")
    log("stock pass 2 (X2)")
    st2, _, _ = stock_pass(index, days, specials, {(k, E): m_s[(k, E)] for (k, E) in m_s}, log)
    st2 = stock_costs(st2)
    log("index pass 2 (X2)")
    it2, _, _ = index_pass(index, breadth, specials, lots, m_i)
    it2 = index_costs(it2)
    it = pd.concat([it1, it2], ignore_index=True)
    stt = pd.concat([st1, st2], ignore_index=True)
    it.to_parquet(out_dir / "OC1_index_trades.parquet")
    stt.to_parquet(out_dir / "OC1_stock_trades.parquet")
    sdf = strata(index, days)
    icnt["lot_carried_dates"] = sorted(set(carried["date"].astype(str)))
    res = score(it, stt, states, sdf, m_i, m_s, {**scnt, **icnt}, max_risk, record=False, out_dir=out_dir)  # dry run: any error stops before the ledger
    if smoke:
        return res
    return score(it, stt, states, sdf, m_i, m_s, {**scnt, **icnt}, max_risk, record=True, out_dir=out_dir)


def score(it, stt, states, strata_df, m_i, m_s, counts, max_risk, record: bool, out_dir: Path | None = None) -> dict:
    D = paths.data_dir()
    nt = json.loads(NOTES.read_text()) if NOTES.exists() else {"spec_sha": _sha(SPEC), "frozen_at": "not frozen (smoke)"}
    variants = []
    for inst in ("NIFTY", "BANKNIFTY", "STOCKS"):
        for v in VARIANTS:
            for q in ("net", "vs_base", "base_net"):
                variants.append(f"{inst}|{v}|{q}")
    variants += ["NIFTY|k30|E1|X1|event_stand_down", "BANKNIFTY|k30|E1|X1|event_stand_down"]
    reg = registry.register("OC1", family="OC", title="Opening Decision Protocol V1 (Madhav): primary tests",
                            hypothesis="confirmed opening-range breaks (breadth 60%, index agreement, rvol 1.5x and VWAP for stocks) by 10:15 make money net of costs, "
                                       "and beat the same entries and exits without the filters; standing down on scheduled event days beats trading through",
                            variants=variants, note=f"spec {nt['spec_sha']}, implementation notes frozen {nt['frozen_at']}") if record else None
    results = {}
    lines = []
    ix = pd.concat([it[it["X"] == "X1"], x2_select(it)])
    sx = pd.concat([stt[stt["X"] == "X1"], x2_select(stt)])
    for inst in ("NIFTY", "BANKNIFTY", "STOCKS"):
        T = sx if inst == "STOCKS" else ix[ix["instrument"] == inst]
        F = (stt if inst == "STOCKS" else it[it["instrument"] == inst])
        key = ["date", "entity"] if inst == "STOCKS" else ["date"]
        for v in VARIANTS:
            k, E, X = v.split("|")
            k = int(k[1:])
            sel = (T["k"] == k) & (T["E"] == E) & (T["X"] == X)
            tf, tb = T[sel & (T["version"] == "FILTERED")], T[sel & (T["version"] == "BASELINE")]
            fold_rows = None
            if X == "X2":
                fold_rows = F[(F["k"] == k) & (F["E"] == E) & F["X"].str.startswith("X2@") & (F["X"] != "X2@dev") & (F["version"] == "FILTERED")]
            out = {}
            for q, series in (("net", day_series(tf, inst)), ("base_net", day_series(tb, inst)), ("vs_base", vs_base(tf, tb, key).rename(columns={"diff": "net"}))):
                dev = tstat(series.loc[series["year"] <= DEV_LAST, "net"])
                val = tstat(series.loc[series["year"] > DEV_LAST, "net"])
                extra = {"unit": "net bps per trade (stocks: per-day mean)", "spec": nt["spec_sha"]}
                if q == "net":
                    extra.update({"dev_summary": summarize(tf[tf["year"] <= DEV_LAST]), "val_summary": summarize(tf[tf["year"] > DEV_LAST]),
                                  "folds": folds(tf, fold_rows, inst)})
                    if inst == "STOCKS":
                        extra["sizing_val"] = sizing_stock(tf[tf["year"] > DEV_LAST], max_risk)
                        extra["shuffle_p_dev"] = shuffle_p(tf, tb, range(2015, DEV_LAST + 1))
                        extra["shuffle_p_val"] = shuffle_p(tf, tb, range(DEV_LAST + 1, 2024))
                        for half, lo, hi in (("rank_1_50", 1, 50), ("rank_51_100", 51, 100)):
                            h = tf[(tf["rank"] >= lo) & (tf["rank"] <= hi)]
                            hs = day_series(h, inst)
                            extra[f"liquidity_{half}"] = {"dev": tstat(hs.loc[hs["year"] <= DEV_LAST, "net"]), "val": tstat(hs.loc[hs["year"] > DEV_LAST, "net"])}
                        c2 = stock_costs(tf.drop(columns=["cost_bps", "gross_bps", "net_bps", "R"]), cost_mult=2.0)
                    else:
                        extra["sizing_val"] = sizing_index(tf[tf["year"] > DEV_LAST], max_risk)
                        c2 = index_costs(tf.drop(columns=["cost_pts", "gross_pts", "net_pts", "gross_bps", "cost_bps", "net_bps", "R"]), cost_mult=2.0)
                    c2s = day_series(c2, inst)
                    extra["costs_doubled"] = {"dev": tstat(c2s.loc[c2s["year"] <= DEV_LAST, "net"]), "val": tstat(c2s.loc[c2s["year"] > DEV_LAST, "net"])}
                    if X == "X2":
                        mm = (m_s if inst == "STOCKS" else m_i).get((k, E) if inst == "STOCKS" else (inst, k, E), {})
                        extra["m_dev"] = round(mm.get("dev", float("nan")), 3)
                if q == "vs_base":
                    # WAIT counterfactual: baseline result on the keys the filters rejected
                    a = tf.set_index(key)
                    rej = tb.set_index(key).drop(index=a.index, errors="ignore")
                    extra["rejected_by_filters"] = {"dev": tstat(rej.loc[rej["year"] <= DEV_LAST, "net_bps"]), "val": tstat(rej.loc[rej["year"] > DEV_LAST, "net_bps"])}
                name = f"{inst}|{v}|{q}"
                line = registry.record(reg, name, dev=dev, val=val, extra=extra, expect=1) if record else {"verdict": None, "z": None}
                out[q] = {"dev": dev, "val": val, "verdict": line["verdict"], "z": line["z"], "extra": extra}
            results[f"{inst}|{v}"] = out
    # event-day stand-down
    sd = strata_df.set_index("date")["scheduled_event_day"].to_dict()
    for inst in ("NIFTY", "BANKNIFTY"):
        t = ix[(ix["instrument"] == inst) & (ix["k"] == 30) & (ix["E"] == "E1") & (ix["X"] == "X1") & (ix["version"] == "FILTERED")]
        te = t[t["date"].map(sd).fillna(False).astype(bool)]
        tn = t[~t["date"].map(sd).fillna(False).astype(bool)]
        dev, val = tstat(te.loc[te["year"] <= DEV_LAST, "net_bps"]), tstat(te.loc[te["year"] > DEV_LAST, "net_bps"])
        extra = {"non_event_days": {"dev": tstat(tn.loc[tn["year"] <= DEV_LAST, "net_bps"]), "val": tstat(tn.loc[tn["year"] > DEV_LAST, "net_bps"])},
                 "event_days_in_sample": int(sum(1 for d, x in sd.items() if x and d.year <= 2023))}
        name = f"{inst}|k30|E1|X1|event_stand_down"
        line = registry.record(reg, name, dev=dev, val=val, extra=extra, expect=-1) if record else {"verdict": None, "z": None}
        results[name] = {"event": {"dev": dev, "val": val, "verdict": line["verdict"], "z": line["z"], "extra": extra}}
    # report-only strata on the primary FILTERED and BASELINE trades, 2015-2023 together
    strat = {}
    sdf = strata_df.set_index("date")
    for inst in ("NIFTY", "BANKNIFTY", "STOCKS"):
        T = sx if inst == "STOCKS" else ix[ix["instrument"] == inst]
        for v in ("k15|E1|X1", "k30|E1|X1"):
            k, E, X = v.split("|")
            t = T[(T["k"] == int(k[1:])) & (T["E"] == E) & (T["X"] == X)]
            ds = t.groupby(["version", "date"])["net_bps"].mean().reset_index().join(sdf, on="date")
            ds["expiry"] = ds["expiry_BANKNIFTY"] if inst == "BANKNIFTY" else ds["expiry_NIFTY"]
            s = {}
            for col in ("gap_bucket", "vix_tercile", "nifty_above_50d", "event_day", "expiry", "era", "weekday"):
                g = ds.groupby(["version", col])["net_bps"].agg(["mean", "size"]).round(2).reset_index()
                s[col] = g.to_dict("records")
            strat[f"{inst}|{v}"] = s
    wait = states.groupby(["instrument", "k", "state", "wait_reason"]).size().reset_index(name="days").to_dict("records")
    man = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "spec_sha": nt["spec_sha"], "notes_frozen_at": nt["frozen_at"], "code": _git(),
           "max_risk_inr": max_risk, "counts": counts, "m_index": {"|".join(map(str, k)): v for k, v in m_i.items()},
           "m_stocks": {"|".join(map(str, k)): v for k, v in m_s.items()}, "states": wait, "results": results, "strata": strat,
           "ledger_family_threshold_z": registry.threshold(registry.family_count("OC")) if record else None, "recorded": record}
    if record:
        (D / "manifests/oc_v1_results.json").write_text(json.dumps(man, indent=1, default=str))
        write_report(man)
    elif out_dir is not None:
        (out_dir / "oc_v1_results_dry.json").write_text(json.dumps(man, indent=1, default=str))
    return man


# ----------------------------------------------------------------------------------------------------------------------------- report
def _f(x, nd=1):
    return "–" if x is None or x != x else f"{x:.{nd}f}"


def write_report(man: dict) -> None:
    L = ["# OC v1 results: Opening Decision Protocol V1, primary tests", "",
         f"Spec `oc_v1.json` sha `{man['spec_sha']}`; implementation notes frozen {man['notes_frozen_at']} before any result; code `{man['code']}`; run {man['at']}.",
         "Dev 2015-2017, validation 2018-2023 (silver only; the 2024+ holdout is sealed and was not read).",
         "Unit: net basis points of the entry price per trade after costs (stocks: per-day mean, then across days). "
         f"Ledger family OC; every row below counts; the bar now is z = {man['ledger_family_threshold_z']:.2f}.", "",
         "## Primary tests", "",
         "| Instrument | Variant | Protocol net, dev (t, days) | Protocol net, val (t, days) | Verdict | vs plain rule, val (t) | Verdict | Plain rule net, val (t) | Folds + | m (X2) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in man["results"].items():
        if "net" not in r:
            continue
        inst, v = name.split("|", 1)
        n, vb, bn = r["net"], r["vs_base"], r["base_net"]
        fo = n["extra"].get("folds", {})
        L.append(f"| {inst} | {v} | {_f(n['dev'][0])} ({_f(n['dev'][1], 2)}, {n['dev'][2]}) | {_f(n['val'][0])} ({_f(n['val'][1], 2)}, {n['val'][2]}) | {n['verdict']} | "
                 f"{_f(vb['val'][0])} ({_f(vb['val'][1], 2)}) | {vb['verdict']} | {_f(bn['val'][0])} ({_f(bn['val'][1], 2)}) | {fo.get('positive_folds', '–')}/{fo.get('of', '–')} | "
                 f"{n['extra'].get('m_dev', '')} |")
    L += ["", "## Event days: stand down vs trade through (k30|E1|X1, protocol trades)", "", "| Instrument | Event-day net dev (t, n) | val (t, n) | Non-event val | Verdict |", "|---|---|---|---|---|"]
    for name, r in man["results"].items():
        if "event" in r:
            e = r["event"]
            ne = e["extra"]["non_event_days"]["val"]
            L.append(f"| {name.split('|')[0]} | {_f(e['dev'][0])} ({_f(e['dev'][1], 2)}, {e['dev'][2]}) | {_f(e['val'][0])} ({_f(e['val'][1], 2)}, {e['val'][2]}) | {_f(ne[0])} ({_f(ne[1], 2)}, {ne[2]}) | {e['verdict']} |")
    L += ["", "## What the protocol decided by 10:15 (index days)", "", "| Instrument | k | State | Why waiting | Days |", "|---|---|---|---|---|"]
    for s in man["states"]:
        L.append(f"| {s['instrument']} | {s['k']} | {s['state']} | {s['wait_reason'] or ''} | {s['days']} |")
    L += ["", "## Trade quality and sizing (validation years, protocol trades)", "",
          "| Instrument | Variant | Trades/yr | Win rate | Avg win / loss (bps) | PF | Exp. R | Cost share | Rs 1,000-risk: risk-cap share | Rs per trade | Costs x2 val (t) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in man["results"].items():
        if "net" not in r:
            continue
        inst, v = name.split("|", 1)
        x = r["net"]["extra"]
        s, z, c2 = x.get("val_summary", {}), x.get("sizing_val", {}), x.get("costs_doubled", {}).get("val", [None, None, 0])
        if not s.get("trades"):
            continue
        L.append(f"| {inst} | {v} | {s['trades_per_year']} | {s['win_rate']} | {s['avg_win_bps']} / {s['avg_loss_bps']} | {s['profit_factor']} | {s['expectancy_R']} | {s['cost_share']} | "
                 f"{z.get('risk_cap_share')} | {z.get('rupees_per_feasible_trade', z.get('rupees_per_trade'))} | {_f(c2[0])} ({_f(c2[1], 2)}) |")
    L += ["", "## Data used and left out", "", "```", json.dumps(man["counts"], indent=1), "```", "",
          "Strata (gap, VIX tercile, Nifty vs 50-day, event day, expiry day, era, weekday) are in `manifests/oc_v1_results.json` (report only, never tested)."]
    REPORT.write_text("\n".join(L) + "\n")


def selftest() -> dict:
    """Hand-built paths with known answers for the entry, retest and exit logic, and the vectorised fees against costs.cost."""
    T = 20
    base = np.full((1, T), 100.0)
    O, H, L, C = base.copy(), base + 0.2, base - 0.2, base.copy()
    # long: entry at bar 5 open 101, stop 99.5; bar 8 low 99.4 -> stopped at 99.5; MAE 1.6 (to the low beyond? capped at fill) MFE from highs
    O[0, 5:] = 101; H[0, 5:] = 101.5; L[0, 5:] = 100.8; C[0, 5:] = 101
    L[0, 8] = 99.4
    px, tx, st, mae, mfe = simulate(O, H, L, np.array([5]), np.array([1]), np.array([99.5]), 15)
    assert st[0] and tx[0] == 8 and abs(px[0] - 99.5) < 1e-9, (px, tx, st)
    assert abs(mae[0] - 1.5) < 1e-9 and abs(mfe[0] - 0.5) < 1e-9, (mae, mfe)
    # gap through the stop: bar 9 opens at 99 below a 99.5 stop -> fill at 99
    O2, H2, L2 = O.copy(), H.copy(), L.copy()
    L2[0, 8] = 100.8
    O2[0, 9] = 99.0; L2[0, 9] = 98.9; H2[0, 9] = 99.2
    px, tx, st, _, _ = simulate(O2, H2, L2, np.array([5]), np.array([1]), np.array([99.5]), 15)
    assert st[0] and tx[0] == 9 and abs(px[0] - 99.0) < 1e-9
    # time exit at the open of bar X
    px, tx, st, _, _ = simulate(O2, H2, L2, np.array([5]), np.array([1]), np.array([90.0]), 15)
    assert (not st[0]) and tx[0] == 15 and abs(px[0] - O2[0, 15]) < 1e-9
    # short mirror
    px, tx, st, _, _ = simulate(-O + 200, -L + 200, -H + 200, np.array([5]), np.array([-1]), np.array([100.5]), 15)
    assert st[0] and tx[0] == 8 and abs(px[0] - 100.5) < 1e-9
    # no entry
    px, tx, st, mae, _ = simulate(O, H, L, np.array([-1]), np.array([0]), np.array([np.nan]), 15)
    assert np.isnan(px[0]) and tx[0] == -1 and not st[0]
    # retest: edge 100, band 0.1%: break at bar 3, bar 5 low 100.05 (touch), bar 6 closes 100.3 low 100.02 -> entry bar 7, extreme 100.02
    O, H, L, C = (np.full((1, T), 100.5) for _ in range(4))
    H[:] += 0.2; L[:] -= 0.2
    L[0, 4] = 100.2; L[0, 5] = 100.05; C[0, 5] = 100.1; L[0, 6] = 100.02; C[0, 6] = 100.3
    e, ext, failed = retest_entry(H, L, C, np.array([3]), np.array([1]), np.array([100.0]), 0.001, 30)
    assert e[0] == 7 and abs(ext[0] - 100.02) < 1e-9 and not failed[0], (e, ext, failed)
    # retest that goes through the band first fails
    L[0, 4] = 99.8
    e, ext, failed = retest_entry(H, L, C, np.array([3]), np.array([1]), np.array([100.0]), 0.001, 30)
    assert e[0] == -1 and failed[0]
    # first_true / ffill
    assert list(first_true(np.array([[False, True, True], [False, False, False]]))) == [1, -1]
    f = ffill_rows(np.array([[1.0, np.nan, 3.0, np.nan]]))
    assert list(f[0]) == [1.0, 1.0, 3.0, 3.0]
    # fees: vectorised = costs.cost
    for kind in ("intraday", "futures"):
        for side in ("buy", "sell"):
            for v, y in ((50_000.0, 2016), (2_000_000.0, 2023)):
                a = float(leg_fees(kind, side, np.array([v]), np.array([y]))[0])
                b = costs.cost(kind, side, v, y)
                assert abs(a - b) < 1e-6, (kind, side, v, y, a, b)
    # ATR: 14 most recent closed bars, tail then today
    tr = np.arange(75, dtype=float)[None, :]
    tail = np.full((1, 14), 100.0)
    assert abs(atr_at(tr, tail, np.array([4]))[0] - (10 * 100 + 0 + 1 + 2 + 3) / 14) < 1e-9
    return {"selftest": "PASS"}


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "selftest":
        print(selftest())
    elif cmd == "notes":
        print(json.dumps(notes(), indent=1))
    elif cmd == "run":
        r = run(lambda s: print(f"[{dt.datetime.now():%H:%M:%S}] {s}", flush=True))
        print("done", r["ledger_family_threshold_z"])
    elif cmd == "smoke":
        r = run(lambda s: print(f"[{dt.datetime.now():%H:%M:%S}] {s}", flush=True), smoke=True)
        print("smoke ok", json.dumps(r["counts"], default=str)[:1500])
    elif cmd == "report":
        write_report(json.loads((paths.data_dir() / "manifests/oc_v1_results.json").read_text()))
    else:
        raise SystemExit(__doc__)
