"""Evidence-id allowlist. Warehouse rank is not a cite.

Defect: decision_store used `cited or knowledge_ids`. An empty cite list is
falsy, so RANGE (no family hit) wrote the whole catalog into evidence_ids_json.
That catalog includes SET14, HOT-birth, SEQ2, continuation, and closed S2 rows.

This module is the gate. It does not TAKE, does not fill, does not credit M2,
and does not backfill old rows. Context cites stay off until a new-row inspect
passes. Continuation may remain the setup column. It is not an evidence id.

Laptop wire, new inserts only. Do not replace decision_store.py from this
branch. The laptop bar-open repair is not on p1-cycle-ingest.

    from src.intelligence.cite_allowlist import apply_new_row
    apply_new_row(row, payload, snapshot, agent_version=VERSION)

Call that instead of `cited or knowledge_ids`. Do not UPDATE old rows.
"""
from __future__ import annotations

import json
from typing import Any

FILTER_VERSION = "cite.allowlist.v1"
SCHEMA_VERSION = "persist.hygiene.v1"

# Dump-fix surface. The 3 context cites are not in this tuple.
LIVE_5 = (
    "card.hunter.r3.v1",
    "card.squeeze.r3.v1",
    "card.h1.volume_shock.v1",
    "card.mrd.size_after_vol.v0",
    "card.mrd.sync_after_vol.v0",
)

ALIASES = {
    "h1.volume_shock.v1": "card.h1.volume_shock.v1",
    "mrd.size_after_vol.v0": "card.mrd.size_after_vol.v0",
    "mrd.sync_after_vol.v0": "card.mrd.sync_after_vol.v0",
    "hunter": "card.hunter.r3.v1",
    "squeeze": "card.squeeze.r3.v1",
}

# Prefix or exact. Checked after alias canonicalization.
DENY_PREFIXES = (
    "set14",
    "card.set14",
    "hot.birth",
    "card.hot.birth",
    "seq2",
    "card.seq2",
    "te.",
    "mrd7",
    "watch.score",
    "hl.rx",
    "hlrx",
    "exit_map",
    "engine.exit",
    "card.continuation",
    "continuation.",
    "s2.hunter",
    "s2.squeeze",
    "card.s2.",
)

# Flip only after a new G5 row inspect passes. Not this commit.
CONTEXT_CITES_DEPLOYED = False

ABSENCE = ("NOT_MEASURED", "NOT_AVAILABLE", "NOT_APPLICABLE", "MISSING")


def canonical(raw: str) -> str:
    s = str(raw or "").strip()
    return ALIASES.get(s, s)


def denied(cid: str) -> bool:
    low = cid.lower()
    return any(low == p or low.startswith(p) for p in DENY_PREFIXES)


def filter_evidence_ids(
    proposed: list[Any] | None,
    *,
    knowledge_ids: list[Any] | None = None,
) -> dict[str, Any]:
    """Filter a proposed cite list.

    knowledge_ids is accepted and ignored. Reading it was the dump.
    """
    del knowledge_ids  # explicit: warehouse rank must not become a cite
    kept: list[str] = []
    stripped: list[str] = []
    for raw in list(proposed or []):
        cid = canonical(str(raw))
        if not cid or cid in ABSENCE:
            continue
        if denied(cid) or cid not in LIVE_5:
            if cid not in stripped:
                stripped.append(cid)
            continue
        if cid not in kept:
            kept.append(cid)
    return {
        "evidence_ids": kept or ["NOT_MEASURED"],
        "stripped": stripped,
        "knowledge_ids_ignored": True,
        "context_cites_deployed": CONTEXT_CITES_DEPLOYED,
        "filter_version": FILTER_VERSION,
        "paper_take": False,
        "counts_for_m2": False,
        "exec": False,
    }


def stamp_new_row(
    *,
    agent_version: str | None,
    engine_version: str | None = None,
    card_version: str | None = None,
) -> dict[str, Any]:
    """Versions for a new insert only. Caller must not UPDATE old rows."""
    card = canonical(card_version or "")
    if card not in LIVE_5:
        card = "UNKNOWN"
    return {
        "engine_version": engine_version or "UNKNOWN",
        "agent_version": agent_version or "UNKNOWN",
        "card_version": card,
        "schema_version": SCHEMA_VERSION,
        "cite_filter_version": FILTER_VERSION,
        "backfill": False,
        "context_cites_deployed": CONTEXT_CITES_DEPLOYED,
    }


def apply_new_row(
    row: dict[str, Any],
    payload: dict[str, Any],
    snapshot: dict[str, Any] | None,
    *,
    agent_version: str | None,
    engine_version: str | None = None,
) -> dict[str, Any]:
    """Write the allowlist onto a new row. Does not touch last_bar_open."""
    snap = snapshot or {}
    raw = list(snap.get("cited") or [])
    filt = filter_evidence_ids(raw, knowledge_ids=snap.get("knowledge_ids"))
    setup = snap.get("selected_strategy")
    stamps = stamp_new_row(
        agent_version=agent_version,
        engine_version=engine_version,
        card_version=str(setup) if setup else None,
    )
    row["evidence_ids_json"] = json.dumps(filt["evidence_ids"])
    payload["evidence_ids"] = filt["evidence_ids"]
    payload["evidence_stripped"] = filt["stripped"]
    payload["evidence_filter"] = filt
    payload["versions"] = stamps
    payload["backfill"] = False
    payload["counts_for_m2"] = False
    payload["paper_take"] = False
    payload["exec"] = False
    return filt
