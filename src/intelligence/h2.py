"""S5-H2 — Hunter REVERSAL gate histogram. Measurement only.

Reads existing observation ledgers. Does not mutate Hunter.
Hist replay already stores evaluate_primary.reason_codes in hunter rationale.
Live ticks get reason_codes after Ananta cycle-obs plumbing is deployed.

CLI: lab h2
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from src.tools.observation_log import OBSERVATION_LOG, REPLAY_LOG, _read_jsonl

HUNTER = "hunter"
REVERSAL = "REVERSAL"


def histogram(source: str = "replay") -> Dict[str, Any]:
    path = REPLAY_LOG if source in ("replay", "historical", "historical_lab") else OBSERVATION_LOG
    tag = "historical_lab" if path == REPLAY_LOG else "live_paper"
    rows = _read_jsonl(path)
    if not rows:
        return {
            "ok": True,
            "h2": "APPROVED_MEASUREMENT",
            "source": tag,
            "n": 0,
            "data_gap": True,
            "keep": False,
            "note": f"{path} empty. Not a Hunter rewrite. Wave A stays WATCH.",
        }

    regime_n = Counter()
    reversal_codes = Counter()
    reversal_dec = Counter()
    reversal_profiles = Counter()
    coded = 0
    uncoded = 0
    reversal_n = 0
    hunter_n = 0
    take_eq = 0

    for obs in rows:
        st = obs.get("system_truth") or {}
        for o in st.get("strategy_observations") or []:
            if (o.get("strategy") or o.get("strategy_key") or "").lower() != HUNTER:
                continue
            hunter_n += 1
            regime = _regime(o, st)
            regime_n[regime] += 1
            if o.get("decision") in ("TAKE", "ENTER") or (
                o.get("setup_detected") and not _filtered(o)
            ):
                take_eq += 1
            if regime != REVERSAL:
                continue
            reversal_n += 1
            reversal_dec[str(o.get("decision") or "?")] += 1
            prof = o.get("entry_profile")
            if prof:
                reversal_profiles[str(prof)] += 1
            codes = _codes(o)
            if codes == ["UNCODED"]:
                uncoded += 1
            else:
                coded += 1
            for c in codes:
                reversal_codes[c] += 1

    top = reversal_codes.most_common(16)
    return {
        "ok": True,
        "h2": "APPROVED_MEASUREMENT",
        "source": tag,
        "n_obs": len(rows),
        "n_hunter_rows": hunter_n,
        "n_reversal": reversal_n,
        "n_take_eq_any_regime": take_eq,
        "data_gap": reversal_n == 0,
        "codes_present": coded > 0,
        "n_coded": coded,
        "n_uncoded": uncoded,
        "hunter_regime_counts": dict(regime_n),
        "reversal_decisions": dict(reversal_dec),
        "reversal_profiles": dict(reversal_profiles),
        "reason_code_histogram": dict(top),
        "top_killers": [k for k, _ in top if str(k).startswith("REJECTED_")][:8],
        "keep": False,
        "loosen_gates": False,
        "laws": {
            "measurement_only": True,
            "no_rsi_loosen": True,
            "no_vcp_disable": True,
            "no_htf_disable": True,
            "no_trend_up_enable": True,
            "histogram_is_not_a_rewrite": True,
        },
        "read": (
            "Which STABILIZED_REVERSAL gates fire on REVERSAL bars. "
            "A frequent REJECTED_* is a map cell, not a license to disable that gate. "
            "UNCODED live rows = Ananta has not yet attached reason_codes to cycle obs."
        ),
        "note": "H2 report. Not KEEP. Not Hunter v1.1. Wave A stays WATCH.",
    }


def print_h2(source: str = "replay") -> Dict[str, Any]:
    report = histogram(source)
    print(f"\nH2 HUNTER REVERSAL GATES  ({report.get('source')})")
    print("=" * 64)
    print("Measurement only. Histogram ≠ rewrite. Do not loosen RSI / VCP / HTF.")
    print(
        f"  obs={report.get('n_obs')}  hunter_rows={report.get('n_hunter_rows')}  "
        f"REVERSAL={report.get('n_reversal')}  coded={report.get('n_coded')}  "
        f"uncoded={report.get('n_uncoded')}"
    )
    print(f"  hunter regimes: {report.get('hunter_regime_counts')}")
    print(f"  REVERSAL decisions: {report.get('reversal_decisions')}")
    if report.get("reversal_profiles"):
        print(f"  REVERSAL profiles: {report.get('reversal_profiles')}")
    print("-" * 64)
    hist = report.get("reason_code_histogram") or {}
    if not hist:
        print("  DATA_GAP — no codes. Hist replay rationale should have REJECTED_*.")
        print("  Live: deploy Ananta cycle-obs reason_codes, do not stop the watcher long.")
    else:
        print("  reason_codes on REVERSAL (rank = how often that gate kills)")
        n_rev = max(int(report.get("n_reversal") or 1), 1)
        for i, (code, n) in enumerate(hist.items(), 1):
            pct = round(100.0 * n / n_rev, 1)
            print(f"    {i:>2}. {code:<36} n={n:<5} {pct}% of REVERSAL rows")
        killers = report.get("top_killers") or []
        if killers:
            print(f"  top killers: {', '.join(killers)}")
    print("-" * 64)
    print("  KEEP=False  loosen_gates=False  TREND_UP still rejected as live enable")
    print("  Next: leave watch running. Do not spend a week retuning Hunter.")
    print("=" * 64)
    print()
    return report


def _regime(row: dict, st: dict) -> str:
    r = row.get("regime")
    if isinstance(r, dict):
        r = r.get("asset") or r.get("regime") or r.get("market")
    if r:
        return str(r).upper()
    by = st.get("regimes_by_symbol") or {}
    sym = row.get("symbol") or "BTC/USD"
    slot = by.get(sym) or by.get("BTC/USD") or {}
    if isinstance(slot, dict):
        return str(slot.get("asset") or slot.get("regime") or "?").upper()
    if slot:
        return str(slot).upper()
    return "?"


def _filtered(row: dict) -> bool:
    s = str(row.get("skip_reason") or "").upper()
    return s == "REGIME_FILTERED" or s.startswith("REGIME_FILTERED")


def _codes(row: dict) -> List[str]:
    raw = row.get("reason_codes")
    if isinstance(raw, list) and raw:
        return [str(c).strip() for c in raw if str(c).strip()]
    rat = str(row.get("rationale") or "")
    parts = [p.strip() for p in rat.split(",") if p.strip()]
    rejected = [p for p in parts if p.startswith("REJECTED_")]
    if rejected:
        return rejected
    skip = str(row.get("skip_reason") or "").strip()
    if skip:
        return [skip]
    return ["UNCODED"]
