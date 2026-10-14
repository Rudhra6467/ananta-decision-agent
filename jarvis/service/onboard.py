"""The first conversation (build plan Phase 5, D12, D13): a new visitor meets Ananta inside Ask Ananta, not on a series of screens.

Every step teaches Ananta about the person, shows something Ananta can do, or sets up something Ananta keeps doing (rule 3).
Each step is saved as it is answered (step + transcript in the account's profile), so someone who leaves halfway resumes where
they stopped; Start over runs it again. Every line has a typed path and tappable answers; voice says the first sentence or two.
Beginners get one extra plain sentence for words like zone, stop and paper.

  permission -> can_do -> name -> experience -> crypto -> risk -> coins -> capital -> interest -> setup -> mode -> acts -> demo -> demo_exit
  -> explore -> done

demo / demo_exit (Madhav, Oct 11): when nothing is ready, a DEMO trade at the live price shows how a trade is taken in the mode they
chose (Ask me first: a request card to approve; Auto: it just happens) and how it is exited. It lives only in this profile, never
in a book, scoreboard or the evidence, is labelled DEMO everywhere, and disappears at the first sign-out or after 24 hours.
explore: 'How would you like to explore?' with questions about Ananta's setups and research; the one-minute app tour is one choice.
Typing anything at any step (except the name) ends the first conversation and goes to Ananta as a normal question.

The service decides the words and the next step (no AI call, free and instant); the app only shows them and sends the answers.
"""
from __future__ import annotations

import json
from typing import Any

from jarvis.service import account

STEPS = ("permission", "can_do", "name", "experience", "crypto", "risk", "coins", "capital", "interest", "setup", "mode", "acts", "demo", "demo_exit",
         "explore", "done")
DEMO_HOURS = 24
DEMO_FEE = 0.002                                     # NDAX fee a side, so the demo result looks like a real one
TYPED = "__typed__"                                  # the person typed a question instead of answering: end here, go to Ask
EXPLORE = [
    "What trading setups does Ananta use right now?",
    "What did the research find for each setup?",
    "Which setup has a proven edge, and when does it trade?",
    "Why does Ananta skip most days?",
]
NEXT_CHIPS = ["Give Ananta $500 paper capital and test it live", "Give Ananta $1,000 paper capital and test it live"]
EXP = [["never", "Never"], ["under_1y", "Under a year"], ["1_3y", "1–3 years"], ["over_3y", "Over 3 years"]]
CRYPTO = [["new", "New to it"], ["hold", "I hold some"], ["trade", "I trade it"]]
RISK = [["careful", "Careful"], ["balanced", "Balanced"], ["bold", "Bold"]]
CAN_DO = ["Watches the coins you choose, every 15 minutes, day and night",
          "Finds setups and explains them: why, and what would prove them wrong",
          "Takes practice trades for you, or asks you first: your choice",
          "Watches your own trades and warns you before they turn bad",
          "Answers anything about your coins and your trades, by voice or typing"]


def _get(db, k: str, default: Any = None) -> Any:
    account._table(db)
    r = db.execute("SELECT v FROM visitor_profile WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default


def _put(db, k: str, v: Any) -> None:
    account._table(db)
    db.execute("INSERT OR REPLACE INTO visitor_profile VALUES (?,?)", (k, json.dumps(v)))
    db.commit()


def _say(j, who: str, text: str) -> None:
    log = _get(j.db, "onboard_log", [])
    log.append({"who": who, "text": text})
    _put(j.db, "onboard_log", log[-60:])


def _greeting(j) -> str:
    h = account.local_hour(account.profile(j.db), j.now())
    return "Good morning" if 5 <= h < 12 else "Good afternoon" if 12 <= h < 17 else "Good evening"


def _beginner(p: dict) -> bool:
    return account.level(p) != "experienced"


def _first_step(j) -> str:
    """Where someone starts: from the top, or (an existing visitor at their next sign-in, plan 5.8) at the first thing we don't know."""
    p = account.profile(j.db)
    if not _get(j.db, "onboard_log"):
        return "permission"
    for s in ("name", "experience", "crypto", "risk", "coins", "capital"):
        if not p.get(s) or (s == "coins" and not p.get("coins")):
            return s
    return "interest"


def step(j) -> str:
    s = _get(j.db, "onboard_step")
    if s == "tour":                                    # the old last step (before Oct 11) now leads into the demo
        return "demo"
    return s if s in STEPS else _first_step(j)


def done(j) -> bool:
    return step(j) == "done"


def _setup_choice(j) -> dict:
    """The setup step: the best ready or nearly-ready setup on the coin(s) they care about, as a decision card; or 'nothing now'
    with the setup kinds to watch for (the evidence-based default first)."""
    from jarvis.service import watches
    from jarvis.service.app import _main

    p = account.profile(j.db)
    coins = _get(j.db, "onboard_coins") or p.get("coins") or None
    best = watches.best_setups(_main(), p.get("risk"), coins, n=1)
    ks, _ = watches.kinds_for(p.get("risk"))
    return {"best": (best.get("best") or [None])[0], "kinds": ks}


def prompt(j) -> dict:
    """What Ananta says now and what the person can answer with."""
    s = step(j)
    p = account.profile(j.db)
    name = p.get("name") or ""
    beg = _beginner(p)
    out: dict[str, Any] = {"step": s, "log": _get(j.db, "onboard_log", []), "done": s == "done"}
    if s == "permission":
        out |= {"say": "Ananta talks with you. Allow the microphone?", "input": {"type": "choice", "options": [["voice", "Allow voice"], ["type", "I'll type"]]}}
    elif s == "can_do":
        out |= {"say": "Here is what I can do for you.", "input": {"type": "card", "items": CAN_DO, "options": [["ok", "Let's start"]]}}
    elif s == "name":
        out |= {"say": f"{_greeting(j)}! I'm Ananta, a trading assistant designed by Madhav. What should I call you?",
                "input": {"type": "name", "value": name}}
    elif s == "experience":
        out |= {"say": (f"Nice to meet you, {name}. " if name else "") + "A few quick questions so I can guide you the right way. How long have you been trading?",
                "input": {"type": "choice", "options": EXP}}
    elif s == "crypto":
        out |= {"say": "And crypto?", "input": {"type": "choice", "options": CRYPTO}}
    elif s == "risk":
        out |= {"say": "How do you feel about risk?", "input": {"type": "choice", "options": RISK},
                "note": "Careful: I only use the setups with the strongest evidence, and risk less on each trade." if beg else None}
    elif s == "coins":
        out |= {"say": "Any coins you care about? Pick as many as you like.",
                "input": {"type": "coins", "options": [[c, account.NAMES[c]] for c in account.COINS], "value": p.get("coins") or []}}
    elif s == "capital" and p.get("capital") and account._has_fills(j.db):      # already trading: the capital stays as it is
        out |= {"say": f"You're already practising with ${int(p['capital']):,}, so we'll keep that.", "input": {"type": "choice", "options": [["keep", "Continue"]]}}
    elif s == "capital":
        lead = ("Got it. I'll explain as we go and keep the jargon out. " if beg else "Got it. I'll keep it short; ask me to break anything down. ")
        out |= {"say": lead + "I'll guide you through the app and the coins we watch. How much would you like to practise with? It's paper money, nothing real.",
                "input": {"type": "capital", "options": list(account.CAPITALS), "value": p.get("capital") or 5000},
                "note": "Paper money means pretend money: every trade works like a real one, but nothing real is bought." if beg else None}
    elif s == "interest":
        cs = p.get("coins") or account.COINS
        out |= {"say": "Do you have a coin or a kind of setup in mind? These are the coins I watch.",
                "input": {"type": "choice", "options": [[c, account.NAMES.get(c, c)] for c in cs] + [["any", "You choose"]]}}
    elif s == "setup":
        ch = _setup_choice(j)
        b = ch["best"]
        if b and b["state"] == "FIRED":
            c = b["card"]
            risk = account.RISK_PCT.get(p.get("risk") or "balanced", 1.0)
            out |= {"say": f"{c['found'][:1].upper() + c['found'][1:]}. Why: {c['why']}. Wrong if: {c['wrong_if']}. What I'd do: risk {risk:g}% of your money, "
                           f"with a stop at that line.", "card": c, "found": True,
                    "input": {"type": "choice", "options": [[b["kind"], "Watch for this"]] + [[k["kind"], k["name"]] for k in ch["kinds"] if k["kind"] != b["kind"]]},
                    "note": "A zone is a price band where buyers stepped in before; a stop is the price where the idea is wrong and we sell." if beg else None}
        else:
            close = f" {b['card']['found'].split(':')[0]} is close: {b['why'].split(':')[0]}." if b and b["state"] == "CLOSE" else ""
            opts = [[k["kind"], k["name"] + ("  (best evidence so far)" if k.get("default") else "")] for k in ch["kinds"]]
            out |= {"say": f"Nothing worth taking right now.{close} I'll keep watching. What should I watch for?", "found": False,
                    "input": {"type": "choice", "options": opts + [["any", "You choose"]]}}
    elif s == "mode":
        out |= {"say": "When it comes, how should I take it?",
                "input": {"type": "choice", "options": [["auto", "Auto: I take it and tell you"], ["ask", "Ask me first: I send you a request"]]}}
    elif s == "acts":
        w = _get(j.db, "onboard_watch") or {}
        out |= {"say": w.get("said") or "Done.", "input": {"type": "choice", "options": [["seen", "Show me"]]}, "watch": w}
    elif s == "demo":
        mode = _get(j.db, "onboard_mode") or "ask"
        d = _demo_plan(j)
        if mode == "ask":
            out |= {"say": f"Nothing is ready right now, so let me show you how I'll ask you. When a real setup appears, you get a request like this one. "
                           f"This is a DEMO, not a signal.",
                    "demo": d, "input": {"type": "choice", "options": [["approve", "Approve the demo buy"], ["skip", "Skip the demo"]]}}
        else:
            out |= {"say": "Nothing is ready right now, so let me show you how I take a trade by myself and tell you. This is a DEMO, not a signal.",
                    "demo": d, "input": {"type": "choice", "options": [["go", "Show me the demo trade"], ["skip", "Skip the demo"]]}}
    elif s == "demo_exit":
        d = demo(j) or {}
        out |= {"say": "The demo trade is open, with its stop below. Now the exit: I sell when the plan says so, or you can sell any time from Books.",
                "demo": d, "input": {"type": "choice", "options": [["exit", "Exit the demo trade"]]}}
    elif s == "explore":
        out |= {"say": (f"That's how a trade works, {name}. " if name else "That's how a trade works. ") + "How would you like to explore Ananta?",
                "input": {"type": "choice", "options": [[q, q] for q in EXPLORE] + [["tour", "Show me around the app"]]}}
    else:
        out |= {"say": "That's it. Ask me anything, or tell me what to watch.", "input": None}
    return out


def _next(j, s: str) -> None:
    i = STEPS.index(s)
    _put(j.db, "onboard_step", STEPS[min(i + 1, len(STEPS) - 1)])


def answer(j, s: str, value: Any, email: str = "", tz: str | None = None) -> dict:
    """Save one answer and move on. Raises ValueError (shown to the person) on a bad answer."""
    from jarvis.service import watches

    cur = step(j)
    if value == TYPED and cur != "done":             # they typed a question: the first conversation ends, Ask takes it
        _put(j.db, "onboard_step", "done")
        _put(j.db, "onboard_done", int(j.now()))
        return {**prompt(j), "ask": True, "follow_ups": EXPLORE[:3]}
    if s == "tour" and cur == "demo":               # an app from before Oct 11 answering the old last step
        s = "demo"
    if s != cur:                                   # an old screen answering a step already done: just show where we are
        return prompt(j)
    p = account.profile(j.db)
    asked = prompt(j).get("say") or ""                # the question being answered goes into the transcript first
    said = extra = None
    if tz:
        try:
            account.update(j, {"tz": tz}, email)
        except ValueError:
            pass
    if s == "permission":
        _put(j.db, "voice_ok", value == "voice")
        said = "Allow voice" if value == "voice" else "I'll type"
    elif s == "can_do":
        said = "Let's start"
    elif s == "name":
        account.update(j, {"name": str(value or "")}, email)
        said = account.profile(j.db)["name"]
    elif s in ("experience", "crypto", "risk"):
        account.update(j, {s: str(value)}, email)
        said = dict({"experience": EXP, "crypto": CRYPTO, "risk": RISK}[s]).get(str(value), str(value))
    elif s == "coins":
        account.update(j, {"coins": list(value or [])}, email)
        said = ", ".join(account.NAMES.get(c, c) for c in account.profile(j.db)["coins"])
    elif s == "capital" and value == "keep":
        said = "Continue"
    elif s == "capital":
        account.update(j, {"capital": int(value), "tour_done": True}, email)
        account.update(j, {"start_trading": True, "method": "jarvis"}, email)
        said = f"${int(value):,}"
        extra = f"Good, let's start paper trading crypto with the ${int(value):,} you picked."
    elif s == "interest":
        _put(j.db, "onboard_coins", None if value == "any" else [str(value)])
        said = "You choose" if value == "any" else account.NAMES.get(str(value), str(value))
    elif s == "setup":
        allowed = {k["kind"] for k in watches.kinds()}
        kind = watches.DEFAULT_KIND if value == "any" or value not in allowed else str(value)
        _put(j.db, "onboard_kind", kind)
        said = "You choose" if value == "any" else watches.KINDS[kind]["name"]
    elif s == "mode":
        if value not in ("auto", "ask"):
            raise ValueError("choose Auto or Ask me first")
        coins = _get(j.db, "onboard_coins") or p.get("coins") or ["BTC"]
        kind = _get(j.db, "onboard_kind") or watches.DEFAULT_KIND
        w = watches.create(j, coins, None, kind, str(value), by="ananta (first conversation)")
        res = None
        try:                                       # a setup that is ready right now acts at once (auto: the order; ask: the request)
            from jarvis.service.app import _main

            snap = watches.snapshot(_main())
            res = watches.check_account(j, {c: snap[c] for c in coins if c in snap})
        except Exception:  # noqa: BLE001
            res = None
        who = ", ".join(account.NAMES.get(c, c) for c in coins)
        how = "and I'll take it and tell you" if value == "auto" else "and I'll ask before buying"
        line = f"Done. I'm watching {who} for {watches.KINDS[kind]['name'].lower()}, {how}. Here's where you'll see it."
        traded = [r for r in (res or []) if r.get("kind") == "trade"]
        requested = [r for r in (res or []) if r.get("kind") == "ask"]
        if traded:
            line += f" It was ready now, so I bought it: {traded[0]['body']}"
        elif requested:
            line += " It's ready now: your request is waiting in Needs you."
        _put(j.db, "onboard_watch", {"id": w["id"], "said": line, "order_placed": bool(traded)})
        _put(j.db, "onboard_mode", str(value))
        said = "Auto" if value == "auto" else "Ask me first"
    elif s == "acts":
        said = None
    elif s == "demo":
        if value in ("skip", "later"):
            said = "Skip the demo"
            _say(j, "ananta", asked)
            _say(j, "you", said)
            _put(j.db, "onboard_step", "explore")
            return prompt(j)
        d = _demo_plan(j)
        if not d.get("price"):
            raise ValueError("no live price for the demo right now; try again in a minute, or skip it")
        d.update(entry_t=int(j.now()), entry=d["price"], status="OPEN", mode=_get(j.db, "onboard_mode") or "ask")
        _put(j.db, "demo_seen_mode", d["mode"])
        _put(j.db, "demo_trade", d)
        said = "Approve the demo buy" if value == "approve" else "Show me the demo trade"
        extra = (f"DEMO: bought {d['qty']:g} {d['coin']} (${d['usd']:,.2f}) at ${d['price']:,.2f}. Stop at ${d['stop']:,.2f}. "
                 "It's marked DEMO and isn't counted anywhere.")
    elif s == "demo_exit":
        d = demo(j)
        if d and d.get("status") == "OPEN":
            px = _live(d["coin"]) or d["entry"]
            pnl = d["qty"] * px * (1 - DEMO_FEE) - d["qty"] * d["entry"] * (1 + DEMO_FEE)
            d.update(exit=px, exit_t=int(j.now()), pnl=round(pnl, 2), status="CLOSED")
            _put(j.db, "demo_trade", d)
            extra = (f"DEMO: sold {d['coin']} at ${px:,.2f}. Result ${pnl:+,.2f} after fees, which is mostly the cost of buying and selling. "
                     f"It stays in Books marked DEMO until you sign out, or {DEMO_HOURS} hours at most.")
        said = "Exit the demo trade"
    elif s == "explore":
        said = "Show me around the app" if value == "tour" else str(value)
        _put(j.db, "onboard_done", int(j.now()))
        _say(j, "ananta", asked)
        _say(j, "you", said)
        _next(j, s)
        out = prompt(j)
        return {**out, "explore": value, "follow_ups": [q for q in EXPLORE if q != value][:2] + NEXT_CHIPS}
    _say(j, "ananta", asked)
    if said:
        _say(j, "you", said)
    if extra:
        _say(j, "ananta", extra)
    _next(j, s)
    return prompt(j)


def _live(coin: str) -> float | None:
    try:
        from jarvis.service.app import _main

        return (_main().prices() or {}).get(coin)
    except Exception:  # noqa: BLE001
        return None


def _demo_plan(j) -> dict:
    """The demo's coin, size and stop: their first coin, 1% of their practice money (at least $10), a stop 3% below."""
    p = account.profile(j.db)
    coin = ((_get(j.db, "onboard_coins") or p.get("coins") or ["BTC"]) + ["BTC"])[0]
    px = _live(coin)
    usd = max(10.0, round(0.01 * float(p.get("capital") or 1000), 2))
    return {"demo": True, "coin": coin, "name": account.NAMES.get(coin, coin), "price": px, "usd": usd,
            "qty": round(usd / px, 6) if px else None, "stop": round(px * 0.97, 6) if px else None,
            "why": "DEMO: not a signal. It only shows how a trade is taken and exited."}


def demo(j) -> dict | None:
    """The demo trade, while it may still be shown (until sign-out, or DEMO_HOURS at most)."""
    d = _get(j.db, "demo_trade")
    if d and int(j.now()) - int(d.get("entry_t") or 0) > DEMO_HOURS * 3600:
        clear_demo(j)
        return None
    return d


def clear_demo(j) -> None:
    j.db.execute("DELETE FROM visitor_profile WHERE k='demo_trade'")
    j.db.commit()


def set_capital(j, amount: int, email: str = "") -> dict:
    """The 'Give Ananta $500 / $1,000' chips after the first conversation: Ananta practises with that much, then asks how to take trades."""
    account.update(j, {"capital": int(amount), "start_trading": True, "method": "jarvis"}, email)
    return {"say": f"Done. Ananta now practises with ${int(amount):,} of paper money on the live market, with the same rules and costs as "
                   "Madhav's own book. Nothing is bought until a setup is ready. How should it take each trade?",
            "follow_ups": ["Ask me first for every setup", "Fully automatic"]}


def set_mode(j, mode: str, email: str = "") -> dict:
    """Semi-automatic (ask first) or fully automatic. Choosing 'ask' when the demo showed 'auto' runs the demo again in ask mode."""
    if mode not in ("auto", "ask"):
        raise ValueError("choose ask or auto")
    account.update(j, {"auto": mode == "auto"}, email)
    _put(j.db, "onboard_mode", mode)
    seen = (_get(j.db, "demo_trade") or {}).get("mode") or _get(j.db, "demo_seen_mode")
    if mode == "ask" and seen != "ask":
        clear_demo(j)
        _put(j.db, "onboard_step", "demo")
        return {"demo_again": True, "say": "Semi-automatic: I'll ask you before every trade. Here's how that looks."}
    if mode == "ask":
        return {"say": "Semi-automatic: I'll ask you before every trade, the way the demo showed. Requests appear in Needs you and on your phone.",
                "follow_ups": EXPLORE[:2] + ["What are you watching for me?"]}
    return {"say": "Fully automatic: I take each setup myself, with its stop, and tell you right away. You can switch back any time in Markets.",
            "follow_ups": EXPLORE[:2] + ["What are you watching for me?"]}


def start_over(j) -> None:
    for k in ("onboard_step", "onboard_log", "onboard_coins", "onboard_kind", "onboard_watch", "onboard_done", "onboard_mode", "demo_trade"):
        j.db.execute("DELETE FROM visitor_profile WHERE k=?", (k,))
    j.db.commit()
