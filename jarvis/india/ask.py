"""Ask Ananta, Indian market (V2, first version, 23 Oct): the same chat the crypto app uses, answering only from India's read model.
How it works
  * The model never answers from its own head: every question goes with a FACTS block (the read model, trimmed) and the rules; it answers in
    the crypto Ask's three layers (answer / breakdown / evidence) plus follow-ups, as JSON, so the app renders it unchanged.
  * No lookups yet (the read model is small enough to send whole); India lookups over the registry and the exit book come next.
  * Claude through the same API the crypto Ask uses (key from the agent's .env, never printed); a daily cap; threads kept as files under
    <data>/ask/ on the Mac. Phase 1 has NO actions: a request to act is answered with "paper only; nothing is placed from chat".
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
import uuid
from pathlib import Path

import requests

from jarvis.india import views

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
ASK_DIR = DATA / "ask"
ENV_FILE = Path(os.getenv("ANANTA_AGENT_ENV", "/Users/vamsie/code/ananta-decision-agent/.env"))
MODEL = os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5")
DAILY_LIMIT = int(os.getenv("ASK_DAILY_LIMIT", "150"))
HISTORY_TURNS = 8
SYSTEM = """You are Ananta, Madhav's trading assistant for the INDIAN market (NSE stocks and the Nifty index), on paper only. Address him as "sir".
Answer ONLY from the FACTS block in the user turn; it is India's read model for the latest session (and, for Madhav, "account_allocation": his holdings graded A-D and ranked, the suggested changes, the paper moves and what is being watched; quote its grades, actions and "wrong_if" exactly). Never invent a number, a stock or a reason.
If the facts do not hold the answer, say so plainly and say what the facts do hold. Nothing here is financial advice; no real money is traded;
you cannot place, change or close anything from chat (say "paper only; nothing is placed from chat" if asked to act).
Explain technical words with a plain meaning alongside the name (simplify the explanation, not the intelligence). Be brutally honest: a lost
session is lost, a wrong call is wrong, 0 of 3 is 0 of 3. Keep the answer to 2-5 sentences a person can read in under ten seconds.
Reply with ONE JSON object and nothing else: {"kind":"answer","stage":"observation|outcome|learning","answer":"...","breakdown":["...","..."],
"evidence":["<fact and where it comes from>", ...],"assumption":"","follow_ups":["short question","short question","short question"],
"next_action":{"label":"","why":"","route":""},"show":[],"options":[],"route":"india"}.
If the question is unclear, use "kind":"clarify" with 2-4 "options". If it is off-topic, answer briefly as "kind":"outside" without facts."""


def _load_env_key() -> str:
    k = os.getenv("ANTHROPIC_API_KEY", "")
    if k or not ENV_FILE.exists():
        return k
    for line in ENV_FILE.read_text().splitlines():
        m = re.match(r"\s*(?:export\s+)?ANTHROPIC_API_KEY\s*=\s*(.*?)\s*$", line)
        if m:
            v = m.group(1)
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            os.environ["ANTHROPIC_API_KEY"] = v
            return v
    return ""


# ---------------------------------------------------------------------------------------------------------------- facts

def facts(owner: bool = False) -> dict:
    """The read model, trimmed to what a question can use (about 3-4k tokens). The owner's facts also carry the account allocation plan."""
    rm = views.readmodel()
    d = rm.get("decisions_today") or {}
    sb = rm.get("stock_book") or {}
    L = rm.get("learning") or {}
    lg = L.get("league") or {}
    r = rm.get("research") or {}
    j = rm.get("jobs") or {}
    pos = views.open_positions()
    marks = views.exec_marks()
    return {"data_through": rm.get("data_through"), "next_session": rm.get("next_session"), "built_at": rm.get("built_at"), "brief": rm.get("brief"),
            "market": {k: (rm.get("market") or {}).get(k) for k in ("nifty_close", "nifty_vs_sma50", "nifty_vs_sma200", "trend_state", "vix_close", "breadth_200d_liquid", "words")},
            "daily_call": {k: (rm.get("call") or {}).get(k) for k in ("call", "rule", "scored", "hits", "null_hits")},
            "stock_book": {"rules": sb.get("rules"), "open_positions": sb.get("open_positions"), "scale": "Rs 50,000 notional a trade (research scale), every registered exit tracked; the reference exit shown is hold_20d",
                           "by_campaign": {c: {k: m.get(k) for k in ("open", "closed", "realised_inr", "open_unrealised_inr", "win_rate")} for c, m in marks.items()},
                           "campaign_meaning": views.CAMPAIGN_WHY, "top_positions": [{"symbol": p["coin"], "campaign": p["campaign"], "since": p["since"], "pnl_pct": p["pnl_pct"]} for p in pos[:12]],
                           "recent_closed": [{"symbol": c["coin"], "campaign": c["campaign"], "net_inr": c["net_usd"], "why": c["why"], "exit_date": c["exit_date"]} for c in views.closed_trades(8)]},
            "decisions_for_next_session": {"rules": d.get("rules"), "decided_at": d.get("decided_at"), "candidates": d.get("candidates"),
                                           "chosen": [{"symbol": x.get("symbol"), "campaign": x.get("campaign"), "close": x.get("close"), "why": x.get("why")} for x in d.get("chosen", [])]},
            "index_line_sp1": {"capital_inr": 60000, **{k: (rm.get("sp1") or {}).get(k) for k in ("status", "words", "decisions", "errors")}, "sessions": ((rm.get("sp1") or {}).get("book") or {}).get("sessions")},
            "reference_traders_league": {"h1": lg.get("h1"), "informed": lg.get("informed"), "meaning": "HINDSIGHT = best trips the session offered; RANDOM = chance; MARKET = the liquid 250; coverage = of the top 20 trips, how many Ananta took / passed / had no rule for"},
            "missed_movers": (L.get("missed") or {}).get("line"), "drafts": L.get("drafts"),
            "research": {"studies": r.get("studies"), "gate_G02": r.get("gate"), "gate_counters": r.get("gate_counters"), "registry_verdicts": r.get("verdicts"), "exit_book_chosen": (r.get("exit_book") or {}).get("chosen")},
            "jobs": {"signin": j.get("signin"), "problems": [{"job": x["label"], "problems": x["problems"]} for x in j.get("jobs", []) if not x.get("ok")]},
            "guardrails": (rm.get("guardrails") or {}).get("words"), "missing_sections": rm.get("missing"),
            "reconstruction_last_night": {k: (rm.get("reconstruction") or {}).get(k) for k in ("headline", "people_words", "not_done_words", "league_words", "reviews", "findings")} | {"staircase": ((rm.get("reconstruction") or {}).get("staircase") or {}).get("words"),
                                          "meaning": "the nightly reconstruction card (what the market and other participants did, what Ananta did and did not do, trade reviews, findings); SAFE findings go to the repair board by themselves, DECISION findings wait for Madhav; the staircase says what the allocated capital may use (ADMITTED only; nothing yet)"},
            **({"account_allocation": _alloc_facts()} if owner else {})}


def _alloc_facts() -> dict:
    p = views.allocation_plan(full=True)
    if not p.get("ready"):
        return {"ready": False, "words": p.get("headline")}
    return {"mode": p["mode"], "headline": p["headline"], "paper": True, "sleeves": p["sleeves"], "regime_table_now": p.get("regime"), "options_sleeve": p.get("options"),
            "holdings_ranked": [{"rank": x["rank"], "symbol": x["symbol"], "grade": x["grade"], "score": x["score"], "action": x["action"], "value_inr": x["value_inr"], "weight_pct": x["weight_pct"],
                                 "pnl_pct": x["pnl_pct"], "suggest_inr": x["suggest_inr"], "why": x["why"], "wrong_if": x["wrong_if"]} for x in p.get("holdings", [])],
            "paper_moves_today": p.get("moves"), "moves_applied": p.get("moves_applied"), "watching": p.get("watch"), "snapshot": p.get("snapshot"),
            "meaning": "advisory = options fixed at Rs 50,000, stocks as in the account, Ananta rates/ranks/suggests and moves nothing; autonomous = Ananta moves capital between stocks, options and cash on paper inside the regime table; grades A>=70, B>=55, C>=40, D below"}


# ---------------------------------------------------------------------------------------------------------------- threads

def _tpath(thread: str) -> Path:
    return ASK_DIR / f"{thread}.jsonl"


def thread_messages(thread: str) -> list[dict]:
    try:
        return [json.loads(x) for x in _tpath(thread).read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def _index() -> list[dict]:
    try:
        return [json.loads(x) for x in (ASK_DIR / "threads.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def _touch_index(thread: str, title: str, voice: bool) -> None:
    ASK_DIR.mkdir(parents=True, exist_ok=True)
    old = next((r for r in _index() if r.get("thread") == thread), {})
    rows = [r for r in _index() if r.get("thread") != thread]
    n = sum(1 for m in thread_messages(thread) if m.get("role") == "user")
    now = time.time()
    rows.append({"thread": thread, "title": old.get("title") or title, "time": dt.datetime.fromtimestamp(now).strftime("%b %-d, %-I:%M %p"), "messages": n, "t": int(now), "voice": voice,
                 **({"pending_flag": old["pending_flag"]} if old.get("pending_flag") else {})})
    (ASK_DIR / "threads.jsonl").write_text("\n".join(json.dumps(r) for r in rows[-200:]) + "\n")


def threads() -> list[dict]:
    return sorted(_index(), key=lambda r: -r["t"])[:20]


def last() -> dict:
    rows = threads()
    if not rows:
        return {"last": None, "continue_minutes": 30}
    r = rows[0]
    return {"last": {**r, "minutes_ago": round((time.time() - r["t"]) / 60, 1), "talking_to": None}, "continue_minutes": 30}


def today_count() -> int:
    day = dt.date.today().isoformat()
    n = 0
    for r in _index():
        if dt.datetime.fromtimestamp(r["t"]).date().isoformat() == day:
            n += r.get("messages", 0)
    return n


def _append(thread: str, row: dict) -> None:
    ASK_DIR.mkdir(parents=True, exist_ok=True)
    with _tpath(thread).open("a") as f:
        f.write(json.dumps(row) + "\n")


def export(thread: str) -> str:
    out = []
    for m in thread_messages(thread):
        out.append(("You: " + m.get("text", "")) if m.get("role") == "user" else ("Ananta: " + str(m.get("answer") or m.get("error") or "")))
    return "\n\n".join(out)


def delete_thread(thread: str) -> dict:
    try:
        _tpath(thread).unlink()
    except OSError:
        pass
    rows = [r for r in _index() if r.get("thread") != thread]
    (ASK_DIR / "threads.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return {"ok": True}


def rate(mid: str, rating: int) -> dict:
    for p in ASK_DIR.glob("*.jsonl"):
        if p.name == "threads.jsonl":
            continue
        rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        hit = False
        for r in rows:
            if r.get("id") == mid:
                r["rating"] = rating
                hit = True
        if hit:
            p.write_text("".join(json.dumps(r) + "\n" for r in rows))
            return {"ok": True}
    return {"ok": False}


# ---------------------------------------------------------------------------------------------------------------- the model

def _claude(system: str, history: list[dict], user: str, post=None) -> tuple[str, dict]:
    key = _load_env_key()
    if not key:
        raise RuntimeError("no model key on this service")
    msgs = [{"role": m["role"], "content": m["text"]} for m in history] + [{"role": "user", "content": user}]
    body = {"model": MODEL, "max_tokens": 1200, "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}], "messages": msgs}
    post = post or (lambda url, headers, body: requests.post(url, headers=headers, json=body, timeout=90).json())
    r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body)
    if r.get("error"):
        raise RuntimeError(str(r["error"].get("message", r["error"]))[:160])
    text = "".join(c.get("text", "") for c in (r.get("content") or []) if c.get("type") == "text")
    u = r.get("usage") or {}
    return text, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0) or 0, "model": MODEL}


def _sections(text: str) -> dict:
    """A markdown reply despite the rules: the first part is the answer; **breakdown** / **evidence** / **follow-ups** lists become the layers."""
    parts = re.split(r"\n\s*\*\*(breakdown|evidence|follow[- ]?ups?|next)\*\*\s*\n", text, flags=re.I)
    d = {"kind": "answer", "answer": parts[0].strip()[:1200]}
    for i in range(1, len(parts) - 1, 2):
        key = parts[i].lower()
        items = [re.sub(r"^[-*•]\s*", "", ln).strip() for ln in parts[i + 1].splitlines() if ln.strip()]
        if key.startswith("break"):
            d["breakdown"] = items
        elif key.startswith("evid"):
            d["evidence"] = items
        elif key.startswith("follow"):
            d["follow_ups"] = [x.strip("?") + "?" for x in items][:4]
    return d


def _parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        d = json.loads(m.group(0) if m else text)
    except (ValueError, AttributeError):
        d = _sections(text)
    d.setdefault("kind", "answer")
    d.setdefault("stage", "observation")
    d.setdefault("answer", "")
    for k in ("breakdown", "evidence", "follow_ups", "show", "options", "points", "actions", "ui"):
        if not isinstance(d.get(k), list):
            d[k] = []
    d.setdefault("assumption", "")
    d.setdefault("next_action", {})
    d.setdefault("route", "india")
    return d


def _offline(question: str, f: dict, why: str) -> dict:
    """No model (no key, a refused call): the read model's own sentences, so the chat still answers honestly."""
    return {"kind": "answer", "stage": "observation", "answer": " ".join((f.get("brief") or [])[:3]) or "The India read model has not been built yet.",
            "breakdown": [f"Daily call: {(f.get('daily_call') or {}).get('call')} ({(f.get('daily_call') or {}).get('hits')} of {(f.get('daily_call') or {}).get('scored')} right)",
                          f"Stock book: {(f.get('stock_book') or {}).get('open_positions')} open positions", f"Index line: {(f.get('index_line_sp1') or {}).get('words')}"],
            "evidence": [f"readmodel/latest.json, data through {f.get('data_through')}"], "assumption": "", "follow_ups": ["What did you decide for the next session?", "Is every job running?", "What is the Nifty trend?"],
            "next_action": {}, "show": [], "options": [], "points": [], "actions": [], "ui": [], "route": "india", "note": f"answered from the read model only: {why}"}


ACT = re.compile(r"\b(buy|sell|place|book|exit|close|order|short)\b", re.I)


def ask(who: str, text: str, thread: str | None = None, mode: str | None = None, context: dict | None = None, voice: bool = False, post=None,
        token: str | None = None, flag_post=None, flag_get=None) -> dict:
    text = (text or "").strip()[:2000]
    if not text:
        raise ValueError("empty question")
    if today_count() >= DAILY_LIMIT:
        raise ValueError(f"daily question limit reached ({DAILY_LIMIT}); it resets in 24 hours")
    thread = thread or uuid.uuid4().hex[:12]
    fixed = allocation_flow(text, who) or fix_flow(text, thread, token, context, post=flag_post, get=flag_get)      # a mode switch, or a problem, a pick or "my flags": in code
    if fixed is not None:
        uid = uuid.uuid4().hex[:12]
        _append(thread, {"id": uid, "role": "user", "text": text, "t": int(time.time()), "voice": voice})
        rid = uuid.uuid4().hex[:12]
        row = {"id": rid, "role": "assistant", "t": int(time.time()), "provider": "rule", "ms": 0, "rating": None, **fixed, "model_label": "Ananta (rules)", "mode": mode or "auto", "cost_usd": 0.0, "thread": thread}
        _append(thread, row)
        _touch_index(thread, text[:60], voice)
        return {**row, "timing": {"ms": 0}}
    hist = [{"role": m["role"], "text": m["text"] if m["role"] == "user" else json.dumps({k: m.get(k) for k in ("answer", "breakdown")})} for m in thread_messages(thread)[-2 * HISTORY_TURNS:]]
    uid = uuid.uuid4().hex[:12]
    _append(thread, {"id": uid, "role": "user", "text": text, "t": int(time.time()), "voice": voice})
    f = facts(owner=(who == "owner" or not str(who).startswith("guest:")))
    t0 = time.time()
    if ACT.search(text) and re.search(r"\b(now|please|for me|this|it|today)\b", text, re.I) and len(text) < 90:
        reply = {"kind": "answer", "stage": "observation", "answer": "Paper only, sir: nothing is placed, changed or closed from chat. The stock book and the index line decide by their rules, and every decision is in the Home feed.",
                 "breakdown": [], "evidence": ["India leakcheck: no order path exists in this service"], "assumption": "", "follow_ups": ["What did you decide for the next session?", "What are the guardrails?"],
                 "next_action": {}, "show": [], "options": [], "points": [], "actions": [], "ui": [], "route": "india"}
        usage = {"model": "rule"}
    else:
        user = f"QUESTION: {text}\n\nFACTS (India read model, data through {f.get('data_through')}):\n{json.dumps(f, default=str)}\n\nReply with the JSON object only: begin with {{ and end with }}, no markdown, no text outside it."
        try:
            raw, usage = _claude(SYSTEM, hist, user, post=post)
            reply = _parse(raw)
        except Exception as e:  # noqa: BLE001
            reply = _offline(text, f, str(e)[:120])
            usage = {"model": "none"}
    ms = int((time.time() - t0) * 1000)
    rid = uuid.uuid4().hex[:12]
    row = {"id": rid, "role": "assistant", "t": int(time.time()), "provider": "claude" if usage.get("model") not in ("rule", "none") else usage.get("model"), "ms": ms, "rating": None, **reply,
           "model_label": "Claude Sonnet" if usage.get("model") not in ("rule", "none") else "Ananta (rules)", "mode": mode or "auto", "cost_usd": round((usage.get("in", 0) * 3 + usage.get("out", 0) * 15) / 1e6, 5),
           "usage": usage, "thread": thread}
    _append(thread, row)
    _touch_index(thread, text[:60], voice)
    return {**row, "id": rid, "thread": thread, "timing": {"ms": ms}}


def thread_view(thread: str) -> list[dict]:
    out = []
    for m in thread_messages(thread):
        if m.get("role") == "user":
            out.append({"id": m.get("id"), "role": "user", "text": m.get("text"), "voice": bool(m.get("voice"))})
        else:
            out.append({k: v for k, v in m.items() if k not in ("usage",)})
    return out


def stats() -> dict:
    rows = _index()
    return {"threads": len(rows), "questions": sum(r.get("messages", 0) for r in rows), "today": today_count(), "limit": DAILY_LIMIT, "model": MODEL}


# ---------------------------------------------------------------------------------------------------------------- the fix flow, by voice or chat (Madhav, 23 Oct)
# "Ananta voice agent should be able to do the whole process, not a separate flag button": a problem said to Ananta is filed on the shared
# repair board (the sign-in service's fix flow, with his own token), the fixes come back as numbered choices, he picks one by voice or tap,
# and the repair worker builds the safe ones and tells him. Rules in code, no model call.
JARVIS_URL = os.getenv("ANANTA_JARVIS_URL", "http://127.0.0.1:8100")
FLAG = re.compile(r"\b(flag|broken|not working|doesn'?t work|isn'?t working|fix (it|this|that|the)|bug|wrong|report (it|this|that))\b", re.I)
PICK = re.compile(r"^\s*(?:fix\s*)?(?:option\s*)?(\d)\b|^\s*(?:the\s+)?(first|second|third|one|two|three)\b", re.I)
STATUS = re.compile(r"\b(my (flags?|requests?)|what happened to (my|the) (flag|request)|is it fixed|did you fix)\b", re.I)
WORDS = {"first": 1, "one": 1, "second": 2, "two": 2, "third": 3, "three": 3}


def _pending(thread: str) -> dict | None:
    for r in _index():
        if r.get("thread") == thread and r.get("pending_flag"):
            return r["pending_flag"]
    return None


def _set_pending(thread: str, flag: dict | None) -> None:
    ASK_DIR.mkdir(parents=True, exist_ok=True)
    rows = _index()
    if not any(r.get("thread") == thread for r in rows):
        rows.append({"thread": thread, "title": "", "time": "", "messages": 0, "t": int(time.time()), "voice": False})
    for r in rows:
        if r.get("thread") == thread:
            r["pending_flag"] = flag
    (ASK_DIR / "threads.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def _reply(answer: str, follow_ups: list[str], evidence: list[str], extra: dict | None = None) -> dict:
    return {"kind": "answer", "stage": "observation", "answer": answer, "breakdown": [], "evidence": evidence, "assumption": "", "follow_ups": follow_ups[:4],
            "next_action": {}, "show": [], "options": [], "points": [], "actions": [], "ui": [], "route": "india", **(extra or {})}


ALLOC_AUTO = re.compile(r"(\b(everything|all of it|allocation|the capital|my capital|the money|portfolio)\s+(is\s+|to be\s+|should be\s+)?autonomous\b|\b(go|switch|set|make|turn|put)\b[^.?!]{0,40}\bautonomous\b|\b(you|ananta)\s+(decide|manage|handle|move)\b[^.?!]{0,30}\b(allocation|capital|money|split|everything)\b)", re.I)
ALLOC_ADV = re.compile(r"\b(advisory|suggest only|only suggest|stop (moving|managing) (the )?(capital|money)|back to (advisory|suggestions))\b", re.I)
ALLOC_Q = re.compile(r"^\s*(what|how|why|explain|tell me|does|is it)\b", re.I)


def allocation_flow(text: str, who: str) -> dict | None:
    """'Everything is autonomous' / 'go back to advisory', by voice or chat: sets the allocation mode in code (owner only, paper only)."""
    if ALLOC_Q.search(text):
        return None
    mode = "autonomous" if ALLOC_AUTO.search(text) else ("advisory" if ALLOC_ADV.search(text) else None)
    if mode is None:
        return None
    if not (who == "owner" or not str(who).startswith("guest:")):
        return _reply("Only Madhav can change how capital is allocated.", [], [])
    import datetime as _dt
    p = DATA / "paper" / "allocation.json"
    cur = {}
    try:
        cur = json.loads(p.read_text())
    except (OSError, ValueError):
        pass
    rec = {"mode": mode, "options_inr": cur.get("options_inr") or 50000.0, "set_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "set_by": who, "paper": True,
           "note": "set by voice or chat"}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, indent=1))
    if mode == "autonomous":
        ans = ("Done, sir: allocation is autonomous, on paper. From the next plan (within minutes, then each evening) I set the split between stocks, options and cash from the market's regime, "
               "move capital between them by the table (at most 10% of the pool a session, never under Rs 2,000), keep every move in the ledger, and keep watching the market and your positions for changes and new chances. "
               "Nothing is sent to your broker; real orders wait for the gate and your yes.")
        fu = ["What will you move first?", "What are you watching?", "Go back to advisory"]
    else:
        ans = ("Done, sir: back to advisory. Options stay fixed at Rs 50,000, stocks stay as they are in your account, and I rate and rank every holding and suggest changes. I move nothing.")
        fu = ["Rate my holdings", "What would you change first?", "Go autonomous"]
    return _reply(ans, fu, ["allocation setting saved to paper/allocation.json"], {"route": "india"})


def fix_flow(text: str, thread: str, token: str | None, context: dict | None, post=None, get=None) -> dict | None:
    """Returns a reply when the message is about a problem, a pick, or the flags' status; None otherwise (the model answers)."""
    if not token:
        return None
    H = {"Authorization": f"Bearer {token}", "X-Ananta-Quiet": "1"}
    post = post or (lambda url, body: requests.post(url, json=body, headers=H, timeout=60))
    get = get or (lambda url: requests.get(url, headers=H, timeout=30))
    pend = _pending(thread)
    m = PICK.match(text) if pend else None
    if pend and m:
        n = int(m.group(1)) if m.group(1) else WORDS.get(m.group(2).lower(), 0)
        if 1 <= n <= len(pend.get("options") or []):
            r = post(f"{JARVIS_URL}/v3/flags/{pend['num']}/choose", {"option": n - 1, "words": text[:200]})
            j = r.json() if hasattr(r, "json") else r
            state = j.get("state")
            _set_pending(thread, None)
            if state == "queued":
                a = f"Done, sir: fix {n} for request {pend['num']} is queued. The repair worker builds it, tests it and puts it live within minutes; you get 'Fixed: request {pend['num']}' on your phone."
            elif state == "plan":
                a = f"Noted, sir: fix {n} for request {pend['num']} is near trading, so the worker writes the plan and waits for your yes. Nothing changes until then."
            else:
                a = f"Request {pend['num']}: {state or j.get('detail') or 'recorded'}."
            return _reply(a, ["What happened to my flag?", "What did you decide for the next session?"], [f"fix flow: request {pend['num']}, option {n}, state {state}"])
    if STATUS.search(text):
        r = get(f"{JARVIS_URL}/v3/flags")
        j = r.json() if hasattr(r, "json") else r
        flags = [f for f in (j.get("flags") or []) if str(f.get("market", "")).startswith("ind") or "Indian market" in str(f.get("text", ""))][:5] or (j.get("flags") or [])[:5]
        if not flags:
            return _reply("No flags on the board yet, sir.", ["What did you decide for the next session?"], ["fix flow board: empty"])
        lines = "; ".join(f"request {f.get('num')}: {str(f.get('state') or f.get('status') or '?')} - {str(f.get('text') or '')[:60]}" for f in flags)
        return _reply(f"Your flags, sir: {lines}.", ["Flag something else", "What did you decide for the next session?"], [f"fix flow board: {len(flags)} shown"])
    if FLAG.search(text) and len(text) >= 8:
        screen = str((context or {}).get("here", {}).get("label") if isinstance((context or {}).get("here"), dict) else (context or {}).get("screen") or "")[:80]
        r = post(f"{JARVIS_URL}/v3/flags", {"text": text[:600], "market": "india", "screen": screen, "route": "ask"})
        j = r.json() if hasattr(r, "json") else r
        if not j.get("num"):
            return _reply(f"I could not file that, sir: {str(j.get('detail') or j)[:120]}", [], [])
        opts = j.get("options") or []
        lines = [f"{i + 1}. {o.get('title')} - {'I fix it and put it live' if o.get('lane') == 'SAFE' else 'near trading: a plan for your yes'}" for i, o in enumerate(opts)]
        _set_pending(thread, {"num": j["num"], "options": [{"title": o.get("title"), "lane": o.get("lane")} for o in opts]})
        a = f"Flagged as request number {j['num']}, sir. " + (f"{j.get('diagnosis')} " if j.get("diagnosis") else "") + ("Fixes: " + " ".join(lines) + " Say a number or tap one." if lines else "I'll tell you when it's fixed.")
        return _reply(a, [f"Fix {i + 1}: {o.get('title')}" for i, o in enumerate(opts)], [f"fix flow: request {j['num']} filed on the shared board"], {"flag": j})
    return None
