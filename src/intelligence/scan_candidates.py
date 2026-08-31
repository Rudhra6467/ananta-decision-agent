"""Offline scanner candidates. Interesting ≠ BUY. Issued WAIT/UNKNOWN."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.t4_contracts import REFUSE, candidate as make_candidate
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "SCAN-CAND-v0"
GRID = Path("knowledge_grid.json")
FINDINGS = Path("findings.json")
OUT = Path("scan_candidates.json")


def _fp_from_obs(obs: dict) -> str:
    mt = obs.get("market_truth") or {}
    btc = mt.get("btc") or {}
    if not btc and isinstance(mt.get("assets"), dict):
        btc = mt["assets"].get("BTC/USD") or {}
    trend = str(btc.get("trend_flag") or "UNKNOWN")
    comp = str(btc.get("compression_flag") or "UNKNOWN")
    r1 = btc.get("ret_1h_pct")
    try:
        x = float(r1) if r1 is not None else None
    except (TypeError, ValueError):
        x = None
    if x is None:
        ret = "UNKNOWN"
    elif x > 0.4:
        ret = "UP_STRONG"
    elif x > 0.08:
        ret = "UP"
    elif x < -0.4:
        ret = "DOWN_STRONG"
    elif x < -0.08:
        ret = "DOWN"
    else:
        ret = "FLAT"
    if trend == "UP" and (x or 0) > 0:
        label = "BULLISH"
    elif trend == "DOWN" and (x or 0) < 0:
        label = "BEARISH"
    elif trend in ("UNKNOWN",) or comp == "UNKNOWN":
        label = "UNCLEAR"
    else:
        label = "NEUTRAL"
    return f"{trend}|{comp}|{ret}|{label}"


def _why(fp: str) -> str:
    parts = (fp or "").split("|")
    trend = parts[0] if parts else "UNKNOWN"
    comp = parts[1] if len(parts) > 1 else "UNKNOWN"
    if "UNKNOWN" in fp:
        return "unclear_state"
    if comp == "COMPRESSION":
        return "compression"
    if comp == "EXPANSION":
        return "expansion"
    if trend in ("UP", "DOWN"):
        return "directional_tape"
    return "structure"


def _cite(fp: str) -> List[dict]:
    if not GRID.exists():
        return []
    try:
        rows = json.loads(GRID.read_text()).get("rows") or []
    except Exception:
        return []
    trend = (fp or "").split("|")[0]
    regime = {"UP": "TREND_UP", "DOWN": "TREND_DOWN"}.get(trend, "")
    out = []
    for row in rows:
        if regime and row.get("regime") != regime and not (
            row.get("regime") == "COMPRESSION" and "COMPRESSION" in fp
        ):
            if row.get("regime") not in (regime, "COMPRESSION"):
                continue
        books = row.get("books") or {}
        hurt = [b for b, c in books.items() if c.get("vs_sitout") == "TAKE_HURT"]
        wash = [b for b, c in books.items() if c.get("vs_sitout") == "WASH"]
        out.append({
            "strategy": row.get("strategy"),
            "regime": row.get("regime"),
            "hurt_books": hurt,
            "wash_books": wash,
            "keep": False,
        })
    return out[:8]


def build(*, asset: str = "BTC/USD") -> Dict[str, Any]:
    rows = _read_jsonl(OBSERVATION_LOG) if OBSERVATION_LOG.exists() else []
    obs = rows[-1] if rows else None
    fp = _fp_from_obs(obs) if obs else "UNKNOWN|UNKNOWN|UNKNOWN|UNCLEAR"
    price = None
    if obs:
        mt = obs.get("market_truth") or {}
        slot = mt.get("btc") or (mt.get("assets") or {}).get(asset) or {}
        price = slot.get("price")
    cand = make_candidate(
        asset=asset,
        timeframe="15m",
        fingerprint=fp,
        why=_why(fp),
        price=price,
    )
    cites = _cite(fp)
    hurt_any = any(c.get("hurt_books") for c in cites)
    issued = "UNKNOWN" if "UNKNOWN" in fp else "WAIT"
    cand["issued"] = issued
    cand["evidence_refs"] = cites
    cand["version"] = VERSION
    cand["obs_id"] = (obs or {}).get("id")
    cand["why_not_take"] = (
        "I2_BASELINE_NO_SUITABLE; grid has TAKE_HURT cells; live TAKE quality = 0"
        if hurt_any else
        "I2_BASELINE_NO_SUITABLE; SUITABLE=0"
    )
    report = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "keep": False,
        "execute": False,
        "not_a_trade": True,
        "issued": issued,
        "live_n": len(rows),
        "candidate": cand,
        "refuse": dict(REFUSE),
    }
    OUT.write_text(json.dumps(report, indent=2, default=str))
    report["saved"] = str(OUT)
    return report


def print_scan() -> Dict[str, Any]:
    r = build()
    c = r.get("candidate") or {}
    print(f"\nSCAN CANDIDATE  {r['version']}")
    print("=" * 64)
    print("Interesting ≠ BUY. Issued WAIT/UNKNOWN. execute=False.")
    print(f"  asset={c.get('asset')}  fp={c.get('fingerprint')}")
    print(f"  why={c.get('why_interesting')}  price={c.get('observed_price')}")
    print(f"  issued={r.get('issued')}  live_n={r.get('live_n')}")
    print(f"  why_not_take={c.get('why_not_take')}")
    print("-" * 64)
    for ref in (c.get("evidence_refs") or [])[:6]:
        print(
            f"  {ref.get('strategy')} × {ref.get('regime')}  "
            f"hurt={ref.get('hurt_books')} wash={ref.get('wash_books')}"
        )
    print("-" * 64)
    print(f"  saved={r.get('saved')}  keep=False")
    print("=" * 64)
    print()
    return r
