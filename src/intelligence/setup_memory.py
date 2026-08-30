"""Setup Memory v0 — jsonl join, not a database, not a ranker.

CLI: lab memory [live|replay|eth] [strategy] [regime]
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.intelligence.attribution import HORIZON_SHORT, _forward, population_role
from src.intelligence.books import artifact, ledger_path, tag as book_tag
from src.intelligence.decision_quality import NOISE_PCT, evidence_depth
from src.intelligence.evidence_engine import provenance
from src.intelligence.h2 import _codes, _regime
from src.intelligence.schema import WAVE_A
from src.tools.observation_log import _read_jsonl

VERSION = "SETUP-MEMORY-v0.2"
HORIZONS = ("fwd_15m_pct", "fwd_1h_pct", "fwd_4h_pct")


def extract(source: str = "replay") -> Dict[str, Any]:
    path = ledger_path(source)
    tag = book_tag(source)
    rows = _read_jsonl(path)
    records: List[dict] = []
    for obs in rows:
        st = obs.get("system_truth") or {}
        ot = obs.get("outcome_truth") or {}
        mt = obs.get("market_truth") or {}
        fwd = _forward(ot)
        ts = str(obs.get("ts") or st.get("ts") or "")
        obs_id = st.get("obs_id") or obs.get("obs_id")
        tf = "1h" if tag == "historical_lab" else str(st.get("timeframe") or "1h")
        for o in st.get("strategy_observations") or []:
            if not o.get("setup_detected"):
                continue
            rec = _record(o, st, mt, fwd, ts=ts, obs_id=obs_id, source=tag, tf=tf)
            records.append(rec)

    index = _index(records)
    report = {
        "ok": True,
        "schema": "setup_memory_v0",
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": tag,
        "book": str(path),
        "n_obs": len(rows),
        "n_setups": len(records),
        "data_gap": len(rows) == 0,
        "keep": False,
        "live_enable": False,
        "ranker": False,
        "similarity": False,
        "n_take": sum(1 for r in records if r["population_role"] == "TAKE"),
        "n_skip_setup": sum(1 for r in records if r["population_role"] == "SKIP_SETUP"),
        "refusal": _refusal_rollup(records),
        "by_cell": index,
        "records": records,
        "laws": {
            "jsonl_join_not_a_database": True,
            "books_are_separate": True,
            "memory_does_not_authorize_keep": True,
            "costly_skip_is_not_trend_up_enable": True,
        },
        "note": "Empirical memory. ETH book does not replace BTC replay.",
    }
    slim = dict(report)
    slim["records"] = f"{len(records)} records omitted from index file"
    dest = artifact("setup_memory_index", source)
    try:
        dest.write_text(json.dumps(slim, indent=2, default=str))
        report["saved"] = str(dest)
    except Exception:
        report["saved"] = None
    return report


def print_memory(source: str = "replay", strategy: Optional[str] = None, regime: Optional[str] = None) -> Dict[str, Any]:
    report = extract(source)
    strat = (strategy or "").lower().strip() or None
    reg = (regime or "").upper().strip() or None
    print(f"\nSETUP MEMORY  {report.get('version')}  ({report.get('source')})")
    print("=" * 64)
    print(f"book={report.get('book')}  keep=False")
    print(
        f"  obs={report.get('n_obs')}  setups={report.get('n_setups')}  "
        f"TAKE={report.get('n_take')}  SKIP_SETUP={report.get('n_skip_setup')}  "
        f"data_gap={report.get('data_gap')}"
    )
    ref = report.get("refusal") or {}
    print(
        f"  refusal +1h  COSTLY={ref.get('n_costly_1h')}  "
        f"PROTECTIVE={ref.get('n_protective_1h')}  WASH={ref.get('n_wash_1h')}  "
        f"NO_SAMPLE={ref.get('n_no_sample_1h')}"
    )
    print("-" * 64)
    cells = report.get("by_cell") or {}
    shown = 0
    for key in sorted(cells):
        c = cells[key]
        if strat and c["strategy"] != strat:
            continue
        if reg and c["regime"] != reg:
            continue
        shown += 1
        print(
            f"    {c['strategy']:<14} {str(c.get('asset') or '').split('/')[0]:<5} {c['regime']:<12} "
            f"n={c['n']:<4} TAKE={c['n_take']:<4} SKIP_SETUP={c['n_skip_setup']:<4} "
            f"+1h_TAKE={_fmt(c.get('mean_1h_take'))}  "
            f"+1h_SKIP={_fmt(c.get('mean_1h_skip_setup'))}  "
            f"skip→ costly={c.get('n_costly_1h', 0)} prot={c.get('n_protective_1h', 0)} wash={c.get('n_wash_1h', 0)}"
        )
    if shown == 0:
        print("  no matching setup cells (DATA_GAP or filter empty).")
    print("-" * 64)
    print("  COSTLY skip ≠ TREND_UP enable. Memory ≠ KEEP. ETH ≠ overwrite BTC.")
    print(f"  saved: {report.get('saved')}")
    print("=" * 64)
    print()
    return report


def _record(o: dict, st: dict, mt: dict, fwd: dict, *, ts: str, obs_id: Any, source: str, tf: str) -> dict:
    key = (o.get("strategy") or "").lower()
    asset = o.get("symbol") or "BTC/USD"
    regime = _regime(o, st)
    role = population_role(o)
    outcomes = {HORIZON_SHORT[h]: fwd.get(h) for h in HORIZONS}
    return {
        "schema": "setup_record_v0",
        "obs_id": obs_id,
        "ts": ts,
        "source": source,
        "strategy": key,
        "asset": asset,
        "timeframe": tf,
        "regime": regime,
        "population_role": role,
        "decision": o.get("decision"),
        "skip_reason": o.get("skip_reason"),
        "entry_profile": o.get("entry_profile"),
        "reason_codes": _codes(o),
        "wave_a": key in WAVE_A,
        "research_shadow": bool(o.get("research_shadow")),
        "live_watch": key in WAVE_A and source == "live_paper",
        "outcomes": outcomes,
        "refusal": _refusal(role, outcomes, source),
        "market": _fingerprint(mt, asset),
        "provenance": provenance(
            strategy=key, asset=asset, timeframe=tf, regime=regime,
            source=source, period={"min_ts": ts, "max_ts": ts, "n_rows": 1},
        ),
        "keep": False,
    }


def refusal_stamp(ret: Optional[float], *, usable: bool = True) -> str:
    if not usable:
        return "UNUSABLE_CLOCK"
    if ret is None:
        return "NO_SAMPLE"
    try:
        x = float(ret)
    except (TypeError, ValueError):
        return "NO_SAMPLE"
    if x >= NOISE_PCT:
        return "COSTLY"
    if x <= -NOISE_PCT:
        return "PROTECTIVE"
    return "WASH"


def _refusal(role: str, outcomes: dict, source: str) -> Optional[dict]:
    if role != "SKIP_SETUP":
        return None
    hist = source == "historical_lab"
    return {
        "+15m": {"ret_pct": outcomes.get("+15m"), "stamp": refusal_stamp(outcomes.get("+15m"), usable=not hist)},
        "+1h": {"ret_pct": outcomes.get("+1h"), "stamp": refusal_stamp(outcomes.get("+1h"))},
        "+4h": {"ret_pct": outcomes.get("+4h"), "stamp": refusal_stamp(outcomes.get("+4h"))},
        "note": "COSTLY = market rose after SKIP. Finding, not a gate to loosen.",
    }


def _refusal_rollup(records: List[dict]) -> dict:
    c = {"n_costly_1h": 0, "n_protective_1h": 0, "n_wash_1h": 0, "n_no_sample_1h": 0}
    for r in records:
        stamp = (((r.get("refusal") or {}).get("+1h") or {}).get("stamp"))
        if stamp == "COSTLY":
            c["n_costly_1h"] += 1
        elif stamp == "PROTECTIVE":
            c["n_protective_1h"] += 1
        elif stamp == "WASH":
            c["n_wash_1h"] += 1
        elif stamp == "NO_SAMPLE":
            c["n_no_sample_1h"] += 1
    return c


def _fingerprint(mt: dict, symbol: str) -> dict:
    assets = (mt or {}).get("assets") or {}
    slot: dict = {}
    if isinstance(assets, dict):
        slot = assets.get(symbol) or {}
    if not slot:
        if "ETH" in (symbol or ""):
            slot = (mt or {}).get("eth") or {}
        else:
            slot = (mt or {}).get("btc") or {}
    if not isinstance(slot, dict) or not slot:
        return {"data_gap": True}
    return {
        "data_gap": False,
        "price": slot.get("price"),
        "trend": slot.get("trend_flag") or slot.get("trend"),
        "compression": slot.get("compression_flag") or slot.get("compression"),
        "ret_1h_pct": slot.get("ret_1h_pct"),
        "ret_4h_pct": slot.get("ret_4h_pct"),
        "vol": slot.get("vol_proxy_1h_pct") or slot.get("vol"),
    }


def _index(records: List[dict]) -> Dict[str, dict]:
    buckets: Dict[str, dict] = {}
    sums: Dict[str, dict] = defaultdict(lambda: {"take": 0.0, "n_take": 0, "skip": 0.0, "n_skip": 0})
    for r in records:
        cid = f"{r['strategy']}|{r['asset']}|{r['timeframe']}|{r['regime']}"
        b = buckets.setdefault(
            cid,
            {
                "id": cid, "strategy": r["strategy"], "asset": r["asset"],
                "timeframe": r["timeframe"], "regime": r["regime"],
                "n": 0, "n_take": 0, "n_skip_setup": 0,
                "n_costly_1h": 0, "n_protective_1h": 0, "n_wash_1h": 0,
                "mean_1h_take": None, "mean_1h_skip_setup": None,
                "take_depth": "NONE", "keep": False,
            },
        )
        b["n"] += 1
        v = r.get("outcomes", {}).get("+1h")
        acc = sums[cid]
        if r["population_role"] == "TAKE":
            b["n_take"] += 1
            if v is not None:
                acc["take"] += float(v)
                acc["n_take"] += 1
        elif r["population_role"] == "SKIP_SETUP":
            b["n_skip_setup"] += 1
            if v is not None:
                acc["skip"] += float(v)
                acc["n_skip"] += 1
            stamp = ((r.get("refusal") or {}).get("+1h") or {}).get("stamp")
            if stamp == "COSTLY":
                b["n_costly_1h"] += 1
            elif stamp == "PROTECTIVE":
                b["n_protective_1h"] += 1
            elif stamp == "WASH":
                b["n_wash_1h"] += 1
    for cid, b in buckets.items():
        acc = sums[cid]
        if acc["n_take"]:
            b["mean_1h_take"] = round(acc["take"] / acc["n_take"], 4)
        if acc["n_skip"]:
            b["mean_1h_skip_setup"] = round(acc["skip"] / acc["n_skip"], 4)
        b["take_depth"] = evidence_depth(b["n_take"], role="TAKE")
    return buckets


def _fmt(v) -> str:
    if v is None:
        return "—"
    return f"{v}%"
