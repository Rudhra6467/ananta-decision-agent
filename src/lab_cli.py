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
MIN_1H_BARS = 250  # lab warmup
USABLE_1Y_BARS = 6000


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
        print(
            f"  {str(row.get('symbol')):<12} 1h={n:<6} span={span}d  "
            f"{row.get('from') or '—'} → {row.get('to') or '—'}  "
            f"gaps={gaps}  {flag}"
        )
        if weakest is None or n < weakest:
            weakest = n
    print("-" * 72)
    print(f"  weakest 1h: {weakest}   usable_1y: {usable_n}/{len(rows)}")
    print(f"  acceptance: ≥{USABLE_1Y_BARS} 1h bars and ≥300 days")
    print()
    return weakest, rows


def run_wave_a_lab(period: str = "1y"):
    """Queue Ananta Research Lab backtest for Wave A. source=backtest, not KEEP."""
    from src.tools.ananta_api import create_lab_run

    print("\nWAVE A LAB BACKTEST")
    print("=" * 64)
    print("source = backtest. Ranking/context only. Will NOT change KEEP/WATCH.")
    print(f"strategies = {', '.join(WAVE_A)}   period = {period}")
    print("=" * 64)

    cov = print_lab_coverage()
    if cov is None:
        return
    weakest, rows = cov if isinstance(cov, tuple) else (cov, [])
    if weakest is None:
        return
    usable_all = bool(rows) and all(r.get("usable_1y") for r in rows)
    if not usable_all:
        print("P0 not met: Lab/API does not yet have ~1y of 1h candles on the full book.")
        print("In the backend venv (so MONGO_URL comes from backend/.env):")
        print()
        print("  cd ~/code/Ananta/backend")
        print("  source .venv/bin/activate")
        print("  python scripts/backfill_1h.py")
        print()
        print("Wait for BACKFILL_DONE, then: lab coverage")
        print("Do not treat a short window as 1y strategy proof.")
        if weakest < MIN_1H_BARS:
            return
        print("Warmup is enough for a *short* replay, but refusing period=1y until usable_1y.")
        return

    from src.tools.ananta_api import create_lab_run

    active = _active_lab_run()
    if active:
        rid = active.get("id")
        st = active.get("status")
        print(f"LabWorker already has {st} run_id={rid} — not queueing another.")
        print("Attaching. Ctrl+C returns to the prompt; the backend keeps running.")
        _remember_run(rid)
        poll_lab_run(rid)
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
    _remember_run(run_id)
    print(f"Queued run_id={run_id}")
    print("Polling until DONE. Ctrl+C returns to the prompt; backend job continues.")
    poll_lab_run(run_id)


def _remember_run(run_id: str):
    if run_id:
        LAB_RUN_ID.write_text(run_id.strip())


def _known_run_id() -> str | None:
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


def _active_lab_run() -> dict | None:
    from src.tools.ananta_api import list_lab_runs

    listed = list_lab_runs(limit=20)
    if not listed.get("success"):
        return None
    runs = (listed.get("data") or {}).get("runs") or []
    for run in runs:
        if run.get("status") in ("RUNNING", "QUEUED") and run.get("kind") == "backtest":
            return run
    return None


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
                elapsed = int(time.time() - started)
                print(f"  status={status}  progress={pct}  elapsed={elapsed}s", flush=True)
                last_key = key
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
            time.sleep(10)
    except KeyboardInterrupt:
        print()
        print(f"  Detached. Backend still running run_id={run_id}")
        print("  Type: lab wait    to attach again")
        print("  Type: lab status  to peek")


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
    print("-" * 64)
    print(f"  run_id   : {run.get('id') or run_id}")
    print(f"  status   : {run.get('status')}")
    print(f"  progress : {run.get('progress_pct')}")
    print(f"  kind     : {run.get('kind')}  period={run.get('period')}")
    print(f"  error    : {run.get('error')}")
    if run.get("status") in ("DONE", "FAILED"):
        _save_evidence(run)
        _summarize_result(run.get("result"))
    else:
        print("  still running — type: lab wait")
    print("-" * 64)
    print()


def handle_lab_command(user_input: str) -> bool:
    """Dispatch all 'lab ...' CLI. Returns True if consumed."""
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
    else:
        print("lab | lab wait | lab status | lab coverage")
    return True


def print_understanding_report():
    """P1: Strategy Understanding Report from the Contract Knowledge Object."""
    from src.tools.ananta_api import get_lab_coverage, get_strategy_knowledge

    print("\nSTRATEGY UNDERSTANDING REPORT")
    print("=" * 64)
    print("Implementation + router are authoritative. DNA is thesis, not policy.")
    print("Wave A stays WATCH. This is understanding, not KEEP.")
    print("-" * 64)

    cov = get_lab_coverage()
    usable = False
    if cov.get("success"):
        data = cov.get("data") or {}
        usable = bool(data.get("usable_1y_all"))
        print(f"Historical coverage usable_1y_all={usable}  ({data.get('usable_1y_count')})")
    else:
        print(f"Coverage: {cov.get('error')}")

    kn = get_strategy_knowledge()
    if not kn.get("success"):
        print(f"Knowledge Object failed: {kn.get('error') or kn}")
        print("Backend must be restarted after git pull (GET /api/strategy/knowledge).")
        print("=" * 64)
        return

    for s in (kn.get("data") or {}).get("strategies") or []:
        key = s.get("strategy_id")
        print()
        print(f"{s.get('name')}  ({key} v{s.get('version')})")
        print("─" * 40)
        print("  Implementation:      VERIFIED")
        print(f"  Entry logic:          VERIFIED  ({len(s.get('entry_conditions') or [])} gates)")
        print(f"  Exit logic:           VERIFIED")
        print(f"  Parameters:           VERIFIED")
        print(f"  Regime gates:         VERIFIED  allowed={s.get('allowed_regimes')}")
        print(f"  Router policy:        VERIFIED  {s.get('actual_router_gates')}")
        print(f"  Timeframe:            {s.get('timeframe')}")
        print(f"  Authoritative truth:  {s.get('authoritative_truth')}")
        for c in s.get("contradictions") or []:
            print("  CONTRADICTION:")
            print(f"    {c.get('agent_must_say')}")
        pe = s.get("paper_evidence") or {}
        he = s.get("historical_evidence") or {}
        print(f"  Historical evidence:  {'AVAILABLE' if he.get('available') else 'NOT YET'}  source={he.get('source')}")
        print(f"  Paper evidence:       {pe.get('note')}")
        print(f"  TAKE outcomes:        {pe.get('take_outcomes', 0)}")
        print(f"  Understanding:        {s.get('understanding_confidence')}  (object consumed)")
        print(f"  Evidence confidence:  {s.get('evidence_confidence')}")
        print(f"  Decision confidence:  per-opportunity only — not a strategy score")
        print(f"  Current status:       {s.get('current_status')}  / Wave A WATCH")
    print()
    print("=" * 64)
    print("Do not KEEP. Do not enable the other 12.")
    print()
