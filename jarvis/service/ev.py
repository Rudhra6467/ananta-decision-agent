"""The expected-value table (engine fix 3, review #26): what history measured for each daily rule, by market state (the exposure
dial) and liquidity tier, after costs, over random entries of the same tier and state, walk-forward, shrunk toward zero.
A cell that did not pass in BOTH periods is 0: no measured edge.

  value(rule, state, tier)   expected % per trade over random (0 when unmeasured)
  for_trigger(j, coin, trigger)   the value of a brain wake's trigger right now (dial state, the coin's tier)
  table()                     the passing cells, for the app and Ask
"""
from __future__ import annotations

import json
from pathlib import Path

_CACHE: dict = {"m": None, "cells": {}}


def _cells() -> dict:
    p = Path(__file__).resolve().parents[2] / "docs" / "research" / "review26.json"
    if not p.exists():
        return {}
    m = p.stat().st_mtime
    if _CACHE["m"] != m:
        rows = json.loads(p.read_text()).get("cells", [])
        _CACHE.update(m=m, cells={(r["rule"], r["state"], r["tier"]): r for r in rows})
    return _CACHE["cells"]


def value(rule: str, state: str, tier: str) -> float:
    r = _cells().get((rule, state, tier))
    return float(r["expected_excess_pct"]) if r and r.get("passes") else 0.0


def table() -> list[dict]:
    return [{"rule": r["rule"], "state": r["state"], "tier": r["tier"], "expected_excess_pct": r["expected_excess_pct"],
             "discovery": r["DISCOVERY"], "confirm": r["CONFIRM"]} for r in _cells().values() if r.get("passes")]


def for_trigger(j, coin: str, trigger: str) -> dict:
    """The best measured value among a wake's triggers, for this coin's tier and today's dial."""
    from jarvis.service import exposure, registry, universe_watch
    from src.research import reads as R

    dial = (exposure.state(j) or {}).get("dial")
    state = "OPEN" if dial else "CLOSED"
    tier = "A" if coin in R.COINS else (registry.tier_of(j, coin) or "C")
    best, rule = 0.0, None
    for t in (trigger or "").split("|"):
        if not t.startswith("setup:"):
            continue
        sp = universe_watch.split(t[6:])
        base = (sp[0] if sp else t[6:]).split(".")[0]
        v = value(base, state, tier)
        if v > best:
            best, rule = v, base
    return {"expected_excess_pct": best, "rule": rule, "state": state, "tier": tier}


def fidelity(j, min_n: int = 10) -> dict:
    """Engine fix 5: does paper trading match the backtest? For each rule x tier x dial state, the forward paper average (% per
    trade after costs, from the evidence ledger's $100 stakes) beside review #26's backtest average over both periods. A cell with
    enough forward trades that runs more than 3 points a trade under its backtest is flagged: the backtest flattered it (costs,
    fills, timing) and the gap is a repair-shop item before anything trusts its number."""
    import statistics
    import time

    from jarvis.service import exposure, universe_watch

    try:
        dial = exposure.dial_by_day(j)
    except Exception:  # noqa: BLE001
        dial = {}
    fwd: dict = {}
    for w, net, et in j.db.execute("SELECT watch, net_usd, entry_t FROM evidence_trades WHERE watch LIKE '%-U_' AND watch NOT LIKE 'RANDOM%' "
                                   "AND status='CLOSED' AND entry_t IS NOT NULL").fetchall():
        sp = universe_watch.split(w)
        if not sp or sp[1] == "C":
            continue
        d = dial.get(time.strftime("%Y-%m-%d", time.gmtime(et)))
        state = "?" if d is None else "OPEN" if d > 0 else "CLOSED"
        fwd.setdefault((sp[0].split(".")[0], state, sp[1]), []).append(net or 0.0)
    rows = []
    for (rule, state, tier), xs in sorted(fwd.items()):
        c = _cells().get((rule, state, tier))
        bt = None
        if c:
            n1, n2 = c["DISCOVERY"]["trades"], c["CONFIRM"]["trades"]
            if n1 + n2:
                bt = round((c["DISCOVERY"]["mean_net_pct"] * n1 + c["CONFIRM"]["mean_net_pct"] * n2) / (n1 + n2), 2)
        m = round(statistics.fmean(xs), 2)
        flag = ("too few trades" if len(xs) < min_n else "no backtest cell" if bt is None else
                "BELOW BACKTEST: check costs, fills and timing" if m < bt - 3 else "in line with the backtest")
        rows.append({"rule": rule, "state": state, "tier": tier, "paper_trades": len(xs), "paper_avg_pct": m, "backtest_avg_pct": bt, "verdict": flag})
    return {"cells": rows, "min_trades": min_n,
            "rule": "Paper must track the backtest within 3 points a trade over at least 10 trades; a cell below it goes to the repair shop."}
