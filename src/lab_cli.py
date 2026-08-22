"""Wave A strategy DNA + Research Lab 1y evidence (source=backtest, not KEEP)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

WAVE_A = ("hunter", "squeeze", "bollinger-mr")
LAB_EVIDENCE = Path("lab_evidence.json")
DEFAULT_SYMBOLS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "XRP/USD",
    "PAXG/USD", "LINK/USD", "AAVE/USD", "ARB/USD", "RENDER/USD",
]
MIN_1H_BARS = 250  # lab backtest warmup is 200


def _dna_fields(s: dict) -> dict:
    dna = s.get("dna") or {}
    if not isinstance(dna, dict):
        dna = {}
    return {
        "key": s.get("key") or s.get("id"),
        "name": s.get("name") or s.get("key"),
        "purpose": dna.get("purpose") or s.get("description") or "",
        "works_best": dna.get("works_best") or "",
        "avoid": dna.get("avoid") or "",
        "risk": dna.get("risk") or "",
        "holding": dna.get("holding") or "",
        "preferred_coins": dna.get("preferred_coins") or [],
        "tags": dna.get("tags") or [],
        "author_confidence": dna.get("confidence"),
    }


def print_strategy_dna():
    """Pull Ananta registry DNA. This is understanding, not ranking evidence."""
    from src.tools.ananta_api import get_strategy_registry, get_strategy_status

    print("\nSTRATEGY DNA (from Ananta registry — facts, not Agent ranking)")
    print("=" * 64)
    print("Wave A is hunter / squeeze / bollinger-mr because we LOCKED a")
    print("narrow lab — not because the Agent scored all 15 and picked three.")
    print("-" * 64)

    reg = get_strategy_registry()
    if not reg.get("success"):
        print(f"Could not fetch registry: {reg.get('error') or reg}")
        print()
        return
    rows = [_dna_fields(s) for s in (reg.get("strategies") or [])]
    by_key = {r["key"]: r for r in rows if r.get("key")}

    st = get_strategy_status()
    enabled = set()
    if st.get("success"):
        enabled = {s.get("key") for s in st.get("strategies", []) if s.get("enabled")}

    print("WAVE A (enabled lab set)")
    for k in WAVE_A:
        r = by_key.get(k) or {"key": k, "name": k, "purpose": "(no DNA on registry)"}
        on = "ON " if k in enabled else "off"
        print(f"\n  [{on}] {r.get('name')}  ({k})")
        print(f"      purpose   : {r.get('purpose') or '—'}")
        print(f"      works_best: {r.get('works_best') or '—'}")
        print(f"      avoid     : {r.get('avoid') or '—'}")
        print(f"      risk/hold : {r.get('risk') or '—'} / {r.get('holding') or '—'}")
        tags = r.get("tags") or []
        if tags:
            print(f"      tags      : {', '.join(map(str, tags))}")

    print("\n" + "-" * 64)
    print("OTHER CATALOG (not Wave A — do not enable)")
    for r in rows:
        k = r.get("key")
        if not k or k in WAVE_A:
            continue
        print(f"  ○ {r.get('name')} ({k}) — {str(r.get('purpose') or '')[:72]}")
    print("-" * 64)
    print("Modify production logic only via: observe → hypothesis → lab/paper")
    print("→ evaluate → human promotion. Agent may rank. Agent may not rewrite.")
    print("=" * 64)
    print()


def _save_evidence(run: dict):
    payload = {
        "source": "backtest",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "wave_a": list(WAVE_A),
        "run_id": run.get("id"),
        "status": run.get("status"),
        "kind": run.get("kind"),
        "period": run.get("period"),
        "strategies": run.get("strategies"),
        "symbols": run.get("symbols"),
        "result": run.get("result"),
        "error": run.get("error"),
        "note": "BACKTEST context only. Does not promote KEEP. Paper TAKEs still required.",
    }
    LAB_EVIDENCE.write_text(json.dumps(payload, indent=2, default=str))
    return LAB_EVIDENCE


def _summarize_result(result) -> None:
    if not result:
        print("  (no result payload yet)")
        return
    if isinstance(result, dict) and result.get("error"):
        print(f"  error: {result.get('error')}")
        return
    # Flexible: print compact metrics if present
    if isinstance(result, dict):
        cards = result.get("strategies") or result.get("per_strategy") or result.get("cards")
        per_symbol = result.get("per_symbol") or result.get("symbols")
        if isinstance(cards, list):
            for c in cards:
                if not isinstance(c, dict):
                    continue
                key = c.get("strategy") or c.get("key") or c.get("name")
                print(
                    f"  {key}: trades={c.get('trades')} ret={c.get('total_return_pct')} "
                    f"wr={c.get('win_rate_pct')} dd={c.get('max_drawdown_pct')} "
                    f"pf={c.get('profit_factor')}"
                )
            return
        if isinstance(per_symbol, dict):
            for sym, m in list(per_symbol.items())[:12]:
                if isinstance(m, dict) and "error" in m:
                    print(f"  {sym}: {m.get('error')} have={m.get('have')}")
                elif isinstance(m, dict):
                    print(
                        f"  {sym}: trades={m.get('trades')} ret={m.get('total_return_pct')} "
                        f"wr={m.get('win_rate_pct')}"
                    )
            return
        keys = list(result.keys())[:12]
        print(f"  result keys: {keys}")
    else:
        print(f"  result type={type(result).__name__}")


def print_lab_coverage():
    from src.tools.ananta_api import get_lab_coverage

    cov = get_lab_coverage()
    if not cov.get("success"):
        print(f"Coverage failed: {cov.get('error') or cov}")
        return None
    data = cov.get("data") or {}
    rows = data.get("symbols") or []
    print("\nLAB CANDLE COVERAGE")
    print("-" * 64)
    weakest = None
    for row in rows:
        n = row.get("bars_1h") or 0
        print(
            f"  {row.get('symbol'):<12} 1h={n:<6} 4h={row.get('bars_4h') or 0:<5} "
            f"1d={row.get('bars_1d') or 0}"
        )
        if weakest is None or n < weakest:
            weakest = n
    print("-" * 64)
    print(f"  weakest 1h series: {weakest} bars (need ≥ {MIN_1H_BARS} to backtest)")
    print()
    return weakest


def run_wave_a_lab(period: str = "1y"):
    """Queue Ananta Research Lab backtest for Wave A. source=backtest, not KEEP."""
    from src.tools.ananta_api import create_lab_run, get_lab_run

    print("\nWAVE A LAB BACKTEST")
    print("=" * 64)
    print("source = backtest. Ranking/context only. Will NOT change KEEP/WATCH.")
    print(f"strategies = {', '.join(WAVE_A)}   period = {period}")
    print("=" * 64)

    weakest = print_lab_coverage()
    if weakest is None:
        return
    if weakest < MIN_1H_BARS:
        print("Not enough 1h candles for a 1y replay (warmup is 200 bars).")
        print("In the backend venv, run this once (Kraken history download):")
        print()
        print("  cd ~/code/Ananta/backend")
        print("  source .venv/bin/activate")
        print("  python scripts/backfill_1h.py")
        print()
        print("Then type lab again. Do not treat a failed short window as strategy proof.")
        return

    payload = {
        "kind": "backtest",
        "symbols": DEFAULT_SYMBOLS,
        "period": period,
        "strategies": list(WAVE_A),
        "timeframe": "1h",
        "compare_timeframes": False,
        "exit_method": "fixed",
        "min_trades": 1,
        "label": f"Wave A {period} evidence (agent lab)",
    }
    created = create_lab_run(payload)
    if not created.get("success"):
        print(f"Could not queue lab run: {created.get('error') or created}")
        return
    run_id = (created.get("data") or {}).get("id")
    print(f"Queued run_id={run_id}  polling (LabWorker on the backend)...")

    last_status = None
    for _ in range(180):  # ~9 min
        time.sleep(3)
        got = get_lab_run(run_id)
        if not got.get("success"):
            print(f"  poll error: {got.get('error')}")
            continue
        run = got.get("data") or {}
        status = run.get("status")
        pct = run.get("progress_pct")
        if status != last_status:
            print(f"  status={status}  progress={pct}")
            last_status = status
        elif pct is not None:
            print(f"  progress={pct}", flush=True)
        if status in ("DONE", "FAILED"):
            path = _save_evidence(run)
            print("-" * 64)
            print(f"  finished: {status}")
            if run.get("error"):
                print(f"  error: {run.get('error')}")
            _summarize_result(run.get("result"))
            print(f"  saved: {path}  (source=backtest)")
            print("  KEEP still requires paper TAKEs.")
            print("=" * 64)
            return
    print("Still running. Type: lab status")
    print(f"  run_id={run_id}")


def print_lab_status():
    if not LAB_EVIDENCE.exists():
        print("No lab_evidence.json yet. Type: lab")
        return
    doc = json.loads(LAB_EVIDENCE.read_text())
    print("\nLAST LAB EVIDENCE")
    print("-" * 64)
    print(f"  source   : {doc.get('source')}  (not KEEP)")
    print(f"  run_id   : {doc.get('run_id')}")
    print(f"  status   : {doc.get('status')}")
    print(f"  period   : {doc.get('period')}")
    print(f"  saved_at : {doc.get('saved_at')}")
    _summarize_result(doc.get("result"))
    print("-" * 64)
    print()
