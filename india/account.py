"""The account book (Madhav, 23 Oct 2026: "on the home tab it shows it trades on allocation; in the backend it runs everything"; design section 7, agreed
the same day): a paper twin of his account that trades the allocator's sleeves at account size. The research books do not change.

  python -m india.account run     apply every allocation day that is final, mark the positions, write paper/account/state.json and view.json
  python -m india.account show

How it works
- Opened once from the daily Zerodha ledger snapshot (read-only): every holding at its quantity and average price, the account's cash, and the
  options sleeve at the allocator's options amount (Rs 50,000; paper until funded).
- Each allocation day d is applied once, only when it is final (a later session's row exists in paper/allocation_ledger.jsonl), so a mode
  switch during the day never trades twice. Fills are at the newest snapshot's last price after d (decided on d, filled after it), with
  india/costs.py delivery costs charged on every leg.
    sleeve options -> cash / cash -> options      the sleeve amounts move
    stock_sell (TIDY / TRIM / REDUCE)             whole shares worth the amount, at most the position; proceeds less costs to cash
    stock_buy                                     only for a family ADMITTED on the evidence staircase (india/reconstruct.admitted()); none today
- Marked every run at the newest snapshot's last prices. If Madhav trades the real account himself, the twin does not follow; the view lists the
  differences so neither side is silently wrong.
Paper only: no order is placed; the no-order rule (india/leakcheck.py) holds. Only the allocator's paper decisions are applied here.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

from india import allocator, costs, paths


def _dir() -> Path:
    d = paths.data_dir() / "paper" / "account"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _load(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _prices(snap: dict) -> dict:
    return {h["tradingsymbol"]: float(h.get("last_price") or 0) for h in snap.get("holdings") or [] if h.get("tradingsymbol")}


def open_book(snap: dict, options_inr: float) -> dict:
    pos = {h["tradingsymbol"]: {"qty": int(h["quantity"]), "avg": float(h.get("average_price") or 0), "last": float(h.get("last_price") or 0)}
           for h in snap.get("holdings") or [] if (h.get("quantity") or 0) > 0}
    return {"opened_at": _now(), "opened_from": snap.get("source"), "snapshot_day": snap.get("day"), "positions": pos, "cash_inr": round(float(snap.get("cash_inr") or 0), 2),
            "options_inr": float(options_inr), "applied_days": [], "trades": [], "costs_inr": 0.0,
            "opened_value_inr": round(sum(int(h["quantity"]) * float(h.get("last_price") or 0) for h in snap.get("holdings") or [] if (h.get("quantity") or 0) > 0) + float(snap.get("cash_inr") or 0) + float(options_inr), 2)}


def _apply(book: dict, row: dict, px: dict, adm: set, when: str) -> list[dict]:
    done = []
    for m in row.get("moves") or []:
        kind, amt = m.get("kind"), float(m.get("inr") or 0)
        t = {"day": row["day"], "filled_at": when, "kind": kind, "why": m.get("why")}
        if kind == "sleeve":
            src, dst = m.get("from"), m.get("to")
            have = book["options_inr"] if src == "options" else book["cash_inr"]
            amt = min(amt, have)
            if src == "options":
                book["options_inr"] -= amt
            else:
                book["cash_inr"] -= amt
            if dst == "options":
                book["options_inr"] += amt
            else:
                book["cash_inr"] += amt
            t.update({"from": src, "to": dst, "inr": round(amt, 2)})
        elif kind == "stock_sell":
            sym = m.get("symbol")
            p = book["positions"].get(sym)
            price = px.get(sym) or (p or {}).get("last") or 0
            if not p or price <= 0:
                t.update({"symbol": sym, "skipped": "not held in the twin or no price"})
                done.append(t)
                continue
            qty = min(p["qty"], max(1, math.floor(amt / price)))
            value = qty * price
            c = costs.cost("delivery", "sell", value)
            p["qty"] -= qty
            book["cash_inr"] += value - c
            book["costs_inr"] += c
            t.update({"symbol": sym, "side": "SELL", "qty": qty, "price": price, "value_inr": round(value, 2), "cost_inr": round(c, 2), "pnl_inr": round(qty * (price - p["avg"]) - c, 2)})
            if p["qty"] <= 0:
                del book["positions"][sym]
        elif kind == "stock_buy":
            fam = m.get("family") or ""
            if f"stock:{fam}" not in adm:
                t.update({"symbol": m.get("symbol"), "skipped": "the family is not ADMITTED on the evidence staircase"})
                done.append(t)
                continue
            sym, price = m.get("symbol"), px.get(m.get("symbol")) or 0
            if price <= 0:
                t.update({"symbol": sym, "skipped": "no price"})
                done.append(t)
                continue
            qty = math.floor(min(amt, book["cash_inr"]) / price)
            if qty < 1:
                t.update({"symbol": sym, "skipped": "not enough cash for one share"})
                done.append(t)
                continue
            value = qty * price
            c = costs.cost("delivery", "buy", value)
            p = book["positions"].setdefault(sym, {"qty": 0, "avg": price, "last": price})
            p["avg"] = (p["avg"] * p["qty"] + value) / (p["qty"] + qty)
            p["qty"] += qty
            book["cash_inr"] -= value + c
            book["costs_inr"] += c
            t.update({"symbol": sym, "side": "BUY", "qty": qty, "price": price, "value_inr": round(value, 2), "cost_inr": round(c, 2)})
        done.append(t)
    return done


def run() -> dict:
    snap = allocator.account()
    cfg = allocator.settings()
    p = _dir() / "state.json"
    book = _load(p) or (open_book(snap, cfg["options_inr"]) if snap.get("status") == "ok" else None)
    if book is None:
        return {"status": "missing", "words": "no account snapshot yet: the twin opens from the first daily ledger snapshot"}
    try:
        from india import reconstruct
        adm = reconstruct.admitted()
    except Exception:  # noqa: BLE001
        adm = set()
    led = allocator._jsonl(paths.data_dir() / "paper" / "allocation_ledger.jsonl")
    days = sorted({r["day"] for r in led})
    px = _prices(snap)
    when = snap.get("taken_at") or _now()
    for r in led:
        d = r["day"]
        final = any(x > d for x in days)
        if not final or d in book["applied_days"] or r.get("mode") != "autonomous" or d < (book.get("snapshot_day") or ""):
            continue
        book["trades"] += _apply(book, r, px, adm, when)
        book["applied_days"].append(d)
    for sym, pos in book["positions"].items():
        if px.get(sym):
            pos["last"] = px[sym]
    stocks = sum(v["qty"] * v["last"] for v in book["positions"].values())
    value = stocks + book["cash_inr"] + book["options_inr"]
    real = {h["tradingsymbol"]: int(h["quantity"]) for h in snap.get("holdings") or [] if (h.get("quantity") or 0) > 0}
    diff = [{"symbol": s, "twin_qty": book["positions"].get(s, {}).get("qty", 0), "real_qty": real.get(s, 0)} for s in sorted(set(real) | set(book["positions"]))
            if book["positions"].get(s, {}).get("qty", 0) != real.get(s, 0)]
    p.write_text(json.dumps(book, indent=1))
    pending = [r["day"] for r in led if r.get("mode") == "autonomous" and r.get("moves") and r["day"] not in book["applied_days"]]
    start = book.get("opened_value_inr") or round(value)
    view = {"built_at": _now(), "paper": True, "opened_at": book["opened_at"], "start_inr": round(start), "return_pct": round(100 * (value / start - 1), 2) if start else 0.0, "value_inr": round(value), "stocks_inr": round(stocks), "cash_inr": round(book["cash_inr"]), "options_inr": round(book["options_inr"]),
            "positions": sorted([{"symbol": s, **{k: round(v, 2) if isinstance(v, float) else v for k, v in pos.items()}, "value_inr": round(pos["qty"] * pos["last"]), "pnl_pct": round(100 * (pos["last"] / pos["avg"] - 1), 1) if pos["avg"] else None}
                                 for s, pos in book["positions"].items()], key=lambda r: -r["value_inr"]),
            "trades": book["trades"][-30:], "trades_count": len(book["trades"]), "costs_inr": round(book["costs_inr"], 2), "applied_days": book["applied_days"], "pending_days": pending,
            "differs_from_real": diff, "admitted": sorted(adm),
            "words": (f"Account book (paper twin): ₹{value:,.0f} — stocks ₹{stocks:,.0f} in {len(book['positions'])} names, options ₹{book['options_inr']:,.0f}, cash ₹{book['cash_inr']:,.0f}; "
                      f"{len(book['trades'])} paper trade(s) so far" + (f"; the moves of {', '.join(pending)} fill after that day closes" if pending else "") + "."
                      + (" It buys new names only from ADMITTED families; none yet." if not adm else ""))}
    (_dir() / "view.json").write_text(json.dumps(view, indent=1))
    return view


if __name__ == "__main__":
    v = run() if (sys.argv[1:] or ["run"])[0] == "run" else (_load(_dir() / "view.json") or {})
    print(v.get("words"))
