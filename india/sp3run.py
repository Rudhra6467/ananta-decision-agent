"""SP3, the positional playbook: the post-freeze run on dev (2010-2017) and validation (2018-2023), from registrations/sp3_v1.json
(sha 20f9070f3d3a61c9, frozen 20 Oct 2026). india/sp3.py holds the pre-freeze steps (coverage, counts, stops); this file holds stages 2 to 6.
Nothing here reads a row dated after 2023-12-29; the holdout (2024-01-01 to 2026-09-30) is sealed and is opened only by its own registered
run after Madhav's recorded approval (india/sealed.py HOLDOUT_RUNS 'sp3_holdout'). Steps, each writing its evidence file:

  python -m india.sp3run bars       holding bars (data.prices): EQ, BE and BZ cash rows, one per sid-date (highest turnover), adjusted by the
                                    product of the applied corporate-action factors after the row's date; renames followed per the frozen
                                    stop list                             -> gold/studies/SP3_holding_bars.parquet, manifests/sp3_bars.json
  python -m india.sp3run outcomes   stage 2: every candidate x every stock action (26 + random control) with the in_window_events rules
                                                                          -> gold/studies/SP3_outcomes.parquet, manifests/sp3_outcomes.json
  python -m india.sp3run features   stage 3: the situation features at each candidate's signal date (market and stock)
                                                                          -> gold/studies/SP3_features.parquet, manifests/sp3_features.json
  python -m india.sp3run learn      stages 4-6 (india/sp3learn.py): walk-forward models, policy, books, tests, registry rows, results doc

Conventions fixed here, as the spec words them: the window is the 61 sessions of the stock's own bars after the signal (bars T+1..T+61, as
exitlab); the fill at T+1's open plus the half-spread for the liquidity rank at T; exit fills minus the half-spread; fees are not in the
GROSS return (they are added at slot size in stage 4, and at the actual values in the book); a forced end (halt, ca_artifact, permanent
stop, data_end) carries its own reason and, for end_scheme / data_end / relist_no_factor / end_exchange_change, no exit fees.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import costs, paths
from india import sp3 as prep

HERE = Path(__file__).parent
SPEC = prep.SPEC
SPEC_SHA = "20f9070f3d3a61c9"
E_END = prep.E_END                     # 2023-12-29
START = "2005-01-01"
W = 61                                  # bars T+1 .. T+61 (exitlab.HORIZON + 1)
STOP_ATR = 2.0
HALT_DAYS = 10
STOP_GAP = 62
BIG_MOVE = 0.5
BIG_MOVE_WINDOW = 5
RUNS = Path.home() / "ananta_runs" / "sp3"

# stage_2_every_action.stock_exits: 26 actions in the spec's order (ties in score go to the earlier one) + the random-exit control
# kind: hold n | target m (R) | trail k (ATR multiples) | sma n | swing n | scale_half k | hold+low20 n ; stop0: initial stop in ATRs (None = no stop)
ACTIONS = (
    [(f"hold_{d}d", "hold", d, 2.0) for d in (5, 10, 20, 40, 60)]
    + [(f"target_{m}R", "target", m, 2.0) for m in (1, 2, 3)]
    + [(f"atr_trail_{k}", "trail", k, 2.0) for k in (2, 3, 4)]
    + [(f"sma_close_{n}", "sma", n, 2.0) for n in (10, 20, 50)]
    + [(f"swing_low_{n}", "swing", n, 2.0) for n in (5, 10, 20)]
    + [("scale_half_then_trail3", "scale_half", 3, 2.0)]
    + [("hold60_low20", "hold_low20", 60, 2.0)]
    + [("hold_2d", "hold", 2, 2.0), ("hold_3d", "hold", 3, 2.0)]
    + [("hold_20d_nostop", "hold", 20, None), ("hold_60d_nostop", "hold", 60, None)]
    + [("hold_20d_stop3", "hold", 20, 3.0), ("hold_60d_stop3", "hold", 60, 3.0)]
)
ACTION_NAMES = [a[0] for a in ACTIONS]
RANDOM_DRAWS = 5
assert len(ACTIONS) == 25   # the spec's "26 actions" = these 25 choosable actions + the random-exit control (5 draws, never chosen)
NO_EXIT_FEE_REASONS = ("end_scheme", "data_end", "relist_no_factor", "end_exchange_change")


def _git() -> dict:
    run = lambda *a: subprocess.run(["git", *a], cwd=HERE.parent, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "dirty": sorted(run("status", "--porcelain", "india/sp3run.py", "india/sp3learn.py", "india/sp3.py").splitlines())}


def _spec_sha() -> str:
    return hashlib.sha256(SPEC.read_bytes()).hexdigest()[:16]


def _check_spec():
    s = _spec_sha()
    if s != SPEC_SHA:
        raise SystemExit(f"registrations/sp3_v1.json sha {s} is not the frozen {SPEC_SHA}: refusing to run on a changed specification")


def _write(name: str, obj: dict) -> Path:
    p = paths.manifest_dir() / name
    obj = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "spec_sha": _spec_sha(), **_git(), **obj}
    p.write_text(json.dumps(obj, indent=1, default=str))
    return p


def sessions(end: str = E_END) -> pd.DatetimeIndex:
    cal = pd.read_parquet(paths.data_dir() / "silver" / "calendar" / "calendar.parquet")
    s = pd.to_datetime(cal.loc[cal["is_trading_day"], "date"])
    return pd.DatetimeIndex(sorted(d for d in s if d <= pd.Timestamp(end)))


# ================================================================================================================== holding bars (data.prices)
def stops_table() -> pd.DataFrame:
    """The frozen 2005-2023 permanent-stop list with the two approved overrides (in_window_events.relist_without_factor, exchange_change)."""
    s = pd.read_csv(prep.STOPS_CSV, dtype=str).fillna("")
    s["last_session"] = pd.to_datetime(s["last_session"])
    s["check"] = s["treatment"].str.contains("CHECK")
    s["follow"] = (s["class"] == "renamed") & ~s["check"]
    def reason(cls: str, follow: bool, symbols: str) -> str:
        if follow:
            return "followed"
        if cls == "renamed":                      # a CHECK rename: not followed across the relisting (approved 20 Oct 2026)
            return "relist_no_factor"
        if "SPICEJET" in symbols.upper():         # left NSE's permitted-to-trade list, kept trading on BSE (approved 20 Oct 2026)
            return "end_exchange_change"
        if cls in ("scheme", "voluntary_delisting"):
            return "end_scheme"
        return "end_failed"
    s["end_reason"] = [reason(c, f, y) for c, f, y in zip(s["class"], s["follow"], s["symbols"])]
    return s[["sid", "symbols", "last_session", "class", "successor_sid", "check", "follow", "end_reason"]]


def build_bars() -> dict:
    """gold/studies/SP3_holding_bars.parquet: one row per (sid, date) from the EQ, BE and BZ cash rows 2004-2023 (the highest-turnover series),
    o/h/l/c adjusted by cum_factor = the product of the applied factors (silver/corporate_actions/factors.parquet, apply = true) for the row's
    symbol with an ex-date after the row's date; raw_close kept for share counts; the rename successors of the frozen stop list are appended to
    the stopped sid (followed, not a stop). Also ll20 (the lowest low of the 20 bars before the bar) for the hold60_low20 action."""
    t0 = time.time()
    D = paths.data_dir()
    cm = str(D / "silver" / "cm_bhavcopy" / "year=*" / "part.parquet")
    names = D / "silver" / "security_master" / "names.parquet"
    con = duckdb.connect()
    rows = con.execute(f"""
        with cm as (select date, symbol, series, open, high, low, close, turnover, isin from read_parquet('{cm}')
                    where series in ('EQ','BE','BZ') and close > 0 and open > 0 and date >= '2004-01-01' and date <= ?
                    and coalesce(isin, '') not like 'INF%'),
             ent as (select distinct isin, entity from read_parquet('{names}')),
             k as (select c.*, coalesce(e.entity, c.symbol) as sid, row_number() over (partition by coalesce(e.entity, c.symbol), c.date order by c.turnover desc, c.series) as rn
                   from cm c left join ent e on e.isin = c.isin)
        select date, sid, symbol, series, open as o, high as h, low as l, close as c, close as raw_close from k where rn = 1""", [pd.Timestamp(E_END).date()]).df()
    rows["date"] = pd.to_datetime(rows["date"])
    f = pd.read_parquet(D / "silver" / "corporate_actions" / "factors.parquet", columns=["symbol", "ex_date", "factor", "apply"])
    f = f[f["apply"].astype(bool) & f["factor"].notna() & (f["factor"] > 0)].copy()
    f["ex_date"] = pd.to_datetime(f["ex_date"])
    # cum_factor per (symbol, date): product of factors with ex_date > date  == total product / product of factors with ex_date <= date
    rows = rows.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)
    cum = np.ones(len(rows))
    fsym = {s: g.sort_values("ex_date") for s, g in f.groupby("symbol")}
    sym = rows["symbol"].to_numpy()
    bounds = np.r_[0, np.flatnonzero(sym[1:] != sym[:-1]) + 1, len(rows)]
    dd = rows["date"].to_numpy()
    for a, z in zip(bounds[:-1], bounds[1:]):
        g = fsym.get(sym[a])
        if g is None:
            continue
        ex = g["ex_date"].to_numpy()
        logf = np.log(g["factor"].to_numpy())
        suffix = np.cumsum(logf[::-1])[::-1]          # suffix[i] = sum of log factors from i on
        suffix = np.r_[suffix, 0.0]
        k = np.searchsorted(ex, dd[a:z], side="right")  # first factor with ex_date > date
        cum[a:z] = np.exp(suffix[k])
    for col in ("o", "h", "l", "c"):
        rows[col] = rows[col] / cum
    rows["cum_factor"] = cum
    # renames followed: successor bars after L are appended under the stopped sid (one chain step; the successor keeps its own rows too)
    st = stops_table()
    fol = st[st["follow"]]
    extra = []
    by_sid = {s: g for s, g in rows.groupby("sid", sort=False)}
    for r in fol.itertuples():
        g = by_sid.get(r.successor_sid)
        if g is None:
            continue
        e = g[g["date"] > r.last_session].copy()
        e["sid"] = r.sid
        e["followed_from"] = r.successor_sid
        extra.append(e)
    n_follow = sum(len(e) for e in extra)
    rows["followed_from"] = ""
    if extra:
        rows = pd.concat([rows] + extra, ignore_index=True)
    rows = rows.sort_values(["sid", "date"], kind="mergesort").reset_index(drop=True)
    # the lowest low of the 20 bars before each bar (per sid), for hold60_low20
    g = rows.groupby("sid", sort=False)["l"]
    rows["ll20"] = g.shift(1).groupby(rows["sid"], sort=False).rolling(20, min_periods=20).min().reset_index(level=0, drop=True)
    out = paths.gold() / "studies" / "SP3_holding_bars.parquet"
    rows.to_parquet(out, index=False)
    info = {"rows": int(len(rows)), "sids": int(rows["sid"].nunique()), "first": str(rows["date"].min().date()), "last": str(rows["date"].max().date()),
            "series_share": {k: int(v) for k, v in rows["series"].value_counts().items()}, "rows_with_factor": int((cum != 1).sum()),
            "factors_applied": int(len(f)), "renames_followed": int(len(fol)), "follow_rows_appended": int(n_follow),
            "stops": {k: int(v) for k, v in st["end_reason"].value_counts().items()}, "file": str(out), "seconds": round(time.time() - t0, 1)}
    _write("sp3_bars.json", info)
    return info


# ====================================================================================================================== stage 2: outcomes
def load_bars_index() -> dict:
    """sid -> dict(dates ndarray[datetime64[D]], o, h, l, c, raw_close, cum_factor, ll20) from the holding-bars table."""
    b = pd.read_parquet(paths.gold() / "studies" / "SP3_holding_bars.parquet")
    b = b.sort_values(["sid", "date"], kind="mergesort")
    out = {}
    for sid, g in b.groupby("sid", sort=False):
        out[sid] = {"dates": g["date"].to_numpy().astype("datetime64[D]"), "o": g["o"].to_numpy(), "h": g["h"].to_numpy(), "l": g["l"].to_numpy(),
                    "c": g["c"].to_numpy(), "raw_close": g["raw_close"].to_numpy(), "cum": g["cum_factor"].to_numpy(), "ll20": g["ll20"].to_numpy()}
    return out


def ca_events() -> dict:
    """sid -> sorted dates of unconfirmed corporate-action flags (gold/ca_flags, status not FROZEN), the in_window_events.ca_artifact events."""
    ca = pd.read_parquet(paths.gold() / "ca_flags" / "ca_flags.parquet", columns=["sid", "date", "status"])
    ca = ca[(ca["status"] != "FROZEN") & (pd.to_datetime(ca["date"]) <= pd.Timestamp(E_END))]
    return {s: np.sort(pd.to_datetime(g["date"]).to_numpy().astype("datetime64[D]")) for s, g in ca.groupby("sid")}


def split_records() -> dict:
    """symbol -> sorted ex-dates of split, bonus or consolidation records (silver/corporate_actions/factors.parquet, any status): with an
    unconfirmed flag they are what makes a one-day move above 50% a ca_artifact rather than a real move."""
    f = pd.read_parquet(paths.data_dir() / "silver" / "corporate_actions" / "factors.parquet", columns=["symbol", "ex_date", "kind"])
    f = f[f["kind"].str.upper().str.contains("SPLIT|BONUS|CONSOL", regex=True, na=False)]
    f["ex_date"] = pd.to_datetime(f["ex_date"])
    f = f[f["ex_date"] <= pd.Timestamp(E_END)]
    return {s: np.sort(g["ex_date"].to_numpy().astype("datetime64[D]")) for s, g in f.groupby("symbol")}


def _first_true(m: np.ndarray, fill: int) -> np.ndarray:
    """Index of the first True per row, `fill` where none."""
    any_ = m.any(axis=1)
    idx = m.argmax(axis=1)
    return np.where(any_, idx, fill)


def _roll_mean(C: np.ndarray, n: int) -> np.ndarray:
    """mean of C[i+1-n .. i] (NaN where i+1 < n), per row."""
    N, Wn = C.shape
    cs = np.cumsum(np.nan_to_num(C), axis=1)
    out = np.full_like(C, np.nan)
    if Wn >= n:
        out[:, n - 1:] = (cs[:, n - 1:] - np.concatenate([np.zeros((N, 1)), cs[:, :Wn - n]], axis=1)) / n
    return out


def _roll_min_prev(L: np.ndarray, n: int) -> np.ndarray:
    """min of L[i-n .. i-1] (NaN where i < n), per row."""
    out = np.full_like(L, np.nan)
    if L.shape[1] > n:
        Lf = np.where(np.isnan(L), np.inf, L)
        win = np.lib.stride_tricks.sliding_window_view(Lf, n, axis=1)  # win[:, j] covers j .. j+n-1
        out[:, n:] = win[:, :L.shape[1] - n].min(axis=2)
    return out


def action_exits(kind: str, n: float, stop_atr, O, H, L, C, LL20, entry, atr, n_valid, rand_day=None):
    """One action on the window matrices (rows = candidates, columns = bars 0..W-1, NaN past n_valid). Returns (exit_bar, exit_price, reason)
    for exits decided inside the valid bars; exit_bar = W where the action never exits before the forced end. Replicates exitlab._exit: at bar
    i a pending close-decision from bar i-1 fills at o[i] first, then the stop (fill at min(open, stop)), then the target (fill at max(open,
    target)); close decisions are hold (i+1 >= n), sma (c below the mean of the last n window closes), swing (c below the lowest low of the
    previous n bars), low20 (c below the lowest low of the 20 bars before the bar, from the stock's history), random (i+1 >= the draw)."""
    N, Wn = O.shape
    idx = np.arange(Wn)[None, :]
    valid = idx < n_valid[:, None]
    e, a = entry[:, None], atr[:, None]
    risk = STOP_ATR * a
    stop0 = (e - stop_atr * a) if stop_atr is not None else np.full((N, 1), -np.inf)
    # the highest high before bar i (entry at bar 0): used by the trails
    Hn = np.where(valid, H, -np.inf)
    peak_prev = np.maximum(e, np.c_[np.full((N, 1), -np.inf), np.maximum.accumulate(Hn, axis=1)[:, :-1]])
    if kind == "trail":
        stop = np.maximum(stop0, peak_prev - n * a)
    elif kind == "scale_half":
        half = np.maximum.accumulate(np.where(valid, H >= e + risk, False), axis=1)
        half_before = np.c_[np.zeros((N, 1), bool), half[:, :-1]]
        stop = np.where(half_before, np.maximum(np.maximum(stop0, e), peak_prev - n * a), stop0)
    else:
        stop = np.broadcast_to(stop0, (N, Wn))
    s_hit = valid & (L <= stop)
    i_s = _first_true(s_hit, Wn)
    rows = np.arange(N)
    s_px = np.where(i_s < Wn, np.minimum(O[rows, np.minimum(i_s, Wn - 1)], stop[rows, np.minimum(i_s, Wn - 1)]), np.nan)
    i_t, t_px = np.full(N, Wn), np.full(N, np.nan)
    if kind == "target":
        tgt = e + n * risk
        i_t = _first_true(valid & (H >= tgt), Wn)
        t_px = np.where(i_t < Wn, np.maximum(O[rows, np.minimum(i_t, Wn - 1)], tgt[:, 0]), np.nan)
    # close decisions
    if kind == "hold":
        pend = (idx + 1 >= n)
        why = "time"
    elif kind == "sma":
        pend = (idx + 1 >= n) & (C < _roll_mean(C, int(n)))
        why = "sma"
    elif kind == "swing":
        pend = (idx >= n) & (C < _roll_min_prev(L, int(n)))
        why = "swing"
    elif kind == "hold_low20":
        pend = (idx + 1 >= n) | (C < LL20)
        why = "time_or_low20"
    elif kind == "random":
        pend = idx + 1 >= rand_day[:, None]
        why = "random"
    else:
        pend = np.zeros((N, Wn), bool)
        why = ""
    pend = pend & valid
    i_p = _first_true(pend, Wn)
    fill_p = np.where(i_p < Wn, i_p + 1, Wn + 1)                 # fills at the next bar's open (Wn+1 = never inside the window)
    # resolve: earliest effective bar; ties: pending fill, then stop, then target
    best = np.minimum(np.minimum(fill_p, i_s), i_t)
    exit_bar = np.where(best <= Wn, best, Wn)
    reason = np.where(fill_p == best, why, np.where(i_s == best, "stop", "target"))
    px = np.where(fill_p == best, O[rows, np.minimum(fill_p, Wn - 1)], np.where(i_s == best, s_px, t_px))
    inside = exit_bar < n_valid                                     # otherwise the forced end applies
    exit_bar = np.where(inside, exit_bar, Wn)
    px = np.where(inside, px, np.nan)
    reason = np.where(inside, reason, "")
    return exit_bar, px, reason


def build_outcomes(chunk: int = 40000) -> dict:
    """Stage 2 on the frozen candidate table: gold/studies/SP3_candidates.parquet (one row per candidate with its entry, window and forced-end
    facts) and gold/studies/SP3_outcomes.parquet (one row per candidate x action)."""
    _check_spec()
    t0 = time.time()
    cand = pd.read_parquet(paths.gold() / prep.CANDS)
    cand = cand.sort_values(["signal_date", "family", "sid"], kind="mergesort").reset_index(drop=True)
    cand["cand_id"] = np.arange(len(cand), dtype=np.int32)
    feat = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=["sid", "date", "atr14"])
    feat["date"] = pd.to_datetime(feat["date"])
    cand = cand.merge(feat.rename(columns={"date": "signal_date"}), on=["sid", "signal_date"], how="left", validate="many_to_one")
    bars = load_bars_index()
    caf = ca_events()
    spl = split_records()
    stops = stops_table().drop_duplicates("sid").set_index("sid")
    sess = sessions()
    sidx = {d: k for k, d in enumerate(sess)}
    e_idx = sidx[pd.Timestamp(E_END)]
    cand["sess_i"] = cand["signal_date"].map(sidx)
    cand["late"] = cand["sess_i"] > e_idx - STOP_GAP
    cand["hs"] = cand["liq_rank"].map(costs.half_spread_bps).to_numpy() / 1e4
    names = pd.read_parquet(paths.data_dir() / "silver" / "security_master" / "names.parquet", columns=["symbol", "entity"]).drop_duplicates()
    ent_syms = names.groupby("entity")["symbol"].apply(set).to_dict()
    N = len(cand)
    O = np.full((N, W), np.nan); H = O.copy(); L = O.copy(); C = O.copy(); LL = O.copy(); CUM0 = np.full(N, np.nan)
    n_valid = np.zeros(N, int); forced = np.array([""] * N, dtype=object); forced_px = np.full(N, np.nan); forced_bar = np.zeros(N, int)
    entry_date = np.full(N, np.datetime64("NaT"), dtype="datetime64[D]"); exit_dates = {}
    raw_close_T = np.full(N, np.nan); prev_close = np.full(N, np.nan); status = np.array(["OK"] * N, dtype=object)
    counts = {"NO_FILL_no_bars": 0, "NO_FILL_halt_at_entry": 0, "NO_FILL_ca_before_entry": 0, "no_atr": 0}
    ev_counts = {"halt": 0, "ca_artifact": 0, "ca_artifact_bigmove": 0, "end_scheme": 0, "end_failed": 0, "relist_no_factor": 0, "end_exchange_change": 0, "data_end": 0, "end": 0}
    sids = cand["sid"].to_numpy(); sigs = cand["signal_date"].to_numpy().astype("datetime64[D]")
    for k in range(N):
        b = bars.get(sids[k])
        if b is None:
            status[k] = "NO_FILL_no_bars"; counts["NO_FILL_no_bars"] += 1; continue
        d = b["dates"]
        iT = int(np.searchsorted(d, sigs[k], side="left"))
        if iT < len(d) and d[iT] == sigs[k]:
            raw_close_T[k] = b["raw_close"][iT]; prev_close[k] = b["c"][iT]
        i0 = int(np.searchsorted(d, sigs[k], side="right"))
        if i0 >= len(d):
            status[k] = "NO_FILL_no_bars"; counts["NO_FILL_no_bars"] += 1; continue
        if (d[i0] - sigs[k]).astype(int) > HALT_DAYS:
            status[k] = "NO_FILL_halt_at_entry"; counts["NO_FILL_halt_at_entry"] += 1; continue
        j1 = min(len(d), i0 + W)
        n = j1 - i0
        win = slice(i0, j1)
        O[k, :n], H[k, :n], L[k, :n], C[k, :n], LL[k, :n] = b["o"][win], b["h"][win], b["l"][win], b["c"][win], b["ll20"][win]
        CUM0[k] = b["cum"][i0]
        entry_date[k] = d[i0]
        nv, why, px, fb = n, "end", b["c"][j1 - 1], n - 1
        if n < W:   # the stock's bars end inside the window: a permanent stop or the period end
            if sids[k] in stops.index and stops.loc[sids[k], "end_reason"] != "followed" and d[-1] == np.datetime64(stops.loc[sids[k], "last_session"].date()):
                why = stops.loc[sids[k], "end_reason"]
                px = 0.0 if why == "end_failed" else b["c"][j1 - 1]
            else:
                why = "data_end"
        gaps = np.diff(d[win]).astype(int)
        hk = np.flatnonzero(gaps > HALT_DAYS)
        if len(hk) and hk[0] + 1 < nv:
            kk = int(hk[0]) + 1
            nv, why, px, fb = kk, "halt", b["o"][i0 + kk], kk
        ev = caf.get(sids[k])
        if ev is not None:
            inwin = ev[(ev > sigs[k]) & (ev <= d[i0 + nv - 1])]
            if len(inwin):
                m = int(np.searchsorted(d[win][:nv], inwin[0], side="left"))
                if m == 0:
                    status[k] = "NO_FILL_ca_before_entry"; counts["NO_FILL_ca_before_entry"] += 1; continue
                if m < nv:
                    nv, why, px, fb = m, "ca_artifact", b["c"][i0 + m - 1], m - 1
        # a one-day move above 50% is an artefact only with a flag or a split/bonus/consolidation record within 5 sessions of it
        cc = np.r_[prev_close[k] if prev_close[k] == prev_close[k] else b["c"][i0], b["c"][i0:i0 + nv]]
        big = np.flatnonzero(np.abs(cc[1:] / cc[:-1] - 1) > BIG_MOVE)
        if len(big):
            recs = [caf.get(sids[k], np.array([], dtype="datetime64[D]"))] + [spl.get(s, np.array([], dtype="datetime64[D]")) for s in ent_syms.get(sids[k], {sids[k]})]
            recs = np.concatenate(recs) if recs else np.array([], dtype="datetime64[D]")
            for bi in big:
                lo, hi = d[max(0, i0 + bi - BIG_MOVE_WINDOW)], d[min(len(d) - 1, i0 + bi + BIG_MOVE_WINDOW)]
                if len(recs) and ((recs >= lo) & (recs <= hi)).any():
                    if bi == 0:
                        status[k] = "NO_FILL_ca_before_entry"; counts["NO_FILL_ca_before_entry"] += 1; nv = 0; break
                    nv, why, px, fb = int(bi), "ca_artifact_bigmove", b["c"][i0 + bi - 1], int(bi) - 1
                    break
        if nv == 0:
            continue
        n_valid[k], forced[k], forced_px[k], forced_bar[k] = nv, why, px, fb
        ev_counts[why] += 1
    ok = (status == "OK") & cand["atr14"].notna().to_numpy() & (cand["atr14"] > 0).to_numpy()
    counts["no_atr"] = int(((status == "OK") & ~cand["atr14"].notna().to_numpy()).sum())
    status[(status == "OK") & ~ok] = "NO_FILL_no_atr"
    entry = O[:, 0]
    atr = cand["atr14"].to_numpy()
    hs = cand["hs"].to_numpy()
    cand["entry_date"] = pd.to_datetime(entry_date)
    cand["entry_o"] = entry
    cand["raw_entry_o"] = entry * CUM0
    cand["raw_close_T"] = raw_close_T
    cand["n_valid"] = n_valid
    cand["forced_reason"] = forced
    cand["forced_bar"] = forced_bar
    cand["status"] = status
    cand["year"] = cand["signal_date"].dt.year
    # ---- every action on the valid rows, in chunks
    out_parts = []
    rows_ok = np.flatnonzero(ok)
    for a0 in range(0, len(rows_ok), chunk):
        r = rows_ok[a0:a0 + chunk]
        Oc, Hc, Lc, Cc, LLc = O[r], H[r], L[r], C[r], LL[r]
        nv, e, a, h_ = n_valid[r], entry[r], atr[r], hs[r]
        fpx, fb, fwhy = forced_px[r], forced_bar[r], forced[r]
        risk = STOP_ATR * a
        rr = np.arange(len(r))
        acts = [(nm, kind, n, s) for nm, kind, n, s in ACTIONS] + [(f"random_exit_{j}", "random", j, 2.0) for j in range(RANDOM_DRAWS)]
        for nm, kind, n, s in acts:
            rd = None
            if kind == "random":
                u = prep.hash_many(cand["sid"].to_numpy()[r], cand["signal_date"].to_numpy()[r], 1000 + n)
                rd = 1 + np.floor(u * np.maximum(1, np.minimum(W - 1, nv - 1))).astype(int)
            eb, px, why = action_exits(kind, n, s, Oc, Hc, Lc, Cc, LLc, e, a, nv, rd)
            forced_here = eb >= W
            eb = np.where(forced_here, fb, eb)
            px = np.where(forced_here, fpx, px)
            why = np.where(forced_here, fwhy, why)
            ebc = np.minimum(eb, W - 1)
            hh = np.where(np.arange(W)[None, :] <= ebc[:, None], Hc, -np.inf).max(axis=1)
            ll = np.where(np.arange(W)[None, :] <= ebc[:, None], Lc, np.inf).min(axis=1)
            gross = (px * (1 - h_)) / (e * (1 + h_)) - 1
            last_c = Cc[rr, np.maximum(nv - 1, 0)]
            gross_alt = np.where(why == "end_failed", (last_c * (1 - h_)) / (e * (1 + h_)) - 1, gross)            # sensitivity: stops at the last close
            gross_prehalt = np.where(why == "halt", (last_c * (1 - h_)) / (e * (1 + h_)) - 1, gross)             # training label when the resume bar is past the fold
            out_parts.append(pd.DataFrame({"cand_id": cand["cand_id"].to_numpy()[r], "action": nm, "exit_bar": eb.astype(np.int16), "exit_px": px, "reason": why,
                                           "gross": gross, "gross_alt": gross_alt, "gross_prehalt": gross_prehalt, "r_gross": (px - e) / risk,
                                           "mfe_r": (hh - e) / risk, "mae_r": (e - ll) / risk}))
        print(f"  outcomes {a0 + len(r)}/{len(rows_ok)}  {time.time() - t0:.0f}s", flush=True)
    outc = pd.concat(out_parts, ignore_index=True)
    # the exit date of each row (the window bar's date), for fees by date and for the fold rule on halted training labels
    ed = np.full(len(outc), np.datetime64("NaT"), dtype="datetime64[D]")
    cid = outc["cand_id"].to_numpy(); eb = outc["exit_bar"].to_numpy()
    sid_of = cand["sid"].to_numpy(); ent_of = cand["entry_date"].to_numpy().astype("datetime64[D]")
    for s, idxs in pd.Series(np.arange(len(outc))).groupby(sid_of[cid]):
        b = bars[s]; ii = idxs.to_numpy()
        i0 = np.searchsorted(b["dates"], ent_of[cid[ii]], side="left")
        ed[ii] = b["dates"][np.minimum(i0 + eb[ii], len(b["dates"]) - 1)]
    outc["exit_date"] = pd.to_datetime(ed)
    outc["hold"] = (outc["exit_bar"] + 1).astype(np.int16)
    G = paths.gold() / "studies"
    cand.to_parquet(G / "SP3_candidates.parquet", index=False)
    outc.to_parquet(G / "SP3_outcomes.parquet", index=False)
    # the window bars the books mark positions with: opens, closes and each bar's session index (-1 past the valid window)
    WS = np.full((N, W), -1, dtype=np.int32)
    sess_days = sess.to_numpy().astype("datetime64[D]")
    for k in np.flatnonzero(ok):
        b = bars[sids[k]]
        i0 = int(np.searchsorted(b["dates"], sigs[k], side="right"))
        nv = n_valid[k]
        j1 = min(len(b["dates"]), i0 + W)
        WS[k, :j1 - i0] = np.searchsorted(sess_days, b["dates"][i0:j1])
    np.savez_compressed(G / "SP3_windows.npz", O=O.astype(np.float32), C=C.astype(np.float32), S=WS, n_valid=n_valid.astype(np.int16))
    by_fam = cand[ok].groupby("family")["forced_reason"].value_counts().unstack(fill_value=0)
    by_year = cand[ok].groupby("year")["forced_reason"].value_counts().unstack(fill_value=0)
    info = {"candidates": int(N), "with_outcomes": int(ok.sum()), "status": {k: int(v) for k, v in pd.Series(status).value_counts().items()}, "no_fill": counts,
            "in_window_events_per_window": ev_counts, "in_window_events_by_family": {f: {k: int(v) for k, v in r.items()} for f, r in by_fam.iterrows()},
            "in_window_events_by_year": {int(y): {k: int(v) for k, v in r.items()} for y, r in by_year.iterrows()},
            "late_rows_within_62_sessions_of_E": int(cand["late"].sum()), "actions": ACTION_NAMES + [f"random_exit_{j}" for j in range(RANDOM_DRAWS)],
            "outcome_rows": int(len(outc)), "reasons": {k: int(v) for k, v in outc["reason"].value_counts().items()},
            "gross_mean_by_action": {k: round(float(v), 5) for k, v in outc.groupby("action")["gross"].mean().items()},
            "files": [str(G / "SP3_candidates.parquet"), str(G / "SP3_outcomes.parquet")], "seconds": round(time.time() - t0, 1)}
    _write("sp3_outcomes.json", info)
    return info


# ====================================================================================================================== stage 3: features
# Categorical features carry their levels as strings ('missing' included); the continuous ones (breadth, vix, nifty_ret20, fii_share, ret_20)
# are stored raw and cut into terciles on each fold's training rows by sp3learn (stage_3_situation.levels).
MARKET_CAT = ["nifty_trend", "vix_vs50", "small_vs_large", "qqq_vs200", "qqq_move", "sched_5"]
MARKET_NUM = ["breadth", "vix", "nifty_ret20", "fii_share"]
STOCK_CAT = ["dist50_b", "rsi_b", "vol_heat", "deliv_high", "rv20_top", "liq_b", "fo_member", "band5", "results_meeting_10"]
STOCK_NUM = ["ret_20"]
GROUPS = {"market_trend": ["nifty_trend", "nifty_ret20"], "breadth": ["breadth"], "vix": ["vix", "vix_vs50"], "size": ["small_vs_large", "liq_b"],
          "us": ["qqq_vs200", "qqq_move"], "fii": ["fii_share"], "scheduled_events": ["sched_5"], "stock_technical": ["dist50_b", "rsi_b", "ret_20", "rv20_top"],
          "stock_flow": ["vol_heat", "deliv_high", "fo_member"], "stock_events": ["band5", "results_meeting_10"]}


def _vs(s: pd.Series, n: int) -> pd.Series:
    return s / s.rolling(n, min_periods=n).mean() - 1


def market_table(sess: pd.DatetimeIndex) -> pd.DataFrame:
    """One row per session: the market situation known at T's close (stage_3_situation.market), silver only, to 2023-12-29."""
    D = paths.data_dir()
    ix = pd.read_parquet(D / "silver" / "kite_index" / "day" / "day.parquet", columns=["index_name", "date", "close"])
    ix["date"] = pd.to_datetime(ix["date"])
    piv = ix[ix["date"] <= pd.Timestamp(E_END)].pivot_table(index="date", columns="index_name", values="close", aggfunc="last").sort_index()
    out = pd.DataFrame(index=sess)
    n50 = piv["NIFTY 50"]
    a50, a200 = _vs(n50, 50), _vs(n50, 200)
    trend = pd.Series(np.where(a50.isna() | a200.isna(), "missing", np.where((a50 > 0) & (a200 > 0), "above_both", np.where((a50 < 0) & (a200 < 0), "below_both", "mixed"))), index=piv.index)
    out["nifty_trend"] = trend.reindex(sess).fillna("missing")
    out["nifty_ret20"] = (n50 / n50.shift(20) - 1).reindex(sess)
    vix = piv["INDIA VIX"] if "INDIA VIX" in piv else pd.Series(np.nan, index=piv.index)
    out["vix"] = vix.reindex(sess)
    v50 = _vs(vix, 50).reindex(sess)
    out["vix_vs50"] = np.where(v50.isna(), "missing", np.where(v50 > 0, "above", "below"))
    ratio = (piv["NIFTY SMLCAP 100"] / piv["NIFTY 100"])
    r50 = _vs(ratio, 50).reindex(sess)
    out["small_vs_large"] = np.where(r50.isna(), "missing", np.where(r50 > 0, "above", "below"))
    # breadth: the share of the liquid 250 above the 200-day average on T
    f = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=["date", "liq_rank", "dist_sma200"])
    f["date"] = pd.to_datetime(f["date"])
    f = f[(f["liq_rank"] <= 250) & (f["date"] <= pd.Timestamp(E_END))]
    br = f.groupby("date")["dist_sma200"].apply(lambda x: float((x > 0).mean()))
    out["breadth"] = br.reindex(sess)
    # QQQ: the last US close dated on or before T (the US session of date T is on Tiingo before T+1 opens)
    us = pd.read_parquet(D / "silver" / "us" / "us_close.parquet")
    q = us[us["symbol"] == "QQQ"].copy()
    q["date"] = pd.to_datetime(q["date"])
    q = q[q["date"] <= pd.Timestamp(E_END)].set_index("date").sort_index()
    q["vs200"] = _vs(q["adj_close"], 200)
    j = pd.merge_asof(pd.DataFrame({"date": sess}), q[["vs200", "ret"]].reset_index(), on="date", direction="backward").set_index("date")
    out["qqq_vs200"] = np.where(j["vs200"].isna(), "missing", np.where(j["vs200"] > 0, "above", "below"))
    out["qqq_move"] = np.where(j["ret"].isna(), "missing", np.where(j["ret"] > 0.01, "up1", np.where(j["ret"] < -0.01, "down1", "flat")))
    # FII index-futures long share (2012+)
    po = pd.read_parquet(D / "silver" / "flows" / "participant_oi.parquet", columns=["date", "client_type", "future_index_long", "future_index_short"])
    po = po[po["client_type"] == "FII"].copy()
    po["date"] = pd.to_datetime(po["date"])
    po = po[po["date"] <= pd.Timestamp(E_END)].set_index("date")
    out["fii_share"] = (po["future_index_long"] / (po["future_index_long"] + po["future_index_short"])).reindex(sess)
    # a scheduled RBI / Budget / election-count day within the next 5 sessions (known before)
    from india import scenario
    sched = {pd.Timestamp(d) for d in scenario.scheduled_dates()}
    pos = {d: k for k, d in enumerate(sess)}
    flags = np.zeros(len(sess), bool)
    for d in sched:
        k = pos.get(d)
        if k is None:
            k = int(sess.searchsorted(d))
        for j in range(max(0, k - 5), k):
            flags[j] = True
    out["sched_5"] = np.where(flags, "yes", "no")
    out.index.name = "date"
    return out.reset_index()


def rsi14_table() -> pd.DataFrame:
    """rsi14 per (sid, date) from the lab's adjusted EQ bars (Wilder, alpha 1/14, as india.sp3.indicators and the paper engine)."""
    b = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["sid", "date", "c"])
    b["date"] = pd.to_datetime(b["date"])
    b = b[b["date"] <= pd.Timestamp(E_END)].sort_values(["sid", "date"], kind="mergesort").reset_index(drop=True)
    d = b.groupby("sid", sort=False)["c"].diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    au = up.groupby(b["sid"], sort=False).transform(lambda x: x.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    ad = dn.groupby(b["sid"], sort=False).transform(lambda x: x.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    b["rsi14"] = 100 - 100 / (1 + au / ad.replace(0, np.nan))
    return b[["sid", "date", "rsi14"]]


def build_features() -> dict:
    _check_spec()
    t0 = time.time()
    D, G = paths.data_dir(), paths.gold()
    cand = pd.read_parquet(G / "studies" / "SP3_candidates.parquet")
    sess = sessions()
    mk = market_table(sess)
    fc = ["sid", "date", "symbol", "liq_rank", "dist_sma50", "ret_20", "vol_ratio20", "deliv_pct", "rv20"]
    feat = pd.read_parquet(G / "features" / "daily.parquet", columns=fc)
    feat["date"] = pd.to_datetime(feat["date"])
    feat = feat[(feat["date"] >= pd.Timestamp(START)) & (feat["date"] <= pd.Timestamp(E_END))]
    liq = feat[feat["liq_rank"] <= 250].copy()
    liq["rv20_rank"] = liq.groupby("date")["rv20"].rank(pct=True)
    x = cand[["cand_id", "sid", "signal_date", "liq_rank"]].merge(liq.drop(columns=["liq_rank"]).rename(columns={"date": "signal_date"}), on=["sid", "signal_date"], how="left")
    x = x.merge(rsi14_table().rename(columns={"date": "signal_date"}), on=["sid", "signal_date"], how="left")
    x["dist50_b"] = np.where(x["dist_sma50"].isna(), "missing", np.where(x["dist_sma50"] < 0, "under0", np.where(x["dist_sma50"] > 0.2, "over20", "0to20")))
    x["rsi_b"] = np.where(x["rsi14"].isna(), "missing", np.where(x["rsi14"] < 30, "under30", np.where(x["rsi14"] > 70, "over70", "30to70")))
    x["vol_heat"] = np.where(x["vol_ratio20"].isna(), "missing", np.where(x["vol_ratio20"] > 1.5, "hot", "normal"))
    x["deliv_high"] = np.where(x["deliv_pct"].isna(), "missing", np.where(x["deliv_pct"] > 60, "high", "low"))
    x["rv20_top"] = np.where(x["rv20_rank"].isna(), "missing", np.where(x["rv20_rank"] > 0.8, "top", "rest"))
    x["liq_b"] = np.where(x["liq_rank"] <= 50, "1to50", np.where(x["liq_rank"] <= 150, "51to150", "151to250"))
    # F&O membership: a FUTSTK row for the symbol on T
    con = duckdb.connect()
    fo = con.execute(f"select distinct date, symbol from read_parquet('{D / 'silver' / 'fo_bhavcopy' / 'year=*' / 'part.parquet'}') where instrument = 'FUTSTK' and date <= ?",
                     [pd.Timestamp(E_END).date()]).df()
    fo["date"] = pd.to_datetime(fo["date"])
    fo["fo_member"] = "yes"
    x = x.merge(fo.rename(columns={"date": "signal_date"}), on=["symbol", "signal_date"], how="left")
    x["fo_member"] = x["fo_member"].fillna("no")
    # lower band hit in the last 5 sessions (PR zips, 2010+): 'missing' before the source starts
    rb = prep.raw_base(E_END)
    rb["date"] = pd.to_datetime(rb["date"])
    bh = pd.read_parquet(D / "silver" / "pr" / "band_hits.parquet", columns=["date", "symbol", "series", "side"])
    bh["date"] = pd.to_datetime(bh["date"])
    bh = bh[(bh["series"] == "EQ") & bh["side"].str.upper().str.startswith("L") & (bh["date"] <= pd.Timestamp(E_END))]
    band = bh.merge(rb[["date", "symbol", "sid"]].drop_duplicates(), on=["date", "symbol"], how="inner")[["sid", "date"]].drop_duplicates()
    band_start = band["date"].min()
    pos = {d: k for k, d in enumerate(sess)}
    bset = set(zip(band["sid"], band["date"].map(pos)))
    si = x["signal_date"].map(pos).to_numpy()
    hit = np.array([any((s, k - j) in bset for j in range(5)) for s, k in zip(x["sid"], si)])
    x["band5"] = np.where(x["signal_date"] < band_start, "missing", np.where(hit, "yes", "no"))
    # a results board meeting intimated by T for the next 10 sessions (PR zips, 2010+)
    bm = pd.read_parquet(D / "silver" / "pr" / "board_meetings.parquet", columns=["date", "symbol", "meeting_date", "category"])
    bm = bm[bm["category"] == "results"].copy()
    bm["date"], bm["meeting_date"] = pd.to_datetime(bm["date"]), pd.to_datetime(bm["meeting_date"])
    bm = bm[(bm["date"] <= pd.Timestamp(E_END)) & bm["meeting_date"].notna()]
    bm_start = bm["date"].min()
    bm["mi"] = bm["meeting_date"].map(lambda d: int(sess.searchsorted(d)))      # the session index of the meeting (or the next session)
    bm["ii"] = bm["date"].map(lambda d: int(sess.searchsorted(d)))
    by_sym = {s: g[["ii", "mi"]].to_numpy() for s, g in bm.groupby("symbol")}
    def meeting_ahead(sym, k):
        g = by_sym.get(sym)
        if g is None or k != k:
            return False
        return bool(((g[:, 0] <= k) & (g[:, 1] > k) & (g[:, 1] <= k + 10)).any())
    rm = np.array([meeting_ahead(s, k) for s, k in zip(x["symbol"], si)])
    x["results_meeting_10"] = np.where(x["signal_date"] < bm_start, "missing", np.where(rm, "yes", "no"))
    x = x.merge(mk.rename(columns={"date": "signal_date"}), on="signal_date", how="left")
    for c in MARKET_CAT:
        x[c] = x[c].fillna("missing")
    cols = ["cand_id", "sid", "signal_date"] + MARKET_CAT + MARKET_NUM + STOCK_CAT + STOCK_NUM
    x = x[cols].sort_values("cand_id").reset_index(drop=True)
    x.to_parquet(G / "studies" / "SP3_features.parquet", index=False)
    mk.to_parquet(G / "studies" / "SP3_market.parquet", index=False)
    levels = {c: {k: int(v) for k, v in x[c].value_counts().items()} for c in MARKET_CAT + STOCK_CAT}
    miss = {c: int(x[c].isna().sum()) for c in MARKET_NUM + STOCK_NUM}
    info = {"rows": int(len(x)), "levels": levels, "numeric_missing": miss, "band_source_start": str(band_start.date()), "board_meetings_start": str(bm_start.date()),
            "groups": GROUPS, "files": [str(G / "studies" / "SP3_features.parquet"), str(G / "studies" / "SP3_market.parquet")], "seconds": round(time.time() - t0, 1)}
    _write("sp3_features.json", info)
    return info


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    if a[:1] == ["bars"]:
        print(json.dumps(build_bars(), indent=1, default=str))
    elif a[:1] == ["outcomes"]:
        o = build_outcomes()
        print(json.dumps({k: o[k] for k in ("candidates", "with_outcomes", "status", "in_window_events_per_window", "outcome_rows", "reasons", "seconds")}, indent=1, default=str))
    elif a[:1] == ["features"]:
        o = build_features()
        print(json.dumps({k: o[k] for k in ("rows", "levels", "numeric_missing", "seconds")}, indent=1, default=str))
    else:
        print(__doc__)
