"""Reviews 39 and 40 (pre-registered in docs/research/REVIEW_39.md and REVIEW_40.md, 10 Nov 2026; Madhav lifted Rule B for these two):
the $500 book's core on eight years of daily candles. 39: is the live buy-in-thirds core at least as good as the all-in core it replaced?
40: does one confirmation step (the dial open on two closes in a row before a first buy) cut the flip-flops without hurting the result?

The core only (BTC 0.40, ETH 0.20 of the book; the rest in cash): no edge trades, no brakes. A decision on a day's close fills at the next
day's open, with the NDAX fee and the coin's half-spread. THIRDS calls discipline.core_targets the way the live step does. Nothing is tuned.

    python -m src.research.review39 <pre-registration commit>      # writes docs/research/review39.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from src.research import review25 as R

START = 500.0
CORE = {"BTC": 0.40, "ETH": 0.20}
SPLITS = {"DISCOVERY": ("2018-01-01", "2023-12-31"), "CONFIRM": ("2024-01-01", "2099-01-01")}
OUT = Path(__file__).resolve().parents[2] / "docs" / "research" / "review39.json"


def load() -> dict:
    """BTC and ETH daily candles on the days both have, with the averages the rules read."""
    raw = {c: {b[0]: b for b in R.daily(c)} for c in CORE}
    days = sorted(set(raw["BTC"]) & set(raw["ETH"]))
    out: dict = {"t": days}
    for c in CORE:
        out[c] = {"o": [raw[c][t][1] for t in days], "c": [raw[c][t][4] for t in days]}
        out[c]["ema50"] = R.ema(out[c]["c"], 50)
    out["BTC"]["sma200"] = R.sma(out["BTC"]["c"], 200)
    out["BTC"]["sma20"] = R.sma(out["BTC"]["c"], 20)
    return out


def sim(D: dict, mode: str, confirm: bool, t0: int, t1: int, cost: dict | None = None) -> dict:
    from jarvis.service import discipline
    from src.intelligence.ndax_costs import DEFAULT_HS, HALF_SPREAD, NDAX_FEE

    cost = cost or {c: NDAX_FEE + HALF_SPREAD.get(c, DEFAULT_HS) for c in CORE}
    T, btc = D["t"], D["BTC"]
    cash, pos, done, last_tr = START, {}, 0, None
    eq, entries, fills, paid, invested = [], 0, 0, 0.0, []

    def state_at(i: int) -> str:
        return discipline.dial_state_from(btc["c"][i], btc["ema50"][i], btc["sma200"][i]) or "CLOSED"

    for i in range(1, len(T) - 1):
        if T[i] < t0 or T[i] > t1:
            continue
        px = {c: D[c]["c"][i] for c in CORE}
        value = cash + sum(q * px[c] for c, q in pos.items())
        eq.append(value)
        invested.append(1 - cash / value if value else 0.0)
        nxt = {c: D[c]["o"][i + 1] for c in CORE}

        def sell(c: str, qty: float) -> None:
            nonlocal cash, fills, paid
            qty = min(qty, pos.get(c, 0.0))
            if qty <= 0:
                return
            cash += qty * nxt[c] * (1 - cost[c])
            paid += qty * nxt[c] * cost[c]
            fills += 1
            pos[c] -= qty
            if pos[c] <= 1e-12:
                del pos[c]

        def buy(c: str, cad: float) -> None:
            nonlocal cash, fills, paid
            cad = min(cad, cash)
            if cad <= 0:
                return
            pos[c] = pos.get(c, 0.0) + cad / (nxt[c] * (1 + cost[c]))
            paid += cad * cost[c] / (1 + cost[c])
            cash -= cad
            fills += 1

        state = state_at(i)
        was_open = state_at(i - 1) != "CLOSED"
        had_core = bool(pos)
        if mode == "HOLD60":
            if not pos:
                buy("BTC", 0.6 * value)
            continue
        if mode == "GATE50_60":                                   # the hurdle at the core's weight: Bitcoin above its 50-day average
            on = btc["ema50"][i] is not None and btc["c"][i] > btc["ema50"][i]
            if on and not pos:
                entries += 1
                buy("BTC", 0.6 * value)
            elif not on and pos:
                sell("BTC", pos["BTC"])
            continue
        if state == "CLOSED":
            for c in list(pos):
                sell(c, pos[c])
            done = 0
            continue
        if mode == "ALLIN":
            if not pos and (was_open or not confirm):
                entries += 1
                for c, w in CORE.items():
                    buy(c, w * value)
            continue
        # THIRDS: the live core-v2, in the live step's order (each coin's own invalidation, trims, then buys)
        for c in list(pos):
            e = D[c]["ema50"][i]
            if e is not None and px[c] < e:
                sell(c, pos[c])
        if not pos:
            done = 0
        held = {c: q * px[c] for c, q in pos.items()}
        plan = discipline.core_targets(state, value, CORE, done, held=held)
        for c in list(pos):
            over = held[c] - plan["target"].get(c, 0.0)
            if over > plan["trim_band"] * value:
                sell(c, over / px[c])
                held[c] = pos.get(c, 0.0) * px[c]
        core_now = dict(pos)
        want = True
        if state == "CONFIRMED" and core_now:
            above20 = btc["sma20"][i] is not None and btc["c"][i] > btc["sma20"][i]
            want = above20 and last_tr != i and done < 3
        if confirm and not core_now and not was_open:
            want = False
        if want:
            added = False
            for c in CORE:
                need = plan["next"].get(c, 0.0) - (held.get(c, 0.0) if c in core_now else 0.0)
                if need > max(5.0, 0.01 * value):
                    buy(c, need)
                    added = True
            if added:
                if not had_core or not core_now:
                    entries += 1
                done, last_tr = done + 1, i
    if len(eq) < 2:
        return {"days": len(eq)}
    peak, mdd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    yrs = len(eq) / 365
    cagr = (eq[-1] / START) ** (1 / yrs) - 1
    return {"end": round(eq[-1], 2), "return_pct": round(100 * (eq[-1] / START - 1), 1), "cagr_pct": round(100 * cagr, 1), "max_fall_pct": round(100 * mdd, 1),
            "cagr_over_fall": round(cagr / abs(mdd), 3) if mdd else None, "entries": entries, "entries_per_year": round(entries / yrs, 1), "fills": fills,
            "cost_paid": round(paid, 2), "avg_invested_pct": round(100 * sum(invested) / len(invested), 1), "days": len(eq)}


ROWS = (("ALLIN", "ALLIN", False), ("THIRDS", "THIRDS", False), ("ALLIN+CONFIRM", "ALLIN", True), ("THIRDS+CONFIRM", "THIRDS", True),
        ("HOLD60", "HOLD60", False), ("GATE50_60", "GATE50_60", False))


def main(prereg: str = "") -> dict:
    D = load()
    last = time.strftime("%Y-%m-%d", time.gmtime(D["t"][-1]))
    out: dict = {"reviews": [39, 40], "written": time.strftime("%Y-%m-%d %H:%M"), "pre_registration_commit": prereg or "unanchored",
                 "data": {"first": time.strftime("%Y-%m-%d", time.gmtime(D["t"][0])), "last": last, "days": len(D["t"])}, "periods": {}}
    for name, (a, b) in SPLITS.items():
        out["periods"][name] = {row: sim(D, mode, confirm, R._t(a), R._t(b)) for row, mode, confirm in ROWS}
    P = out["periods"]
    k = "cagr_over_fall"
    r39 = {p: {"ratio_ok": P[p]["THIRDS"][k] >= P[p]["ALLIN"][k], "ends_above_start": P[p]["THIRDS"]["end"] > START} for p in P}
    out["review39"] = {"by_period": r39, "pass": all(v["ratio_ok"] and v["ends_above_start"] for v in r39.values())}
    base = "THIRDS" if P["DISCOVERY"]["THIRDS"][k] > P["DISCOVERY"]["ALLIN"][k] else "ALLIN"
    r40 = {p: {"entries_cut_pct": round(100 * (1 - P[p][base + "+CONFIRM"]["entries"] / P[p][base]["entries"]), 1) if P[p][base]["entries"] else None,
               "ratio_not_lower": P[p][base + "+CONFIRM"][k] >= P[p][base][k]} for p in P}
    out["review40"] = {"base": base, "by_period": r40,
                       "pass": all((v["entries_cut_pct"] or 0) >= 25 and v["ratio_not_lower"] for v in r40.values())}
    OUT.write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    r = main(sys.argv[1] if len(sys.argv) > 1 else "")
    for p, rows in r["periods"].items():
        print(p)
        for name, v in rows.items():
            print(f"  {name:15}", {x: v.get(x) for x in ("return_pct", "cagr_pct", "max_fall_pct", "cagr_over_fall", "entries", "entries_per_year", "cost_paid", "avg_invested_pct")})
    print("review 39:", json.dumps(r["review39"]))
    print("review 40:", json.dumps(r["review40"]))
