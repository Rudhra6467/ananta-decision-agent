"""Plain-language views for the app (v0.3): activity feed, day summary, holdings, trade detail,
evidence (collected / forwarded) and the cockpit. Read-only; built from the Agent's own files.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.intelligence import explorer_engine as xe
from src.intelligence import setup_checklist as sc

SETUP = dict(sc.NAMES) | {"RND": "Random entry (baseline)"}
TYPE = {"LONG_TERM": "Long-term (weeks)", "SHORT_TERM": "Short-term (days)", "INTRADAY": "Intraday (hours)"}
TYPE_PLAN = {
    "LONG_TERM": "Held while the trend lasts. Stop below support (about 3 hourly ranges). After +2R the stop trails up. Exit if the daily close falls under its 20-day average. Time limit 60 days.",
    "SHORT_TERM": "Target 2x the risk (or just under resistance). Stop 2 hourly ranges below entry. Exit early if the hourly close falls under its 50-hour average. Time limit 5 days.",
    "INTRADAY": "Quick target 1.5x the risk (at least +1.2%). Tight stop. Exit if the 15-minute trend turns down or nothing happens in 4 hours. Time limit 8 hours.",
}


def exit_text(bell: str | None) -> str:
    if not bell:
        return ""
    b = bell.upper()
    if b.startswith("X1"):
        return "Stop-loss hit"
    if b.startswith("X2"):
        return "Emergency exit (BTC or coin crash)" if "CRASH" in b else "Emergency exit (kill switch)"
    if b.startswith("X3"):
        return {"X3_DAILY_EMA20": "Warning bell: daily close under the 20-day average", "X3_1H_EMA50": "Warning bell: hourly close under the 50-hour average",
                "X3_S4_30M": "Warning bell: 30-minute trend turned down", "X3_S4_15M": "Warning bell: 15-minute trend turned down",
                "X3_NO_PROGRESS": "Warning bell: no progress in 4 hours"}.get(b, "Warning bell exit")
    if b.startswith("X4"):
        return "Trailing stop (profit protected)" if "TRAIL" in b else "Target reached"
    if b.startswith("X5"):
        return "Time limit reached"
    return bell


def _local(t: float) -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.fromtimestamp(t, ZoneInfo("America/Toronto")).strftime("%b %d, %I:%M %p").replace(" 0", " ")
    except Exception:  # noqa: BLE001
        return datetime.fromtimestamp(t, timezone.utc).strftime("%b %d %H:%M UTC")


def _px(x: float | None) -> str:
    if x is None:
        return "-"
    return f"${x:,.2f}" if x >= 10 else f"${x:.4f}" if x >= 0.1 else f"${x:.5f}"


def _jsonl(p: Path, n: int = 400) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines()[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def _ts(iso: str | None) -> float:
    try:
        return datetime.fromisoformat(iso).timestamp() if iso else 0.0
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
def feed(j, hours: float = 72, limit: int = 60) -> list[dict]:
    """What happened, newest first, one sentence each. kind: buy | sell | watch | portfolio | warn | info."""
    now = j.now()
    since = int(now - hours * 3600)
    items: list[dict] = []
    ex = j._explorer()
    if ex:
        for (js,) in ex.store.book.execute("SELECT json FROM events WHERE t >= ? AND kind IN ('FILLED','CLOSED','ORDER') ORDER BY seq", (since,)):
            e = json.loads(js)
            if e.get("catch_up") and e["kind"] == "ORDER":
                continue
            name = SETUP.get(e.get("setup"), e.get("setup"))
            if e["kind"] == "FILLED":
                items.append({"t": e["t"], "kind": "buy", "coin": e["coin"], "trade_id": e.get("id"),
                              "title": f"Bought {e['coin']} (paper, $100)",
                              "body": f"{name}. {TYPE.get(e.get('type'), '')} trade at {_px(e.get('entry'))}, stop {_px(e.get('stop'))}."})
            elif e["kind"] == "CLOSED":
                net = e.get("net_usd") or 0
                items.append({"t": e["t"], "kind": "sell", "coin": e["coin"], "trade_id": e.get("id"), "good": net > 0,
                              "title": f"Sold {e['coin']}: {'+' if net >= 0 else '-'}${abs(net):.2f}",
                              "body": f"{exit_text(e.get('bell'))}. Setup: {name}."})
            elif e["kind"] == "ORDER" and not e.get("shadow"):
                items.append({"t": e["t"], "kind": "watch", "coin": e["coin"],
                              "title": f"Waiting to buy {e['coin']} at {_px(e.get('limit'))}",
                              "body": f"{name}. A limit order for 1-2 hours; it only fills if the price dips to it."})
    L = j._layer()
    for (js,) in L.con.execute("SELECT json FROM decisions WHERE day_t >= ? ORDER BY day_t", (since - 86400,)):
        d = json.loads(js)
        hold = [c for c, r in (d.get("ratings") or {}).items() if r.get("hold")]
        t = _ts(d.get("day", "").replace(" ", "T") + ":00+00:00") if d.get("day") else 0
        if t >= since:
            items.append({"t": t, "kind": "portfolio", "title": f"Portfolio check: hold {len(hold)} of {len(d.get('ratings') or {})} coins",
                          "body": ("BTC is above its 50-day average, so the market gate is open." if d.get("btc_gate") else
                                   "BTC is below its 50-day average: the portfolio moves to cash.")})
    fills = [json.loads(js) for (js,) in L.con.execute("SELECT json FROM fills WHERE t >= ? ORDER BY seq", (since,))]
    by_t: dict[tuple, list] = {}
    for f in fills:
        if f["book"] == "MAIN":
            by_t.setdefault((f["t"] // 3600,), []).append(f)
    for _, fs in by_t.items():
        buys = [f["coin"] for f in fs if f["side"] == "BUY"]
        sells = [f["coin"] for f in fs if f["side"] == "SELL"]
        parts = ([f"bought {', '.join(buys)}"] if buys else []) + ([f"sold {', '.join(sells)}"] if sells else [])
        items.append({"t": fs[0]["t"], "kind": "portfolio", "title": "Portfolio rebalanced (paper)",
                      "body": "; ".join(parts).capitalize() + f". ${sum(f['usd'] for f in fs):,.0f} moved, costs ${sum(f['cost'] for f in fs):.2f}."})
    hb = [h for h in _jsonl(j.dir / "watch_heartbeat.jsonl", 200) if _ts(h.get("ts")) >= since]
    for h in hb:
        t = _ts(h.get("ts"))
        if not h.get("ok"):
            items.append({"t": t, "kind": "warn", "title": "Hourly watch could not reach the backend", "body": str(h.get("error", ""))[:160]})
            continue
        for a in h.get("takes") or []:
            items.append({"t": t, "kind": "buy", "coin": a, "title": f"Hourly watch: paper buy {a}", "body": "Strategy book (SD6)."})
    for a in _jsonl(j.dir / "watch_alerts.jsonl", 300):
        t = _ts(a.get("ts"))
        if t < since or a.get("level") == "PHONE":
            continue
        title, body = a.get("title", ""), a.get("body", "")
        if "paper exit" in title and body.startswith("sd6."):
            p = body.split()
            coin = p[0].split(".")[1] if "." in p[0] else ""
            pnl = float(p[-1]) if p and p[-1].replace(".", "").replace("-", "").isdigit() else None
            why = p[1].split("/")[-1].replace("_", " ").lower() if len(p) > 1 else ""
            items.append({"t": t, "kind": "sell", "coin": coin, "good": (pnl or 0) > 0,
                          "title": f"Hourly watch sold {coin}" + (f": {'+' if pnl >= 0 else '-'}${abs(pnl):.2f}" if pnl is not None else ""),
                          "body": f"Strategy book (SD6). Reason: {why}."})
        elif a.get("level") in ("WARN", "ERROR"):
            items.append({"t": t, "kind": "warn", "title": title.replace("Ananta", "").strip(": "), "body": body[:200]})
    for (t, who, action, detail, result) in j.db.execute("SELECT t, who, action, detail, result FROM audit WHERE t >= ? AND action NOT IN ('login') ORDER BY seq", (since,)):
        label = {"portfolio.mode": f"Portfolio mode set to {detail}", "safety.kill_switch": f"Kill switch {detail}",
                 "portfolio.approve": "You approved portfolio changes", "portfolio.reject": "You rejected portfolio changes"}.get(action, action)
        items.append({"t": t, "kind": "info", "title": label, "body": "From the Jarvis app."})
    items.sort(key=lambda x: x["t"], reverse=True)
    for it in items:
        it["time"] = _local(it["t"])
    return items[:limit]


def _pl():
    from src.intelligence import portfolio_layer as pl

    return pl


def _starts() -> float:
    from src.intelligence import explorer_live as xl

    return float(xl.START_CAPITAL + _pl().START)


def day_summary(j) -> dict:
    """Today in four numbers and one sentence."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/Toronto")
    now = j.now()
    start = datetime.fromtimestamp(now, tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    ex = j._explorer()
    px = ex.prices() if ex else {}
    xs = ex.status() if ex else None
    ps = j._layer().status(px)
    snap = j.db.execute("SELECT explorer, main FROM snapshots WHERE t >= ? ORDER BY t LIMIT 1", (int(start),)).fetchone()
    opened = closed = 0
    if ex:
        opened = ex.store.book.execute("SELECT count(*) FROM events WHERE kind='FILLED' AND t >= ?", (int(start),)).fetchone()[0]
        closed = ex.store.book.execute("SELECT count(*) FROM events WHERE kind='CLOSED' AND t >= ?", (int(start),)).fetchone()[0]
    looks = sum(1 for h in _jsonl(j.dir / "watch_heartbeat.jsonl", 100) if _ts(h.get("ts")) >= start and h.get("ok"))
    pend = len(ps["pending"])
    main_eq = ps["books"]["MAIN"]["equity"]
    total = (xs["equity"] if xs else 0) + main_eq
    start_total = (snap[0] + snap[1]) if snap else None
    sentence = (f"{pend} portfolio change(s) wait for your approval." if pend else
                "Nothing needs you. Paper only: no real money is at risk.")
    return {
        "date": datetime.fromtimestamp(now, tz).strftime("%A, %b %d"),
        "paper_value": round(total, 2), "start_value": _starts(),
        "today_change": round(total - start_total, 2) if start_total else None,
        "explorer": {"value": xs["equity"] if xs else None, "open": len(xs["open"]) if xs else 0, "opened_today": opened, "closed_today": closed},
        "portfolio": {"value": main_eq, "return_pct": ps["books"]["MAIN"]["return_pct"], "mode": ps["mode"], "holding": len(ps["books"]["MAIN"]["holdings"]), "pending": pend},
        "hourly_watch": {"looks_today": looks},
        "sentence": sentence,
    }


# ---------------------------------------------------------------------------
def holdings(j) -> dict:
    """Portfolio (MAIN book) like a brokerage page: value, cost, P&L, weight, rating."""
    ex = j._explorer()
    px = ex.prices() if ex else {}
    L = j._layer()
    ps = L.status(px)
    last = ps.get("last_decision") or {}
    ratings = last.get("ratings") or {}
    cost: dict[str, float] = {}
    units: dict[str, float] = {}
    for (js,) in L.con.execute("SELECT json FROM fills ORDER BY seq"):
        f = json.loads(js)
        if f["book"] != "MAIN":
            continue
        c, u = f["coin"], f["usd"] / f["px"]
        if f["side"] == "BUY":
            cost[c] = cost.get(c, 0) + f["usd"] + f["cost"]
            units[c] = units.get(c, 0) + u
        else:
            if units.get(c):
                frac = min(1.0, u / units[c])
                cost[c] -= cost[c] * frac
                units[c] -= units[c] * frac
    book = ps["books"]["MAIN"]
    eq = book["equity"]
    rows = []
    for c, val in sorted(book["holdings"].items(), key=lambda kv: -kv[1]):
        eng = ex.st["engines"].get(c) if ex else None
        d1 = list(eng.tf["1d"].bars) if eng else []
        day_ch = (px[c] / d1[-1][4] - 1) if (d1 and c in px) else None
        r = ratings.get(c, {})
        cb = cost.get(c)
        rows.append({"coin": c, "value": round(val, 2), "price": px.get(c), "cost": round(cb, 2) if cb else None,
                     "pnl": round(val - cb, 2) if cb else None, "pnl_pct": round(100 * (val / cb - 1), 2) if cb else None,
                     "weight_pct": round(100 * val / eq, 1) if eq else None, "day_pct": round(100 * day_ch, 2) if day_ch is not None else None,
                     "rating": r.get("rating"), "why": _rating_plain(r)})
    watch = [{"coin": c, "rating": r.get("rating"), "why": _rating_plain(r)} for c, r in ratings.items() if c not in book["holdings"]]
    invested = sum(r["value"] for r in rows)
    sh = ps["books"]["SHADOW"]
    return {"mode": ps["mode"], "value": eq, "start": _pl().START, "return_pct": book["return_pct"], "cash": book["cash"],
            "invested": round(invested, 2), "costs_paid": book["costs"], "holdings": rows, "not_held": watch,
            "pending": ps["pending"], "decided": last.get("day"), "btc_gate": last.get("btc_gate"),
            "shadow": {"value": sh["equity"], "return_pct": sh["return_pct"]},
            "rule_plain": "Hold a coin while its daily close is above its 20-day and 50-day averages and BTC is above its 50-day average. Equal weights, checked every day, rebalanced weekly."}


def _rating_plain(r: dict) -> str:
    rt = r.get("rating")
    base = {"STRONG": "Strong uptrend and leading the group.", "OK": "In an uptrend, middle of the group.",
            "WEAK": "Still in an uptrend but lagging; first to go if the trend breaks.", "OUT": "Below its averages: not held."}.get(rt, "")
    return base


def trade_detail(j, trade_id: str) -> dict:
    ex = j._explorer()
    if not ex:
        raise ValueError("explorer not running")
    coin = trade_id.split("-")[0]
    eng = ex.st["engines"].get(coin)
    if not eng:
        raise ValueError("unknown trade")
    tr = next((t for t in list(eng.trades) + list(eng.actual_closed) + list(eng.closed) if t.id == trade_id), None)
    if tr is None:
        raise ValueError("trade not found")
    a = tr.actual
    px = eng.tf["5m"].last[4]
    is_open = not a.done
    now_px = px if is_open else a.exit_px
    pnl = xe.net_usd(tr, a) if a.done else xe.NOTIONAL * (px / tr.entry - 1)
    start = tr.entry_t - 12 * 3600
    end = (a.exit_t or j.now()) + (6 * 3600 if a.done else 0)
    bars = [b for b in eng.tf["15m"].bars if start <= b[0] <= end]
    if len(bars) < 20:
        bars = [b for b in eng.tf["1h"].bars if start - 24 * 3600 <= b[0] <= end]
    order_tags = tr.tags or {}
    conds = []
    s1 = order_tags.get("S1")
    if s1:
        conds.append(f"1h trend: {'up' if s1 == 'BULL' else 'down' if s1 == 'BEAR' else 'no clear trend'}")
    if order_tags.get("trend_4h"):
        conds.append(f"4h trend: {order_tags['trend_4h'].lower()}")
    if order_tags.get("daily_above_ema50") is not None:
        conds.append("Daily close above the 50-day average" if order_tags["daily_above_ema50"] else "Daily close below the 50-day average")
    if order_tags.get("rsi1h") is not None:
        conds.append(f"1h RSI {order_tags['rsi1h']:.0f}")
    if order_tags.get("btc_S1"):
        conds.append(f"BTC 1h trend: {'up' if order_tags['btc_S1'] == 'BULL' else 'down' if order_tags['btc_S1'] == 'BEAR' else 'no clear trend'}")
    to_stop = (a.stop / now_px - 1) if (is_open and a.stop) else None
    to_target = (a.target / now_px - 1) if (is_open and a.target) else None
    timeline = [{"time": _local(tr.entry_t), "text": f"Bought at {_px(tr.entry)} ({'limit order filled' if tr.entry_kind == 'LIMIT' else 'market'})"}]
    if a.done:
        timeline.append({"time": _local(a.exit_t), "text": f"Sold at {_px(a.exit_px)}: {exit_text(a.exit_bell)}"})
    else:
        timeline.append({"time": "now", "text": f"Price {_px(px)}"})
    shadows = {k: {"net_usd": round(xe.net_usd(tr, v), 2) if v.done else None, "exit": exit_text(v.exit_bell) if v.done else "still open"}
               for k, v in tr.variants.items() if k != "ACTUAL"}
    return {
        "id": tr.id, "coin": coin, "open": is_open, "invested": xe.NOTIONAL,
        "setup": tr.setup, "setup_name": SETUP.get(tr.setup, tr.setup), "type": tr.typ, "type_name": TYPE.get(tr.typ),
        "entry": tr.entry, "entry_time": _local(tr.entry_t), "price": now_px,
        "pnl_usd": round(pnl, 2), "pnl_pct": round(pnl, 2),   # $100 trades: dollars == percent
        "stop": a.stop, "target": a.target, "trailing": a.trail, "to_stop_pct": None if to_stop is None else round(100 * to_stop, 2),
        "to_target_pct": None if to_target is None else round(100 * to_target, 2),
        "time_limit": _local(tr.entry_t + xe.TIME_CAP[a.typ]) if is_open else None,
        "exit": exit_text(a.exit_bell) if a.done else None, "exit_time": _local(a.exit_t) if a.done else None,
        "why_bought": f"{SETUP.get(tr.setup, tr.setup)}: the 15-minute check found every condition of this setup met.",
        "conditions_at_entry": conds, "plan": TYPE_PLAN.get(tr.typ), "timeline": timeline,
        "what_if": shadows,
        "chart": {"tf": "15m" if len(bars) >= 20 else "1h", "points": [{"t": b[0], "c": b[4]} for b in bars],
                  "entry_t": tr.entry_t, "exit_t": a.exit_t},
    }


# ---------------------------------------------------------------------------
def _ledger(j) -> dict:
    for base in (j.dir, Path(__file__).resolve().parents[2]):
        p = base / "docs" / "repair_shop" / "ledger.json"
        if p.exists():
            return json.loads(p.read_text())
    return {"reviews": [], "queue": [], "in_use": [], "safety_changes": []}


def evidence_collected(j) -> dict:
    ex = j._explorer()
    led = _ledger(j)
    counts: dict[str, Any] = {}
    by_setup: dict[str, dict] = {}
    first_t = None
    if ex:
        B = ex.store.book
        first_t = ex.st.get("trade_from_t")
        for kind, n in B.execute("SELECT kind, count(*) FROM events GROUP BY kind"):
            counts[kind] = n
        for (js,) in B.execute("SELECT json FROM events WHERE kind IN ('ORDER','FILLED','CLOSED','SIGHTING')"):
            e = json.loads(js)
            s = e.get("setup") or "?"
            d = by_setup.setdefault(s, {"setup": s, "name": SETUP.get(s, s), "seen": 0, "orders": 0, "shadow_orders": 0, "bought": 0, "closed": 0, "net_usd": 0.0})
            if e["kind"] == "SIGHTING":
                d["seen"] += 1
            elif e["kind"] == "ORDER":
                d["shadow_orders" if e.get("shadow") else "orders"] += 1
            elif e["kind"] == "FILLED":
                d["bought"] += 1
            elif e["kind"] == "CLOSED":
                d["closed"] += 1
                d["net_usd"] = round(d["net_usd"] + (e.get("net_usd") or 0), 2)
    shadows: dict[str, int] = {}
    if ex:
        for (js,) in ex.store.book.execute("SELECT json FROM events WHERE kind='ORDER' AND json LIKE '%\"shadow\": \"%'"):
            e = json.loads(js)
            shadows[e.get("shadow")] = shadows.get(e.get("shadow"), 0) + 1
    hb = _jsonl(j.dir / "watch_heartbeat.jsonl", 5000)
    looks = sum(1 for h in hb if h.get("ok"))
    hunter = _hourly_strategies(j)
    rec = j.dir / "explorer_reconstruct.json"
    recon = json.loads(rec.read_text()) if rec.exists() else None
    days = round((j.now() - first_t) / 86400, 1) if first_t else 0
    closed_n = counts.get("CLOSED", 0)
    tracker = [
        {"key": "days", "label": "Days of live paper evidence", "value": days,
         "explain": "How long the 15-minute Explorer has been trading on paper. History replays cover 7 years; live days check that the live system behaves like the replay."},
        {"key": "looks_15m", "label": "15-minute checks", "value": int(days * 96 * 10),
         "explain": "Every 15 minutes the Explorer checks 10 coins for its setups (about 960 checks a day)."},
        {"key": "sightings", "label": "Setups seen", "value": counts.get("SIGHTING", 0),
         "explain": "Every time any setup's conditions were all met (traded or not). Each sighting is matched to its history in the intraday atlas: how often it reached +3% before -1.5%."},
        {"key": "orders", "label": "Buy orders placed", "value": sum(d["orders"] for d in by_setup.values()),
         "explain": "Real paper limit orders. Most expire unfilled because the price must dip to the limit."},
        {"key": "bought", "label": "Paper buys", "value": counts.get("FILLED", 0),
         "explain": "Orders that filled. Each is a $100 paper trade with its own stop, target and warning bells."},
        {"key": "closed", "label": "Closed trades", "value": closed_n, "goal": 30,
         "explain": "Finished trades. The first live-vs-replay check (Q1) needs 30."},
        {"key": "shadows", "label": "Shadow trades", "value": sum(shadows.values()), "parts": shadows,
         "explain": "Trades we did not take but track anyway: random entries (the baseline to beat), setups with no trade type, orders blocked by a full slot or the caps. They show what we would have got."},
        {"key": "hourly_looks", "label": "Hourly watch looks", "value": looks,
         "explain": "The hourly watch runs Hunter (reversals) and Squeeze (compression breakouts) on 10 coins. Hunter is rare: about 2-8 times per coin per year."},
        {"key": "hunter", "label": "Hunter near-misses (last 24h)", "value": hunter.get("hunter", {}).get("detected_24h", 0),
         "parts": hunter.get("hunter", {}).get("top_reasons", {}),
         "explain": "Hours where Hunter saw a possible reversal but a condition failed. The reasons show what was missing."},
        {"key": "reconstruction", "label": "Nightly rebuild matches live", "value": ("yes" if recon and recon.get("match") else "no" if recon else "not yet"),
         "detail": recon, "explain": "Each night the day is rebuilt from raw candles. If the rebuild and the live log agree, the evidence can be trusted."},
    ]
    forwarded = [{"id": r["id"], "title": r["title"], "date": r["date"], "verdict": r["verdict"], "why": r["forwarded_because"],
                  "question": r["question"], "result": r["result"], "changed": r["changed"]} for r in led["reviews"]]
    shop = {"running": [r for r in led["reviews"] if r["status"] == "RUNNING"],
            "waiting": led["queue"], "done": [{"id": r["id"], "title": r["title"], "verdict": r["verdict"], "date": r["date"]} for r in led["reviews"] if r["status"] == "DONE"],
            "summary": f"{sum(1 for r in led['reviews'] if r['status'] == 'DONE')} reviews done ({sum(1 for r in led['reviews'] if r['verdict'] == 'PASS')} passed). "
                       f"{len(led['queue'])} questions wait for more live evidence."}
    return {"collected": sorted(by_setup.values(), key=lambda d: d["setup"]), "tracker": tracker, "forwarded": forwarded, "shop": shop}


def _hourly_strategies(j, hours: float = 24) -> dict:
    runs = sorted((j.dir / "watch_runs").glob("*.json"), key=lambda p: p.stat().st_mtime)
    cut = j.now() - hours * 3600
    out: dict[str, dict] = {}
    for p in runs[-48:]:
        if p.stat().st_mtime < cut:
            continue
        try:
            env = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        for r in env.get("results") or []:
            coin = (r.get("symbol") or "").split("/")[0]
            sig = r.get("strategy_signals") or {}
            for o in r.get("strategy_observations") or []:
                s = out.setdefault(o.get("strategy"), {"looks": 0, "setups": 0, "detected_24h": 0, "top_reasons": {}, "latest": {}})
                s["looks"] += 1
                s["setups"] += bool(o.get("setup_detected"))
                if (sig.get(o.get("strategy")) or {}).get("detected"):
                    s["detected_24h"] += 1
                for c in o.get("reason_codes") or []:
                    s["top_reasons"][c] = s["top_reasons"].get(c, 0) + 1
                s["latest"][coin] = {"decision": o.get("decision"), "reasons": o.get("reason_codes") or [o.get("skip_reason")],
                                     "regime": o.get("regime"), "evidence": (sig.get(o.get("strategy")) or {}).get("evidence")}
    for s in out.values():
        s["top_reasons"] = dict(sorted(s["top_reasons"].items(), key=lambda kv: -kv[1])[:6])
    return out


def evidence_forwarded(j) -> dict:
    """Repairs that passed and now run in paper (tracked against their expectation), plus safety changes."""
    led = _ledger(j)
    ex = j._explorer()
    px = ex.prices() if ex else {}
    ps = j._layer().status(px)
    first = j._layer().con.execute("SELECT day_t, json FROM decisions ORDER BY day_t LIMIT 1").fetchone()
    bh = None
    if first and ex:
        d0 = json.loads(first[1])
        closes = {c: r.get("close") for c, r in (d0.get("ratings") or {}).items() if r.get("close")}
        rets = [px[c] / closes[c] - 1 for c in closes if c in px]
        bh = round(100 * sum(rets) / len(rets), 2) if rets else None
    pts = j.db.execute("SELECT t, main, shadow FROM snapshots ORDER BY t").fetchall()
    items = []
    for it in led.get("in_use", []):
        row = dict(it)
        if it["id"] == "T3":
            row["tracking"] = {"main_return_pct": ps["books"]["MAIN"]["return_pct"], "shadow_return_pct": ps["books"]["SHADOW"]["return_pct"],
                               "buy_hold_return_pct": bh, "trades": ps["books"]["MAIN"]["trades"], "costs_usd": ps["books"]["MAIN"]["costs"],
                               "days": round((j.now() - first[0]) / 86400, 1) if first else 0,
                               "series": [{"t": t, "main": m, "shadow": s} for t, m, s in pts[-400:]]}
            row["verdict_so_far"] = "Too early: the backtest's edge shows over months, not days."
        review = next((r for r in led["reviews"] if r["id"] == it.get("from")), None)
        if review:
            row["review"] = review
        items.append(row)
    return {"in_use": items, "safety_changes": led.get("safety_changes", [])}


def cockpit(j) -> dict:
    s = j.safety()
    ps = j._layer().status({})
    switches = [
        {"key": "kill_switch", "label": "Kill switch", "on": bool(s.get("kill_switch_on")),
         "help": "On = close every paper position and block new entries.", "confirm": True},
        {"key": "portfolio_auto", "label": "Portfolio autopilot", "on": ps["mode"] == "AUTO",
         "help": "On = the portfolio rebalances by itself. Off = it suggests and waits for you.", "confirm": True},
        {"key": "live_trading", "label": "Live trading (real money)", "on": False, "locked": True,
         "help": "Locked: no exchange is connected. Paper only."},
    ]
    systems = [
        {"label": "Hands (backend)", "ok": bool(s.get("hands_reachable"))},
        {"label": "15-minute Explorer", "ok": not s.get("explorer_stale"), "last": s.get("explorer_last_scan")},
        {"label": "Hourly watch", "ok": True, "last": s.get("hourly_watch_last")},
    ]
    return {"switches": switches, "systems": systems, "circuit_breakers": s.get("circuit_breakers"), "recent_actions": s.get("recent_actions")}
