"""One DI pass on the latest live observation. Memory may not TAKE."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.intelligence.findings import findings as load_findings
from src.intelligence.rank_desk import rank_for
from src.intelligence.scan_candidates import _fp_from_obs, build as build_scan
from src.intelligence.state_card import card as state_card
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "DI-LOOP-v0"
OUT = Path("di_loop.json")


def run() -> Dict[str, Any]:
    rows = _read_jsonl(OBSERVATION_LOG) if OBSERVATION_LOG.exists() else []
    obs = rows[-1] if rows else {}
    st = state_card(obs)
    fp = st.get("fingerprint") or _fp_from_obs(obs)
    scan = build_scan()
    rank = rank_for(fp)
    find = load_findings()
    issued = rank.get("issued") or scan.get("issued") or "UNKNOWN"
    if issued not in ("WAIT", "UNKNOWN"):
        issued = "WAIT"
    hurt = find.get("unsuitable_or_hurt") or []
    out = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "obs_id": obs.get("id"),
        "live_n": len(rows),
        "fingerprint": fp,
        "price": st.get("price"),
        "sma20": st.get("sma20"),
        "vwap": st.get("vwap"),
        "issued": issued,
        "can_take": False,
        "keep": False,
        "why": rank.get("why") or "I2_BASELINE_NO_SUITABLE",
        "scan_why": (scan.get("candidate") or {}).get("why_interesting"),
        "rank_rows": rank.get("rows") or [],
        "hurt_n": len(hurt),
        "missing_state": st.get("fields_missing_for_richer_state") or [],
    }
    OUT.write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = str(OUT)
    return out


def print_loop() -> Dict[str, Any]:
    r = run()
    print(f"\nDI LOOP  {r['version']}")
    print("=" * 64)
    print("State → scan → rank → findings. Issued WAIT/UNKNOWN. Not KEEP.")
    print(f"  fp={r.get('fingerprint')}  price={r.get('price')} sma20={r.get('sma20')}")
    print(f"  issued={r.get('issued')}  why={r.get('why')}  live_n={r.get('live_n')}")
    print(f"  scan={r.get('scan_why')}  hurt_cells={r.get('hurt_n')}")
    print("-" * 64)
    for x in (r.get("rank_rows") or [])[:6]:
        print(
            f"  {x.get('strategy'):<20} {x.get('regime'):<12} "
            f"worst={x.get('worst')} hurt={x.get('hurt_books')}"
        )
    print("-" * 64)
    print("  I4 cannot TAKE. I5 blocked. Wave A stays WATCH.")
    print(f"  saved={r.get('saved')}  keep=False")
    print("=" * 64)
    print()
    return r
