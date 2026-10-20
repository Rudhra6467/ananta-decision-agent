"""SP3, the positional playbook (registrations/sp3_v1.json). This file holds the PRE-FREEZE steps only; nothing here reads an outcome.

  python -m india.sp3 prep coverage     the coverage rule (presence only, from the download manifests; no data file is read)
                                        -> manifests/sp3_prep_coverage.json
  python -m india.sp3 prep counts       stage-1 candidate counts on the families that survive coverage (family x year, no outcomes)
                                        -> manifests/sp3_prep_counts.json and gold/studies/SP3_candidates_prep.parquet (data, never committed)
  python -m india.sp3 prep stops        the 2005-2023 permanent-stop list and the mechanical rule's agreement
                                        -> registrations/sp3_permanent_stops.csv and manifests/sp3_prep_stops.json

Reads (prep counts / stops): gold/features/daily.parquet, gold/bars/adj_daily.parquet, gold/universe/u_liq_in.parquet (through the features
table's liq_rank), gold/ca_flags, silver/cm_bhavcopy, silver/security_master (isin -> entity only), silver/corporate_actions, silver/pr,
silver/announce and silver/calendar, every one cut at 2023-12-29. No forward return, exit, P&L or price move after a signal is computed: a
candidate rule on session T sees bars dated T and earlier only, and the stop step looks only at whether bars exist and at corporate records.
The study itself (stages 2-6) is written after the freeze and cross-checked by india/checks/sp3_crosscheck.py before any result is read.
Leak check: this file may call only sealed.coverage / sealed.coverage_summary (india/leakcheck.py).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths, sealed

HERE = Path(__file__).parent
SPEC = HERE / "registrations" / "sp3_v1.json"
H0, H1 = "2024-01-01", "2026-09-30"

# every source an SP3 family or feature depends on, with the manifest that records its downloads (stage_1 / stage_3 / in_window_events)
SOURCES = [
    {"source": "cash market prices (all families, holding bars)", "manifest": "cm_bhavcopy", "used_by": ["ALL"]},
    {"source": "delivery share", "manifest": "delivery", "used_by": ["feature:delivery_share"]},
    {"source": "participant OI (FII index-futures long share)", "manifest": "flows_participant_oi", "used_by": ["feature:fii_long_share"]},
    {"source": "F&O bhavcopy (F&O membership, index futures)", "manifest": "fo_bhavcopy", "used_by": ["feature:fo_member", "INDEX"]},
    {"source": "PR zips (price-band hits, board meetings, dividend records)", "manifest": "pr_zip", "used_by": ["BAND", "GAPD", "feature:band_hit_5", "feature:results_meeting_10"]},
    {"source": "corporate actions (adjustment factors, scheme records)", "manifest": "corporate_actions", "used_by": ["ALL"]},
    {"source": "announcements (holdout permanent-stop records)", "manifest": "announce_api", "used_by": ["in_window_events.holdout_permanent_stops"]},
    {"source": "Nasdaq (QQQ) close", "manifest": "us_close", "match": {"symbol": "QQQ"}, "used_by": ["feature:qqq"]},
] + [{"source": f"index {n} (day)", "manifest": "kite_index", "match": {"symbol": n, "interval": "day"}, "used_by": u} for n, u in (
    ("NIFTY 50", ["feature:nifty_trend", "feature:nifty_ret20", "INDEX"]), ("NIFTY BANK", ["INDEX"]), ("INDIA VIX", ["feature:vix"]),
    ("NIFTY SMLCAP 100", ["feature:small_vs_large"]), ("NIFTY 100", ["feature:small_vs_large"]))]

# results filings: the exchange replaced the old results index with integrated filings in April 2025 (old index: about 14k quarterly filings a
# year to 2024, 14 in Apr 2025, near zero after; integrated API: none before Apr 2025). The rule needs one meaning of 'broadcast time' across the
# holdout, checked on 200 filings present in BOTH sources in 2018-2023 (coverage_rule); there are none, so the check cannot pass.
RESULTS = {"source": "results filings (broadcast times)", "manifests": ["results_index", "results_index_integrated_v2"],
           "used_by": ["RESU", "RESD", "feature:results_filed_5"], "switch": "2025-04-01"}


def coverage() -> dict:
    rows = []
    for s in SOURCES:
        r = sealed.coverage_summary(s["manifest"], H0, H1, s.get("match"))
        rows.append({**s, **r})
    # results: presence of a status-200 window is not enough when a source was retired, so each era counts only its own source
    old = set(sealed.coverage("results_index", H0, "2025-03-31"))
    new = set(sealed.coverage("results_index_integrated_v2", RESULTS["switch"], H1))
    allsess = sealed.coverage_summary("cm_bhavcopy", H0, H1)["sessions"]
    share = len(old | new) / allsess if allsess else 0.0
    rows.append({**RESULTS, "share_present": round(share, 4), "comparison_200": {
        "rule": "lowest 200 of hash(filing_id, 19) among 2018-2023 filings present in both sources; pass if at least 190 match to the minute",
        "result": "NOT POSSIBLE: the integrated API has no filing before 2025-04, so no 2018-2023 filing is in both sources", "pass": False},
        "verdict": "FAIL", "why": "the source changes inside the holdout (2025-04) and the broadcast-time meaning cannot be checked across the change"})
    struck_fam = sorted({u for r in rows if r["verdict"] == "FAIL" for u in r["used_by"] if not u.startswith(("feature:", "ALL", "INDEX", "in_window"))})
    struck_feat = sorted({u.split(":", 1)[1] for r in rows if r["verdict"] == "FAIL" for u in r["used_by"] if u.startswith("feature:")})
    fatal = [r["source"] for r in rows if r["verdict"] == "FAIL" and any(u in ("ALL", "INDEX") or u.startswith("in_window") for u in r["used_by"])]
    out = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "window": [H0, H1], "rule": "PASS at >= 99% of sessions present and no gap over 5 sessions; presence from the download manifests only",
           "sources": rows, "struck_families": struck_fam, "struck_features": struck_feat, "fatal": fatal}
    (paths.manifest_dir() / "sp3_prep_coverage.json").write_text(json.dumps(out, indent=1, default=str))
    return out


# =============================================================================================================== prep counts (stage 1)
# Every rule below reads the bar of session T and earlier bars only. The spec's words decide ties: "at least" includes the threshold, "more
# than", "under", "above" exclude it; EPS (1e-9 on a ratio) keeps a float rounding of an exact tie from flipping the side the words give it.
E_END = "2023-12-29"                  # E for dev and validation (in_window_events.boundary)
C_START = "2005-01-01"                # training starts in 2005 (data.periods); the counts run 2005-2023 (pre_freeze.candidate_counts)
FAMILY_START = {"BAND": "2010-01-01", "GAPD": "2010-01-01"}   # PR-zip sources begin in 2010 (stage_1 BAND and GAPD)
REAL = ("BRK", "PULL", "REV", "DECL", "BAND", "HI52", "LO52", "SQZ", "BBMR", "GAPU", "GAPD", "RESU", "RESD", "RETEST", "MOM")
NEEDS_RESULTS = ("RESU", "RESD")      # results-filing families: coded only if the coverage rule lets them in (it struck both on 20 Oct)
PRIORITY = ("RETEST", "BRK", "HI52", "SQZ", "MOM", "GAPU", "RESU", "PULL", "BBMR", "REV", "RESD", "GAPD", "BAND", "DECL", "LO52", "ANY")
SPACING_DAYS = 14
ANY_SALT, CTL_SALT = 11, 13
ROW_BUDGET, ANY_CAP_STEPS, STEPS_PER_UNIT = 400_000, 6, 200   # 3% = 6 steps of 0.5%; a step is 1/200
EPS = 1e-9
CA_WINDOW = 200                       # sessions of the stock's own bars, T included (universe.stocks)
CANDS = "studies/SP3_candidates_prep.parquet"


def hash_u(sid: str, date, s: int) -> float:
    """hash(sid, date, s): the first 8 hex digits of sha256('sid|YYYY-MM-DD|s') read as an integer, divided by 16^8 (stage_1 ANY)."""
    d = date if isinstance(date, str) else pd.Timestamp(date).strftime("%Y-%m-%d")
    return int(hashlib.sha256(f"{sid}|{d}|{s}".encode()).hexdigest()[:8], 16) / 16 ** 8


def hash_many(sids, dates, s: int) -> np.ndarray:
    ds = pd.DatetimeIndex(pd.to_datetime(pd.Series(dates).to_numpy())).strftime("%Y-%m-%d")
    return np.fromiter((int(hashlib.sha256(f"{a}|{d}|{s}".encode()).hexdigest()[:8], 16) for a, d in zip(sids, ds)), dtype=np.float64, count=len(ds)) / 16 ** 8


def any_rate(non_any_rows: int, any_eligible: int) -> tuple[float, float]:
    """stage_1 size_check: min(3%, (400,000 - non-ANY rows) / ANY-eligible rows), rounded down to 0.5%, at least 0.5%. Integer steps, so an
    exact multiple of 0.5% is not lost to float rounding. Returns (rate, unrounded fraction)."""
    raw = (ROW_BUDGET - non_any_rows) / any_eligible if any_eligible else 0.0
    steps = (ROW_BUDGET - non_any_rows) * STEPS_PER_UNIT // any_eligible if any_eligible else 0
    return min(ANY_CAP_STEPS, max(1, steps)) / STEPS_PER_UNIT, raw


def space(df: pd.DataFrame, days: int = SPACING_DAYS) -> pd.DataFrame:
    """One candidate per stock per family per `days` calendar days (the lab rule, studies.entry_sets): walking each stock's fires in date order, a
    fire is kept when it is at least `days` days after the last KEPT fire. df holds one family's fires [sid, date]."""
    d = df.sort_values(["sid", "date"], kind="mergesort")
    sid = d["sid"].to_numpy()
    day = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    keep = np.zeros(len(d), dtype=bool)
    last_s, last_d = None, 0
    for k in range(len(d)):
        if sid[k] != last_s or day[k] - last_d >= days:
            keep[k] = True
            last_s, last_d = sid[k], day[k]
    return d[keep]


def _flag_window(bars: pd.DataFrame, ev: pd.DataFrame, n: int) -> np.ndarray:
    """For each bar (sorted by sid, date): is there an event dated after the stock's bar n sessions back and on or before this bar? For the first n
    bars of a stock the window starts at its first bar. An event on a day without a bar of the stock falls to the stock's next bar."""
    out = np.zeros(len(bars), dtype=bool)
    if ev.empty:
        return out
    evs = {s: np.sort(g["date"].to_numpy().astype("datetime64[D]")) for s, g in ev.groupby("sid")}
    sid = bars["sid"].to_numpy()
    dd = bars["date"].to_numpy().astype("datetime64[D]")
    bounds = np.r_[0, np.flatnonzero(sid[1:] != sid[:-1]) + 1, len(bars)]
    for a, z in zip(bounds[:-1], bounds[1:]):
        e = evs.get(sid[a])
        if e is None:
            continue
        d = dd[a:z]
        lo = np.empty_like(d)
        lo[:n] = d[0] - np.timedelta64(1, "D")
        lo[n:] = d[:-n] if len(d) > n else lo[n:]
        out[a:z] = (np.searchsorted(e, d, side="right") - np.searchsorted(e, lo, side="right")) > 0
    return out


def indicators(bars: pd.DataFrame, brk_days: pd.DataFrame, ca: pd.DataFrame, band: pd.DataFrame) -> pd.DataFrame:
    """Columns the features table lacks, per bar of every stock, each from that bar and earlier bars of the same stock (adjusted prices):
    rsi14 (Wilder, as india.studies2._indicators and the paper engine), hi250 / lo250 (max / min of the previous 250 closes), sma20, sd20
    (population standard deviation of the last 20 closes, Bollinger's definition), bbw = 4 sd20 / sma20 and bbw_p10 (10th percentile, linear
    interpolation, of the 250 widths ending at the bar), bb_lower = sma20 - 2 sd20, mom = c(T-20) / c(T-250) - 1, raw_pc (the previous bar's
    raw close), RETEST's reference (rt_level, rt_age: the most recent BRK day 5 or more sessions back, its age in the stock's sessions and the
    highest close of the 20 sessions before it), ca200 (an unconfirmed corporate-action flag in the stock's 200 sessions to T) and band5 (a
    lower-band hit in the stock's last 5 sessions). Sessions are the stock's own bars."""
    b = bars.sort_values(["sid", "date"], kind="mergesort").reset_index(drop=True)
    sid = b["sid"]
    g = b.groupby("sid", sort=False)
    b["i"] = g.cumcount()
    d = g["c"].diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    au = up.groupby(sid, sort=False).transform(lambda x: x.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    ad = dn.groupby(sid, sort=False).transform(lambda x: x.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    b["rsi14"] = 100 - 100 / (1 + au / ad.replace(0, np.nan))
    pc = g["c"].shift(1)
    roll = lambda s, n: s.groupby(sid, sort=False).rolling(n, min_periods=n)
    b["hi250"] = roll(pc, 250).max().reset_index(level=0, drop=True)
    b["lo250"] = roll(pc, 250).min().reset_index(level=0, drop=True)
    b["sma20"] = roll(b["c"], 20).mean().reset_index(level=0, drop=True)
    b["sd20"] = roll(b["c"], 20).std(ddof=0).reset_index(level=0, drop=True)
    b["bbw"] = 4 * b["sd20"] / b["sma20"]
    b["bbw_p10"] = roll(b["bbw"], 250).quantile(0.1, interpolation="linear").reset_index(level=0, drop=True)
    b["bb_lower"] = b["sma20"] - 2 * b["sd20"]
    b["mom"] = g["c"].shift(20) / g["c"].shift(250) - 1
    b["raw_pc"] = g["raw_close"].shift(1) if "raw_close" in b else np.nan
    # RETEST: BRK days within the top 500 (whatever the rank or spacing), carried forward with the highest close of the 20 sessions before them
    prev20 = roll(pc, 20).max().reset_index(level=0, drop=True)
    isb = b.set_index(["sid", "date"]).index.isin(pd.MultiIndex.from_frame(brk_days[["sid", "date"]])) if len(brk_days) else np.zeros(len(b), bool)
    ref_i = pd.Series(np.where(isb, b["i"], np.nan)).groupby(sid, sort=False).ffill()
    # the most recent BRK day at or before T-5 (its bar number, forward-filled, as of 5 bars back); its level is read from that very bar
    ref_i5 = ref_i.groupby(sid, sort=False).shift(5)
    b["rt_age"] = b["i"] - ref_i5
    pos = (b.index.to_numpy() - b["i"].to_numpy()) + ref_i5.fillna(-1).to_numpy().astype(np.int64)   # row of the BRK bar in b (same stock)
    b["rt_level"] = np.where(ref_i5.notna(), prev20.to_numpy()[np.clip(pos, 0, None)], np.nan)
    b["ca200"] = _flag_window(b, ca, CA_WINDOW)
    hit = b.set_index(["sid", "date"]).index.isin(pd.MultiIndex.from_frame(band[["sid", "date"]])) if len(band) else np.zeros(len(b), bool)
    b["band5"] = pd.Series(hit.astype(float)).groupby(sid, sort=False).rolling(5, min_periods=1).max().reset_index(level=0, drop=True).astype(bool)
    return b


def fire(p: pd.DataFrame) -> dict[str, pd.Series]:
    """The stage-1 rules on panel rows (one per stock-day of the features table, merged with indicators()). Each returns True where the family
    fires on T, before liquidity, eligibility and spacing. MOM is ranked separately (mom_top)."""
    f = lambda c: p[c].astype("boolean").fillna(False).astype(bool) if c in p else pd.Series(False, index=p.index)
    above200 = p["dist_sma200"] > EPS
    gap_dn = (p["gap_pct"] <= -0.03 + EPS) & (p["ret_1"] <= -0.03 + EPS)
    div_big = (p["div_amt"] >= (0.02 - EPS) * p["raw_pc"]) if "div_amt" in p else pd.Series(False, index=p.index)
    lvl = p["rt_level"]
    return {
        "BRK": f("breakout20") & (p["vol_ratio20"] >= 1.5 - EPS) & above200,
        "PULL": above200 & (p["dist_sma20"] <= -0.05 + EPS),
        "REV": p["rsi14"] < 30 - EPS,
        "DECL": p["ret_60"] < -0.30 - EPS,
        "BAND": f("band5"),
        "HI52": (p["c"] > p["hi250"]) & above200,
        "LO52": p["c"] < p["lo250"],
        "SQZ": (p["bbw"] <= p["bbw_p10"]) & (p["dist_sma50"] > EPS),
        "BBMR": (p["c"] < p["bb_lower"]) & above200,
        "GAPU": (p["gap_pct"] >= 0.03 - EPS) & (p["ret_1"] >= 0.03 - EPS),
        "GAPD": gap_dn & ~div_big.fillna(False).astype(bool),
        "RETEST": lvl.notna() & (p["rt_age"] <= 60) & (p["l"] <= lvl + p["atr14"]) & (p["c"] > lvl),
        "MOM": f("mom_top"),
    }


def brk_rule(feat: pd.DataFrame) -> pd.Series:
    return feat["breakout20"].astype("boolean").fillna(False).astype(bool) & (feat["vol_ratio20"] >= 1.5 - EPS) & (feat["dist_sma200"] > EPS)


def month_ends(sessions) -> list:
    """The last session of each month in the trading calendar given (cut at E: 2023-12-29 is the last session of December 2023)."""
    s = pd.DatetimeIndex(sorted(pd.to_datetime(pd.Series(list(sessions)))))
    return sorted(pd.Series(s).groupby([s.year, s.month]).max())


def mom_top(p: pd.DataFrame, ends: list) -> pd.Series:
    """MOM: on the last session of each month, the top decile of mom within the liquid 250 (rank 1-250, every stock with a value): descending rank
    (ties share the better rank) at most floor(n / 10). Eligibility is applied afterwards, like every family."""
    out = pd.Series(False, index=p.index)
    pool = p[p["date"].isin(ends) & (p["liq_rank"] <= 250) & p["mom"].notna()]
    if pool.empty:
        return out
    r = pool.groupby("date")["mom"].rank(ascending=False, method="min")
    n = pool.groupby("date")["mom"].transform("size")
    out.loc[pool.index[(r <= n // 10).to_numpy()]] = True
    return out


def panel(feat: pd.DataFrame, bars: pd.DataFrame, ca: pd.DataFrame, band: pd.DataFrame, div: pd.DataFrame, sessions, fams=None,
          start: str = C_START, end: str = E_END) -> pd.DataFrame:
    """One row per stock-day of the features table on [start, end] with the indicator columns, `elig` (liquidity rank 1-250 on T and no
    unconfirmed corporate-action flag in the stock's 200 sessions to T) and one column f_<FAMILY> per family (the rule fired on T, before
    eligibility and spacing). feat: the features table (date, sid, symbol, liq_rank, o, h, l, c, ret_1, ret_60, gap_pct, atr14, vol_ratio20,
    dist_sma20, dist_sma50, dist_sma200, breakout20); bars: every adjusted bar of every stock (sid, date, o, h, l, c, raw_close); ca: unconfirmed
    corporate-action flags (sid, date); band: lower-band hits (sid, date); div: dividend ex-dates (symbol, date, amount, known_from); sessions:
    the trading calendar to `end`. Nothing dated after `end` is read, and a row dated T uses rows dated T or earlier only."""
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    feat = feat[feat["date"] <= hi]
    bars = bars[bars["date"] <= hi]
    ca, band = ca[ca["date"] <= hi], band[band["date"] <= hi]
    ind = indicators(bars, feat.loc[brk_rule(feat), ["sid", "date"]], ca, band)
    cols = ["sid", "date", "i", "rsi14", "hi250", "lo250", "sma20", "sd20", "bbw", "bbw_p10", "bb_lower", "mom", "raw_pc", "rt_age", "rt_level", "ca200", "band5", "c"]
    p = feat[feat["date"] >= lo].merge(ind[cols].rename(columns={"c": "c_bar"}), on=["sid", "date"], how="left", validate="one_to_one")
    if len(div):
        dv = div[(div["known_from"] <= div["date"]) & (div["date"] <= hi) & div["amount"].notna()].groupby(["symbol", "date"], as_index=False)["amount"].max()
        p = p.merge(dv.rename(columns={"amount": "div_amt"}), on=["symbol", "date"], how="left")
    p["mom_top"] = mom_top(p, month_ends([x for x in sessions if pd.Timestamp(x) <= hi]))
    p["ca200"] = p["ca200"].astype("boolean").fillna(False).astype(bool)
    p["elig"] = (p["liq_rank"] <= 250) & ~p["ca200"]
    for fam, m in fire(p).items():
        if fams is None or fam in fams:
            p["f_" + fam] = m.to_numpy(dtype=bool)
    return p


def assemble(p: pd.DataFrame, fams, rate: float | None = None, start: str = C_START) -> tuple[pd.DataFrame, dict]:
    """From panel rows to the candidate table: each family's eligible fires from its start date, the 14-day spacing within each family, CTL,
    ANY (hash draw at the rate, then spacing) and the priority flag (after spacing). rate=None computes the ANY rate from the counts (the
    pre-freeze step); a number uses it (the frozen any_rate). Returns (sid, family, signal_date, liq_rank, priority_family) and the counts."""
    elig = p["elig"].astype(bool)
    info: dict = {"families": list(fams), "start": start}
    rows, fires = [], {}
    for fam in fams:
        m = p["f_" + fam].astype(bool) & elig & (p["date"] >= pd.Timestamp(max(start, FAMILY_START.get(fam, start))))
        fires[fam] = int(m.sum())
        rows.append(space(p.loc[m, ["sid", "date", "liq_rank"]]).assign(family=fam))
    real = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["sid", "date", "liq_rank", "family"])
    # CTL: per day, as many eligible liquid stocks as there are distinct real-family stock-days that day (after spacing), lowest hash(sid, date, 13) first; not spaced
    el = p.loc[elig & (p["date"] >= pd.Timestamp(start)), ["sid", "date", "liq_rank"]].reset_index(drop=True)
    el["h13"] = hash_many(el["sid"], el["date"], CTL_SALT)
    need = real.drop_duplicates(["sid", "date"]).groupby("date").size()
    el["k"] = el["date"].map(need).fillna(0).astype(int)
    el = el.sort_values(["date", "h13", "sid"], kind="mergesort")
    el["pos"] = el.groupby("date").cumcount()
    ctl = el[el["pos"] < el["k"]][["sid", "date", "liq_rank"]].assign(family="CTL")
    non_any = int(len(real) + len(ctl))          # every other family's rows, CTL included, after spacing and before priority
    n_elig = int(len(el))                        # ANY-eligible: the eligible liquid stock-days
    r, raw = any_rate(non_any, n_elig) if rate is None else (float(rate), float("nan"))
    el["h11"] = hash_many(el["sid"], el["date"], ANY_SALT)
    anyr = space(el.loc[el["h11"] < r, ["sid", "date", "liq_rank"]]).assign(family="ANY")   # hash draw first, then the 14-day spacing
    cand = pd.concat([real, ctl, anyr], ignore_index=True).rename(columns={"date": "signal_date"})
    # priority: one row per stock-day among the rows kept after spacing; ANY only where no real family fired; CTL is outside the order (never chosen)
    pr = {f_: k for k, f_ in enumerate(PRIORITY)}
    cand["_p"] = cand["family"].map(pr)
    best = cand[cand["family"] != "CTL"].sort_values(["sid", "signal_date", "_p"], kind="mergesort").drop_duplicates(["sid", "signal_date"])
    cand["priority_family"] = False
    cand.loc[best.index, "priority_family"] = True
    cand = cand.drop(columns="_p").sort_values(["signal_date", "family", "sid"], kind="mergesort").reset_index(drop=True)
    cand["liq_rank"] = cand["liq_rank"].astype(int)
    cand = cand[["sid", "family", "signal_date", "liq_rank", "priority_family"]]
    yr = cand["signal_date"].dt.year
    tab = cand.groupby([cand["family"], yr]).size().unstack(fill_value=0)
    ptab = cand[cand["priority_family"]].groupby([cand["family"], yr]).size().unstack(fill_value=0)
    distinct = real.drop_duplicates(["sid", "date"])
    info.update({
        "rows_after_spacing_before_priority": {k: {int(y): int(v) for y, v in row.items()} for k, row in tab.iterrows()},
        "rows_after_spacing_total": {k: int(v) for k, v in tab.sum(axis=1).items()},
        "fires_before_spacing": fires,
        "priority_rows": {k: {int(y): int(v) for y, v in row.items()} for k, row in ptab.iterrows()},
        "priority_rows_total": {k: int(v) for k, v in ptab.sum(axis=1).items()},
        "distinct_real_family_stock_days": int(len(distinct)),
        "distinct_real_family_stock_days_by_year": {int(y): int(v) for y, v in distinct.groupby(distinct["date"].dt.year).size().items()},
        "ctl_rows": int(len(ctl)),
        "any_eligible": n_elig, "any_eligible_by_year": {int(y): int(v) for y, v in el.groupby(el["date"].dt.year).size().items()},
        "non_any_rows": non_any, "real_family_rows": int(len(real)),
        "any_rate": r, "any_rate_unrounded": raw, "any_drawn_before_spacing": int((el["h11"] < r).sum()), "any_rows": int(len(anyr)),
        "total_rows": int(len(cand)),
    })
    return cand, info


def stage1(feat, bars, ca, band, div, sessions, struck=NEEDS_RESULTS, rate: float | None = None, start: str = C_START, end: str = E_END):
    """Stage 1 on [start, end] (panel, then assemble) on the families that survive coverage. Returns (candidate table, counts, panel)."""
    missing = [x for x in NEEDS_RESULTS if x not in struck]
    if missing:
        raise NotImplementedError(f"{missing} survived the coverage rule but have no code here (results filings were struck on 20 Oct 2026)")
    fams = [x for x in REAL if x not in struck]
    p = panel(feat, bars, ca, band, div, sessions, fams, start, end)
    cand, info = assemble(p, fams, rate, start)
    info.update({"struck": sorted(struck), "end": end})
    return cand, info, p


# ----------------------------------------------------------------------------------------------- loaders (silver and gold, cut at E_END)

def _sql_rows(sql: str, params=None) -> pd.DataFrame:
    import duckdb
    con = duckdb.connect()
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()


def _cm_glob() -> str:
    return str(paths.data_dir() / "silver" / "cm_bhavcopy" / "year=*" / "part.parquet")


def raw_base(end: str = E_END) -> pd.DataFrame:
    """Every series-EQ cash row to `end` keyed as the lab keys it (sid = the ISIN entity where the row carries an ISIN, else the symbol; funds out):
    date, sid, symbol, raw_close, turnover. Used for the dividend yield (raw close of T-1) and to map PR-zip symbols to sids on their dates."""
    D = paths.data_dir()
    names = D / "silver" / "security_master" / "names.parquet"
    cm = _cm_glob()
    return _sql_rows(f"""
        with cm as (select date, symbol, close, turnover, isin from read_parquet('{cm}') where series = 'EQ' and close > 0 and date <= ?
                    and coalesce(isin, '') not like 'INF%' and symbol not in (select distinct symbol from read_parquet('{cm}') where isin like 'INF%')),
             ent as (select distinct isin, entity from read_parquet('{names}'))
        select c.date, coalesce(e.entity, c.symbol) as sid, c.symbol, c.close as raw_close, c.turnover from cm c left join ent e on e.isin = c.isin""",
                     [pd.Timestamp(end).date()])


_DIV_RS = re.compile(r"R[SE]\.?\s*-?\s*(\d+(?:\.\d+)?)")
_NUM = re.compile(r"(\d+(?:\.\d+)?)")


def div_amount(purpose: str) -> tuple[float | None, bool]:
    """Rupees per share named in a PR-zip book-closure purpose, summed over its dividend parts ('FIN DIV-RS 6/SPL DIV-RS 4' = 10). Returns
    (amount, complete): complete is False when a dividend part names no rupee amount ('INTERIM DIVIDEND', 'DIVIDEND - 10%' of face value)."""
    tot, complete, any_div = 0.0, True, False
    for seg in re.split(r"/(?!-)", str(purpose).upper()):
        if "DIV" not in seg:
            continue
        any_div = True
        m = _DIV_RS.search(seg)
        if m is None and "%" not in seg:
            m = _NUM.search(seg)
        if m is None:
            complete = False
            continue
        tot += float(m.group(1))
    if not any_div:
        return None, False
    return (tot if tot > 0 else None), complete


def dividends(end: str = E_END) -> tuple[pd.DataFrame, dict]:
    """Dividend ex-dates from the PR zips (silver/pr/bc_actions, 2010 on), known from the first daily file that lists them. The amount is the PR
    text's (largest record per symbol and ex-date); where the PR text gives none, or only part, the exchange's corporate-action record for the
    same symbol and ex-date (silver/corporate_actions record_b, kind DIVIDEND) supplies a lower bound. No amount at all: kept as unknown (NaN),
    which does not exclude a gap (the rule needs a dividend shown to be 2% or more); counted."""
    D = paths.data_dir()
    bc = pd.read_parquet(D / "silver" / "pr" / "bc_actions.parquet", columns=["date", "symbol", "ex_date", "purpose"])
    bc = bc[bc["purpose"].str.upper().str.contains("DIV", na=False) & bc["ex_date"].notna()]
    bc["date"], bc["ex_date"] = pd.to_datetime(bc["date"]), pd.to_datetime(bc["ex_date"])
    hi = pd.Timestamp(end)
    bc = bc[(bc["date"] <= hi) & (bc["ex_date"] <= hi)]
    rec = bc.groupby(["symbol", "ex_date", "purpose"], as_index=False)["date"].min().rename(columns={"date": "known_from"})
    parsed = rec["purpose"].map(div_amount)
    rec["amt"] = [a for a, _ in parsed]
    rec["complete"] = [c for _, c in parsed]
    rb = pd.read_parquet(D / "silver" / "corporate_actions" / "record_b.parquet", columns=["symbol", "ex_date", "kind", "amount"])
    rb = rb[(rb["kind"] == "DIVIDEND") & rb["amount"].notna()]
    rb["ex_date"] = pd.to_datetime(rb["ex_date"], errors="coerce")
    rb = rb[rb["ex_date"] <= hi].groupby(["symbol", "ex_date"])["amount"].max()
    g = rec.groupby(["symbol", "ex_date"]).agg(known_from=("known_from", "min"), amt=("amt", "max"), complete=("complete", "max")).reset_index()
    full = g["complete"] & g["amt"].notna()
    fb = pd.Series(list(zip(g["symbol"], g["ex_date"]))).map(rb.to_dict()).to_numpy(dtype=float)
    g["amount"] = np.where(full, g["amt"], np.fmax(g["amt"].to_numpy(dtype=float), fb))
    info = {"pr_dividend_ex_dates": int(len(g)), "amount_from_pr_text": int(full.sum()),
            "amount_from_record_b_or_partial": int((~full & pd.Series(g["amount"]).notna()).sum()), "amount_unknown": int(pd.Series(g["amount"]).isna().sum())}
    return g.rename(columns={"ex_date": "date"})[["symbol", "date", "amount", "known_from"]], info


def load_inputs(end: str = E_END) -> dict:
    """The lab tables stage 1 reads, every one cut at `end` (2023-12-29)."""
    D, G, hi = paths.data_dir(), paths.gold(), pd.Timestamp(end)
    fc = ["date", "sid", "symbol", "liq_rank", "o", "h", "l", "c", "ret_1", "ret_60", "gap_pct", "atr14", "vol_ratio20", "dist_sma20", "dist_sma50", "dist_sma200", "breakout20"]
    feat = pd.read_parquet(G / "features" / "daily.parquet", columns=fc)
    feat["date"] = pd.to_datetime(feat["date"])
    feat = feat[feat["date"] <= hi].reset_index(drop=True)
    bars = pd.read_parquet(G / "bars" / "adj_daily.parquet", columns=["sid", "date", "o", "h", "l", "c"])
    bars["date"] = pd.to_datetime(bars["date"])
    bars = bars[bars["date"] <= hi]
    rb = raw_base(end)
    rb["date"] = pd.to_datetime(rb["date"])
    one = rb.sort_values("turnover", ascending=False, kind="mergesort").drop_duplicates(["date", "sid"])   # the lab's row per (date, sid)
    bars = bars.merge(one[["sid", "date", "raw_close"]], on=["sid", "date"], how="left")
    ca = pd.read_parquet(G / "ca_flags" / "ca_flags.parquet", columns=["sid", "date", "status"])
    ca["date"] = pd.to_datetime(ca["date"])
    n_frozen = int((ca["status"] == "FROZEN").sum())
    frozen = ca[(ca["status"] == "FROZEN") & (ca["date"] <= hi)][["sid", "date"]]
    ca = ca[(ca["status"] != "FROZEN") & (ca["date"] <= hi)][["sid", "date"]]      # unconfirmed corporate actions only (the 75 ambiguous events)
    bh = pd.read_parquet(D / "silver" / "pr" / "band_hits.parquet", columns=["date", "symbol", "series", "side"])
    bh["date"] = pd.to_datetime(bh["date"])
    bh = bh[(bh["series"] == "EQ") & bh["side"].str.upper().str.startswith("L") & (bh["date"] <= hi)]
    band = bh.merge(rb[["date", "symbol", "sid"]].drop_duplicates(), on=["date", "symbol"], how="inner")[["sid", "date"]].drop_duplicates()
    div, dinfo = dividends(end)
    cal = pd.read_parquet(D / "silver" / "calendar" / "calendar.parquet")
    sessions = sorted(d for d in pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]) if d <= hi)
    return {"feat": feat, "bars": bars, "ca": ca, "band": band, "div": div, "sessions": sessions,
            "_info": {"dividends": dinfo, "ca_flags_unconfirmed_rows": int(len(ca)), "ca_flags_frozen_rows": n_frozen, "band_low_hits_mapped": int(len(band)),
                      "bars_without_raw_close": int(bars["raw_close"].isna().sum())}, "_frozen": frozen}


def _git() -> dict:
    run = lambda *a: subprocess.run(["git", *a], cwd=HERE.parent, capture_output=True, text=True).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "sp3_py_dirty": bool(run("status", "--porcelain", "india/sp3.py"))}


def struck_families() -> list[str]:
    f = paths.manifest_dir() / "sp3_prep_coverage.json"
    if not f.exists():
        raise SystemExit("run `python -m india.sp3 prep coverage` first: the families stage 1 runs on depend on it (pre_freeze.order)")
    return json.loads(f.read_text())["struck_families"]


def prep_counts() -> dict:
    t0 = time.time()
    struck = struck_families()
    inp = load_inputs()
    cand, info, p = stage1(inp["feat"], inp["bars"], inp["ca"], inp["band"], inp["div"], inp["sessions"], struck=struck)
    elig = p["elig"]
    rules = {k[2:]: p[k] for k in p.columns if k.startswith("f_")}
    # diagnostics (counts only): what each convention changes, so a reviewer can see it
    in_win = (p["date"] >= pd.Timestamp(C_START))
    sess = [d for d in inp["sessions"] if d >= pd.Timestamp(C_START)]
    have = set(p.loc[elig, "date"])
    empty = [d for d in sess if d not in have]
    runs = []
    for d in empty:
        if runs and (sess.index(d) - sess.index(runs[-1][1])) == 1:
            runs[-1][1] = d
        else:
            runs.append([d, d])
    bs = inp["bars"].sort_values(["sid", "date"], kind="mergesort").reset_index(drop=True)[["sid", "date"]]
    fzk = bs[_flag_window(bs, inp["_frozen"], CA_WINDOW)].assign(fz=True)
    pz = p[["sid", "date"]].merge(fzk, on=["sid", "date"], how="left")["fz"].fillna(False).to_numpy(dtype=bool)
    dv = inp["div"]
    unk = dv[dv["amount"].isna() & (dv["known_from"] <= dv["date"])][["symbol", "date"]].assign(u=True)
    pu = p[["symbol", "date"]].merge(unk, on=["symbol", "date"], how="left")["u"].fillna(False).to_numpy(dtype=bool)
    naive = {"BRK": p["breakout20"].astype("boolean").fillna(False).astype(bool) & (p["vol_ratio20"] > 1.5) & (p["dist_sma200"] > 0),
             "PULL": (p["dist_sma200"] > 0) & (p["dist_sma20"] < -0.05)}
    gd = (p["gap_pct"] <= -0.03 + EPS) & (p["ret_1"] <= -0.03 + EPS) & elig & (p["date"] >= pd.Timestamp(FAMILY_START["GAPD"]))
    sc = sessions_index(inp["sessions"])
    late = cand["signal_date"].map(sc) > sc[pd.Timestamp(E_END)] - 62
    diag = {
        "sessions_2005_2023": len(sess), "sessions_with_no_eligible_stock": len(empty),
        "no_eligible_runs": [[str(a.date()), str(b.date())] for a, b in runs],
        "liquid_stock_days": int((p["liq_rank"] <= 250).sum()), "ineligible_unconfirmed_ca": int(((p["liq_rank"] <= 250) & p["ca200"]).sum()),
        "frozen_runs_would_also_remove": int((((p["liq_rank"] <= 250) & ~p["ca200"]).to_numpy() & pz).sum()),
        "brk_e02_strict_vs_spec_words_fires_differ": int(((naive["BRK"] != rules["BRK"]) & elig).sum()),
        "pull_e02_strict_vs_spec_words_fires_differ": int(((naive["PULL"] != rules["PULL"]) & elig).sum()),
        "gapd_price_rule_fires": int(gd.sum()), "gapd_removed_by_dividend_2pct": int((gd & ~rules["GAPD"]).sum()),
        "gapd_on_unknown_amount_dividend_ex_date": int((gd.to_numpy() & pu).sum()),
        "features_close_vs_bar_close_max_rel_diff": float(((p["c"] - p["c_bar"]).abs() / p["c"]).max()),
        "rows_signalled_within_62_sessions_of_E": int(late.sum()),
        "inputs": inp["_info"],
    }
    out_dir = paths.gold() / "studies"
    out_dir.mkdir(parents=True, exist_ok=True)
    cand.to_parquet(out_dir / Path(CANDS).name, index=False)
    spec = json.loads(SPEC.read_text())
    out = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "spec_version": spec["version"], **_git(),
           "rules": "stage_1_gather_everything as worded in sp3_v1.json draft 5; see india/sp3.py stage1() for each convention", **info,
           "diagnostics": diag, "candidate_table": str(Path("gold") / CANDS), "candidate_table_rows": int(len(cand)), "seconds": round(time.time() - t0, 1)}
    (paths.manifest_dir() / "sp3_prep_counts.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def sessions_index(sessions) -> dict:
    return {pd.Timestamp(d): k for k, d in enumerate(sorted(pd.to_datetime(pd.Series(list(sessions)))))}


# =============================================================================================================== prep stops (2005-2023)
# Whether bars exist and corporate records; no price is read. in_window_events.boundary: L = the stock's last session (EQ, BE or BZ) on or
# before E; a permanent stop if E - L >= 62 market sessions. Renames inside an ISIN entity are already one sid; the two kinds of rename the
# sid key cannot see are settled here mechanically (the 2011 sid-key switch, NSE's symbol-change list); every other case is classified by hand
# in registrations/sp3_permanent_stops_evidence.json, and this step refuses to run if that list and the computed cases differ.
STOP_GAP = 62
SWITCH_DAYS = 10            # a symbol sid whose symbol carries an ISIN within 10 calendar days after L: the sid key switched to the ISIN entity
RENAME_DAYS = 10            # symbol-change list: the new symbol's first session within 10 calendar days after L ...
RENAME_EFFECTIVE = (-10, 30)  # ... and the change effective between 10 days before and 30 days after L
EVIDENCE = HERE / "registrations" / "sp3_permanent_stops_evidence.json"
STOPS_CSV = HERE / "registrations" / "sp3_permanent_stops.csv"
CLASSES = ("scheme", "voluntary_delisting", "renamed", "compulsory", "liquidation", "suspended_unresolved", "unresolved")
FAILED = ("compulsory", "liquidation", "suspended_unresolved", "unresolved")
TREATMENT = {"scheme": "end_scheme: closes at last_session's close, no exit fees; the slot frees at the next session",
             "voluntary_delisting": "end_scheme: closes at last_session's close, no exit fees; the slot frees at the next session",
             "renamed": "followed to successor_sid; not a stop"}
TREATMENT.update({c: "end_failed: -100% (sensitivity: last_session's close); the slot frees at the next session" for c in FAILED})
# the mechanical holdout rule (in_window_events.holdout_permanent_stops), with the record categories it reads written out so the holdout run
# uses exactly these: scheme / voluntary_delisting records for the sid in the 250 market sessions ending at L; renamed = the ISIN entity has
# sessions after L; otherwise end_failed. Precedence renamed > scheme > voluntary_delisting.
MECH_WINDOW = 250
MECH_SCHEME_CATS = ("Amalgamation/Merger", "Scheme of Arrangement", "Results/Scheme of Arrangement")   # silver/announce category
MECH_VOL_CATS = ("Voluntary Delisting", "Public Announcement - Delisting")                           # silver/announce category
MECH_DELIST_CAT = "Delisting"                       # silver/announce category: counts as voluntary only with MECH_VOL_RE in the text
MECH_SCHEME_RE = r"\bamalgamat\w*|(?<!de-)\bmergers?\b|scheme of arrangement"    # PR-zip subjects and corporate-action subjects
MECH_VOL_RE = r"delisting offer|voluntar\w* delist\w*|reverse book[- ]?building"


def _cash_rows(end: str = E_END) -> pd.DataFrame:
    """Every EQ, BE and BZ cash row to `end`: date, symbol, series, isin, sid (the lab's key: the ISIN entity, else the symbol)."""
    D = paths.data_dir()
    names = D / "silver" / "security_master" / "names.parquet"
    r = _sql_rows(f"""select c.date, c.symbol, c.series, c.isin, coalesce(e.entity, c.symbol) as sid
        from read_parquet('{_cm_glob()}') c left join (select distinct isin, entity from read_parquet('{names}')) e on e.isin = c.isin
        where c.series in ('EQ', 'BE', 'BZ') and c.date <= ?""", [pd.Timestamp(end).date()])
    r["date"] = pd.to_datetime(r["date"])
    return r


def stop_cases(rows: pd.DataFrame, sids, sessions, end: str = E_END) -> pd.DataFrame:
    """The candidate sids whose last session L (any of EQ, BE, BZ) is at least STOP_GAP market sessions before E: sid, L, gap, symbols, isins."""
    sess = pd.DatetimeIndex(sorted(pd.to_datetime(pd.Series(list(sessions)))))
    sess = sess[sess <= pd.Timestamp(end)]
    g = rows[rows["sid"].isin(set(sids))].groupby("sid")
    last = g["date"].max()
    gap = (len(sess) - 1) - sess.searchsorted(last.to_numpy(), side="left")
    out = pd.DataFrame({"sid": last.index, "L": last.to_numpy(), "gap": gap})
    out = out[out["gap"] >= STOP_GAP].reset_index(drop=True)
    sy = g["symbol"].apply(lambda x: sorted(set(x)))
    isn = rows[rows["sid"].isin(set(out["sid"])) & rows["isin"].notna()].groupby("sid")["isin"].apply(lambda x: sorted(set(x)))
    out["symbols"] = out["sid"].map(sy)
    out["isins"] = out["sid"].map(isn).apply(lambda x: x if isinstance(x, list) else [])
    return out


class _Rows:
    """The cash rows indexed for the stop step: per symbol (sorted by date) and each sid's last session."""
    def __init__(self, rows: pd.DataFrame):
        r = rows.sort_values(["symbol", "date", "series"], kind="mergesort")
        self.by_sym = {s: g for s, g in r.groupby("symbol", sort=False)}
        self.last = rows.groupby("sid")["date"].max()

    def first_after(self, symbols, after: pd.Timestamp, with_isin: bool = False):
        best = None
        for s in symbols:
            g = self.by_sym.get(s)
            if g is None:
                continue
            g = g[g["date"] > after]
            if with_isin:
                g = g[g["isin"].notna()]
            if len(g) and (best is None or g.iloc[0]["date"] < best["date"]):
                best = g.iloc[0]
        return best

    def has_after(self, sid, after: pd.Timestamp) -> bool:
        return sid in self.last.index and self.last[sid] > after


def settle_mechanical(cases: pd.DataFrame, rx: "_Rows", symbol_changes: list[dict]) -> dict:
    """The cases this code settles: the 2011 sid-key switch and confirmed symbol-change renames. sid -> {class, successor, evidence}."""
    out = {}
    sc = pd.DataFrame(symbol_changes or [], columns=["old", "new", "effective", "company"])
    sc["effective"] = pd.to_datetime(sc["effective"])
    for c in cases.itertuples():
        L = pd.Timestamp(c.L)
        if not c.isins:     # a symbol sid: its symbol carrying an ISIN from the next sessions is the 2011 key switch
            f = rx.first_after(c.symbols, L, with_isin=True)
            if f is not None and (f["date"] - L).days <= SWITCH_DAYS:
                out[c.sid] = {"class": "renamed", "successor": f["sid"], "evidence": f"silver/cm_bhavcopy: symbol {f['symbol']} carries ISIN {f['isin']} from "
                              f"{f['date'].date()} (the cash file's ISIN column starts 2011-06-22 and the lab's sid switches from the symbol to the ISIN entity)"}
                continue
        lo, hi = L + pd.Timedelta(days=RENAME_EFFECTIVE[0]), L + pd.Timedelta(days=RENAME_EFFECTIVE[1])
        hits = []
        for h in sc[sc["old"].isin(c.symbols) & (sc["effective"] >= lo) & (sc["effective"] <= hi)].itertuples():
            f = rx.first_after([h.new], L)
            if f is not None and (f["date"] - L).days <= RENAME_DAYS:
                hits.append((f["date"], h, f))
        if hits:
            hits.sort(key=lambda x: x[0])
            if len(hits) > 1 and hits[0][0] == hits[1][0] and hits[0][2]["sid"] != hits[1][2]["sid"]:
                raise RuntimeError(f"{c.sid}: two symbol-change successors start on the same day")
            d, h, f = hits[0]
            out[c.sid] = {"class": "renamed", "successor": f["sid"], "evidence": f"NSE symbol-change list (https://nsearchives.nseindia.com/content/equities/symbolchange.csv): "
                          f"{h.old} -> {h.new} effective {h.effective.date()} ({h.company}); {h.new}'s first cash session {d.date()}"}
    return out


def mechanical(cases: pd.DataFrame, rx: "_Rows", sessions, settled: dict, ann: pd.DataFrame, prz: pd.DataFrame, rb: pd.DataFrame, end: str = E_END) -> pd.DataFrame:
    """in_window_events.holdout_permanent_stops on the 2005-2023 cases. ann: silver/announce (symbol, isin, category, date, text); prz: PR-zip
    announcements (date, symbol, subject); rb: corporate-action records (symbol, isin, ex_date, subject). Returns sid, mech_class, mech_why."""
    sess = pd.DatetimeIndex(sorted(pd.to_datetime(pd.Series(list(sessions)))))
    sess = sess[sess <= pd.Timestamp(end)]
    out = []
    for c in cases.itertuples():
        L = pd.Timestamp(c.L)
        lo = sess[max(0, sess.searchsorted(L) - (MECH_WINDOW - 1))]
        syms, isn = set(c.symbols), set(c.isins)
        # renamed: the sid's ISIN entity has sessions after L (a symbol sid's ISIN entity: the one its symbol switched to in 2011)
        ent = c.sid if c.isins else (settled.get(c.sid, {}).get("successor") if "carries ISIN" in settled.get(c.sid, {}).get("evidence", "") else None)
        if ent is not None and rx.has_after(ent, L):
            out.append((c.sid, "renamed", f"ISIN entity {ent} has sessions after L"))
            continue
        a = ann[(ann["symbol"].isin(syms) | ann["isin"].isin(isn)) & (ann["date"] >= lo) & (ann["date"] <= L)]
        p = prz[prz["symbol"].isin(syms) & (prz["date"] >= lo) & (prz["date"] <= L)]
        b = rb[(rb["symbol"].isin(syms) | rb["isin"].isin(isn)) & (rb["ex_date"] >= lo) & (rb["ex_date"] <= L)]
        sch = a[a["category"].isin(MECH_SCHEME_CATS)]
        sch_p = p[p["subject"].str.contains(MECH_SCHEME_RE, case=False, regex=True, na=False)]
        sch_b = b[b["subject"].fillna("").str.contains(MECH_SCHEME_RE, case=False, regex=True)]
        vol = a[a["category"].isin(MECH_VOL_CATS) | ((a["category"] == MECH_DELIST_CAT) & a["text"].str.contains(MECH_VOL_RE, case=False, regex=True, na=False))]
        vol_p = p[p["subject"].str.contains(MECH_VOL_RE, case=False, regex=True, na=False)]
        if len(sch) or len(sch_p) or len(sch_b):
            why = (f"announce {sch['date'].max().date()} [{sch.loc[sch['date'].idxmax(), 'category']}]" if len(sch) else
                   f"PR {sch_p['date'].max().date()}" if len(sch_p) else f"corporate action {sch_b['ex_date'].max().date()}")
            out.append((c.sid, "scheme", why))
        elif len(vol) or len(vol_p):
            out.append((c.sid, "voluntary_delisting", f"announce {vol['date'].max().date()} [{vol.loc[vol['date'].idxmax(), 'category']}]" if len(vol) else f"PR {vol_p['date'].max().date()}"))
        else:
            out.append((c.sid, "end_failed", "no scheme or delisting-offer record in the window"))
    return pd.DataFrame(out, columns=["sid", "mech_class", "mech_why"])


def _expected_mech(cls: str) -> str:
    return cls if cls in ("scheme", "voluntary_delisting", "renamed") else "end_failed"


def _treat(cls: str) -> str:
    return {"scheme": "end_scheme", "voluntary_delisting": "end_scheme", "renamed": "followed"}.get(cls, "end_failed")


def prep_stops() -> dict:
    t0 = time.time()
    D, hi = paths.data_dir(), pd.Timestamp(E_END)
    cp = paths.gold() / CANDS
    if not cp.exists():
        raise SystemExit("run `python -m india.sp3 prep counts` first: the stop list covers the stocks that appear as stage-1 candidates (pre_freeze.order)")
    sids = set(pd.read_parquet(cp, columns=["sid"])["sid"])
    rows = _cash_rows()
    cal = pd.read_parquet(D / "silver" / "calendar" / "calendar.parquet")
    sessions = sorted(d for d in pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]) if d <= hi)
    cases = stop_cases(rows, sids, sessions)
    ev = json.loads(EVIDENCE.read_text())
    rx = _Rows(rows)
    settled = settle_mechanical(cases, rx, ev.get("symbol_changes", []))
    manual = ev["cases"]
    need = set(cases["sid"]) - set(settled)
    if need != set(manual):
        raise RuntimeError(f"{EVIDENCE.name} does not match the computed cases: missing {sorted(need - set(manual))}, extra {sorted(set(manual) - need)}")
    out, flags = [], []
    for c in cases.sort_values(["L", "sid"]).itertuples():
        m = settled.get(c.sid) or manual[c.sid]
        cls, succ = m["class"], m.get("successor")
        if cls not in CLASSES:
            raise RuntimeError(f"{c.sid}: unknown class {cls}")
        if cls == "renamed":
            if not succ or not rx.has_after(succ, pd.Timestamp(c.L)):
                raise RuntimeError(f"{c.sid}: renamed but the successor {succ!r} has no session after L")
        elif succ:
            raise RuntimeError(f"{c.sid}: a successor is given for class {cls}")
        treat = TREATMENT[cls] + (f"; CHECK: {m['flag']}" if m.get("flag") else "")
        if m.get("flag"):
            flags.append({"sid": c.sid, "class": cls, "flag": m["flag"]})
        out.append({"sid": c.sid, "symbols": "/".join(c.symbols), "isin": "/".join(c.isins), "last_session": str(pd.Timestamp(c.L).date()), "class": cls,
                    "successor_sid": succ or "", "evidence": m["evidence"], "treatment": treat,
                    "settled_by": "code: 2011 sid-key switch" if c.sid in settled and "carries ISIN" in m["evidence"] else "code: symbol-change list" if c.sid in settled else "manual"})
    csv_df = pd.DataFrame(out)
    cols = ["sid", "symbols", "isin", "last_session", "class", "successor_sid", "evidence", "treatment"]
    csv_df[cols].to_csv(STOPS_CSV, index=False, lineterminator="\n")
    sha = hashlib.sha256(STOPS_CSV.read_bytes()).hexdigest()
    # the mechanical rule on the same cases
    allsym = {s for x in cases["symbols"] for s in x}
    allisin = {s for x in cases["isins"] for s in x}
    ann = pd.read_parquet(D / "silver" / "announce" / "announcements.parquet", columns=["symbol", "isin", "category", "an_dt", "text"])
    ann = ann[ann["symbol"].isin(allsym) | ann["isin"].isin(allisin)].copy()
    ann["date"] = pd.to_datetime(ann["an_dt"]).dt.normalize()
    ann = ann[ann["date"] <= hi]
    prz = pd.read_parquet(D / "silver" / "pr" / "announcements.parquet", columns=["date", "symbol", "subject"])
    prz = prz[prz["symbol"].isin(allsym)].copy()
    prz["date"] = pd.to_datetime(prz["date"])
    prz = prz[prz["date"] <= hi]
    rb = pd.read_parquet(D / "silver" / "corporate_actions" / "record_b.parquet", columns=["symbol", "isin", "ex_date", "subject"])
    rb["ex_date"] = pd.to_datetime(rb["ex_date"], errors="coerce")
    rb = rb[(rb["symbol"].isin(allsym) | rb["isin"].isin(allisin)) & (rb["ex_date"] <= hi)]
    mech = mechanical(cases, rx, sessions, settled, ann, prz, rb)
    j = csv_df.merge(mech, on="sid")
    j["expected"] = j["class"].map(_expected_mech)
    j["agree"] = j["mech_class"] == j["expected"]
    j["agree_treatment"] = j["class"].map(_treat) == j["mech_class"].map(lambda x: {"scheme": "end_scheme", "voluntary_delisting": "end_scheme", "renamed": "followed"}.get(x, "end_failed"))
    by = {}
    for cls, g in j.groupby("class"):
        by[cls] = {"n": int(len(g)), "mechanical_agrees": int(g["agree"].sum()), "treatment_agrees": int(g["agree_treatment"].sum()),
                   "mechanical_says": {k: int(v) for k, v in g["mech_class"].value_counts().items()}}
    excl = j[j["settled_by"] != "code: 2011 sid-key switch"]
    by_ex = {}
    for cls, g in excl.groupby("class"):
        by_ex[cls] = {"n": int(len(g)), "mechanical_agrees": int(g["agree"].sum()), "treatment_agrees": int(g["agree_treatment"].sum()),
                      "mechanical_says": {k: int(v) for k, v in g["mech_class"].value_counts().items()}}
    dis = j[~j["agree"] & (j["settled_by"] != "code: 2011 sid-key switch")][["sid", "symbols", "last_session", "class", "mech_class", "mech_why"]]
    res = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **_git(), "E": E_END, "rule": f"L = last EQ/BE/BZ session on or before E; permanent stop if E - L >= {STOP_GAP} market sessions",
           "candidate_sids": len(sids), "cases": int(len(cases)), "csv": str(STOPS_CSV.relative_to(HERE.parent)), "csv_sha256": sha,
           "counts_by_class": {k: int(v) for k, v in csv_df["class"].value_counts().items()},
           "counts_by_class_excluding_2011_key_switch": {k: int(v) for k, v in excl["class"].value_counts().items()},
           "settled_by": {k: int(v) for k, v in csv_df["settled_by"].value_counts().items()},
           "cases_by_year_of_L": {int(y): int(v) for y, v in pd.to_datetime(csv_df["last_session"]).dt.year.value_counts().sort_index().items()},
           "mechanical_rule": {"window_sessions_ending_at_L": MECH_WINDOW, "scheme_announce_categories": list(MECH_SCHEME_CATS), "voluntary_announce_categories": list(MECH_VOL_CATS),
                               "delisting_category_needs_text": [MECH_DELIST_CAT, MECH_VOL_RE], "scheme_text_re (PR subjects, corporate-action subjects)": MECH_SCHEME_RE,
                               "voluntary_text_re (PR subjects)": MECH_VOL_RE, "renamed": "the sid's ISIN entity has sessions after L (for a pre-2011 symbol sid: the entity its symbol switched to in 2011)",
                               "precedence": "renamed > scheme > voluntary_delisting > end_failed"},
           "agreement_by_class": by, "agreement_by_class_excluding_2011_key_switch": by_ex,
           "agreement_overall": {"cases": int(len(j)), "class": int(j["agree"].sum()), "treatment": int(j["agree_treatment"].sum()),
                                 "excluding_2011_key_switch": {"cases": int(len(excl)), "class": int(excl["agree"].sum()), "treatment": int(excl["agree_treatment"].sum())}},
           "disagreements": dis.to_dict("records"), "flags": flags,
           "evidence_file": {"path": str(EVIDENCE.relative_to(HERE.parent)), "sha256": hashlib.sha256(EVIDENCE.read_bytes()).hexdigest()},
           "seconds": round(time.time() - t0, 1)}
    (paths.manifest_dir() / "sp3_prep_stops.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    if a[:2] == ["prep", "coverage"]:
        o = coverage()
        for r in o["sources"]:
            print(f"{r['verdict']:4s}  {r.get('share_present', 0):7.2%}  gap {str(r.get('longest_gap', '-')):>3s}  {r['source']}")
        print("struck families:", o["struck_families"], " struck features:", o["struck_features"], " FATAL:", o["fatal"])
    elif a[:2] == ["prep", "counts"]:
        o = prep_counts()
        tab = pd.DataFrame(o["rows_after_spacing_before_priority"]).T.fillna(0).astype(int)
        print(tab.to_string(), flush=True)
        print({k: o[k] for k in ("distinct_real_family_stock_days", "ctl_rows", "any_eligible", "non_any_rows", "any_rate", "any_rate_unrounded", "any_rows", "total_rows", "commit")})
        print(json.dumps(o["diagnostics"], indent=1, default=str))
    elif a[:2] == ["prep", "stops"]:
        o = prep_stops()
        print({k: o[k] for k in ("cases", "counts_by_class", "counts_by_class_excluding_2011_key_switch", "settled_by", "csv_sha256", "agreement_overall", "commit")})
        print(json.dumps(o["agreement_by_class_excluding_2011_key_switch"], indent=1))
    else:
        print(__doc__)
