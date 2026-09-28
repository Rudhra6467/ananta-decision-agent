"""Repair the running envelope path without replacing decision_store.py.

decision_store still strips TAKE. This correction rewrites only the decision
and paper receipt after that strip, and only for a valid paper-path receipt.
It does not touch bar_tf, last_bar_open, or evidence_ids.
A fixture fill is not a market trade.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.intelligence.paper_path import decide, issued_from_paper, record_paper_fill

UNTOUCHED = ("bar_tf", "last_bar_open", "evidence_ids_json", "timeframe")


def correct(out: dict[str, Any] | None, db_path: Path | None = None) -> dict[str, Any]:
    out = dict(out or {})
    state = dict(out.get("l2_state") or {})
    if str(state.get("id") or "").startswith("fixture.") or state.get("fixture") is True:
        state["source"] = "FIXTURE"
    elif not state.get("source") or str(state.get("source")).lower() == "observation":
        state["source"] = "LIVE"
    paper = decide(state)
    issued = issued_from_paper(paper)
    if issued != "TAKE":
        out["paper_path"] = {"issued": issued, "reason": paper.get("reason"), "paper_fill": False, "exec": False, "counts_for_m2": False}
        return out
    fill = record_paper_fill({**paper, "asset": state.get("asset")})
    out["issued"] = "TAKE"
    out["action"] = "TAKE"
    out["reason"] = paper.get("reason")
    out["best_id"] = paper.get("best_id")
    out["can_take"] = True
    out["paper_take"] = True
    out["keep"] = False
    out["exec"] = False
    out["live"] = False
    out["counts_for_m2"] = False
    out["authority_granted"] = False
    out["paper_book"] = fill
    out["evidence_class"] = paper.get("evidence_class")
    out["not_a_market_trade"] = paper.get("not_a_market_trade")
    out["paper_path"] = paper
    store = out.get("decision_store") or {}
    out["decision_store"] = {**store, **rewrite_persisted(store, paper, fill, db_path)}
    return out


def rewrite_persisted(store: dict[str, Any], paper: dict[str, Any], fill: dict[str, Any], db_path: Path | None = None) -> dict[str, Any]:
    rid = store.get("id")
    saved = db_path or store.get("saved")
    if not rid or not saved:
        return {"rewritten": False, "reason": "NO_ROW"}
    path = Path(saved)
    if not path.exists():
        return {"rewritten": False, "reason": "DB_MISSING"}
    if paper.get("source") == "FIXTURE" and path.name == "agent_decisions.sqlite":
        return {"rewritten": False, "reason": "FIXTURE_REFUSED_ON_LIVE_DB"}
    con = sqlite3.connect(str(path))
    try:
        before = con.execute("SELECT bar_tf, last_bar_open, evidence_ids_json, timeframe, payload_json FROM decisions WHERE id=?", (rid,)).fetchone()
        if not before:
            return {"rewritten": False, "reason": "ROW_MISSING"}
        bar_tf, last_bar_open, evidence_ids, timeframe, payload_json = before
        payload = json.loads(payload_json)
        payload["paper_book"] = fill
        payload["paper_take"] = True
        payload["exec"] = False
        payload["keep"] = False
        payload["counts_for_m2"] = False
        payload["counts_for_paper"] = True
        payload["fills"] = 1
        payload["evidence_class"] = paper.get("evidence_class")
        payload["not_a_market_trade"] = paper.get("not_a_market_trade")
        payload["authority_granted"] = False
        con.execute("UPDATE decisions SET decision=?, setup=?, payload_json=? WHERE id=?", ("TAKE", paper.get("best_id"), json.dumps(payload, default=str), rid))
        con.commit()
        after = con.execute("SELECT decision, bar_tf, last_bar_open, evidence_ids_json, timeframe FROM decisions WHERE id=?", (rid,)).fetchone()
    finally:
        con.close()
    untouched = after[1] == bar_tf and after[2] == last_bar_open and after[3] == evidence_ids and after[4] == timeframe
    return {"rewritten": after[0] == "TAKE" and untouched, "decision": after[0], "untouched": list(UNTOUCHED) if untouched else [], "saved": str(path), "id": rid}
