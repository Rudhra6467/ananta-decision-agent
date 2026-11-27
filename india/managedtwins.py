"""The managed book's two twins (Madhav, 26 Nov 2026 22:22 Toronto, in chat: "Yes, let's set it up"; open-list flag 290).

Two books that make no decisions, marked every session from the managed book's first day (30 Oct 2026), so the book's page can say in
rupees what Ananta's own decisions added or cost:
  held     the 30 Oct stocks and cash held unchanged (no cut, no replacement, no park)
  index    the 30 Oct stocks' value all in the Nifty index fund (NIFTYBEES) at the 30 Oct close, the cash kept as cash
Stocks and cash only: the options lot is the options line's own result and is kept apart, exactly as india/managed.py split() keeps it.

Reporting only. It reads the managed book's state (paper/managed/state.json) and the paper book's own daily bars (managed.bars(), the
same prices the book is marked at); it writes paper/managed/twins.json and changes nothing the book does.

  python -m india.managedtwins        -> paper/managed/twins.json (and prints the line)
"""
from __future__ import annotations

import datetime as dt
import json

from india import paths

FUND = "NIFTYBEES"


def _dir():
    return paths.data_dir() / "paper" / "managed"


def _load(p, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def start_holdings(book: dict) -> dict[str, int]:
    """The stocks held on the book's first day: what it holds now from the account, plus every share it sold of a stock it never bought."""
    bought = {t["symbol"] for t in book.get("trades") or [] if t.get("filled") and t.get("side") == "BUY"}
    out = {s: int(v["qty"]) for s, v in (book.get("positions") or {}).items() if v.get("source") == "twin" and int(v.get("qty") or 0) > 0}
    for t in book.get("trades") or []:
        if t.get("filled") and t.get("side") == "SELL" and t["symbol"] not in bought:
            out[t["symbol"]] = out.get(t["symbol"], 0) + int(t["qty"])
    return out


def stocks_cash_start(book: dict) -> float:
    """The book's stocks and cash at the start, counted as india/managed.py split() counts them (money moved into options added back)."""
    moved_in = sum(float(m["inr"]) * (1 if m.get("to") == "options" else -1) for m in book.get("sleeve_moves") or [])
    return float(book["start_inr"]) - (float(book["options_inr"]) - moved_in)


def stocks_cash_now(book: dict) -> float:
    moved_in = sum(float(m["inr"]) * (1 if m.get("to") == "options" else -1) for m in book.get("sleeve_moves") or [])
    return sum(v["qty"] * v["last"] for v in book["positions"].values()) + float(book["cash_inr"]) + moved_in


def marks(book: dict, closes) -> dict:
    """closes: a date-indexed frame of daily closes, one column a symbol. One mark per session from the start day to the last close."""
    start = str(book["start_day"])[:10]
    hold = start_holdings(book)
    idx = [d for d in closes.index if d.strftime("%Y-%m-%d") >= start]
    if not idx or idx[0].strftime("%Y-%m-%d") != start:
        return {"status": "missing", "words": f"no close on file for the book's first day ({start}), so the twins cannot be marked"}
    c0 = closes.loc[idx[0]]
    missing = sorted(s for s in list(hold) + [FUND] if s not in closes.columns or c0.get(s) != c0.get(s))
    if missing:
        return {"status": "missing", "words": "no first-day close for " + ", ".join(missing) + ", so the twins cannot be marked"}
    stocks0 = sum(q * float(c0[s]) for s, q in hold.items())
    cash0 = stocks_cash_start(book) - stocks0
    rows, last = [], {}
    for d in idx:
        c = closes.loc[d]
        for s in list(hold) + [FUND]:                   # a stock with no close that day stays at its last close
            if c.get(s) == c.get(s) and c.get(s) is not None:
                last[s] = float(c[s])
        held = cash0 + sum(q * last[s] for s, q in hold.items())
        index = cash0 + stocks0 * last[FUND] / float(c0[FUND])
        rows.append({"day": d.strftime("%Y-%m-%d"), "held_inr": round(held), "index_inr": round(index)})
    return {"status": "ok", "start_day": start, "holdings": hold, "stocks_start_inr": round(stocks0), "cash_start_inr": round(cash0),
            "stocks_cash_start_inr": round(stocks_cash_start(book)), "marks": rows}


def words(book: dict, m: dict, day: str | None = None) -> dict:
    """The line for the book's page: what the decisions added or cost against holding still, and against the index fund."""
    if m.get("status") != "ok":
        return {"status": m.get("status"), "words": m.get("words")}
    day = day or m["marks"][-1]["day"]
    row = next((r for r in reversed(m["marks"]) if r["day"] <= day), m["marks"][-1])
    now = stocks_cash_now(book)
    vs_held, vs_index = now - row["held_inr"], now - row["index_inr"]
    w = (f"Ananta's own decisions since {dt.date.fromisoformat(m['start_day']):%a %-d %b} {'added' if vs_held >= 0 else 'cost'} ₹{abs(vs_held):,.0f} against the same "
         f"stocks and cash held unchanged (₹{row['held_inr']:,.0f}); the book is ₹{abs(vs_index):,.0f} {'ahead of' if vs_index >= 0 else 'behind'} those stocks put in "
         f"the Nifty index fund (₹{row['index_inr']:,.0f}). Stocks and cash only, marked {dt.date.fromisoformat(row['day']):%a %-d %b}; the options lot apart.")
    return {"status": "ok", "day": row["day"], "managed_stocks_cash_inr": round(now), "held_inr": row["held_inr"], "index_inr": row["index_inr"],
            "decisions_vs_held_inr": round(vs_held), "decisions_vs_index_inr": round(vs_index), "words": w}


def build() -> dict:
    book = _load(_dir() / "state.json")
    if not book:
        out = {"status": "missing", "words": "the managed book has not started"}
    else:
        from india import managed
        df = managed.bars()
        closes = df.pivot_table(index="date", columns="symbol", values="close").sort_index()
        m = marks(book, closes)
        view = _load(_dir() / "view.json", {}) or {}
        out = {**m, **words(book, m, str(view.get("day") or "") or None)}
        out["built_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (_dir() / "twins.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


def line() -> str | None:
    """The twins' line as last written (read by the trials list and the book's page); None when not built yet."""
    t = _load(_dir() / "twins.json", {}) or {}
    return t.get("words") if t.get("status") == "ok" else None


if __name__ == "__main__":
    print(build().get("words"))
