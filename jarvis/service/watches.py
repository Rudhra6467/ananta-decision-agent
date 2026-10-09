"""Watches that act for an account (build plan 1.4 to 1.8, Madhav 2026-10-08: "Keep watching BTC for me" must create a watch,
and later "BTC is approaching the condition you asked me to watch for. I haven't taken anything yet because you chose approval
mode").

A watch: coins (or a named group), a setup kind in plain words, a mode, and a state.
  kinds   only ideas our evidence allows to trade on paper (status cards with PAPER permission); switched-off kinds are never offered
  modes   tell (tell me when it fires), ask (ask me first: a card that expires), auto (Ananta takes it and tells me)
  states  WATCHING -> CLOSE (one condition missing) -> FIRED (acted on) ; PAUSED ; DELETED
Every 15 minutes check_all() looks at the shared brain (the decision chain and the Explorer's setups) once, then at every
account's watches. Whatever Ananta does is written as a decision card (found, why, wrong if, doing) in the account's activity
log, which also answers "what are you doing", "what changed since this morning".

Trust boundary: Ananta trades only through a watch in auto mode or a card the person confirmed; manual positions are watched
(monitor_manual) and get a warning and an exit card, never an automatic sale (their own stop is their own instruction).
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Callable

GROUPS = {"my_coins": "my coins", "all": "all 10 coins", "large": "the large coins (Bitcoin, Ethereum, Solana, XRP)"}
LARGE = ["BTC", "ETH", "SOL", "XRP"]
KINDS = {
    "zone_pullback": {"name": "Pullback into a supported zone", "card": "ZONES",
                      "plain": "price dips into a zone history supports while the coin's trend is up and Bitcoin's market rule is open"},
    "setup_15m": {"name": "A 15-minute setup completes", "card": "EXPLORER",
                  "plain": "every condition of one of Ananta's 15-minute setups is met (still being tested on paper)"},
    "trend_hold": {"name": "Hold while the trend is up", "card": "T3",
                   "plain": "the trend portfolio rates the coin strong while Bitcoin's market rule is open"},
}
DEFAULT_KIND = "zone_pullback"          # the best-supported kind today (zones + market rule + structural stop: SUPPORTED, PAPER)
MODES = {"tell": "tell me when it fires", "ask": "ask me first", "auto": "take it and tell me"}
EXPIRY_S = 30 * 60                      # D3: an "ask me first" card expires after 30 minutes
REARM_S = 24 * 3600                     # a fired watch looks again a day later
MAX_ORDER_SHARE = 0.25                  # D2: one order at most a quarter of the capital


def _table(db) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS account_watches (id TEXT PRIMARY KEY, t INTEGER, coins TEXT, grp TEXT, kind TEXT, mode TEXT,
            state TEXT, detail TEXT, checked_t INTEGER, fired_t INTEGER, by TEXT);
        CREATE TABLE IF NOT EXISTS account_activity (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, title TEXT, body TEXT, card TEXT, ref TEXT);
    """)
    db.commit()


def kinds() -> list[dict]:
    """The kinds a person may pick: only ideas whose evidence card allows paper trading."""
    from jarvis.service import brain

    cards = brain.status_cards()
    out = []
    for k, v in KINDS.items():
        c = cards.get(v["card"]) or {}
        if c.get("permission") in ("PAPER", "LIVE_PROVEN"):
            out.append({"kind": k, "name": v["name"], "plain": v["plain"], "evidence": (c.get("evidence") or "").lower(),
                        "default": k == DEFAULT_KIND})
    return out


def log(j, kind: str, title: str, body: str = "", card: dict | None = None, ref: str = "") -> dict:
    _table(j.db)
    row = (uuid.uuid4().hex[:12], int(j.now()), kind, title[:200], body[:600], json.dumps(card) if card else None, ref)
    j.db.execute("INSERT INTO account_activity VALUES (?,?,?,?,?,?,?)", row)
    j.db.commit()
    return {"id": row[0], "t": row[1], "kind": kind, "title": title, "body": body, "card": card}


def activity(j, since: int = 0, n: int = 50) -> list[dict]:
    _table(j.db)
    return [{"id": i, "t": t, "kind": k, "title": ti, "body": b, "card": json.loads(c) if c else None, "ref": r}
            for i, t, k, ti, b, c, r in j.db.execute("SELECT * FROM account_activity WHERE t >= ? ORDER BY t DESC, rowid DESC LIMIT ?", (since, n))]


def _coins_of(j, coins: list[str] | None, grp: str | None) -> list[str]:
    from jarvis.service import account

    if grp == "my_coins":
        return account.profile(j.db).get("coins") or list(account.COINS)
    if grp == "all":
        return list(account.COINS)
    if grp == "large":
        return list(LARGE)
    return [c for c in dict.fromkeys(str(x).upper() for x in coins or []) if c in account.COINS]


def create(j, coins: list[str] | None = None, grp: str | None = None, kind: str | None = None, mode: str = "ask", by: str = "") -> dict:
    _table(j.db)
    kind = kind or DEFAULT_KIND
    allowed = {k["kind"] for k in kinds()}
    if kind not in allowed:
        raise ValueError(f"I can't watch for that: our evidence does not allow trading it. Choose from: {', '.join(sorted(allowed))}")
    if mode not in MODES:
        raise ValueError("mode is tell, ask or auto")
    if grp and grp not in GROUPS:
        raise ValueError(f"group is one of: {', '.join(GROUPS)}")
    cs = _coins_of(j, coins, grp)
    if not cs:
        raise ValueError("name at least one of our 10 coins, or a group")
    wid = "W" + uuid.uuid4().hex[:9]
    j.db.execute("INSERT INTO account_watches VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (wid, int(j.now()), json.dumps(cs), grp, kind, mode, "WATCHING", None, None, None, by))
    j.db.commit()
    w = get(j, wid)
    log(j, "watch", f"Watching {describe(w)}", f"Mode: {MODES[mode]}.", ref=wid)
    return w


def get(j, wid: str) -> dict | None:
    _table(j.db)
    r = j.db.execute("SELECT * FROM account_watches WHERE id=?", (wid,)).fetchone()
    return _row(r) if r else None


def _row(r) -> dict:
    wid, t, coins, grp, kind, mode, state, detail, checked_t, fired_t, by = r
    w = {"id": wid, "t": t, "coins": json.loads(coins or "[]"), "group": grp, "kind": kind, "kind_name": KINDS.get(kind, {}).get("name", kind),
         "mode": mode, "mode_words": MODES.get(mode, mode), "state": state, "detail": json.loads(detail) if detail else {},
         "checked_t": checked_t, "fired_t": fired_t, "by": by}
    return w


def describe(w: dict) -> str:
    from jarvis.service.account import NAMES

    who = GROUPS.get(w.get("group") or "") or ", ".join(NAMES.get(c, c) for c in w["coins"])
    return f"{who} for: {w['kind_name'].lower()}"


def list_(j, include_deleted: bool = False) -> list[dict]:
    _table(j.db)
    q = "SELECT * FROM account_watches" + ("" if include_deleted else " WHERE state != 'DELETED'") + " ORDER BY t DESC"
    return [_row(r) for r in j.db.execute(q)]


def change(j, wid: str, mode: str | None = None, state: str | None = None) -> dict:
    w = get(j, wid)
    if not w:
        raise ValueError("unknown watch")
    if mode:
        if mode not in MODES:
            raise ValueError("mode is tell, ask or auto")
        j.db.execute("UPDATE account_watches SET mode=? WHERE id=?", (mode, wid))
        log(j, "watch", f"{describe(w).split(' for:')[0]}: now {MODES[mode]}", ref=wid)
    if state:
        if state not in ("WATCHING", "PAUSED", "DELETED"):
            raise ValueError("state is WATCHING, PAUSED or DELETED")
        j.db.execute("UPDATE account_watches SET state=? WHERE id=?", (state, wid))
        log(j, "watch", f"Stopped watching {describe(w)}" if state == "DELETED" else f"Watch {state.lower()}: {describe(w)}", ref=wid)
    j.db.commit()
    return get(j, wid)


# ---------------------------------------------------------------------------
# matching (once per 15 minutes, for every account)
# ---------------------------------------------------------------------------
def snapshot(main_j) -> dict:
    """The shared brain's view, computed once per cycle: per coin the decision chain (without any account's risk or exposure),
    the Explorer's closest setup, and the trend portfolio's rating."""
    from jarvis.service import chain, views

    out: dict[str, dict] = {}
    b = chain.board(main_j, book=([], 10000.0))
    m = {r["coin"]: r for r in views.markets(main_j).get("coins") or []}
    for r in b.get("coins", []):
        gates = {g["gate"]: g for g in r.get("gates", [])}
        out[r["coin"]] = {"chain": r, "gates": gates, "market": m.get(r["coin"]) or {}}
    return out


def _gate_ok(s: dict, name: str) -> bool:
    return (s["gates"].get(name) or {}).get("status") == "PASS"


def evaluate(kind: str, s: dict) -> tuple[str, str, dict]:
    """(state, why, plan) for one coin: FIRED, CLOSE or WATCHING."""
    ch, mk = s["chain"], s["market"]
    price = ch.get("price") or mk.get("price")
    inv = (s["gates"].get("INVALIDATION") or {}).get("values") or {}
    stop = inv.get("stop")
    zone = (ch.get("observations") or {}).get("zone") or {}
    res = zone.get("next_resistance_pct")
    plan = {"price": price, "stop": stop, "target": round(price * (1 + res / 100), 8) if price and res and res > 1.2 else None}
    if kind == "zone_pullback":
        need = ["REGIME", "TREND", "LOCATION", "INVALIDATION"]
        ok = [g for g in need if _gate_ok(s, g)]
        if len(ok) == len(need) and stop and price and stop < price:
            return "FIRED", ch.get("summary") or "", plan
        if len(ok) == len(need) - 1:
            miss = next(g for g in need if g not in ok)
            return "CLOSE", f"{len(ok)} of {len(need)}: waiting on {miss.lower()} ({(s['gates'].get(miss) or {}).get('why', '')})", plan
        return "WATCHING", ch.get("summary") or "", plan
    if kind == "setup_15m":
        cl = mk.get("closest") or {}
        if cl and cl.get("met") == cl.get("of") and _gate_ok(s, "REGIME"):
            return "FIRED", f"{cl.get('name')}: every condition met, market open", plan
        if cl and cl.get("of", 0) - cl.get("met", 0) == 1:
            return "CLOSE", f"{cl.get('name')}: {cl.get('met')} of {cl.get('of')}, missing {', '.join(cl.get('missing') or [])}", plan
        return "WATCHING", f"closest: {cl.get('name')} {cl.get('met')}/{cl.get('of')}" if cl else "", plan
    if kind == "trend_hold":
        strong = mk.get("rating") == "STRONG" and _gate_ok(s, "REGIME") and _gate_ok(s, "TREND")
        if strong and stop and price and stop < price:
            return "FIRED", "the trend portfolio rates it strong and the market rule is open", plan
        return ("CLOSE" if _gate_ok(s, "TREND") else "WATCHING"), "trend up, waiting for a strong rating" if _gate_ok(s, "TREND") else "", plan
    return "WATCHING", "", plan


def kinds_for(risk: str | None) -> tuple[list[dict], list[str]]:
    """Plan 4.4: risk comfort is a real filter. Careful accounts get only kinds whose evidence is SUPPORTED; the others get every
    paper-allowed kind. Returns (kinds, names filtered out), so Ananta mentions a filter only when it actually removed something."""
    ks = kinds()
    if (risk or "balanced") != "careful":
        return ks, []
    keep = [k for k in ks if k["evidence"] == "supported"]
    return keep, [k["name"] for k in ks if k not in keep]


def best_setups(main_j, risk: str | None = None, coins: list[str] | None = None, n: int = 3) -> dict:
    """Plan 4.3: "show me the setup you like most". Every coin against every kind this account may use, ranked: setups that are
    ready first, then the ones one condition away. Each comes as a decision card."""
    ks, filtered = kinds_for(risk)
    snap = snapshot(main_j)
    rows = []
    for coin, s in snap.items():
        if coins and coin not in coins:
            continue
        for k in ks:
            state, why, plan = evaluate(k["kind"], s)
            if state == "WATCHING":
                continue
            rows.append({"coin": coin, "kind": k["kind"], "kind_name": k["name"], "state": state, "why": why, "plan": plan,
                         "card": card(coin, k["kind"], why, plan, "Nothing bought: tell me to watch it or to place it."),
                         "rank": (0 if state == "FIRED" else 1, 0 if k.get("default") else 1)})
    rows.sort(key=lambda r: r["rank"])
    out = {"best": [{k: v for k, v in r.items() if k != "rank"} for r in rows[:n]], "kinds_used": [k["name"] for k in ks]}
    if filtered:
        out["filtered_out"] = {"kinds": filtered, "why": "careful risk comfort: only setups with supported evidence"}
    if not rows:
        out["none"] = "No setup is ready or one condition away right now."
    return out


def size_usd(j, price: float, stop: float) -> float:
    """D2: risk a share of capital at the stop (careful 0.5%, balanced 1%, bold 1.5%), at most a quarter of capital, within cash."""
    from jarvis.service import account
    from jarvis.service.manual import Manual

    p = account.profile(j.db)
    st = Manual(j.db, j.now).state(j.prices())
    risk = account.RISK_PCT.get(p.get("risk") or "balanced", 1.0) / 100
    usd = st["start"] * risk / max(1e-9, (price - stop) / price)
    return round(max(10.0, min(usd, MAX_ORDER_SHARE * st["start"], st["cash"] * 0.98)), 2)


def card(coin: str, kind: str, why: str, plan: dict, doing: str) -> dict:
    from jarvis.service.account import NAMES

    stop = plan.get("stop")
    return {"found": f"{NAMES.get(coin, coin)}: {KINDS[kind]['name'].lower()}", "why": why,
            "wrong_if": f"a fall below {stop:,.6g}" if stop else "no clear place it is wrong yet", "doing": doing}


def act(j, w: dict, coin: str, why: str, plan: dict, push: Callable[[str, str], Any] | None = None) -> dict:
    """A fired watch: tell, ask (card that expires) or auto (paper order in this account's book)."""
    from jarvis.service.mandate import Mandate
    from jarvis.service.manual import Manual

    price, stop = plan.get("price"), plan.get("stop")
    usd = size_usd(j, price, stop) if price and stop else None
    order = {"side": "buy", "coin": coin, "usd": usd, "stop": stop, "target": plan.get("target"),
             "reason": f"Watch {w['id']}: {KINDS[w['kind']]['name'].lower()}. {why}"[:300]}
    if w["mode"] == "auto" and usd:
        try:
            f = Manual(j.db, j.now).execute("ananta", order, j.prices(), trigger=f"ananta-auto:{w['id']}")
            c = card(coin, w["kind"], why, plan, f"Bought ${f['usd']:,.0f} at {f['price']:,.6g} (auto mode).")
            out = log(j, "trade", f"Bought {coin} for you", c["doing"], c, ref=f["fill"])
        except ValueError as exc:
            c = card(coin, w["kind"], why, plan, f"Could not buy: {exc}.")
            out = log(j, "skip", f"{coin} fired, not bought", c["doing"], c, ref=w["id"])
    elif w["mode"] == "ask" and usd:
        try:
            pv = Manual(j.db, j.now).preview(order, j.prices())
            c = card(coin, w["kind"], why, plan, f"Asking you first: {pv['summary']} The request expires in 30 minutes.")
            a = Mandate(j.db, j.now).propose("paper_order", f"{coin} watch fired. {pv['summary']}",
                                             {**pv["order"], "expires_t": int(j.now()) + EXPIRY_S, "card": c})
            out = log(j, "ask", f"{coin}: your watch fired, waiting for your yes", c["doing"], c, ref=a["id"])
        except ValueError as exc:
            c = card(coin, w["kind"], why, plan, f"It fired, but I could not prepare an order: {exc}.")
            out = log(j, "skip", f"{coin} fired, no order prepared", c["doing"], c, ref=w["id"])
    else:
        c = card(coin, w["kind"], why, plan, "Telling you only (tell-me mode); nothing bought.")
        out = log(j, "tell", f"{coin}: your watch fired", c["doing"], c, ref=w["id"])
    if push:
        try:
            push(out["title"], out["body"])
        except Exception:  # noqa: BLE001
            pass
    return out


def check_account(j, snap: dict, push: Callable | None = None) -> list[dict]:
    _table(j.db)
    try:                                                  # "Pause Ananta for me" (plan 3.8): no watch acts for this account
        from jarvis.service import account

        if account.profile(j.db).get("paused"):
            return []
    except Exception:  # noqa: BLE001
        pass
    now = int(j.now())
    done = []
    for w in list_(j):
        if w["state"] in ("PAUSED", "DELETED"):
            continue
        if w["state"] == "FIRED" and w["fired_t"] and now - w["fired_t"] < REARM_S:
            continue
        best = ("WATCHING", "", {}, None)
        per = {}
        for coin in w["coins"]:
            s = snap.get(coin)
            if not s:
                continue
            st, why, plan = evaluate(w["kind"], s)
            per[coin] = {"state": st, "why": why}
            rank = {"FIRED": 2, "CLOSE": 1, "WATCHING": 0}
            if rank[st] > rank[best[0]]:
                best = (st, why, plan, coin)
        state, why, plan, coin = best
        detail = {"coins": per, "best": coin, "why": why}
        if state == "FIRED" and coin:
            a = act(j, w, coin, why, plan, push)
            j.db.execute("UPDATE account_watches SET state='FIRED', fired_t=?, checked_t=?, detail=? WHERE id=?",
                         (now, now, json.dumps(detail), w["id"]))
            done.append({"watch": w["id"], "coin": coin, "kind": a.get("kind"), "body": a.get("body")})
        else:
            if state == "CLOSE" and w["state"] != "CLOSE" and coin:
                log(j, "close", f"{coin} is getting close to your watch", why, ref=w["id"])
            j.db.execute("UPDATE account_watches SET state=?, checked_t=?, detail=? WHERE id=?", (state, now, json.dumps(detail), w["id"]))
        j.db.commit()
    return done


def monitor_manual(j, snap: dict, push: Callable | None = None) -> list[dict]:
    """1.6: the account's own positions are watched like any other; a risky one gets one warning and an exit card per reason."""
    from jarvis.service.mandate import Mandate
    from jarvis.service.manual import Manual

    _table(j.db)
    st = Manual(j.db, j.now).state(j.prices())
    out = []
    for p in st["positions"]:
        s = snap.get(p["coin"]) or {}
        reasons = []
        pnl_pct = 100 * (p["pnl"] or 0) / p["cost"] if p.get("cost") else 0
        if not p.get("stop") and pnl_pct <= -5:
            reasons.append(("deep", f"down {abs(pnl_pct):.1f}% with no stop set"))
        if s and not _gate_ok(s, "REGIME"):
            reasons.append(("riskoff", "Bitcoin's market rule turned risk-off"))
        if s and not _gate_ok(s, "TREND") and pnl_pct < 0:
            reasons.append(("trend", "its own trend turned down"))
        for key, why in reasons:
            ref = f"warn:{p['coin']}:{key}:{int(p['cost'])}"
            if j.db.execute("SELECT 1 FROM account_activity WHERE ref=?", (ref,)).fetchone():
                continue
            c = {"found": f"Your {p['coin']} position is getting risky", "why": why,
                 "wrong_if": "it recovers above where you bought", "doing": "I won't touch it. I recommend reviewing it; tap Exit if you want out."}
            Mandate(j.db, j.now).propose("paper_order", f"Exit your {p['coin']} position? ({why})",
                                         {"side": "sell", "coin": p["coin"], "usd": None, "reason": f"exit suggested: {why}", "card": c,
                                          "expires_t": int(j.now()) + 6 * 3600})
            out.append(log(j, "warn", f"Your {p['coin']} position: {why}", c["doing"], c, ref=ref))
            if push:
                try:
                    push(f"Your {p['coin']} position", why)
                except Exception:  # noqa: BLE001
                    pass
    return out


def state(j) -> dict:
    """1.8: 'what are you doing right now' for this account."""
    from jarvis.service.mandate import Mandate
    from jarvis.service.manual import Manual

    ws = [w for w in list_(j) if w["state"] != "DELETED"]
    pos = Manual(j.db, j.now).state(j.prices())["positions"]
    held = len(pos)
    if not getattr(j, "sandbox", False):                  # Madhav: every open trade across his books, not only his own calls
        try:
            from jarvis.service import books

            held = len(books.view(j, getattr(j, "owner_name", "") or "", True)["trades"])
        except Exception:  # noqa: BLE001
            pass
    waiting = [f"{w['detail'].get('best')}: {w['detail'].get('why')}" for w in ws if w["state"] == "CLOSE" and w["detail"].get("best")]
    needs = Mandate(j.db, j.now).pending()
    n_w = len([w for w in ws if w["state"] != "PAUSED"])
    watching = f"Watching {n_w} setup{'s' if n_w != 1 else ''}"
    if not getattr(j, "sandbox", False):                  # Madhav: the brain's own watches run for his books every 15 minutes
        watching = "Watching 10 coins: the 15-minute, hourly and daily setups" + (f", plus your {n_w} watch{'es' if n_w != 1 else ''}" if n_w else "")
    lines = [{"tone": "good", "text": watching},
             {"tone": "good", "text": f"Monitoring {held} position{'s' if held != 1 else ''}"}]
    lines += [{"tone": "wait", "text": f"Waiting for {x}"} for x in waiting[:3]]
    try:                                                  # the shared market rule: is Ananta allowed to buy at all right now?
        from jarvis.service import views

        mk = views.market_rule(j)
        if mk.get("regime") == "RISK_OFF":
            lines.append({"tone": "wait", "text": "Waiting for Bitcoin to close back above its 50-day average"})
        elif mk.get("regime") == "ALLOWED" and mk.get("live_side") == "below":
            lines.append({"tone": "wait", "text": "Waiting for Bitcoin's daily close: it dipped under its 50-day average"})
    except Exception:  # noqa: BLE001
        pass
    lines.append({"tone": "act", "text": f"{len(needs)} need{'s' if len(needs) == 1 else ''} you"} if needs else {"tone": "none", "text": "Nothing needs you"})
    return {"lines": lines, "watches": ws, "positions": pos, "needs_you": len(needs)}


def since(j, t: int) -> dict:
    """1.8: 'what changed since this morning' for this account. Madhav's also carries his books' own feed (zone entries, trades,
    warnings), since the brain acts for him directly."""
    ev = activity(j, since=t, n=100)
    if not getattr(j, "sandbox", False):
        try:
            from jarvis.service import views

            for i, f in enumerate(views.feed(j, hours=max(1.0, (j.now() - t) / 3600), limit=60)):
                if (f.get("t") or 0) >= t:
                    ev.append({"id": f"feed{i}", "t": f["t"], "kind": f.get("kind"), "title": f.get("title"), "body": f.get("body"), "card": None, "ref": None})
        except Exception:  # noqa: BLE001
            pass
        ev.sort(key=lambda x: -(x.get("t") or 0))
    return {"since_t": t, "events": ev[:100]}


def check_all(main_j, accounts: list, push_for: Callable[[Any], Callable | None] | None = None) -> dict:
    """The 15-minute pass: one snapshot of the shared brain, then every account's watches and positions."""
    t0 = time.time()
    snap = snapshot(main_j)
    fired = warned = 0
    for j in accounts:
        push = push_for(j) if push_for else None
        try:
            fired += len(check_account(j, snap, push))
            warned += len(monitor_manual(j, snap, push))
        except Exception:  # noqa: BLE001  one account never stops the others
            continue
    return {"accounts": len(accounts), "fired": fired, "warned": warned, "ms": int(1000 * (time.time() - t0))}
