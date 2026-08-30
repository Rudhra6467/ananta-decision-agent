"""Excursion v0 — MFE/MAE proxy from already-joined horizons.

Not bar-high/low MFE. Uses max/min of +15m/+1h/+4h close returns.
True path MFE needs Ananta OHLC highs. This is the offline table now.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.setup_memory import extract

VERSION = "EXCURSION-v0"
BOOKS = ("replay", "eth", "sol")
LABEL = {"replay": "BTC", "eth": "ETH", "sol": "SOL"}
HORIZONS = ("+15m", "+1h", "+4h")

CELLS = [
    ("donchian-breakout", "TREND_UP"),
    ("keltner-breakout", "TREND_UP"),
    ("bollinger-mr", "COMPRESSION"),
    ("hunter", "TREND_UP"),
    ("hunter", "REVERSAL"),
]


def _exc(outcomes: dict) -> Dict[str, Optional[float]]:
    vals = []
    for h in HORIZONS:
        v = (outcomes or {}).get(h)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    if not vals:
        return {"mfe": None, "mae": None, "n_h": 0}
    return {"mfe": max(vals), "mae": min(vals), "n_h": len(vals)}


def _mean(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 4) if xs else None


def report() -> Dict[str, Any]:
    rows = []
    for strategy, regime in CELLS:
        entry = {"strategy": strategy, "regime": regime, "books": {}, "keep": False}
        for b in BOOKS:
            mem = extract(b)
            mfes, maes = [], []
            n_take = 0
            for rec in mem.get("records") or []:
                if rec.get("strategy") != strategy:
                    continue
                if str(rec.get("regime") or "").upper() != regime:
                    continue
                if rec.get("population_role") != "TAKE":
                    continue
                n_take += 1
                e = _exc(rec.get("outcomes") or {})
                if e["mfe"] is not None:
                    mfes.append(e["mfe"])
                    maes.append(e["mae"])
            entry["books"][LABEL[b]] = {
                "n_take": n_take,
                "n_path": len(mfes),
                "mean_mfe": _mean(mfes),
                "mean_mae": _mean(maes),
            }
        rows.append(entry)
    out = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "method": "max/min of +15m/+1h/+4h close returns",
        "not": "true high/low path MFE",
        "keep": False,
        "rows": rows,
    }
    Path("excursion_report.json").write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = "excursion_report.json"
    return out


def print_excursion() -> Dict[str, Any]:
    r = report()
    print(f"\nEXCURSION  {r['version']}")
    print("=" * 72)
    print("MFE/MAE proxy from joined horizons. Not KEEP. Not bar-path.")
    print(f"  method={r['method']}")
    print("-" * 72)
    print(f"  {'cell':<32} {'bk':<4} {'take':>4} {'MFE':>8} {'MAE':>8}")
    print("-" * 72)
    for row in r["rows"]:
        label = f"{row['strategy']} × {row['regime']}"
        first = True
        for bk in ("BTC", "ETH", "SOL"):
            c = row["books"][bk]
            print(
                f"  {(label if first else ''):<32} {bk:<4} {c['n_take']:>4} "
                f"{str(c['mean_mfe'] if c['mean_mfe'] is not None else '—'):>8} "
                f"{str(c['mean_mae'] if c['mean_mae'] is not None else '—'):>8}"
            )
            first = False
        print()
    print("-" * 72)
    print(f"  saved={r['saved']}  keep=False")
    print("=" * 72)
    print()
    return r
