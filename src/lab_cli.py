"""Wave A strategy DNA + Research Lab 1y evidence (source=backtest, not KEEP)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

WAVE_A = ("hunter", "squeeze", "bollinger-mr")
LAB_EVIDENCE = Path("lab_evidence.json")
LAB_RUN_ID = Path("lab_run_id.txt")
DEFAULT_SYMBOLS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "XRP/USD",
    "PAXG/USD", "LINK/USD", "AAVE/USD", "ARB/USD", "RENDER/USD",
]
MIN_1H_BARS = 250
USABLE_1Y_BARS = 6000


def handle_lab_command(user_input: str) -> bool:
    raw = (user_input or "").strip().lower()
    if raw != "lab" and not raw.startswith("lab "):
        return False
    rest = raw[4:].strip() if raw.startswith("lab ") else ""
    if rest in ("", "1y", "backtest"):
        run_wave_a_lab("1y")
    elif rest in ("status", "evidence"):
        print_lab_status()
    elif rest in ("wait", "attach", "poll"):
        rid = _known_run_id()
        active = _active_lab_run()
        if active:
            rid = active.get("id") or rid
            _remember_run(rid)
        if not rid:
            print("No run to wait on. Type: lab")
        else:
            print(f"Attaching to {rid}. Ctrl+C detaches.")
            poll_lab_run(rid)
    elif rest in ("coverage",):
        print_lab_coverage()
    elif rest.startswith("watch"):
        parts = rest.split()
        interval = 15
        for i, p in enumerate(parts):
            if p in ("--interval", "-i") and i + 1 < len(parts):
                try:
                    interval = int(parts[i + 1])
                except ValueError:
                    pass
            elif p.isdigit():
                interval = int(p)
        from src.lab_watch import run_lab_watch
        run_lab_watch(interval)
    elif rest in ("observations", "obs", "observation"):
        from src.tools.observation_log import print_recent_observations
        print_recent_observations(limit=12)
    elif rest in ("outcomes", "outcome", "forward"):
        from src.tools.outcome_truth import backfill_outcomes, print_outcomes_summary
        summary = backfill_outcomes(limit=200)
        print(f"→ outcomes backfill: filled={summary.get('filled')} scanned={summary.get('scanned')} ok={summary.get('ok')}")
        if summary.get("error"):
            print(f"  error: {summary.get('error')}")
        print_outcomes_summary(limit=10)
    elif rest in ("once", "tick", "observe"):
        from src.lab_watch import capture_one_observation, _print_tick
        _print_tick(capture_one_observation())
    else:
        print("lab | lab watch [N] | lab once | lab outcomes | lab observations | lab wait | lab status | lab coverage")
    return True


def print_lab_coverage():
    from src.tools.ananta_api import get_lab_coverage
    cov = get_lab_coverage()
    if not cov.get("success"):
        print(f"Coverage failed: {cov.get('error') or cov}")
        return None
    data = cov.get("data") or {}
    rows = data.get("symbols") or []
    print("\nLAB CANDLE COVERAGE (1h — what Lab/API actually read)")
    print("-" * 72)
    weakest = None
    usable_n = 0
    for row in rows:
        n = row.get("bars_1h") or 0
        span = row.get("span_days")
        gaps = row.get("gap_count")
        usable = row.get("usable_1y")
        if usable:
            usable_n += 1
        flag = "OK_1Y" if usable else "SHORT"
        print(f"  {str(row.get('symbol')):<12} 1h={n:<6} span={span}d  {row.get('from') or '—'} → {row.get('to') or '—'}  gaps={gaps}  {flag}")
        if weakest is None or n < weakest:
            weakest = n
    print("-" * 72)
    print(f"  weakest 1h: {weakest}   usable_1y: {usable_n}/{len(rows)}")
    print()
    return weakest, rows


def run_wave_a_lab(period: str = "1y"):
    from src.tools.ananta_api import create_lab_run
    print("\nWAVE A LAB BACKTEST")
    print("source = backtest. Will NOT change KEEP/WATCH.")
    cov = print_lab_coverage()
    if cov is None:
        return
    weakest, rows = cov if isinstance(cov, tuple) else (cov, [])
    if weakest is None:
        return
    usable_all = bool(rows) and all(r.get("usable_1y") for r in rows)
    if not usable_all:
        print("P0 not met. Run scripts/backfill_1h.py then lab coverage.")
        return
    active = _active_lab_run()
    if active:
        rid = active.get("id")
        print(f"LabWorker already {active.get('status')} run_id={rid}")
        _remember_run(rid)
        poll_lab_run(rid)
        return
    payload = {"kind": "backtest", "symbols": DEFAULT_SYMBOLS, "period": period, "strategies": list(WAVE_A), "timeframe": "1h", "compare_timeframes": False, "exit_method": "fixed", "min_trades": 1, "label": f"Wave A {period} evidence (agent lab)"}
    created = create_lab_run(payload)
    if not created.get("success"):
        print(f"Could not queue: {created.get('error') or created}")
        return
    run_id = (created.get("data") or {}).get("id")
    _remember_run(run_id)
    print(f"Queued run_id={run_id}")
    poll_lab_run(run_id)


def _remember_run(run_id: str):
    if run_id:
        LAB_RUN_ID.write_text(run_id.strip())


def _known_run_id():
    if LAB_RUN_ID.exists():
        rid = LAB_RUN_ID.read_text().strip()
        if rid:
            return rid
    if LAB_EVIDENCE.exists():
        try:
            return (json.loads(LAB_EVIDENCE.read_text()) or {}).get("run_id")
        except Exception:
            return None
    return None


def _active_lab_run():
    from src.tools.ananta_api import list_lab_runs
    listed = list_lab_runs(limit=20)
    if not listed.get("success"):
        return None
    for run in (listed.get("data") or {}).get("runs") or []:
        if run.get("status") in ("RUNNING", "QUEUED") and run.get("kind") == "backtest":
            return run
    return None


def _save_evidence(run: dict):
    payload = {"source": "backtest", "saved_at": datetime.now(timezone.utc).isoformat(), "wave_a": list(WAVE_A), "run_id": run.get("id"), "status": run.get("status"), "kind": run.get("kind"), "period": run.get("period"), "strategies": run.get("strategies"), "symbols": run.get("symbols"), "result": run.get("result"), "error": run.get("error"), "note": "BACKTEST context only. Does not promote KEEP."}
    LAB_EVIDENCE.write_text(json.dumps(payload, indent=2, default=str))
    return LAB_EVIDENCE


def _summarize_result(result) -> None:
    if not result:
        print("  (no result payload yet)")
        return
    if isinstance(result, dict) and result.get("error"):
        print(f"  error: {result.get('error')}")
        return
    if isinstance(result, dict):
        cards = result.get("strategies") or result.get("per_strategy") or result.get("cards")
        per_symbol = result.get("per_symbol") or result.get("symbols")
        if isinstance(cards, list):
            for c in cards:
                if isinstance(c, dict):
                    key = c.get("strategy") or c.get("key") or c.get("name")
                    print(f"  {key}: trades={c.get('trades')} ret={c.get('total_return_pct')} wr={c.get('win_rate_pct')}")
            return
        if isinstance(per_symbol, dict):
            for sym, m in list(per_symbol.items())[:12]:
                if isinstance(m, dict):
                    print(f"  {sym}: trades={m.get('trades')} ret={m.get('total_return_pct')} wr={m.get('win_rate_pct')}")
            return
        print(f"  result keys: {list(result.keys())[:12]}")


def poll_lab_run(run_id: str):
    from src.tools.ananta_api import get_lab_run
    last_key = None
    started = time.time()
    try:
        while True:
            got = get_lab_run(run_id)
            if not got.get("success"):
                print(f"  poll error: {got.get('error')}")
                time.sleep(5)
                continue
            run = got.get("data") or {}
            status = run.get("status")
            pct = run.get("progress_pct")
            key = (status, pct)
            if key != last_key:
                print(f"  status={status}  progress={pct}  elapsed={int(time.time()-started)}s", flush=True)
                last_key = key
            if status in ("DONE", "FAILED"):
                path = _save_evidence(run)
                print(f"  finished: {status}")
                if run.get("error"):
                    print(f"  error: {run.get('error')}")
                _summarize_result(run.get("result"))
                print(f"  saved: {path}  (source=backtest)")
                print("  KEEP still requires paper TAKEs.")
                return
            time.sleep(10)
    except KeyboardInterrupt:
        print(f"  Detached. Backend still running run_id={run_id}")


def print_lab_status():
    from src.tools.ananta_api import get_lab_run
    run_id = _known_run_id()
    active = _active_lab_run()
    if active and not run_id:
        run_id = active.get("id")
        _remember_run(run_id)
    if not run_id:
        print("No lab run id. Type: lab")
        return
    got = get_lab_run(run_id)
    if not got.get("success"):
        print(f"Could not fetch run {run_id}: {got.get('error') or got}")
        return
    run = got.get("data") or {}
    print("\nLAB RUN (live)")
    print(f"  run_id   : {run.get('id') or run_id}")
    print(f"  status   : {run.get('status')}")
    print(f"  progress : {run.get('progress_pct')}")
    if run.get("status") in ("DONE", "FAILED"):
        _save_evidence(run)
        _summarize_result(run.get("result"))
    else:
        print("  still running — type: lab wait")


def print_strategy_dna():
    from src.tools.ananta_api import get_strategy_registry, get_strategy_status
    print("\nSTRATEGY DNA (from Ananta registry — facts, not Agent ranking)")
    reg = get_strategy_registry()
    if not reg.get("success"):
        print(f"Could not fetch registry: {reg.get('error') or reg}")
        return
    print("Wave A: hunter, squeeze, bollinger-mr (human-locked lab set)")
    for s in reg.get("strategies") or []:
        k = s.get("key") or s.get("id")
        print(f"  {k}: {(s.get('dna') or {}).get('purpose') or s.get('description') or ''}")


def print_understanding_report():
    from src.tools.ananta_api import get_lab_coverage, get_strategy_knowledge
    print("\nSTRATEGY UNDERSTANDING REPORT")
    kn = get_strategy_knowledge()
    if not kn.get("success"):
        print(f"Knowledge Object failed: {kn.get('error') or kn}")
        return
    for s in (kn.get("data") or {}).get("strategies") or []:
        print(f"{s.get('name')} ({s.get('strategy_id')}) understanding={s.get('understanding_confidence')} evidence={s.get('evidence_confidence')}")
        for c in s.get("contradictions") or []:
            print(f"  CONTRADICTION: {c.get('agent_must_say')}")
    print("Do not KEEP. Do not enable the other 12.")
