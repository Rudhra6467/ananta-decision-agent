"""G5 persist — append reconstructable snapshots to agent_decisions.sqlite.

Not App Mongo. Not research-db. Does not TAKE. Does not credit M2.
Does not backfill. Does not update old rows.
Local JSON next to the process is a copy, not the log.

last_bar_open is the last closed 1h bar. A forming bar is floored back one hour.
Fingerprint is never the stamp. Cycle seconds are never the stamp.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = "agent_decisions.sqlite"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    ts_utc TEXT NOT NULL,
    camera TEXT NOT NULL,
    instrument TEXT NOT NULL,
    timeframe TEXT,
    bar_tf TEXT NOT NULL,
    last_bar_open TEXT,
    understanding TEXT NOT NULL,
    decision TEXT NOT NULL,
    setup TEXT,
    evidence_ids_json TEXT NOT NULL,
    authority_level INTEGER NOT NULL DEFAULT 0,
    knowledge_maturity TEXT,
    source_ref TEXT,
    payload_json TEXT NOT NULL
)
"""


def decisions_db_path() -> Path:
    env = os.environ.get("ANANTA_DECISIONS_DB")
    if env:
        return Path(env)
    return Path(DEFAULT_DB)


def _ensure(con: sqlite3.Connection) -> None:
    con.execute(CREATE_SQL)


def _parse_utc(raw: Any) -> datetime | None:
    s = str(raw or "").strip()
    if not s or s in ("None", "null") or "|" in s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _floor_hour(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def closed_bar_open(funnel: dict[str, Any] | None, state: dict[str, Any] | None, ts: str) -> str:
    """ISO open of the last 1h bar whose close is at or before cycle time.

    If the candidate open is still forming, step back one hour.
    Never returns a fingerprint. Never returns raw cycle seconds.
    """
    funnel = funnel or {}
    state = state or {}
    opened = None
    for candidate in (
        funnel.get("last_closed_bar_open"),
        funnel.get("last_bar_open"),
        state.get("last_closed_bar_open"),
        state.get("last_bar_open"),
    ):
        opened = _parse_utc(candidate)
        if opened:
            break
    cycle = _parse_utc(ts) or _parse_utc(funnel.get("as_of_time") or funnel.get("ran_at"))
    if opened is not None:
        opened = _floor_hour(opened)
        if cycle is not None and opened + timedelta(hours=1) > cycle:
            opened = opened - timedelta(hours=1)
    elif cycle is None:
        return ""
    else:
        opened = _floor_hour(cycle)
        if opened + timedelta(hours=1) > cycle:
            opened = opened - timedelta(hours=1)
    return opened.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _agent_version() -> str:
    """Import inside the function. di_loop imports this module."""
    try:
        from src.intelligence.di_loop import VERSION
        return str(VERSION)
    except Exception:
        return "UNKNOWN"


def persist_snapshot(
    snapshot: dict[str, Any],
    *,
    funnel: dict[str, Any] | None = None,
    exit_plan: dict[str, Any] | None = None,
    counterfactual: dict[str, Any] | None = None,
    paper_book: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    from src.intelligence.cite_allowlist import apply_new_row

    path = Path(db_path) if db_path else decisions_db_path()
    state = (snapshot or {}).get("market_state") or {}
    issued = str((snapshot or {}).get("issued") or "NO_TRADE")
    if issued == "TAKE":
        issued = "NO_TRADE"
    ts = str((snapshot or {}).get("timestamp") or datetime.now(timezone.utc).isoformat())
    asset = str(state.get("asset") or "BOOK")
    asset_key = asset.upper().replace("/USD", "").split("/")[0].split("-")[0]
    tf = str((funnel or {}).get("bar_tf") or state.get("tf") or "unknown")
    cycle_id = str(
        state.get("cycle_id")
        or (funnel or {}).get("cycle_id")
        or (snapshot or {}).get("cycle_id")
        or ""
    )
    cid = cycle_id.replace("cyc_", "")[:20] if cycle_id and cycle_id != "unknown" else ts.replace(":", "").replace("-", "")[:15]
    rid = f"decision.g5.{asset_key.lower()}.{cid}"
    understanding = {
        "WATCH": "SETUP_PRESENT",
        "WAIT": "FORMING",
        "SHADOW_PAPER": "PRESENT",
        "NO_TRADE": "UNKNOWN",
        "UNKNOWN": "UNKNOWN",
    }.get(issued, "UNKNOWN")
    bar_open = closed_bar_open(funnel, state, ts)
    payload = {
        "snapshot": snapshot,
        "funnel": funnel,
        "exit_plan": exit_plan,
        "counterfactual": counterfactual,
        "paper_book": paper_book,
        "cycle_id": cycle_id or None,
        "cycle_ts": ts,
        "last_closed_bar_open": bar_open,
        "counts_for_m2": False,
        "counts_for_paper": False,
        "paper_take": False,
        "keep": False,
        "exec": False,
        "fills": 0,
        "backfill": False,
    }
    row = {
        "id": rid,
        "ts_utc": ts,
        "camera": "hands_cycle",
        "instrument": asset_key,
        "timeframe": tf,
        "bar_tf": tf,
        "last_bar_open": bar_open,
        "understanding": understanding,
        "decision": issued,
        "setup": (snapshot or {}).get("selected_strategy"),
        "evidence_ids_json": "[]",
        "authority_level": 0,
        "knowledge_maturity": "DOCUMENTED",
        "source_ref": cycle_id or "g5.snapshot.v1",
        "payload_json": "",
    }
    apply_new_row(row, payload, snapshot, agent_version=_agent_version())
    row["payload_json"] = json.dumps(payload, default=str)
    con = sqlite3.connect(str(path))
    try:
        _ensure(con)
        con.execute(
            """
            INSERT OR REPLACE INTO decisions (
                id, ts_utc, camera, instrument, timeframe, bar_tf, last_bar_open,
                understanding, decision, setup, evidence_ids_json, authority_level,
                knowledge_maturity, source_ref, payload_json
            ) VALUES (
                :id, :ts_utc, :camera, :instrument, :timeframe, :bar_tf, :last_bar_open,
                :understanding, :decision, :setup, :evidence_ids_json, :authority_level,
                :knowledge_maturity, :source_ref, :payload_json
            )
            """,
            row,
        )
        con.commit()
    finally:
        con.close()
    versions = payload.get("versions") or {}
    return {
        "saved": str(path),
        "id": rid,
        "decision": issued,
        "instrument": asset_key,
        "cycle_id": cycle_id or None,
        "last_bar_open": bar_open,
        "cite_filter_version": versions.get("cite_filter_version"),
        "backfill": False,
        "paper_take": False,
        "fills": 0,
    }
