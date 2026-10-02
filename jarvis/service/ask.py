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

MAX_TOOL_ROUNDS = 10
HISTORY_TURNS = 8
DAILY_LIMIT = int(os.getenv("ASK_DAILY_LIMIT", "150"))
GEMINI_MODELS = [m.strip() for m in os.getenv("ASK_GEMINI_MODELS", "gemini-3.5-flash,gemini-3.1-flash-lite,gemini-flash-latest").split(",") if m.strip()]
GEMINI_MODEL = GEMINI_MODELS[0]       # free tier: when the first model is busy (503), the next one answers
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
1. Facts only from lookups. Call the lookups you need before answering (usually 1-4, at most 6; ask for several in one round when you can; never call the same lookup twice; after a propose_* lookup succeeds, answer straight away); use only the lookups listed, by their exact names. Never invent prices, trades, counts or history. If a lookup returns nothing, say the evidence is not there.
2. Setups: in the setups lookup, "complete" means all conditions were met at the last check. Report complete setups as complete even when no new trade was placed, and say why (already holding that coin's trade type, no trade type fits, caps). Never say "none are triggering" when the lookup shows complete ones.
2b. Keep separate: what the market is doing, what Ananta observed, which setup may be forming, which conditions are met or missing, what history says, what action (if any) is justified, whether anything was executed, the outcome, what was learned.
3. Uncertainty: small samples are small; say so (e.g. "1 day of live evidence"). No predictions or promises. Historical odds are odds, not forecasts.
4. Scope: trading, markets, the economy and news that moves markets, and Ananta itself. Anything else: kind "out_of_scope" with a one-line polite reply ("That's outside my area - I'm built for trading and markets.").
5. Actions you can PREPARE (the owner confirms each card in the app): paper orders in the owner's manual book (propose_paper_order), alerts (propose_alert), mandate changes (propose_mandate_change). You can START a read-only reconstruction (start_research). You cannot: place real orders (no exchange is connected; real orders come only after the live rules are approved), flip switches (kill switch and autopilot are in the Cockpit), or approve the portfolio's own suggestions (Portfolio screen). For those use kind "cannot_do_yet" and say exactly where to do it. If an order request is missing the amount, ask for it (clarify); check it against the mandate's limits and say if it conflicts.
6. Unclear: if the question could mean different things that lead to different answers, use kind "clarify" with 2-4 short "Did you mean" options. A message that does not say what it is about (e.g. "do the thing", "fix it", "that one") with no earlier topic in the conversation is unclear: clarify, never answer it with a status report. If one reading is clearly most likely, answer it and state the assumption. Follow-ups ("why?", "and before that?") refer to the last topic.
7. If the conversation note says clarification already failed twice, do not ask again: use kind "not_understood" with 3 example questions you can answer.
8. Money: $ with 2 decimals; percentages with 1-2 decimals; times in Toronto time if given.

9. Changes: use a propose_* lookup only when the owner explicitly asks for that action in this message (an order, an alert, a mandate change); never offer one unasked. You can only PREPARE changes (propose_* lookups). Say clearly that a confirmation card is waiting; never claim something was changed.
10. The owner's mandate (below) is the standing brief: follow its limits, use its goals to judge what matters, and point out when a request conflicts with it.
11. Screens: when it helps, add "show" items so the app can open the right screen: {"screen": "coin", "coin": "ETH"} | {"screen": "trade", "id": "<trade id>"} | {"screen": "markets"} | {"screen": "portfolio"} | {"screen": "evidence"} | {"screen": "cockpit"} | {"screen": "mandate"}, each with a short "label" like "Open ETH chart".

OUTPUT: reply with ONE JSON object and nothing else:
{"kind": "answer" | "clarify" | "not_understood" | "out_of_scope" | "cannot_do_yet",
 "stage": one lifecycle word or "" ,
 "answer": "1-3 plain sentences: the direct answer",
 "breakdown": ["3-7 short bullet strings: the reasoning, plain words"],
 "evidence": [{"label": "...", "value": "...", "source": "which lookup / record", "time": "when, if known"}],
 "assumption": "the reading you assumed, or empty",
 "options": ["for clarify only: short options"],
 "follow_ups": ["2-3 natural next questions"],
 "show": [{"screen": "...", "label": "..."}]}"""

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
    ("alerts", "The owner's alerts: active ones, and recently fired ones with their messages.", OFF),
    ("propose_alert", "Prepare an alert when the owner asks to be told about something: kind price_above / price_below (value = price), "
     "move_pct (value = percent move in a day), setup (setup = E1-E5 or ANY: tells when that setup's conditions are all met). "
     "This does NOT create it: the owner confirms a card in the app. Alerts are checked every 15 minutes and cost nothing.",
     _schema({"kind": {"type": "string"}, "coin": COIN, "value": {"type": "number"}, "setup": {"type": "string"}, "note": {"type": "string"}}, ["kind", "coin"])),
    ("manual_book", "The owner's own manual paper book (orders the owner asked for, separate from the Explorer and the portfolio): cash, positions, P&L, recent fills with reasons, and the decision journal.", OFF),
    ("propose_paper_order", "Prepare a PAPER order in the owner's manual book when the owner asks to buy or sell. side buy | sell, coin, usd amount "
     "(for sell, omit usd to sell all), optional stop and target prices, and the owner's reason in their words. This does NOT trade: "
     "it shows a confirmation card (price now, size, exposure, cash after) that the owner must approve with Face ID. Never for real money.",
     _schema({"side": {"type": "string"}, "coin": COIN, "usd": {"type": "number"}, "stop": {"type": "number"}, "target": {"type": "number"},
              "reason": {"type": "string"}}, ["side", "coin"])),
    ("start_research", "Start a research job now (read-only, no cost): kind 'reconstruction' rebuilds every Explorer decision from raw candles "
     "and checks it matches the live log. The owner gets a phone note when done. Also returns recent jobs.",
     _schema({"kind": {"type": "string", "description": "reconstruction"}}, ["kind"])),
    ("mandate", "The owner's mandate in full: goals, markets, styles, setups, limits, how to talk. Also any actions waiting for the owner.", OFF),
    ("propose_mandate_change", "Prepare a change to the owner's mandate when the owner asks to change their goals, limits, styles or preferences. "
     "This does NOT change anything: it creates a confirmation card the owner must approve in the app.",
     _schema({"section": {"type": "string", "description": "goal | markets_now | markets_later | styles | setups | limits | how_to_talk"},
              "op": {"type": "string", "description": "add | replace | remove"},
              "text": {"type": "string", "description": "the new sentence (add / replace)"},
              "old": {"type": "string", "description": "the existing sentence, exactly (replace / remove)"}}, ["section", "op"])),
]
TOOL_DESC = {n: d for n, d, _ in TOOLS}

HUNTER_REASONS = {
    "REJECTED_RSI_NOT_RESET": "RSI has not dropped enough to count as a reset",
    "REJECTED_NO_VCP_BASE": "no tight base (volatility contraction) under the price",
    "REJECTED_HTF_TREND_MISALIGNED": "the higher-timeframe trend points the other way",
    "REJECTED_NO_SUPPORT_ZONE": "no support zone nearby",
    "REJECTED_VOLUME_NOT_EXHAUSTED": "selling volume has not dried up yet",
    "REJECTED_CHASING_GREEN_CANDLE": "price already jumped (would be chasing a green candle)",
    "REJECTED_OUTSIDE_ATR_ZONE": "price is not close enough to the entry zone",
    "REGIME_FILTERED": "the market regime does not suit this strategy",
    "no_qualifying_setup": "no qualifying setup",
}


class Lookups:
    """Read-only functions over Ananta's data. Each returns plain JSON-able data."""

    def __init__(self, j, thread: str | None = None):
        self.j = j
        self._ex = None
        self.thread = thread
        self.created: list[dict] = []          # pending actions prepared during this answer

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

    def t_mandate(self) -> dict:
        from jarvis.service.mandate import Mandate

        M = Mandate(self.j.db, self.j.now)
        return {**M.get(), "pending_actions": M.pending()}

    def t_propose_mandate_change(self, section: str, op: str, text: str = "", old: str = "") -> dict:
        from jarvis.service.mandate import SECTION_NAMES, Mandate

        if section not in SECTION_NAMES:
            return {"error": f"section must be one of {', '.join(SECTION_NAMES)}"}
        if op not in ("add", "replace", "remove") or (op != "remove" and not text.strip()):
            return {"error": "op is add / replace / remove, and add or replace needs text"}
        verb = {"add": "Add to", "replace": "Change in", "remove": "Remove from"}[op]
        summary = f"{verb} \"{SECTION_NAMES[section]}\": {text or old}"
        a = Mandate(self.j.db, self.j.now).propose("mandate", summary, {"section": section, "op": op, "text": text, "old": old}, self.thread)
        self.created.append(a)
        return {"prepared": a, "note": "Not applied. The owner sees a confirmation card and must approve it."}

    def t_alerts(self) -> dict:
        from jarvis.service.alerts import Alerts

        return {"alerts": Alerts(self.j.db, self.j.now).list()[:30]}

    def t_propose_alert(self, kind: str, coin: str, value: float | None = None, setup: str | None = None, note: str = "") -> dict:
        from jarvis.service.alerts import Alerts
        from jarvis.service.mandate import Mandate

        try:
            v = Alerts.validate({"kind": kind, "coin": coin, "value": value, "setup": setup, "note": note})
        except ValueError as exc:
            return {"error": str(exc)}
        if self.ex and v["coin"] not in self.ex.st["engines"]:
            return {"error": f"Ananta only watches {', '.join(self.ex.st['engines'])}"}
        summary = "Alert me when " + Alerts.describe(v["kind"], v["coin"], v["value"], v["setup"])
        a = Mandate(self.j.db, self.j.now).propose("alert", summary, v, self.thread)
        self.created.append(a)
        return {"prepared": a, "note": "Not active yet. The owner confirms the card in the app."}

    def t_manual_book(self) -> dict:
        from jarvis.service.manual import Manual

        Mn = Manual(self.j.db, self.j.now)
        return {**Mn.state(self.j.prices()), "fills": Mn.fills(15), "journal": Mn.journal(15)}

    def t_propose_paper_order(self, side: str, coin: str, usd: float | None = None, stop: float | None = None,
                              target: float | None = None, reason: str = "") -> dict:
        from jarvis.service.manual import Manual
        from jarvis.service.mandate import Mandate

        try:
            pv = Manual(self.j.db, self.j.now).preview({"side": side, "coin": coin, "usd": usd, "stop": stop, "target": target, "reason": reason},
                                                      self.j.prices())
        except ValueError as exc:
            return {"error": str(exc)}
        a = Mandate(self.j.db, self.j.now).propose("paper_order", pv["summary"], pv["order"], self.thread)
        self.created.append(a)
        return {"prepared": a, "preview": pv, "note": "Not executed. The owner confirms the card (Face ID); it fills at the price at that moment."}

    def t_start_research(self, kind: str) -> dict:
        from jarvis.service.manual import Manual

        Mn = Manual(self.j.db, self.j.now)
        if kind != "reconstruction":
            return {"error": "available research jobs: reconstruction", "recent": Mn.jobs(5)}
        from src.intelligence import explorer_live as xl

        def push(t, b):
            from src.intelligence.paper_watch import push_phone

            return push_phone(t, b, level="EVENT")
        j = Mn.start_job("ananta (asked by owner)", "reconstruction", lambda: xl.reconstruct(self.j.dir), push=push,
                         background=os.getenv("ASK_JOBS_INLINE") != "1")
        return {"started": j, "note": "Running in the background; takes a minute or two. The owner gets a phone note when done.", "recent": Mn.jobs(5)}

    def t_report(self, kind: str = "daily") -> dict:
        r = self.j._latest("explorer_weekly" if kind.startswith("w") else "explorer_daily")
        return r or {"error": f"no {kind} report yet"}


# ---------------------------------------------------------------------------
# providers (plain HTTPS, no SDKs)
# ---------------------------------------------------------------------------
def _post(url: str, headers: dict, body: dict, timeout: int = 60) -> dict:
    import requests

    for wait in (2, 6, 0):     # busy / rate-limited: retry twice
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as exc:
            raise RuntimeError(f"503 network/timeout: {str(exc)[:120]}") from exc
        if r.status_code not in (429, 500, 502, 503, 529) or not wait:
            break
        time.sleep(wait)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    return r.json()


MODELS = {   # key: provider, API model, price per million tokens (input, output), cache-read multiplier
    "gemini": {"label": "Gemini Flash", "provider": "gemini", "model": None, "price": (0.0, 0.0), "cache": 0.0},
    "haiku": {"label": "Claude Haiku", "provider": "claude", "model": os.getenv("ASK_HAIKU_MODEL", "claude-haiku-4-5-20251001"), "price": (1.0, 5.0), "cache": 0.1},
    "sonnet": {"label": "Claude Sonnet", "provider": "claude", "model": os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5"), "price": (2.0, 10.0), "cache": 0.1},
    "opus": {"label": "Claude Opus", "provider": "claude", "model": os.getenv("ASK_OPUS_MODEL", "claude-opus-5-5"), "price": (4.0, 20.0), "cache": 0.05},
}
MODES = {"everyday": "gemini", "deep": "sonnet", "max": "opus"}
ALIASES = {"claude": "sonnet", "gemini": "gemini", "haiku": "haiku", "sonnet": "sonnet", "opus": "opus"}
DEEP_WORDS = re.compile(r"\b(why|explain|compare|evaluat|analy[sz]|should|prepare|review|learn|history|histor|reconstruct|what if|strategy|strateg|backtest|"
                        r"evidence|break it down|reason|plan|risk|recommend|better|worse|improve|test)", re.I)


def route(text: str) -> tuple[str, str]:
    """Auto mode: everyday questions to free Gemini, investigations to Claude Sonnet."""
    if len(text) > 160 or DEEP_WORDS.search(text):
        return "sonnet", "Auto picked Claude: this needs investigation"
    return "gemini", "Auto picked Gemini: everyday question"


def cost_usd(key: str, usage: dict) -> float:
    m = MODELS.get(key) or MODELS["gemini"]
    pin, pout = m["price"]
    return round((usage.get("in", 0) * pin + usage.get("cache_write", 0) * pin * 1.25 + usage.get("cache_read", 0) * pin * m["cache"]
                  + usage.get("out", 0) * pout) / 1e6, 5)


def _strip_cache(msgs: list) -> None:
    for m in msgs:
        if isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict):
                    b.pop("cache_control", None)


def run_claude(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post, model: str | None = None) -> tuple[str, dict]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    model = model or CLAUDE_MODEL
    msgs = [{"role": m["role"], "content": m["text"]} for m in history] + [{"role": "user", "content": [{"type": "text", "text": user}]}]
    tdefs = [{"name": n, "description": d, "input_schema": s} for n, d, s in TOOLS]
    tdefs[-1] = {**tdefs[-1], "cache_control": {"type": "ephemeral"}}          # cache: tools + system
    sysb = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    usage = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
    rnd = -1
    for _ in range(MAX_TOOL_ROUNDS + 3):
        rnd = min(rnd + 1, MAX_TOOL_ROUNDS)
        _strip_cache(msgs)                       # one moving breakpoint on the newest message (max 4 in total)
        last = msgs[-1]["content"]
        if isinstance(last, list) and last:
            last[-1]["cache_control"] = {"type": "ephemeral"}
        r = post("https://api.anthropic.com/v1/messages",
                 {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                 {"model": model, "max_tokens": 3000, "system": sysb, "tools": tdefs, "messages": msgs,
                  **({"tool_choice": {"type": "none"}} if rnd == MAX_TOOL_ROUNDS else {})})   # last round: answer with what you have
        u = r.get("usage") or {}
        usage["in"] += u.get("input_tokens", 0)
        usage["out"] += u.get("output_tokens", 0)
        usage["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        usage["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
        content = r.get("content") or []
        calls = [c for c in content if c.get("type") == "tool_use"]
        if not calls:
            text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
            if not text.strip() and usage.get("nudged", 0) < 2:      # ended without words (only thinking): ask for the answer
                usage["nudged"] = usage.get("nudged", 0) + 1
                rnd = MAX_TOOL_ROUNDS - 1                           # the next round must answer
                msgs.append({"role": "assistant", "content": content or [{"type": "text", "text": "(no answer)"}]})
                msgs.append({"role": "user", "content": [{"type": "text", "text": "Please give your final answer now, as the JSON object."}]})
                continue
            usage["model"] = model
            return text, usage
        msgs.append({"role": "assistant", "content": content})
        results = []
        for c in calls:
            out = tools.call(c["name"], c.get("input") or {})
            log.append({"tool": c["name"], "args": c.get("input")})
            results.append({"type": "tool_result", "tool_use_id": c["id"], "content": json.dumps(out, default=str)[:20000]})
        msgs.append({"role": "user", "content": results})
    raise RuntimeError("too many lookup rounds")


def _gemini_schema(s: dict) -> dict:
    if not s.get("properties"):
        return None
    return s


def run_gemini(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post) -> tuple[str, dict]:
    err = None
    for m in GEMINI_MODELS:
        try:
            text, usage = _gemini_once(m, system, history, user, tools, log, post)
            usage["model"] = m
            return text, usage
        except RuntimeError as exc:
            err = exc
            if not str(exc)[:3] in ("503", "429", "500", "404"):
                raise
    raise RuntimeError(f"Gemini's free service is busy right now. Try again in a minute, or switch to Claude. ({str(err)[:80]})")


def _gemini_once(model: str, system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post) -> tuple[str, dict]:
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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    for rnd in range(MAX_TOOL_ROUNDS + 1):
        r = post(url, {"x-goog-api-key": key, "content-type": "application/json"},
                 {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                  "tools": [{"functionDeclarations": decls}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4000},
                  **({"toolConfig": {"functionCallingConfig": {"mode": "NONE"}}} if rnd == MAX_TOOL_ROUNDS else {})})
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
            res = json.loads(js) if len(js) <= 20000 else {"truncated": js[:20000]}
            resp.append({"functionResponse": {"name": c["name"], "response": {"result": res}}})
        contents.append({"role": "user", "parts": resp})
    raise RuntimeError("too many lookup rounds")


PROVIDERS: dict[str, Callable] = {
    "gemini": run_gemini,
    "haiku": lambda *a, **k: run_claude(*a, model=MODELS["haiku"]["model"], **k),
    "sonnet": lambda *a, **k: run_claude(*a, model=MODELS["sonnet"]["model"], **k),
    "opus": lambda *a, **k: run_claude(*a, model=MODELS["opus"]["model"], **k),
}
SETTINGS_DEFAULT = {"ask_enabled": "1", "voice_enabled": "1", "daily_budget_usd": "2", "over_budget": "gemini"}


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
    a = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', t)          # cut-off JSON: keep the answer at least
    if a:
        return {"kind": "answer", "stage": "", "answer": json.loads('"' + a.group(1) + '"'), "breakdown": [], "evidence": [],
                "assumption": "", "options": [], "follow_ups": []}
    if not t:
        raise RuntimeError("the model returned an empty answer; please ask again")
    return {"kind": "answer", "stage": "", "answer": t, "breakdown": [], "evidence": [],
            "assumption": "", "options": [], "follow_ups": []}


SCREENS = {"coin", "trade", "markets", "portfolio", "evidence", "cockpit", "mandate", "home"}


def _clean_show(items) -> list[dict]:
    out = []
    for it in (items or [])[:4]:
        if not isinstance(it, dict) or it.get("screen") not in SCREENS:
            continue
        x = {"screen": it["screen"], "label": str(it.get("label") or it["screen"].capitalize())[:40]}
        if it["screen"] == "coin":
            if not str(it.get("coin", "")).isalnum():
                continue
            x["coin"] = str(it["coin"]).upper()[:6]
        if it["screen"] == "trade":
            if not re.fullmatch(r"[A-Za-z0-9_\-]{3,80}", str(it.get("id", ""))):
                continue
            x["id"] = str(it["id"])
        out.append(x)
    return out


EXAMPLES = ["How is the market right now?", "What setups are close on ETH?", "How is the portfolio doing?", "What has Hunter been doing today?", "What did we learn from the repair shop?"]


class Ask:
    def __init__(self, j, providers: dict[str, Callable] | None = None):
        self.j = j
        self.providers = providers or PROVIDERS
        j.db.executescript("""
            CREATE TABLE IF NOT EXISTS ask_messages (id TEXT PRIMARY KEY, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT,
                provider TEXT, model TEXT, ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, tools TEXT, error TEXT, rating INTEGER);
            CREATE TABLE IF NOT EXISTS ask_misunderstood (t INTEGER, thread TEXT, question TEXT, kind TEXT, provider TEXT);
            CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT);
        """)
        cols = {r[1] for r in j.db.execute("PRAGMA table_info(ask_messages)")}
        for c, typ in (("cost_usd", "REAL"), ("mode", "TEXT"), ("note", "TEXT")):
            if c not in cols:
                j.db.execute(f"ALTER TABLE ask_messages ADD COLUMN {c} {typ}")
        j.db.commit()

    # ---- settings and spend ----
    def setting(self, k: str) -> str:
        row = self.j.db.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
        return row[0] if row else SETTINGS_DEFAULT.get(k, "")

    def settings(self) -> dict:
        return {k: self.setting(k) for k in SETTINGS_DEFAULT}

    def set_setting(self, who: str, k: str, v: str) -> dict:
        if k not in SETTINGS_DEFAULT:
            raise ValueError(f"unknown setting {k}")
        if k == "daily_budget_usd":
            x = float(v)
            if not 0 <= x <= 50:
                raise ValueError("budget must be between $0 and $50 a day")
            v = str(round(x, 2))
        if k in ("ask_enabled", "voice_enabled"):
            v = "1" if str(v).lower() in ("1", "true", "on", "yes") else "0"
        if k == "over_budget" and v not in ("gemini", "stop"):
            raise ValueError("over_budget is gemini or stop")
        self.j.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (k, v))
        self.j.db.commit()
        self.j.audit(who, "settings", f"{k}={v}", "OK")
        return self.settings()

    def _day_start(self) -> int:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Toronto")
        return int(datetime.fromtimestamp(self.j.now(), tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

    def spend(self) -> dict:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Toronto")
        d0 = self._day_start()
        m0 = int(datetime.fromtimestamp(self.j.now(), tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
        def tot(since):
            rows = self.j.db.execute("SELECT provider, COUNT(*), COALESCE(SUM(cost_usd),0) FROM ask_messages WHERE role='assistant' AND error IS NULL AND t >= ? GROUP BY 1", (since,)).fetchall()
            out: dict = {}
            for k, n, c in rows:
                lab = MODELS.get(ALIASES.get(k, k), {}).get("label", k)
                o = out.setdefault(lab, {"answers": 0, "usd": 0.0})
                o["answers"] += n
                o["usd"] = round(o["usd"] + c, 4)
            return out
        today, month = tot(d0), tot(m0)
        spent = sum(v["usd"] for v in today.values())
        budget = float(self.setting("daily_budget_usd"))
        return {"today_usd": round(spent, 4), "month_usd": round(sum(v["usd"] for v in month.values()), 4), "budget_usd": budget,
                "left_usd": round(max(0.0, budget - spent), 4), "today": today, "month": month, "settings": self.settings()}

    def _history(self, thread: str) -> list[dict]:
        rows = self.j.db.execute("SELECT role, text, reply FROM ask_messages WHERE thread=? AND error IS NULL ORDER BY t DESC, rowid DESC LIMIT ?",
                                 (thread, HISTORY_TURNS * 2)).fetchall()[::-1]
        out = []
        for role, text, reply in rows:
            if role == "user":
                if out and out[-1]["role"] == "user":
                    out.pop()
                out.append({"role": "user", "text": text})
            else:
                r = json.loads(reply) if reply else {}
                brief = {k: r.get(k) for k in ("kind", "answer", "breakdown", "evidence", "options") if r.get(k)}
                if out and out[-1]["role"] == "assistant":
                    out.pop()
                out.append({"role": "assistant", "text": json.dumps(brief)[:4000]})
        while out and out[0]["role"] != "user":
            out.pop(0)
        if out and out[-1]["role"] == "user":
            out.pop()
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
        return self.j.db.execute("SELECT count(*) FROM ask_messages WHERE role='user' AND COALESCE(mode,'') NOT LIKE 'eval:%' AND t >= ?",
                                 (int(self.j.now() - 86400),)).fetchone()[0]

    def _pick(self, text: str, mode: str | None, provider: str | None) -> tuple[str, str, str]:
        """-> (model key, mode label, note)."""
        if provider:                                            # old clients: provider gemini / claude
            key = ALIASES.get(provider.lower())
            if not key:
                raise ValueError(f"unknown provider {provider}")
            return key, provider.lower(), ""
        mode = (mode or "auto").lower()
        if mode == "auto":
            key, note = route(text)
            return key, "auto", note
        if mode in MODES:
            return MODES[mode], mode, ""
        if mode in MODELS:
            return mode, mode, ""
        raise ValueError(f"unknown mode {mode}")

    def ask(self, who: str, text: str, thread: str | None = None, provider: str | None = None, mode: str | None = None,
            second_of: str | None = None, context: dict | None = None, voice: bool = False, source: str = "") -> dict:
        text = (text or "").strip()[:2000]
        if not text:
            raise ValueError("empty question")
        if self.setting("ask_enabled") != "1":
            raise ValueError("Ask Ananta is switched off in the Cockpit")
        thread = thread or uuid.uuid4().hex[:12]
        key, mode_label, note = self._pick(text, mode, provider)
        if source != "eval" and self.today_count() >= DAILY_LIMIT:
            raise ValueError(f"daily question limit reached ({DAILY_LIMIT}); it resets in 24 hours")
        if MODELS[key]["provider"] == "claude":
            sp = self.spend()
            if sp["today_usd"] >= sp["budget_usd"]:
                if self.setting("over_budget") == "stop":
                    raise ValueError(f"today's Claude budget (${sp['budget_usd']:.2f}) is used up; raise it in the Cockpit or use Everyday")
                key, note = "gemini", f"Claude budget for today (${sp['budget_usd']:.2f}) is used up, so Gemini answered"
        history = self._history(thread)
        tries = self._failed_clarifies(thread)
        now = int(self.j.now())
        uid = uuid.uuid4().hex[:12]
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, provider, mode) VALUES (?,?,?,?,?,?,?)",
                          (uid, thread, now, "user", text, key, ("eval:" if source == "eval" else "") + ("voice:" if voice else "") + mode_label))
        self.j.db.commit()
        notes = []
        if tries:
            notes.append(f"[conversation note: clarification has failed {tries} time(s) in a row]")
        if second_of:
            notes.append("[conversation note: the owner asked for a second opinion on this question; answer it independently from the data]")
        if voice:
            notes.append("[voice session: the 'answer' is spoken aloud, so make it 1-3 short spoken sentences with no symbols, tables or abbreviations "
                         "(say 'percent', 'dollars'); put numbers and detail in breakdown and evidence, and use 'show' to put the right chart or card on screen]")
        if context:
            notes.append("[screen context: the owner is looking at " + json.dumps(context, default=str)[:600] + "]")
        user_msg = f"[now: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now))}]" + ("\n" + "\n".join(notes) if notes else "") + f"\n{text}"
        log: list = []
        t0 = time.time()
        aid = uuid.uuid4().hex[:12]
        used = key
        from jarvis.service.mandate import Mandate

        system = SYSTEM + "\n\nOWNER'S MANDATE (current)\n" + Mandate(self.j.db, self.j.now).text()
        try:
            try:
                L = Lookups(self.j, thread)
                raw, usage = self.providers[key](system, history, user_msg, L, log)
            except Exception as exc:  # noqa: BLE001
                # free Gemini busy: escalate once to Claude Haiku if allowed and within budget
                if key == "gemini" and "haiku" in self.providers and self.spend()["left_usd"] > 0.02 and os.getenv("ANTHROPIC_API_KEY"):
                    used = "haiku"
                    note = (note + "; " if note else "") + "Gemini was busy, so Claude Haiku answered"
                    log.clear()
                    L = Lookups(self.j, thread)
                    raw, usage = self.providers["haiku"](system, history, user_msg, L, log)
                else:
                    raise exc
            try:
                reply = parse(raw)
            except RuntimeError:
                if not L.created and MODELS[used]["provider"] == "claude" and "gemini" in self.providers:
                    # Claude occasionally ends with thinking only; answer this one with Gemini instead of failing
                    note = (note + "; " if note else "") + "Claude gave no words this time, so Gemini answered"
                    used = "gemini"
                    log.clear()
                    L = Lookups(self.j, thread)
                    raw, usage = self.providers["gemini"](system, history, user_msg, L, log)
                    reply = parse(raw)
                elif not L.created:
                    raise
                else:
                    reply = {"kind": "answer", "stage": "decision", "evidence": [], "assumption": "", "options": [], "follow_ups": [],
                         "answer": "I've prepared this for you; nothing happens until you confirm the card: " + "; ".join(a["summary"] for a in L.created),
                         "breakdown": []}
        except Exception as exc:  # noqa: BLE001
            ms = int(1000 * (time.time() - t0))
            self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, provider, mode, ms, tools, error) VALUES (?,?,?,?,?,?,?,?,?)",
                              (aid, thread, now + 1, "assistant", used, mode_label, ms, json.dumps(log), str(exc)[:500]))
            self.j.db.commit()
            return {"id": aid, "thread": thread, "provider": used, "error": str(exc)[:240]}
        model = usage.get("model") or MODELS[used]["model"] or GEMINI_MODEL
        cost = cost_usd(used, usage)
        if reply["kind"] == "clarify" and tries >= 2:
            reply = {**reply, "kind": "not_understood", "options": [],
                     "answer": "Sorry, I still don't understand what you're asking. Here are things I can answer:", "follow_ups": EXAMPLES[:3]}
        if reply["kind"] in ("clarify", "not_understood"):
            self.j.db.execute("INSERT INTO ask_misunderstood VALUES (?,?,?,?,?)", (now, thread, text, reply["kind"], used))
        ms = int(1000 * (time.time() - t0))
        reply["show"] = _clean_show(reply.get("show"))
        reply["actions"] = L.created
        meta = {"model_label": MODELS[used]["label"], "mode": mode_label, "cost_usd": cost, "note": note, "second_of": second_of}
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, provider, model, ms, tokens_in, tokens_out, tools, cost_usd, mode, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (aid, thread, now + 1, "assistant", json.dumps({**reply, **meta}), used, model, ms,
                           usage.get("in", 0) + usage.get("cache_read", 0) + usage.get("cache_write", 0), usage.get("out", 0), json.dumps(log), cost, mode_label, note))
        self.j.db.commit()
        self.j.audit(who, "ask", text[:200], f"{used} {reply['kind']} {ms}ms ${cost:.4f}")
        return {"id": aid, "thread": thread, "provider": used, "model": model, "ms": ms, "lookups": [x["tool"] for x in log], **reply, **meta}

    # ---- voice ----
    def transcribe(self, audio_b64: str, mime: str = "audio/wav", post=_post) -> str:
        """Speech to text with Gemini (free tier). Audio is not stored."""
        if self.setting("voice_enabled") != "1":
            raise ValueError("Voice is switched off in the Cockpit")
        if not audio_b64 or len(audio_b64) > 12_000_000:
            raise ValueError("audio missing or too long (about 2 minutes at most)")
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        prompt = ("Transcribe this spoken message exactly, in English. It is the owner talking to Ananta, a crypto trading assistant "
                  "(coins: BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP; words: Hunter, Squeeze, Explorer, setup, portfolio, mandate). "
                  "Return only the words spoken. If there is no speech, return an empty string.")
        err = None
        order = ["gemini-3.1-flash-lite"] + [m for m in GEMINI_MODELS if m != "gemini-3.1-flash-lite"]     # fastest first for speech
        for m in order:
            try:
                r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                         {"x-goog-api-key": key, "content-type": "application/json"},
                         {"contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": mime, "data": audio_b64}}, {"text": prompt}]}],
                          "generationConfig": {"temperature": 0.0, "maxOutputTokens": 600}})
                parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip().strip('"')
            except RuntimeError as exc:
                err = exc
        raise RuntimeError(f"could not transcribe right now ({str(err)[:80]})")

    def voice_turn(self, who: str, audio_b64: str, mime: str, thread: str | None, mode: str | None, context: dict | None, source: str = "") -> dict:
        heard = self.transcribe(audio_b64, mime)
        if not heard:
            return {"heard": "", "thread": thread, "error": "I didn't catch any words. Try again a little closer to the phone."}
        out = self.ask(who, heard, thread=thread, mode=mode, context=context, voice=True, source=source)
        return {"heard": heard, **out}

    def second(self, who: str, msg_id: str) -> dict:
        row = self.j.db.execute("SELECT thread, t, provider FROM ask_messages WHERE id=? AND role='assistant'", (msg_id,)).fetchone()
        if not row:
            raise ValueError("unknown answer")
        thread, t, prov = row
        q = self.j.db.execute("SELECT text FROM ask_messages WHERE thread=? AND role='user' AND t <= ? ORDER BY t DESC, rowid DESC LIMIT 1", (thread, t)).fetchone()
        if not q:
            raise ValueError("question not found")
        other = "sonnet" if MODELS.get(prov, MODELS["gemini"])["provider"] == "gemini" else "gemini"
        return self.ask(who, q[0], thread=thread, mode=other, second_of=msg_id)

    def rate(self, msg_id: str, rating: int) -> None:
        self.j.db.execute("UPDATE ask_messages SET rating=? WHERE id=? AND role='assistant'", (1 if rating > 0 else -1, msg_id))
        self.j.db.commit()

    def threads(self, n: int = 20) -> list[dict]:
        rows = self.j.db.execute("""SELECT thread, MIN(t), MAX(t), COUNT(*) FROM ask_messages GROUP BY thread ORDER BY MAX(t) DESC LIMIT ?""", (n,)).fetchall()
        out = []
        for th, t0, t1, cnt in rows:
            first = self.j.db.execute("SELECT text, mode FROM ask_messages WHERE thread=? AND role='user' ORDER BY t LIMIT 1", (th,)).fetchone()
            out.append({"thread": th, "title": (first[0] if first else "")[:80], "time": views._local(t1), "messages": cnt,
                        "voice": bool(first and (first[1] or "").startswith("voice:"))})
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
        for prov, n, ms, tin, tout, up, down, errs, cost in self.j.db.execute("""
                SELECT provider, COUNT(*), AVG(ms), SUM(tokens_in), SUM(tokens_out), SUM(rating=1), SUM(rating=-1), SUM(error IS NOT NULL), SUM(cost_usd)
                FROM ask_messages WHERE role='assistant' GROUP BY provider"""):
            out[prov] = {"answers": n, "avg_seconds": round((ms or 0) / 1000, 1), "tokens_in": tin, "tokens_out": tout,
                         "thumbs_up": up or 0, "thumbs_down": down or 0, "errors": errs or 0, "usd": round(cost or 0, 4),
                         "usd_per_answer": round((cost or 0) / max(1, n - (errs or 0)), 4)}
        mis = [dict(zip(("t", "thread", "question", "kind", "provider"), r)) for r in
               self.j.db.execute("SELECT * FROM ask_misunderstood ORDER BY t DESC LIMIT 30")]
        return {"providers": out, "misunderstood": mis, "today": self.today_count(), "daily_limit": DAILY_LIMIT, "spend": self.spend()}
