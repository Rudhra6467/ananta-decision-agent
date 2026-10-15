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
# A cell re-tested by a later pre-registered review takes that review's verdict and value (REVIEW_29.md, approved Oct 15: on PASS
# the closed-dial value becomes the new pooled excess shrunk by n/(n+50); on FAIL it goes to 0; INSUFFICIENT changes nothing).
LATER = {("H07", "CLOSED", "A"): ("review29.json", "review #29")}


def _later(path: Path, key: tuple, src: str) -> dict | None:
    try:
        d = json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return None
    if d.get("stopped"):
        return None
    for c in d.get("cells") or []:
        if (c.get("rule"), c.get("state"), c.get("tier")) == key and c.get("verdict") in ("PASS", "WEAKENED", "FAIL"):
            return {**c, "passes": c["verdict"] in ("PASS", "WEAKENED"), "source": src}
    return None


def _cells() -> dict:
    d = Path(__file__).resolve().parents[2] / "docs" / "research"
    p = d / "review26.json"
    if not p.exists():
        return {}
    m = (p.stat().st_mtime,) + tuple((d / f).stat().st_mtime if (d / f).exists() else 0 for f, _ in LATER.values())
    if _CACHE["m"] != m:
        rows = json.loads(p.read_text()).get("cells", [])
        cells = {(r["rule"], r["state"], r["tier"]): {**r, "source": "review #26"} for r in rows}
        for key, (f, src) in LATER.items():
            c = _later(d / f, key, src)
            if c:
                cells[key] = c
        _CACHE.update(m=m, cells=cells)
    return _CACHE["cells"]


def value(rule: str, state: str, tier: str) -> float:
    r = _cells().get((rule, state, tier))
    return float(r["expected_excess_pct"]) if r and r.get("passes") else 0.0


def table() -> list[dict]:
    return [{"rule": r["rule"], "state": r["state"], "tier": r["tier"], "expected_excess_pct": r["expected_excess_pct"],
             "discovery": r["DISCOVERY"], "confirm": r["CONFIRM"], "source": r.get("source")} for r in _cells().values() if r.get("passes")]


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


def fidelity_alert(j, push=None) -> list[str]:
    """Oct 15 (audit FIX1-5): the fidelity check was only displayed. A cell that turns BELOW BACKTEST now goes to the repair shop
    by itself, once per cell: a phone note and a request (by 'ananta-auto'); Rule A's 'execution within 3 points' depends on it."""
    from jarvis.service import requests_log

    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    out = []
    for c in fidelity(j)["cells"]:
        if not c["verdict"].startswith("BELOW BACKTEST"):
            continue
        key = f"ev:fidelity_flag:{c['rule']}|{c['state']}|{c['tier']}"
        if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
            continue
        text = (f"Paper vs backtest: {c['rule']} on tier {c['tier']} with the dial {c['state']} averages {c['paper_avg_pct']:+.2f}% a trade over "
                f"{c['paper_trades']} paper trades against {c['backtest_avg_pct']:+.2f}% in the backtest (more than 3 points under). "
                "Check costs, fills and timing before trusting its number.")
        requests_log.add(j, "data", text, about=f"fidelity {c['rule']}", by="ananta-auto")
        if push:
            try:
                push(f"Fidelity: {c['rule']} tier {c['tier']} below its backtest", text[:220])
            except Exception:  # noqa: BLE001
                pass
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?, ?)", (key, str(int(j.now()))))
        out.append(key.split(":", 2)[2])
    j.db.commit()
    return out


RETIRE_N = 20


def retirement_watch(j, push=None) -> list[dict]:
    """BOOK500.md's retirement rule, its detection leg (requests #26 and #27; research audit BOOK500-BRAKES, Oct 15). For each setup the
    $500 book can trade (a measured tier-A cell in review #26's table whose strategy is ACTIVE or whose rule is PROMOTED), the last 20
    closed paper trades in that cell; with all 20 in, an average below zero after costs flags it. It only FLAGS: one request and one phone
    note per setup, saying nothing was switched off. Retiring (no new entries, open trades finish on their own plan, review in the repair
    shop) waits for Madhav's yes. The rule's second leg, 3+ points a trade under the backtest, is fidelity_alert. Before 20 trades nothing is
    decided. Returns one row per watched cell: rule, state, tier, closed (of 20), window_avg_pct, retire."""
    import time

    from jarvis.service import exposure, requests_log, strategy_status, universe_watch

    try:
        prom = universe_watch.promoted(j)
    except Exception:  # noqa: BLE001
        prom = set()
    try:
        dial = exposure.dial_by_day(j)
    except Exception:  # noqa: BLE001
        dial = {}
    cells = set()
    for r in table():
        if r["tier"] != "A":
            continue
        e = strategy_status.of_watch(r["rule"])
        if (e and e[1].get("status") == "ACTIVE") or f"{r['rule']}-UA" in prom:
            cells.add((r["rule"], r["state"]))
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    out = []
    for rule, state in sorted(cells):
        rows = j.db.execute("SELECT net_usd, entry_t FROM evidence_trades WHERE (watch=? OR watch LIKE ?) AND status='CLOSED' AND entry_t IS NOT NULL "
                            "ORDER BY exit_t", (f"{rule}-UA", f"{rule}.%-UA")).fetchall()
        mine = []
        for net, et in rows:
            d = dial.get(time.strftime("%Y-%m-%d", time.gmtime(et)))
            if ("?" if d is None else "OPEN" if d > 0 else "CLOSED") == state:
                mine.append(net or 0.0)
        win = mine[-RETIRE_N:]
        avg = round(sum(win) / len(win), 2) if win else None
        row = {"rule": rule, "state": state, "tier": "A", "closed": len(win), "of": RETIRE_N, "window_avg_pct": avg,
               "retire": bool(len(win) >= RETIRE_N and avg is not None and avg < 0)}
        out.append(row)
        key = f"ev:retire_flag:{rule}|{state}|A"
        if row["retire"] and not j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
            text = (f"Retirement rule (BOOK500.md): {rule} on tier A with the dial {state.lower()} averages {avg:+.2f}% a trade over its last "
                    f"{RETIRE_N} closed paper trades, below zero after costs. The rule says: no new entries, open trades finish on their own plan, a "
                    "review in the repair shop. Nothing was switched off; Madhav decides whether to retire it.")
            requests_log.add(j, "data", text, about=f"retirement {rule}", by="ananta-auto")
            if push:
                try:
                    push(f"Retirement rule met: {rule}", text[:220])
                except Exception:  # noqa: BLE001
                    pass
            j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?, ?)", (key, str(int(j.now()))))
            row["flagged"] = True
    j.db.commit()
    return out
