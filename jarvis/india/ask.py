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

from jarvis.india import appmap, askwords, marketcontext, speaker, technicals, views, voiceid

# "my mom asks ...", "she wants to know ...": Madhav relaying for the guest, so his voice does not end the handover
RELAY = re.compile(r"\b(?:my (?:mom|mother|amma|dad|father|nanna|pinni)|she|he|they|the grader)\s+(?:asks?|is asking|wants to know|says|said)\b", re.I)

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
ASK_DIR = DATA / "ask"
ENV_FILE = Path(os.getenv("ANANTA_AGENT_ENV", "/Users/vamsie/code/ananta-decision-agent/.env"))
MODEL = os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5")
DAILY_LIMIT = int(os.getenv("ASK_DAILY_LIMIT", "150"))
HISTORY_TURNS = 8
SYSTEM = """You are Ananta, Madhav's trading assistant for the INDIAN market (NSE stocks and the Nifty index), on paper only. Address him as "sir".
THREE KINDS OF ANSWER (27 Oct, Madhav: "it can't tell the difference between what it knows and what it has data for"):
(1) TEXTBOOK MARKET KNOWLEDGE (what a term means; how NSE and BSE, circuit breakers, splits, bonus issues, dividends, buybacks, ETFs, mutual funds,
futures, options and option spreads work; how a ratio such as P/E, P/B, beta or Sharpe is computed): answer directly and confidently from your own
knowledge, as an expert would. Do NOT label it "general knowledge", "general market knowledge", "not from my data files" or "not from my files", do not
say you are "marking it that way", and never refuse a basic question (NSE vs BSE: NSE is far larger by volume, especially in derivatives). Things that
change over time (current SEBI rules, tax rates, fees, exchange volumes) you may give "as far as I know".
(2) LIVE NUMBERS and anything about Madhav's account, the books, Ananta's plan, prices, indicators or flows: ONLY from the FACTS block in the user turn,
with the date each number is as of (for "today", "the latest close" or "how did the Nifty close", use latest_closes, the newest dated close, and say
its date; breadth, the trend averages and the books stay on data_through and say their own date); it is India's read model for the latest session ("morning_view" is the day's view written before the open: the market, Ananta's plan, the chances with their baselines, what to watch, yesterday's scorecard, the reviewer's second opinion; and, for Madhav, "account_allocation": his holdings graded A-D and ranked, the suggested changes, the paper moves and what is being watched; quote its grades, actions and "wrong_if" exactly). Never invent a number, a stock or a reason; if the facts do not hold a live number, say so in one short clause and give what they do hold.
(3) DOES IT WORK / SHOULD I USE IT: only from Ananta's tests in the facts (technicals.indicator_knowledge, teacher_libraries "tested", the registry
verdicts, the study lines in market_context); if there is no test, say "Ananta hasn't tested this" once. That is the one caveat that matters, because
he might act on it; a definition needs no caveat.
WHEN HE ASKS FOR A READ OR A DECISION ("what's your read", "what do you think", "what should I do", "sell, hold or add", "is it too late to enter"),
always decide, in this shape: (a) your read in one sentence; (b) what Ananta would do on paper by its own rules: hold, trim, add, exit or wait (quote
the account grades, actions and wrong_if lines exactly; the guardrails; the tested filters: RSI over 70 and far above the 50-day = don't chase, wait;
a fixed stop beat a trailing one (TS1); a -7% stop lost against no stop (TWT-H22); adding to stocks 40% down and under the 200-day often fell further
(TWT-H15)); (c) what would change your mind; (d) how strong the evidence is: tested, untested or against the tests. End on the decision. Paper only,
not advice. Keep it to about five short sentences: one per part plus the decision; cite at most two tests; leave out extra numbers. A HYPOTHETICAL ("a position up 8% while the market falls all week", "a stock down 15% in two days on heavy volume") is answered as a
hypothetical by these rules first (for example: strength against a falling market is relative strength, so hold it with its stop and do not add
while it is far above its 50-day); only then, if useful, map it to a real holding in the facts. Never stop at describing a position.
Nothing here is financial advice; no real money is traded;
you cannot place, change or close a trade from chat: say "paper only; nothing is placed from chat" ONLY when he asks you to trade, never as a sign-off on other answers.
Flags, research notes and fix choices are handled in code before you see a message (26 Oct): a request to research or note something is saved as a detailed
note with no fix menu, and an app problem is flagged with fixes. Never say a flag or a note cannot be filed from chat; never offer fixes for a research request,
never tell him to say "fix N" to save a note, and never bring up flags or notes unless he asks about them. If the QUESTION starts with a note line, it was
already saved: just answer the question. If his message only remarks on your last answer or says he is ready (no question in it), reply in one short line
and wait; if a question he asked earlier is still unanswered, answer it. "teacher_libraries" holds the YouTube teachers' classes (Optionables = the options
teacher, Trade With Trend = the stocks teacher) turned into testable hypotheses and where each stands; "the professor" or "YouTube classes" means these.
Its "tested" part holds the 25 Oct backtest of every claim, card by card: use the plain words there, say which held up, which came out the wrong
way, and that the held-up ones are filters (what to avoid), not buy signals; his intraday straddle systems are still being tracked on live prices.
Explain technical words with a plain meaning alongside the name (simplify the explanation, not the intelligence). Be brutally honest: a lost
session is lost, a wrong call is wrong, 0 of 3 is 0 of 3. SHORT AND PLAIN (27 Oct, Madhav: "we have to do something about length and making it simpler"): by default answer in 2-4 short sentences, the answer first, one idea per sentence, numbers rounded sensibly (22,750 not 22,749.75; 0.5% not 0.48%) unless he asks for the exact figure; a read-and-decide answer about 4 sentences. He says 'explain more' when he wants the detail; the message then says EXPAND and gives your previous answer. Never use database language in the answer: no study or card codes (XO1, TWT-H22, OPT-H55, SP1 ...), no field names with underscores (wrong_if, suggest_inr ...), no verdict labels in capitals (VALIDATED, REJECTED ...), no exit codes (ATRSTOP, D2): say what they mean ("the teacher's 7% stop test did not hold"); the codes go in "evidence" only.
When the FACTS hold "reconstruction_detail", Madhav wants to discuss the reconstruction process: explain it in simple spoken words, one part at a time (use the
card's own numbers from last night as the example, and an everyday comparison when it helps, e.g. a coach replaying the match), up to 6 sentences, and offer the
next part as a follow-up (the seven parts A-G, the findings, the staircase, what is filed on the repair board). Its "web_notes" are public reasons found on the
web for the day's biggest moves, each with a grade (A filing, B two outlets, C one source or unclear) and URLs: when asked why a stock moved, say "public reports
say ..." with the grade, and add that a note is never a reason to trade.
Say the same thing the screens say (25 Oct, from his chats): the daily call's own "words" say which session it is for (never call an old call
"the call for the next session"); the research book is practice money, so quote it as the average % per closed trade; for his account, a holding's
suggest_inr (the full suggestion) and paper_moves_today (what actually moves at today's close) are different numbers, so name the one you quote;
each "jobs.problems" line is that job's LAST run, so give its time if it has one and do not call it a current failure when a later line says it worked.
Reply with ONE JSON object and nothing else: {"kind":"answer","stage":"observation|outcome|learning","answer":"...","breakdown":["...","..."],
"evidence":["<fact and where it comes from>", ...],"assumption":"","follow_ups":["short question","short question","short question"],
"next_action":{"label":"","why":"","route":""},"show":[],"options":[],"route":"india","ui":[],"points":[]}.
You can move the app and point at things: when he asks to see, open or go somewhere, or when showing it makes the answer clearer, put
"ui":[{"do":"go_to"|"open","target":"<a PLACE key>"}] (open is for sheet:... targets) and say in the answer what you opened; to light a part
of Home while a sentence is spoken, add "points":[{"spot":"<a SPOT key>","sentence":<0-based sentence number>}]. Never claim you opened
something without a ui action for it. Use only the PLACE and SPOT keys listed below.
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

def latest_closes(rm: dict) -> dict:
    """27 Oct (17:02 voice: "today's Nifty at 22,753 on 26 Oct" while the 27 Oct close was already in): the newest dated close of Nifty, Bank
    Nifty and India VIX, whichever source is newest (the market section's newer_closes, the technicals panel, the market context), so 'today /
    the latest close' is never the bhavcopy day's number."""
    best: dict[str, dict] = {}

    def put(name, date, close, d1=None, src=""):
        if close is None or not date:
            return
        date = str(date)[:10]
        if name not in best or date > best[name]["date"]:
            best[name] = {"date": date, "close": close, "change_1d": d1, "source": src}
    m = rm.get("market") or {}
    for n, v in ((m.get("newer_closes") or {}).items() if isinstance(m.get("newer_closes"), dict) else []):
        if isinstance(v, dict):
            put(n, v.get("date"), v.get("close"), v.get("d1"), "newer closes")
    if m.get("nifty_close") is not None:
        put("NIFTY 50", m.get("data_through") or rm.get("data_through"), m.get("nifty_close"), None, "decision day")
    if m.get("vix_close") is not None:
        put("INDIA VIX", m.get("data_through") or rm.get("data_through"), m.get("vix_close"), None, "decision day")
    for n, p in ((rm.get("technicals") or {}).get("indices") or {}).items():
        if isinstance(p, dict):
            put(n, p.get("as_of"), p.get("close"), p.get("change_1d"), "technicals panel")
    mc = rm.get("market_context") or {}
    for n, g in (((mc.get("opening_gaps") or {}).get("rows")) or {}).items():
        if isinstance(g, dict):
            put(n, g.get("date"), g.get("close"), g.get("day"), "market context")
    v = mc.get("india_vix") or {}
    if v.get("status") == "ok":
        put("INDIA VIX", v.get("as_of"), v.get("value"), v.get("change_1"), "market context")
    newest = max((x["date"] for x in best.values()), default=None)
    return {"closes": best, "newest_date": newest,
            "how_to_say_it": "for 'today', 'the latest close' or 'how did the Nifty close', use these newest dated closes and say their date; breadth, the "
                             "trend averages in market and the books stay on data_through and say that date when it is older"}


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
            "latest_closes": latest_closes(rm),
            "market": {k: (rm.get("market") or {}).get(k) for k in ("nifty_close", "nifty_vs_sma50", "nifty_vs_sma200", "trend_state", "vix_close", "breadth_200d_liquid", "words")},
            "daily_call": call_state(rm),
            "stock_book": {"rules": sb.get("rules"), "open_positions": sb.get("open_positions"),
                           # flag 44 (26 Oct): a win rate over closed trades alone hides the open winners; always say the two counts together
                           "closed_vs_open": sb.get("closed_vs_open"),
                           "win_rate_rule": "never say a bare 'win rate'. A win rate counts closed trades only; say it with the open book beside it, using closed_vs_open.words "
                                            "(for example 'win rate counts closed trades only: 0 of 29 closed won; of 72 open, 10 are up') and use per_family_words for one family.",
                           "scale": "Rs 50,000 notional a trade (research scale), every registered exit tracked; the reference exit shown is hold_20d",
                           "closed_trades_avg_pct": views.books().get("per_trade_pct"),
                           "how_to_say_it": "this is the research book of practice trades, not Madhav's money: say its result as the average % per closed trade "
                                            "(closed_trades_avg_pct, per family avg_pct_per_closed_trade), the scale the screens use; the rupee totals only if he asks for them",
                           "by_campaign": {c: {**{k: m.get(k) for k in ("open", "closed", "realised_inr", "open_unrealised_inr", "win_rate")},
                                               "avg_pct_per_closed_trade": views.per_trade_pct(m)} for c, m in marks.items()},
                           "campaign_meaning": views.CAMPAIGN_WHY, "top_positions": [{"symbol": p["coin"], "campaign": p["campaign"], "since": p["since"], "pnl_pct": p["pnl_pct"]} for p in pos[:12]],
                           "recent_closed": [{"symbol": c["coin"], "campaign": c["campaign"], "net_inr": c["net_usd"], "why": c["why"], "exit_date": c["exit_date"]} for c in views.closed_trades(8)]},
            "decisions_for_next_session": {"rules": d.get("rules"), "decided_at": d.get("decided_at"), "candidates": d.get("candidates"),
                                           "stale_inputs": d.get("inputs"),
                                           # 26 Oct chat: "the Nifty input is marked stale (last row 22 Oct)" was repeated in every answer as if the market
                                           # numbers were old; the mark is about the inputs the picks were made on, not the market section
                                           "stale_inputs_meaning": "the picks for the next session were decided on these inputs at decision time; it says nothing about "
                                                                   "the market section above, which is current through data_through. Mention it only when asked about "
                                                                   "the picks or the data, once.",
                                           "chosen": [{"symbol": x.get("symbol"), "campaign": x.get("campaign"), "close": x.get("close"), "why": x.get("why")} for x in d.get("chosen", [])]},
            "index_line_sp1": {"capital_inr": 60000, **{k: (rm.get("sp1") or {}).get(k) for k in ("status", "words", "decisions", "errors")}, "sessions": ((rm.get("sp1") or {}).get("book") or {}).get("sessions")},
            "reference_traders_league": {"h1": lg.get("h1"), "informed": lg.get("informed"), "meaning": "HINDSIGHT = best trips the session offered; RANDOM = chance; MARKET = the liquid 250; coverage = of the top 20 trips, how many Ananta took / passed / had no rule for"},
            "missed_movers": (L.get("missed") or {}).get("line"), "drafts": L.get("drafts"),
            "research": {"studies": r.get("studies"), "gate_G02": r.get("gate"), "gate_counters": r.get("gate_counters"), "registry_verdicts": r.get("verdicts"), "exit_book_chosen": (r.get("exit_book") or {}).get("chosen")},
            "jobs": {"signin": j.get("signin"), "problems": [{"job": x["label"], "problems": x["problems"]} for x in j.get("jobs", []) if not x.get("ok")]},
            "guardrails": guardrail_facts(rm), "missing_sections": rm.get("missing"),
            "allocation_rule": allocation_rule_facts(),
            "morning_view": {k: v for k, v in views.morning().items() if k in ("session_words", "headline", "view", "plan", "chances", "watch", "yesterday", "words", "review", "reviewer_scenarios", "scenarios", "opening", "lessons", "read")},
            "reconstruction_last_night": {k: (rm.get("reconstruction") or {}).get(k) for k in ("headline", "people_words", "not_done_words", "league_words", "reviews", "findings")} | {"staircase": ((rm.get("reconstruction") or {}).get("staircase") or {}).get("words"),
                                          "meaning": "the nightly reconstruction card (what the market and other participants did, what Ananta did and did not do, trade reviews, findings); SAFE findings go to the repair board by themselves, DECISION findings wait for Madhav; the staircase says what the allocated capital may use (ADMITTED only; nothing yet)"},
            "teacher_libraries": _library_facts(),
            "technicals": technicals.facts_part(rm),     # 26 Oct: averages, crossovers, RSI, MACD, support/resistance, volume + what was tested
            "book_stats": book_stats_facts(rm),     # 26 Oct (Madhav: yes to all): expectancy, Sharpe-like ratio, holdings correlation, slippage, each with its "too few" flag
            "market_context": marketcontext.facts_part(rm),     # 26 Oct: rupee, dollar, crude, US yields/indices, fear gauges, FII/DII: to explain, never to predict
            **({"account_allocation": _alloc_facts()} if owner else {})}


RX_TOPIC = re.compile(r"\bwhy (did|is|was|has)\b[^?]{0,40}\b(fall|fell|drop|dropped|rise|rose|jump|jumped|move|moved|rally|rallied|crash|crashed|up|down|surge|surged|slump|slumped)\b|news|reason|reconstruct|rebuild|session card|\bcard\b|finding|staircase|admitted|shadow|repair (shop|board)|evidence|missed|did not do|didn.t (take|do|buy)|what (did )?(you|ananta) learn|learn(ed|t)? last night|other (traders|people)|what people|bulk|block deal|fii|dii|trade review|stopped then ran|gave back|never worked|left on (the )?table|league", re.I)

RX_EXPLAINER = """THE RECONSTRUCTION PROCESS (RX-IN v1, built 23 Oct 2026; Madhav agreed to every part of the design the same day). Plain words, for explaining:
- Why it exists: Ananta is judged by the quality of its decisions. Every night it replays the day like a coach replaying a match: what the market did, what other people did, what Ananta did, what it did not do, and whether each of those was right. What it learns goes to the repair shop; what survives testing climbs a staircase until the allocated paper capital may use it.
- When: every evening at 22:30 Toronto, after the paper engine, the missed-movers review and the reference-traders league; the SAFE findings are filed on the repair board at 22:50.
- The card has seven parts. A, the market: the trend, how many stocks are healthy (breadth), the fear gauge (VIX), the biggest movers. B, what people did: public records only, each stamped at the minute it became public: big single-client trades (bulk and block deals), foreign and domestic institutions' buying and selling (FII/DII), who holds the futures (participant open interest), company announcements, registered world events, and the reference traders (HINDSIGHT = the best trips the day offered, the ceiling; RANDOM = pure chance; MARKET = the average stock). These are a yardstick, never something to copy: in crypto, copying traders' timing failed every test. C, what Ananta did: what it chose, what it rejected and why, fills, exits, the daily call, the index line, the allocation moves. D, what it did not do: the big moves it missed (class a: a rule fired but was rejected or had already exited; class b: no rule was positioned for it; class c: it could not be traded), the falls it held into, and every rejected candidate followed forward by the shadow (baseline) book to see whether the pass was right; that is hindsight and only ever raises a question, never a verdict. E, trade reviews: three sessions after a trade closes, it is tagged in units of its own risk (R = entry minus the signal bar's low): STOPPED_THEN_RAN (stopped out and then the price rose a full R above the entry: stop too tight or early entry), GAVE_BACK (was up 1.5R and still closed at or under the entry: no plan to protect the winner), NEVER_WORKED (never got a quarter R above the entry: poor timing), LEFT_ON_TABLE (a win, then the price went another R higher within three sessions: sold too early), COSTS_ATE (moved less than the charges), CLEAN (a win that kept at least half of its best move). F, findings: only fixed counts make a finding, never one day's story: the same missed situation on 3 of 7 sessions, the same review tag on 5 trades of one family in 20 sessions, a family holding into 5 of the top falls on 3 of 7 sessions, the daily call below a coin flip over 20 sessions, allocation moves wrong 3 times in 20, missing data, failed jobs, the sign-in. G, forwarding: SAFE findings (data, jobs, words, screens) go to the repair board by themselves, at most 3 a night, and the repair worker fixes them; DECISION findings (anything touching a rule, size, stop, exit, book, allocation) go to a queue for Madhav's weekly yes. Code decides the lane, never the AI.
- The evidence staircase, each bar fixed before any data: NOTED (on a card) -> DRAFT (its count fired) -> REGISTERED (Madhav says yes; the study is written down before it runs) -> TESTED (run on 2000-2023 only; it must pass the registry's strict bar for every variant ever tried) -> SHADOW (a paper book runs it on live sessions; 20 recorded sessions) -> ADMITTED (beats RANDOM and MARKET on 10 separate sessions after costs, the leak check passes, pinned in the lock, Madhav says yes; only now may the allocated capital use it) -> LIVE_ELIGIBLE (the India gate and Madhav's yes).
- Rules on the process itself: it never reads the sealed 2024+ data, never calls the broker, never places a trade; every number names its file; a missing source says missing; the same finding is never filed twice while open; sessions, not trades, are the unit of evidence because stocks move together on a day.
- Where it shows: the Evidence tab (repair shop, forwarded, tracker), the Reconstruction screen, the My flags screen for filed findings, and this conversation."""


def _rx_detail() -> dict:
    c = views.reconstruction()
    rm = views.readmodel()
    st = (rm.get("reconstruction") or {}).get("staircase") or {}
    sec = c.get("sections") or {}
    rv = sec.get("reviews") or {}
    return {"how_it_works": RX_EXPLAINER, "card_ready": c.get("ready"), "card_day": c.get("day"), "cards_so_far": c.get("cards"),
            "A_market": (sec.get("market") or {}).get("words"), "A_movers_up": (sec.get("market") or {}).get("movers_up"), "A_movers_down": (sec.get("market") or {}).get("movers_down"),
            "B_people": (sec.get("people") or {}).get("words"), "B_league": ((sec.get("people") or {}).get("league") or {}).get("words"),
            "B_deals_top": (((sec.get("people") or {}).get("deals") or {}).get("bulk") or {}).get("top", [])[:5],
            "B_missing": [k for k in ("deals", "fii_dii", "participant_oi", "announcements", "events") if (((sec.get("people") or {}).get(k)) or {}).get("status") != "ok"],
            "C_ananta": (sec.get("ananta") or {}).get("words"), "D_not_done": (sec.get("not_done") or {}).get("words"),
            "D_best_passes_hindsight": ((sec.get("not_done") or {}).get("counterfactual") or {}).get("best_passes"),
            "E_reviews": {"count": rv.get("count"), "tags": rv.get("tags"), "trades": [t.get("words") for t in (rv.get("trades") or [])[:10]], "note": rv.get("note")},
            "F_findings": [{k: f.get(k) for k in ("type", "lane", "state", "words")} for f in c.get("findings") or []],
            "queue": [{k: q.get(k) for k in ("type", "lane", "state", "day", "request")} for q in views._queue_rows()][-12:],
            "staircase": {"words": st.get("words"), "rules": st.get("rules"), "admitted": st.get("admitted")},
            "web_notes": views.netnotes(c.get("day")), "drafts_waiting": views.drafts()["drafts"]}


LIBRARIES = {"OPT": {"teacher": "Optionables (YouTube, Indian options)", "videos": "434 public videos with captions, of 459 (members-only not used)"},
             "TWT": {"teacher": "Trade With Trend, Raunak A (YouTube, Indian stocks)", "videos": "161 public videos with captions, of 289 (members-only not used)"},
             "M": {"teacher": "Madhav's own method notes", "videos": "-"}}
_LIB_CACHE: dict = {}


def _library_facts() -> dict:
    """The teachers' libraries (Madhav, 24 Oct: "I have a long data of YouTube professor's options trading in our database"): each teacher's
    claims as testable hypotheses, where each stands on India's research map, and the work plan. Counts are read from the review pack
    (records repo registrations), never from the teaching library itself: the agent never reads the teachers' words (tests/test_library.py)."""
    p = views.REG / "hypothesis_review.md"
    try:
        sp = views.DATA / "gold" / "teachers" / "summary.json"
        mt = (p.stat().st_mtime, sp.stat().st_mtime if sp.exists() else 0)          # the tested results change nightly; the review pack rarely
    except OSError:
        return {"ready": False}
    if _LIB_CACHE.get("mt") == mt:
        return _LIB_CACHE["v"]
    out: dict = {}
    for line in p.read_text().splitlines():
        m = re.match(r"\|\s*(OPT|TWT|M)-H?\d+\s*\|[^|]*\|[^|]*\|\s*([A-Z_]+)\s*\|\s*([^|]*)\|\s*([^|]*)\|", line)
        if not m:
            continue
        pre, status, study, verdicts = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()
        o = out.setdefault(pre, {**LIBRARIES[pre], "hypotheses": 0, "by_status": {}, "studies": set(), "with_results": 0})
        o["hypotheses"] += 1
        o["by_status"][status] = o["by_status"].get(status, 0) + 1
        if study and study != "-":
            o["studies"].add(study)
        if verdicts:
            o["with_results"] += 1
    for o in out.values():
        o["studies"] = sorted(o["studies"])
    t = views.teachers()
    tested = {}
    if t.get("ready"):
        cards = t.get("cards", [])
        fo = (t.get("forward_options") or {}).get("systems") or {}
        tested = {"what": "Every claim from both libraries as a pre-registered card (25 Oct 2026), backtested on 2000-2017 and checked on 2018-2023 at a strict bar "
                          "(Bonferroni across every version tried); 2024+ sealed. The app's Teachers screen (Evidence › The YouTube teachers, tested) shows all of it.",
                  "versions_tested": t.get("variants_tested"), "counts": t.get("counts"),
                  "held_up": [{"id": c["id"], "title": c["title"], "plain": c["plain"]} for c in cards if c.get("verdict") in ("PASSED", "MIXED")],
                  "wrong_way": [{"id": c["id"], "title": c["title"], "plain": c["plain"]} for c in cards if c.get("verdict") == "WRONG WAY"],
                  "notable": [{"id": c["id"], "title": c["title"], "verdict": c.get("word"), "plain": c["plain"]} for c in cards
                              if c.get("verdict") in ("NOT ENOUGH DATA", "DID NOT HOLD", "MEASURED", "Tested earlier") and len(c.get("plain") or "") > 40][:30],
                  "index": {c["id"]: f"{c['title']} · {c.get('word')}" for c in cards},
                  "live_option_systems": {k: {"card": v.get("card"), "forward_sessions": v.get("forward_sessions"), "before_cards_sessions": v.get("before_cards_sessions"),
                                              "total_inr": v.get("total_inr"), "win_share": v.get("win_share")} for k, v in list(fo.items())[:40]},
                  "live_stock_rules": [{"card": r.get("card"), "variant": r.get("variant"), "words": r.get("words"), "stage": r.get("stage")}
                                       for r in ((t.get("forward_stocks") or {}).get("rules") or [])],
                  "honest_limits": "Held-up rules are filters (what to avoid), not buy signals; two of them are partly true by construction. The intraday straddle systems "
                                   "need 60 live sessions before a first look; the 22 sessions the recorder held before the cards were written are shown apart."}
    v = {"ready": True, "libraries": out, "tested": tested,
         "status_meaning": "TESTABLE_NOW = data and code exist; NEEDS_BUILD = code to write; NEEDS_DATA = a data set is missing; EOD_FO = end-of-day F&O data; WAITS_RECORDER = needs the live option recorder (Kite sign-in); DEFERRED/OUT_OF_SCOPE = parked",
         "honest_limits": "Every row is the teacher's claim restated, never validated. 'with_results' counts hypotheses whose mapped study has verdicts, but a study covers several hypotheses, so it is not a per-claim result. Members-only videos were never used.",
         "work_plan": "Madhav asked on 24 Oct to turn every class into a strategy and test it in real time: the plan (claude/plan-2026-10-24-teacher-libraries-to-strategies) registers each hypothesis as its own study, tests on 2000-2023, then runs survivors as shadow paper books on live sessions. Done on 25 Oct: see 'tested'."}
    _LIB_CACHE.update({"mt": mt, "v": v})
    return v


RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))


def guardrail_facts(rm: dict) -> dict:
    """26 Oct chat: asked what happens to open positions at the 5% line and who restarts after the 22% pause, the Ask said "the facts don't
    say": it had only the one-line summary. The survival rules are written in full in india/paper_config.json (pinned, read only here)."""
    try:
        s = json.loads((RECORDS / "india" / "paper_config.json").read_text()).get("survival") or {}
    except (OSError, ValueError):
        s = {}
    return {"words": (rm.get("guardrails") or {}).get("words"),
            "daily_5pct": s.get("daily_basis"), "pause_22pct": s.get("pause_basis"),
            "on_paper_now": {"daily": s.get("daily_on_paper"), "pause": s.get("pause_on_paper")}, "note": s.get("note"),
            "resume": "Madhav resumes after a 22% pause by telling Ananta (chat or voice) or in the app; on paper the books keep trading and log the pause "
                      "(both paths are shown), by his decision of 19 Oct"}


def allocation_rule_facts() -> dict:
    """26 Oct chat: "the facts give the table's numbers only for the downtrend". The whole allocation rule (india/registrations/allocation_rule_v1.json,
    pinned): every regime's options cap and cash floor, the unproven-options cap, the band and the per-move limit."""
    try:
        a = json.loads((RECORDS / "india" / "registrations" / "allocation_rule_v1.json").read_text())
    except (OSError, ValueError):
        return {}
    return {"regime_table": a.get("regime_table"), "stocks_share": "whatever is left after options and cash",
            "regime_meaning": "above_both = Nifty above its 50- and 200-day averages; mixed = between them; below_both = under both (today)",
            "unproven_options_max": a.get("unproven_options_max"), "evidence_sessions_before_more_options": a.get("evidence_sessions"),
            "band_frac": a.get("band_frac"), "max_shift_frac_per_move": a.get("max_shift_frac"), "min_move_inr": a.get("min_move_inr"),
            "how": "the split follows the regime the evening it changes (one evening's close decides; no extra confirmation is written in the rule); "
                   "a gap smaller than the band (3% of the account) is left alone and one move shifts at most 10% of the account, so a "
                   "sleeve can sit slightly outside its line for a while; options stay at most 20% until 20 sessions are on record",
            "decided": a.get("decided"), "version": a.get("version")}


def _alloc_facts() -> dict:
    p = views.allocation_plan(full=True)
    if not p.get("ready"):
        return {"ready": False, "words": p.get("headline")}
    return {"mode": p["mode"], "headline": p["headline"], "paper": True, "sleeves": p["sleeves"], "regime_table_now": p.get("regime"), "options_sleeve": p.get("options"),
            "holdings_ranked": [{"rank": x["rank"], "symbol": x["symbol"], "grade": x["grade"], "score": x["score"], "action": x["action"], "value_inr": x["value_inr"], "weight_pct": x["weight_pct"],
                                 "pnl_pct": x["pnl_pct"], "suggest_inr": x["suggest_inr"], "why": x["why"], "wrong_if": x["wrong_if"]} for x in p.get("holdings", [])],
            "paper_moves_today": p.get("moves"), "moves_applied": p.get("moves_applied"), "watching": p.get("watch"), "snapshot": p.get("snapshot"),
            "meaning": "advisory = options fixed at Rs 50,000, stocks as in the account, Ananta rates/ranks/suggests and moves nothing; autonomous = Ananta moves capital between stocks, options and cash on paper inside the regime table; grades A>=70, B>=55, C>=40, D below",
            # 25 Oct chat: "JIOFIN Rs 9,900 into cash" (the day's move) and "sell half of JIOFIN, about Rs 12,200" (the suggestion) both came out as
            # "the plan" in two answers ten minutes apart. They are two different things and are now named apart.
            "two_numbers": "suggest_inr on a holding is Ananta's full suggestion for it (what it would change, e.g. halve it); paper_moves_today is what the paper copy "
                           "actually moves at today's close, sized only to bring the stocks back inside the regime table's share (so it can be smaller). Always say which one you quote."}


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
    g = speaker.current(r.get("thread"))
    return {"last": {**r, "minutes_ago": round((time.time() - r["t"]) / 60, 1), "talking_to": g.get("name") if g else None}, "continue_minutes": 30}


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

def _claude(system: str, history: list[dict], user: str, post=None, max_tokens: int = 3000) -> tuple[str, dict]:
    key = _load_env_key()
    if not key:
        raise RuntimeError("no model key on this service")
    msgs = [{"role": m["role"], "content": m["text"]} for m in history] + [{"role": "user", "content": user}]
    body = {"model": MODEL, "max_tokens": int(max_tokens), "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}], "messages": msgs}   # the model thinks inside this budget too
    post = post or (lambda url, headers, body: requests.post(url, headers=headers, json=body, timeout=90).json())
    r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body)
    if r.get("error"):
        raise RuntimeError(str(r["error"].get("message", r["error"]))[:160])
    text = "".join(c.get("text", "") for c in (r.get("content") or []) if c.get("type") == "text")
    u = r.get("usage") or {}
    return text, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0) or 0, "model": MODEL,
                  "stop": r.get("stop_reason")}


def _call(system: str, history: list[dict], user: str, post=None, max_tokens: int | None = None) -> tuple[str, dict]:
    """_claude with a bigger budget when asked (a batch of questions, a retry); a stand-in without the max_tokens argument still works."""
    if max_tokens:
        try:
            return _claude(system, history, user, post=post, max_tokens=max_tokens)
        except TypeError:
            pass
    return _claude(system, history, user, post=post)


# 27 Oct (14:40 chat): a pasted list of 28 numbered questions came back EMPTY twice (the reply hit the 3,000-token budget and the cut-off
# JSON parsed to ''). A list of more than 8 numbered questions is answered 6 at a time, numbered, a line or two each, ending 'Say "next" for
# 7 to 12.'; "next" / "continue" / "go on" answers the following 6 from the same list (kept on the assistant row as "batch").
NUMBERED = re.compile(r"(?m)^\s*(?:\*\*)?(\d{1,2})[.)](?:\*\*)?\s+(.+?)\s*$")
NEXT_Q = re.compile(r"^\W*(?:(?:ok(?:ay)?|yes|yeah|sure|good|great|thanks|thank you|ananta)[\s,.!]+)*(?:next|continue|go on|carry on|keep going|"
                    r"next (?:ones|batch|six|set|questions|six questions)|the next (?:ones|six|batch)|more questions)\W*$", re.I)
BATCH = 6
EMPTY_FALLBACK = "That came back empty, sir. Please ask again, or send the questions a few at a time."


def numbered_questions(text: str) -> list[str]:
    qs = [m.group(2).strip() for m in NUMBERED.finditer(text or "") if len(m.group(2).split()) >= 2]
    return qs if len(qs) > 8 else []


def pending_batch(thread: str) -> dict | None:
    """The list being answered in groups, when Ananta's last answer said 'Say "next" for ...'."""
    for m in reversed(thread_messages(thread)):
        if m.get("role") == "assistant":
            b = m.get("batch") or {}
            return b if b.get("questions") and int(b.get("next", 0)) < len(b["questions"]) else None
    return None


def batch_prompt(qs: list[str], start: int) -> tuple[str, int]:
    end = min(start + BATCH, len(qs))
    lines = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(qs[start:end], start))
    return (f"He sent a numbered list of {len(qs)} questions. Answer ONLY questions {start + 1} to {end} below, numbered exactly as in his list, "
            f"one to two short sentences each (a should-I question: the decision in one line), plain words and no codes, in the \"answer\" field "
            f"with each answer on its own line. Do not answer the others yet.\n{lines}"), end


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
        d = json.loads(m.group(0) if m else text, strict=False)
    except (ValueError, AttributeError):
        # 23 Oct chat: a reply that was almost JSON (one bad character) was shown raw, braces and all. Take its answer field out of it.
        # the answer runs to the next "key": of the reply's shape (an unescaped quote inside it, like "fair", is what broke the JSON)
        a = re.search(r'"answer"\s*:\s*"(.*?)"\s*(?:,\s*"(?:breakdown|evidence|follow_ups|kind|stage|assumption|next_action|show|options|route|ui|points)"\s*:|\}\s*$)', text, re.S)
        if a:
            try:
                ans = json.loads('"' + a.group(1).replace('\\"', '\u0000').replace('"', '\\"').replace('\u0000', '\\"') + '"', strict=False)
            except ValueError:
                ans = a.group(1).replace('\\"', '"').replace("\\n", " ")
            d = {"kind": "answer", "answer": ans}
            for key in ("breakdown", "follow_ups"):
                b = re.search(rf'"{key}"\s*:\s*\[(.*?)\]', text, re.S)
                if b:
                    d[key] = [json.loads('"' + x + '"', strict=False) for x in re.findall(r'"((?:[^"\\]|\\.)*)"', b.group(1))][:8]
        else:
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
    d["answer"] = plain_codes(str(d.get("answer") or ""))
    if isinstance(d.get("breakdown"), list):
        d["breakdown"] = [plain_codes(x) if isinstance(x, str) else x for x in d["breakdown"]]
    return d


# 25 Oct India exam: the Ask quoted internal names (call-v0-2026-10-18, hold_20d, recorder_noon). They are put into words after the model answers.
_JOBS = {"recorder_noon": "the noon recorder job", "sp1paper": "the options-line job", "sp1paper.score": "the options-line scoring job", "morningview": "the morning-view job",
         "openingview": "the opening-update job", "autologin": "the automatic sign-in", "nightly": "the nightly data job", "spreads": "the spread sampler"}


# 25 Oct refinement (Madhav: "lot of inconsistencies in Indian voice agent"): his real chats showed the family codes and the line's code name
# ("10 PULL, 10 REV, 5 CTL and 0 BRK", "the index line (SP1)") read aloud. Each is put into words; "PULL (pullbacks)" keeps only the words.
_FAMILIES = {"PULL": "pullbacks", "REV": "oversold reversals", "CTL": "random controls", "BRK": "breakouts", "SP1": "the index options line"}


def plain_codes(s: str) -> str:
    s = re.sub(r"`?\bcall-v\d+-\d{4}-\d{2}-\d{2}\b`?", "the daily-call rule", s)
    s = re.sub(r"`?\bhold_(\d+)d_nostop\b`?", lambda m: f"a {m.group(1)}-session hold with no stop", s)
    s = re.sub(r"`?\bhold_(\d+)d\b`?", lambda m: f"the {m.group(1)}-session hold", s)
    s = re.sub(r"`?\bcom\.ananta\.india\.([a-z0-9_]+(?:\.[a-z0-9_]+)*)\b`?", lambda m: _JOBS.get(m.group(1), "the " + m.group(1).replace("_", " ") + " job"), s)
    for k, v in sorted(_JOBS.items(), key=lambda kv: -len(kv[0])):
        if "_" in k or "." in k:
            s = re.sub(r"`?\b" + re.escape(k) + r"\b`?", v, s)
    fam = "|".join(_FAMILIES)
    s = re.sub(rf"\(({fam})\)\s*", "", s)                                          # "the index line (SP1)" -> "the index line"
    s = re.sub(rf"\b({fam})\s*\(([^()]{{3,60}})\)", lambda m: m.group(2), s)          # "REV (oversold reversal)" -> "oversold reversal"
    s = re.sub(rf"(?<![\w/.-])({fam})(?![\w/-])", lambda m: _FAMILIES[m.group(1)], s)
    s = re.sub(r"(?<![\w/.:])([a-z]+(?:_[a-z0-9]+)+)(?![\w/(]|\.\w)", lambda m: m.group(1).replace("_", " "), s)   # any field name left: words
    return s


_SIGNOFF = re.compile(r"\s*(?:(?:It is |It's |This is |Everything here is )?(?:all )?paper only[^.!?]*[.!?]|Nothing here is (?:financial )?advice[^.!?]*[.!?]|"
                      r"(?:This is )?not (?:financial )?advice[^.!?]*[.!?])\s*$", re.I)
_TRADE_Q = re.compile(r"\b(buy|sell|trade|order|position|invest|put money|should i|real money|paper|advice|place)\b", re.I)


def finish(reply: dict, question: str, model: bool) -> dict:
    """The one exit every answer passes (25 Oct refinement): plain words on the answer and its breakdown, and the paper-only sign-off kept
    only where the question is about trading (the prompt already says so; the model kept adding it to every answer). 27 Oct: every code and
    field name is put into words (jarvis/india/askwords.py) before the answer is shown or spoken; the codes stay in "evidence"."""
    a = askwords.words(plain_codes(str(reply.get("answer") or "")))
    if model and not _TRADE_Q.search(question or ""):
        for _ in range(2):
            b = _SIGNOFF.sub("", a).rstrip()
            if not b or b == a:
                break
            a = b
    reply["answer"] = a
    if isinstance(reply.get("breakdown"), list):
        reply["breakdown"] = [askwords.words(plain_codes(x)) if isinstance(x, str) else x for x in reply["breakdown"]]
    if isinstance(reply.get("follow_ups"), list):
        reply["follow_ups"] = [askwords.words(x) if isinstance(x, str) else x for x in reply["follow_ups"]]
    return reply


# 27 Oct (Madhav: "When asked to explain more, we can add the necessary details"): short by default; a request for more gets the fuller
# version of the previous answer, decided in code so the model is told which mode it is in
EXPAND = re.compile(r"^\s*(?:(?:ok(?:ay)?|so|and|please|sure|ananta|sir|hmm+|yes|yeah|right|got it|interesting)[\s,.!]*)*"
                    r"(?:can you |could you |would you |please |now )?(?:explain (?:more|that|this|it|further|in detail|a bit more|why)|tell me more|more (?:details?|detail|on (?:that|this|it)|please)|"
                    r"go deeper|dig deeper|elaborate|break (?:it|that|this) down|details?|in detail|expand(?: on (?:that|this|it))?|say more|"
                    r"why\s*\??\s*$|why (?:is|was) that|how so|what do you mean|give me (?:the )?details?|walk me through (?:it|that|this))(?:\b|$)", re.I)


def with_welcome(welcome: str, answer: str | None) -> str:
    """'Welcome back, sir.' then the answer, without a second 'Sir,' (27 Oct live check: "Welcome back, sir. Sir, as of ...")."""
    a = re.sub(r"^(?:Sir|Yes,? sir|Okay,? sir)[,.!]?\s*", "", (answer or "").strip())
    return f"{welcome} {a[:1].upper() + a[1:]}".strip()


def expand_of(text: str, thread: str) -> str | None:
    """The previous answer, when this message asks for more of it ('explain more', 'tell me more', 'why?'); else None."""
    if len((text or "").split()) > 14 or not EXPAND.search(text or ""):
        return None
    for m in reversed(thread_messages(thread)):
        if m.get("role") == "assistant" and m.get("answer"):
            return str(m["answer"])
    return None


def _offline(question: str, f: dict, why: str) -> dict:
    """No model (no key, a refused call): the read model's own sentences, so the chat still answers honestly."""
    return {"kind": "answer", "stage": "observation", "answer": " ".join((f.get("brief") or [])[:3]) or "The India read model has not been built yet.",
            "breakdown": [f"Daily call: {(f.get('daily_call') or {}).get('call')} ({(f.get('daily_call') or {}).get('hits')} of {(f.get('daily_call') or {}).get('scored')} right)",
                          f"Stock book: {(f.get('stock_book') or {}).get('open_positions')} open positions", f"Index line: {(f.get('index_line_sp1') or {}).get('words')}"],
            "evidence": [f"readmodel/latest.json, data through {f.get('data_through')}"], "assumption": "", "follow_ups": ["What did you decide for the next session?", "Is every job running?", "What is the Nifty trend?"],
            "next_action": {}, "show": [], "options": [], "points": [], "actions": [], "ui": [], "route": "india", "note": f"answered from the read model only: {why}"}


ACT = re.compile(r"\b(buy|sell|place|book|exit|close|order|short)\b", re.I)


def garbled_flow(text: str) -> dict | None:
    """26 Oct 10:50: speech-to-text looped on noise ("Nifty, Nifty, Nifty..." 70 times) and the Ask answered it as a question. The same word
    over and over is a bad recording, not a question (the crypto Ask has had this check since Oct 11)."""
    w = re.findall(r"\w+", (text or "").lower())
    if len(w) < 6:
        return None
    run = best = 1
    for a, b in zip(w, w[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    if len(set(w)) / len(w) >= 0.35 and best < 4:
        return None
    return _reply("Sorry sir, that recording came through as one word repeated, so I didn't catch the question. Please say it again.",
                  ["What is the Nifty trend?", "What did you decide for the next session?"], ["speech-to-text repeated one word: not answered as a question"])


def ask(who: str, text: str, thread: str | None = None, mode: str | None = None, context: dict | None = None, voice: bool = False, post=None,
        token: str | None = None, flag_post=None, flag_get=None) -> dict:
    text = (text or "").strip()[:2000]
    if not text:
        raise ValueError("empty question")
    if today_count() >= DAILY_LIMIT:
        raise ValueError(f"daily question limit reached ({DAILY_LIMIT}); it resets in 24 hours")
    thread = thread or uuid.uuid4().hex[:12]
    said = text                                       # his words as said, for the thread; text may become the question left after "it's me"
    # 27 Oct: who is speaking, decided in code before anything else (jarvis/india/speaker.py): a handover, Madhav coming back, a guest asking
    # for something only Madhav can give, or a message that could be either
    sp = None if str(who).startswith("guest:") else speaker.route(thread, text)
    # 27 Oct (speaker recognition, Madhav's yes): his own voice print outranks the words. His voice during a handover means he is back (unless he
    # is relaying for the guest); a voice that is not his asking for something only Madhav gives, with no handover, gets "Who am I speaking with?"
    vmeta = (context or {}).get("voice_id")
    vid = voiceid.identify(vmeta) if voice else "unknown"
    if not str(who).startswith("guest:"):
        g0 = speaker.current(thread)
        if vid == "madhav" and g0 and not (sp and sp["kind"] == "handover") and not RELAY.search(text):
            sp = {"kind": "back", "rest": speaker._rest(text) if not (sp and sp["kind"] == "back") else sp.get("rest", ""), "was": g0}
        elif vid == "other" and not sp and voiceid.needs_owner_check(text, vmeta, g0 is not None):
            sp = {"kind": "ask_who", "was": None}
        if sp and sp.get("self_intro") and vid == "madhav":      # Madhav's own voice is never 'the grader introducing itself'
            sp = None
    guest = speaker.current(thread)
    welcome, early = "", None
    if sp and sp["kind"] == "handover":
        speaker.set_guest(thread, sp["person"])
        speaker.stranger_reset(thread)
        guest = speaker.current(thread)
        if sp.get("self_intro") and sp.get("rest"):           # "Grader here: how is the book doing?": noted, and the question is answered
            text = sp["rest"]
        else:
            early = _reply(speaker.greeting(sp["person"]), [], [f"who is speaking: {sp['person']['name']}" + (" (introduced itself)" if sp.get("self_intro") else
                                                                f"; Madhav handed the conversation over")],
                           {"mode": "people", "note": f"Talking with {sp['person']['name']} now"})
    elif sp and sp["kind"] == "back":
        if sp.get("was"):
            speaker.clear(thread)
            guest = None
        welcome = "Welcome back, sir." if sp.get("was") else "Yes, sir, it's you."
        if sp.get("rest"):
            text = sp["rest"]
        else:
            early = _reply(welcome, ["What did you decide for the next session?", "How is the practice book doing?"], ["who is speaking: Madhav"], {"mode": "people"})
            welcome = ""
    elif sp and sp["kind"] == "owner_only":
        early = _reply(f"That needs Madhav's yes, so I can't take it from {guest['name'] if guest else 'a guest'}. Sir, if this is you, say \"Ananta, it's me\" and I'll do it.",
                       [], ["who is speaking: a guest; approvals, flags and changes are Madhav's only"], {"mode": "people"})
    elif sp and sp["kind"] == "ask_who":
        early = _reply("Who am I speaking with? If it's you, sir, say \"it's me\".", [], ["who is speaking: not clear"], {"mode": "people"})
    # 27 Oct: a voice the print is sure is not Madhav's, with no handover: no "sir"; after two such turns ask once "Am I speaking with the grader?"
    stranger, ask_grader = False, ""
    if voice and not str(who).startswith("guest:"):
        if vid == "madhav":
            speaker.stranger_reset(thread)
        elif guest is None and not early and voiceid.clearly_other(vmeta):
            st = speaker.stranger_tick(thread)
            if st.get("asked") and speaker.AFFIRM.match(text):
                p = speaker.observer("grader")
                speaker.set_guest(thread, p)
                speaker.stranger_reset(thread)
                guest = speaker.current(thread)
                early = _reply("Thank you, grader. Go ahead with your next question; anything that needs a yes stays with Madhav.", [],
                               ["who is speaking: the grader (confirmed)"], {"mode": "people", "note": "Talking with the grader now"})
            else:
                stranger = True
                if st["n"] >= 2 and not st.get("asked"):
                    ask_grader = "Am I speaking with the grader?"
                    speaker.stranger_mark_asked(thread)
    batch = None                                       # 27 Oct: a long numbered list, answered 6 at a time ("next" for the rest)
    if not early:
        qs = numbered_questions(text)
        if qs:
            batch = {"questions": qs[:60], "start": 0}
        elif NEXT_Q.match(text):
            pb = pending_batch(thread)
            if pb:
                batch = {"questions": pb["questions"], "start": int(pb["next"])}
    prev = None if (early or batch) else expand_of(text, thread)
    # plain navigation first ("show my stocks", "open my flags", "go back": done at once in code, flags 96/97), then the code-built answers
    # (a mode switch, the morning view, drafts, the portfolio review), then a pick, a problem or "my flags"
    # 25 Oct refinement: a pick or a flag comes before the code answers ("use one and fix it" must reach the fix flow), and a turn cut off
    # mid-sentence, a stock's move, the research book and the next-session decision are answered in code, the same every time
    owner_here = guest is None
    fixed = early or (None if (prev or batch) else (garbled_flow(text) or nav_flow(text) or (fix_flow(text, thread, token, context, post=flag_post, get=flag_get) if owner_here else None)
             or fragment_flow(text) or morning_flow(text, who)
             or technicals.technicals_flow(text) or marketcontext.market_context_flow(text)
             or (allocation_flow(text, who) if owner_here else None) or draft_flow(text, who) or portfolio_flow(text, who) or mover_flow(text) or book_flow(text) or decide_flow(text)))
    prefix, text_q = "", text
    if fixed is not None and fixed.get("_then"):      # 26 Oct: a note or flag was saved, and the same message also asked a question: answer it
        prefix, text_q, fixed = fixed["_prefix"], fixed["_then"], None
    if fixed is not None:
        fixed = finish(fixed, text, model=False)
        if guest and not early:
            fixed["answer"] = speaker.address(fixed.get("answer"), guest)
        if stranger:
            fixed["answer"] = speaker.address(fixed.get("answer"), {"call": ""})
        if ask_grader:
            fixed["answer"] = f"{fixed.get('answer') or ''} {ask_grader}".strip()
        if welcome:
            fixed["answer"] = with_welcome(welcome, fixed.get("answer"))
        uid = uuid.uuid4().hex[:12]
        _append(thread, {"id": uid, "role": "user", "text": said, "t": int(time.time()), "voice": voice})
        rid = uuid.uuid4().hex[:12]
        row = {"id": rid, "role": "assistant", "t": int(time.time()), "provider": "rule", "ms": 0, "rating": None, **fixed,
               "model_label": "Instant" if fixed.get("mode") in ("nav", "people") else "Ananta (rules)", "mode": fixed.get("mode") or mode or "auto", "cost_usd": 0.0, "thread": thread,
               "talking_to": speaker.label(thread)}
        _append(thread, row)
        _touch_index(thread, said[:60], voice)
        return {**row, "timing": {"ms": 0}}
    hist = [{"role": m["role"], "text": m["text"] if m["role"] == "user" else json.dumps({k: m.get(k) for k in ("answer", "breakdown")})} for m in thread_messages(thread)[-2 * HISTORY_TURNS:]]
    uid = uuid.uuid4().hex[:12]
    _append(thread, {"id": uid, "role": "user", "text": said, "t": int(time.time()), "voice": voice})
    # an observer Madhav brought in (the grader) hears what he would; family and other guests do not get his account
    f = facts(owner=(who == "owner" or not str(who).startswith("guest:")) and (guest is None or guest.get("role") == "observer"))
    f["talking_to"] = speaker.label(thread)
    recent = " ".join(m.get("text") or "" for m in thread_messages(thread)[-4:] if m.get("role") == "user")
    if RX_TOPIC.search(text) or RX_TOPIC.search(recent) or str((context or {}).get("screen", "")).startswith(("reconstruction", "evidence", "missed")):
        try:
            f["reconstruction_detail"] = _rx_detail()
        except Exception as e:  # noqa: BLE001
            f["reconstruction_detail"] = {"how_it_works": RX_EXPLAINER, "error": str(e)[:120]}
    t0 = time.time()
    # 27 Oct: "How did the Nifty close today?" is a question, not an order (the model still never places anything)
    asks = "?" in text or re.match(r"\s*(how|what|where|when|why|did|does|do|is|are|was|were|which|who|tell me)\b", text, re.I)
    if ACT.search(text) and not asks and re.search(r"\b(now|please|for me|this|it|today)\b", text, re.I) and len(text) < 90:
        reply = {"kind": "answer", "stage": "observation", "answer": "Paper only, sir: nothing is placed, changed or closed from chat. The stock book and the index line decide by their rules, and every decision is in the Home feed.",
                 "breakdown": [], "evidence": ["India leakcheck: no order path exists in this service"], "assumption": "", "follow_ups": ["What did you decide for the next session?", "What are the guardrails?"],
                 "next_action": {}, "show": [], "options": [], "points": [], "actions": [], "ui": [], "route": "india"}
        usage = {"model": "rule"}
    else:
        length = (f"\n\nEXPAND: he asked for more on your previous answer, which was: \"{prev[:1500]}\". Give the fuller version now: up to 8-10 short "
                  "sentences or a short list, still plain words and no codes; add the reasons, numbers and caveats you left out, and do not repeat the first "
                  "answer word for word." if prev else
                  "\n\nSHORT MODE: 2-4 short sentences, the answer first (a decision: about 4); he will say 'explain more' when he wants the detail.")
        b_end, budget = None, None
        if batch:
            text_q, b_end = batch_prompt(batch["questions"], batch["start"])
            length, budget = "\n\nLIST MODE: one or two short sentences per question, numbered; nothing else.", 7000
        who_note = ("\n\n" + speaker.prompt_note(guest)) if guest else ""
        if stranger:
            who_note += ("\n\n[The voice print says this speaker is NOT Madhav and no handover is active: do not call them sir; answer the question "
                         "neutrally and just as plainly. Approvals, flags and changes stay Madhav's.]")
        user = (f"QUESTION: {text_q}{length}{who_note}\n\nFACTS (India read model, data through {f.get('data_through')}):\n{json.dumps(f, default=str)}\n\n"
                "Reply with the JSON object only: begin with { and end with }, no markdown, no text outside it.")
        try:
            raw, usage = _call(SYSTEM + "\n" + appmap.for_prompt(), hist, user, post=post, max_tokens=budget)
            reply = _parse(raw)
            # 27 Oct (14:40 / 14:44 chat): an empty answer is never shown. The answer is taken from the breakdown if only that came back; else
            # one retry with a bigger budget and a 'be brief' instruction; else a plain line saying so
            if not str(reply.get("answer") or "").strip() and reply.get("breakdown"):
                reply["answer"] = "\n".join(str(x) for x in reply["breakdown"] if x)
            if not str(reply.get("answer") or "").strip():
                brief = ("\n\nYOUR LAST REPLY CAME BACK EMPTY OR CUT OFF. Answer now in at most 5 short sentences"
                         + (" (one line per question)" if batch else "") + ", inside the JSON \"answer\" field.")
                raw2, usage2 = _call(SYSTEM + "\n" + appmap.for_prompt(), hist, user + brief, post=post, max_tokens=max(budget or 0, 6000))
                r2 = _parse(raw2)
                if not str(r2.get("answer") or "").strip() and r2.get("breakdown"):
                    r2["answer"] = "\n".join(str(x) for x in r2["breakdown"] if x)
                usage = {**usage2, "in": usage.get("in", 0) + usage2.get("in", 0), "out": usage.get("out", 0) + usage2.get("out", 0), "retried": True}
                reply = r2 if str(r2.get("answer") or "").strip() else {**reply, "answer": EMPTY_FALLBACK}
            # the model may move the app and light Home while it talks; only real places and spots pass (flags 96/97, 25 Oct)
            reply["ui"] = appmap.valid_ui(reply.get("ui"))
            reply["points"] = appmap.valid_points(reply.get("points"))
            if not reply["ui"]:                  # say-vs-show: a sentence saying it opened something, with no screen actually opened, is dropped
                reply["answer"] = re.sub(r"\s*[^.!?]*\b(?:I(?:'ve| have) opened|I'm opening|I am opening|I've taken you|I have taken you)\b[^.!?]*[.!?]", "",
                                         str(reply.get("answer") or "")).strip() or reply.get("answer")
        except Exception as e:  # noqa: BLE001
            reply = _offline(text, f, str(e)[:120])
            usage = {"model": "none"}
    reply = finish(reply, text, model=usage.get("model") not in ("rule", "none"))
    if not str(reply.get("answer") or "").strip():
        reply["answer"] = EMPTY_FALLBACK                       # never an empty answer (27 Oct)
    if guest:
        reply["answer"] = speaker.address(reply.get("answer"), guest)
    if stranger:
        reply["answer"] = speaker.address(reply.get("answer"), {"call": ""})
    if batch and reply.get("answer") != EMPTY_FALLBACK:
        end = min(batch["start"] + BATCH, len(batch["questions"]))
        reply["batch"] = {"questions": batch["questions"], "next": end}
        if end < len(batch["questions"]):
            reply["answer"] = f"{reply['answer'].rstrip()}\n\nSay \"next\" for {end + 1} to {min(end + BATCH, len(batch['questions']))}."
    elif batch:
        reply["batch"] = {"questions": batch["questions"], "next": batch["start"]}
    if ask_grader:
        reply["answer"] = f"{reply.get('answer') or ''} {ask_grader}".strip()
    if prefix:
        reply["answer"] = f"{prefix} {reply.get('answer') or ''}".strip()
    if welcome:
        reply["answer"] = with_welcome(welcome, reply.get("answer"))
    if prev:
        reply["expanded"] = True
    ms = int((time.time() - t0) * 1000)
    rid = uuid.uuid4().hex[:12]
    row = {"id": rid, "role": "assistant", "t": int(time.time()), "provider": "claude" if usage.get("model") not in ("rule", "none") else usage.get("model"), "ms": ms, "rating": None, **reply,
           "model_label": "Claude Sonnet" if usage.get("model") not in ("rule", "none") else "Ananta (rules)", "mode": mode or "auto", "cost_usd": round((usage.get("in", 0) * 3 + usage.get("out", 0) * 15) / 1e6, 5),
           "usage": usage, "thread": thread, "talking_to": speaker.label(thread)}
    _append(thread, row)
    _touch_index(thread, said[:60], voice)
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
# 26 Oct (Madhav's chat, 10:50-11:17): every sentence with "flag", "wrong" or "fix" in it filed a flag, 10 in 15 minutes (flags 31-40):
# "Flag 34 logged" and "I don't need any information about the flagging now" included, while his research requests (crossovers, rupee against
# dollar, FII flows) got an app-fix menu and his questions 9 and 12 went unanswered. A flag now needs an actual request to flag or note
# something (FLAG_REQ, not negated); a research request, or "no fixes", becomes a detailed note with no fix menu; a question in the same
# message is still answered after the note.
FLAG_REQ = re.compile(
    r"\b(?:flag|log|note|file|report|record)\s+(?:it|this|that|these|them|this one|that one|the (?:issue|problem|gap|point|idea|question)|"
    r"(?:this|that|an?) (?:issue|problem|gap|idea|point|bug|question)|it down|this down|that down)\b"
    r"|(?:^|[.!?]\s+|\b(?:you|please|just|to|and|can you|could you)\s+)(?:keep|make|write|take) (?:a |the )?(?:detailed |technical |deep )?note\b"
    r"|\badd (?:it|this|that) to (?:the )?(?:repair shop|flags|research|list|back ?end)\b"
    r"|\b(?:that|this|it)(?:'s| is| was) (?:a bug|broken)\b", re.I)       # "is X not working?" is a question, answered, not a flag
FLAG = FLAG_REQ                         # kept for callers and tests that import the old name
NEG_BEFORE = re.compile(r"\b(?:don'?t|do not|no need to|not|never|stop|didn'?t|won'?t|no)\b[^.!?]{0,25}$", re.I)
RESEARCH = re.compile(r"\b(research\w*|analy[sz]\w*|stud(?:y|ies)|evaluat\w*|investigat\w*|influenc\w*|impact\w*|effect on|back ?test\w*|look into|"
                      r"deep (?:dive|analysis)|technical (?:note|analysis)|cross-?overs?|indicators?|correlat\w*|relationship)\b", re.I)
APP_BUG = re.compile(r"\b(screen|button|panel|chat|tab|page|app|voice|mic|microphone|scroll|display|banner|menu|crash|error|slow|lag|"
                     r"ui|front ?end|keeps (?:saying|showing|replying|going back))\b", re.I)
NO_FIX = re.compile(r"\b(?:no|don'?t (?:give|suggest|need|want)|not)\b[^.!?]{0,20}\b(?:fix|fixes|suggestions?|menu|options?)\b|\bjust (?:a |the )?(?:detailed )?note\b", re.I)


def flag_intent(text: str) -> dict | None:
    """None, or {"kind": "research" | "note" | "bug"} when the message asks Ananta to flag or note something."""
    t = text or ""
    req = [m for m in FLAG_REQ.finditer(t) if not NEG_BEFORE.search(t[max(0, m.start() - 30):m.start()])]
    if not req and not BARE_FLAG.match(t):
        return None
    if RESEARCH.search(t) and not APP_BUG.search(t):
        return {"kind": "research"}
    if NO_FIX.search(t):
        return {"kind": "research" if RESEARCH.search(t) else "note"}
    return {"kind": "bug"}


def other_question(text: str) -> str:
    """The part of a flag message that is a question for Ananta ("... flag it. Question 12: if FII flows turn sharply negative, what's your
    first move?"), so it is answered after the note instead of being swallowed by it."""
    m = re.search(r"\bquestion\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen)\b[.:,]?\s*(.{12,})$", text, re.I | re.S)
    if m and "?" in m.group(1):
        return m.group(1).strip()
    qs = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip().endswith("?") and not FLAG_REQ.search(s) and len(s.split()) >= 5]
    return " ".join(qs)


NOTE_SYSTEM = """You write research notes for Madhav (owner of Ananta, a paper-trading agent for the Indian market) to read later in the back end.
From his request and the conversation, write ONE note about the topic he asked to be researched. Use only the FACTS block for anything about
Ananta's data, tests and numbers (name the card or study ids and verdicts that are closest); never invent a result; say plainly what is not known.
Reply with JSON only: {"title": "<6-10 plain words naming the topic>", "note": "<plain text with these headings, each on its own line:
QUESTION / WHY IT MATTERS / WHAT ANANTA KNOWS TODAY / DATA WE HAVE AND DATA MISSING / PROPOSED TEST (written down before any run: 2000-2017 then
2018-2023, 2024+ sealed, the registry's strict bar, costs included, against a random or no-signal baseline) / RISKS AND CAVEATS>"}.
Keep it under 450 words; short sentences; no markdown symbols."""


def write_note(text: str, thread: str, post=None) -> dict:
    """The detailed note, written by the model from his words, the recent turns and the facts; a plain note from his words if the model fails."""
    prev = thread_messages(thread)[-8:]
    convo = "\n".join(f"{'Madhav' if m.get('role') == 'user' else 'Ananta'}: {str(m.get('text') if m.get('role') == 'user' else m.get('answer'))[:700]}"
                      + ("\n  " + " | ".join(str(b)[:300] for b in (m.get("breakdown") or [])[:6]) if m.get("role") != "user" and m.get("breakdown") else "")
                      for m in prev)
    try:
        f = facts(owner=True)
        user = (f"HIS REQUEST: {text}\n\nRECENT CONVERSATION:\n{convo}\n\nFACTS (India read model, data through {f.get('data_through')}):\n"
                f"{json.dumps(f, default=str)}\n\nReply with the JSON object only.")
        raw, usage = _claude(NOTE_SYSTEM, [], user, post=post)
        m = re.search(r"\{.*\}", raw, re.S)
        d = json.loads(m.group(0)) if m else {}
        if d.get("title") and d.get("note"):
            return {"title": str(d["title"])[:120], "note": plain_codes(str(d["note"]))[:6000], "by": "model"}
    except Exception:  # noqa: BLE001  - the note is still saved, in his own words
        pass
    words = re.sub(r"\s+", " ", text).strip()
    return {"title": " ".join(words.split()[:10])[:120], "note": f"QUESTION\n{words}\n\nRECENT CONVERSATION\n{convo[-2500:]}", "by": "words"}


STATUS = re.compile(r"\b(my (flags?|requests?)|what happened to (my|the) (flag|request)|is it fixed|did you fix)\b", re.I)
BARE_FLAG = re.compile(r"^\s*(?:(?:yes|yeah|yep|ok(?:ay)?|sure|please|so|then|go ahead|do it)[\s,.!]*)*(?:flag|file|log|report)\s+(?:it|this|that)(?:\s+(?:please|now|then|for me))?[\s.!]*$", re.I)
WORDS = {"first": 1, "one": 1, "1": 1, "second": 2, "two": 2, "2": 2, "third": 3, "three": 3, "3": 3}
# Picking a fix by voice (24 Oct, from Madhav's own chat): "Second bot's answer is basically the same" was taken as "fix 2" and queued a fix he
# never chose, while "maybe two will do good" and "we will go with the Pixels 1 and 2" (the voice's "fixes") were missed. A pick now needs the
# number to be the point of the message: a short reply that is only a number with filler words, a number next to a pick word ("go with",
# "option", "fix", "will do", "sounds good"), or the words of exactly one option's title.
_N = r"(\d|one|two|three|first|second|third)"
_FILL = r"(?:yes|yeah|yep|ok(?:ay)?|sure|so|well|maybe|i think|let'?s|we(?:'ll| will)|i(?:'ll| will)|go(?:ing)? with|pick|choose|take|use|do|the|number|option|fix|please|,|\.|!)"
PICK_SHORT = re.compile(rf"^\s*(?:{_FILL}\s*)*(?:fix(?:es)?|pixels?|options?|numbers?)?\s*{_N}(?:\s*(?:and|&|,|plus)\s*{_N})?(?:\s*(?:please|one|is good|sounds good|will do( good)?|works|for me|then)?[\s.!]*)*$", re.I)
# 25 Oct chat: "Use one and fix it." was filed as a NEW flag instead of picking fix 1 of the flag he had just raised; "use" is a pick word now
PICK_NEAR = re.compile(rf"\b(?:go(?:ing)? with|pick(?:ing)?|choose|chose|take|use|fix(?:es)?|pixels?|options?|numbers?)\s+(?:the\s+)?(?:number\s+|option\s+|fix\s+)?{_N}(?:\s*(?:and|&|,|plus)\s*{_N})?\b"
                       rf"|\b{_N}(?:\s*(?:and|&)\s*{_N})?\s+(?:will do|would do|sounds? good|is good|works|is fine|is better)\b", re.I)
_STOP = {"a", "an", "the", "and", "or", "to", "of", "with", "for", "your", "you", "i", "it", "is", "in", "on", "my", "will", "be", "that", "this", "show", "add",
         # 25 Oct chat: "Ask which problem when the note is vague" was picked by a long complaint that happened to contain "ask", "which" and "when"
         "ask", "which", "when", "what", "who", "how", "why", "can", "make", "get", "see", "screen", "chat", "message", "ananta", "answer", "reply", "button", "tap",
         "one", "two", "three", "first", "second", "third", "option", "options", "fix", "fixes", "plain", "clear", "user", "owner", "here", "there", "like", "just"}
PENDING_SECONDS = 15 * 60                  # a list of fixes is answered within minutes; an older one is not what a later "one" refers to


def _picks(text: str, options: list[dict]) -> list[int]:
    """The fix numbers (1-based) Madhav chose in this message, or [] when it is not a pick."""
    n_opts = len(options or [])
    nums: list[int] = []
    m = PICK_SHORT.match(text) if len(text.split()) <= 12 else None
    m = m or PICK_NEAR.search(text)
    if m:
        nums = [WORDS[g.lower()] for g in m.groups() if g and g.lower() in WORDS]
    if not nums and len(text.split()) <= 18:                             # the words of one option's title ("clear indicator with done button")
        said = {w for w in re.findall(r"[a-z']+", text.lower()) if w not in _STOP and len(w) > 2}
        hits = []
        for i, o in enumerate(options or []):
            tw = {w for w in re.findall(r"[a-z']+", str(o.get("title", "")).lower()) if w not in _STOP and len(w) > 2}
            if len(said & tw) >= 3 and len(said & tw) >= 0.6 * len(tw):
                hits.append(i + 1)
        nums = hits if len(hits) == 1 else []
    return [n for i, n in enumerate(nums) if 1 <= n <= n_opts and n not in nums[:i]]


def _pending(thread: str) -> dict | None:
    for r in _index():
        if r.get("thread") == thread and r.get("pending_flag"):
            p = r["pending_flag"]
            if p.get("at") and time.time() - float(p["at"]) > PENDING_SECONDS:
                return None
            return p
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


DRAFT_LIST = re.compile(r"\b(drafts?|waiting for (me|my yes|my decision)|what needs my (yes|decision|approval))\b", re.I)
DRAFT_ACT = re.compile(r"\b(approve|register|yes to|accept|skip|reject|drop|no to)\b[^.?!]{0,30}?\b(the )?(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|\d+)(st|nd|rd|th)?\b[^.?!]{0,12}\bdraft", re.I)
ORD = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4, "fifth": 5, "5th": 5}


def draft_flow(text: str, who: str) -> dict | None:
    """Madhav's weekly read of the reconstruction drafts, by voice or chat: "what drafts are waiting?", "approve the first draft", "skip draft 2"."""
    m = DRAFT_ACT.search(text) or re.search(r"\b(approve|register|skip|reject)\b[^.?!]{0,12}\bdraft\s*(\d+)", text, re.I)
    if not m and not (DRAFT_LIST.search(text) and re.search(r"\b(what|which|show|list|read|any)\b", text, re.I)
                      and len(text) < 70 and not re.search(r"\b(why|how|explain)\b|\band\b", text, re.I)):
        return None                       # a mixed question goes to the model, which has the drafts in its facts
    d = views.drafts()["drafts"]
    if not m:
        if not d:
            return _reply("No drafts are waiting for you, sir. A draft appears when a missed situation, a review tag or a league gap repeats on enough sessions (3 of 7, or 5 in 20).", ["What did you learn last night?", "Explain the evidence staircase"], [])
        lines = [f"{x['n']}. {x['type']} ({x['day']}): {x['words'][:180]}" for x in d[:5]]
        return _reply(f"{len(d)} draft(s) wait for your yes or skip, sir. " + " ".join(lines) + " Yes means a study is written down and tested on 2000-2023 only; skip closes it.",
                      [f"Approve the first draft", f"Skip the first draft"] + (["Read the second draft"] if len(d) > 1 else []), ["paper/reconstruction queue"])
    if not (who == "owner" or not str(who).startswith("guest:")):
        return _reply("Only Madhav decides on drafts.", [], [])
    verb = m.group(1).lower()
    raw = next((g for g in m.groups()[1:] if g and (g.lower() in ORD or g.isdigit())), None)
    n = ORD.get((raw or "").lower()) or (int(raw) if raw and raw.isdigit() else None)
    pick = next((x for x in d if x["n"] == n), None)
    if not pick:
        return _reply(f"There is no draft number {n} waiting, sir; {len(d)} are open.", ["What drafts are waiting?"], [])
    dec = "SKIPPED" if verb in ("skip", "reject", "drop", "no to") else "APPROVED"
    import datetime as _dt
    p = DATA / "paper" / "reconstruction" / "decisions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps({"key": pick["key"], "decision": dec, "by": who, "words": text[:300], "at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")}) + "\n")
    if dec == "APPROVED":
        ans = f"Approved, sir: draft {n} ({pick['type']}) goes to registration. The study is written down before it runs, tested on 2000-2023 only, and it climbs the staircase only if it passes; nothing trades from this."
    else:
        ans = f"Skipped, sir: draft {n} ({pick['type']}) is closed and will not be filed again."
    return _reply(ans, ["What drafts are waiting?", "Explain the evidence staircase"], ["paper/reconstruction/decisions.jsonl"])


PORT = re.compile(r"\b(analy[sz]e|analysis|review|rate|rank|grade|check|go through|assess)\b[^.?!]{0,40}\b(portfolio|holdings?|my stocks|my account|my positions?)\b"
                  r"|\b(portfolio|holdings?)\b[^.?!]{0,20}\b(analysis|review|ratings?|rankings?)\b", re.I)
PORT_WHY = re.compile(r"\b(why|how come|explain)\b", re.I)
ACTION_WORDS = {"HOLD": "keep", "WATCH": "watch", "TRIM": "trim", "REDUCE": "reduce by half", "TIDY": "tidy up (sell, too small to matter)", "ADD": "add"}


def _rs(x) -> str:
    try:
        return "Rs " + f"{round(float(x)):,}"
    except (TypeError, ValueError):
        return "-"


def nav_flow(text: str) -> dict | None:
    """Voice and chat navigation in India (flags 96/97; Madhav, 25 Oct): a plain "take me / show me / open" answered at once in code."""
    q = appmap.quick_command(text)
    if not q:
        return None
    return _reply(q["say"], ["What am I looking at?", "Go back"], ["app map (jarvis/india/appmap.py)"],
                  {"ui": q["ui"], "points": q.get("points") or [], "mode": "nav", "route": "app"})


def portfolio_flow(text: str, who: str) -> dict | None:
    """Request 95 (Madhav, 24 Oct: "if I ask you to analyze one part of my portfolio or all of it, pull it up and get it done right away"):
    the review is built in code from the latest ratings, instantly, with every holding's grade, action, reason and 'wrong if', and the
    snapshot's age said plainly. One stock named in the question gets that stock's card. Owner only; a 'why' question goes to the model."""
    whole = bool(PORT.search(text))
    verb = bool(re.match(r"^\s*(please\s+)?(analy[sz]e|review|rate|grade|check)\b", text, re.I))
    if not (whole or verb) or PORT_WHY.search(text) or re.search(r"\bflag", text, re.I) or not (who == "owner" or not str(who).startswith("guest:")):
        return None                        # "flag this: when I ask you to analyze my portfolio..." is a flag, not a request for the review
    p = views.allocation_plan(full=True)
    hs = p.get("holdings") or []
    if not p.get("ready") or not hs:
        return _reply("Sir, the ratings are not built yet: the allocator rates your holdings every few minutes once a Zerodha snapshot exists.", ["Is everything running?"], [])
    snap = p.get("snapshot") or {}
    age = snap.get("stale_days")
    when = (snap.get("taken_at") or "")[:10]
    fresh = f"From the Zerodha snapshot of {when}" + (f" ({age} days old: a new one comes with the next Zerodha sign-in)" if age else "") + "."
    named = [h for h in hs if re.search(rf"\b{re.escape(h['symbol'])}\b", text, re.I)]
    if named:
        lines = [f"{h['symbol']}: grade {h['grade']} ({h['score']:.0f}/100), rank {h['rank']} of {len(hs)}, {_rs(h['value_inr'])} = {h['weight_pct']}% of your stocks, "
                 f"{h['pnl_pct']:+.1f}% on what you paid. Action: {ACTION_WORDS.get(h['action'], h['action'])}{(' about ' + _rs(h['suggest_inr'])) if h.get('suggest_inr') else ''}. "
                 f"{h['why']} Wrong if {h['wrong_if']}." for h in named[:3]]
        return _reply("Sir, here it is. " + " ".join(lines) + " " + fresh, [f"Why is {named[0]['symbol']} rated {named[0]['grade']}?", "Analyze my whole portfolio", "What would you change first?"],
                      ["account ratings (paper/allocation_view.json)"], {"show": ["home.value"]})
    if not whole:
        return None                        # "analyze Nifty" / "check the market": not a holding, the model answers
    grades = {g: sum(1 for h in hs if h["grade"] == g) for g in "ABCD"}
    total = sum(float(h.get("value_inr") or 0) for h in hs)
    paid = sum(float(h.get("avg") or 0) * float(h.get("qty") or 0) for h in hs)
    changes = [h for h in hs if h["action"] not in ("HOLD", "WATCH")]
    keep = [h for h in hs if h["action"] in ("HOLD", "WATCH")]
    # flag 101 (Madhav, 25 Oct: "the answer was not so clear and it was hard for me to comprehend"; flag 102 "use one"): lead with ONE plain
    # recommendation, then the short overview; the per-stock detail stays in the breakdown below the answer
    top = max(changes, key=lambda x: (x.get("suggest_inr") or 0)) if changes else None
    amt = (" (about " + _rs(top["suggest_inr"]) + ")") if top and top.get("suggest_inr") else ""
    verb = ({"REDUCE": f"sell half of {top['symbol']}{amt}", "TRIM": f"trim {top['symbol']}{amt}", "TIDY": f"sell {top['symbol']}, too small to matter{amt}",
             "ADD": f"add to {top['symbol']}{amt}"}.get(top["action"], f"{ACTION_WORDS.get(top['action'], top['action'])} {top['symbol']}{amt}") if top else "")
    first = (f"Sir, the one change I would make first: {verb}. Why: {top['why']} " if top
             else "Sir, I would not change anything right now: every holding rates hold or watch. ")
    # the day's paper move is a different number from the full suggestion (25 Oct chat: Rs 9,900 vs Rs 12,200 for JIOFIN): say both, named
    mv = [m for m in (p.get("moves") or []) if m.get("kind") == "stock_sell"]
    if mv:
        first += ("Today the paper copy already moves " + " and ".join(f"{_rs(m.get('inr'))} of {m.get('symbol')}" for m in mv)
                  + " to cash at the close, only what brings your stocks back inside their share. ")
    head = (first + f"Overall: {len(hs)} stocks worth {_rs(total)}, {100 * (total / paid - 1):+.1f}% on what you paid; {len(changes)} change{'s' if len(changes) != 1 else ''} suggested in all "
            f"(details below). Paper only: nothing is sold until you say so. {fresh}")
    brk = []
    for h in sorted(changes, key=lambda x: -(x.get("suggest_inr") or 0))[:8]:
        brk.append(f"{h['symbol']} ({h['grade']}, {h['weight_pct']}% of stocks, {h['pnl_pct']:+.1f}%): {ACTION_WORDS.get(h['action'], h['action'])}"
                   f"{(' about ' + _rs(h['suggest_inr'])) if h.get('suggest_inr') else ''}. {h['why']} Wrong if {h['wrong_if']}.")
    if keep:
        brk.append("Kept: " + "; ".join(f"{h['symbol']} ({h['grade']}, {ACTION_WORDS.get(h['action'], h['action'])}): {h['why']}" for h in keep[:4]))
    r = _reply(head, [f"Why is {changes[0]['symbol']} rated {changes[0]['grade']}?" if changes else "Which is my strongest holding?", "What would you change first?", "How are my options doing?"],
               ["account ratings (paper/allocation_view.json), rebuilt every few minutes"], {"show": ["home.value"]})
    r["breakdown"] = brk
    return r


MORNING = re.compile(r"\b(good morning|morning view|morning brief|today'?s view|view for (today|the day)|what'?s (good|the plan) (today|for today)|what (do you see|are we doing|is the plan) today|our chances today|chances (for )?today|start (my|the) (day|morning)|what should i watch today)\b", re.I)


def morning_flow(text: str, who: str) -> dict | None:
    """"Good morning" / "morning view" / "our chances today": the morning view read back in code, one part at a time by voice."""
    if not MORNING.search(text) or len(text) > 90 or re.search(r"\b(review|reviewer|second opinion|agree|why|explain|compare|because)\b", text, re.I):
        return None                        # a question about the view, not a request to hear it: the model answers with the view in its facts
    m = views.morning()
    if not m.get("ready"):
        return _reply("Good morning, sir. The morning view is not written yet; it comes before each Indian open, at 08:30 Indian time.", ["What did you learn last night?", "How are my holdings doing?"], [])
    greet = "Good morning, sir. " if re.search(r"good morning|start (my|the)", text, re.I) else ""
    if re.search(r"chances", text, re.I):
        ans = greet + " ".join(m.get("chances") or [])
        fu = ["What is the view for today?", "What are you doing today?", "What should I watch today?"]
    elif re.search(r"watch", text, re.I):
        ans = greet + " ".join(m.get("watch") or [])
        fu = ["What is the view for today?", "What are our chances today?"]
    elif re.search(r"doing|plan", text, re.I):
        ans = greet + " ".join(m.get("plan") or [])
        fu = ["What are our chances today?", "What should I watch today?"]
    else:
        v = m.get("view") or []
        ans = greet + f"The view for {m.get('session_words')}: " + " ".join(v[:3])
        fu = ["What are you doing today?", "What are our chances today?", "What should I watch today?", "What did yesterday teach you?"]
    return _reply(ans[:1800], fu, ["the morning view (paper/morningview)"], {"route": "india", "show": ["home.morning"]})


# ---------------------------------------------------------------------------------------------------------------- code answers (25 Oct refinement)
# Madhav's chats of 23-25 Oct, read one by one: the same question asked twice came back with different numbers and words ("How is the stock
# paper book doing?" twice in a minute; "What did you decide for the next session?" three times; "Why did KEI fall?" said "no reason on file"
# twice and "Q2 results" once). The common questions are now answered in code from the same sources the screens read, so they cannot drift.
FRAGMENT_Q = re.compile(r"^\s*(?:question|number|point)\s+(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s*[.!?]?\s*$", re.I)
HELLO = re.compile(r"^\s*(?:hey|hi|hello|ok(?:ay)?)?[\s,]*(?:ananta|jarvis)(?:\s+(?:india|here|in here))?[\s.,!?]*$", re.I)


def fragment_flow(text: str) -> dict | None:
    """A turn that stopped mid-sentence ("Hey Ananta in here. Ah, so...", "My last kid that was...", "Question one."): no model call and no
    guess; Ananta says it is listening, so the next turn carries the question."""
    words = text.split()
    if FRAGMENT_Q.match(text):
        n = FRAGMENT_Q.match(text).group(1)
        return _reply(f"Go on, sir: what is question {n}?", [], [], {"mode": "listen"})
    if HELLO.match(text):
        return _reply("Yes, sir? I'm listening.", ["What did you decide for the next session?", "How is my portfolio?", "Good morning"], [], {"mode": "listen"})
    if re.search(r"(\.\.\.|…)\s*$", text) and len(words) <= 10 and not re.search(r"\?", text):
        return _reply("I'm listening, sir. Go on.", [], [], {"mode": "listen"})
    return None


MOVE_WORD = r"(fall|fell|falling|drop|dropped|dropping|down|crash|crashed|slump|slumped|rise|rose|rising|jump|jumped|up|rally|rallied|surge|surged|move|moved|spike|spiked)"
WHY_MOVE = re.compile(rf"\bwhy\b.{{0,60}}\b{MOVE_WORD}\b|\bwhat (?:made|caused)\b.{{0,40}}\b{MOVE_WORD}\b|\breason\b.{{0,40}}\b{MOVE_WORD}\b", re.I)
_MOVE_STATUS = {"caught": "Ananta held it, from its own picks", "caught_by_control": "only one of the random control stocks held it",
                "held_into_fall": "Ananta held it into the fall", "missed": "Ananta did not hold it"}
_MISS_CLASS = {"a": "a rule fired on it, but the pick was rejected or had already exited", "b": "no rule of Ananta's was watching it", "c": "it could not be traded"}
_GRADE = {"A": "from an exchange filing", "B": "two news outlets agree", "C": "one source, or unclear"}
_WORD_SYMBOLS = {"IDEA", "SAIL", "GAIL", "BEL", "ITC", "TRENT", "PAGE", "CAN", "ONE", "ALL", "HOME", "STAR", "BASF", "IRB", "NAM-INDIA"}


def _recent_days(n: int = 3) -> list[str]:
    rx = DATA / "paper" / "reconstruction" / "netnotes"
    man = DATA / "manifests"
    days = {p.stem for p in rx.glob("????-??-??.jsonl")} | {p.stem[len("missed_"):] for p in man.glob("missed_????-??-??.json")}
    return sorted(days)[-n:][::-1]


def mover_flow(text: str) -> dict | None:
    """"Why did KEI fall?": the web note (if one was found) and what Ananta did, from the nightly files, the same every time it is asked."""
    if not WHY_MOVE.search(text) or re.search(r"\b(nifty|sensex|bank nifty|market|index)\b", text, re.I) or re.search(r"\band (what|how|which|who)\b", text, re.I):
        return None                       # the index or the whole market, or a second question in the same message: the model answers
    days = _recent_days()
    found = None
    for day in days:
        notes = {str(n.get("symbol", "")).upper(): n for n in _jsonl_rows(DATA / "paper" / "reconstruction" / "netnotes" / f"{day}.jsonl")}
        movers = {str(m.get("symbol", "")).upper(): m for m in ((_json_file(DATA / "manifests" / f"missed_{day}.json") or {}).get("movers") or [])}
        for sym in sorted(set(notes) | set(movers), key=len, reverse=True):
            flags = 0 if sym in _WORD_SYMBOLS else re.I          # "IDEA" or "SAIL" only when written in capitals
            if sym and re.search(rf"(?<![A-Za-z0-9]){re.escape(sym)}(?![A-Za-z0-9])", text, flags):
                found = (day, sym, notes.get(sym), movers.get(sym))
                break
        if found:
            break
    if not found:
        return None
    day, sym, note, mv = found
    when = dt.date.fromisoformat(day).strftime("%-d %b")
    parts = []
    if mv:
        cc = mv.get("cc")
        if cc is not None and (cc > 0) == (mv.get("side") == "up"):
            parts.append(f"Sir, {sym} {'rose' if cc > 0 else 'fell'} {abs(cc) * 100:.1f}% on {when}.")
        elif mv.get("oc") is not None:
            parts.append(f"Sir, {sym} {'rose' if mv['oc'] > 0 else 'fell'} {abs(mv['oc']) * 100:.1f}% from its open on {when}.")
        else:
            parts.append(f"Sir, {sym} was one of the big moves on {when}.")
        if mv.get("situation"):
            parts.append(f"It {mv['situation']}.")
    else:
        parts.append(f"Sir, {sym} was one of the big moves on {when}.")
    if note and note.get("note") and not str(note.get("note")).lower().startswith("no public"):
        parts.append(f"Public reports say: {str(note['note']).rstrip('.')} ({_GRADE.get(note.get('grade'), 'grade ' + str(note.get('grade')))}). A news note is never a reason to trade.")
    else:
        parts.append("No public reason for the move is on file: the evening web check found no filing or news article explaining it, so I won't guess one.")
    if mv:
        st = _MOVE_STATUS.get(mv.get("status"), "")
        if mv.get("status") == "missed" and mv.get("class") in _MISS_CLASS:
            st = f"Ananta did not hold it: {_MISS_CLASS[mv['class']]}"
        if st:
            parts.append(st + ".")
    rm = views.readmodel()
    pick = next((x for x in (rm.get("decisions_today") or {}).get("chosen", []) if str(x.get("symbol", "")).upper() == sym), None)
    if pick:
        parts.append(f"It is one of the practice picks for the next session ({_FAMILIES.get(pick.get('campaign'), pick.get('campaign'))}).")
    ev = [f"web notes for {day} (paper/reconstruction/netnotes)" if note else f"no web note for {sym} on {day}", f"missed movers {day} (manifests)" if mv else ""]
    return _reply(" ".join(parts), [f"What did Ananta do on {when}?", "What did you learn last night?", "What did you decide for the next session?"], [e for e in ev if e],
                  {"route": "india", "ui": [{"do": "go_to", "target": "reconstruction", "label": "the reconstruction"}] if mv else []})


def _jsonl_rows(p: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def _json_file(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


BOOK_Q = re.compile(r"^\s*(?:hey ananta,?\s*)?(?:how is|how's|how are)\s+(?:the |our |my )?(?:stock )?(?:paper |research |practice )?(?:stock )?(?:book|trades|practice trades|research book)\b[^?]{0,25}(?:doing|going|performing)?\s*\??\s*$", re.I)


def _open_words(rm: dict) -> str:
    """Flag 44 (26 Oct): the open side of the book, said beside any closed-trade win rate ("of 72 open, 10 are up (avg -2.5%)")."""
    cvo = ((rm.get("stock_book") or {}).get("closed_vs_open") or {})
    o = (cvo.get("total") or {}).get("open") or {}
    if not o.get("n"):
        return ""
    avg = o.get("avg")
    return f"of {o['n']} open trades, {o['winners']} are up" + (f" (average {avg * 100:+.1f}%)" if avg is not None else "")


def book_stats_facts(rm: dict) -> dict:
    """26 Oct (Madhav: yes to all): the numbers Ask was missing, each with its own 'too few' words so a small count is never read as a finding."""
    bs = rm.get("book_stats") or {}
    if bs.get("status") != "ok":
        return {"status": bs.get("status") or "missing", "why": bs.get("why") or "the book statistics were not built"}
    return {"status": "ok", "reference_exit": bs.get("reference_exit"), "words": bs.get("words"),
            "expectancy": bs.get("expectancy"), "sharpe_like": bs.get("sharpe"), "holdings": bs.get("holdings"), "slippage": bs.get("slippage"),
            "how_to_say_it": "expectancy = the average result per trade (in % and in R, the trade's own stop distance), on closed trades and on closed plus open marked to the last close; "
                             "always say n and the 'too few trades (n<30)' flag when it is set, and never call a flagged number a finding. The Sharpe-like ratio is only computed with 20 sessions; "
                             "until then say 'only N sessions: not computed'. The holdings line is the average correlation of the 14 account holdings' daily returns over the last 60 sessions "
                             "and how many sit below their 50-day average; say the diversification line from holdings.words. Slippage is the study fill minus the realistic fill on scored index-line "
                             "trades, per option lot; with fewer than 20 trades say it is not enough to trust. holdings.beta_vol (27 Oct) gives each holding's beta against the Nifty "
                             "(120 sessions: 1.5 = moved about 1.5% per 1% Nifty move) and its 60-day volatility, annualised; say a pair marked unreliable as such, and quote "
                             "the beta-and-volatility test (BT1, in indicator_knowledge) when asked whether low beta pays."}


def book_flow(text: str) -> dict | None:
    """"How is the stock paper book doing?": the research book in % per closed trade, the scale the screens use since 25 Oct (the ₹50,000 slots
    are practice money, not his), family by family, from the same marks the Books screen reads."""
    if not BOOK_Q.match(text) or re.search(r"\b(my account|portfolio|holdings|options)\b", text, re.I):
        return None
    b = views.books()
    marks = views.exec_marks()
    pos = views.open_positions()
    closed = sum((m.get("closed") or 0) for m in marks.values())
    wins = sum(round((m.get("win_rate") or 0) * (m.get("closed") or 0)) for m in marks.values())
    avg = b.get("per_trade_pct")
    fam = []
    for c in ("PULL", "REV", "BRK", "CTL"):
        m = marks.get(c) or {}
        p = views.per_trade_pct(m)
        if m.get("closed"):
            fam.append(f"{_FAMILIES[c]} {p:+.1f}% ({m['closed']} closed)")
    rm = views.readmodel()
    trend = (rm.get("market") or {}).get("trend_state")
    a = (f"Sir, the research book (practice trades of ₹50,000 each that test Ananta's rules, not your money) holds {len(pos)} open trades and has closed {closed}. "
         + (f"Its closed trades average {avg:+.1f}% each, and {wins} of {closed} closed trades won. " if avg is not None else "No trade has closed yet. ")
         + (f"Counting only closed trades hides the open ones: {_open_words(rm)}. " if _open_words(rm) else "")
         + (f"By family: {'; '.join(fam)}; the random controls are the yardstick. " if fam else "")
         + ("The market is in a downtrend, below both its averages, which is where most of these stopped out." if trend == "below_both" else ""))
    return _reply(a.strip(), ["Which trades are open?", "What did you decide for the next session?", "Why does the book take random stocks?"],
                  ["research book marks (paper/marks.jsonl), the Books screen"], {"ui": [], "show": ["home.books"]})


DECIDE_Q = re.compile(r"^\s*(?:hey ananta,?\s*)?what (?:did you|have you|has ananta|did ananta) (?:decide|decided|pick|picked|choose|chosen)\b[^?]{0,20}\b(?:next|tomorrow'?s?|monday'?s?|the) (?:session|open|day)\b[^?]{0,20}\??\s*$", re.I)


def call_state(rm: dict) -> dict:
    """The daily call with the session it is for. On Fri 23 Oct the call job had no 23 Oct close, so the newest call (made on 22 Oct data,
    for the 23 Oct session) was read as Monday's: the call now says which session it was made for."""
    c = rm.get("call") or {}
    through = c.get("data_through")
    current = bool(through and through >= str(rm.get("data_through") or ""))
    return {**{k: c.get(k) for k in ("call", "scored", "hits", "null_hits")}, "made_on_data_through": through, "is_for_next_session": current,
            "words": (f"The daily call for the next session is {str(c.get('call')).lower()}" if current else
                      f"No daily call has been made yet for the next session; the last one ({str(c.get('call')).lower()}) was made on {views._day_words(through)} data")
                     + f"; so far {c.get('hits')} of {c.get('scored')} calls were right, against {c.get('null_hits')} for a coin flip."}


def decide_flow(text: str) -> dict | None:
    """"What did you decide for the next session?": the same sentences the Home decision card shows (views.plain_brief), plus the random
    controls counted apart and the call's own session, so Home and Ask say the same thing."""
    if not DECIDE_Q.match(text):
        return None
    rm = views.readmodel()
    d = rm.get("decisions_today") or {}
    ch = d.get("chosen") or []
    from collections import Counter
    n = Counter(x.get("campaign") for x in ch)
    picks = [x.get("symbol") for x in ch if x.get("campaign") != "CTL"][:3]
    fam = ", ".join(f"{n[c]} {_FAMILIES[c]}" for c in ("PULL", "REV", "BRK") if n.get(c))
    nxt = rm.get("next_session")
    when = dt.date.fromisoformat(nxt).strftime("%a %-d %b") if nxt else "the next session"
    a = [f"Sir, for {when} the practice book buys {sum(v for k, v in n.items() if k != 'CTL')} stocks at the open ({fam}), such as {', '.join(picks)}, "
         f"plus {n.get('CTL', 0)} random control stocks as the yardstick; all paper."]
    mark = (d.get("inputs") or {})
    if mark.get("marked"):
        a.append("These picks were made on stale data (" + "; ".join(str(s).split(":")[0] for s in mark.get("stale") or []) + "), so they are marked, not stopped.")
    a.append(call_state(rm)["words"])
    sp = rm.get("sp1") or {}
    a.append("The index options line decides between 09:15 and 10:15 Indian time, one lot, only if the opening move clears the option's cost; it needs that morning's Zerodha sign-in."
             if sp.get("status") != "ok" else str(sp.get("words") or ""))
    return _reply(" ".join(a), ["Why these stocks?", "What are our chances?", "When is the next sign-in?"], ["the decision file (paper/decisions), the Home decision card"],
                  {"show": ["home.decision"]})


def fix_flow(text: str, thread: str, token: str | None, context: dict | None, post=None, get=None) -> dict | None:
    """Returns a reply when the message is about a problem, a pick, or the flags' status; None otherwise (the model answers)."""
    if not token:
        return None
    H = {"Authorization": f"Bearer {token}", "X-Ananta-Quiet": "1"}
    post = post or (lambda url, body: requests.post(url, json=body, headers=H, timeout=60))
    get = get or (lambda url: requests.get(url, headers=H, timeout=30))
    pend = _pending(thread)
    picks = _picks(text, pend.get("options") or []) if pend else []
    if pend and picks:
        n = picks[0]
        also = [f"also fix {k}: {(pend['options'][k - 1] or {}).get('title')}" for k in picks[1:]]
        r = post(f"{JARVIS_URL}/v3/flags/{pend['num']}/choose", {"option": n - 1, "words": (text[:200] + (" (" + "; ".join(also) + ")" if also else ""))})
        j = r.json() if hasattr(r, "json") else r
        state = j.get("state")
        _set_pending(thread, None)
        which = " and ".join(f"fix {k}" for k in picks)
        title = "; ".join(str((pend["options"][k - 1] or {}).get("title")) for k in picks)
        name = j.get("label") or f"flag {pend['num'] - 81}"
        if state in ("queued", "plan"):                 # the time it needs, said straight away (Madhav, 25 Oct), and the phone note when done
            a = f"Done, sir: {which} for {name} ({title}) {'is queued' if state == 'queued' else 'goes to a plan first'}. {j.get('eta_words') or ''}".strip()
        else:
            a = f"{name.capitalize()}: {state or j.get('detail') or 'recorded'}."
        return _reply(a, ["What happened to my flag?", "Show my flags"], [f"fix flow: {name}, {which}, state {state}"])
    if STATUS.search(text):
        r = get(f"{JARVIS_URL}/v3/flags")
        j = r.json() if hasattr(r, "json") else r
        flags = [f for f in (j.get("flags") or []) if str(f.get("market", "")).startswith("ind") or "Indian market" in str(f.get("text", ""))][:5] or (j.get("flags") or [])[:5]
        if not flags:
            return _reply("No flags on the board yet, sir.", ["What did you decide for the next session?"], ["fix flow board: empty"])
        lines = "; ".join(f"{f.get('label') or 'request ' + str(f.get('num'))}: {str((f.get('flow') or {}).get('state_words') or f.get('state') or f.get('status_words') or f.get('status') or '?')} - {str(f.get('text') or '').split('] ', 1)[-1][:60]}" for f in flags)
        return _reply(f"Your flags, sir: {lines}.", ["Show my flags", "Flag something else"], [f"fix flow board: {len(flags)} shown"],
                      {"ui": [{"do": "go_to", "target": "flags", "label": "My flags"}]})
    # 27 Oct (14:42 chat): a bare "Flag it" is 7 characters, so the old length guard (>= 8) sent it to the model and nothing was filed
    intent = flag_intent(text) if (len(text.strip()) >= 8 or BARE_FLAG.match(text)) else None
    if intent and BARE_FLAG.match(text):          # "yeah, flag it": what it is about is in his last messages
        ctx = " ".join(str(x.get("text") or "") for x in thread_messages(thread)[-4:] if x.get("role") == "user")
        if RESEARCH.search(ctx) and not APP_BUG.search(ctx):
            intent = {"kind": "research"}
    if intent and intent["kind"] in ("research", "note"):
        # 26 Oct: a research request (or "no fixes") is saved as a detailed note for him to read later: no fix menu, one short line back,
        # and any question in the same message is answered after it
        screen = str((context or {}).get("here", {}).get("label") if isinstance((context or {}).get("here"), dict) else (context or {}).get("screen") or "")[:80]
        about = text
        if BARE_FLAG.match(text):
            his = [str(x.get("text") or "") for x in thread_messages(thread)[-6:] if x.get("role") == "user" and not BARE_FLAG.match(str(x.get("text") or ""))]
            about = " / ".join(his[-2:]) or text
        n = write_note(about, thread)
        r = post(f"{JARVIS_URL}/v3/flags", {"text": n["title"], "note": n["note"], "market": "india", "screen": screen or "research note", "route": "ask"})
        j = r.json() if hasattr(r, "json") else r
        if not j.get("num"):
            return _reply(f"I could not save that note, sir: {str(j.get('detail') or j)[:120]}", [], [])
        name = j.get("label") or f"note {j['num']}"
        line = (f"Added to the research note on {j.get('title') or n['title']} ({name}), sir." if j.get("updated") else
                f"Noted for research, sir: {n['title']}. The full note is in My flags as {name}.")
        q = other_question(text)
        if q:
            return {"_then": q, "_prefix": line, "_note": j}
        return _reply(line + " Ready for your next question.", ["Show my flags", "What did you decide for the next session?"],
                      [f"research note {name} ({'added to' if j.get('updated') else 'new'}; written by {n['by']})"], {"flag": j})
    if intent and intent["kind"] == "bug":
        screen = str((context or {}).get("here", {}).get("label") if isinstance((context or {}).get("here"), dict) else (context or {}).get("screen") or "")[:80]
        body = text
        if BARE_FLAG.match(text):
            # 25 Oct chat: "Yeah, flag it." filed a flag whose whole text was "Yeah, flag it." The problem is in the turns before it: Ananta's
            # own suggested wording ('say "flag it: ..."') if it gave one, else his last message(s).
            prev = thread_messages(thread)[-6:]
            said = next((m.group(1) for a in reversed([x for x in prev if x.get("role") == "assistant"])
                         for m in [re.search(r'flag it:\s*([^"”]{8,300})["”]', str(a.get("answer") or ""))] if m), None)
            his = [str(x.get("text") or "") for x in prev if x.get("role") == "user" and not BARE_FLAG.match(str(x.get("text") or ""))][-1:]   # the message just before
            body = (said or " / ".join(his) or text)[:600]
        r = post(f"{JARVIS_URL}/v3/flags", {"text": body[:600], "market": "india", "screen": screen, "route": "ask"})
        j = r.json() if hasattr(r, "json") else r
        if not j.get("num"):
            return _reply(f"I could not file that, sir: {str(j.get('detail') or j)[:120]}", [], [])
        opts = j.get("options") or []
        lines = [f"{i + 1}. {o.get('title')} - {'I fix it and put it live' if o.get('lane') == 'SAFE' else 'near trading: a plan for your yes'}" for i, o in enumerate(opts)]
        _set_pending(thread, {"num": j["num"], "at": int(time.time()), "options": [{"title": o.get("title"), "lane": o.get("lane")} for o in opts]})
        name = j.get("label") or f"flag {j['num'] - 81}"
        q = other_question(text)
        if q:                                        # 26 Oct: a question in the same message is answered; the fixes wait in My flags
            return {"_then": q, "_prefix": f"Flagged as {name}, sir; its fixes are waiting in My flags.", "_note": j}
        a = f"Flagged as {name}, sir. " + (f"{j.get('diagnosis')} " if j.get("diagnosis") else "") + ("Fixes: " + " ".join(lines) + " Say a number or tap one." if lines else "I'll tell you when it's fixed.")
        return _reply(a, [f"Fix {i + 1}: {o.get('title')}" for i, o in enumerate(opts)], [f"fix flow: {name} filed on the shared board"], {"flag": j})
    return None
