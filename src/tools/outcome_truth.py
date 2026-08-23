"""
Stage 2 — Forward Outcome Truth.

Attach +15m / +1h / +4h returns to Observations using independent
Kraken OHLC (not Ananta regime). Current spot is only a fallback.

method = ohlc_close_at_or_after_horizon
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.tools.observation_log import OBSERVATION_LOG, read_recent_observations

HORIZONS_MIN = (15, 60, 240)  # +15m, +1h, +4h
KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"
PAIR_FOR = {"BTC/USD": "XBTUSD", "ETH/USD": "ETHUSD"}
INTERVAL_FOR = {15: 15, 60: 60, 240: 60}  # 4h uses 1h bars


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


def _horizon_key(minutes: int) -> str:
    return f"+{minutes}m" if minutes < 60 else f"+{minutes // 60}h"


def _kraken_ohlc(pair: str, interval: int) -> List[Tuple[int, float]]:
    try:
        r = requests.get(
            KRAKEN_OHLC,
            params={"pair": pair, "interval": interval},
            timeout=20,
        )
        if r.status_code != 200:
            return []
        body = r.json() or {}
        if body.get("error"):
            # Kraken uses [] for no error
            err = body.get("error")
            if err:
                return []
        result = body.get("result") or {}
        rows = None
        for k, v in result.items():
            if k == "last":
                continue
            if isinstance(v, list) and v:
                rows = v
                break
        if not rows:
            return []
        out = []
        for x in rows:
            try:
                out.append((int(x[0]), float(x[4])))
            except Exception:
                continue
        return out
    except Exception:
        return []


def _close_at_or_after(candles: List[Tuple[int, float]], due: datetime) -> Optional[Tuple[float, int]]:
    if not candles:
        return None
    due_unix = int(due.timestamp())
    for t, close in candles:
        if t >= due_unix:
            return close, t
    return None


def _spot_from_market_truth() -> Dict[str, float]:
    """Fallback: same path as Stage 1 (known working on this laptop)."""
    try:
        from src.tools.market_truth import capture_market_truth
        mt = capture_market_truth()
    except Exception:
        return {}
    out: Dict[str, float] = {}
    b = mt.get("btc") or {}
    e = mt.get("eth") or {}
    if b.get("price") is not None:
        out["BTC/USD"] = float(b["price"])
    if e.get("price") is not None:
        out["ETH/USD"] = float(e["price"])
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


def _ensure_outcome_shell(obs: dict) -> dict:
    ot = obs.get("outcome_truth")
    if not isinstance(ot, dict):
        ot = {
            "schema": "outcome_v0",
            "method": "ohlc_close_at_or_after_horizon",
            "horizons_min": list(HORIZONS_MIN),
            "assets": {},
            "status": "pending",
            "note": "Independent of Ananta regime. Not KEEP evidence alone.",
        }
    assets = ot.setdefault("assets", {})
    for sym in ("BTC/USD", "ETH/USD"):
        slot = assets.setdefault(sym, {})
        base = _base_price(obs, sym)
        if slot.get("price_at_obs") is None and base is not None:
            slot["price_at_obs"] = base
        for m in HORIZONS_MIN:
            slot.setdefault(_horizon_key(m), None)
    ot["horizons_min"] = list(HORIZONS_MIN)
    ot["method"] = "ohlc_close_at_or_after_horizon"
    return ot


def fill_due_horizons(
    obs: dict,
    *,
    candles: Dict[Tuple[str, int], List[Tuple[int, float]]],
    spots: Dict[str, float],
    now: Optional[datetime] = None,
) -> Tuple[dict, bool, str]:
    now = now or _utc_now()
    ts = _parse_ts(obs.get("ts") or (obs.get("system_truth") or {}).get("ts"))
    if not ts:
        return obs, False, "no_ts"
    ot = _ensure_outcome_shell(obs)
    changed = False
    reason = "ok"
    for sym in ("BTC/USD", "ETH/USD"):
        slot = ot["assets"].setdefault(sym, {})
        base = slot.get("price_at_obs") or _base_price(obs, sym)
        if base is None:
            reason = "no_base"
            continue
        slot["price_at_obs"] = base
        for m in HORIZONS_MIN:
            key = _horizon_key(m)
            existing = slot.get(key)
            if isinstance(existing, dict) and existing.get("price") is not None:
                continue
            due = ts + timedelta(minutes=m)
            if now < due:
                continue
            interval = INTERVAL_FOR[m]
            pair = PAIR_FOR[sym]
            series = candles.get((pair, interval)) or []
            hit = _close_at_or_after(series, due)
            if hit:
                px, bar_t = hit
                method = "ohlc"
            else:
                px = spots.get(sym)
                bar_t = None
                method = "spot_fallback"
                if px is None:
                    reason = "no_price"
                    continue
            ret = round((float(px) / float(base) - 1.0) * 100.0, 4) if base else None
            slot[key] = {
                "ts": now.isoformat(),
                "price": float(px),
                "ret_pct": ret,
                "due_at": due.isoformat(),
                "lag_sec": int((now - due).total_seconds()),
                "method": method,
                "bar_time": bar_t,
            }
            changed = True
    complete = True
    any_fill = False
    for sym in ("BTC/USD", "ETH/USD"):
        slot = ot["assets"].get(sym) or {}
        for m in HORIZONS_MIN:
            key = _horizon_key(m)
            cell = slot.get(key)
            if isinstance(cell, dict) and cell.get("price") is not None:
                any_fill = True
            else:
                complete = False
    ot["status"] = "complete" if complete else ("partial" if any_fill else "pending")
    ot["updated_at"] = now.isoformat()
    obs["outcome_truth"] = ot
    return obs, changed, reason if changed else reason


def rewrite_observation_log(rows: List[dict]) -> bool:
    try:
        import json
        with OBSERVATION_LOG.open("w") as f:
            for r in rows:
                f.write(json.dumps(r, default=str) + "\n")
        return True
    except Exception:
        return False


def backfill_outcomes(limit: int = 400) -> Dict[str, Any]:
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
    now = _utc_now()
    candles: Dict[Tuple[str, int], List[Tuple[int, float]]] = {}
    ohlc_ok = {}
    for pair in ("XBTUSD", "ETHUSD"):
        for interval in (15, 60):
            series = _kraken_ohlc(pair, interval)
            candles[(pair, interval)] = series
            ohlc_ok[f"{pair}:{interval}"] = len(series)
    spots = _spot_from_market_truth()

    filled = 0
    skip_reasons: Dict[str, int] = {}
    changed_any = False
    for i in range(start, len(rows)):
        rows[i], ch, why = fill_due_horizons(
            rows[i], candles=candles, spots=spots, now=now
        )
        skip_reasons[why] = skip_reasons.get(why, 0) + 1
        if ch:
            filled += 1
            changed_any = True

    if changed_any:
        rewrite_observation_log(rows)

    n_partial = n_complete = n_pending = 0
    for r in rows[start:]:
        st = ((r.get("outcome_truth") or {}) or {}).get("status") or "pending"
        if st == "complete":
            n_complete += 1
        elif st == "partial":
            n_partial += 1
        else:
            n_pending += 1

    return {
        "ok": True,
        "scanned": len(rows) - start,
        "filled": filled,
        "spots": spots,
        "ohlc_bars": ohlc_ok,
        "reasons": skip_reasons,
        "status_counts": {
            "complete": n_complete,
            "partial": n_partial,
            "pending": n_pending,
        },
        "now": now.isoformat(),
        "rewrote": changed_any,
    }


def print_outcomes_summary(limit: int = 12) -> None:
    import json

    rows: List[dict] = []
    if OBSERVATION_LOG.exists():
        for line in OBSERVATION_LOG.read_text().strip().splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    print("\nOUTCOME TRUTH (Stage 2 — forward returns)")
    print("=" * 64)
    print("method=ohlc_close_at_or_after_horizon  independent of Ananta regime")
    print("-" * 64)
    if not rows:
        print("  (empty — run: lab once / lab watch)")
        print("=" * 64)
        return

    def fmt_cell(slot, key):
        h = (slot or {}).get(key)
        if not isinstance(h, dict):
            return "—"
        r = h.get("ret_pct")
        return f"{r}%" if r is not None else "—"

    # oldest filled-or-due + newest, so a pending tail cannot hide S2
    show = rows[: min(4, len(rows))] + rows[-min(limit, len(rows)) :]
    seen = set()
    ordered = []
    for r in show:
        k = r.get("obs_id") or r.get("ts")
        if k in seen:
            continue
        seen.add(k)
        ordered.append(r)
    for r in ordered:
        ot = r.get("outcome_truth") or {}
        st = r.get("system_truth") or {}
        btc = (ot.get("assets") or {}).get("BTC/USD") or {}
        print(
            f"  {str(r.get('ts', ''))[:19]}  dec={st.get('agent_decision')}  "
            f"status={ot.get('status') or 'pending'}  "
            f"BTC +15m={fmt_cell(btc, '+15m')} +1h={fmt_cell(btc, '+1h')} +4h={fmt_cell(btc, '+4h')}"
        )
    print("-" * 64)
    print("  Tip: lab outcomes  → backfill due horizons now")
    print("  Not KEEP evidence alone — process marks still human.")
    print("=" * 64)
    print()
