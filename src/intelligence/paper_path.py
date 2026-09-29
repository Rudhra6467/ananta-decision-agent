"""Controlled paper path. A fixture fill is not a market trade.

Does not set exec. Does not credit M2. Does not grant knowledge authority.
Does not un-bench continuation. Does not turn SET16 into a take.
Does not loosen a hunter or squeeze threshold.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "paper.path.v1"
ELIGIBLE = {
    "hunter": {"regime": "REVERSAL", "card": "card.hunter.r3.v1"},
    "squeeze": {"regime": "COMPRESSION", "card": "card.squeeze.r3.v1"},
}
PROOF_NAME = "paper_path_proof_v1.json"


def fixture_proven(state=None, proof_path=None):
    state = state or {}
    if state.get("fixture_proven") is True:
        return True
    if state.get("fixture_proven") is False:
        return False
    path = proof_path or Path(__file__).with_name(PROOF_NAME)
    if not path.exists():
        return False
    try:
        proof = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return proof.get("status") == "FIXTURE_PASS" and proof.get("not_a_market_trade") is True


def _base(action, reason, best_id, **extra):
    out = {"version": VERSION, "action": action, "label": action if action in ("TAKE", "WAIT", "WATCH", "SHADOW_PAPER", "UNKNOWN", "NO_TRADE") else "NO_TRADE", "reason": reason, "best_id": best_id, "paper_fill_allowed": False, "paper_order": False, "paper_fill": False, "exec": False, "keep": False, "live": False, "counts_for_m2": False, "authority_granted": False, "knowledge_authority": "NONE", "not_validated": True, "evidence_class": "NONE", "not_a_market_trade": True, "source": extra.pop("source", None), "core": extra.pop("core", None), "missing": extra.pop("missing", [])}
    out.update(extra)
    return out


def decide(state, proof_path=None):
    state = dict(state or {})
    source = str(state.get("source") or "LIVE").upper()
    if source not in ("FIXTURE", "LIVE"):
        source = "LIVE"
    if state.get("observer_match") == "set16":
        return _base("WATCH", "MATCH_NOT_TAKE", "card.set16.move_cold_lag.v1", source=source)
    if state.get("continuation_would_qualify"):
        return _base("SHADOW_PAPER", "BEST_AVAILABLE_STRATEGY_HAS_NO_PAPER_AUTHORITY", "card.continuation.r3.v1", source=source)
    hunter = bool(state.get("hunter_qualifying"))
    squeeze = bool(state.get("squeeze_qualifying"))
    if hunter and squeeze:
        return _base("NO_TRADE", "AMBIGUOUS_CORE", None, source=source)
    if not hunter and not squeeze:
        return _base("NO_TRADE", "NO_QUALIFYING_SETUP", None, source=source)
    core = "hunter" if hunter else "squeeze"
    spec = ELIGIBLE[core]
    missing = [k for k in ("asset", "tf", "regime", "source") if not state.get(k)]
    if state.get("regime") != spec["regime"]:
        return _base("NO_TRADE", "REGIME_DOES_NOT_MATCH_CORE", spec["card"], source=source, core=core)
    if missing:
        return _base("UNKNOWN", "MISSING_REQUIRED_INPUT", spec["card"], source=source, core=core, missing=sorted(set(missing)))
    if source == "LIVE" and not fixture_proven(state, proof_path):
        return _base("WAIT", "FIXTURE_NOT_PROVEN", spec["card"], source=source, core=core)
    return _base("TAKE", "PAPER_PATH_QUALIFYING_SETUP", spec["card"], source=source, core=core, paper_fill_allowed=True, paper_order=True, paper_fill=True, evidence_class="FIXTURE" if source == "FIXTURE" else "LIVE_PAPER", not_a_market_trade=source == "FIXTURE")


def issued_from_paper(decision):
    label = str(decision.get("label") or decision.get("action") or "NO_TRADE")
    if label == "TAKE":
        allowed = decision.get("paper_fill_allowed") is True and decision.get("exec") is False and decision.get("counts_for_m2") is False and decision.get("authority_granted") is False and decision.get("live") is False
        return "TAKE" if allowed else "NO_TRADE"
    return label if label in ("NO_TRADE", "WATCH", "WAIT", "SHADOW_PAPER", "UNKNOWN") else "NO_TRADE"


def record_paper_fill(receipt):
    if issued_from_paper(receipt) != "TAKE":
        return {"id": "paper.ledger.v1", "status": "REFUSED", "last_refuse": receipt.get("reason") or "PAPER_PATH_REFUSED", "paper_take": False, "exec": False, "keep": False, "counts_for_m2": False, "trade_count": 0, "open_positions": []}
    return {"id": "paper.ledger.v1", "status": "PAPER_FILL_RECORDED", "cash": 1000.0, "reserved_capital": 100.0, "open_positions": [{"instrument": receipt.get("asset"), "core": receipt.get("core"), "card": receipt.get("best_id"), "notional": 100.0, "evidence_class": receipt.get("evidence_class"), "not_a_market_trade": receipt.get("not_a_market_trade"), "source": receipt.get("source")}], "trade_count": 1, "paper_order": True, "paper_fill": True, "paper_take": True, "exec": False, "keep": False, "live": False, "counts_for_m2": False, "authority_granted": False, "knowledge_authority": "NONE", "credentials": "none", "last_refuse": None}


def run_fixture(proof_path=None):
    proof_path = proof_path or Path(__file__).with_name(PROOF_NAME)
    cases = {
        "fixture_squeeze": {"asset": "BTC", "tf": "1h", "regime": "COMPRESSION", "direction": "LONG", "source": "FIXTURE", "squeeze_qualifying": True},
        "fixture_hunter": {"asset": "ETH", "tf": "1h", "regime": "REVERSAL", "direction": "SHORT", "source": "FIXTURE", "hunter_qualifying": True},
        "family_match_not_setup": {"asset": "BTC", "tf": "1h", "regime": "COMPRESSION", "direction": "LONG", "source": "LIVE", "squeeze_qualifying": False},
        "continuation": {"asset": "SOL", "tf": "1h", "regime": "TREND_UP", "direction": "LONG", "source": "FIXTURE", "continuation_would_qualify": True},
        "set16": {"asset": "ADA", "tf": "15m", "regime": "LAG", "direction": "LONG", "source": "FIXTURE", "observer_match": "set16"},
        "missing_asset": {"tf": "1h", "regime": "COMPRESSION", "direction": "LONG", "source": "FIXTURE", "squeeze_qualifying": True},
        "live_before_proof": {"asset": "BTC", "tf": "1h", "regime": "COMPRESSION", "direction": "LONG", "source": "LIVE", "squeeze_qualifying": True, "fixture_proven": False},
        "forced_take_without_receipt": {"label": "TAKE", "action": "TAKE", "paper_fill_allowed": False, "exec": False},
    }
    results = {}
    for name, state in cases.items():
        if name == "forced_take_without_receipt":
            results[name] = {"issued": issued_from_paper(state), "fill": None}
            continue
        decision = decide(state, proof_path=Path("/tmp/paper_path_no_proof.json"))
        issued = issued_from_paper(decision)
        fill = record_paper_fill({**decision, "asset": state.get("asset")})
        results[name] = {"issued": issued, "reason": decision.get("reason"), "evidence_class": decision.get("evidence_class"), "fill_status": fill.get("status"), "m2": fill.get("counts_for_m2"), "exec": fill.get("exec"), "authority": decision.get("authority_granted"), "market": decision.get("not_a_market_trade") is False}
    ok = results["fixture_squeeze"]["issued"] == "TAKE" and results["fixture_squeeze"]["fill_status"] == "PAPER_FILL_RECORDED" and results["fixture_squeeze"]["evidence_class"] == "FIXTURE" and results["fixture_squeeze"]["market"] is False and results["fixture_squeeze"]["m2"] is False and results["fixture_squeeze"]["exec"] is False and results["fixture_squeeze"]["authority"] is False and results["fixture_hunter"]["issued"] == "TAKE" and results["family_match_not_setup"]["issued"] == "NO_TRADE" and results["continuation"]["issued"] == "SHADOW_PAPER" and results["set16"]["issued"] == "WATCH" and results["missing_asset"]["issued"] == "UNKNOWN" and results["live_before_proof"]["issued"] == "WAIT" and results["forced_take_without_receipt"]["issued"] == "NO_TRADE"
    proof = {"id": "paper.path.proof.v1", "status": "FIXTURE_PASS" if ok else "FIXTURE_FAIL", "not_a_market_trade": True, "not_m2": True, "exec": False, "authority_granted": False, "knowledge_authority": "NONE", "cases": results}
    if ok:
        proof_path.write_text(json.dumps(proof, indent=2))
    return proof
