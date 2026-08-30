"""Excursion v0.3 — MFE/MAE proxy; BTC ETH SOL AVAX."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.setup_memory import extract

VERSION = "EXCURSION-v0.3"
BOOKS = ("replay", "eth", "sol", "avax")
LABEL = {"replay": "BTC", "eth": "ETH", "sol": "SOL", "avax": "AVAX"}
HIST_HORIZONS = ("+1h", "+4h")

CELLS = [
    ("donchian-breakout", "TREND_UP"),
    ("keltner-breakout", "TREND_UP"),
    ("atr-breakout", "TREND_UP"),
    ("bollinger-mr", "COMPRESSION"),
    ("bollinger-mr", "RANGE"),
    ("continuation", "TREND_UP"),
    ("hunter", "REVERSAL"),
    ("hunter", "TREND_UP"),
    ("squeeze", "COMPRESSION"),
]


def _exc(outcomes: dict) -> Dict[str, Optional[float]]:
    vals = []
    for h in HIST_HORIZONS:
        v = (outcomes or {}).get(h)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    if not vals:
        return {"mfe": None, "mae": None, "n_h": 0}
    return {"mfe": max(vals), "mae": min(vals), "n_h": len(vals)}


def _mean(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 4) if xs else None


def report() -> Dict[str, Any]:
    mems = {b: extract(b) for b in BOOKS}
    rows = []
    for strategy, regime in CELLS:
        entry = {"strategy": strategy, "regime": regime, "books": {}, "keep": False}
        for b in BOOKS:
            mem = mems[b]
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
                "data_gap": bool(mem.get("data_gap")),
            }
        rows.append(entry)
    out = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "method": "max/min of +1h/+4h close returns (hist +15m excluded)",
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
    print("BTC ETH SOL AVAX. Hist +15m excluded. Not KEEP.")
    print("-" * 72)
    for row in r["rows"]:
        label = f"{row['strategy']} × {row['regime']}"
        first = True
        for bk in ("BTC", "ETH", "SOL", "AVAX"):
            c = row["books"][bk]
            print(
                f"  {(label if first else ''):<32} {bk:<5} take={c['n_take']:<4} "
                f"MFE={c['mean_mfe']} MAE={c['mean_mae']}"
            )
            first = False
        print()
    print(f"  saved={r['saved']}  keep=False")
    print("=" * 72)
    print()
    return r
