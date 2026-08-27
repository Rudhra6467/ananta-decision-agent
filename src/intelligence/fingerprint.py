"""Market Truth fingerprints v0 — structured flags, not chart similarity.

Attaches a coarse fingerprint to every setup_record:
  trend | compression | ret_1h bin | independent label

Then cross-tabs TAKE vs COSTLY / PROTECTIVE / WASH.
Does not KEEP. Does not search similar charts. Does not rank strategies.

CLI: lab fingerprints [live|replay] [strategy]

v0.1: strategy-conditioned slices. Mixed tables confound
Bollinger TAKE-eq with Hunter TREND_UP refusals.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.setup_memory import extract
from src.tools.audit_truth import _independent_label

VERSION = "FP-v0.1"
REPORT_PATH = Path("fingerprint_report.json")
MIN_KEY_N = 5
MIN_SLICE_KEY_N = 3
SLICE_ORDER = ("hunter", "squeeze", "bollinger-mr", "continuation")


def fingerprints(source: str = "replay") -> Dict[str, Any]:
    mem = extract(source)
    records = mem.get("records") or []
    tagged = []
    n_gap = 0
    for rec in records:
        fp = from_record(rec)
        rec = dict(rec)
        rec["fingerprint"] = fp
        tagged.append(rec)
        if fp.get("data_gap"):
            n_gap += 1

    by_trend = _xtab(tagged, lambda r: r["fingerprint"]["trend"])
    by_comp = _xtab(tagged, lambda r: r["fingerprint"]["compression"])
    by_label = _xtab(tagged, lambda r: r["fingerprint"]["independent_label"])
    by_ret = _xtab(tagged, lambda r: r["fingerprint"]["ret_1h_bin"])
    by_key = _xtab(tagged, lambda r: r["fingerprint"]["key"])
    keys = {k: v for k, v in by_key.items() if v["n"] >= MIN_KEY_N}
    by_strategy = _strategy_slices(tagged)

    report = {
        "ok": True,
        "schema": "market_fingerprint_v0",
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": mem.get("source"),
        "n_setups": len(tagged),
        "n_data_gap": n_gap,
        "keep": False,
        "similarity": False,
        "ranker": False,
        "by_trend": by_trend,
        "by_compression": by_comp,
        "by_independent_label": by_label,
        "by_ret_1h_bin": by_ret,
        "by_key": keys,
        "by_strategy": by_strategy,
        "laws": {
            "fingerprint_is_not_chart_similarity": True,
            "fingerprint_is_not_keep": True,
            "ananta_regime_is_not_the_fingerprint": True,
            "sparse_keys_are_anecdote": True,
            "costly_on_a_flag_is_not_trend_up_enable": True,
            "mixed_table_is_confounded": True,
            "strategy_slice_is_not_keep": True,
        },
        "note": (
            "v0.1 strategy slices. Mixed rollup confounds Bollinger TAKE-eq with "
            "Hunter refusals. A slice is a map, not KEEP."
        ),
    }
    slim = {k: v for k, v in report.items()}
    try:
        REPORT_PATH.write_text(json.dumps(slim, indent=2, default=str))
        report["saved"] = str(REPORT_PATH)
    except Exception:
        report["saved"] = None
    return report


def print_fingerprints(source: str = "replay", strategy: Optional[str] = None) -> Dict[str, Any]:
    report = fingerprints(source)
    want = (strategy or "").lower().strip() or None
    print(f"\nMARKET TRUTH FINGERPRINTS  {report.get('version')}  ({report.get('source')})")
    print("=" * 64)
    print("Structured flags. Not similarity. Not KEEP. Strategy slices ≠ mixed rollup.")
    print(
        f"  setups={report.get('n_setups')}  data_gap={report.get('n_data_gap')}  "
        f"keep=False"
    )
    if not want:
        print("-" * 64)
        print("  ROLLUP (all strategies — confounded. Read slices below.)")
        _print_xtab("BY TREND", report.get("by_trend") or {})
        _print_xtab("BY INDEPENDENT LABEL", report.get("by_independent_label") or {})
    print("-" * 64)
    slices = report.get("by_strategy") or {}
    order = [k for k in SLICE_ORDER if k in slices] + [k for k in slices if k not in SLICE_ORDER]
    shown = 0
    for key in order:
        if want and key != want:
            continue
        shown += 1
        sl = slices[key]
        print(
            f"  {key:<14} n={sl.get('n')}  TAKE={sl.get('TAKE')}  "
            f"COSTLY={sl.get('COSTLY')}  PROT={sl.get('PROTECTIVE')}  WASH={sl.get('WASH')}"
        )
        _print_xtab("    trend", sl.get("by_trend") or {})
        _print_xtab("    independent", sl.get("by_independent_label") or {})
        keys = sl.get("by_key") or {}
        if keys:
            print(f"    keys n>={MIN_SLICE_KEY_N}")
            for k, row in sorted(keys.items(), key=lambda kv: -kv[1]["n"]):
                print(f"      {_fmt_row(k, row, key_w=36)}")
            print()
    if shown == 0:
        print("  no matching strategy slice.")
    print("-" * 64)
    print("  Slice ≠ KEEP. Mixed rollup is confounded. COSTLY ≠ TREND_UP enable.")
    print(f"  saved: {report.get('saved')}")
    print("=" * 64)
    print()
    return report


def _strategy_slices(tagged: List[dict]) -> Dict[str, dict]:
    groups: Dict[str, list] = defaultdict(list)
    for rec in tagged:
        groups[str(rec.get("strategy") or "?")].append(rec)
    out: Dict[str, dict] = {}
    for key, rows in groups.items():
        by_key = _xtab(rows, lambda r: r["fingerprint"]["key"])
        tally = _xtab(rows, lambda _r: "ALL").get("ALL") or {
            "n": 0, "TAKE": 0, "COSTLY": 0, "PROTECTIVE": 0, "WASH": 0,
        }
        out[key] = {
            "n": tally.get("n", len(rows)),
            "TAKE": tally.get("TAKE", 0),
            "COSTLY": tally.get("COSTLY", 0),
            "PROTECTIVE": tally.get("PROTECTIVE", 0),
            "WASH": tally.get("WASH", 0),
            "by_trend": _xtab(rows, lambda r: r["fingerprint"]["trend"]),
            "by_compression": _xtab(rows, lambda r: r["fingerprint"]["compression"]),
            "by_independent_label": _xtab(rows, lambda r: r["fingerprint"]["independent_label"]),
            "by_ret_1h_bin": _xtab(rows, lambda r: r["fingerprint"]["ret_1h_bin"]),
            "by_key": {k: v for k, v in by_key.items() if v["n"] >= MIN_SLICE_KEY_N},
            "keep": False,
        }
    return out


def from_record(rec: dict) -> dict:
    slot = rec.get("market") or {}
    return from_slot(slot, breadth=None)


def from_slot(slot: dict, breadth: Any = None) -> dict:
    if not slot or slot.get("data_gap"):
        return _gap()
    trend = str(slot.get("trend") or slot.get("trend_flag") or "UNKNOWN").upper() or "UNKNOWN"
    comp = str(slot.get("compression") or slot.get("compression_flag") or "UNKNOWN").upper() or "UNKNOWN"
    if trend in ("", "NONE", "NULL"):
        trend = "UNKNOWN"
    if comp in ("", "NONE", "NULL"):
        comp = "UNKNOWN"
    r1 = _num(slot.get("ret_1h_pct"))
    r4 = _num(slot.get("ret_4h_pct"))
    label = _independent_label({
        "ok": True,
        "trend": trend if trend != "UNKNOWN" else "",
        "ret_1h": r1,
        "breadth": breadth,
    })
    r1b = ret_bin(r1)
    key = f"{trend}|{comp}|{r1b}|{label}"
    return {
        "schema": "market_fingerprint_v0",
        "data_gap": False,
        "trend": trend,
        "compression": comp,
        "ret_1h_pct": r1,
        "ret_4h_pct": r4,
        "ret_1h_bin": r1b,
        "ret_4h_bin": ret_bin(r4),
        "independent_label": label,
        "key": key,
        "keep": False,
    }


def ret_bin(x: Optional[float]) -> str:
    if x is None:
        return "UNKNOWN"
    if x >= 0.4:
        return "UP_STRONG"
    if x >= 0.15:
        return "UP"
    if x <= -0.4:
        return "DOWN_STRONG"
    if x <= -0.15:
        return "DOWN"
    return "FLAT"


def _gap() -> dict:
    return {
        "schema": "market_fingerprint_v0",
        "data_gap": True,
        "trend": "UNKNOWN",
        "compression": "UNKNOWN",
        "ret_1h_pct": None,
        "ret_4h_pct": None,
        "ret_1h_bin": "UNKNOWN",
        "ret_4h_bin": "UNKNOWN",
        "independent_label": "UNCLEAR",
        "key": "UNKNOWN|UNKNOWN|UNKNOWN|UNCLEAR",
        "keep": False,
    }


def _role(rec: dict) -> str:
    if rec.get("population_role") == "TAKE":
        return "TAKE"
    stamp = ((rec.get("refusal") or {}).get("+1h") or {}).get("stamp")
    if stamp in ("COSTLY", "PROTECTIVE", "WASH"):
        return stamp
    return rec.get("population_role") or "?"


def _xtab(records: List[dict], key_fn) -> Dict[str, dict]:
    buckets: Dict[str, dict] = defaultdict(lambda: {
        "n": 0, "TAKE": 0, "COSTLY": 0, "PROTECTIVE": 0, "WASH": 0, "other": 0,
    })
    for rec in records:
        k = str(key_fn(rec) or "UNKNOWN")
        b = buckets[k]
        b["n"] += 1
        role = _role(rec)
        if role in ("TAKE", "COSTLY", "PROTECTIVE", "WASH"):
            b[role] += 1
        else:
            b["other"] += 1
    return dict(buckets)


def _print_xtab(title: str, table: dict) -> None:
    print(f"  {title}")
    if not table:
        print("    (empty)")
        return
    print(f"    {'flag':<16} {'n':>5}  {'TAKE':>5}  {'COSTLY':>6}  {'PROT':>5}  {'WASH':>5}")
    for k, row in sorted(table.items(), key=lambda kv: -kv[1]["n"]):
        print(f"    {_fmt_row(k, row)}")
    print()


def _fmt_row(k: str, row: dict, key_w: int = 16) -> str:
    return (
        f"{k:<{key_w}} {row.get('n', 0):>5}  {row.get('TAKE', 0):>5}  "
        f"{row.get('COSTLY', 0):>6}  {row.get('PROTECTIVE', 0):>5}  {row.get('WASH', 0):>5}"
    )


def _num(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
