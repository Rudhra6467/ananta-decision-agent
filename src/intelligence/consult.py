"""Knowledge consult v0.1 — key match first, then trend. Memory may not TAKE.

Exact fingerprint key (trend|compression|ret1h|label) before inheriting
the whole UP/DOWN bucket. Sparse keys → UNKNOWN, not parent WASH.

CLI: lab consult [live|replay]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.fingerprint import from_market_truth, from_record
from src.intelligence.lookup import lookup
from src.intelligence.setup_memory import extract
from src.tools.observation_log import OBSERVATION_LOG, REPLAY_LOG, _read_jsonl

VERSION = "CONSULT-v0.1"
OUT = Path("knowledge_consult.json")
CONSULT_LOG = Path("consult_log.jsonl")
MIN_KEY_N = 5


def consult(
    observation: Optional[dict] = None,
    *,
    source: str = "live",
    hist_mem: Optional[dict] = None,
    parent_cache: Optional[dict] = None,
    write_snapshot: bool = True,
) -> Dict[str, Any]:
    obs = observation if observation is not None else _latest(source)
    mt = (obs or {}).get("market_truth") or {}
    st = (obs or {}).get("system_truth") or {}
    asset = str(st.get("symbol") or "BTC/USD")
    fp = from_market_truth(mt, asset)
    flag = str(fp.get("trend") or "UNKNOWN")
    key = str(fp.get("key") or "")
    match = "NONE"
    n_key = 0
    rows: List[dict] = []
    parent_rows: List[dict] = []
    k_action = "UNKNOWN"
    why = "NO_TAPE_FLAG"

    if flag not in ("UNKNOWN", "", "NONE"):
        mem = hist_mem if hist_mem is not None else extract("replay")
        matched = [
            r for r in (mem.get("records") or [])
            if from_record(r).get("key") == key
        ]
        n_key = len(matched)
        cache = parent_cache if parent_cache is not None else {}
        if flag not in cache:
            cache[flag] = lookup(flag, "replay")
        parent = cache[flag]
        parent_rows = _slim(parent.get("rows") or [])
        if n_key >= MIN_KEY_N:
            match = "KEY"
            rows = _slim(_score_records(matched, flag=key))
            k_action = "WAIT"
            why = "I2_BASELINE_NO_SUITABLE"
        elif n_key > 0:
            match = "SPARSE_KEY"
            rows = _slim(_score_records(matched, flag=key))
            k_action = "UNKNOWN"
            why = "SPARSE_FINGERPRINT_KEY"
        else:
            match = "TREND"
            rows = parent_rows
            k_action = "WAIT" if parent_rows else "UNKNOWN"
            why = "I2_BASELINE_NO_SUITABLE" if parent_rows else "NO_HIST_FOR_FLAG"

    report = {
        "ok": True,
        "version": VERSION,
        "source_obs": "live_paper" if source == "live" else "historical_lab",
        "obs_id": (obs or {}).get("obs_id") or ((obs or {}).get("system_truth") or {}).get("obs_id"),
        "fingerprint": {
            "trend": fp.get("trend"),
            "compression": fp.get("compression"),
            "independent_label": fp.get("independent_label"),
            "ret_1h_bin": fp.get("ret_1h_bin"),
            "key": fp.get("key"),
            "data_gap": fp.get("data_gap"),
        },
        "flag": flag,
        "match": match,
        "n_key": n_key,
        "min_key_n": MIN_KEY_N,
        "rows": rows,
        "parent_trend_rows": parent_rows if match == "SPARSE_KEY" else [],
        "knowledge_action": k_action,
        "why": why,
        "issued_override": False,
        "keep": False,
        "live_enable": False,
        "trend_up_enable": False,
        "authority_earned": False,
        "laws": {
            "consult_is_not_keep": True,
            "consult_cannot_take": True,
            "consult_cannot_override_issued": True,
            "wave_a_watch": True,
            "i2_hist_baseline_locked": True,
            "unknown_is_valid": True,
            "sparse_key_does_not_inherit_parent": True,
        },
        "note": (
            "Exact fingerprint key first. Sparse key → UNKNOWN, not parent WASH. "
            "Memory does not fill."
        ),
    }
    if write_snapshot:
        try:
            OUT.write_text(json.dumps(report, indent=2, default=str))
            report["saved"] = str(OUT)
        except Exception:
            report["saved"] = None
    _append_log(report)
    return report


def backfill(source: str = "live") -> Dict[str, Any]:
    """Score every live obs once. Does not KEEP. Does not enable."""
    path = OBSERVATION_LOG if source == "live" else REPLAY_LOG
    rows = _read_jsonl(path)
    seen = _logged_ids()
    hist = extract("replay")
    parents: dict = {}
    n_new = 0
    for obs in rows:
        oid = (obs or {}).get("obs_id") or ((obs or {}).get("system_truth") or {}).get("obs_id")
        if not oid or str(oid) in seen:
            continue
        consult(obs, source=source, hist_mem=hist, parent_cache=parents, write_snapshot=False)
        seen.add(str(oid))
        n_new += 1
    return {
        "ok": True,
        "n_obs": len(rows),
        "n_new": n_new,
        "n_logged": len(seen),
        "keep": False,
        "live_enable": False,
    }


def print_backfill(source: str = "live") -> Dict[str, Any]:
    report = backfill(source)
    print(f"\nCONSULT BACKFILL  {VERSION}")
    print("=" * 64)
    print("Offline consult on existing live tape. Not KEEP. Not a fill.")
    print(
        f"  obs={report.get('n_obs')}  new={report.get('n_new')}  "
        f"logged={report.get('n_logged')}  keep=False"
    )
    print("-" * 64)
    print("  Next: lab consult-dq")
    print("=" * 64)
    return report


def _logged_ids() -> set:
    ids = set()
    if not CONSULT_LOG.exists():
        return ids
    try:
        for line in CONSULT_LOG.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            oid = row.get("obs_id")
            if oid:
                ids.add(str(oid))
    except Exception:
        return ids
    return ids


def _append_log(report: dict) -> None:
    """Append a slim consult so later DQ can score the consults themselves."""
    slim = {
        "ts": report.get("obs_id"),
        "obs_id": report.get("obs_id"),
        "flag": report.get("flag"),
        "match": report.get("match"),
        "n_key": report.get("n_key"),
        "fp": (report.get("fingerprint") or {}).get("key"),
        "knowledge_action": report.get("knowledge_action"),
        "why": report.get("why"),
        "keep": False,
        "issued_override": False,
        "version": report.get("version"),
    }
    try:
        with CONSULT_LOG.open("a") as f:
            f.write(json.dumps(slim, default=str) + "\n")
    except Exception:
        return


def print_consult(source: str = "live") -> Dict[str, Any]:
    report = consult(source=source)
    print(f"\nKNOWLEDGE CONSULT  {report.get('version')}")
    print("=" * 64)
    print("Key match first. Sparse key ≠ parent DOWN WASH. Memory may not TAKE.")
    print(
        f"  tape={report.get('flag')}  match={report.get('match')}  "
        f"n_key={report.get('n_key')}  knowledge_action={report.get('knowledge_action')}  "
        f"override=False"
    )
    print(f"  why={report.get('why')}  obs={report.get('obs_id') or '—'}")
    fp = report.get("fingerprint") or {}
    print(f"  fp={fp.get('key')}  gap={fp.get('data_gap')}")
    print("-" * 64)
    rows = report.get("rows") or []
    if not rows:
        print("  (no hist rows — UNKNOWN is valid)")
    for r in rows:
        print(
            f"  {r.get('strategy'):<18} n={r.get('n')} TAKE={r.get('TAKE')}  "
            f"depth={r.get('depth')}  vs_sitout={r.get('vs_sitout')}  "
            f"+1h_TAKE={r.get('mean_1h_take')}  +1h_SKIP={r.get('mean_1h_skip')}"
        )
    parent = report.get("parent_trend_rows") or []
    if parent:
        print("  parent TREND (context only — not inherited)")
        for r in parent:
            print(
                f"    {r.get('strategy'):<16} TAKE={r.get('TAKE')}  "
                f"vs_sitout={r.get('vs_sitout')}"
            )
    print("-" * 64)
    print("  Consult ≠ KEEP. Consult ≠ TREND_UP. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report


def _slim(rows: List[dict]) -> List[dict]:
    out = []
    for r in rows:
        out.append({
            "strategy": r.get("strategy"),
            "n": r.get("n"),
            "TAKE": r.get("TAKE"),
            "depth": r.get("depth"),
            "vs_sitout": r.get("vs_sitout"),
            "mean_1h_take": r.get("mean_1h_take"),
            "mean_1h_skip": r.get("mean_1h_skip"),
            "keep": False,
        })
    return out


def _score_records(records: List[dict], *, flag: str) -> List[dict]:
    """Local score so key slices do not borrow the parent trend mean."""
    from collections import defaultdict
    from src.intelligence.decision_quality import NOISE_PCT, evidence_depth, path_call

    buckets: Dict[str, dict] = defaultdict(lambda: {
        "n": 0, "TAKE": 0, "take_rets": [], "skip_rets": [],
    })
    for rec in records:
        key = str(rec.get("strategy") or "?")
        b = buckets[key]
        b["n"] += 1
        ret = (rec.get("outcomes") or {}).get("+1h")
        if rec.get("population_role") == "TAKE":
            b["TAKE"] += 1
            if isinstance(ret, (int, float)):
                b["take_rets"].append(float(ret))
        elif isinstance(ret, (int, float)):
            b["skip_rets"].append(float(ret))
    rows = []
    for strat, b in buckets.items():
        n_take = int(b["TAKE"])
        take_mean = round(sum(b["take_rets"]) / len(b["take_rets"]), 4) if b["take_rets"] else None
        skip_mean = round(sum(b["skip_rets"]) / len(b["skip_rets"]), 4) if b["skip_rets"] else None
        take_call = path_call(take_mean, len(b["take_rets"]), usable=True, role="TAKE")
        vs = "NO_TAKE" if n_take <= 0 else take_call
        if n_take > 0 and take_call not in ("INSUFFICIENT_EVIDENCE", "NO_SAMPLE") and take_mean is not None and skip_mean is not None:
            delta = take_mean - skip_mean
            if abs(delta) < NOISE_PCT:
                vs = "WASH"
            elif delta >= NOISE_PCT:
                vs = "TAKE_GT_SITOUT"
            else:
                vs = "TAKE_LT_SITOUT"
        rows.append({
            "strategy": strat,
            "flag": flag,
            "n": b["n"],
            "TAKE": n_take,
            "depth": evidence_depth(n_take, role="TAKE"),
            "mean_1h_take": take_mean,
            "mean_1h_skip": skip_mean,
            "vs_sitout": vs,
            "keep": False,
        })
    rows.sort(key=lambda r: (-int(r["TAKE"]), -int(r["n"]), r["strategy"]))
    return rows


def _latest(source: str) -> Optional[dict]:
    path = OBSERVATION_LOG if source == "live" else REPLAY_LOG
    rows = _read_jsonl(path)
    return rows[-1] if rows else None
