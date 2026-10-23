"""Flag it, choose the fix, get told when it's fixed (Madhav, 23 Oct 2026).

Madhav: "I flag an issue and decide on how to fix it and the agent sends the request immediately to backend and gets it fixed and
updates me back ... on both Indian and crypto." His choice: the agent fixes and deploys the SAFE ones by itself; anything that trades,
sizes, costs or is pinned in either lock comes back as a proposal for his yes.

The flow, one row per flag beside its repair-board request (owner_requests, jarvis/service/requests_log.py):

  1. flag()     the app's Flag button sends what is wrong, the market (crypto or india) and the screen. A repair-board request is filed
                at once; a cheap AI call (Sonnet) reads it and offers up to three ways to fix it, each with a lane:
                  SAFE      words, screens, voice, reports, display bugs: the repair worker builds, tests and deploys it
                  DECISION  anything near trading (rules, sizes, costs, stops, exits, books, the gate, a lock): plan only, for his yes
                The lane is decided by code (lane_of), never by the AI alone: the stricter of the two wins.
  2. choose()   Madhav taps one option. SAFE -> state "queued" (scripts/repair_worker.py picks it up within two minutes);
                DECISION -> state "plan" (the worker writes the plan, changes no code).
  3. the worker reports each step (report()): working -> deployed / needs_decision / failed, with the commit and the cost; the request's
                status follows (DONE when deployed), and requests_log.notify sends "Fixed: request N" to the phone.

Spending: the triage call is capped at TRIAGE_DAILY a day; the worker at WORKER_DAILY fixes a day (scripts/repair_worker.py).
Nothing here places an order or changes a trading rule; the worker refuses any change outside SAFE_PATHS (repair_worker.allowed).
"""
from __future__ import annotations

import json
import os
import re
import time

TRIAGE_DAILY = int(os.getenv("FIX_TRIAGE_DAILY", "20"))
SONNET = os.getenv("FIX_TRIAGE_MODEL", "claude-sonnet-5-5")
STATES = ("triaged", "queued", "plan", "working", "deployed", "needs_decision", "failed", "cancelled")
STATE_WORDS = {"triaged": "waiting for your choice", "queued": "queued for the repair worker", "plan": "the worker is writing a plan for your yes",
               "working": "the repair worker is on it", "deployed": "fixed and live", "needs_decision": "needs your yes",
               "failed": "the fix did not pass its checks; nothing changed", "cancelled": "cancelled"}

# Words that put a fix near trading: such a fix is never built by the worker, only planned (DECISION lane).
TRADING = re.compile(r"\b(trade|trades|trading|buy|buys|sell|sells|order|orders|size|sizing|position size|stop|stops|stop-loss|target|exit|exits|"
                     r"entry|entries|threshold|rule|rules|strategy|strategies|book500|\$500 book|book's rules|cost table|costs?|fee|fees|spread|"
                     r"brake|brakes|kill switch|gate|lock|pinned|pin|watch rule|setup rule|risk|leverage|holdout|backtest|live money|real money)\b", re.I)
COLS = ("num", "market", "screen", "route", "lane", "options", "choice", "state", "log", "cost_usd", "branch", "commit_sha", "t", "updated_t")


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS fix_flow (num INTEGER PRIMARY KEY, market TEXT, screen TEXT, route TEXT, lane TEXT, options TEXT, "
                 "choice INTEGER, state TEXT, log TEXT, cost_usd REAL, branch TEXT, commit_sha TEXT, t INTEGER, updated_t INTEGER)")
    j.db.commit()


def lane_of(*texts: str) -> str:
    """SAFE unless any text is about trading; code decides, so a hopeful AI label cannot open the trading lane."""
    return "DECISION" if any(TRADING.search(t or "") for t in texts) else "SAFE"


PROMPT = """You are the repair desk of Ananta, a paper-trading app ({market} market). The owner flagged a problem on the screen "{screen}" (route {route}):

"{text}"

Offer up to three different ways to fix it, most likely first. Each fix must be small and concrete: what will change on screen or in
the words, voice or report, in plain English a non-programmer understands (one or two sentences). Do not offer to change trading rules,
sizes, costs, stops, exits, strategies, the gate or anything that trades; if the problem can only be fixed that way, say so in a fix
whose title starts with "Needs your decision:". Reply with JSON only:
{{"diagnosis": "<one sentence: what is most likely wrong>", "options": [{{"title": "<5-8 words>", "what": "<1-2 sentences>"}}]}}"""


def _ask_ai(prompt: str, post=None) -> tuple[dict, float]:
    from jarvis.service import weblook

    post = post or weblook._post
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("no AI key")
    r = post("https://api.anthropic.com/v1/messages",
             {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
             {"model": SONNET, "max_tokens": 700, "messages": [{"role": "user", "content": prompt}]}, timeout=40)
    text = "".join(b.get("text", "") for b in r.get("content") or [] if b.get("type") == "text")
    u = r.get("usage") or {}
    cost = (u.get("input_tokens", 0) * 3.0 + u.get("output_tokens", 0) * 15.0) / 1e6
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise RuntimeError("the triage reply had no JSON")
    return json.loads(m.group(0)), round(cost, 4)


def _spent_today(j) -> int:
    day0 = int(time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d")))
    return j.db.execute("SELECT COUNT(*) FROM fix_flow WHERE t>=? AND cost_usd>0", (day0,)).fetchone()[0]


def _fallback(text: str) -> dict:
    return {"diagnosis": "I could not read it with the AI just now, so here are the two plain choices.",
            "options": [{"title": "Fix it as I described", "what": f"The repair worker reads your words and makes that change: \"{text[:160]}\"."},
                        {"title": "Investigate and tell me first", "what": "The worker finds the cause and writes a plan; nothing changes until you say yes."}]}


def flag(j, text: str, market: str = "crypto", screen: str = "", route: str = "", post=None, use_ai: bool = True) -> dict:
    """File the request now and offer the fixes. Returns the request number, the diagnosis and the options with their lanes."""
    from jarvis.service import requests_log

    _table(j)
    market = "india" if str(market).lower().startswith("ind") else "crypto"
    text = (text or "").strip()
    if not text:
        raise ValueError("say what is wrong")
    where = f"[{'Indian market' if market == 'india' else 'Crypto'} · {screen or route or 'app'}] "
    req = requests_log.add(j, "bug", where + text, about=f"flag:{market}:{screen or route}"[:120], by="owner")
    num = req["num"]
    old = j.db.execute("SELECT options FROM fix_flow WHERE num=?", (num,)).fetchone()
    if old:                                                   # the same words again: the same request and its options
        return {"num": num, "duplicate": True, **json.loads(old[0])}
    cost = 0.0
    tri = None
    if use_ai and _spent_today(j) < TRIAGE_DAILY:
        try:
            tri, cost = _ask_ai(PROMPT.format(market=market, screen=screen or "?", route=route or "?", text=text[:800]), post=post)
        except Exception as exc:  # noqa: BLE001 - the plain choices still work
            tri = {**_fallback(text), "ai_error": str(exc)[:120]}
    tri = tri if tri and tri.get("options") else _fallback(text)
    opts = []
    for o in tri["options"][:3]:
        title, what = str(o.get("title", ""))[:80], str(o.get("what", ""))[:300]
        ln = "DECISION" if title.lower().startswith("needs your decision") else lane_of(text, title, what)
        opts.append({"title": title, "what": what, "lane": ln,
                     "does": "I'll fix it, test it and put it live, then tell you" if ln == "SAFE" else "Near trading: I'll write the plan and wait for your yes"})
    body = {"diagnosis": str(tri.get("diagnosis", ""))[:300], "options": opts}
    now = int(time.time())
    j.db.execute(f"INSERT OR REPLACE INTO fix_flow ({', '.join(COLS)}) VALUES ({', '.join('?' * len(COLS))})",
                 (num, market, screen[:80], route[:120], lane_of(text), json.dumps(body), None, "triaged",
                  json.dumps([[now, "flagged; options offered"]]), cost, None, None, now, now))
    j.db.commit()
    return {"num": num, "say": f"Flagged as request {num}. Choose how to fix it.", **body}


def choose(j, num: int, option: int, words: str = "") -> dict:
    """Madhav picked option `option` (0-based). SAFE -> queued for the worker; DECISION -> plan only."""
    from jarvis.service import requests_log

    _table(j)
    row = get(j, num)
    if not row:
        raise ValueError(f"no flag {num}")
    if row["state"] not in ("triaged", "needs_decision", "failed"):
        raise ValueError(f"request {num} is already {STATE_WORDS.get(row['state'], row['state'])}")
    opts = row["options"]["options"]
    if not 0 <= option < len(opts):
        raise ValueError("pick one of the offered fixes")
    o = opts[option]
    lane = "DECISION" if "DECISION" in (o["lane"], lane_of(words)) else "SAFE"
    state = "queued" if lane == "SAFE" else "plan"
    _log(j, num, f"Madhav chose: {o['title']}" + (f" ({words[:200]})" if words else ""), state=state, lane=lane, choice=option)
    requests_log.set_status(j, num, "PLANNED", f"Madhav chose: {o['title']}. {o['what']}" + (f" His words: {words[:200]}" if words else "")
                            + (" The repair worker builds, tests and deploys it, then reports back." if lane == "SAFE"
                               else " Near trading: the worker writes a plan only; nothing changes without his yes."))
    return {"num": num, "state": state, "lane": lane, "say": f"Request {num}: {STATE_WORDS[state]}. I'll tell you when it's done."}


def _log(j, num: int, line: str, **set_) -> None:
    row = j.db.execute("SELECT log FROM fix_flow WHERE num=?", (num,)).fetchone()
    log = json.loads(row[0]) if row and row[0] else []
    log.append([int(time.time()), line[:400]])
    cols = {"log": json.dumps(log[-40:]), "updated_t": int(time.time()), **set_}
    j.db.execute(f"UPDATE fix_flow SET {', '.join(f'{k}=?' for k in cols)} WHERE num=?", (*cols.values(), num))
    j.db.commit()


def report(j, num: int, state: str, line: str, commit: str | None = None, cost: float = 0.0, branch: str | None = None) -> dict:
    """The repair worker moves a flag on; the request's status follows, and the phone hears about DONE / PLANNED / WONT."""
    from jarvis.service import requests_log

    assert state in STATES, state
    row = get(j, num)
    set_ = {"state": state, "cost_usd": round((row or {}).get("cost_usd") or 0.0, 4) + round(cost, 4)}
    if commit:
        set_["commit_sha"] = commit
    if branch:
        set_["branch"] = branch
    _log(j, num, line, **set_)
    if state == "deployed":
        requests_log.set_status(j, num, "DONE", f"Fixed and live: {line}" + (f" (commit {commit[:7]})" if commit else ""))
    elif state in ("needs_decision", "failed"):
        requests_log.set_status(j, num, "PLANNED", f"{STATE_WORDS[state].capitalize()}: {line}")
    return get(j, num)


def get(j, num: int) -> dict | None:
    _table(j)
    r = j.db.execute(f"SELECT {', '.join(COLS)} FROM fix_flow WHERE num=?", (int(num),)).fetchone()
    if not r:
        return None
    d = dict(zip(COLS, r))
    d["options"] = json.loads(d["options"] or "{}")
    d["log"] = json.loads(d["log"] or "[]")
    d["state_words"] = STATE_WORDS.get(d["state"], d["state"])
    return d


def pending(j, states=("queued", "plan")) -> list[dict]:
    _table(j)
    q = ",".join("?" * len(states))
    return [get(j, n) for (n,) in j.db.execute(f"SELECT num FROM fix_flow WHERE state IN ({q}) ORDER BY t", states)]


def board(j, limit: int = 60) -> list[dict]:
    """Every request, newest first, with its flag flow when it has one (the app's 'My flags' screen)."""
    from jarvis.service import requests_log

    _table(j)
    out = []
    for r in requests_log.list_(j)[:limit]:
        f = get(j, r["num"])
        out.append({**r, "flow": f})
    return out
