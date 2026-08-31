"""Strategy × EP-2025-26 phase on HAVE book. Not KEEP. Not 2021."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict

from src.intelligence.attribution import _forward, population_role
from src.intelligence.books import ledger_path
from src.intelligence.episode_tag import EPISODE, phase_for
from src.tools.observation_log import _read_jsonl

VERSION = "EPISODE-SLICE-v0"
FOCUS = ("PRE_LEAD", "LEAD_IN", "PEAK_BAND", "DRAWDOWN")


def print_slice(source: str = "replay") -> Dict[str, Any]:
    rows = _read_jsonl(ledger_path(source))
    cells: Dict[str, dict] = {}
    acc = defaultdict(lambda: {"take_sum": 0.0, "take_n": 0, "skip_sum": 0.0, "skip_n": 0})
    for obs in rows:
        st = obs.get("system_truth") or {}
        ot = obs.get("outcome_truth") or {}
        ts = str(obs.get("ts") or st.get("ts") or "")
        phase = phase_for(ts)
        if phase not in FOCUS:
            continue
        fwd = _forward(ot).get("fwd_1h_pct")
        for o in st.get("strategy_observations") or []:
            if not o.get("setup_detected"):
                continue
            key = (o.get("strategy") or "").lower()
            cid = f"{key}|{phase}"
            b = cells.setdefault(cid, {"strategy": key, "phase": phase, "n": 0, "take": 0, "skip": 0})
            b["n"] += 1
            role = population_role(o)
            if role == "TAKE":
                b["take"] += 1
                if fwd is not None:
                    acc[cid]["take_sum"] += float(fwd)
                    acc[cid]["take_n"] += 1
            elif role == "SKIP_SETUP":
                b["skip"] += 1
                if fwd is not None:
                    acc[cid]["skip_sum"] += float(fwd)
                    acc[cid]["skip_n"] += 1
    print(f"\nEPISODE SLICE  {VERSION}  {EPISODE}")
    print("=" * 64)
    print("Setups only. Phase ≠ KEEP. Thin cells stay UNKNOWN.")
    print("-" * 64)
    for cid in sorted(cells):
        b = cells[cid]
        a = acc[cid]
        mt = None if not a["take_n"] else round(a["take_sum"] / a["take_n"], 4)
        ms = None if not a["skip_n"] else round(a["skip_sum"] / a["skip_n"], 4)
        b["+1h_take"] = mt
        b["+1h_skip"] = ms
        print(
            f"  {b['strategy']:<18} {b['phase']:<12} "
            f"n={b['n']:<4} TAKE={b['take']:<3} SKIP={b['skip']:<3} "
            f"+1h_T={mt if mt is not None else '—'}  +1h_S={ms if ms is not None else '—'}"
        )
    print("-" * 64)
    print("  DRAWDOWN-heavy book is expected. PEAK_BAND will be thin.")
    print("=" * 64)
    print()
    out = {"ok": True, "version": VERSION, "episode": EPISODE, "cells": cells, "keep": False}
    Path("episode_slice.json").write_text(json.dumps(out, indent=2, default=str))
    return out
