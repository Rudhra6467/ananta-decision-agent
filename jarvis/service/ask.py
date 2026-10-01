"""Ask Ananta: the conversational layer over the Ananta system (phase 1: ask and explain, read-only).

How it works
  * The model never answers from its own head: it calls LOOKUPS (functions below) over Ananta's own data and
    answers only from what they return.
  * Providers are swappable: Gemini (free tier) and Claude (Anthropic API). Same lookups, same rules, so the
    two can be compared on real questions (feedback thumbs + latency are logged per provider).
  * Every answer comes in three layers at once: answer (just tell me), breakdown (break it down), evidence
    (show me the evidence), plus a stage label (observation ... learning).
  * Unclear question -> "Did you mean" options; after 2 failed tries -> says it did not understand + examples.
    Off-topic -> polite "not my area". Misunderstandings are logged for review.
  * Phase 1 has NO actions: requests to act get "I can't do that from chat yet" and point to the Cockpit.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any, Callable

from jarvis.service import views

MAX_TOOL_ROUNDS = 8
HISTORY_TURNS = 8
DAILY_LIMIT = int(os.getenv("ASK_DAILY_LIMIT", "150"))
GEMINI_MODEL = os.getenv("ASK_GEMINI_MODEL", "gemini-2.5-flash")
CLAUDE_MODEL = os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """You are Ananta, the trading operator for one owner (Vamsi). You speak like a calm, knowledgeable trading desk operator: simple words first, numbers second, no hype.

WHAT ANANTA IS (use these words)
- Paper only. No real money, no exchange connected. Market: crypto spot, 10 coins (BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP), buying only, NDAX costs (0.20% fee + spread per side).
- Watches (processes that keep running):
  * The 15-minute Explorer: checks 10 coins every 15 minutes for setups E1-E5 and trades them on paper ($100 each, own stop/target/warning bells). Trade types: Long-term (weeks), Short-term (days), Intraday (hours). Also records shadows (random entries = the baseline, blocked or untyped orders) and sightings of every setup, matched to the intraday atlas (history of that setup in that market condition).
  * The hourly watch: runs the strategies Hunter (reversal at support) and Squeeze (compression breakout) in the backend. Hunter is rare: about 2-8 times per coin per year. Its strategy book is called SD6.
- Strategies: Hunter and Squeeze (hourly watch); Continuation is benched (shadow only); Explorer setups E1 Pullback in an uptrend, E2 Breakout after a quiet period, E3 Bounce at support, E4 Momentum continuation, E5 Squeeze breakout; E6-E8 dip setups are watched, never traded; T3 is the portfolio trend strategy.
- Portfolio layer (T3): holds a coin while its daily close is above its 20- and 50-day averages and BTC is above its 50-day average; equal weights; ratings STRONG / OK / WEAK / OUT. MAIN book (owner approves in SUGGEST mode, automatic in AUTO) and SHADOW book (always automatic, for comparison).
- Repair shop: questions forwarded from evidence, pre-registered, tested on 2017-2023 then 2024-Jul 2026 data. Reviews 1-3 failed (no short-term entry beats costs), review 4 (T3) passed. The variable registry records what to KEEP / WATCH / DROP.
- Lifecycle words, always say which stage a thing is in: observation -> candidate setup (some conditions met) -> setup (all conditions met) -> decision (order placed or skipped) -> execution (filled) -> position -> outcome (closed) -> evaluation -> learning. Never let "interesting" sound like "bought".

RULES
1. Facts only from lookups. Call the lookups you need (several if needed) before answering. Never invent prices, trades, counts or history. If a lookup returns nothing, say the evidence is not there.
2. Keep separate: what the market is doing, what Ananta observed, which setup may be forming, which conditions are met or missing, what history says, what action (if any) is justified, whether anything was executed, the outcome, what was learned.
3. Uncertainty: small samples are small; say so (e.g. "1 day of live evidence"). No predictions or promises. Historical odds are odds, not forecasts.
4. Scope: trading, markets, the economy and news that moves markets, and Ananta itself. Anything else: kind "out_of_scope" with a one-line polite reply ("That's outside my area - I'm built for trading and markets.").
5. Actions: in this version you cannot change anything (no orders, no switches, no approvals). If asked to act, use kind "cannot_do_yet": say what you would need, and that the Cockpit or Portfolio screen can do switches and approvals now.
6. Unclear: if the question could mean different things that lead to different answers, use kind "clarify" with 2-4 short "Did you mean" options. If one reading is clearly most likely, answer it and state the assumption. Follow-ups ("why?", "and before that?") refer to the last topic.
7. If the conversation note says clarification already failed twice, do not ask again: use kind "not_understood" with 3 example questions you can answer.
8. Money: $ with 2 decimals; percentages with 1-2 decimals; times in Toronto time if given.

OUTPUT: reply with ONE JSON object and nothing else:
{"kind": "answer" | "clarify" | "not_understood" | "out_of_scope" | "cannot_do_yet",
 "stage": one lifecycle word or "" ,
 "answer": "1-3 plain sentences: the direct answer",
 "breakdown": ["3-7 short bullet strings: the reasoning, plain words"],
 "evidence": [{"label": "...", "value": "...", "source": "which lookup / record", "time": "when, if known"}],
 "assumption": "the reading you assumed, or empty",
 "options": ["for clarify only: short options"],
 "follow_ups": ["2-3 natural next questions"]}"""

OFF = {"type": "object", "properties": {}}


def _schema(props: dict, req: list | None = None) -> dict:
    return {"type": "object", "properties": props, **({"required": req} if req else {})}


COIN = {"type": "string", "description": "Coin symbol, e.g. ETH"}

TOOLS = [
    ("overview", "What Ananta is doing right now: watches, last checks, paper values, open trades, portfolio mode, kill switch, anything waiting for the owner.", OFF),
    ("market", "The market picture now for one coin or all 10: price, 1h/4h/daily trend, RSI, momentum, volume, support/resistance, BTC trend.", _schema({"coin": {**COIN, "description": "Optional coin; omit for all"}})),
    ("setups", "Explorer setups for a coin (or all coins): for each setup which conditions are met and which are missing right now, plus Hunter and Squeeze status from the hourly watch with the reasons they did not trigger.", _schema({"coin": {**COIN, "description": "Optional coin; omit for the closest candidates across all coins"}})),
    ("strategy", "Activity of a strategy over recent hours: hunter, squeeze, continuation, explorer (E1-E8) or t3/portfolio. Detections, near-misses, top reasons, trades.", _schema({"name": {"type": "string"}, "hours": {"type": "number"}}, ["name"])),
    ("trades", "Paper trades. status: open | closed | all. Optional coin. Includes entry, price, P&L, stop, target, exit reason, and what the shadow variants would have done.", _schema({"status": {"type": "string"}, "coin": COIN})),
    ("trade", "Full detail of one trade by its id (from trades): why it was bought, conditions at entry, exit plan, timeline, what-if variants.", _schema({"id": {"type": "string"}}, ["id"])),
    ("portfolio", "The T3 portfolio: value, return, holdings with cost and P&L, ratings and reasons, pending proposals, mode, comparison with buy-and-hold and the shadow book.", OFF),
    ("history", "What happened historically after a setup in the current market condition (intraday atlas, 2017-2026 5m data): odds of +3% before -1.5%, net after costs, typical 1h/4h/24h ranges. Give coin to use its current condition.", _schema({"setup": {"type": "string", "description": "E1-E8 or ANY"}, "coin": COIN})),
    ("evidence", "Evidence collected so far (counts, by setup, shadows, hourly looks, reconstruction match) and the repair shop: forwarded questions, verdicts, queue, repairs in use and how they are tracking.", OFF),
    ("knowledge", "Search Ananta's research and knowledge: repair shop reviews, rulebook, variable registry, studies. Use for 'what did we learn', 'why do we do X', 'has this been tested'.", _schema({"query": {"type": "string"}}, ["query"])),
    ("changes", "What changed / happened in the last N hours: buys, sells, orders, portfolio moves, warnings, owner actions.", _schema({"hours": {"type": "number"}})),
    ("report", "The latest daily or weekly report text.", _schema({"kind": {"type": "string", "description": "daily | weekly"}})),
]
TOOL_DESC = {n: d for n, d, _ in TOOLS}

HUNTER_REASONS = {
    "REJECTED_RSI_NOT_RESET": "RSI has not dropped enough to count as a reset",
    "REJECTED_NO_VCP_BASE": "no tight base (volatility contraction) under the price",
    "REJECTED_HTF_TREND_MISALIGNED": "the higher-timeframe trend points the other way",
    "REJECTED_NO_SUPPORT_ZONE": "no support zone nearby",
    "REGIME_FILTERED": "the market regime does not suit this strategy",
    "no_qualifying_setup": "no qualifying setup",
}


class Lookups:
    """Read-only functions over Ananta's data. Each returns plain JSON-able data."""

    def __init__(self, j):
        self.j = j
        self._ex = None

    @property
    def ex(self):
        if self._ex is None:
            self._ex = self.j._explorer()
        return self._ex

    def _eng(self, coin: str):
        if not self.ex:
            raise ValueError("the Explorer is not running")
        c = (coin or "").upper().replace("/USD", "")
        if c not in self.ex.st["engines"]:
            raise ValueError(f"unknown coin {coin}; Ananta watches {', '.join(self.ex.st['engines'])}")
        return c, self.ex.st["engines"][c]

    def _state(self, eng):
        T = eng.last_scan
        if T is None or not eng.ready():
            raise ValueError("this coin's engine is still warming up")
        return eng.state(T)

    def call(self, name: str, args: dict) -> Any:
        fn = getattr(self, "t_" + name, None)
        if fn is None:
            return {"error": f"no lookup named {name}"}
        try:
            return fn(**(args or {}))
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)[:300]}

    # ---- lookups ----
    def t_overview(self) -> dict:
        s = views.day_summary(self.j)
        c = views.cockpit(self.j)
        xs = self.ex.status() if self.ex else None
        return {"now_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(self.j.now())), "summary": s, "systems": c["systems"],
                "switches": {w["key"]: w["on"] for w in c["switches"]},
                "open_trades": [{k: t[k] for k in ("id", "coin", "setup", "type", "entry", "price", "pnl_usd", "suggestion", "why")} for t in (xs["open"] if xs else [])],
                "pending_orders": xs["pending_orders"] if xs else []}

    def t_market(self, coin: str | None = None) -> dict:
        coins = [coin] if coin else list(self.ex.st["engines"]) if self.ex else []
        out = {}
        for c in coins:
            cc, eng = self._eng(c)
            st = self._state(eng)
            d = views.sc.describe_state(st)
            d1 = list(eng.tf["1d"].bars)
            if len(d1) >= 2:
                d["change_24h_pct"] = round(100 * (eng.tf["5m"].last[4] / d1[-1][4] - 1), 2)
                d["change_7d_pct"] = round(100 * (eng.tf["5m"].last[4] / d1[-7][4] - 1), 2) if len(d1) >= 7 else None
            d["as_of_utc"] = time.strftime("%H:%M", time.gmtime(eng.last_scan))
            out[cc] = d
        return out

    def t_setups(self, coin: str | None = None) -> dict:
        hourly = views._hourly_strategies(self.j, hours=3)
        res: dict[str, Any] = {}
        coins = [coin] if coin else list(self.ex.st["engines"]) if self.ex else []
        for c in coins:
            cc, eng = self._eng(c)
            rows = views.sc.checklist(eng, self._state(eng))
            if not coin:
                rows = [r for r in rows if r["traded"] and r["met"] >= r["of"] - 1]
            res[cc] = {"explorer": [{"setup": r["setup"], "name": r["name"], "traded_by_explorer": r["traded"], "met": f"{r['met']}/{r['of']}",
                                     "complete": r["complete"], "missing": r["missing"],
                                     **({"conditions": r["conditions"]} if coin else {})} for r in rows],
                       "hourly_watch": {s: {**(v["latest"].get(cc) or {}),
                                            "reasons_plain": [HUNTER_REASONS.get(x, x) for x in ((v["latest"].get(cc) or {}).get("reasons") or []) if x]}
                                        for s, v in hourly.items()}}
        return {"note": "met = conditions true at the last 15-minute check. A setup is only traded when ALL are met (and a trade type fits).", "coins": res}

    def t_strategy(self, name: str, hours: float = 24) -> dict:
        n = name.lower()
        if n in ("hunter", "squeeze", "continuation", "trend_rider", "vcp"):
            hs = views._hourly_strategies(self.j, hours=hours)
            key = {"continuation": "trend_rider"}.get(n, n)
            s = hs.get(key) or hs.get(n)
            if not s:
                return {"strategy": n, "note": "no hourly-watch records for this strategy in the window", "available": list(hs)}
            s = dict(s)
            s["top_reasons_plain"] = {HUNTER_REASONS.get(k, k): v for k, v in s["top_reasons"].items()}
            return {"strategy": n, "hours": hours, **s, "paper_book_SD6": self._sd6()}
        if n in ("t3", "portfolio"):
            return self.t_portfolio()
        ev = views.evidence_collected(self.j)
        return {"strategy": "explorer", "by_setup": ev["collected"], "tracker": ev["tracker"][:7]}

    def _sd6(self) -> dict:
        hb = [h for h in views._jsonl(self.j.dir / "watch_heartbeat.jsonl", 50) if h.get("ok")]
        return (hb[-1].get("book") if hb else {}) or {}

    def t_trades(self, status: str = "open", coin: str | None = None) -> dict:
        out: dict[str, Any] = {}
        if not self.ex:
            return {"error": "Explorer not running"}
        if status in ("open", "all"):
            out["open"] = [t for t in self.ex.status()["open"] if not coin or t["coin"] == coin.upper()]
        if status in ("closed", "all"):
            rows = []
            for (js,) in self.ex.store.book.execute("SELECT json FROM events WHERE kind='CLOSED' ORDER BY seq DESC LIMIT 50"):
                e = json.loads(js)
                if coin and e["coin"] != coin.upper():
                    continue
                rows.append({"id": e["id"], "coin": e["coin"], "setup": e["setup"], "type": e["type"], "net_usd": e.get("net_usd"),
                             "exit": views.exit_text(e.get("bell")), "time": views._local(e["t"])})
            out["closed"] = rows
        out["hourly_watch_SD6_book"] = self._sd6()
        return out

    def t_trade(self, id: str) -> dict:  # noqa: A002
        d = views.trade_detail(self.j, id)
        d["chart"] = {"points": len(d["chart"]["points"])}
        return d

    def t_portfolio(self) -> dict:
        h = views.holdings(self.j)
        f = views.evidence_forwarded(self.j)
        t3 = next((x for x in f["in_use"] if x["id"] == "T3"), {})
        tr = dict(t3.get("tracking") or {})
        tr.pop("series", None)
        return {**h, "tracking_vs_buy_hold": tr, "expectation": t3.get("expect")}

    def t_history(self, setup: str = "ANY", coin: str | None = None) -> dict:
        p = self.j.dir / "intraday_atlas.json"
        if not p.exists():
            return {"error": "the intraday atlas is not available"}
        from src.research.intraday_atlas import lookup

        at = json.loads(p.read_text())
        s1 = b1 = None
        if coin:
            _, eng = self._eng(coin)
            st = self._state(eng)
            s1, b1 = st["S1"], st.get("btc_S1")
        hit = lookup(at, setup.upper(), s1, b1)
        if not hit:
            return {"error": f"no history for {setup}"}
        return {"setup": setup.upper(), "condition": {"coin_1h_trend": s1, "btc_1h_trend": b1}, "level": hit["level"],
                "history_2024_2026": hit["recent"], "positive_after_costs_in_both_periods": hit["stable_positive_after_costs"],
                "how_to_read": "p_target = share that reached the target before the stop; net_pct = average result after NDAX costs; ranges are 10th/50th/90th percentile moves in %. Brackets: e.g. '3/1.5_24h' = +3% target, -1.5% stop, 24 hours."}

    def t_evidence(self) -> dict:
        ev = views.evidence_collected(self.j)
        fw = views.evidence_forwarded(self.j)
        for x in fw["in_use"]:
            (x.get("tracking") or {}).pop("series", None)
        return {**ev, "in_use": fw["in_use"], "safety_changes": fw["safety_changes"]}

    def t_knowledge(self, query: str) -> dict:
        roots = [self.j.dir / "docs" / "repair_shop", self.j.dir / "docs" / "research"]
        files = [p for r in roots if r.exists() for p in r.glob("*.md")] + [self.j.dir / "docs" / "RULEBOOK_V0.md", self.j.dir / "docs" / "VARIABLE_REGISTRY.md"]
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2]
        hits = []
        for p in files:
            if not p.exists():
                continue
            text = p.read_text()
            paras = re.split(r"\n(?=#)|\n\n", text)
            for para in paras:
                low = para.lower()
                score = sum(low.count(w) for w in words)
                if score:
                    hits.append((score, p.name, para.strip()[:900]))
        hits.sort(key=lambda h: -h[0])
        reg = self.j.dir / "docs" / "variable_registry.json"
        regs = []
        if reg.exists():
            r = json.loads(reg.read_text())
            for v in r["variables"]:
                blob = json.dumps(v).lower()
                if any(w in blob for w in words):
                    regs.append(v)
        return {"passages": [{"file": f, "text": t} for _, f, t in hits[:6]], "registry": regs[:8]}

    def t_changes(self, hours: float = 24) -> dict:
        return {"hours": hours, "events": [{k: it.get(k) for k in ("time", "kind", "title", "body")} for it in views.feed(self.j, hours=hours, limit=40)]}

    def t_report(self, kind: str = "daily") -> dict:
        r = self.j._latest("explorer_weekly" if kind.startswith("w") else "explorer_daily")
        return r or {"error": f"no {kind} report yet"}


# ---------------------------------------------------------------------------
# providers (plain HTTPS, no SDKs)
# ---------------------------------------------------------------------------
def _post(url: str, headers: dict, body: dict, timeout: int = 90) -> dict:
    import requests

    r = requests.post(url, headers=headers, json=body, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    return r.json()


def run_claude(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post) -> tuple[str, dict]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    msgs = [{"role": m["role"], "content": m["text"]} for m in history] + [{"role": "user", "content": user}]
    tdefs = [{"name": n, "description": d, "input_schema": s} for n, d, s in TOOLS]
    usage = {"in": 0, "out": 0}
    for _ in range(MAX_TOOL_ROUNDS + 1):
        r = post("https://api.anthropic.com/v1/messages",
                 {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                 {"model": CLAUDE_MODEL, "max_tokens": 2000, "system": system, "tools": tdefs, "messages": msgs})
        u = r.get("usage") or {}
        usage["in"] += u.get("input_tokens", 0)
        usage["out"] += u.get("output_tokens", 0)
        content = r.get("content") or []
        calls = [c for c in content if c.get("type") == "tool_use"]
        if not calls:
            return "".join(c.get("text", "") for c in content if c.get("type") == "text"), usage
        msgs.append({"role": "assistant", "content": content})
        results = []
        for c in calls:
            out = tools.call(c["name"], c.get("input") or {})
            log.append({"tool": c["name"], "args": c.get("input")})
            results.append({"type": "tool_result", "tool_use_id": c["id"], "content": json.dumps(out, default=str)[:30000]})
        msgs.append({"role": "user", "content": results})
    raise RuntimeError("too many lookup rounds")


def _gemini_schema(s: dict) -> dict:
    if not s.get("properties"):
        return None
    return s


def run_gemini(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post) -> tuple[str, dict]:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["text"]}]} for m in history]
    contents.append({"role": "user", "parts": [{"text": user}]})
    decls = []
    for n, d, s in TOOLS:
        x = {"name": n, "description": d}
        if _gemini_schema(s):
            x["parameters"] = s
        decls.append(x)
    usage = {"in": 0, "out": 0}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    for _ in range(MAX_TOOL_ROUNDS + 1):
        r = post(url, {"x-goog-api-key": key, "content-type": "application/json"},
                 {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                  "tools": [{"functionDeclarations": decls}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4000}})
        u = r.get("usageMetadata") or {}
        usage["in"] += u.get("promptTokenCount", 0)
        usage["out"] += u.get("candidatesTokenCount", 0)
        cand = (r.get("candidates") or [{}])[0]
        content = cand.get("content") or {"role": "model", "parts": []}
        parts = content.get("parts") or []
        calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not calls:
            return "".join(p.get("text", "") for p in parts if not p.get("thought")), usage
        contents.append(content)          # returned as-is (keeps any thought signatures)
        resp = []
        for c in calls:
            out = tools.call(c["name"], c.get("args") or {})
            log.append({"tool": c["name"], "args": c.get("args")})
            js = json.dumps(out, default=str)
            res = json.loads(js) if len(js) <= 30000 else {"truncated": js[:30000]}
            resp.append({"functionResponse": {"name": c["name"], "response": {"result": res}}})
        contents.append({"role": "user", "parts": resp})
    raise RuntimeError("too many lookup rounds")


PROVIDERS: dict[str, Callable] = {"gemini": run_gemini, "claude": run_claude}


def parse(text: str) -> dict:
    """The model's JSON reply; lenient (code fences, text around it). Falls back to plain text."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            if isinstance(d, dict) and d.get("answer"):
                d.setdefault("kind", "answer")
                for k, default in (("breakdown", []), ("evidence", []), ("options", []), ("follow_ups", []), ("stage", ""), ("assumption", "")):
                    d.setdefault(k, default)
                if isinstance(d["breakdown"], str):
                    d["breakdown"] = [d["breakdown"]]
                return d
        except json.JSONDecodeError:
            pass
    return {"kind": "answer", "stage": "", "answer": t or "I could not form an answer.", "breakdown": [], "evidence": [],
            "assumption": "", "options": [], "follow_ups": []}


EXAMPLES = ["How is the market right now?", "What setups are close on ETH?", "How is the portfolio doing?", "What has Hunter been doing today?", "What did we learn from the repair shop?"]


class Ask:
    def __init__(self, j, providers: dict[str, Callable] | None = None):
        self.j = j
        self.providers = providers or PROVIDERS
        j.db.executescript("""
            CREATE TABLE IF NOT EXISTS ask_messages (id TEXT PRIMARY KEY, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT,
                provider TEXT, model TEXT, ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, tools TEXT, error TEXT, rating INTEGER);
            CREATE TABLE IF NOT EXISTS ask_misunderstood (t INTEGER, thread TEXT, question TEXT, kind TEXT, provider TEXT);
        """)

    def _history(self, thread: str) -> list[dict]:
        rows = self.j.db.execute("SELECT role, text, reply FROM ask_messages WHERE thread=? AND error IS NULL ORDER BY t DESC, rowid DESC LIMIT ?",
                                 (thread, HISTORY_TURNS * 2)).fetchall()[::-1]
        out = []
        for role, text, reply in rows:
            if role == "user":
                out.append({"role": "user", "text": text})
            else:
                r = json.loads(reply) if reply else {}
                brief = {k: r.get(k) for k in ("kind", "answer", "breakdown", "evidence", "options") if r.get(k)}
                out.append({"role": "assistant", "text": json.dumps(brief)[:4000]})
        while out and out[0]["role"] != "user":
            out.pop(0)
        return out

    def _failed_clarifies(self, thread: str) -> int:
        n = 0
        for (reply,) in self.j.db.execute("SELECT reply FROM ask_messages WHERE thread=? AND role='assistant' AND error IS NULL ORDER BY t DESC, rowid DESC LIMIT 4", (thread,)):
            k = (json.loads(reply or "{}")).get("kind")
            if k == "clarify":
                n += 1
            else:
                break
        return n

    def today_count(self) -> int:
        return self.j.db.execute("SELECT count(*) FROM ask_messages WHERE role='user' AND t >= ?", (int(self.j.now() - 86400),)).fetchone()[0]

    def ask(self, who: str, text: str, thread: str | None = None, provider: str | None = None) -> dict:
        text = (text or "").strip()[:2000]
        if not text:
            raise ValueError("empty question")
        thread = thread or uuid.uuid4().hex[:12]
        provider = (provider or os.getenv("ASK_PROVIDER", "gemini")).lower()
        if provider not in self.providers:
            raise ValueError(f"unknown provider {provider}")
        if self.today_count() >= DAILY_LIMIT:
            raise ValueError(f"daily question limit reached ({DAILY_LIMIT}); it resets in 24 hours")
        history = self._history(thread)
        tries = self._failed_clarifies(thread)
        now = int(self.j.now())
        uid = uuid.uuid4().hex[:12]
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, provider) VALUES (?,?,?,?,?,?)", (uid, thread, now, "user", text, provider))
        self.j.db.commit()
        note = f"\n\n[conversation note: clarification has failed {tries} time(s) in a row]" if tries else ""
        user_msg = f"[now: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now))}]{note}\n{text}"
        log: list = []
        t0 = time.time()
        aid = uuid.uuid4().hex[:12]
        model = GEMINI_MODEL if provider == "gemini" else CLAUDE_MODEL
        try:
            raw, usage = self.providers[provider](SYSTEM, history, user_msg, Lookups(self.j), log)
            reply = parse(raw)
        except Exception as exc:  # noqa: BLE001
            ms = int(1000 * (time.time() - t0))
            self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, provider, model, ms, tools, error) VALUES (?,?,?,?,?,?,?,?,?)",
                              (aid, thread, now + 1, "assistant", provider, model, ms, json.dumps(log), str(exc)[:500]))
            self.j.db.commit()
            return {"id": aid, "thread": thread, "provider": provider, "error": f"{provider} failed: {str(exc)[:200]}"}
        if reply["kind"] == "clarify" and tries >= 2:
            reply = {**reply, "kind": "not_understood", "options": [],
                     "answer": "Sorry, I still don't understand what you're asking. Here are things I can answer:", "follow_ups": EXAMPLES[:3]}
        if reply["kind"] in ("clarify", "not_understood"):
            self.j.db.execute("INSERT INTO ask_misunderstood VALUES (?,?,?,?,?)", (now, thread, text, reply["kind"], provider))
        ms = int(1000 * (time.time() - t0))
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, provider, model, ms, tokens_in, tokens_out, tools) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (aid, thread, now + 1, "assistant", json.dumps(reply), provider, model, ms, usage["in"], usage["out"], json.dumps(log)))
        self.j.db.commit()
        self.j.audit(who, "ask", text[:200], f"{provider} {reply['kind']} {ms}ms")
        return {"id": aid, "thread": thread, "provider": provider, "model": model, "ms": ms, "lookups": [x["tool"] for x in log], **reply}

    def rate(self, msg_id: str, rating: int) -> None:
        self.j.db.execute("UPDATE ask_messages SET rating=? WHERE id=? AND role='assistant'", (1 if rating > 0 else -1, msg_id))
        self.j.db.commit()

    def threads(self, n: int = 20) -> list[dict]:
        rows = self.j.db.execute("""SELECT thread, MIN(t), MAX(t), COUNT(*) FROM ask_messages GROUP BY thread ORDER BY MAX(t) DESC LIMIT ?""", (n,)).fetchall()
        out = []
        for th, t0, t1, cnt in rows:
            first = self.j.db.execute("SELECT text FROM ask_messages WHERE thread=? AND role='user' ORDER BY t LIMIT 1", (th,)).fetchone()
            out.append({"thread": th, "title": (first[0] if first else "")[:80], "time": views._local(t1), "messages": cnt})
        return out

    def thread(self, thread: str) -> list[dict]:
        out = []
        for mid, t, role, text, reply, prov, ms, err, rating in self.j.db.execute(
                "SELECT id, t, role, text, reply, provider, ms, error, rating FROM ask_messages WHERE thread=? ORDER BY t, rowid", (thread,)):
            if role == "user":
                out.append({"id": mid, "role": "user", "text": text})
            else:
                out.append({"id": mid, "role": "assistant", "provider": prov, "ms": ms, "rating": rating,
                            **({"error": err} if err else json.loads(reply or "{}"))})
        return out

    def stats(self) -> dict:
        out = {}
        for prov, n, ms, tin, tout, up, down, errs in self.j.db.execute("""
                SELECT provider, COUNT(*), AVG(ms), SUM(tokens_in), SUM(tokens_out), SUM(rating=1), SUM(rating=-1), SUM(error IS NOT NULL)
                FROM ask_messages WHERE role='assistant' GROUP BY provider"""):
            out[prov] = {"answers": n, "avg_seconds": round((ms or 0) / 1000, 1), "tokens_in": tin, "tokens_out": tout,
                         "thumbs_up": up or 0, "thumbs_down": down or 0, "errors": errs or 0}
        mis = [dict(zip(("t", "thread", "question", "kind", "provider"), r)) for r in
               self.j.db.execute("SELECT * FROM ask_misunderstood ORDER BY t DESC LIMIT 30")]
        return {"providers": out, "misunderstood": mis, "today": self.today_count(), "daily_limit": DAILY_LIMIT}
