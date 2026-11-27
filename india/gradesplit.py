"""The holding grade shown in two parts (Madhav, 26 Nov 2026 22:22 Toronto, in chat: "Yes, let's set it up"; open-list flag 291).

The allocator's grade (india/allocator.py, weights pinned in india/registrations/allocation_rule_v1.json) adds up eight parts. Two of them
say nothing about where a stock goes next: the result on what was paid (up to 15 points) and the holding's size in the account (up to 10).
The 17 Nov cut study (india/cutstudy.py) found the full grade right 53% / 52% against a random stock's 54% / 53%.

This module SHOWS the grade in two parts, from the allocator's own `parts`, and changes nothing:
  outlook   the stock itself: trend (above 200d, above 20d, RSI), regime fit, volatility, liquidity; scaled to 0-100 (their weights add to 75)
  fit       its size in the account: the concentration part (within size / large / too large)
  result    the result on what was paid, shown as a fact and not counted
It also names the holdings where the grade and the weak-against-the-market check (india/managed.weak_vs_market, the one rule with a small
edge in the cut study) disagree. The cut rule keeps reading today's grade until HS1 (flag 292) is read and Madhav says yes.

Reporting only: reads paper/allocation_view.json (and the managed book's bars for the weak check), writes paper/gradesplit.json.

  python -m india.gradesplit        -> paper/gradesplit.json (and prints the line)
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from india import paths

OUTLOOK_PARTS = ("trend", "regime", "volatility", "liquidity")


def _load(p, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def outlook_max(weights: dict) -> float:
    return float(sum(weights.get(k, 0) for k in ("above_200d", "above_20d", "rsi_healthy", "regime_fit", "volatility", "liquidity"))) or 75.0


def fit_words(conc: float | None, full: float) -> str:
    if conc is None:
        return "size unknown"
    return "within size" if conc >= full else ("large" if conc > 0 else "too large")


def split(holdings: list[dict], weights: dict, weak: set | None = None) -> list[dict]:
    mx, full = outlook_max(weights), float(weights.get("concentration", 10))
    out = []
    for h in holdings:
        parts = h.get("parts") or {}
        rated = bool(h.get("rated")) and str(h.get("grade")) != "not graded"
        o = sum(float(parts.get(k) or 0) for k in OUTLOOK_PARTS)
        row = {"symbol": h.get("symbol"), "grade": h.get("grade"), "score": h.get("score"), "action": h.get("action"),
               "outlook": round(100 * o / mx) if rated else None, "fit": fit_words(parts.get("concentration"), full),
               "weight_pct": h.get("weight_pct"), "result_pct": h.get("pnl_pct"), "rated": rated}
        if weak is not None and rated:
            w = h.get("symbol") in weak
            row["weak_vs_market"] = w
            row["disagree"] = (w and h.get("action") in ("HOLD", "ADD", "WATCH")) or (not w and h.get("action") == "REDUCE")
        out.append(row)
    return out


def words(rows: list[dict]) -> str:
    r = [x for x in rows if x["rated"]]
    if not r:
        return ""
    s = sorted(r, key=lambda x: -(x["outlook"] or 0))
    lead = ", ".join(f"{x['symbol']} {x['outlook']}" for x in s[:3])
    tail = ", ".join(f"{x['symbol']} {x['outlook']}" for x in s[-2:])
    big = [x["symbol"] for x in r if x["fit"] != "within size"]
    dis = [x["symbol"] for x in r if x.get("disagree")]
    w = (f"The grade in two parts (shown only; the cut rule still reads the full grade): outlook, the stock itself out of 100, strongest {lead}, "
         f"weakest {tail}; ")
    w += (f"larger than its size allows: {', '.join(big)}; " if big else "every holding within its size; ")
    w += "the result on what was paid is shown, not counted."
    if dis:
        w += f" The grade and the weak-against-the-market check disagree on {', '.join(dis)}."
    return w


def build() -> dict:
    d = paths.data_dir() / "paper"
    v = _load(d / "allocation_view.json", {}) or {}
    rule = _load(Path(__file__).parent / "registrations" / "allocation_rule_v1.json", {}) or {}
    weights = rule.get("rating") or {}
    weak = None
    try:                                   # the weak check reads the book's own bars; it never breaks the split
        from india import managed
        weak = managed.weak_vs_market(managed.features(managed.bars(), v.get("day") or str(dt.date.today())), managed.cfg())
    except Exception:  # noqa: BLE001
        weak = None
    rows = split(v.get("holdings") or [], weights, weak)
    out = {"status": "ok" if rows else "empty", "day": v.get("day"), "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "rows": rows, "words": words(rows), "weak_check": weak is not None}
    (d / "gradesplit.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    print(build().get("words"))
