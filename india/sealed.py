"""The sealed loader: the only code allowed to read rows dated 2024-01-01 or later.

A reader names its purpose; the request is checked against the purposes allowed below and written to manifests/sealed_access.jsonl (who, why,
what window, how many rows) before any row is returned. Nothing here lets a study score a rule on the holdout. Allowed purposes:
  paper_lookback  the live paper engine's last few hundred sessions, to compute indicators (200-day average, 14-day range) for a signal on today's close
  paper_context   the engine's market context (Nifty 50 and India VIX against their averages) recorded with each decision
  forecast_score  index closes after a forecast's horizon, to score forecasts written beforehand in paper/forecasts.jsonl (no rule scored)
  integrity       selected columns for data checks (duplicates, mappings, stale files, calendar coverage); no returns are computed
  manifest        row counts, last date and file fingerprints for the dataset-version manifest
  calibration     settlement IVs of recorded days, to measure how far the synthetic option prices are from the recorder's real ones (R01); no rule is scored
  holdout         the ONE registered confirmatory run of a frozen study (HOLDOUT_RUNS): opened once, after Madhav's approval, with a fixed window and
                  a fixed folder list; every query is logged; once the run is marked completed it can never be opened again
  paper_model / paper_parity   after a run is completed: its own derived tables, to fit the live model the spec prescribes and to check the
                  live paper code against the run's rows (holdout_outputs); the verdicts are already in the ledger and cannot change
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
    df = con.execute(f"select index_name, date, close from read_parquet({files!r}, union_by_name=true) where date >= ? and list_contains(?, index_name)", [since_d, names]).df()
    con.close()
    _log(purpose, "kite_index day " + ",".join(names), since, len(df))
    return df.drop_duplicates(["index_name", "date"], keep="last")


ALLOWED_CONTEXT = {"paper_context", "forecast_score"}


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


# ----------------------------------------------------------------------------------------------------------------------------- holdout runs
HOLDOUT_RUNS = {
    "sp1_holdout": {"registration": "registrations/sp1_v2.json", "start": "2024-01-01", "end": "2026-10-16",
                    "approved": "Madhav, 19 Oct 2026 19:52 Toronto (chat: 'Yes' to opening the SP1 holdout)",
                    "folders": ["kite_index/minute", "kite_index/day", "cm_bhavcopy", "kite_5m", "flows", "fo_bhavcopy", "fo_greeks"]},
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
