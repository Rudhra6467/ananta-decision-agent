"""CLI for Decision Intelligence. Also reachable as `lab di` / `lab system` / ...

    python -m src.intelligence system
    python -m src.intelligence profile
    python -m src.intelligence profile SAFE
    python -m src.intelligence di
    python -m src.intelligence experiments
    python -m src.intelligence paper-sim
    python -m src.intelligence contract
    python -m src.intelligence attribution
    python -m src.intelligence research hunter
    python -m src.intelligence universe


    python -m src.intelligence intent OBSERVE
"""
from __future__ import annotations

import json
import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    cmd = (args[0] if args else "help").lower()
    rest = args[1:]
    if cmd in ("help", "-h", "--help"):
        print_help()
        return 0
    if cmd in ("system", "status", "completeness"):
        return _cmd_system()
    if cmd in ("profile", "profiles", "risk"):
        return _cmd_profile(rest)
    if cmd in ("di", "decide", "adjudicate"):
        return _cmd_di(rest)
    if cmd in ("experiments", "experiment", "s5"):
        return _cmd_experiments(rest)
    if cmd in ("paper-sim", "papersim", "sim", "paper"):
        return _cmd_paper()
    if cmd in ("contract", "api"):
        return _cmd_contract(rest)
    if cmd in ("attribution", "attr"):
        source = rest[0] if rest else "live"
        return _cmd_attribution(source)
    if cmd in ("research", "strategy"):
        key = rest[0] if rest else None
        return _cmd_research(key)
    if cmd in ("memory", "setups", "setup-memory"):
        return _cmd_memory(rest)
    if cmd in ("fingerprints", "fingerprint", "fp"):
        return _cmd_fingerprints(rest)
    if cmd in ("opportunity", "opp", "scan"):
        return _cmd_opportunity()
    if cmd in ("universe", "sru", "cells"):
        return _cmd_universe()
    if cmd in ("cards", "card", "evidence-cards"):
        key = rest[0] if rest else None
        return _cmd_cards(key)
    if cmd in ("boards", "board", "rank"):
        return _cmd_boards()
    if cmd in ("lookup", "state", "recall"):
        flag = rest[0] if rest else "UP"
        source = rest[1] if len(rest) > 1 else "replay"
        return _cmd_lookup(flag, source)
    if cmd in ("baseline", "i2", "lock"):
        return _cmd_baseline()
    if cmd in ("consult", "ask", "knowledge"):
        if rest and rest[0].lower() in ("backfill", "fill"):
            return _cmd_consult_backfill(rest[1] if len(rest) > 1 else "live")
        if rest and rest[0].lower() in ("dq", "quality"):
            return _cmd_consult_dq()
        source = rest[0] if rest else "live"
        return _cmd_consult(source)
    if cmd in ("consult-dq", "consultdq"):
        return _cmd_consult_dq()
    if cmd in ("sitout", "sit-out", "opportunity-cost"):
        return _cmd_sitout()
    if cmd in ("h2", "hunter-gates"):
        source = rest[0] if rest else "replay"
        return _cmd_h2(source)
    if cmd in ("quality", "dq", "meter"):
        return _cmd_quality()
    if cmd in ("gates", "gate", "safety"):
        return _cmd_gates()
    if cmd in ("intent", "context"):
        return _cmd_intent(rest)
    print_help()
    return 1


def print_help() -> None:
    print(
        "lab system | lab profile [SAFE|MODERATE|AGGRESSIVE] | lab di | "
        "lab experiments | lab paper-sim | lab contract | lab attribution [live|replay] | "
        "lab research [hunter] | lab quality | lab h2 | lab universe | lab cards | lab boards | lab lookup | lab baseline | lab consult | lab consult backfill | lab consult-dq | lab sitout | lab memory | lab fingerprints | lab opportunity | lab gates | lab intent [OBSERVE|RESEARCH|PAPER_TRADE]"
    )
    print("Wave A stays WATCH. lab opportunity = interface lock, not a scanner. H1 live enable rejected.")


def _dump(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _cmd_system() -> int:
    from src.intelligence.system_status import completeness

    _dump(completeness())
    return 0


def _cmd_profile(rest: List[str]) -> int:
    from src.intelligence.profiles import (
        PROFILES,
        get_active_profile_name,
        get_profile,
        set_active_profile,
    )

    if rest:
        name = rest[0]
        if name.lower() in ("show", "list"):
            _dump({k: v.as_dict() for k, v in PROFILES.items()})
            return 0
        prof = set_active_profile(name)
        print(f"→ active profile = {prof.name} (behavior parameters, not a new agent)")
        _dump(prof.as_dict())
        return 0
    name = get_active_profile_name()
    print(f"active profile = {name}")
    _dump(get_profile(name).as_dict())
    return 0


def _cmd_di(rest: List[str]) -> int:
    from src.intelligence.orchestrate import run_cycle

    persist = "--persist" in rest or "persist" in rest
    result = run_cycle(persist=persist)
    d = result.get("decision") or {}
    print("\nDECISION INTELLIGENCE")
    print("=" * 64)
    print(f"  recommended : {d.get('recommended_action')}")
    print(f"  issued      : {d.get('issued_action')}")
    print(f"  execute     : {d.get('execution_allowed')}  (Ananta authority)")
    print(f"  strategy    : {d.get('strategy_key')}  {d.get('symbol')}")
    print(f"  profile     : {d.get('profile')}  intent={d.get('user_intent')}")
    print(f"  skip_reason : {d.get('skip_reason')}")
    conf = d.get("confidences") or {}
    print(
        f"  confidence  : understanding={conf.get('understanding')}  "
        f"evidence={conf.get('evidence')}  decision={conf.get('decision')}  blended=never"
    )
    print(f"  thesis      : {d.get('thesis')}")
    print(f"  counter     : {d.get('counter_thesis')}")
    print(f"  adjudicate  : {d.get('adjudication')}")
    kc = result.get("knowledge_consult") or {}
    if kc:
        print(
            f"  consult     : tape={kc.get('flag')}  knowledge_action={kc.get('knowledge_action')}  "
            f"why={kc.get('why')}  override=False"
        )
    print("-" * 64)
    print("  Wave A WATCH. TAKE is not KEEP. S5 is parked. Consult cannot TAKE.")
    print("=" * 64)
    if "--json" in rest or "json" in rest:
        _dump(result)
    return 0


def _cmd_experiments(rest: List[str]) -> int:
    from src.intelligence.experiments import approve, list_experiments, propose, try_run

    if rest and rest[0] in ("run", "start"):
        exp_id = rest[1] if len(rest) > 1 else "S5-H3"
        _dump(try_run(exp_id))
        return 0
    if rest and rest[0] == "approve":
        exp_id = rest[1] if len(rest) > 1 else ""
        human = rest[2] if len(rest) > 2 else "operator"
        _dump(approve(exp_id, human=human, note="cli"))
        return 0
    if rest and rest[0] == "propose":
        title = " ".join(rest[1:]) or "untitled"
        _dump(propose(title=title, hypothesis=title, kind="measurement"))
        return 0
    rows = list_experiments()
    print("\nEXPERIMENT LEDGER (H3 measurement / H2 pending Ananta dump / H1 live enable rejected)")
    print("=" * 64)
    for r in rows:
        print(
            f"  {r['id']:<8} {r['status']:<24} runnable={r['runnable_now']}  {r['title']}"
        )
        print(f"           blocked: {', '.join(r['blocked_by'])}")
    print("-" * 64)
    print("  try_run never mutates Wave A. H3 report = lab attribution. H1 live enable rejected.")
    print("=" * 64)
    return 0


def _cmd_paper() -> int:
    from src.intelligence.paper import simulate

    result = simulate(persist=False)
    print("\nPAPER SIMULATION (no fill, no enable)")
    print("=" * 64)
    d = (result.get("cycle") or {}).get("decision") or {}
    print(f"  recommended={d.get('recommended_action')}  issued={d.get('issued_action')}")
    print(f"  placed_order={result.get('placed_order')}  enabled={result.get('enabled_strategy')}")
    print(f"  wave_a={result.get('wave_a_status')}")
    print("=" * 64)
    return 0


def _cmd_contract(rest: List[str]) -> int:
    from src.intelligence.contract import contract_spec, probe

    if rest and rest[0] in ("probe", "ping"):
        _dump(probe())
        return 0
    spec = contract_spec()
    print("\nAGENT ↔ ANANTA CONTRACT v0 + decision_v0")
    print("=" * 64)
    for r in spec["expected_routes"]:
        print(f"  {r['method']:<6} {r['path']:<40} {r['need']}")
    print("-" * 64)
    print("  not a route: " + ", ".join(spec["not_a_route"]))
    print("  Agent never writes Mongo. UI is a client. Ananta owns fills.")
    print("=" * 64)
    return 0


def _cmd_attribution(source: str) -> int:
    import json
    from pathlib import Path

    from src.intelligence.attribution import attribute_print_ready

    report = attribute_print_ready(source)
    path = Path(
        "attribution_replay.json" if report.get("source") == "historical_lab" else "attribution_live.json"
    )
    try:
        path.write_text(json.dumps(report, indent=2, default=str))
    except Exception:
        path = None
    print(f"\nATTRIBUTION / H3 ({report.get('source')})  n={report.get('n')}  data_gap={report.get('data_gap')}")
    print("=" * 64)
    print(f"  {report.get('note')}")
    print("-" * 64)

    def _triple(means: dict) -> str:
        means = means or {}
        parts = []
        for k in ("fwd_15m_pct", "fwd_1h_pct", "fwd_4h_pct"):
            v = means.get(k)
            parts.append("—" if v is None else f"{v}%")
        return "  ".join(parts)

    for k, b in (report.get("by_strategy") or {}).items():
        print(
            f"  {k:<14} rows={b.get('n_rows')} setup={b.get('n_setup')} "
            f"TAKE={b.get('n_take')} SKIP={b.get('n_skip')} WAIT={b.get('n_wait')} "
            f"filtered={b.get('n_regime_filtered')}"
        )
        print(f"                 mean +15m / +1h / +4h")
        print(
            f"                   TAKE n_1h={(b.get('n_fwd_after_take') or {}).get('fwd_1h_pct', 0)}  "
            f"{_triple(b.get('mean_fwd_after_take'))}"
        )
        print(
            f"                   SKIP n_1h={(b.get('n_fwd_after_skip') or {}).get('fwd_1h_pct', 0)}  "
            f"{_triple(b.get('mean_fwd_after_skip'))}"
        )
        print(
            f"                   WAIT n_1h={(b.get('n_fwd_after_wait') or {}).get('fwd_1h_pct', 0)}  "
            f"{_triple(b.get('mean_fwd_after_wait'))}"
        )
    print("-" * 64)
    print("  H3 = this report. Wave A stays WATCH. Not KEEP. Not a trade.")
    if path:
        print(f"  saved: {path}")
    print("=" * 64)
    return 0


def _cmd_research(key: Optional[str]) -> int:
    from src.intelligence.research import research

    report = research(key)
    print("\nSTRATEGY RESEARCH")
    print("=" * 64)
    for s in report.get("strategies") or []:
        print(f"  {s['strategy_id']}  lifecycle={s['lifecycle']}  regimes={s['thesis_allowed_regimes']}")
        live = s.get("live_evidence") or {}
        hist = s.get("historical_evidence") or {}
        print(
            f"    live  setup={live.get('n_setup')} take={live.get('n_take')} "
            f"skip={live.get('n_skip')} filtered={live.get('n_regime_filtered')} gap={live.get('data_gap')}"
        )
        print(
            f"    hist  setup={hist.get('n_setup')} take={hist.get('n_take')} "
            f"skip={hist.get('n_skip')} filtered={hist.get('n_regime_filtered')} gap={hist.get('data_gap')}"
        )
        print(f"    verdict={s['verdict']}  KEEP=no")
    print("=" * 64)
    return 0


def _cmd_memory(rest: List[str]) -> int:
    from src.intelligence.setup_memory import print_memory

    source = "replay"
    strat = None
    regime = None
    args = [a for a in rest if a]
    if args and args[0].lower() in ("live", "replay", "historical", "historical_lab"):
        source = args[0]
        args = args[1:]
    if args:
        strat = args[0]
    if len(args) > 1:
        regime = args[1]
    print_memory(source, strat, regime)
    return 0


def _cmd_fingerprints(rest: List[str]) -> int:
    from src.intelligence.fingerprint import print_fingerprints

    source = "replay"
    strat = None
    args = [a for a in rest if a]
    if args and args[0].lower() in ("live", "replay", "historical", "historical_lab"):
        source = args[0]
        args = args[1:]
    if args:
        strat = args[0]
    print_fingerprints(source, strat)
    return 0


def _cmd_opportunity() -> int:
    from src.intelligence.opportunity_engine import print_opportunity

    print_opportunity()
    return 0


def _cmd_universe() -> int:
    from src.intelligence.universe import print_universe

    print_universe()
    return 0


def _cmd_cards(key: Optional[str]) -> int:
    from src.intelligence.evidence_cards import print_cards

    print_cards(key)
    return 0


def _cmd_boards() -> int:
    from src.intelligence.boards import print_boards

    print_boards()
    return 0


def _cmd_lookup(flag: str, source: str) -> int:
    from src.intelligence.lookup import print_lookup

    print_lookup(flag, source)
    return 0


def _cmd_baseline() -> int:
    from src.intelligence.i2_baseline import print_baseline

    print_baseline()
    return 0


def _cmd_consult(source: str) -> int:
    from src.intelligence.consult import print_consult

    print_consult(source if source in ("live", "replay", "historical") else "live")
    return 0


def _cmd_sitout() -> int:
    from src.intelligence.sitout import print_sitout

    print_sitout()
    return 0


def _cmd_consult_backfill(source: str) -> int:
    from src.intelligence.consult import print_backfill

    print_backfill(source if source in ("live", "replay") else "live")
    return 0


def _cmd_consult_dq() -> int:
    from src.intelligence.consult_dq import print_consult_dq

    print_consult_dq()
    return 0


def _cmd_h2(source: str) -> int:
    from src.intelligence.h2 import print_h2

    print_h2(source)
    return 0


def _cmd_quality() -> int:
    from src.intelligence.decision_quality import print_meter

    print_meter()
    return 0


def _cmd_gates() -> int:
    from src.intelligence.gates import HARD_ALWAYS, evaluate_gates
    from src.intelligence.profiles import get_profile

    allowed, issued, hits = evaluate_gates(
        recommended_action="TAKE",
        strategy_key="hunter",
        setup_detected=True,
        profile=get_profile(),
        user_intent="PAPER_TRADE",
        ananta_ok=True,
        user_confirmed=True,
        evidence_confidence=0.9,
        decision_confidence=0.9,
    )
    print("\nHARD SAFETY (TAKE hunter, confirmed, high confidence)")
    print("=" * 64)
    print(f"  execution_allowed={allowed}  issued={issued}")
    print(f"  hard_always={list(HARD_ALWAYS)}")
    print("-" * 64)
    for h in hits:
        flag = "PASS" if h.passed else "BLOCK"
        print(f"  [{flag:<5}] {h.layer:<8} {h.code:<28} {h.detail}")
    print("-" * 64)
    print("  Agent can recommend. Ananta executes. Wave A WATCH blocks the fill.")
    print("=" * 64)
    return 0


def _cmd_intent(rest: List[str]) -> int:
    from src.intelligence.user_context import get_user_context, set_user_intent

    if rest:
        ctx = set_user_intent(rest[0])
        print(f"→ intent = {ctx.intent}  (PROMOTE/AUTONOMOUS remain blocked)")
        _dump(ctx.as_dict())
        return 0
    _dump(get_user_context().as_dict())
    return 0
