"""Qualifying setup through the production decision functions.

This is not a Hands POST and not a market trade.
It uses the same functions the laptop envelope uses:
observation_from_result -> di_loop.run -> paper_path_wire.correct.
The fixture id keeps the fill labeled FIXTURE. It refuses the live sqlite.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from src.intelligence.cycle_ingest import observation_from_result
from src.intelligence.di_loop import run
from src.intelligence.paper_path_wire import correct


def _item(asset: str, regime: str, strategy: str | None, setup: bool) -> dict[str, Any]:
    row = {"strategy": strategy, "setup_detected": setup, "regime": regime} if strategy else None
    return {"symbol": asset, "status": "ok", "regime": regime, "price": 100.0, "strategy_observations": [row] if row else [], "fixture": True}


def _trace(name: str, asset: str, regime: str, strategy: str | None, setup: bool, db: Path) -> dict[str, Any]:
    cycle_id = f"fixture.{name}"
    obs = observation_from_result(_item(asset, regime, strategy, setup), cycle_id=cycle_id, ts="2026-09-28T12:32:00+00:00", bar_tf="1h")
    obs["id"] = f"fixture.{name}.{asset}"
    before = run(obs)
    after = correct(before, db_path=db)
    store = after.get("decision_store") or {}
    row = None
    if store.get("id") and db.exists():
        con = sqlite3.connect(db)
        row = con.execute("SELECT decision, bar_tf FROM decisions WHERE id=?", (store.get("id"),)).fetchone()
        con.close()
    return {
        "name": name,
        "not_a_hands_post": True,
        "not_a_market_trade": after.get("not_a_market_trade", True),
        "setup_detected": setup,
        "qualifying": {"hunter": (before.get("l2_state") or {}).get("hunter_qualifying"), "squeeze": (before.get("l2_state") or {}).get("squeeze_qualifying")},
        "retrieved_ids": ((before.get("snapshot") or {}).get("retrieved") or [])[:8],
        "knowledge_influence": "NOT_SHOWN",
        "before_correct": before.get("issued"),
        "after_correct": after.get("issued"),
        "reason": after.get("reason"),
        "best": after.get("best_id"),
        "fill": (after.get("paper_book") or {}).get("status"),
        "evidence_class": after.get("evidence_class"),
        "exec": after.get("exec"),
        "m2": after.get("counts_for_m2"),
        "authority": after.get("authority_granted"),
        "sqlite_decision": None if row is None else row[0],
        "sqlite_bar_tf": None if row is None else row[1],
    }


def run_harness(db: Path | None = None) -> dict[str, Any]:
    db = db or Path("/tmp/paper_path_harness.sqlite")
    if db.name == "agent_decisions.sqlite":
        raise SystemExit("FIXTURE_REFUSED_ON_LIVE_DB")
    if db.exists():
        db.unlink()
    os.environ["ANANTA_DECISIONS_DB"] = str(db)
    cases = [
        _trace("squeeze", "BTC", "COMPRESSION", "squeeze", True, db),
        _trace("hunter", "ETH", "REVERSAL", "hunter", True, db),
        _trace("range_quiet", "SOL", "RANGE", None, False, db),
        _trace("family_match", "XRP", "COMPRESSION", "squeeze", False, db),
    ]
    ok = (
        cases[0]["after_correct"] == "TAKE"
        and cases[0]["fill"] == "PAPER_FILL_RECORDED"
        and cases[0]["evidence_class"] == "FIXTURE"
        and cases[0]["not_a_market_trade"] is True
        and cases[0]["exec"] is False
        and cases[0]["m2"] is False
        and cases[0]["authority"] is False
        and cases[0]["sqlite_decision"] == "TAKE"
        and cases[0]["qualifying"]["squeeze"] is True
        and cases[1]["after_correct"] == "TAKE"
        and cases[1]["qualifying"]["hunter"] is True
        and cases[2]["after_correct"] == "NO_TRADE"
        and cases[3]["after_correct"] == "NO_TRADE"
        and cases[3]["qualifying"]["squeeze"] is False
    )
    return {
        "id": "production.path.harness.v1",
        "status": "HARNESS_PASS" if ok else "HARNESS_FAIL",
        "path": "observation_from_result -> di_loop.run -> paper_path_wire.correct",
        "not_a_hands_post": True,
        "not_a_market_trade": True,
        "knowledge_influence": "NOT_SHOWN",
        "persisted_bar_tf_note": "GitHub decision_store may still write the scan label. Do not replace decision_store.py from this harness.",
        "db": str(db),
        "cases": cases,
    }


if __name__ == "__main__":
    report = run_harness()
    print(report["status"])
    for row in report["cases"]:
        print(f"{row['name']}: before={row['before_correct']} after={row['after_correct']} fill={row['fill']} class={row['evidence_class']} sqlite={row['sqlite_decision']}")
