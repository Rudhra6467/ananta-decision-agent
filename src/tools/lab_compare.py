"""
Live vs historical comparison — same observation_v0, two sources.

Does not mix files. Does not KEEP.
Live TAKE ≠ historical TAKE-equivalent.
BTC path ≠ strategy PnL.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.tools.audit_truth import audit_observations
from src.tools.observation_log import OBSERVATION_LOG, REPLAY_LOG

WAVE_A = ("hunter", "squeeze", "bollinger-mr")
COMPARE_REPORT = Path("compare_live_vs_historical.json")


def _strategy_counts(source: str) -> Dict[str, Counter]:
    path = REPLAY_LOG if source == "replay" else OBSERVATION_LOG
    per = {k: Counter() for k in WAVE_A}
    if not path.exists():
        return per
    for line in path.read_text().strip().splitlines():
        try:
            obs = json.loads(line)
        except Exception:
            continue
        st = obs.get("system_truth") or {}
        for o in st.get("strategy_observations") or []:
            key = str(o.get("strategy") or "")
            if key not in per:
                continue
            dec = str(o.get("decision") or "").upper()
            per[key][dec] += 1
            if o.get("setup_detected"):
                per[key]["setups"] += 1
            skip = str(o.get("skip_reason") or "")
            if skip:
                per[key][f"skip:{skip}"] += 1
    return per


def _pct(part, whole) -> Optional[float]:
    if not whole:
        return None
    return round(100.0 * part / whole, 1)


def build_compare() -> dict:
    live = audit_observations(source="live")
    hist = audit_observations(source="replay")
    live_st = _strategy_counts("live")
    hist_st = _strategy_counts("replay")

    def slice_audit(a: dict) -> dict:
        n = a.get("n_observations") or 0
        ra = a.get("regime_audit") or {}
        da = a.get("decision_audit") or {}
        return {
            "n": n,
            "n_with_fwd_1h": a.get("n_with_fwd_1h"),
            "decisions": a.get("decisions"),
            "regime_audit": ra,
            "regime_misclassified_pct": _pct(ra.get("MISCLASSIFIED") or 0, n),
            "regime_supported_pct": _pct(ra.get("SUPPORTED") or 0, n),
            "decision_audit": da,
            "mean_fwd_1h_after_skip_wait": a.get("mean_fwd_1h_after_skip_wait"),
            "mean_fwd_1h_after_TAKE": a.get("mean_fwd_1h_after_take"),
            "hunter_skip_reasons_top": a.get("hunter_skip_reasons_top"),
        }

    report = {
        "schema": "compare_v0",
        "ts": datetime.now(timezone.utc).isoformat(),
        "live": slice_audit(live),
        "historical": slice_audit(hist),
        "strategy_live": {k: dict(v) for k, v in live_st.items()},
        "strategy_historical": {k: dict(v) for k, v in hist_st.items()},
        "incommensurable": [
            "Live = multi-symbol 15m paper ticks. Historical = BTC 1h stride=4 TAKE-equivalent.",
            "Live TAKE is a paper/agent take. Historical TAKE is setup AND Wave A gate — not a fill.",
            "Hunter skip counts on live are per-symbol flattened; do not compare raw 428 vs 104.",
            "MISCLASSIFIED is slow BTC market label vs fast 1h flags — same clock problem on both files.",
        ],
        "laws": {
            "do_not_mix_files": True,
            "btc_path_is_not_strategy_pnl": True,
            "historical_take_is_not_keep": True,
            "no_auto_mutation": True,
            "wave_a_watch": True,
        },
        "next": "S5 proposed experiments only after this compare is reviewed. Human approval. Wave A WATCH.",
    }
    return report


def print_compare(report: Optional[dict] = None) -> None:
    report = report or build_compare()
    COMPARE_REPORT.write_text(json.dumps(report, indent=2, default=str))
    live = report.get("live") or {}
    hist = report.get("historical") or {}

    print()
    print("LIVE vs HISTORICAL  (same schema, two sources — not KEEP)")
    print("=" * 64)
    print("live_paper  vs  historical_lab. Do not mix. Wave A stays WATCH.")
    print("-" * 64)
    print(f"  live file        : {OBSERVATION_LOG}  n={live.get('n')}  +1h={live.get('n_with_fwd_1h')}")
    print(f"  historical file  : {REPLAY_LOG}  n={hist.get('n')}  +1h={hist.get('n_with_fwd_1h')}")
    print("-" * 64)
    print("INCOMMENSURABLE (read before the numbers)")
    for line in report.get("incommensurable") or []:
        print(f"  • {line}")
    print("-" * 64)
    print("DECISIONS")
    print(f"  live        : {live.get('decisions')}")
    print(f"  historical  : {hist.get('decisions')}  (TAKE = TAKE-eq, not paper TAKE)")
    print("-" * 64)
    print("REGIME AUDIT  (Ananta BTC market label vs independent flags)")
    print(f"  live        : {live.get('regime_audit')}  "
          f"MIS={live.get('regime_misclassified_pct')}%  SUP={live.get('regime_supported_pct')}%")
    print(f"  historical  : {hist.get('regime_audit')}  "
          f"MIS={hist.get('regime_misclassified_pct')}%  SUP={hist.get('regime_supported_pct')}%")
    print("-" * 64)
    print("DECISION AUDIT  (SKIP/WAIT vs BTC +1h path — opportunity cost, not PnL)")
    print(f"  live        : {live.get('decision_audit')}")
    print(f"  historical  : {hist.get('decision_audit')}")
    print(f"  mean +1h sit-out live={live.get('mean_fwd_1h_after_skip_wait')}%  "
          f"hist={hist.get('mean_fwd_1h_after_skip_wait')}%")
    print(f"  mean +1h TAKE      live={live.get('mean_fwd_1h_after_TAKE')}%  "
          f"hist={hist.get('mean_fwd_1h_after_TAKE')}%  (hist TAKE-eq mostly bollinger-mr)")
    print("-" * 64)
    print("STRATEGY  (counts; live is multi-symbol flattened)")
    sl, sh = report.get("strategy_live") or {}, report.get("strategy_historical") or {}
    for key in WAVE_A:
        print(f"  {key}")
        print(f"      live : {dict(sl.get(key) or {})}")
        print(f"      hist : {dict(sh.get(key) or {})}")
    print("-" * 64)
    print("ALLOWED AS FINDINGS (not experiments, not KEEP)")
    print("  1. Hunter fires setups in TREND_UP; Wave A/router allow REVERSAL only — measured on 1y.")
    print("  2. Hunter is almost silent in allowed REVERSAL (hist TAKE-eq=4 on stride=4).")
    print("  3. Squeeze is rare; gates aligned with COMPRESSION.")
    print("  4. Bollinger-MR dominates hist TAKE-eq and is still a shadow/re-test, not a router executor.")
    print("  5. Sit-out +1h is a wash at 1y; overnight live window was slightly protective. Neither promotes.")
    print("  6. MISCLASSIFIED ~20–26% is slow market-label vs fast 1h flags on both clocks.")
    print("-" * 64)
    print("NOT ALLOWED")
    print("  Hunter v1.1 from this compare. Extra agents. TradingAgents clone. KEEP/CUT.")
    print("  S5 = proposed experiments after this review + human approval.")
    print(f"  saved: {COMPARE_REPORT}")
    print("=" * 64)
    print()
