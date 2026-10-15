"""The ten graduation gates (research audit, Oct 15: card APP-GRAD).

The old app's "Graduation Readiness scorecard" (Ananta repo, analytics.graduation_readiness, 2026-05-29) was an objective paper-to-live
checklist: it asks for a repeatable edge that survives costs and different market states, not just a profit. The audit asked for it to be
turned into code and run unchanged on every paper book. This is that code. The ten definitions and thresholds are the old app's, ported as
written. A threshold changes only with a written reason in THRESHOLD_LOG, and tests/test_graduation.py pins the numbers so an edit cannot be
a drive-by.

Read-only: it scores a list of closed trades and changes nothing. It is a second view beside Rule A (60 market days, both dial states seen,
execution fidelity within 3 points) and the Acceptance Gate, never a replacement for either.

What a market must supply (nothing else is assumed):
  pnl        money made or lost on the closed trade, after fees and the spread the fill paid
  t          when it closed (epoch seconds, or a YYYY-MM-DD date)
  regime     the market state at entry. For the $500 book: the exposure dial, "OPEN" or "CLOSED". Gate 5 needs two states that both pay.
  sideways   True/False if the book labels sideways markets; None if it does not. The old app labelled them by volatility (low compression).
             A book with no such label cannot be scored on gate 7: the gate is reported "not measured" and does not pass (never a quiet pass).
"""
from __future__ import annotations

import calendar
import time

# The old app's thresholds, written once. Changing one needs a line in THRESHOLD_LOG saying why (and Madhav's yes).
THRESHOLDS = {
    "round_trips": 50,               # gate 1: completed buy-and-sell pairs
    "profit_factor": 1.3,            # gate 3: money won divided by money lost, above
    "max_drawdown_pct": 15.0,        # gate 4: worst fall of the closed-trade equity, under
    "positive_regimes": 2,           # gate 5: market states that made money
    "top_regime_share_pct": 60.0,    # gate 5: the best state's share of the money made, at most
    "sideways_rate_multiple": 1.5,   # gate 7: trades per day in sideways markets vs overall, at most
    "observation_days": 30,          # gate 8: first exit to last exit, at least
    "weeks_positive": 2,             # gate 8: of the last 3 weeks
    "ruin_line_pct": 20.0,           # gate 9: the account is never down this much
    "single_trade_share_pct": 20.0,  # gate 10: the best trade's share of the money made, at most
}
THRESHOLD_LOG = [
    {"date": "2026-05-29", "what": "all ten, as the old app wrote them", "reason": "origin (Ananta repo, analytics.graduation_readiness)"},
    {"date": "2026-10-15", "what": "none changed", "reason": "ported unchanged (research audit card APP-GRAD)"},
]
DAY = 86400


def _ts(x) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(calendar.timegm(time.strptime(str(x)[:10], "%Y-%m-%d")))                  # a UTC date at 00:00
    except Exception:  # noqa: BLE001
        return None


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _drawdown_pct(pnls: list[float], start: float) -> float:
    """Worst peak-to-trough fall of the equity (start plus the running sum of closed trades), in percent."""
    if start <= 0:
        return 0.0
    eq = peak = start
    worst = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        if peak > 0:
            worst = max(worst, (peak - eq) / peak * 100.0)
    return round(worst, 3)


def _span_days(ts: list[float]) -> float:
    return max((max(ts) - min(ts)) / DAY, 0.0) if len(ts) >= 2 else 0.0


def score(trades: list[dict], start: float, now: float | None = None, costs_counted: bool = True) -> dict:
    """The ten gates over closed trades, oldest first. `start` is the book's starting money; `costs_counted` is the caller's statement that every
    pnl is after fees and the spread its fill paid (the $500 book fills at NDAX's own bid and ask plus the 0.20% fee)."""
    T = THRESHOLDS
    now = float(now if now is not None else time.time())
    rows = []
    for t in trades:
        ts = _ts(t.get("t"))
        if ts is not None and t.get("pnl") is not None:
            rows.append({"pnl": float(t["pnl"]), "t": ts, "regime": t.get("regime"), "sideways": t.get("sideways")})
    rows.sort(key=lambda r: r["t"])
    pnls = [r["pnl"] for r in rows]
    n = len(pnls)

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_rate, loss_rate = (len(wins) / n, len(losses) / n) if n else (0.0, 0.0)
    expectancy = win_rate * _mean(wins) - loss_rate * _mean([abs(p) for p in losses])
    gross_profit, gross_loss = sum(wins), sum(abs(p) for p in losses)
    pf = gross_profit / gross_loss if gross_loss > 0 else None
    dd = _drawdown_pct(pnls, start)

    net: dict[str, float] = {}
    for r in rows:
        k = r["regime"] or "UNKNOWN"
        net[k] = net.get(k, 0.0) + r["pnl"]
    pos = {k: v for k, v in net.items() if v > 0 and k != "UNKNOWN"}
    top_share = round(max(pos.values()) / sum(pos.values()) * 100.0, 2) if pos else 0.0
    regime_ok = len(pos) >= T["positive_regimes"] and top_share <= T["top_regime_share_pct"]

    side = [r for r in rows if r["sideways"] is True]
    side_measured = any(r["sideways"] is not None for r in rows)
    side_exp = round(_mean([r["pnl"] for r in side]), 4)
    overall_days, side_days = _span_days([r["t"] for r in rows]), _span_days([r["t"] for r in side])
    overall_rate = n / overall_days if overall_days > 0 else 0.0
    side_rate = len(side) / side_days if side_days > 0 else 0.0
    overtrading = overall_rate > 0 and side_rate > T["sideways_rate_multiple"] * overall_rate
    side_ok = side_measured and (not side or (side_exp >= 0 and not overtrading))

    weeks = []
    for w in range(3):                         # the 3 most recent 7-day windows
        lo, hi = now - (w + 1) * 7 * DAY, now - w * 7 * DAY
        inside = [r["pnl"] for r in rows if lo <= r["t"] < hi]
        weeks.append({"window": f"-{w * 7}..-{(w + 1) * 7}d", "net_pnl": round(sum(inside), 4), "trades": len(inside)})
    weeks_pos = sum(1 for x in weeks if x["net_pnl"] > 0)
    stable = overall_days >= T["observation_days"] and weeks_pos >= T["weeks_positive"]

    top_win = max(wins) if wins else 0.0
    top_share_trade = round(top_win / gross_profit * 100.0, 2) if gross_profit > 0 else 0.0

    def g(gid, label, target, actual, ok, measured=True):
        return {"id": gid, "label": label, "target": target, "actual": actual, "passed": bool(ok), "measured": measured}

    criteria = [
        g("min_trades", f"At least {T['round_trips']} completed round trips", f">= {T['round_trips']}", f"{n}", n >= T["round_trips"]),
        g("positive_expectancy", "Positive profit per trade", "> 0", f"{expectancy:+.2f} per trade", expectancy > 0),
        g("profit_factor", f"Profit factor above {T['profit_factor']}", f"> {T['profit_factor']}", f"{pf:.2f}" if pf is not None else "no losing trade yet",
          pf is not None and pf > T["profit_factor"]),
        g("max_drawdown", f"Worst fall under {T['max_drawdown_pct']:.0f}%", f"< {T['max_drawdown_pct']:.0f}%", f"{dd:.1f}%", dd < T["max_drawdown_pct"]),
        g("regime_diversification", "No single market state carries the profit",
          f">= {T['positive_regimes']} states pay, the best <= {T['top_regime_share_pct']:.0f}% of the profit",
          f"{len(pos)} state(s) pay, the best {top_share:.0f}%", regime_ok),
        g("friction_accounted", "Fees and spread counted", "every result after costs",
          ("counted" if costs_counted else "not counted") if n else "no trades yet", costs_counted and n > 0),
        g("no_sideways_overtrading", "No overtrading in sideways markets",
          f"profit >= 0 and rate <= {T['sideways_rate_multiple']}x overall",
          (f"{len(side)} sideways trade(s), average {side_exp:+.2f}" if side_measured else "this book has no sideways label"), side_ok, side_measured),
        g("stability", f"Watched {T['observation_days']}+ days, {T['weeks_positive']} of the last 3 weeks up",
          f">= {T['observation_days']} days and {T['weeks_positive']}/3 weeks", f"{overall_days:.0f} days, {weeks_pos}/3 weeks up", stable),
        g("account_survival", f"The account never down {T['ruin_line_pct']:.0f}%", f"fall < {T['ruin_line_pct']:.0f}%", f"worst fall {dd:.1f}%",
          dd < T["ruin_line_pct"]),
        g("risk_consistency", f"No single trade is over {T['single_trade_share_pct']:.0f}% of the profit",
          f"best trade <= {T['single_trade_share_pct']:.0f}% of the profit", f"best trade {top_share_trade:.0f}% of the profit",
          gross_profit > 0 and top_share_trade <= T["single_trade_share_pct"]),
    ]
    passed = sum(1 for c in criteria if c["passed"])
    return {"passed_count": passed, "total_gates": len(criteria), "all_passed": passed == len(criteria),
            "verdict": "READY" if passed == len(criteria) else "NOT READY",
            "headline": f"{passed} of {len(criteria)} passed: {'READY' if passed == len(criteria) else 'NOT READY'}",
            "criteria": criteria, "not_measured": [c["id"] for c in criteria if not c["measured"]],
            "metrics": {"closed_trades": n, "expectancy": round(expectancy, 4), "profit_factor": round(pf, 3) if pf is not None else None,
                        "net_pnl": round(sum(pnls), 4), "max_drawdown_pct": dd, "observation_days": round(overall_days, 2),
                        "regime_net_pnl": {k: round(v, 4) for k, v in net.items()}, "weekly_windows": weeks},
            "thresholds": dict(T)}


def sentence(g: dict, book: str) -> str:
    """The scorecard in one plain sentence for the nightly note and Ask: the count, then what still stands in the way."""
    short = {"min_trades": "round trips", "positive_expectancy": "profit per trade", "profit_factor": "profit factor", "max_drawdown": "worst fall",
             "regime_diversification": "market states", "friction_accounted": "costs counted", "no_sideways_overtrading": "sideways trading",
             "stability": "weeks watched", "account_survival": "account survival", "risk_consistency": "one trade carrying the profit"}
    left = [f"{short[c['id']]} ({c['actual']}, needs {c['target']})" + (", not measured" if not c["measured"] else "") for c in g["criteria"] if not c["passed"]]
    return (f"{book}: {g['passed_count']} of {g['total_gates']} graduation gates passed, {g['verdict'].lower()}"
            + (". Still short on: " + "; ".join(left) if left else "") + ".")


def book500_trades(j) -> tuple[list[dict], float]:
    """The $500 book's closed trades in the shape score() reads, and its starting money (CAD)."""
    from jarvis.service import ndax_book
    from src.research import book500 as B

    ndax_book._table(j)
    s = ndax_book._get(j, "state") or {}
    rows = []
    for c in s.get("closed") or []:
        d = c.get("dial")
        rows.append({"pnl": c.get("pnl_cad"), "t": c.get("out"), "regime": None if d is None else ("OPEN" if d else "CLOSED"), "sideways": None,
                     "coin": c.get("coin"), "sleeve": c.get("sleeve")})
    return rows, float(B.START_CAD)


def book500_card(j, now: float | None = None) -> dict:
    """What the nightly note and Ask show for the $500 book."""
    rows, start = book500_trades(j)
    g = score(rows, start, now=now if now is not None else j.now())
    return {"passed": g["passed_count"], "of": g["total_gates"], "verdict": g["verdict"], "not_measured": g["not_measured"],
            "closed_trades": g["metrics"]["closed_trades"], "sentence": sentence(g, "The $500 book"),
            "failing": [c["id"] for c in g["criteria"] if not c["passed"]]}
