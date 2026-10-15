"""
Stage 1+2 — Continuous Market + Ananta Observation + Outcome backfill.

lab watch [--interval N minutes]

Each tick:
  1. Independent Market Truth (Kraken public)
  2. Ananta evaluation cycle (System Truth)
  3. Agent decision summary (WAIT/SKIP/TAKE aggregate)
  4. Co-timestamped Observation record
  5. Backfill due +15m/+1h/+4h Outcome Truth on prior rows

Does NOT enable strategies, KEEP, or mutate production code.
Ctrl+C stops the watcher only.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.tools.market_truth import capture_market_truth
from src.tools.observation_log import build_observation, append_observation, print_recent_observations

WAVE_A = ("hunter", "squeeze", "bollinger-mr")
DEFAULT_INTERVAL_MIN = 15
MIN_INTERVAL_MIN = 5
MAX_INTERVAL_MIN = 60


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _agent_decision_from_cycle(data: dict) -> Tuple[str, Dict[str, Any]]:
    results = data.get("results") or []
    if not results and data.get("symbol"):
        results = [data]

    n_take = 0
    n_skip = 0
    n_wait = 0
    n_setup = 0
    regimes: Dict[str, Any] = {}
    obs_flat: List[dict] = []

    for item in results:
        sym = item.get("symbol") or "?"
        regimes[sym] = item.get("regime") or item.get("market_regime")
        for o in item.get("strategy_observations") or []:
            obs_flat.append({**o, "symbol": sym})
            if o.get("setup_detected"):
                n_setup += 1
            dec = str(o.get("decision") or "").upper()
            if dec in ("TAKE", "ENTER", "BUY", "SELL"):
                n_take += 1
            elif dec in ("SKIP",):
                n_skip += 1
            else:
                n_wait += 1

    if n_take > 0:
        decision = "TAKE"
    elif n_setup > 0 and n_skip > 0:
        decision = "SKIP"
    else:
        decision = "WAIT"

    meta = {
        "n_symbols": len(results),
        "n_setups": n_setup,
        "n_take_obs": n_take,
        "n_skip_obs": n_skip,
        "n_wait_obs": n_wait,
        "regimes_by_symbol": regimes,
        "strategy_observations": obs_flat[:80],
    }
    return decision, meta


def capture_one_observation() -> Dict[str, Any]:
    from src.tools.ananta_api import run_evaluation_cycle, get_portfolio

    ts = _utc_now()
    obs_id = f"obs_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"

    market = capture_market_truth()

    cycle = run_evaluation_cycle()
    system: Dict[str, Any] = {
        "obs_id": obs_id,
        "ts": ts,
        "ananta_ok": bool(cycle.get("success")),
        "ananta_error": None if cycle.get("success") else (cycle.get("error") or cycle),
        "cycle_id": None,
        "ran_at": None,
        "agent_decision": "UNKNOWN",
        "regimes_by_symbol": {},
        "strategy_observations": [],
        "portfolio": None,
        "wave_a": list(WAVE_A),
        "note": "Ananta regime is a hypothesis, not ground truth",
    }

    if cycle.get("success"):
        data = cycle.get("data") or {}
        decision, meta = _agent_decision_from_cycle(data)
        system["ran_at"] = data.get("ran_at")
        system["agent_decision"] = decision
        system["regimes_by_symbol"] = meta.get("regimes_by_symbol") or {}
        system["strategy_observations"] = meta.get("strategy_observations") or []
        system["n_symbols"] = meta.get("n_symbols")
        system["n_setups"] = meta.get("n_setups")
        system["cycle_id"] = data.get("cycle_id") or (
            f"cyc_watch_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        )
        try:
            from src.tools.cycle_log import start_cycle, log_decision, log_opportunities

            cid = start_cycle(regime=None, notes=f"lab_watch obs={obs_id}")
            system["cycle_id"] = cid
            log_decision(
                cycle_id=cid,
                action=decision,
                strategy="wave-a",
                confidence=None,
                reason="lab_watch aggregate",
                status="observed",
            )
            opps = []
            for o in system["strategy_observations"]:
                if o.get("setup_detected") or str(o.get("decision") or "").upper() in ("SKIP", "TAKE"):
                    opps.append({
                        "strategy": o.get("strategy"),
                        "symbol": o.get("symbol"),
                        "decision": o.get("decision"),
                        "skip_reason": o.get("skip_reason"),
                        "setup": o.get("setup_detected"),
                        "regime": o.get("regime"),
                    })
            if opps:
                log_opportunities(
                    cycle_id=cid,
                    candidates=opps,
                    chosen_action=decision,
                    chosen_strategy="wave-a",
                )
        except Exception:
            pass

    try:
        port = get_portfolio()
        if port.get("success"):
            system["portfolio"] = port.get("data")
    except Exception:
        pass

    record = build_observation(
        system_truth=system,
        market_truth=market,
        outcome_truth=None,
        source="live_paper",
    )
    record["obs_id"] = obs_id
    ok = append_observation(record)
    record["_written"] = ok
    try:
        from src.tools.outcome_truth import backfill_outcomes
        summary = backfill_outcomes(limit=100)
        record["_outcome_backfill"] = summary
    except Exception as e:
        record["_outcome_backfill"] = {"ok": False, "error": str(e)}
    return record


def _print_tick(record: dict) -> None:
    st = record.get("system_truth") or {}
    mt = record.get("market_truth") or {}
    btc = mt.get("btc") or {}
    eth = mt.get("eth") or {}
    print()
    print(f"[{record.get('ts', '')[:19]}] Observation {record.get('obs_id')}")
    print(
        f"  MARKET  source={mt.get('source')} ok={mt.get('ok')}  "
        f"BTC={btc.get('price')} (1h={btc.get('ret_1h_pct')}% trend={btc.get('trend_flag')})  "
        f"ETH={eth.get('price')}  breadth={mt.get('breadth_1h_pct_positive')}"
    )
    print(
        f"  SYSTEM  decision={st.get('agent_decision')}  cycle={st.get('cycle_id')}  "
        f"setups={st.get('n_setups')}  ananta_ok={st.get('ananta_ok')}"
    )
    regimes = st.get("regimes_by_symbol") or {}
    if regimes:
        bits = [f"{k.split('/')[0]}={v}" for k, v in list(regimes.items())[:6]]
        print(f"  REGIME(hypothesis)  {', '.join(bits)}")
    bf = record.get("_outcome_backfill") or {}
    if bf.get("ok"):
        print(f"  OUTCOME  backfill filled={bf.get('filled')} scanned={bf.get('scanned')} (Stage 2)")
    else:
        print(f"  OUTCOME  backfill pending/error={bf.get('error') or 'n/a'}")
    print(f"  saved={record.get('_written')}  file=observation_log.jsonl")
    print("  (log only — no KEEP, no strategy mutation)")


def run_lab_watch(interval_min: int = DEFAULT_INTERVAL_MIN) -> None:
    interval_min = max(MIN_INTERVAL_MIN, min(MAX_INTERVAL_MIN, int(interval_min)))
    seconds = interval_min * 60
    print()
    print("LAB WATCH — Stage 1+2 continuous Observation + Outcome backfill")
    print("=" * 64)
    print(f"interval = {interval_min} min  (range {MIN_INTERVAL_MIN}–{MAX_INTERVAL_MIN})")
    print("Each tick: Market Truth + Ananta cycle + decision + due Outcome fill")
    print("Ananta regime = hypothesis. No auto ENABLE/KEEP/mutation.")
    print("Ctrl+C stops the watcher (backend keeps running).")
    print("=" * 64)

    n = 0
    try:
        while True:
            n += 1
            print(f"\n--- tick {n} ---")
            try:
                rec = capture_one_observation()
                _print_tick(rec)
            except Exception as e:
                print(f"  tick error: {e}")
            print(f"  sleeping {interval_min} min ...")
            time.sleep(seconds)
    except KeyboardInterrupt:
        print()
        print("lab watch stopped.")
        print_recent_observations(limit=5)
        print("Tip: lab observations   → review ledger")
        print("     lab outcomes       → backfill + show forward returns")
        print("     cycle / mark       → still available for human marks")
