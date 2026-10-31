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


# 25 Oct audit: TMCV read +262% and TMPV +10%, which looked lopsided. Checked: the broker's average prices split the old Tata Motors cost
# 68.85% / 31.15% (TMPV / TMCV), exactly Tata Motors' published cost-of-acquisition split for the demerger (record date 14 Oct 2025).
# The numbers are right; the note says so and gives the pair's combined result, which is the honest view of one original holding.
DEMERGERS = {("TMPV", "TMCV"): "one Tata Motors holding split by the demerger (record date 14 Oct 2025); the broker splits its cost 68.85% / 31.15%, "
                               "as Tata Motors published"}


def demerger_notes(positions: dict) -> dict:
    out = {}
    for pair, why in DEMERGERS.items():
        ps = [positions.get(s) for s in pair]
        if all(ps) and all(p["avg"] for p in ps):
            cost = sum(p["avg"] for p in ps)
            now = sum(p["last"] for p in ps)
            words = f"{why}; together {100 * (now / cost - 1):+.1f}% on the original cost"
            for s in pair:
                out[s] = words
    return out


def last_session(now: dt.datetime | None = None) -> str | None:
    """The last completed NSE session (a trading day on the calendar, after 16:00 IST), or None without a calendar."""
    import pandas as pd

    p = paths.data_dir() / "silver" / "calendar" / "calendar.parquet"
    if not p.exists():
        return None
    cal = pd.read_parquet(p, columns=["date", "is_trading_day"])
    ist = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    cut = ist.date() if ist.hour >= 16 else ist.date() - dt.timedelta(days=1)
    days = pd.to_datetime(cal.loc[cal["is_trading_day"].astype(bool), "date"]).dt.date
    days = days[days <= cut]
    return str(days.max()) if len(days) else None


def stale_marks(snap: dict, symbols: list[str], now: dt.datetime | None = None) -> tuple[dict, dict]:
    """25 Oct audit: when the Zerodha snapshot is older than the last completed session, the twin is marked at that session's NSE closes
    (sealed purpose account_marks, Madhav 25 Oct 2026) instead of the stale snapshot prices. Returns (prices, note); prices is empty and the note
    says why when the snapshot is current or no close is on file yet. Marks only: fills keep the snapshot rule above."""
    last = last_session(now)
    day = snap.get("day")
    if not last or not day or day >= last:
        return {}, {"marked_at": "snapshot", "snapshot_day": day, "last_session": last}
    try:
        from india import sealed
        df = sealed.read_marks("account_marks", last, symbols)
    except Exception as e:  # noqa: BLE001 - recorded, never hidden: the view says the marks are the stale snapshot's
        return {}, {"marked_at": "snapshot (stale)", "snapshot_day": day, "last_session": last, "why": f"{type(e).__name__}: {e}"[:200]}
    px = {r.symbol: float(r.close) for r in df.itertuples()}
    return px, {"marked_at": f"NSE close {last}" if px else "snapshot (stale)", "snapshot_day": day, "last_session": last,
                "closes_found": len(px), "of": len(set(symbols))}


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
    nse, marks = stale_marks(snap, list(book["positions"]))
    for sym, pos in book["positions"].items():
        if nse.get(sym):
            pos["last"] = nse[sym]
    stocks = sum(v["qty"] * v["last"] for v in book["positions"].values())
    value = stocks + book["cash_inr"] + book["options_inr"]
    real = {h["tradingsymbol"]: int(h["quantity"]) for h in snap.get("holdings") or [] if (h.get("quantity") or 0) > 0}
    diff = [{"symbol": s, "twin_qty": book["positions"].get(s, {}).get("qty", 0), "real_qty": real.get(s, 0)} for s in sorted(set(real) | set(book["positions"]))
            if book["positions"].get(s, {}).get("qty", 0) != real.get(s, 0)]
    p.write_text(json.dumps(book, indent=1))
    pending = [r["day"] for r in led if r.get("mode") == "autonomous" and r.get("moves") and r["day"] not in book["applied_days"]]
    start = book.get("opened_value_inr") or round(value)
    notes = demerger_notes(book["positions"])
    view = {"built_at": _now(), "paper": True, "opened_at": book["opened_at"], "start_inr": round(start), "return_pct": round(100 * (value / start - 1), 2) if start else 0.0, "value_inr": round(value), "stocks_inr": round(stocks), "cash_inr": round(book["cash_inr"]), "options_inr": round(book["options_inr"]),
            "positions": sorted([{"symbol": s, **{k: round(v, 2) if isinstance(v, float) else v for k, v in pos.items()}, "value_inr": round(pos["qty"] * pos["last"]), "pnl_pct": round(100 * (pos["last"] / pos["avg"] - 1), 1) if pos["avg"] else None,
                                  **({"note": notes[s]} if s in notes else {})}
                                 for s, pos in book["positions"].items()], key=lambda r: -r["value_inr"]),
            "trades": book["trades"][-30:], "trades_count": len(book["trades"]), "costs_inr": round(book["costs_inr"], 2), "applied_days": book["applied_days"], "pending_days": pending,
            "differs_from_real": diff, "admitted": sorted(adm), "marks": marks,
            "words": ((f"Prices are the NSE close of {marks['last_session']}: the account snapshot is from {marks['snapshot_day']}. "
                       if str(marks.get("marked_at", "")).startswith("NSE") else
                       f"Prices are from the account snapshot of {marks['snapshot_day']}, older than the last session ({marks['last_session']}). "
                       if marks.get("marked_at") == "snapshot (stale)" else "")
                      + f"₹{value:,.0f} on paper: ₹{stocks:,.0f} in {len(book['positions'])} stocks, ₹{book['options_inr']:,.0f} set aside for options, ₹{book['cash_inr']:,.0f} cash. "
                      + (f"{len(book['trades'])} paper trade{'s' if len(book['trades']) != 1 else ''} so far." if book["trades"] else "No paper trades yet.")
                      + (" Today's move fills after the session closes." if pending else "")
                      + (" It buys a new stock only once a rule has proved itself on paper and you say yes." if not adm else ""))}
    try:   # 30 Oct (Phase 5): the frozen "as he had it" portfolio and the Nifty 500 beside the twin, every run
        view["benchmark"] = benchmark(book, marks)
    except Exception as e:  # noqa: BLE001
        view["benchmark"] = {"status": "unavailable", "why": f"{type(e).__name__}: {str(e)[:120]}"}
    (_dir() / "view.json").write_text(json.dumps(view, indent=1))
    return view


# ----------------------------------------------------------------------------------------------- Phase 5: the twin against the frozen portfolio and the index

def frozen(book: dict) -> dict:
    """The holdings as they were when the twin opened, frozen: never traded, only marked. Written once from the opening snapshot."""
    p = _dir() / "frozen.json"
    f = _load(p)
    if f:
        return f
    snap = _load(Path(book["opened_from"]), {}) or {}
    pos = {h["tradingsymbol"]: {"qty": int(h["quantity"]), "avg": float(h.get("average_price") or 0), "last_at_open": float(h.get("last_price") or 0)}
           for h in snap.get("holdings") or [] if (h.get("quantity") or 0) > 0}
    eq = ((snap.get("margins") or {}).get("equity") or {}).get("available") or {}
    cash = float(eq.get("live_balance", eq.get("cash", 0)) or 0)
    opt = float(book.get("opened_value_inr") or 0) - sum(v["qty"] * v["last_at_open"] for v in pos.values()) - cash
    f = {"frozen_at": _now(), "from": book["opened_from"], "day": book.get("snapshot_day"), "positions": pos, "cash_inr": round(cash, 2), "options_inr": round(opt, 2),
         "start_inr": book.get("opened_value_inr"), "note": "Madhav's holdings as they stood when the twin opened; never traded, marked at the same prices as the twin"}
    p.write_text(json.dumps(f, indent=1))
    return f


def benchmark(book: dict, marks: dict) -> dict:
    """One row a session in paper/account/benchmark.jsonl: the twin, the frozen portfolio and the Nifty 500 (price index; dividends of about
    1.2-1.5% a year are not in it and are said) since the day the twin opened. Words for the view and the facts."""
    from india import sealed
    f = frozen(book)
    last = {s: pos["last"] for s, pos in book["positions"].items()}
    nse = {}
    try:
        snap = allocator.account()
        nse, _m = stale_marks(snap, list(f["positions"]))
    except Exception:  # noqa: BLE001
        pass
    px = {**{s: v.get("last_at_open", 0) for s, v in f["positions"].items()}, **{s: v for s, v in nse.items() if v}, **{s: v for s, v in last.items() if v}}
    frozen_val = sum(v["qty"] * px.get(s, v["last_at_open"]) for s, v in f["positions"].items()) + f["cash_inr"] + f["options_inr"]
    twin_val = sum(v["qty"] * v["last"] for v in book["positions"].values()) + book["cash_inr"] + book["options_inr"]
    start = float(f.get("start_inr") or book.get("opened_value_inr") or twin_val)
    day = marks.get("last_session") or marks.get("snapshot_day")
    n500 = None
    try:
        ix = sealed.read_index("paper_context", f["day"], ["NIFTY 500"])
        ix = ix.sort_values("date")
        if len(ix):
            first = float(ix.iloc[0]["close"])
            lastrow = ix[ix["date"].astype(str) <= str(day)]
            n500 = {"from": str(ix.iloc[0]["date"]), "to": str(lastrow.iloc[-1]["date"]) if len(lastrow) else None, "ret_pct": round(100 * (float(lastrow.iloc[-1]["close"]) / first - 1), 2) if len(lastrow) else None}
    except Exception as e:  # noqa: BLE001
        n500 = {"error": f"{type(e).__name__}: {str(e)[:80]}"}
    row = {"day": day, "at": _now(), "twin_inr": round(twin_val), "frozen_inr": round(frozen_val), "start_inr": round(start),
           "twin_ret_pct": round(100 * (twin_val / start - 1), 2), "frozen_ret_pct": round(100 * (frozen_val / start - 1), 2),
           "nifty500_ret_pct": (n500 or {}).get("ret_pct"), "twin_minus_frozen_pct": round(100 * (twin_val - frozen_val) / start, 2)}
    managed = _load(paths.data_dir() / "paper" / "managed" / "view.json")      # 30 Oct (Madhav's yes): the managed book, the fourth column
    if managed and managed.get("value_inr"):
        row.update({"managed_inr": managed["value_inr"], "managed_ret_pct": managed.get("return_pct"), "managed_start_day": managed.get("start_day"),
                    "managed_sessions": (managed.get("clock") or {}).get("sessions"), "managed_minus_frozen_pct": round(100 * (managed["value_inr"] - frozen_val) / start, 2)})
    p = _dir() / "benchmark.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
    rows = [r for r in rows if r.get("day") != day] + [row]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    try:                                   # 30 Oct outsider r4: "since 22 Oct (2 sessions)" counted benchmark rows, while the clock said 6: count trading days
        from india import managed
        sessions = managed.sessions_between(f["day"], str(day)) if day and str(day) > f["day"] else 0
    except Exception:  # noqa: BLE001
        sessions = len(rows)
    row["sessions"] = sessions
    words = (f"Since {f['day']} ({sessions} session{'s' if sessions != 1 else ''}): the twin {row['twin_ret_pct']:+.2f}%, your holdings left as they were {row['frozen_ret_pct']:+.2f}%, "
             f"the Nifty 500 {row['nifty500_ret_pct']:+.2f}% (price index, dividends not in it). " if row.get("nifty500_ret_pct") is not None else
             f"Since {f['day']} ({sessions} sessions): the twin {row['twin_ret_pct']:+.2f}%, your holdings left as they were {row['frozen_ret_pct']:+.2f}%. ")
    if row.get("managed_ret_pct") is not None:
        words += f"The managed book (cuts replaced on paper, since {row.get('managed_start_day')}, session {row.get('managed_sessions')} of 60): {row['managed_ret_pct']:+.2f}%. "
    words += "Nothing is read into the gap before 60 sessions; the twin's changes so far are the allocator's sleeve and weak-holding moves."
    return {"status": "ok", **row, "sessions": sessions, "frozen_day": f["day"], "words": words}


if __name__ == "__main__":
    v = run() if (sys.argv[1:] or ["run"])[0] == "run" else (_load(_dir() / "view.json") or {})
    print(v.get("words"))
