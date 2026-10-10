"""Each account's own data (build plan Phase 1, 2026-10-08): one profile per account, yours included, and the visitor's own
screens. Madhav, 2026-10-06: "Remove everything. Let it be like a new account".

Profile (table visitor_profile in the account's own database; the owner's lives in jarvis.sqlite): name, time zone, experience,
crypto knowledge, risk comfort, explanation level, voice, theme, coins of interest, capital, and the setup steps below.

A visitor starts with nothing of Madhav's on screen. Setup, in order (the app shows one step at a time):
  name     what should Jarvis call you
  coins    pick a few coins to watch and talk about
  tour     a short walk through their own (empty) tabs, skippable; the last screen lists what they can do
  capital  practice capital: $1,000 or $2,000
  ready    their Books show "Start trading" (nothing else until they start)
  trading  they started: Jarvis finds a trade with them, or they trade themselves
Everything lives in the visitor's own practice database (table visitor_profile). Markets, Home and Books for a visitor are
built only from their coins and their own book; Madhav's books, Explorer, Jarvis's book and history are not shown to them.
"""
from __future__ import annotations

import json
from typing import Any

COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "LINK", "LTC", "BCH"]
NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "XRP", "DOGE": "Dogecoin", "ADA": "Cardano",
         "AVAX": "Avalanche", "LINK": "Chainlink", "LTC": "Litecoin", "BCH": "Bitcoin Cash"}
CAPITALS = tuple(range(1000, 10001, 1000))          # plan 5.4: $1,000 to $10,000 in $1,000 steps
STAGES = ("name", "coins", "tour", "capital", "ready", "trading")
CHOICES = {"experience": ("never", "under_1y", "1_3y", "over_3y"), "crypto": ("new", "hold", "trade"),
           "risk": ("careful", "balanced", "bold"), "theme": ("light", "bat"),
           "voice": ("Calm", "Friendly", "Deep", "Bright", "British", "Phone")}
RISK_PCT = {"careful": 0.5, "balanced": 1.0, "bold": 1.5}          # D2: share of capital a trade may lose at its stop
WORDS = {"never": "never traded", "under_1y": "trading under a year", "1_3y": "trading 1 to 3 years", "over_3y": "trading over 3 years",
         "new": "new to crypto", "hold": "holds some crypto", "trade": "trades crypto"}


def _table(db) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS visitor_profile (k TEXT PRIMARY KEY, v TEXT)")


def profile(db) -> dict:
    _table(db)
    p = {k: json.loads(v) for k, v in db.execute("SELECT k, v FROM visitor_profile")}
    p.setdefault("coins", [])
    return p


def capital(db, default: float = 1000.0) -> float:
    try:
        r = db.execute("SELECT v FROM visitor_profile WHERE k='capital'").fetchone()
        return float(json.loads(r[0])) if r else default
    except Exception:  # noqa: BLE001  the owner's database has no profile: the default
        return default


def stage(p: dict) -> str:
    if not p.get("name"):
        return "name"
    if not p.get("coins"):
        return "coins"
    if not p.get("tour_done"):
        return "tour"
    if not p.get("capital"):
        return "capital"
    if not p.get("started_t"):
        return "ready"
    return "trading"


def update(j, b: dict, email: str = "") -> dict:
    """Saves one or more setup answers. Unknown keys are ignored; bad values raise ValueError (shown to the visitor)."""
    db = j.db
    _table(db)
    now = int(j.now())
    out: dict[str, Any] = {}
    if b.get("name") is not None:
        nm = " ".join(str(b["name"]).split())[:40]
        if not nm:
            raise ValueError("enter a name")
        out["name"] = nm
    if b.get("coins") is not None:
        cs = [c for c in dict.fromkeys(str(x).upper() for x in (b["coins"] or [])) if c in COINS]
        if not cs:
            raise ValueError("pick at least one coin")
        out["coins"] = cs
    for k, allowed in CHOICES.items():
        if b.get(k) is not None:
            v = str(b[k])
            if v not in allowed:
                raise ValueError(f"{k} is one of: {', '.join(allowed)}")
            out[k] = v
    if b.get("tz") is not None:
        tz = str(b["tz"])[:64]
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(tz)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("unknown time zone") from exc
        out["tz"] = tz
    if b.get("tour_done"):
        out["tour_done"] = now
    for k in ("paused", "auto"):                         # plan 3.8 (D11): a visitor's own kill switch and autopilot
        if b.get(k) is not None:
            out[k] = bool(b[k])
    if b.get("capital") is not None:
        cap = int(float(b["capital"]))
        if cap not in CAPITALS:
            raise ValueError("practice capital is $1,000 to $10,000, in steps of $1,000")
        p = profile(db)
        if p.get("capital") and p["capital"] != cap and _has_fills(db):
            raise ValueError("your practice capital is set once you have traded; use Start over to change it")
        out["capital"] = cap
    if b.get("start_trading"):
        out["started_t"] = profile(db).get("started_t") or now
        if b.get("method") in ("jarvis", "myself"):
            out["method"] = b["method"]
    for k, v in out.items():
        db.execute("INSERT OR REPLACE INTO visitor_profile VALUES (?,?)", (k, json.dumps(v)))
    db.commit()
    if "auto" in out:                                   # Auto mode on: every watch takes its trades; off: every watch asks first
        from jarvis.service import watches

        for w in watches.list_(j):
            if w["state"] != "DELETED" and w["mode"] != "tell":
                watches.change(j, w["id"], "auto" if out["auto"] else "ask", None)
    if "name" in out:                                   # the account's name follows (Jarvis calls them by it)
        try:
            j.users_db.execute("UPDATE users SET name=? WHERE email=?", (out["name"], email))
            j.users_db.commit()
        except Exception:  # noqa: BLE001
            pass
    return me(j)


def _has_fills(db) -> bool:
    try:
        return bool(db.execute("SELECT 1 FROM manual_fills LIMIT 1").fetchone())
    except Exception:  # noqa: BLE001
        return False


def level(p: dict) -> str:
    """beginner | experienced, from what they told us (used for how much Ananta explains)."""
    if p.get("experience") in ("1_3y", "over_3y") or p.get("crypto") == "trade":
        return "experienced"
    return "beginner" if p.get("experience") or p.get("crypto") else "unknown"


def owner_profile(j) -> dict:
    """The owner's profile: his saved choices over sensible defaults (D6: Ananta calls him sir; his default voice is male)."""
    p = profile(j.db)
    return {"name": p.get("name") or j.owner_name, "call": "sir", "voice": p.get("voice") or "Deep", "theme": p.get("theme") or "bat",
            "tz": p.get("tz") or "America/Toronto", "experience": p.get("experience") or "over_3y", "crypto": p.get("crypto") or "trade",
            "risk": p.get("risk") or "balanced", "coins": p.get("coins") or list(COINS)}


def local_hour(p: dict, now: float) -> int:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        return datetime.fromtimestamp(now, ZoneInfo(p.get("tz") or "America/Toronto")).hour
    except Exception:  # noqa: BLE001
        return datetime.fromtimestamp(now, ZoneInfo("America/Toronto")).hour


def me(j) -> dict:
    p = profile(j.db)
    try:                                                  # Phase 5: has this visitor finished the first conversation?
        from jarvis.service import onboard

        ob = onboard.step(j)
    except Exception:  # noqa: BLE001
        ob = "done"
    return {"onboard": ob, "profile": {k: p.get(k) for k in ("name", "coins", "capital", "tour_done", "started_t", "method", "tz", "experience", "crypto",
                                                "risk", "voice", "theme", "paused", "auto")} | {"level": level(p)}, "stage": stage(p),
            "coin_choices": [{"coin": c, "name": NAMES[c]} for c in COINS], "capitals": list(CAPITALS)}


# ---------------------------------------------------------------------------
# the visitor's own screens
# ---------------------------------------------------------------------------
def _watch(j, coins: list[str]) -> list[dict]:
    from jarvis.service import views

    m = views.markets(j)
    by = {r["coin"]: r for r in m.get("coins") or []}
    out = []
    for c in coins:
        r = by.get(c) or {"coin": c}
        out.append({k: r.get(k) for k in ("coin", "price", "day_pct", "week_pct", "spark", "trend_1h", "trend_4h", "daily")} | {"name": NAMES.get(c, c)})
    return out


def _book(j) -> dict:
    from jarvis.service.manual import Manual

    m = Manual(j.db, j.now)
    st = m.state(j.prices())
    return {**st, "fills": m.fills()}


def markets(j) -> dict:
    p = profile(j.db)
    rows = _watch(j, p.get("coins") or [])
    up = sum(1 for r in rows if (r.get("day_pct") or 0) > 0)
    return {"visitor": True, "coins": rows, "others": [{"coin": c, "name": NAMES[c]} for c in COINS if c not in (p.get("coins") or [])],
            "summary": (f"{up} of your {len(rows)} coin{'s' if len(rows) != 1 else ''} are up today." if rows else "Pick coins to watch.")}


def books(j) -> dict:
    p = profile(j.db)
    st = stage(p)
    b = _book(j) if p.get("capital") else None
    return {"visitor": True, "stage": st, "capital": p.get("capital"), "started": bool(p.get("started_t")), "method": p.get("method"),
            "coins": p.get("coins") or [], "book": b}


def home(j) -> dict:
    p = profile(j.db)
    rows = _watch(j, p.get("coins") or [])
    b = _book(j) if p.get("capital") else None
    nxt = {"name": "Tell Ananta your name", "coins": "Pick coins to watch", "tour": "Take the quick tour", "capital": "Add practice capital",
           "ready": "Start trading", "trading": None}[stage(p)]
    out = {"visitor": True, "name": p.get("name"), "stage": stage(p), "next": nxt, "coins": rows, "book": b,
           "started": bool(p.get("started_t"))}
    # plan 3.1: the shared market rule, what Ananta is doing for this account, and what needs them (their own layer only)
    from jarvis.service import views, watches
    try:
        out["market"] = views.market_rule(j)
    except Exception:  # noqa: BLE001
        pass
    try:
        out["agent"] = watches.state(j)
    except Exception:  # noqa: BLE001
        pass
    try:
        out["findings"] = [f for f in views.findings(j) if f["kind"] == "SHIFT"]     # market shifts are shared; nothing of Madhav's books
    except Exception:  # noqa: BLE001
        out["findings"] = []
    return out


def prompt_note(j, name: str) -> str:
    """What Jarvis knows about this visitor's own account (added to every question they ask)."""
    try:
        p = profile(j.db)
        b = _book(j) if p.get("capital") else None
    except Exception:  # noqa: BLE001
        return ""
    coins = ", ".join(NAMES.get(c, c) for c in p.get("coins") or []) or "none yet"
    if b:
        pos = "; ".join(f"{x['coin']} ${x['value'] or 0:,.0f} ({'+' if (x['pnl'] or 0) >= 0 else '-'}${abs(x['pnl'] or 0):,.2f})" for x in b["positions"]) or "no open positions"
        book = (f"practice capital ${p['capital']:,}, cash ${b['cash']:,.2f}, value ${b['equity']:,.2f}, {len(b['fills'])} order(s) so far; "
                f"positions: {pos}")
    else:
        book = "no practice capital added yet"
    about = ", ".join(WORDS[v] for v in (p.get("experience"), p.get("crypto")) if v in WORDS)
    lv = level(p)
    style = ("Explain as you go in plain words, one idea at a time, no jargon; offer to go deeper." if lv == "beginner" else
             "Keep it short; they can ask you to break anything down." if lv == "experienced" else "")
    risk = (f" Risk comfort: {p['risk']} (a trade risks {RISK_PCT[p['risk']]}% of their capital at its stop)." if p.get("risk") in RISK_PCT else "")
    return (f"[THEIR OWN ACCOUNT: {name or 'This visitor'} has a practice account of their own"
            + (f" ({about})" if about else "") + f". {style}{risk} Their coins: {coins}. "
            f"Their book: {book}. Trading started: {'yes' if p.get('started_t') else 'not yet'}. "
            "Talk about THEIR coins and THEIR practice book as theirs ('your book', 'your Solana'). Madhav's books (the Explorer, the trend "
            "portfolio, Jarvis's own book) and their history are NOT theirs: never present them as theirs, and mention them only if they ask "
            "how the system works. When they ask you to find a trade: look at their coins first (zones, trend, the market rule), pick at most "
            "one idea with a plan (why, where it is wrong, stop, size in dollars within their cash), and prepare it with propose_paper_order "
            "so they confirm it on a card; if nothing is worth it, say so and say what you are waiting for.]")


def chain_book(j) -> tuple[list[dict], float]:
    """This account's own open positions and equity, for the decision chain's exposure and risk gates (a visitor's answers must
    never count the Explorer's open trades as theirs: status check, Oct 8, Mahi was told she held 12)."""
    from jarvis.service.manual import Manual

    st = Manual(j.db, j.now).state(j.prices())
    return [{"coin": x["coin"], "setup": "yours"} for x in st["positions"]], float(st["equity"] or st["start"])


def brief(j) -> dict:
    """The PORTFOLIO_BRIEF for a visitor's question: their own account only."""
    p = profile(j.db)
    b = _book(j) if p.get("capital") else None
    out: dict[str, Any] = {"whose": "THIS VISITOR'S OWN practice account (not Madhav's books)", "name": p.get("name"),
                           "coins": p.get("coins") or [], "capital": p.get("capital"), "trading_started": bool(p.get("started_t")),
                           "level": level(p), "risk": p.get("risk")}
    if b:
        out["book"] = {"value": b["equity"], "cash": b["cash"], "start": b["start"], "return_pct": b["return_pct"],
                       "positions": [{"coin": x["coin"], "value": x["value"], "pnl": x["pnl"], "stop": x["stop"], "target": x["target"]}
                                     for x in b["positions"]],
                       "orders": [{"t": f["t"], "coin": f["coin"], "side": f["side"], "usd": f["usd"], "price": f["px"]} for f in b["fills"][:10]]}
    out["their_coins_now"] = [{k: v for k, v in r.items() if k != "spark"} for r in _watch(j, p.get("coins") or [])]
    return out
