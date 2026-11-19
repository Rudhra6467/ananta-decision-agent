"""Watchlists and the stock pages behind Markets' search (Madhav, 19 Nov 2026: "we will add one more option here watchlist. Where I can select
stocks ... Upon clicking this box, it takes us to the full watchlist screen" and "The search bar in markets is not responding. How to make it
fully functional. Like how we can view a stock in zerodha or trading view or money control").

  watchlists   the owner's lists, kept in <India data>/app/watchlists.json: [{id, name, symbols}]; each can be renamed or deleted
  stock_page   one stock: its price (Kite now, else the nightly quote book's close), chart, levels, holding, watchlists, Ask Ananta
  stocklist    every name the search can open: the quote book's names (about 1,950 NSE stocks)

Read-only towards the market and the broker; the lists are the only thing written, and only by the owner. Nothing here trades.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path

from jarvis import placekit as K
from jarvis.india import views

LOCK = threading.Lock()
MAX_LISTS, MAX_SYMS = 10, 50


def _path() -> Path:
    return views.DATA / "app" / "watchlists.json"


def _json(p: Path, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def lists() -> list[dict]:
    v = _json(_path(), [])
    return v if isinstance(v, list) else []


def _save(ls: list[dict]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(ls, indent=1))
    os.replace(tmp, p)


_NAMES: dict = {"at": 0.0, "v": {}}


def names() -> dict:
    """symbol -> company name, from the nightly name list behind the quote book (refreshed every 10 minutes)."""
    if time.time() - _NAMES["at"] > 600:
        raw = _json(views.DATA / "manifests" / "quotebook_names.json", {}) or {}
        _NAMES["v"] = {s: str((x or {}).get("name") or s) for s, x in raw.items() if (x or {}).get("kind", "stock") == "stock"}
        _NAMES["at"] = time.time()
    return _NAMES["v"]


def _tidy(n: str) -> str:
    n = re.sub(r"\s+(limited|ltd\.?)$", "", str(n or ""), flags=re.I).strip()
    return n.title() if n.isupper() else n


def stocklist() -> dict:
    """Every name the search box can open, for the app to filter as he types."""
    qb = (_json(views.DATA / "manifests" / "quotebook.json", {}) or {}).get("quotes") or {}
    nm = names()
    rows = [{"s": s, "n": _tidy(nm.get(s, s))} for s in sorted(qb) if re.fullmatch(r"[A-Z0-9&\-]{1,20}", s)]
    return {"ready": True, "rows": rows, "count": len(rows)}


def _quote_book(sym: str) -> dict:
    return ((_json(views.DATA / "manifests" / "quotebook.json", {}) or {}).get("quotes") or {}).get(sym) or {}


def act(body: dict) -> dict:
    """create | rename | delete | add | remove, by the owner. Returns the lists and a short sentence."""
    a, lid = str(body.get("action") or ""), str(body.get("id") or "")
    name = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:30]
    sym = re.sub(r"[^A-Z0-9&\-]", "", str(body.get("sym") or "").upper())[:20]
    with LOCK:
        ls = lists()
        cur = next((x for x in ls if x["id"] == lid), None)
        if a == "create":
            if len(ls) >= MAX_LISTS:
                raise ValueError(f"at most {MAX_LISTS} watchlists")
            n = max([int(m.group(1)) for x in ls for m in [re.fullmatch(r"w(\d+)", x["id"])] if m] or [0]) + 1
            cur = {"id": f"w{n}", "name": name or f"Watchlist {n}", "symbols": [sym] if sym else []}
            ls.append(cur)
            words = f"{cur['name']} created" + (f" with {sym}" if sym else "")
        elif cur is None:
            raise KeyError(lid)
        elif a == "rename":
            if not name:
                raise ValueError("a name is needed")
            cur["name"], words = name, f"Renamed to {name}"
        elif a == "delete":
            ls = [x for x in ls if x["id"] != lid]
            words = f"{cur['name']} deleted"
        elif a == "add":
            if not sym:
                raise ValueError("which stock?")
            if sym not in cur["symbols"]:
                if len(cur["symbols"]) >= MAX_SYMS:
                    raise ValueError(f"at most {MAX_SYMS} stocks in a list")
                cur["symbols"].append(sym)
            words = f"{sym} is in {cur['name']}"
        elif a == "remove":
            cur["symbols"] = [s for s in cur["symbols"] if s != sym]
            words = f"{sym} removed from {cur['name']}"
        else:
            raise ValueError(f"unknown action {a}")
        _save(ls)
    return {"ok": True, "words": words, "lists": ls, "id": (cur or {}).get("id")}


def quotes(syms: list[str]) -> dict:
    """symbol -> {last, change_pct, as_of, live}: Kite now when it answers, else the quote book's close with its day."""
    out: dict = {}
    try:
        from jarvis.india import livesession as L
        q = L.quotes([f"NSE:{s}" for s in syms]) if syms else {}
        for s in syms:
            r = (q.get("rows") or {}).get(f"NSE:{s}") or {}
            if isinstance(r.get("last"), (int, float)):
                pc = r.get("prev_close")
                out[s] = {"last": r["last"], "change_pct": round(100 * (r["last"] / pc - 1), 2) if pc else None, "live": True}
    except Exception:  # noqa: BLE001
        pass
    qb = (_json(views.DATA / "manifests" / "quotebook.json", {}) or {}).get("quotes") or {}
    for s in syms:
        if s not in out and (qb.get(s) or {}).get("close") is not None:
            r = qb[s]
            out[s] = {"last": r["close"], "change_pct": round(100 * r["chg_1d"], 2) if isinstance(r.get("chg_1d"), (int, float)) else None,
                      "as_of": r.get("as_of"), "live": False}
    return out


def _rs(v) -> str:
    return f"₹{v:,.2f}" if isinstance(v, (int, float)) else "—"


def _pc(v) -> str | None:
    return None if not isinstance(v, (int, float)) else f"{v:+.2f}%".replace("-", "−")


def _tone(v):
    return None if not isinstance(v, (int, float)) or v == 0 else ("good" if v > 0 else "bad")


def stock_row(s: str, q: dict, nm: dict) -> dict:
    x = q.get(s) or {}
    return K.row(s, K.clip(_tidy(nm.get(s, "")), 6, 40) or None, right=_rs(x.get("last")) if x else "—", right_sub=_pc(x.get("change_pct")),
                 right_tone=_tone(x.get("change_pct")), to=K.place(f"stock:{s}"))


def boxes() -> list[dict]:
    """One box per watchlist beside Nifty 50, Bank Nifty and the fear gauge (Madhav, 19 Nov)."""
    out = []
    for w in lists():
        q = quotes(w["symbols"][:20])
        ch = [v["change_pct"] for v in q.values() if isinstance(v.get("change_pct"), (int, float))]
        avg = sum(ch) / len(ch) if ch else None
        n = len(w["symbols"])
        out.append(K.box(K.clip(w["name"], 3, 18), f"{n} stock{'s' if n != 1 else ''}", change=_pc(avg), tone=_tone(avg),
                         caption="Average move today" if ch else "Add stocks", to=K.place(f"watchlist:{w['id']}")))
    return out


def sections(tags_all: bool = True) -> list[dict]:
    """Markets' watchlist sections: each list's first five on the overview, all of them under the Watchlist chip."""
    ls, nm = lists(), names()
    if not ls:
        return [{"t": "watchnew", "tags": ["watchlist"], "title": "Your watchlists",
                 "words": "Make a list of stocks to keep an eye on. Search a stock and add it, or start an empty list."}]
    out = []
    for w in ls:
        q = quotes(w["symbols"][:20])
        rows = [stock_row(s, q, nm) for s in w["symbols"]]
        more = K.place(f"watchlist:{w['id']}")
        if tags_all:
            out.append({**K.rows(w["name"], rows[:5] or [K.row("No stocks yet", "Tap to add some", to=more)], count=len(w["symbols"]) or None, more=more), "tags": ["all"]})
        out.append({**K.rows(w["name"], rows or [K.row("No stocks yet", "Search a stock to add it", to=more)], count=len(w["symbols"]) or None, more=more), "tags": ["watchlist"]})
    out.append({"t": "watchnew", "tags": ["watchlist"], "title": None, "words": None})
    return out


def watchlist_page(lid: str) -> dict:
    w = next((x for x in lists() if x["id"] == lid), None)
    if not w:
        return K.page("Watchlist", [K.line("This watchlist is gone. Go back to Markets to make another.")])
    nm = names()
    q = quotes(w["symbols"])
    rows = [stock_row(s, q, nm) for s in w["symbols"]]
    live = any(v.get("live") for v in q.values())
    days = sorted({v.get("as_of") for v in q.values() if v.get("as_of")})
    parts = [{"t": "watchmanage", "id": w["id"], "name": w["name"], "symbols": w["symbols"]},
             K.rows(None, rows, plain=True) if rows else K.line("No stocks yet. Search above to add one."),
             K.trust("Prices from Zerodha's feed, read-only." if live else (f"Closes from the nightly quote book ({days[-1]}); Zerodha's live feed is not signed in." if days else
                                                                             "Prices appear once a stock is added."))]
    return K.page(w["name"], parts, ask_q=f"Tell me about my watchlist {w['name']}: " + ", ".join(w["symbols"][:12]) + ". How do they look now?" if w["symbols"] else None)


def stock_page(sym: str, full: bool = True) -> dict:
    sym = re.sub(r"[^A-Z0-9&\-]", "", sym.upper())
    nm = names()
    qb = _quote_book(sym)
    if sym not in nm and not qb:
        raise KeyError(sym)
    name = _tidy(nm.get(sym, sym))
    q = quotes([sym]).get(sym) or {}
    from jarvis.india import surfaces as IS
    when = "Live from Zerodha" if q.get("live") else (f"{IS._dw(q['as_of'])} close" if q.get("as_of") else None)
    hero = K.hero(f"{sym} · NSE", _rs(q.get("last")), change=_pc(q.get("change_pct")), tone=_tone(q.get("change_pct")), since=when)
    f = lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) else "—"            # noqa: E731
    p = lambda v: f"{100 * v:+.1f}%".replace("-", "−") if isinstance(v, (int, float)) else "—"    # noqa: E731
    kv = [K.kvrow("52-week high", f(qb.get("high_52w")), v_sub=p(qb.get("vs_high_52w")) if qb.get("vs_high_52w") is not None else None),
          K.kvrow("52-week low", f(qb.get("low_52w")), v_sub=p(qb.get("vs_low_52w")) if qb.get("vs_low_52w") is not None else None),
          K.kvrow("20-day average", f(qb.get("sma20"))), K.kvrow("50-day average", f(qb.get("sma50"))), K.kvrow("200-day average", f(qb.get("sma200"))),
          K.kvrow("RSI, 14 days", f"{qb['rsi14']:.0f}" if isinstance(qb.get("rsi14"), (int, float)) else "—")] if qb else []
    perf = [K.kvrow(lbl, p(qb.get(k))) for lbl, k in (("1 week", "chg_1w"), ("1 month", "chg_1m"), ("3 months", "chg_3m"), ("6 months", "chg_6m"), ("1 year", "chg_1y"))
            if qb.get(k) is not None]
    held = None
    if full:
        try:
            from jarvis.india import surfaces as IS
            held = next((h for h in IS.money(True).get("holdings") or [] if str(h.get("symbol")) == sym), None)
        except Exception:  # noqa: BLE001
            held = None
    ins = [w["name"] for w in lists() if sym in w["symbols"]] if full else []
    parts = [hero, K.pricechart(sym, name),
             K.kv([K.kvrow("Shares", f"{held.get('qty'):,}" if held.get("qty") is not None else "—"), K.kvrow("Value", _rs(held.get("value_inr"))),
                   K.kvrow("On what you paid", f"{held['pnl_pct']:+.1f}%" if isinstance(held.get("pnl_pct"), (int, float)) else "—")], title="In your Zerodha holdings") if held else None,
             {"t": "watchadd", "sym": sym, "in": ins} if full else None,
             K.kv(perf, title="Performance") if perf else None,
             K.kv(kv, title="Levels") if kv else None,
             K.trust("Chart from Zerodha's feed, read-only; levels from the nightly closes. A description, never advice or a rule.")]
    return K.page(name, [x for x in parts if x], bar_kind="back", ask_q=f"Tell me about {name} ({sym}): its trend, its levels and what would change your view.")


def dynamic(name: str):
    """/v3/place/stock:<SYM> and /v3/place/watchlist:<id>: the pages whose name carries what they show."""
    if name.startswith("place/stock:"):
        sym = name.split(":", 1)[1]
        return lambda full=True: stock_page(sym, full)
    if name.startswith("place/watchlist:"):
        lid = name.split(":", 1)[1]
        def f(full: bool = True):
            if not full:
                return {"ready": False, "kind": "place", "name": "watchlist", "words": "Watchlists are Madhav's own."}
            return watchlist_page(lid)
        return f
    if name == "stocklist":
        return lambda full=True: stocklist()
    return None


_TOK: dict = {"at": 0.0, "v": {}}


def token(sym: str) -> int | None:
    """The NSE equity's Kite instrument token, from the day's instruments file (bronze/kite_instruments/NSE_<day>.csv)."""
    if time.time() - _TOK["at"] > 3600:
        import csv
        fs = sorted((views.DATA / "bronze" / "kite_instruments").glob("NSE_*.csv"))
        v = {}
        if fs:
            with fs[-1].open() as fh:
                for r in csv.DictReader(fh):
                    if r.get("segment") == "NSE" and r.get("instrument_type", "EQ") == "EQ":
                        try:
                            v[r["tradingsymbol"]] = int(r["instrument_token"])
                        except (KeyError, ValueError):
                            pass
        _TOK.update(at=time.time(), v=v)
    return _TOK["v"].get(sym)
