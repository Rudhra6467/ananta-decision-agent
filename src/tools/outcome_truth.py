"""
Stage 2 — Forward Outcome Truth.

Attach +15m / +1h / +4h returns to Observations using independent
exchange prices (Kraken). Does not use Ananta regime or PnL as proof.

method = spot_at_or_after_horizon (honest: wall-clock due, then spot).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.tools.observation_log import OBSERVATION_LOG, read_recent_observations

HORIZONS_MIN = (15, 60, 240)  # +15m, +1h, +4h
KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker"
PAIR_MAP = {
    "BTC/USD": "XXBTZUSD",
    "ETH/USD": "XETHZUSD",
}


def _parse_ts(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    s = str(ts).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _spot_prices(symbols: List[str]) -> Dict[str, float]:
    pairs = [PAIR_MAP[s] for s in symbols if s in PAIR_MAP]
    if not pairs:
        return {}
    try:
        r = requests.get(KRAKEN_TICKER, params={"pair": ",".join(pairs)}, timeout=12)
        if r.status_code != 200:
            return {}
        result = (r.json() or {}).get("result") or {}
    except Exception:
        return {}
    out: Dict[str, float] = {}
    for pair_id, canon in PAIR_MAP.items():
        row = result.get(pair_id)
        if row is None:
            for k, v in result.items():
                if canon.startswith("BTC") and "XBT" in k:
                    row = v
                    break
                if canon[:3] in k:
                    row = v
                    break
        if not row:
            continue
        try:
            out[canon] = float(row["c"][0])
        except Exception:
            continue
    return out


def _base_price(obs: dict, symbol: str) -> Optional[float]:
    mt = obs.get("market_truth") or {}
    if symbol == "BTC/USD":
        b = mt.get("btc") or {}
        if b.get("price") is not None:
            return float(b["price"])
    if symbol == "ETH/USD":
        e = mt.get("eth") or {}
        if e.get("price") is not None:
            return float(e["price"])
    assets = mt.get("assets") or {}
    a = assets.get(symbol) or {}
    if a.get("price") is not None:
        return float(a["price"])
    return None


def _horizon_key(minutes: int) -> str:
    return f"+{minutes}m" if minutes < 60 else f"+{minutes // 60}h"


def _ensure_outcome_shell(obs: dict) -> dict:
    ot = obs.get("outcome_truth")
    if not isinstance(ot, dict):
        ot = {
            "schema": "outcome_v0",
            "method": "spot_at_or_after_horizon",
            "horizons_min": list(HORIZONS_MIN),
            "assets": {},
            "status": "pending",
            "note": "Independent of Ananta regime. Not strategy KEEP evidence alone.",
        }
    assets = ot.setdefault("assets", {})
    for sym in ("BTC/USD", "ETH/USD"):
        slot = assets.setdefault(sym, {})
        base = _base_price(obs, sym)
        if slot.get("price_at_obs") is None and base is not None:
            slot["price_at_obs"] = base
        for m in HORIZONS_MIN:
            key = _horizon_key(m)
            slot.setdefault(key, None)
    ot["horizons_min"] = list(HORIZONS_MIN)
    ot["method"] = "spot_at_or_after_horizon"
    return ot


def fill_due_horizons(obs: dict, spots: Dict[str, float], now: Optional[datetime] = None) -> Tuple[dict, bool]:
    now = now or _utc_now()
    ts = _parse_ts(obs.get("ts") or (obs.get("system_truth") or {}).get("ts"))
    if not ts:
        return obs, False
    ot = _ensure_outcome_shell(obs)
    changed = False
    for sym in ("BTC/USD", "ETH/USD"):
        slot = ot["assets"].setdefault(sym, {})
        base = slot.get("price_at_obs") or _base_price(obs, sym)
        if base is None:
            continue
        slot["price_at_obs"] = base
        px = spots.get(sym)
        if px is None:
            continue
        for m in HORIZONS_MIN:
            key = _horizon_key(m)
            if slot.get(key):
                continue
            due = ts + timedelta(minutes=m)
            if now < due:
                continue
            ret = round((px / base - 1.0) * 100.0, 4) if base else None
            slot[key] = {
                "ts": now.isoformat(),
                "price": px,
                "ret_pct": ret,
                "due_at": due.isoformat(),
                "lag_sec": int((now - due).total_seconds()),
            }
            changed = True
    complete = True
    any_fill = False
    for sym in ("BTC/USD", "ETH/USD"):
        slot = ot["assets"].get(sym) or {}
        for m in HORIZONS_MIN:
            key = _horizon_key(m)
            if slot.get(key):
                any_fill = True
            else:
                complete = False
    ot["status"] = "complete" if complete else ("partial" if any_fill else "pending")
    ot["updated_at"] = now.isoformat()
    obs["outcome_truth"] = ot
    return obs, changed


def rewrite_observation_log(rows: List[dict]) -> bool:
    try:
        import json
        with OBSERVATION_LOG.open("w") as f:
            for r in rows:
                f.write(json.dumps(r, default=str) + "\n")
        return True
    except Exception:
        return False


def backfill_outcomes(limit: int = 200) -> Dict[str, Any]:
    import json

    if not OBSERVATION_LOG.exists():
        return {"ok": False, "error": "no observation_log.jsonl", "filled": 0, "scanned": 0}

    try:
        lines = OBSERVATION_LOG.read_text().strip().splitlines()
    except Exception as e:
        return {"ok": False, "error": str(e), "filled": 0, "scanned": 0}

    rows: List[dict] = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue

    start = max(0, len(rows) - limit)
    spots = _spot_prices(["BTC/USD", "ETH/USD"])
    now = _utc_now()
    filled = 0
    changed_any = False
    for i in range(start, len(rows)):
        rows[i], ch = fill_due_horizons(rows[i], spots, now=now)
        if ch:
            filled += 1
            changed_any = True

    if changed_any:
        rewrite_observation_log(rows)

    return {
        "ok": True,
        "scanned": len(rows) - start,
        "filled": filled,
        "spots": spots,
        "now": now.isoformat(),
        "rewrote": changed_any,
    }


def print_outcomes_summary(limit: int = 8) -> None:
    rows = read_recent_observations(limit=limit)
    print("\nOUTCOME TRUTH (Stage 2 — forward returns)")
    print("=" * 64)
    print("method=spot_at_or_after_horizon  independent of Ananta regime")
    print("-" * 64)
    if not rows:
        print("  (empty — run: lab once / lab watch)")
        print("=" * 64)
        return
    for r in rows:
        ot = r.get("outcome_truth") or {}
        st = r.get("system_truth") or {}
        btc = (ot.get("assets") or {}).get("BTC/USD") or {}

        def fmt(key):
            h = btc.get(key)
            if not h:
                return "—"
            return f"{h.get('ret_pct')}%"

        print(
            f"  {str(r.get('ts', ''))[:19]}  dec={st.get('agent_decision')}  "
            f"status={ot.get('status') or 'pending'}  "
            f"BTC +15m={fmt('+15m')} +1h={fmt('+1h')} +4h={fmt('+4h')}"
        )
    print("-" * 64)
    print("  Tip: lab outcomes  → backfill due horizons now")
    print("  Not KEEP evidence alone — process marks still human.")
    print("=" * 64)
    print()
