"""The sealed loader: the only code allowed to read rows dated 2024-01-01 or later.

A reader names its purpose; the request is checked against the purposes allowed below and written to manifests/sealed_access.jsonl (who, why,
what window, how many rows) before any row is returned. Nothing here lets a study score a rule on the holdout. Allowed purposes:
  paper_lookback  the live paper engine's last few hundred sessions, to compute indicators (200-day average, 14-day range) for a signal on today's close
  paper_context   the engine's market context (Nifty 50 and India VIX against their averages) recorded with each decision; also the indices' latest
                  P/E, P/B and dividend yield for the market context (read_valuation, 27 Oct 2026)
  forecast_score  index closes after a forecast's horizon, to score forecasts written beforehand in paper/forecasts.jsonl (no rule scored)
  technicals_history  the DATES of the indices' 50/200 and 20/50 moving-average crosses since 2015, for the technicals panel (Madhav, 26 Oct
                  2026); only the event list is returned (index_cross_dates), no price or return
  integrity       selected columns for data checks (duplicates, mappings, stale files, calendar coverage); no returns are computed
  manifest        row counts, last date and file fingerprints for the dataset-version manifest
  calibration     settlement IVs of recorded days, to measure how far the synthetic option prices are from the recorder's real ones (R01); no rule is scored
  coverage        presence only, from the download manifests (no data file is read): the sessions a source was fetched for (SP3 coverage rule)
  holdout         the ONE registered confirmatory run of a frozen study (HOLDOUT_RUNS): opened once, after Madhav's approval, with a fixed window and
                  a fixed folder list; every query is logged; once the run is marked completed it can never be opened again
  paper_model / paper_parity   after a run is completed: its own derived tables, to fit the live model the spec prescribes and to check the
                  live paper code against the run's rows (holdout_outputs); the verdicts are already in the ledger and cannot change
  paper_review    live paper days only (Madhav, 20 Oct 2026): cash-market series-EQ rows dated on or after PAPER_REVIEW_START (the stock paper's
                  first decision day), for the missed-movers review of the paper book (india/missed.py, the only caller india/leakcheck.py allows,
                  with a constant start). An earlier start is refused, never clipped; nothing on history is computed from these rows
  account_marks   one live session's closes for the stocks the account's paper twin holds, only when the Zerodha snapshot is older than that
                  session (Madhav, 25 Oct 2026); india/account.py is the only caller
  sz2_selection   the SZ2 sizing selection (Madhav, 23 Oct 2026, SZ2 decision (a)): the completed SP1 holdout run's own policy trades
                  2024-01-01..2026-10-16 and, to price them as sz2_v1.json prescribes, their previous-session chains, their index minutes and the
                  16 Oct 2026 index closes (read_sz2); no SP1 rule is scored
Apart from a registered holdout run, none of them computes rule performance. A lookback or context request for more than LOOKBACK_DAYS calendar days is refused.

  from india import sealed
  df = sealed.read_cm("paper_lookback", since="2025-09-01")      raw series-EQ cash rows from sealed/silver + silver
Test: tests grep the repo for direct reads of the sealed folder outside this file (see india/leakcheck.py).
"""
from __future__ import annotations

import datetime as dt
import json

from pathlib import Path

import duckdb
import pandas as pd

from india import paths

ALLOWED = {"paper_lookback"}
LOOKBACK_DAYS = 460


def _log(purpose: str, what: str, since: str, rows: int) -> None:
    line = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "purpose": purpose, "what": what, "since": since, "rows": rows}
    with (paths.manifest_dir() / "sealed_access.jsonl").open("a") as fh:
        fh.write(json.dumps(line) + "\n")


def read_cm(purpose: str, since: str) -> pd.DataFrame:
    if purpose not in ALLOWED:
        raise PermissionError(f"sealed read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED)}")
    since_d = pd.Timestamp(since).date()
    if (dt.date.today() - since_d).days > LOOKBACK_DAYS:
        raise PermissionError(f"sealed read refused: window of {(dt.date.today() - since_d).days} days exceeds {LOOKBACK_DAYS}")
    root = paths.data_dir()
    files = [str(p) for p in list((root / "silver/cm_bhavcopy").glob("year=*/part.parquet")) + list((root / "sealed/silver/cm_bhavcopy").glob("year=*/part.parquet"))]
    con = duckdb.connect()
    df = con.execute(
        f"select date, symbol, series, open, high, low, close, prev_close, volume, turnover, isin from read_parquet({files!r}) where series = 'EQ' and close > 0 and date >= ?",
        [since_d]).df()
    con.close()
    _log(purpose, "cm_bhavcopy EQ", since, len(df))
    return df


def read_index(purpose: str, since: str, names: list[str]) -> pd.DataFrame:
    """Daily index closes for the paper engine's market context (Nifty against its averages, VIX). Same rules as read_cm; purpose paper_context."""
    if purpose not in ALLOWED_CONTEXT:
        raise PermissionError(f"sealed index read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_CONTEXT)}")
    since_d = pd.Timestamp(since).date()
    if (dt.date.today() - since_d).days > LOOKBACK_DAYS:
        raise PermissionError(f"sealed read refused: window of {(dt.date.today() - since_d).days} days exceeds {LOOKBACK_DAYS}")
    root = paths.data_dir()
    files = [str(p) for p in (root / "silver/kite_index/day/day.parquet", root / "sealed/silver/kite_index/day/day.parquet") if p.exists()]
    con = duckdb.connect()
    # 26 Oct: the open too, so the market context can say how far the index opened from the previous close (the gap)
    df = con.execute(f"select index_name, date, open, close from read_parquet({files!r}, union_by_name=true) where date >= ? and list_contains(?, index_name)", [since_d, names]).df()
    con.close()
    _log(purpose, "kite_index day " + ",".join(names), since, len(df))
    return df.drop_duplicates(["index_name", "date"], keep="last")


ALLOWED_CONTEXT = {"paper_context", "forecast_score"}


def read_valuation(purpose: str, since: str, names: list[str]) -> pd.DataFrame:
    """The indices' daily P/E, P/B and dividend yield (NSE) for the market context (27 Oct, Madhav's yes): same rules as read_index (purpose
    paper_context, at most LOOKBACK_DAYS back), logged. Nothing is scored from these rows; the long-run comparison uses the pre-2024 file only."""
    if purpose not in ALLOWED_CONTEXT:
        raise PermissionError(f"sealed valuation read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_CONTEXT)}")
    since_d = pd.Timestamp(since).date()
    if (dt.date.today() - since_d).days > LOOKBACK_DAYS:
        raise PermissionError(f"sealed read refused: window of {(dt.date.today() - since_d).days} days exceeds {LOOKBACK_DAYS}")
    root = paths.data_dir()
    files = [str(p) for p in (root / "silver/valuation/index_pepb.parquet", root / "sealed/silver/valuation/index_pepb.parquet") if p.exists()]
    if not files:
        return pd.DataFrame(columns=["index_name", "date", "pe", "pb", "div_yield", "pe_basis"])
    con = duckdb.connect()
    df = con.execute(f"select index_name, date, pe, pb, div_yield, pe_basis from read_parquet({files!r}, union_by_name=true) where date >= ? and list_contains(?, index_name)",
                     [since_d, names]).df()
    con.close()
    _log(purpose, "valuation index_pepb " + ",".join(names), since, len(df))
    return df.drop_duplicates(["index_name", "date"], keep="last")


ALLOWED_CROSSES = {"technicals_history"}
CROSS_PAIRS = ((50, 200), (20, 50))


def index_cross_dates(purpose: str, names: list[str], since: str = "2015-01-01") -> list[dict]:
    """The dates of moving-average crosses (50/200 and 20/50 on daily closes) of the named indices since `since` (Madhav, 26 Oct 2026: "when did
    the 50-day last cross the 200-day?"; the paper_context window of LOOKBACK_DAYS is too short for a 200-day average to see it). Purpose
    technicals_history; logged. Only the event list leaves this function (index, date, pair, direction): no price, no return, no rule
    performance is returned or computed."""
    if purpose not in ALLOWED_CROSSES:
        raise PermissionError(f"sealed cross read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_CROSSES)}")
    root = paths.data_dir()
    files = [str(p) for p in (root / "silver/kite_index/day/day.parquet", root / "sealed/silver/kite_index/day/day.parquet") if p.exists()]
    if not files:
        return []
    con = duckdb.connect()
    df = con.execute(f"select index_name, date, close from read_parquet({files!r}, union_by_name=true) where date >= ? and list_contains(?, index_name)",
                     [pd.Timestamp(since).date(), names]).df()
    con.close()
    df = df.drop_duplicates(["index_name", "date"], keep="last").sort_values(["index_name", "date"])
    out = []
    for name, g in df.groupby("index_name"):
        c = g["close"].astype(float).reset_index(drop=True)
        dates = list(g["date"])
        for f, s in CROSS_PAIRS:
            diff = (c.rolling(f).mean() - c.rolling(s).mean())
            sign = diff.apply(lambda x: 0 if x != x else (1 if x > 0 else -1))
            for i in range(1, len(sign)):
                if sign[i] and sign[i - 1] and sign[i] != sign[i - 1]:
                    out.append({"index_name": name, "date": str(pd.Timestamp(dates[i]).date()), "pair": f"{f}/{s}", "direction": "up" if sign[i] > 0 else "down",
                                "sessions_ago": int(len(sign) - 1 - i)})
    _log(purpose, "kite_index day cross dates only " + ",".join(names), since, len(out))
    return out

PAPER_REVIEW_START = dt.date(2026, 10, 16)   # the stock paper's first decision (data of Fri 16 Oct 2026); no review row is older
ALLOWED_REVIEW = {"paper_review"}


def read_review(purpose: str, since: str, until: str | None = None) -> pd.DataFrame:
    """Live paper days for the missed-movers review (purpose paper_review): raw series-EQ cash rows dated since..until, where since must be on or
    after PAPER_REVIEW_START. Every check runs before any file is opened; a start before the paper's first day is refused, not clipped. The caller
    computes nothing on history from these rows (its universe and indicators come from the paper engine's own decision-time files). Logged."""
    if purpose not in ALLOWED_REVIEW:
        raise PermissionError(f"sealed review read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_REVIEW)}")
    since_d = pd.Timestamp(since).date()
    if since_d < PAPER_REVIEW_START:
        raise PermissionError(f"sealed review read refused: start {since_d} is before the paper's first day {PAPER_REVIEW_START} (live paper days only)")
    until_d = pd.Timestamp(until).date() if until else None
    if until_d is not None and until_d < since_d:
        raise PermissionError(f"sealed review read refused: end {until_d} is before start {since_d}")
    root = paths.data_dir()
    files = [str(p) for p in list((root / "silver/cm_bhavcopy").glob("year=*/part.parquet")) + list((root / "sealed/silver/cm_bhavcopy").glob("year=*/part.parquet"))
             if int(p.parent.name.split("=")[1]) >= PAPER_REVIEW_START.year]
    if not files:
        _log(purpose, "cm_bhavcopy EQ live paper days (no files)", f"{since_d}..{until_d or ''}", 0)
        return pd.DataFrame(columns=["date", "symbol", "series", "open", "high", "low", "close", "prev_close", "volume", "turnover", "isin"])
    con = duckdb.connect()
    sql = ("select date, symbol, series, open, high, low, close, prev_close, volume, turnover, isin from read_parquet(" + repr(files)
           + ", union_by_name=true) where series = 'EQ' and close > 0 and cast(date as date) >= ?" + (" and cast(date as date) <= ?" if until_d else ""))
    df = con.execute(sql, [since_d] + ([until_d] if until_d else [])).df()
    con.close()
    if len(df) and pd.to_datetime(df["date"]).min().date() < PAPER_REVIEW_START:   # never reached: the query bounds it; kept as the second lock
        raise PermissionError("sealed review read refused: a row before the paper's first day came back")
    _log(purpose, "cm_bhavcopy EQ live paper days", f"{since_d}..{until_d or ''}", len(df))
    return df


ALLOWED_OTHERS = {"others_review"}


def read_others(purpose: str, since: str, until: str | None = None) -> dict:
    """Live paper days for the reference-traders review (purpose others_review, Madhav 22 Oct 2026; india/others.py is the only caller
    india/leakcheck.py allows, with a constant start on or after PAPER_REVIEW_START): the same cash rows read_review gives, plus the
    participant-wise open-interest rows (FII, DII, Pro, Client: index and stock futures and options, long and short contracts) dated
    since..until. The hindsight, informed and random reference traders are built from live sessions only; nothing on history is computed
    from these rows and no rule is scored. Logged."""
    if purpose not in ALLOWED_OTHERS:
        raise PermissionError(f"sealed others read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_OTHERS)}")
    since_d = pd.Timestamp(since).date()
    if since_d < PAPER_REVIEW_START:
        raise PermissionError(f"sealed others read refused: start {since_d} is before the paper's first day {PAPER_REVIEW_START} (live paper days only)")
    until_d = pd.Timestamp(until).date() if until else None
    if until_d is not None and until_d < since_d:
        raise PermissionError(f"sealed others read refused: end {until_d} is before start {since_d}")
    cash = _live_cash(purpose, since_d, until_d)
    root = paths.data_dir()
    files = [str(p) for p in [root / "silver/flows/participant_oi.parquet", root / "sealed/silver/flows/participant_oi.parquet"] if p.exists()]
    cols = ["date", "client_type", "future_index_long", "future_index_short", "future_stock_long", "future_stock_short", "option_index_call_long",
            "option_index_put_long", "option_index_call_short", "option_index_put_short", "total_long_contracts", "total_short_contracts"]
    if not files:
        oi = pd.DataFrame(columns=cols)
    else:
        con = duckdb.connect()
        sql = ("select " + ", ".join(cols) + " from read_parquet(" + repr(files) + ", union_by_name=true) where cast(date as date) >= ?"
               + (" and cast(date as date) <= ?" if until_d else "") + " order by date, client_type")
        oi = con.execute(sql, [since_d] + ([until_d] if until_d else [])).df()
        con.close()
    if len(oi) and pd.to_datetime(oi["date"]).min().date() < PAPER_REVIEW_START:
        raise PermissionError("sealed others read refused: a participant row before the paper's first day came back")
    _log(purpose, "participant_oi live paper days", f"{since_d}..{until_d or ''}", len(oi))
    return {"cash": cash, "oi": oi}


ALLOWED_SHADOW = {"shadow_score"}


def read_shadow(purpose: str, since: str, until: str | None = None) -> pd.DataFrame:
    """Live paper days for the shadow trader's scoring (purpose shadow_score, Madhav 30 Oct 2026: one-yes list item 3; india/shadow.py is the
    only caller india/leakcheck.py allows, with a constant start on or after PAPER_REVIEW_START): symbol, date and close of the cash rows
    since..until. The shadow's watch names are compared with the universe on live sessions only; nothing on history and no rule is scored. Logged."""
    if purpose not in ALLOWED_SHADOW:
        raise PermissionError(f"sealed shadow read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_SHADOW)}")
    since_d = pd.Timestamp(since).date()
    if since_d < PAPER_REVIEW_START:
        raise PermissionError(f"sealed shadow read refused: start {since_d} is before the paper's first day {PAPER_REVIEW_START} (live paper days only)")
    until_d = pd.Timestamp(until).date() if until else None
    if until_d is not None and until_d < since_d:
        raise PermissionError(f"sealed shadow read refused: end {until_d} is before start {since_d}")
    return _live_cash(purpose, since_d, until_d)[["symbol", "date", "close"]]


def _live_cash(purpose: str, since_d: dt.date, until_d: dt.date | None) -> pd.DataFrame:
    """The cash rows of live paper days (series EQ), shared by read_review and read_others; the callers have already checked the window."""
    root = paths.data_dir()
    files = [str(p) for p in list((root / "silver/cm_bhavcopy").glob("year=*/part.parquet")) + list((root / "sealed/silver/cm_bhavcopy").glob("year=*/part.parquet"))
             if int(p.parent.name.split("=")[1]) >= PAPER_REVIEW_START.year]
    if not files:
        _log(purpose, "cm_bhavcopy EQ live paper days (no files)", f"{since_d}..{until_d or ''}", 0)
        return pd.DataFrame(columns=["date", "symbol", "series", "open", "high", "low", "close", "prev_close", "volume", "turnover", "isin"])
    con = duckdb.connect()
    sql = ("select date, symbol, series, open, high, low, close, prev_close, volume, turnover, isin from read_parquet(" + repr(files)
           + ", union_by_name=true) where series = 'EQ' and close > 0 and cast(date as date) >= ?" + (" and cast(date as date) <= ?" if until_d else ""))
    df = con.execute(sql, [since_d] + ([until_d] if until_d else [])).df()
    con.close()
    if len(df) and pd.to_datetime(df["date"]).min().date() < PAPER_REVIEW_START:   # never reached: the query bounds it; kept as the second lock
        raise PermissionError("sealed review read refused: a row before the paper's first day came back")
    _log(purpose, "cm_bhavcopy EQ live paper days", f"{since_d}..{until_d or ''}", len(df))
    return df


ALLOWED_MARKS = {"account_marks"}


def read_marks(purpose: str, day: str, symbols: list[str]) -> pd.DataFrame:
    """Closing prices of ONE live session for the stocks the paper twin of the account holds (purpose account_marks, Madhav 25 Oct 2026: "fix
    all items"): used only when the daily Zerodha snapshot is older than the last completed session, so the twin is not marked at stale prices.
    The day must be a live paper day (on or after PAPER_REVIEW_START, not in the future); only series-EQ closes of the named symbols on that
    day come back; nothing is scored. india/account.py is the only caller (tests/test_india_account_marks.py). Logged."""
    if purpose not in ALLOWED_MARKS:
        raise PermissionError(f"sealed marks read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_MARKS)}")
    d = pd.Timestamp(day).date()
    if d < PAPER_REVIEW_START or d > dt.date.today():
        raise PermissionError(f"sealed marks read refused: {d} is not a live paper day")
    syms = sorted({str(s) for s in symbols if s})
    root = paths.data_dir()
    files = [str(p) for p in list((root / "silver/cm_bhavcopy").glob(f"year={d.year}/part.parquet")) + list((root / "sealed/silver/cm_bhavcopy").glob(f"year={d.year}/part.parquet"))]
    if not files or not syms:
        _log(purpose, "cm_bhavcopy EQ closes (nothing to read)", str(d), 0)
        return pd.DataFrame(columns=["symbol", "close"])
    con = duckdb.connect()
    df = con.execute("select symbol, close from read_parquet(" + repr(files) + ", union_by_name=true) where series = 'EQ' and close > 0 "
                     "and cast(date as date) = ? and list_contains(?, symbol)", [d, syms]).df()
    con.close()
    _log(purpose, f"cm_bhavcopy EQ closes of {len(syms)} held stocks", str(d), len(df))
    return df.drop_duplicates("symbol", keep="last")


ALLOWED_CHAIN = {"chain_brief"}


def read_chain(purpose: str, day: str, symbols: list[str] | None = None) -> pd.DataFrame:
    """The index option chain of ONE live session for the pre-market brief (purpose chain_brief, 30 Oct 2026, Phase 4.1): strike, type, expiry,
    close, open interest and volume of NIFTY and BANKNIFTY options on that day, read from the F&O file (sealed since 2024). The day must be a
    live paper day (on or after PAPER_REVIEW_START, not in the future); the brief computes the put-call ratio, max pain and the biggest
    open-interest strikes of the nearest expiry and scores nothing. india/premarket.py is the only caller. Logged."""
    if purpose not in ALLOWED_CHAIN:
        raise PermissionError(f"sealed chain read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_CHAIN)}")
    d = pd.Timestamp(day).date()
    if d < PAPER_REVIEW_START or d > dt.date.today():
        raise PermissionError(f"sealed chain read refused: {d} is not a live paper day")
    syms = sorted(symbols or ["NIFTY", "BANKNIFTY"])
    root = paths.data_dir()
    files = [str(p) for p in list((root / "silver/fo_bhavcopy").glob(f"year={d.year}/part.parquet")) + list((root / "sealed/silver/fo_bhavcopy").glob(f"year={d.year}/part.parquet"))]
    if not files:
        _log(purpose, "fo_bhavcopy OPTIDX chain (no files)", str(d), 0)
        return pd.DataFrame(columns=["symbol", "expiry", "strike", "opt_type", "close", "open_interest", "volume", "underlying"])
    con = duckdb.connect()
    df = con.execute("select symbol, expiry, strike, opt_type, close, open_interest, volume, underlying from read_parquet(" + repr(files) + ", union_by_name=true) "
                     "where instrument = 'OPTIDX' and cast(date as date) = ? and list_contains(?, symbol)", [d, syms]).df()
    con.close()
    _log(purpose, f"fo_bhavcopy OPTIDX chain of {len(syms)} indices", str(d), len(df))
    return df


ALLOWED_SZ2 = {"sz2_selection"}
SZ2_WINDOW = ("2024-01-01", "2026-10-16")
SZ2_APPROVAL = ("Madhav, 23 Oct 2026 (docs/INDIA_LOCK.md, SZ2 decision (a)): 'yes, logged': a logged sealed purpose for the completed SP1 holdout "
                "run's own policy_trades 2024-26; the SZ2 selection may then run as the spec (registrations/sz2_v1.json) wrote it")


def read_sz2(purpose: str, what: str, days: list | None = None) -> pd.DataFrame:
    """The SZ2 sizing selection (purpose sz2_selection; SZ2_APPROVAL), after the SP1 holdout run is COMPLETED (its verdicts are in the ledger
    and cannot change). what:
      policy_trades   that run's own policy trades, 2024-01-01..2026-10-16 (the spec's selection window: inputs.decisions)
      chains          the previous-session option chains of those trades (fo_greeks: strike, type, forward, IV, settle, volume), only on `days`
      index_minutes   the index minute bars (NIFTY 50, NIFTY BANK) on `days` (the trade days and their next sessions), for the minute marks
      scale_close     the NIFTY 50 and NIFTY BANK closes of 2026-10-16 (contracts.lots_and_scale: 'index at the 16 Oct 2026 close')
    Rows outside SZ2_WINDOW are never returned. Nothing here scores an SP1 rule; the sizing never changes which decision is made. Logged."""
    if purpose not in ALLOWED_SZ2:
        raise PermissionError(f"sealed SZ2 read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_SZ2)}")
    if not any(r["run"] == "sp1_holdout" and r["status"] == "completed" for r in _runs()):
        raise PermissionError("sealed SZ2 read refused: the sp1_holdout run is not completed")
    lo, hi = (pd.Timestamp(x).date() for x in SZ2_WINDOW)
    root = paths.data_dir()
    con = duckdb.connect()
    try:
        if what == "policy_trades":
            df = pd.read_parquet(root / "sealed" / "gold" / "sp1_holdout" / "policy_trades.parquet")
            d = pd.to_datetime(df["date"]).dt.date
            df = df[(d >= lo) & (d <= hi)].reset_index(drop=True)
        elif what in ("chains", "index_minutes"):
            ds = sorted({pd.Timestamp(x).date() for x in (days or [])})
            ds = [x for x in ds if lo - dt.timedelta(days=10) <= x <= hi]   # a 2024-01-01 trade's previous session is in silver (2023)
            if not ds:
                return pd.DataFrame()
            if what == "chains":
                files = [str(p) for p in list((root / "sealed/silver/fo_greeks").glob("year=*/part.parquet")) + list((root / "silver/fo_greeks").glob("year=2023/part.parquet"))]
                sql = ("select date, symbol, expiry, strike, opt_type, fwd, iv, settle, coalesce(volume, 0) as volume from read_parquet(" + repr(files)
                       + ", union_by_name=true) where symbol in ('NIFTY', 'BANKNIFTY') and list_contains(?, cast(date as date))")
            else:
                files = [str(p) for p in list((root / "sealed/silver/kite_index/minute").glob("**/*.parquet")) + list((root / "silver/kite_index/minute").glob("year=2023/*.parquet"))]
                sql = ("select index_name, date, (hour(ts) * 60 + minute(ts) - 555) as m, open, high, low, close from read_parquet(" + repr(files)
                       + ", union_by_name=true) where index_name in ('NIFTY 50', 'NIFTY BANK') and list_contains(?, cast(date as date))")
            df = con.execute(sql, [ds]).df()
        elif what == "scale_close":
            files = [str(p) for p in (root / "sealed/silver/kite_index/day").glob("**/*.parquet")]
            df = con.execute("select index_name, cast(date as date) as date, close from read_parquet(" + repr(files) + ", union_by_name=true) "
                             "where index_name in ('NIFTY 50', 'NIFTY BANK') and cast(date as date) = ?", [hi]).df()
        else:
            raise PermissionError(f"sealed SZ2 read refused: unknown item {what!r}")
    finally:
        con.close()
    _log(purpose, f"sz2 {what}" + (f" on {len(days)} days" if days else ""), SZ2_WINDOW[0], len(df))
    return df


def sz2_output_dir(purpose: str) -> Path:
    """Where the SZ2 selection keeps its holdout-era derived tables (trades x structures, per-session paths): inside the sealed tree, so no
    research table outside it carries a 2024+ row. Purpose sz2_selection only; logged."""
    if purpose not in ALLOWED_SZ2:
        raise PermissionError(f"SZ2 outputs refused: purpose {purpose!r}")
    p = paths.data_dir() / "sealed" / "gold" / "sz2"
    p.mkdir(parents=True, exist_ok=True)
    _log(purpose, "sz2 derived tables (sealed/gold/sz2)", SZ2_WINDOW[0], 0)
    return p


ALLOWED_INTEGRITY = {"integrity", "calibration"}


def read_cols(purpose: str, folder: str, cols: list[str], since: str, where: str = "") -> pd.DataFrame:
    """Selected columns of a sealed silver dataset for data-integrity checks (duplicates, mappings, stale files, calendar). Purpose integrity; logged.
    The integrity checks compute no returns and no rule performance from these rows."""
    if purpose not in ALLOWED_INTEGRITY:
        raise PermissionError(f"sealed column read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_INTEGRITY)}")
    base = paths.data_dir() / "sealed" / folder
    files = [str(p) for p in sorted(base.glob("**/*.parquet"))]
    if not files:
        return pd.DataFrame(columns=cols)
    con = duckdb.connect()
    df = con.execute(f"select {', '.join(cols)} from read_parquet({files!r}, union_by_name=true) where date >= ? {('and ' + where) if where else ''}", [pd.Timestamp(since).date()]).df()
    con.close()
    _log(purpose, f"{folder} cols {','.join(cols)}", since, len(df))
    return df


def metadata(folder: str, pattern: str, datecol: str | None) -> dict:
    """Row count, last date and a file fingerprint of the sealed copy of a silver dataset, for the dataset manifest. Reads the date column only, no prices."""
    import hashlib

    base = paths.data_dir() / "sealed" / folder
    files = sorted(p for p in base.glob(pattern) if p.is_file()) if base.exists() else []
    if not files:
        return {"files": 0}
    h = hashlib.sha256()
    for p in files:
        st = p.stat()
        h.update(f"{p.relative_to(paths.data_dir())}|{st.st_size}|{st.st_mtime_ns}\n".encode())
    out = {"files": len(files), "fingerprint": h.hexdigest()[:16]}
    pq = [str(p) for p in files if p.suffix == ".parquet"]
    if pq:
        con = duckdb.connect()
        if datecol:
            r = con.execute(f"select count(*), max({datecol}) from read_parquet({pq!r}, union_by_name=true)").fetchone()
            out.update({"rows": int(r[0]), "last": str(r[1])[:10] if r[1] is not None else None})
        else:
            out["rows"] = int(con.execute(f"select count(*) from read_parquet({pq!r}, union_by_name=true)").fetchone()[0])
        con.close()
    _log("manifest", f"metadata {folder}", "-", out.get("rows") or 0)
    return out


def coverage(manifest: str, since: str = "2024-01-01", until: str = "2026-09-30", match: dict | None = None) -> list[str]:
    """PRESENCE ONLY (SP3 coverage rule, 20 Oct 2026; manifest-based after the third review): the trading sessions between since and until that
    a source's DOWNLOAD MANIFEST (manifests/<manifest>.jsonl) shows as fetched with status 200 (or 'ok'). A daily entry ('date') covers its
    session; a windowed query ('from'/'to', 'start'/'end') covers every session inside the window, so a quiet day of a sparse source (results,
    board meetings) still counts as present; a yearly entry ('year') covers that year's sessions. match filters entries (e.g. {'symbol':
    'NIFTY 50'}). It reads no data file at all, sealed or not, and returns no counts or values. Logged under purpose coverage."""
    cal = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
    lo, hi = pd.Timestamp(since).date(), pd.Timestamp(until).date()
    sessions = sorted(d for d in pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]).dt.date if lo <= d <= hi)
    f = paths.manifest_dir() / f"{manifest}.jsonl"
    present: set = set()
    if f.exists():
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("status") not in (200, "200", "ok") and not (e.get("status") is None and e.get("sha256")):
                continue  # a manifest without a status field (us_close) counts an entry only when it saved a file (sha256)
            if match and any(e.get(k) != v for k, v in match.items()):
                continue
            if e.get("date"):
                a = b = pd.Timestamp(e["date"]).date()
            elif e.get("from") or e.get("start"):
                a = pd.Timestamp(e.get("from") or e.get("start")).date()
                b = pd.Timestamp(e.get("to") or e.get("end") or a).date()
            elif e.get("year"):
                a, b = dt.date(int(e["year"]), 1, 1), dt.date(int(e["year"]), 12, 31)
            else:
                continue
            present.update(d for d in sessions if a <= d <= b)
    out = [str(d) for d in sessions if d in present]
    _log("coverage", f"manifest {manifest} sessions present{(' ' + json.dumps(match)) if match else ''}", since, len(out))
    return out


def coverage_summary(manifest: str, since: str = "2024-01-01", until: str = "2026-09-30", match: dict | None = None) -> dict:
    """The coverage rule's verdict for one source: share of sessions present, the longest run of missing sessions, PASS at >= 99% and no gap over 5."""
    cal = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
    lo, hi = pd.Timestamp(since).date(), pd.Timestamp(until).date()
    sessions = sorted(d for d in pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]).dt.date if lo <= d <= hi)
    have = set(coverage(manifest, since, until, match))
    gap = run = 0
    for d in sessions:
        run = 0 if str(d) in have else run + 1
        gap = max(gap, run)
    share = len(have) / len(sessions) if sessions else 0.0
    return {"manifest": manifest, "match": match, "sessions": len(sessions), "share_present": round(share, 4), "longest_gap": gap,
            "verdict": "PASS" if share >= 0.99 and gap <= 5 else "FAIL"}


# ----------------------------------------------------------------------------------------------------------------------------- holdout runs
HOLDOUT_RUNS = {
    "sp1_holdout": {"registration": "registrations/sp1_v2.json", "start": "2024-01-01", "end": "2026-10-16",
                    "approved": "Madhav, 19 Oct 2026 19:52 Toronto (chat: 'Yes' to opening the SP1 holdout)",
                    "folders": ["kite_index/minute", "kite_index/day", "cm_bhavcopy", "kite_5m", "flows", "fo_bhavcopy", "fo_greeks"]},
    # SP3 (registered at the freeze, 20 Oct 2026): opened once, only after Madhav approves the frozen policy's dev/validation results
    "sp3_holdout": {"registration": "registrations/sp3_v1.json", "start": "2024-01-01", "end": "2026-09-30", "approved": "",
                    "folders": ["cm_bhavcopy", "delivery", "kite_index/day", "flows", "fo_bhavcopy", "pr", "announce"]},
}
_OPEN: dict[str, dict] = {}


def _runs_log():
    return paths.manifest_dir() / "holdout_runs.jsonl"


def _runs() -> list[dict]:
    p = _runs_log()
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def holdout_open(run: str) -> dict:
    """Open a registered holdout run. Refused if the run is unknown, its registration is not frozen or has changed since approval would be checked by
    the caller's spec sha, or the run was already completed (a holdout is used once)."""
    import hashlib

    if run not in HOLDOUT_RUNS:
        raise PermissionError(f"holdout refused: {run!r} is not a registered holdout run")
    h = HOLDOUT_RUNS[run]
    if not h.get("approved"):
        raise PermissionError(f"holdout refused: {run} has no recorded approval from Madhav")
    reg = Path(__file__).parent / h["registration"]
    spec = json.loads(reg.read_text())
    if not str(spec.get("status", "")).startswith("FROZEN"):
        raise PermissionError(f"holdout refused: {h['registration']} is not frozen")
    if any(r["run"] == run and r["status"] == "completed" for r in _runs()):
        raise PermissionError(f"holdout refused: {run} was already completed; a holdout is opened once")
    sha = hashlib.sha256(reg.read_bytes()).hexdigest()[:16]
    prior = [r for r in _runs() if r["run"] == run]
    line = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "run": run, "status": "reopened" if prior else "opened",
            "registration": h["registration"], "sha": sha, "window": [h["start"], h["end"]], "approved": h["approved"]}
    with _runs_log().open("a") as fh:
        fh.write(json.dumps(line) + "\n")
    _log("holdout", f"{run} {line['status']}", h["start"], 0)
    ticket = {"run": run, "sha": sha, **h}
    _OPEN[run] = ticket
    return ticket


def holdout_query(ticket: dict, folder: str, select: str, where: str = "", params: list | None = None, group_by: str = "") -> pd.DataFrame:
    """Rows of one sealed silver folder inside the run's fixed window (the window is always enforced here), logged."""
    run = ticket.get("run")
    if _OPEN.get(run) is not ticket:
        raise PermissionError("holdout query refused: the run is not open in this process")
    if folder not in ticket["folders"]:
        raise PermissionError(f"holdout query refused: {folder} is not in the run's folder list")
    base = paths.data_dir() / "sealed" / "silver" / folder
    files = [str(p) for p in sorted(base.glob("**/*.parquet"))]
    if not files:
        return pd.DataFrame()
    sql = (f"select {select} from read_parquet({files!r}, union_by_name=true) where cast(date as date) >= ? and cast(date as date) <= ?"
           + (f" and ({where})" if where else "") + (f" group by {group_by}" if group_by else ""))
    con = duckdb.connect()
    con.execute("set threads to 6")
    df = con.execute(sql, [pd.Timestamp(ticket["start"]).date(), pd.Timestamp(ticket["end"]).date()] + list(params or [])).df()
    con.close()
    _log("holdout", f"{run} {folder}: {select[:60]}", ticket["start"], len(df))
    return df


def holdout_complete(ticket: dict, summary: dict) -> None:
    run = ticket["run"]
    with _runs_log().open("a") as fh:
        fh.write(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "run": run, "status": "completed",
                             "sha": ticket["sha"], "summary": summary}, default=str) + "\n")
    _OPEN.pop(run, None)


HOLDOUT_OUTPUT_PURPOSES = {
    "paper_model": "fit the live model the frozen spec prescribes for the current year (refit on all earlier years), with its parity check",
    "paper_parity": "compare the live paper code's state rows and decisions on past sessions with the completed run's own rows (no new score)",
}


def holdout_outputs(run: str, purpose: str) -> Path:
    """After a holdout run is COMPLETED (its verdicts are in the ledger and can never change), its own derived tables (situation states,
    outcomes, policy trades) may be read for the purposes above only. Logged; refused before completion."""
    if purpose not in HOLDOUT_OUTPUT_PURPOSES:
        raise PermissionError(f"holdout outputs refused: purpose {purpose!r}")
    if not any(r["run"] == run and r["status"] == "completed" for r in _runs()):
        raise PermissionError(f"holdout outputs refused: {run} is not completed")
    _log(purpose, f"{run} outputs (states, outcomes, trades): {HOLDOUT_OUTPUT_PURPOSES[purpose]}", "-", 0)
    return paths.data_dir() / "sealed" / "gold" / run


def read_flows(purpose: str, since: str) -> pd.DataFrame:
    """Participant-wise OI rows (silver + sealed) for the live paper engine's positioning feature; same rules as read_cm (paper_lookback, LOOKBACK_DAYS)."""
    if purpose not in ALLOWED:
        raise PermissionError(f"sealed read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED)}")
    since_d = pd.Timestamp(since).date()
    if (dt.date.today() - since_d).days > LOOKBACK_DAYS:
        raise PermissionError(f"sealed read refused: window of {(dt.date.today() - since_d).days} days exceeds {LOOKBACK_DAYS}")
    root = paths.data_dir()
    parts = []
    for p in (root / "silver/flows/participant_oi.parquet", root / "sealed/silver/flows/participant_oi.parquet"):
        if p.exists():
            parts.append(pd.read_parquet(p))
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(df):
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[df["date"] >= since_d]
    _log(purpose, "flows participant_oi", since, len(df))
    return df
