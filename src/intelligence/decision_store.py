"""G5 persist — append reconstructable snapshots to agent_decisions.sqlite.

Not App Mongo. Not research-db. Does not TAKE.
Local JSON next to the process is a copy, not the log.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
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


def persist_snapshot(
    snapshot: dict[str, Any],
    *,
    funnel: dict[str, Any] | None = None,
    exit_plan: dict[str, Any] | None = None,
    counterfactual: dict[str, Any] | None = None,
    paper_book: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    path = Path(db_path) if db_path else decisions_db_path()
    state = (snapshot or {}).get("market_state") or {}
    issued = str((snapshot or {}).get("issued") or "NO_TRADE")
    if issued == "TAKE":
        issued = "NO_TRADE"
    ts = str((snapshot or {}).get("timestamp") or datetime.now(timezone.utc).isoformat())
    asset = str(state.get("asset") or "BOOK")
    asset_key = asset.upper().replace("/USD", "").split("/")[0].split("-")[0]
    tf = str(state.get("tf") or "unknown")
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
    cited = list((snapshot or {}).get("cited") or (snapshot or {}).get("knowledge_ids") or [])
    payload = {
        "snapshot": snapshot,
        "funnel": funnel,
        "exit_plan": exit_plan,
        "counterfactual": counterfactual,
        "paper_book": paper_book,
        "cycle_id": cycle_id or None,
        "counts_for_m2": False,
        "counts_for_paper": False,
        "paper_take": False,
        "keep": False,
        "exec": False,
        "fills": 0,
    }
    row = {
        "id": rid,
        "ts_utc": ts,
        "camera": "hands_cycle",
        "instrument": asset_key,
        "timeframe": tf,
        "bar_tf": tf,
        "last_bar_open": str(state.get("fingerprint") or (funnel or {}).get("last_bar_open") or ""),
        "understanding": understanding,
        "decision": issued,
        "setup": (snapshot or {}).get("selected_strategy"),
        "evidence_ids_json": json.dumps(cited),
        "authority_level": 0,
        "knowledge_maturity": "DOCUMENTED",
        "source_ref": cycle_id or "g5.snapshot.v1",
        "payload_json": json.dumps(payload, default=str),
    }
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
    return {"saved": str(path), "id": rid, "decision": issued, "instrument": asset_key, "cycle_id": cycle_id or None, "paper_take": False, "fills": 0}
