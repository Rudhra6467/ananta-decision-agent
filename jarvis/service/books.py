"""Books, as one list (build plan 1.3 and 3.3, Madhav 2026-10-08): every trade the account holds, from every watch, each with a
stamp saying who took it. Madhav: "We can have a stamp for each trade as on to know which one is firing it actually."

Madhav's account: the 15-minute Explorer, the hourly watch, the daily watches (zone touch, the short dip trade), Ananta's own
picks, the trend portfolios (10 coins and the 30-coin tier) and his manual trades (stamped with his initials).
A visitor's account: their own practice book only (their manual trades, and the ones they confirmed on Ananta's cards).
Random comparison trades are evidence, not holdings: they are counted, never listed.
"""
from __future__ import annotations

import json
from typing import Any

DAILY = {"ZONE_TOUCH": "Daily · zone touch", "H07": "Daily · short dip", "H07-T30": "30-coin tier · short dip"}
RANDOM_PREFIX = ("RANDOM", "JARVIS_RANDOM")


def initials(name: str | None) -> str:
    parts = [p for p in (name or "").replace("-", " ").split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return (parts[0][:2] if parts else "ME").upper()


def _stamp(who: str, label: str, source: str) -> dict:
    return {"who": who, "label": label, "source": source}


def _manual(j, name: str) -> tuple[list[dict], list[dict], dict]:
    from jarvis.service.manual import Manual

    m = Manual(j.db, j.now)
    st = m.state(j.prices())
    fills = m.fills(200)
    via = {}
    for f in fills:                                       # the last buy of each coin: placed by them, or confirmed on Ananta's card
        if f["side"] == "BUY" and f["coin"] not in via:
            via[f["coin"]] = f.get("trigger")
    me = initials(name)
    out = []
    for p in st["positions"]:
        card = via.get(p["coin"]) == "owner"
        out.append({"id": f"manual:{p['coin']}", "coin": p["coin"], "book": "manual",
                    "stamp": _stamp("you", f"{me} · confirmed Ananta's idea" if card else me, "manual"),
                    "entry": round(p["cost"] / p["units"], 8) if p.get("units") else None, "cost": p["cost"], "value": p["value"],
                    "pnl_usd": p["pnl"], "pnl_pct": round(100 * p["pnl"] / p["cost"], 2) if p.get("cost") and p.get("pnl") is not None else None,
                    "stop": p["stop"], "target": p["target"], "link": None})
    closed = [{"t": f["t"], "coin": f["coin"], "stamp": _stamp("you", me, "manual"), "what": f"Sold {f['coin']}", "usd": f["usd"],
               "net_usd": None, "why": f.get("trigger")} for f in fills if f["side"] == "SELL"][:20]
    return out, closed, {"name": "Your trades" if name else "Manual book", "value": st["equity"], "start": st["start"]}


def _research(j) -> tuple[list[dict], list[dict], list[dict], int]:
    from jarvis.service import views

    px = j.prices()
    trades, closed, books = [], [], []
    t = views.trades_list(j)
    books.append({"name": "15-minute Explorer", "value": t["value"], "start": t["start"]})
    for x in t["open"]:
        trades.append({"id": x["id"], "coin": x["coin"], "book": "explorer",
                       "stamp": _stamp("ananta", f"15-minute · {x.get('setup_name')}", "explorer"),
                       "entry": x.get("entry"), "now": x.get("price"), "pnl_usd": x.get("pnl_usd"), "since": x.get("since"),
                       "status": x.get("status"), "link": f"/trade/{x['id']}"})
    for x in t["closed"][:20]:
        closed.append({"id": x["id"], "coin": x["coin"], "stamp": _stamp("ananta", f"15-minute · {x.get('setup_name')}", "explorer"),
                       "net_usd": x.get("net_usd"), "why": x.get("exit"), "time": x.get("time"), "link": f"/trade/{x['id']}"})
    randoms = 0
    for tid, watch, coin, entry, stop, det, net, status, exit_t, why in j.db.execute(
            "SELECT id, watch, coin, entry, stop, detail, net_usd, status, exit_t, exit_why FROM evidence_trades "
            "WHERE status IN ('OPEN', 'CLOSED') ORDER BY coalesce(exit_t, entry_t) DESC"):
        if watch.startswith(RANDOM_PREFIX):
            randoms += status == "OPEN"
            continue
        label = "Ananta's own pick" if watch == "JARVIS" else DAILY.get(watch, f"Daily · {watch.lower().replace('_', ' ')}")
        src = "jarvis" if watch == "JARVIS" else "daily"
        if status == "OPEN":
            d = json.loads(det or "{}")
            now = px.get(coin)
            pnl_pct = round(100 * (now / entry - 1), 2) if now and entry else None
            trades.append({"id": tid, "coin": coin, "book": src, "stamp": _stamp("ananta", label, src), "entry": entry, "now": now,
                           "stop": stop, "target": d.get("target"), "pnl_pct": pnl_pct,
                           "pnl_usd": round(pnl_pct, 2) if pnl_pct is not None else None,        # $100 trades: % = dollars
                           "link": f"/jtrade/{tid}" if watch == "JARVIS" else None})
        elif len(closed) < 40:
            closed.append({"id": tid, "coin": coin, "stamp": _stamp("ananta", label, src), "net_usd": net, "why": why, "t": exit_t,
                           "link": f"/jtrade/{tid}" if watch == "JARVIS" else None})
    try:
        h = views.holdings(j)
        books.append({"name": "Trend portfolio", "value": h["value"], "start": h["start"]})
        for x in h["holdings"]:
            trades.append({"id": f"t3:{x['coin']}", "coin": x["coin"], "book": "t3", "stamp": _stamp("ananta", "Trend portfolio", "t3"),
                           "value": x.get("value"), "pnl_usd": x.get("pnl"), "pnl_pct": x.get("pnl_pct"), "link": f"/coin/{x['coin']}"})
    except Exception:  # noqa: BLE001
        pass
    try:
        from jarvis.service import tier30

        s = tier30.status(j)
        m = s["t3"]["books"]["MAIN"]
        books.append({"name": "30-coin trend book", "value": m.get("equity"), "start": 2000.0})
        for c, v in (m.get("holdings") or {}).items():
            val = v if isinstance(v, (int, float)) else (v or {}).get("value")
            trades.append({"id": f"t30:{c}", "coin": c, "book": "t30", "stamp": _stamp("ananta", "30-coin trend book", "t30"), "value": val})
    except Exception:  # noqa: BLE001
        pass
    try:
        hb = [x for x in views._jsonl(j.dir / "watch_heartbeat.jsonl", 5) if x.get("ok")]
        bk = (hb[-1].get("book") or {}) if hb else {}
        if bk:
            books.append({"name": "Hourly watch", "value": round(bk.get("cash", 0) + sum(float(p.get("value") or 0) for p in bk.get("positions") or []), 2),
                          "start": 1000.0})
        for p in bk.get("positions") or bk.get("open") or []:
            trades.append({"id": f"hourly:{p.get('coin')}", "coin": p.get("coin"), "book": "hourly",
                           "stamp": _stamp("ananta", f"Hourly · {p.get('strategy', 'Hunter')}", "hourly"), "entry": p.get("entry"),
                           "pnl_usd": p.get("pnl")})
    except Exception:  # noqa: BLE001
        pass
    return trades, closed, books, randoms


def view(j, name: str, owner: bool) -> dict[str, Any]:
    mine, mine_closed, mine_book = _manual(j, name)
    trades, closed, books, randoms = (_research(j) if owner else ([], [], [], 0))
    trades = trades + mine
    closed = closed + mine_closed
    books = books + [mine_book]
    stamps: dict[str, int] = {}
    for t in trades:
        stamps[t["stamp"]["label"].split(" · ")[0]] = stamps.get(t["stamp"]["label"].split(" · ")[0], 0) + 1
    open_pnl = round(sum(t["pnl_usd"] for t in trades if isinstance(t.get("pnl_usd"), (int, float))), 2)
    closed_pnl = round(sum(c["net_usd"] for c in closed if isinstance(c.get("net_usd"), (int, float))), 2)
    value = round(sum(b["value"] or 0 for b in books), 2)
    start = round(sum(b["start"] or 0 for b in books), 2)
    return {"summary": {"value": value, "start": start, "open_pnl": open_pnl, "closed_pnl_recent": closed_pnl, "open_count": len(trades)},
            "trades": trades, "closed": closed[:40], "books": books, "stamps": stamps, "random_open": randoms,
            "initials": initials(name),
            "read": "Every trade held, from every watch; the stamp says who took it. Random comparison trades are evidence and are "
                    "not listed." if owner else "Your own practice trades."}


def story(j, tid: str, name: str, owner: bool) -> dict[str, Any]:
    """One trade's full story (plan 3.3b): who took it and why, the start, its stop and target, the highest and lowest prices
    since it opened, how it ended, and its decision card. Works for every stamp; a visitor can only open their own trades."""
    from datetime import datetime

    from jarvis.service import views

    v = view(j, name, owner)
    t = next((x for x in v["trades"] if str(x["id"]) == tid), None)
    closed = t is None
    if t is None:
        t = next((x for x in v["closed"] if str(x.get("id")) == tid), None)
    if t is None:
        raise ValueError("That trade is not in this account's books.")
    out: dict[str, Any] = {"id": tid, "coin": t["coin"], "stamp": t["stamp"], "open": not closed, "entry": t.get("entry"), "now": t.get("now"),
                           "stop": t.get("stop"), "target": t.get("target"), "result_usd": t.get("net_usd") if closed else t.get("pnl_usd"),
                           "result_pct": t.get("pnl_pct"), "reasons": [], "exits": []}
    entry_t = exit_t = None
    row = j.db.execute("SELECT entry_t, entry, stop, exit_t, exit, net_usd, why, exit_why, regime, detail FROM evidence_trades WHERE id = ?",
                       (tid,)).fetchone() if owner else None
    if row:
        entry_t, out["entry"], out["stop"], exit_t, ex, net, why, exit_why, regime, det = row
        d = json.loads(det or "{}")
        out["target"] = out["target"] or d.get("target")
        if why:
            out["reasons"].append(why[:1].upper() + why[1:] + ".")
        if regime:
            out["reasons"].append("The market rule was open (buying allowed)." if regime == "ALLOWED" else "The market rule was careful (risk-off).")
        if d.get("zone"):
            out["reasons"].append(f"The zone it bought into: {d['zone'][0]:,.6g} to {d['zone'][1]:,.6g}.")
        if exit_t:
            out["exits"].append({"t": exit_t, "price": ex, "why": exit_why, "usd": net})
    elif t["stamp"]["source"] == "manual":
        from jarvis.service.manual import Manual

        fills = [f for f in Manual(j.db, j.now).fills(200) if f["coin"] == t["coin"]]
        buys = [f for f in fills if f["side"] == "BUY"]
        if buys:
            entry_t = buys[-1]["t"]
            if buys[0].get("reason"):
                out["reasons"].append(f"“{buys[0]['reason']}”")
        out["reasons"].append("Placed by you. Ananta watches it and warns you; it never closes it without your yes.")
        out["exits"] = [{"t": f["t"], "price": f["px"], "why": "sold by you", "usd": f["usd"]} for f in fills if f["side"] == "SELL"][:5]
    else:
        out["reasons"].append(t.get("why") or t["stamp"]["label"])
    out["entry_t"] = entry_t
    out["entry_when"] = datetime.fromtimestamp(entry_t).strftime("%b %d, %-I:%M %p") if entry_t else None
    try:                                                  # the highest and lowest price since it opened (hourly bars)
        c = [x for x in views.chart(j, t["coin"], "1h")["candles"] if entry_t and x["t"] >= entry_t - 3600 and (not exit_t or x["t"] <= exit_t)]
        if c:
            out["peak"], out["low"] = max(x["h"] for x in c), min(x["l"] for x in c)
            if not closed and out.get("now"):                # the live price can be past the last finished hour
                out["peak"], out["low"] = max(out["peak"], out["now"]), min(out["low"], out["now"])
            out["candles"] = c[-120:]
    except Exception:  # noqa: BLE001
        pass
    who = "you" if t["stamp"]["who"] == "you" else "Ananta"
    out["card"] = {"found": f"{t['coin']}: {t['stamp']['label']}", "why": " ".join(out["reasons"][:2]) or None,
                   "wrong_if": f"a fall below {out['stop']:,.6g}" if out.get("stop") else "no stop was set",
                   "doing": (f"Closed: {out['exits'][0]['why']}." if out["exits"] and out["exits"][0].get("why") else "Closed.") if closed
                   else f"Holding. {'Ananta manages it by its plan.' if who == 'Ananta' else 'Ananta watches it for you.'}"}
    return out
