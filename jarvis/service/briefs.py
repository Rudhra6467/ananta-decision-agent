"""Two compact briefs that answer most questions in one model call (the fast path).

Questions come from two places only:
  PORTFOLIO  our books: open / closed trades, the T3 portfolio, my paper trades, what we are watching, what was skipped
  MARKET     the market itself: trend and breadth, the latest 15-minute scan, Hunter / Squeeze, evidence and lessons
route() picks one (or both) from the words of the question, with no model call. The brief goes into the prompt, so the
model answers straight away; lookups stay available only for detail the brief does not hold.
Briefs are cached for 60 seconds (the Explorer only changes every 15 minutes).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from jarvis.service import views

_CACHE: dict[str, tuple[float, dict]] = {}
TTL = 60

PORTFOLIO_WORDS = re.compile(
    r"\b(portfolio|our|we|us|my|mine|trade|trades|position|positions|holding|holdings|hold|book|profit|loss|losing|making money|"
    r"worth|p&l|pnl|closed|open|took|taken|skip|skipped|watch|watching|waiting|attention|change anything|need me|need my|"
    r"alert|alerts|bought|sold|start(ed)? with|up\b|down\b|best|worst)", re.I)
MARKET_WORDS = re.compile(
    r"\b(market|markets|bull|bullish|bear|bearish|scan|scanner|scanning|setup|setups|trend|trending|moving|coins?|"
    r"btc|bitcoin|eth|ethereum|sol|solana|ada|doge|avax|bch|link|ltc|xrp|hunter|squeeze|explorer|strateg\w*|evidence|"
    r"learn\w*|proven|prove|history|histor\w*|condition|conditions|environment|timeframe|stronger|weaker|today|changed|missing)", re.I)


def route(text: str, previous: str | None = None) -> str:
    """'portfolio' | 'market' | 'both'. Short follow-ups ('why?', 'so we wait?') keep the previous route."""
    t = text.strip()
    p, m = bool(PORTFOLIO_WORDS.search(t)), bool(MARKET_WORDS.search(t))
    if len(t.split()) <= 6 and previous and not (p and m):
        if not p and not m:
            return previous
    if p and not m:
        return "portfolio"
    if m and not p:
        return "market"
    if p and m:
        # "how is our bitcoin trade" -> portfolio; "why aren't we taking trades if the market is bullish" -> both
        return "both" if re.search(r"\b(market|scan|setup|bull|bear|trend|why)", t, re.I) else "portfolio"
    return previous or "both"


def _cached(key: str, fn) -> dict:
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    v = fn()
    _CACHE[key] = (time.time(), v)
    return v


def clear() -> None:
    _CACHE.clear()


def _r(x, n=2):
    return None if x is None else round(x, n)


def portfolio_brief(j) -> dict:
    def build() -> dict:
        out: dict[str, Any] = {"as_of_toronto": views._local(j.now())}
        t = views.trades_list(j)
        out["explorer_book"] = {
            "what": "the 15-minute Explorer's own paper trades, $100 each",
            "value": t["value"], "start": t["start"], "open_pnl": t["unrealized"], "closed_pnl": t["realized"],
            "open_trades": [{"id": x["id"], "coin": x["coin"], "setup": x["setup_name"], "type": x["type_name"], "bought": x["entry"],
                             "now": x["price"], "pnl_usd": x["pnl_usd"], "status": x["status"], "since": x["since"]} for x in t["open"]],
            "closed_trades": t["closed"][:8], "closed_count": len(t["closed"]), "waiting_to_fill": t["pending"]}
        h = views.holdings(j)
        out["t3_portfolio"] = {
            "what": "the T3 trend portfolio (holds coins in uptrends, cash in slides)", "mode": h["mode"],
            "value": h["value"], "start": h["start"], "return_pct": h["return_pct"], "cash": h["cash"], "costs_paid": h["costs_paid"],
            "holdings": [{"coin": x["coin"], "value": x["value"], "pnl_pct": x["pnl_pct"], "rating": x["rating"], "weight_pct": x["weight_pct"]} for x in h["holdings"]],
            "not_held": [x["coin"] for x in h["not_held"]], "suggested_changes_waiting": len(h["pending"]),
            "automatic_copy_return_pct": h["shadow"]["return_pct"], "btc_gate_open": h["btc_gate"]}
        try:
            fw = views.evidence_forwarded(j)
            tr = next((x.get("tracking") or {} for x in fw["in_use"] if x["id"] == "T3"), {})
            out["t3_portfolio"]["buy_and_hold_return_pct"] = tr.get("buy_hold_return_pct")
            out["t3_portfolio"]["days"] = tr.get("days")
        except Exception:  # noqa: BLE001
            pass
        try:
            from jarvis.service.manual import Manual

            mb = Manual(j.db, j.now).state(j.prices())
            out["my_paper_book"] = {"what": "orders the owner asked for", "value": mb["equity"], "return_pct": mb["return_pct"],
                                    "positions": [{"coin": p["coin"], "value": p["value"], "pnl": p["pnl"], "stop": p["stop"]} for p in mb["positions"]]}
        except Exception:  # noqa: BLE001
            pass
        hb = [x for x in views._jsonl(j.dir / "watch_heartbeat.jsonl", 30) if x.get("ok")]
        if hb:
            out["hourly_watch_book"] = {"what": "Hunter / Squeeze strategy book (SD6)", **(hb[-1].get("book") or {})}
        m = views.markets(j)
        out["watching"] = {
            "what": "how close each coin is to an Explorer setup (all conditions met = complete)",
            "complete_now": [{"coin": c["coin"], "setup": c["closest"]["name"], "traded": bool(c["open_trades"])}
                             for c in m["coins"] if c.get("closest") and c["closest"]["met"] == c["closest"]["of"]],
            "almost": [{"coin": c["coin"], "setup": c["closest"]["name"], "met": f'{c["closest"]["met"]}/{c["closest"]["of"]}',
                        "missing": c["closest"]["missing"][:1]} for c in m["coins"]
                       if c.get("closest") and c["closest"]["of"] - c["closest"]["met"] == 1],
            "skip_rule": "a complete setup is skipped when that coin already has an open trade of the same type, or no trade type fits"}
        try:
            s = views.day_summary(j)
            mine = (out.get("my_paper_book") or {}).get("value")
            out["all_books"] = {"what": "one line for 'how are we doing' when he does not say which book",
                                "explorer_plus_trend_portfolio_value": s.get("paper_value"), "their_start": s.get("start_value"),
                                "change_usd": round((s.get("paper_value") or 0) - (s.get("start_value") or 0), 2),
                                "today_change_usd": s.get("today_change"), "my_paper_book_value": mine, "my_paper_book_start": 1000.0}
        except Exception:  # noqa: BLE001
            pass
        try:
            out["needs_owner"] = {"cards_waiting": len(__import__("jarvis.service.mandate", fromlist=["Mandate"]).Mandate(j.db, j.now).pending()),
                                  "portfolio_suggestions_waiting": len(h["pending"])}
            from jarvis.service.alerts import Alerts

            out["alerts_active"] = [a["what"] for a in Alerts(j.db, j.now).list(include_done=False)]
        except Exception:  # noqa: BLE001
            pass
        return out
    return _cached("portfolio", build)


def market_brief(j) -> dict:
    def build() -> dict:
        m = views.markets(j)
        coins = []
        for c in m["coins"]:
            cl = c.get("closest") or {}
            coins.append({"coin": c["coin"], "price": c["price"], "day_pct": c["day_pct"], "week_pct": c["week_pct"],
                          "trend_1h": c.get("trend_1h"), "trend_4h": c.get("trend_4h"), "daily": c.get("daily"),
                          "closest_setup": cl.get("name"), "met": f'{cl.get("met")}/{cl.get("of")}' if cl else None,
                          "missing": (cl.get("missing") or [])[:1], "we_hold_trade": bool(c["open_trades"])})
        up_day = sum(1 for c in m["coins"] if (c["day_pct"] or 0) > 0)
        hb = [x for x in views._jsonl(j.dir / "watch_heartbeat.jsonl", 5) if x.get("ok")]
        out: dict[str, Any] = {"as_of_toronto": views._local(j.now()),
                               "regime": {"market": ("ALLOWED: Bitcoin is above its 50-day average, so our tested rule (the Bitcoin 50-day rule) "
                                                     "lets us hold and buy coins in uptrends") if m["btc_gate"] else
                                                    ("RISK-OFF: Bitcoin is below its 50-day average, so our tested rule says stay out / in cash"),
                                          "hourly_by_coin": (hb[-1].get("regimes") if hb else None),
                                          "say": "When asked for status, name the market regime in one phrase from 'market' (this is the one "
                                                 "regime we have tested). hourly_by_coin is the backend's hourly label per coin (e.g. COMPRESSION = "
                                                 "quiet, tight range); use it only as colour."},
                               "breadth": {"up_today": up_day, "uptrend_1h": m["breadth"]["up_1h"], "of": m["breadth"]["of"]},
                               "btc_gate_open": m["btc_gate"], "coins": coins,
                               "scanner": "Explorer checks 10 coins every 15 minutes for 6 setups: E1 pullback in an uptrend, E2 breakout after a quiet period, "
                                          "E3 bounce at support, E4 momentum continuation, E5 squeeze breakout, E6 deep dip (15-minute RSI under 30). "
                                          "A trade needs ALL conditions of one setup. Wide mode (W1) since Oct 3: up to 3 trades per coin per kind."}
        hs = views._hourly_strategies(j, hours=3)
        out["hourly_watch"] = {k: {"setups_found_3h": v["setups"], "main_blockers": list(v["top_reasons_plain"].keys())[:3] if "top_reasons_plain" in v
                                   else [views._reason(r) for r in list(v["top_reasons"])[:3]]} for k, v in hs.items() if k in ("hunter", "squeeze")}
        ev = views.evidence_collected(j)
        tk = {x["key"]: x["value"] for x in ev["tracker"]}
        out["evidence"] = {"live_days": tk.get("days"), "paper_buys": tk.get("bought"), "closed_trades": tk.get("closed"),
                           "closed_needed_for_first_check": 30, "setups_seen": tk.get("sightings"), "replay_matches_live": tk.get("reconstruction"),
                           "repair_shop": ev["shop"]["summary"],
                           "lessons": [f'{r["title"]}: {r["verdict"]}. {r["result"][:220]}' for r in ev["forwarded"]]}
        return out
    return _cached("market", build)


def briefs_for(j, route_name: str, guest: bool = False) -> dict:
    """guest: a visitor's question (build plan 1.2a). Their PORTFOLIO_BRIEF is their own account; the market brief is shared but
    says what THEY hold, never which coins Madhav's Explorer holds. The cache is only for Madhav's own brief."""
    out = {}
    if guest:
        from jarvis.service import account

        if route_name in ("portfolio", "both"):
            out["PORTFOLIO_BRIEF"] = account.brief(j)
        if route_name in ("market", "both"):
            mine = {p["coin"] for p in account.chain_book(j)[0]}
            m = json.loads(json.dumps(market_brief(j), default=str))
            for c in m.get("coins", []):
                c.pop("we_hold_trade", None)
                c["you_hold"] = c["coin"] in mine
            m.pop("evidence", None)
            m["note"] = "Market facts are shared; holdings shown are this visitor's own. Ananta's research books are not theirs."
            out["MARKET_BRIEF"] = m
        return out
    if route_name in ("portfolio", "both"):
        out["PORTFOLIO_BRIEF"] = portfolio_brief(j)
    if route_name in ("market", "both"):
        out["MARKET_BRIEF"] = market_brief(j)
    return out


def size(d: dict) -> int:
    return len(json.dumps(d, default=str))
