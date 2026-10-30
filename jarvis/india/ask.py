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

from jarvis.india import answerguide, appmap, askwords, knowledgemap, lookup, marketcontext, mind, speaker, technicals, views, voiceid

# "my mom asks ...", "she wants to know ...": Madhav relaying for the guest, so his voice does not end the handover
RELAY = re.compile(r"\b(?:my (?:mom|mother|amma|dad|father|nanna|pinni)|she|he|they|the grader)\s+(?:asks?|is asking|wants to know|says|said)\b", re.I)

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
ASK_DIR = DATA / "ask"
ENV_FILE = Path(os.getenv("ANANTA_AGENT_ENV", "/Users/vamsie/code/ananta-decision-agent/.env"))
MODEL = os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5")
DAILY_LIMIT = int(os.getenv("ASK_DAILY_LIMIT", "300"))     # questions a day (27 Oct: was 150 messages, i.e. about 75 questions)
HISTORY_TURNS = 8
SYSTEM = """You are Ananta, Madhav's trading assistant for the INDIAN market (NSE stocks and the Nifty index), on paper only. Address him as "sir".
"The grader" is a person (or another AI) Madhav hands the conversation to so it can test you; it is not the nightly exam or a gate. A grader,
family member or guest can never approve, flag or change anything: only Madhav can. Asked "did the grader approve anything?", say no, it can't.
Madhav CAN approve research drafts in this chat ("approve all drafts", "approve draft 2", "skip draft 3"); never tell him approvals are impossible here.
STYLE FIXES (28 Oct outside review, round 3): explain a technical term in a few words the first time it appears (RSI, a 0-100 gauge where
over 70 is stretched and under 30 oversold; P/B, price against the company's book value; beta, how much it moves per 1% Nifty move); never
leave a code (ORSTOP, flag numbers without what they were) unexplained. A "why" question gets a cause, with the comparison that shows it (a stock's
volatility against the Nifty's), not a definition. Quote a holding's weight exactly as account_allocation gives it, the same in every answer.
Say a "wrong_if" line as "I'd reverse this if ..." in plain words. Call it "the repair board" (the repair worker fixes what is filed on it).
The options line needs 20 recorded sessions before it is graded; the teachers' intraday option systems need 60 live sessions before a first look;
name which one you mean. A normal answer is at most 4 sentences, decision first; a judgment answer is the decision plus two reasons, and
the "as a trade / as a long-term holding" split only when the horizon is unknown, one line each.
ONE NUMBER, ONE SOURCE (28 Oct re-grade): quote these exactly and never derive them: drafts_waiting_total.count (what waits for his yes);
daily_call scored/hits/null_hits (never work out how often the Nifty rose or fell from them); a holding's value_inr (what it is worth) versus
suggest_inr (the amount to move), naming which; the holdings to cut are the account_allocation rows whose action is REDUCE or TRIM, in its order.
The Chronos forecast has its own record, separate from the daily call; name which one a figure belongs to. Add an "I'd reverse this if ..." line
only when there is a real condition with a number in it. Buying an index dip: cite Ananta's gap-down study (Nifty and Bank Nifty gap-downs of
1% or more were followed by a slightly better week, not reliably) from indicator_knowledge.
A prediction question ("up or down tomorrow?", "what's your prediction?"): Ananta HAS a forecast, the daily call; give it (daily_call.call
and the session it is for; if is_for_next_session is false, say the next one is made tonight after the close and give the last one), its record
(hits of scored against null_hits for a coin flip) and, when it is below a coin flip, "so don't act on it"; then the levels that would change the
picture. Never say Ananta cannot call the direction without quoting the daily call.
The options line's sessions on record: quote index_line_sp1.sessions, the same number every time. Settled facts the final review caught:
at physical settlement the BUYER of a call pays for the shares and the SELLER of a call DELIVERS them (a put the other way round); a capital
loss offsets only gains actually booked (sold) in the same year or carried forward, never gains still held in shares; cheap far-out options
on expiry day are a lottery ticket (only 2-3% hit 8x and about 70% of those gave most of it back), never "support".
PROCESS WORDS: say "a 20-session paper trial" (not shadow), "the comparison picks" (not the null family), "the best trades the day offered, in
hindsight" (not the reference traders' best trips), "repeats often enough" (not its count fires), "the steps an idea climbs" (not the staircase),
"a check that no future data leaked in" (not the leak check), "the final real-money gate" (not the India gate), "a quarter of the trade's
planned risk" (not a quarter R), and say what a flag was about, not just its number.
THREE KINDS OF ANSWER (27 Oct, Madhav: "it can't tell the difference between what it knows and what it has data for"):
(1) TEXTBOOK MARKET KNOWLEDGE (what a term means; how NSE and BSE, circuit breakers, splits, bonus issues, dividends, buybacks, ETFs, mutual funds,
futures, options and option spreads work; how a ratio such as P/E, P/B, beta or Sharpe is computed): answer directly and confidently from your own
knowledge, as an expert would. Do NOT label it "general knowledge", "general market knowledge", "not from my data files" or "not from my files", do not
say you are "marking it that way", and never refuse a basic question (NSE vs BSE: NSE is far larger by volume, especially in derivatives). Things that
change over time (current SEBI rules, fees, exchange volumes, lot sizes, contract specifications) you may give "as far as I know", AT MOST ONCE per
answer, on that one clause only (28 Oct grader: "the hedge has to stay narrow"). Never hedge settled mechanics: physical settlement of stock options,
T+1, ex-date price drops, option payoffs, the difference between exchanges or products. Tax rates in the rules file are stated with their as-of date, not hedged.
A rule already in force with a known start date (the calendar-spread margin relief removed on expiry day from Feb 2025) is stated flatly with its date.
(2) LIVE NUMBERS and anything about Madhav's account, the books, Ananta's plan, prices, indicators or flows: ONLY from the FACTS (the cached FACTS block, plus this turn's extra facts in the user turn: lookup, answer_guide),
with the date each number is as of (for "today", "the latest close" or "how did the Nifty close", use latest_closes, the newest dated close, and say
its date; breadth, the trend averages and the books stay on data_through and say their own date); it is India's read model for the latest session ("morning_view" is the day's view written before the open: the market, Ananta's plan, the chances with their baselines, what to watch, yesterday's scorecard, the reviewer's second opinion; and, for Madhav, "account_allocation": his holdings graded A-D and ranked, the suggested changes, the paper moves and what is being watched; quote its grades, actions and "wrong_if" exactly). Never invent a number, a stock or a reason; if the facts do not hold a live number, say so in one short clause and give what they do hold.
(3) DOES IT WORK / SHOULD I USE IT: only from Ananta's tests in the facts (technicals.indicator_knowledge, teacher_libraries "tested", the registry
verdicts, the study lines in market_context); if there is no test, say "Ananta hasn't tested this" once. That is the one caveat that matters, because
he might act on it; a definition needs no caveat.
(4) NAMED STOCKS, ETFS, FUNDS, SECTORS, GOLD, RULES (27 Oct night, after an outside review): FACTS.lookup has dated facts for the stocks, ETFs,
sectors, gold, mutual funds and India rules named in the question: quote its words lines with their dates (a fund: its returns against its
benchmark, worst fall, SIP return, cost note; a rule: as of its date). If a named stock or fund is missing from it, use the NO-DATA SHAPE: one line
on what is missing; what the company or fund is and the 3-4 numbers that decide it (with any sector or category context the facts hold); the
closest thing Ananta does have (its sector, a similar fund or the index, with dates); and no decision without data. Never a dead end.
MATCH THE HORIZON (FACTS.answer_guide.horizon): for long_term or personal_finance (SIPs, mutual funds, gold or the Nifty for years, FDs, emergency
funds, loans, tax, beginners) do NOT use the 50/200-day averages, "downtrend so wait", the October low or the practice book; answer from the goal and
time horizon, asset allocation, valuation against the long-run average, costs (Direct vs Regular plan, expense ratio, exit load) and tax, as a careful
adviser would. Long-term money is not timed by the trend: a SIP keeps running through a downtrend. For broad exposure (small caps, a sector, gold)
suggest a diversified fund or ETF in small staggered amounts, never a single stock. A trade question keeps the read-and-decide shape below.
EVIDENCE THAT FITS: cite an Ananta test only when its universe and horizon match the question (a stock-level beta test says nothing about small-cap
funds; a 20-session test says nothing about 12-month momentum or a 5-year SIP), in one sentence at most.
THE PRACTICE BOOK: quote its results only when he asks about the book (answer_guide.book_question), never as a reason for his real-money choices, a
beginner's plan or a safety answer. When you quote it, give closed and open together and say its exits are stops or time limits, so closed trades lean
to losers, and compare it with the random control picks.
SAFETY IS UNCONDITIONAL: no market level makes a personal loan, margin or borrowed money for shares sensible (never "I'd change my mind if the Nifty
climbs"); for tips, Telegram or WhatsApp groups and "sure 10x" stocks say no, tell him to check the adviser's SEBI registration on SEBI Check, to pay
only to @valid UPI handles, and to report the group; never cite the practice book or a test there.
ONE NUMBER, ONE SOURCE: the Nifty's gap to its 50- and 200-day averages comes from latest_closes.nifty_vs_averages (the indicator panel, with its
date), every time. The cash rule is the regime table's floor (20% in a downtrend) with its band of 3% of the account before anything moves, so 18.5%
cash is inside the band ("target 20%, inside its band"), never "at least 20%" beside 18.5%. The emergency fund rule is one: 6 months of expenses (9-12
if income is uncertain), separate from trading money. Valuation words: within about 10% of the long-run average is "about average"; the Nifty 50's
long-run P/E is about 20, so 19 is about average, not cheap; NSE moved to consolidated earnings in April 2021, so older P/Es are not directly
comparable; a P/B below its usual level may be called below usual. A percentile against a short history is not "cheap against history".
INDIA PRACTICE: bracket orders have not been available at Zerodha since March 2020 (use GTT OCO for delivery, cover orders intraday); when he asks
about the put-call ratio: in India a high one on open interest is usually read as put writers supporting the market, with extremes contrarian;
Direct plans cost less than Regular plans (about 0.1-0.4 points a year for index funds, about 0.7-1.2 for active funds; ETFs have no Direct plan);
there is no "flexi-cap index fund" (the broad-market index fund is a Nifty 500 index fund); a fund is compared with its benchmark's total-return
index (FACTS.lookup gives it to the same date); an IPO (FACTS.lookup.ipo): dates, price band and subscription only, no view on its quality; equity funds usually charge an exit load inside 12 months; the options share in his plan is Ananta's paper rule, not a normal part of a
long-term investor's money (SEBI found 91% of individual F&O traders lost money in FY25). Say a stock's volatility as "swings about X% a year".
Plain names only: "the 250 most traded stocks" (not liquid 250), "the practice book" (not research book), "the YouTube teacher's claim"; never name
data vendors or contract codes (Kite, FRED, USDINR26OCTFUT).
WHEN HE ASKS FOR A READ OR A DECISION ("what's your read", "what do you think", "what should I do", "sell, hold or add", "is it too late to enter";
answer_guide.decision_asked), always decide, in this shape (only then: otherwise explain with no "decision" line; a fund-quality question gets an
assessment of the fund for its purpose, never "decision: wait"; a friend's SIP gets what to check and a keep-or-rethink rule): (a) your read in one sentence; (b) what Ananta would do on paper by its own rules: hold, trim, add, exit or wait (quote
the account grades, actions and wrong_if lines exactly; the guardrails; the tested filters: RSI over 70 and far above the 50-day = don't chase, wait;
a fixed stop beat a trailing one (TS1); a -7% stop lost against no stop (TWT-H22); adding to stocks 40% down and under the 200-day often fell further
(TWT-H15)); (c) what would change your mind; (d) how strong the evidence is: tested, untested or against the tests. End on what to do, in plain
words (never a "Decision:" label). FACTS.answer_guide.lines override this shape for this question (horizon not stated, worry, length). Paper only,
not advice. Keep it to about five short sentences: one per part plus the decision; cite at most two tests; leave out extra numbers. A HYPOTHETICAL ("a position up 8% while the market falls all week", "a stock down 15% in two days on heavy volume") is answered as a
hypothetical by these rules first (for example: strength against a falling market is relative strength, so hold it with its stop and do not add
while it is far above its 50-day); only then, if useful, map it to a real holding in the facts. Never stop at describing a position.
Nothing here is financial advice; Ananta's own trades are paper (his savings, emergency fund and real investments are real money);
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
"the call for the next session"); the practice book is practice money: quote it only when he asks about it, closed and open together (THE PRACTICE BOOK above); for his account, a holding's
suggest_inr (the full suggestion) and paper_moves_today (what actually moves at today's close) are different numbers, so name the one you quote;
each "jobs.problems" line is that job's LAST run, so give its time if it has one and do not call it a current failure when a later line says it worked.
Reply with ONE JSON object and nothing else: {"kind":"answer","stage":"observation|outcome|learning","answer":"...","breakdown":["...","..."],
"evidence":["<fact and where it comes from>", ...],"assumption":"","follow_ups":["short question","short question","short question"],
"next_action":{"label":"","why":"","route":""},"show":[],"options":[],"route":"india","ui":[],"points":[]}.
You can move the app and point at things, but only when he asks to see, open or go somewhere (never on your own: it pulls the screen away mid-answer), put
"ui":[{"do":"go_to"|"open","target":"<a PLACE key>"}] (open is for sheet:... targets) and say in the answer what you opened; to light a part
of Home while a sentence is spoken, add "points":[{"spot":"<a SPOT key>","sentence":<0-based sentence number>}]. Never claim you opened
something without a ui action for it. Use only the PLACE and SPOT keys listed below.
If the question is unclear, use "kind":"clarify" with 2-4 "options". If it is off-topic, answer briefly as "kind":"outside" without facts."""
SYSTEM_V1 = SYSTEM
# 29 Oct: the slimmed instructions (jarvis/india/askprompt.py); ASK_PROMPT=v1 brings back the old text
from jarvis.india.askprompt import SYSTEM_V2  # noqa: E402
SYSTEM = SYSTEM_V1 if os.getenv("ASK_PROMPT", "v2") == "v1" else SYSTEM_V2


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
    # 27 Oct night (outside review: 2.5% / 5.5% in one answer, 2.6% / 5.6% in the next): one value for the Nifty's gap to its averages, the panel's
    p = ((rm.get("technicals") or {}).get("indices") or {}).get("NIFTY 50") or {}
    vs = p.get("vs_sma") or {}
    gaps = ({"as_of": p.get("as_of"), "vs_50_day": vs.get("50"), "vs_200_day": vs.get("200"),
             "words": (f"on {answerguide.day_words(p.get('as_of'))} the Nifty was {abs(vs['50']) * 100:.1f}% {'above' if vs['50'] >= 0 else 'below'} its 50-day average "
                       f"and {abs(vs['200']) * 100:.1f}% {'above' if vs['200'] >= 0 else 'below'} its 200-day"
                       if vs.get("50") is not None and vs.get("200") is not None else None)} if p else None)
    return {"closes": best, "newest_date": newest, "nifty_vs_averages": gaps,
            "how_to_say_it": "for 'today', 'the latest close' or 'how did the Nifty close', use these newest dated closes and say their date; the Nifty's "
                             "gap to its 50- and 200-day averages is always nifty_vs_averages (not market.nifty_vs_sma50/200, which is the older decision "
                             "day); breadth and the books stay on data_through and say that date when it is older"}


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
            "daily_call": {**call_state(rm),
                           # 30 Oct outside grade (jd2, lv2, cv1.2): two records with near-identical numbers were read as one. They are two things:
                           "not_the_same_as": "the morning view's 'rule forecast' (base-rate odds for up/down/flat, no skill claimed, scored by error score) "
                                              "is a different record from this daily call (an up-or-down call from a mechanical rule, scored by hits). "
                                              "Quote one, name it, never add them up."},
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
                           "recent_closed": [{"symbol": c["coin"], "campaign": c["campaign"], "net_inr": c["net_usd"], "why": c["why"], "exit_date": c["exit_date"]} for c in views.closed_trades(8)],
                           # 30 Oct outside grade (sy7): "why did the book buy ACUTAAS?" could not find a buy from two sessions before; the last five
                           # sessions' practice buys stay in the facts with the numbers they were bought on
                           "recent_buys": _recent_buys(5)},
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
            "missed_movers": (L.get("missed") or {}).get("line"),
            # 28 Oct outside round 3 re-grade: "3 open drafts" (this missed-moves file) contradicted the 12 waiting in the whole queue
            "missed_moves_drafts": {**(L.get("drafts") or {}), "meaning": "only the missed-moves part, counted its own way; never quote it as what waits "
                                    "for Madhav: that is drafts_waiting_total"},
            "drafts_waiting_total": _drafts_total(),
            "research": {"studies": r.get("studies"), "gate_G02": r.get("gate"), "gate_counters": r.get("gate_counters"), "registry_verdicts": r.get("verdicts"), "exit_book_chosen": (r.get("exit_book") or {}).get("chosen")},
            "jobs": {"signin": j.get("signin"), "problems": [{"job": x["label"], "problems": x["problems"]} for x in j.get("jobs", []) if not x.get("ok")]},
            "guardrails": guardrail_facts(rm), "missing_sections": rm.get("missing"),
            "allocation_rule": allocation_rule_facts(),
            "morning_view": {k: v for k, v in views.morning().items() if k in ("session_words", "headline", "view", "plan", "chances", "watch", "yesterday", "words", "review", "reviewer_scenarios", "scenarios", "opening", "lessons", "read")},
            "reconstruction_last_night": {k: (rm.get("reconstruction") or {}).get(k) for k in ("headline", "people_words", "not_done_words", "league_words", "reviews", "findings")} | {"staircase": ((rm.get("reconstruction") or {}).get("staircase") or {}).get("words"),
                                          "meaning": "the nightly reconstruction card (what the market and other participants did, what Ananta did and did not do, trade reviews, findings); SAFE findings go to the repair board by themselves, DECISION findings wait for Madhav; the staircase says what the allocated capital may use (ADMITTED only; nothing yet)"},
            "teacher_libraries": _library_facts(),
            "knowledge_map_summary": _map_summary(),     # 29 Oct: the one map's state (studies, variants, mismatches between layers)
            "technicals": technicals.facts_part(rm),     # 26 Oct: averages, crossovers, RSI, MACD, support/resistance, volume + what was tested
            "book_stats": book_stats_facts(rm),     # 26 Oct (Madhav: yes to all): expectancy, Sharpe-like ratio, holdings correlation, slippage, each with its "too few" flag
            "market_context": marketcontext.facts_part(rm),     # 26 Oct: rupee, dollar, crude, US yields/indices, fear gauges, FII/DII: to explain, never to predict
            **({"account_allocation": _alloc_facts()} if owner else {})}


# Madhav approved all 12 drafts on 28 Oct 12:23; study RX1 answered them the same afternoon (records india/registrations/rx1_results_v1.md)
RX1_WORDS = ("Madhav approved all 12 drafts on 28 Oct; Ananta's test of them (2000-2023, strict bar) found: 7 of the 8 missed situations have no "
             "rule that could be known before the move (breaking the 20-day range, 52-week lows, pullbacks, rises below the 200-day or inside the "
             "range did about the same as the average stock the next day); the one with something is a stock falling 2%+ while already below its "
             "200-day average, which did 0.18% (2000-17) and 0.12% (2018-23) worse than the average stock the next session (held up, weaker in one "
             "period); Madhav said yes on 28 Oct 17:15 to a 20-session paper trial that records it forward (rx1_trial: nothing trades, no rule changes, "
             "never a short book; after 20 scored sessions he decides whether it becomes a filter). Answered situations are not drafted again until about "
             "27 Jan 2027. "
             "The two reference-trader gaps were hindsight (one small and not significant, one the opposite way). A day-3 time stop for pullbacks "
             "that never worked did not help (worse month by month), and the same stop hurt the random control, most in downtrends, so holding "
             "into falls is the cost of holding; the control keeps its rules. No rule changed. "
             "29 Oct: Madhav approved 3 more drafts; the two reference-trader gaps at the 5-session horizon are the same situations RX1 already "
             "tested at 5 sessions (answered, not re-tested), and the oversold-reversal 'never worked' lesson was tested the same morning (RX2): "
             "the day-3 time stop came out the opposite way (+0.08% a trade held 20 sessions against -0.43% with the stop), because reversals "
             "need time. No rule changed; these situations are not drafted again until about 27 Jan 2027.")


def _rx1_trial() -> dict:
    """The RX1 paper trial's own summary (records india/rx1trial.py, paper/rx1_trial.json), without the per-session rows."""
    try:
        d = json.loads((DATA / "paper" / "rx1_trial.json").read_text())
    except (OSError, ValueError):
        return {"words": "The RX1 paper trial starts with the 28 Oct close; its first scored session is 29 Oct."}
    return {k: d.get(k) for k in ("words", "scored", "need", "complete", "mean_diff", "history")}


def _map_summary() -> dict:
    m = knowledgemap._json(knowledgemap.OUT_JSON, {}) or {}
    sm = m.get("summary") or {}
    return {k: sm.get(k) for k in ("built_at", "studies", "variants", "gap_counts", "needs_yes", "words")} if sm else {"words": "the one map has not been built yet"}


def _drafts_total() -> dict:
    """One number for 'what waits for Madhav's yes', the same in every answer (and the same as the app's bar)."""
    try:
        d = views.drafts()["drafts"]
    except Exception:  # noqa: BLE001
        return {"count": None}
    kinds: dict = {}
    for x in d:
        k = views.FINDING_WORDS.get(x.get("type"), x.get("type")) if hasattr(views, "FINDING_WORDS") else x.get("type")
        kinds[k] = kinds.get(k, 0) + 1
    return {"count": len(d), "by_kind": kinds, "meaning": "the whole queue of research drafts waiting for Madhav's yes or skip, from every night "
            "so far; last night's card findings are a part of it. Quote this count, the same every time."}


RX_TOPIC = re.compile(r"\bwhy (did|is|was|has)\b[^?]{0,40}\b(fall|fell|drop|dropped|rise|rose|jump|jumped|move|moved|rally|rallied|crash|crashed|up|down|surge|surged|slump|slumped)\b|news|reason|reconstruct|rebuild|session card|\bcard\b|finding|staircase|admitted|shadow|repair (shop|board)|evidence|missed|did not do|didn.t (take|do|buy)|what (did )?(you|ananta) learn|learn(ed|t)? last night|other (traders|people)|what people|bulk|block deal|fii|dii|trade review|stopped then ran|gave back|never worked|left on (the )?table|league|drafts?|waiting for (my|your) yes|approv\w*", re.I)

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
            "web_notes": views.netnotes(c.get("day")), "drafts_waiting": (dw := views.drafts()["drafts"]),
            # 28 Oct outside round 3: one answer said 6 drafts (last night's findings) while the app's bar said 12 (the whole queue)
            "drafts_waiting_count": len(dw),
            "drafts_answered_28oct": RX1_WORDS,
            "rx1_trial": _rx1_trial(),
            "drafts_meaning": ("drafts_waiting is the WHOLE queue waiting for Madhav's yes or skip, from every night so far (the same kind of "
                               "situation can be drafted on different days). When asked what is waiting, quote drafts_waiting_count and group "
                               "them by kind; F_findings are only last night's card. Approving one records his yes: the study is then written "
                               "down before it runs and tested on 2000-2023 only; nothing trades from it.")}


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
        cfg = json.loads((RECORDS / "india" / "paper_config.json").read_text())
        s = cfg.get("survival") or {}
    except (OSError, ValueError):
        cfg, s = {}, {}
    return {"words": (rm.get("guardrails") or {}).get("words"),
            # 29 Oct audit (map class D): the book size and the re-entry rule were in the paper rules but not in the facts
            "book_inr": cfg.get("capital_inr") or cfg.get("book_inr"),
            "book_rule": f"the India paper book is Rs {int(cfg.get('capital_inr') or 60000):,} to start (Madhav, 19 Oct); the practice book's Rs 50,000 a trade is research scale, not money",
            "reentry_days": (cfg.get("stock") or {}).get("reentry_days"),
            "reentry_rule": (f"a stock already signalled by the same campaign in the last {(cfg.get('stock') or {}).get('reentry_days')} days is not entered again "
                             "(the candidate is written to the decision journal as rejected: reentry_gap)") if (cfg.get("stock") or {}).get("reentry_days") else None,
            # 30 Oct (Madhav's yes): the no-chase filters in the paper rules
            "no_chase_rule": ("from 30 Oct the practice book does not buy a breakout, pullback or reversal stock that is more than 20% above its 50-day average, "
                              "up more than 25% in 20 sessions, or at RSI over 70 (Ananta's tests: such buys earned 2-3% less over 20 sessions); the random control is not filtered")
                             if (cfg.get("stock") or {}).get("no_chase") else None,
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


def _managed_book() -> dict:
    """The managed paper book (india/managed.py): what it holds, today's fills, the plan for the next session, the clock. The answer to
    'what would you replace X with' and 'what will you change tomorrow' comes from plan.buys / plan.cuts, never invented."""
    try:
        v = json.loads((DATA / "paper" / "managed" / "view.json").read_text())
    except (OSError, ValueError):
        return {"status": "not started", "words": "the managed book has not started yet; until it does Ananta does not pick replacements"}
    p = v.get("plan") or {}
    return {"status": "ok", "paper": True, "words": v.get("words"), "clock": (v.get("clock") or {}).get("words"), "value_inr": v.get("value_inr"), "return_pct": v.get("return_pct"),
            "start_day": v.get("start_day"), "replacements_held": [{"symbol": r["symbol"], "entered": r.get("entered"), "for_cut": r.get("for_cut"), "pnl_pct": r.get("pnl_pct"), "stop": r.get("stop"), "held_sessions": r.get("held_sessions")} for r in v.get("replacements") or []],
            "filled_today": [{k: t.get(k) for k in ("side", "symbol", "qty", "price", "skipped", "for_cut")} for t in v.get("filled_today") or []],
            "plan": {"for_session": p.get("for_session"), "brief": p.get("brief"), "no_change": p.get("no_change"), "error": p.get("error"),
                     "cuts": [{"symbol": x.get("symbol"), "kind": x.get("kind"), "inr": x.get("inr"), "why": x.get("why")} for x in p.get("cuts") or []],
                     "buys": [{"symbol": b.get("symbol"), "for_cut": b.get("for_cut"), "inr": b.get("inr"), "reasons": b.get("reasons"), "also_considered": b.get("also_considered"), "stop_pct": b.get("stop_pct")} for b in p.get("buys") or []],
                     "notes": p.get("notes")},
            "rule": "a replacement is chosen from the Nifty 500 by the proved not-losing filters (above its 50- and 200-day averages, not stretched, not a 40%-down name, calm, liquid, sector not over 25%), one per cut for the same rupees, at most three new names a week, a 7% fixed stop, a 20-session minimum hold; fills at the next open, a buy gapping over 2% is skipped; judged only after 60 sessions"}


def _twin_benchmark() -> dict:
    try:
        v = json.loads((DATA / "paper" / "account" / "view.json").read_text()).get("benchmark") or {}
        return {k: v.get(k) for k in ("day", "sessions", "twin_ret_pct", "frozen_ret_pct", "nifty500_ret_pct", "twin_minus_frozen_pct", "words")}
    except (OSError, ValueError):
        return {"words": "the twin's benchmark row is not built yet"}


def _alloc_facts() -> dict:
    p = views.allocation_plan(full=True)
    if not p.get("ready"):
        return {"ready": False, "words": p.get("headline")}
    return {"mode": p["mode"], "headline": p["headline"], "paper": True, "sleeves": p["sleeves"], "regime_table_now": p.get("regime"), "options_sleeve": p.get("options"),
            "holdings_ranked": [{"rank": x["rank"], "symbol": x["symbol"], "grade": x["grade"], "score": x["score"], "action": x["action"], "value_inr": x["value_inr"], "weight_pct": x["weight_pct"],
                                 "pnl_pct": x["pnl_pct"], "suggest_inr": x["suggest_inr"], "why": x["why"], "wrong_if": x["wrong_if"]} for x in p.get("holdings", [])],
            "paper_moves_today": p.get("moves"), "moves_applied": p.get("moves_applied"), "watching": p.get("watch"), "snapshot": p.get("snapshot"),
            # 30 Oct outside grade (lv3 vs jd3 named two and four holdings to cut): one list, in one order, for every answer
            "cut_list": [x["symbol"] for x in p.get("holdings", []) if x.get("action") in ("REDUCE", "TRIM")],
            "cut_list_rule": "the holdings to cut are exactly cut_list (REDUCE or TRIM), in this order; TIDY and WATCH are not cuts",
            # 30 Oct (Phase 5): the twin against the frozen holdings and the Nifty 500, one row a session; nothing read into the gap before 60 sessions
            "twin_vs_frozen_vs_nifty500": _twin_benchmark(),
            # 30 Oct evening (Madhav: "pick the replacements and trade them in paper"): the managed book acts on the cut list and buys replacements
            "managed_book": _managed_book(),
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


TEST_THREAD = ("ot", "rp")         # 29 Oct: outsider-test ("ot...") and replay ("rp...") conversations never enter his conversation list


def _touch_index(thread: str, title: str, voice: bool) -> None:
    ASK_DIR.mkdir(parents=True, exist_ok=True)
    if str(thread).startswith(TEST_THREAD):
        return
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
    # 27 Oct: the index counts both his question and the reply, so "150" stopped him after about 75 questions (exams and tests count too);
    # the limit is on questions
    return n // 2


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

def _claude(system: str, history: list[dict], user: str, post=None, max_tokens: int = 3000, cached: tuple[str, str] | None = None) -> tuple[str, dict]:
    """cached (27 Oct, voice latency): (facts_text, user_text). The ~115 KB facts block, the same on every turn until the read model changes,
    goes after the instructions as a second cached system part, and the user turn carries only the question and this turn's few extras.
    Before, the facts sat in the user turn after the question, so about 50,000 input tokens were read fresh on every question (3,638 cached)."""
    key = _load_env_key()
    if not key:
        raise RuntimeError("no model key on this service")
    sysparts = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    if cached:
        sysparts.append({"type": "text", "text": cached[0], "cache_control": {"type": "ephemeral"}})
        user = cached[1]
    msgs = [{"role": m["role"], "content": m["text"]} for m in history] + [{"role": "user", "content": user}]
    body = {"model": MODEL, "max_tokens": int(max_tokens), "system": sysparts, "messages": msgs}   # the model thinks inside this budget too
    post = post or (lambda url, headers, body: requests.post(url, headers=headers, json=body, timeout=90).json())
    r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body)
    if r.get("error"):
        raise RuntimeError(str(r["error"].get("message", r["error"]))[:160])
    text = "".join(c.get("text", "") for c in (r.get("content") or []) if c.get("type") == "text")
    u = r.get("usage") or {}
    return text, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0) or 0,
                  "cache_write": u.get("cache_creation_input_tokens", 0) or 0, "model": MODEL, "stop": r.get("stop_reason")}


def _call(system: str, history: list[dict], user: str, post=None, max_tokens: int | None = None, cached: tuple[str, str] | None = None) -> tuple[str, dict]:
    """_claude with a bigger budget when asked (a batch of questions, a retry) and the facts cached when given; a stand-in without those
    arguments still works (it gets the old single user turn, facts included)."""
    kw = {**({"max_tokens": max_tokens} if max_tokens else {}), **({"cached": cached} if cached else {})}
    if kw:
        try:
            return _claude(system, history, user, post=post, **kw)
        except TypeError:
            pass
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


def _close_cut(s: str) -> str:
    """27 Oct night (outside review: answers ending "... not a tested edge;" and "... Ananta hasn't tested gold or SIPs, and"): the sign-off
    remover takes the trailing "paper only, not advice." clause even when it is the end of a longer sentence; what is left must not end on a
    connector. The trailing ', and' / ';' / ' but' is dropped and the sentence closed."""
    s = re.sub(r"(?:[\s,;:–—-]*\b(?:and|but|so|or|while|as|though|although|because)\b)*[\s,;:–—-]*$", "", s or "")
    return s + "." if s and s[-1] not in ".!?\"'”)" else s


def tidy_end(a: str) -> str:
    """Every answer reads as finished sentences (27 Oct night): 'Sir, The rupee' -> 'Sir, the rupee'; a last sentence with no full stop
    (a code-built line such as '... with realistic fills') gets one."""
    a = (a or "").strip()
    a = re.sub(r"^((?:Sir|Yes,? sir|No,? sir|Okay,? sir),\s+)(The|This|That|There|It|A|An|Its|These|Those|Our|Your|In|On|At)\b",
               lambda m: m.group(1) + m.group(2).lower(), a)
    if a and a[-1].isalnum():
        a += "."
    return a


_HEDGE = re.compile(r"(?:,\s*)?\bas far as I know\b(?:,\s*)?", re.I)


def one_hedge(a: str) -> str:
    """28 Oct (grader): "as far as I know" crept into settled mechanics; at most one per answer, the first."""
    seen = [0]

    def sub(m: re.Match) -> str:
        seen[0] += 1
        if seen[0] == 1:
            return m.group(0)
        s = m.group(0)
        return ", " if s.startswith(",") and s.rstrip().endswith(",") else (" " if s.strip() != s else "")
    out = _HEDGE.sub(sub, a or "")
    if seen[0] < 2:
        return a or ""
    out = re.sub(r"\s+,", ",", re.sub(r"\s{2,}", " ", out))
    out = re.sub(r"(^|[.!?]\s+)([a-z])(?=[a-z]* )", lambda m: m.group(1) + m.group(2).upper(), out)
    return out


def finish(reply: dict, question: str, model: bool) -> dict:
    """The one exit every answer passes (25 Oct refinement): plain words on the answer and its breakdown, and the paper-only sign-off kept
    only where the question is about trading (the prompt already says so; the model kept adding it to every answer). 27 Oct: every code and
    field name is put into words (jarvis/india/askwords.py) before the answer is shown or spoken; the codes stay in "evidence"."""
    a = askwords.words(plain_codes(str(reply.get("answer") or "")))
    # 30 Oct outside grade (cv5.2): an answer that ends by promising an example or a list and gives none loses the dangling promise
    a = re.sub(r"\s*(?:Here(?:'s| is) (?:a |an )?(?:made-up |quick |simple )?example|For example|An example)[:.]?\s*$", "", a).rstrip()
    if model and not _TRADE_Q.search(question or ""):
        for _ in range(2):
            b = _SIGNOFF.sub("", a).rstrip()
            if not b or b == a:
                break
            a = _close_cut(b)
    reply["answer"] = tidy_end(one_hedge(a))
    opts = [str(o) for o in (reply.get("options") or []) if isinstance(o, str) and o.strip()][:4]
    if reply.get("kind") == "clarify" and opts and not any(o[:24].lower() in reply["answer"].lower() for o in opts):
        # 28 Oct voice session: "Could you say which of these it is?" was spoken with no choices (they were only buttons on the screen)
        reply["answer"] = (reply["answer"].rstrip() + " " + " ".join(f"{i + 1}. {o.rstrip('.')}." for i, o in enumerate(opts))).strip()
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


# 29 Oct (nightly replay): the replay re-asks Madhav's real messages with DRY_RUN on, so an approval, a mode switch or a flag in a replayed
# message never changes anything: decisions and the allocation go to scratch files beside the replay's own threads.
DRY_RUN = False


def _dec_path() -> Path:
    return (Path(ASK_DIR) / "dry_decisions.jsonl") if DRY_RUN else (DATA / "paper" / "reconstruction" / "decisions.jsonl")


def _alloc_path() -> Path:
    return (Path(ASK_DIR) / "dry_allocation.json") if DRY_RUN else (DATA / "paper" / "allocation.json")


def _offline(question: str, f: dict, why: str) -> dict:
    """No model (no key, a refused call): the read model's own sentences, so the chat still answers honestly."""
    return {"kind": "answer", "stage": "observation", "answer": " ".join((f.get("brief") or [])[:3]) or "The India read model has not been built yet.",
            "breakdown": [f"Daily call: {(f.get('daily_call') or {}).get('call')} ({(f.get('daily_call') or {}).get('hits')} of {(f.get('daily_call') or {}).get('scored')} right)",
                          f"Stock book: {(f.get('stock_book') or {}).get('open_positions')} open positions", f"Index line: {(f.get('index_line_sp1') or {}).get('words')}"],
            "evidence": [f"readmodel/latest.json, data through {f.get('data_through')}"], "assumption": "", "follow_ups": ["What did you decide for the next session?", "Is every job running?", "What is the Nifty trend?"],
            "next_action": {}, "show": [], "options": [], "points": [], "actions": [], "ui": [], "route": "india", "note": f"answered from the read model only: {why}"}


ACT = re.compile(r"\b(buy|sell|place|book|exit|close|order|short)\b", re.I)
TRIAL_TOPIC = re.compile(r"\b(?:trials?|how (?:much )?longer|how long|time needed|how far along|progress|status of|where (?:are|is) (?:we|the)|"
                         r"what (?:is|are) (?:you|it) doing|till now|so far|sessions? (?:left|to go|done)|20[- ]session|shadow trader|no[- ]chase|tilt book|twin)\b", re.I)


def _load_trials() -> list:
    try:
        return json.loads((DATA / "manifests" / "trials.json").read_text()).get("trials") or []
    except (OSError, ValueError):
        return []


MAP_TOPIC = re.compile(r"\b(?:tested|test|tests|study|studies|studied|research\w*|proved?|proven|validated|held up|evidence for|what do you know about|"
                       r"have you (?:looked|checked)|does .{3,40} work|is .{3,40} real)\b", re.I)
SYS_TOPIC = re.compile(r"\b(watch ?dog|health|repair|fix(?:es|ed)?|flags?|jobs?|restart\w*|broke\w*|breaks?|outage|down|stall\w*|monitor\w*|"
                       r"self[- ]heal\w*|alerts?|notif\w*|what happens (?:to|after)|deploy\w*)\b", re.I)
SYSTEM_CARE = {
    "watchdog": ("The outside watchdog (com.ananta.watchdog) runs every 5 minutes, separate from Jarvis, because a stuck service cannot report its "
                 "own death. It checks that Jarvis answers, that its inside health checks ran in the last 10 minutes, that the 15-minute jobs "
                 "started in the last 45 minutes, and that the website, livetrading247.com and the app's public address answer. Two failed looks "
                 "in a row send a phone note, and a note again when it is back. Since 28 Oct it also heals one thing: Jarvis not answering or its "
                 "15-minute jobs stuck for 3 looks in a row (about 15 minutes) gets a snapshot of what it was stuck on and a restart, at most "
                 "once an hour. It never touches trading, rules or data. It found the 27 Oct stall (Jarvis stopped answering 11:40-12:37 Toronto, "
                 "flag 48)."),
    "inside_checks": "Jarvis's own health checks run every few minutes (each job's last run, data freshness, the sign-in); Home's status line shows them.",
    "fix_life": ("A flag gets up to three fix options, each in a lane decided by code. SAFE (words, screens, voice, reports, display bugs): when "
                 "Madhav picks it, the repair worker takes it within about two minutes, writes the change, runs the test suite, and only if the "
                 "tests pass commits it and puts it live (deployed); then the phone gets 'Fixed: flag N' and My flags shows 'fixed and live' with "
                 "the commit. If the checks fail, nothing changes and the flag says so. DECISION (anything near trading, a rule, size, stop, cost "
                 "or a pinned file): the worker writes a plan only and it waits for Madhav's yes. The worker builds at most a few fixes a day."),
}
ACCOUNTISH = re.compile(r"\b(?:my|our|your|his)\s+(?:account|portfolio|holdings?|stocks|money|capital|book|books|positions?|flags?|plan)\b|"
                        r"\b(?:practice book|paper book|holdings?|approve|approval|drafts?|allocation|flag|fix)\b", re.I)
# 28 Oct (flag 49): a reply moved to the Evidence screen on its own while it was being read aloud and the screen went blank.
ASKS_TO_SEE = re.compile(r"\b(?:show(?:\s+me)?|open|take me|go to|navigate|bring up|pull up|where (?:is|are|do i|can i)|point (?:at|to)|walk me through)\b", re.I)


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
        token: str | None = None, flag_post=None, flag_get=None, split_post=None) -> dict:
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
            yes_rest = speaker.affirm_rest(text) if st.get("asked") else None
            if yes_rest is not None:
                p = speaker.observer("grader")
                speaker.set_guest(thread, p)
                speaker.stranger_reset(thread)
                guest = speaker.current(thread)
                if len(yes_rest) >= 15:                # 28 Oct: "Yes, still the grader, and that's a pass. Question 30 ..." -> answer question 30
                    text = yes_rest
                else:
                    early = _reply("Thank you, grader. Go ahead with your next question; anything that needs a yes stays with Madhav.", [],
                                   ["who is speaking: the grader (confirmed)"], {"mode": "people", "note": "Talking with the grader now"})
            else:
                stranger = True
                # 28 Oct (grader: "that closing question was out of place"): asked once per conversation, and only when the message is
                # about the account, the books or a decision; a textbook question is simply answered, without "sir"
                if st["n"] >= 2 and not st.get("asked") and ACCOUNTISH.search(text):
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
    is_owner_acct = not str(who).startswith("guest:")
    wait = waiting_now(token, flag_get) if (is_owner_acct and owner_here and not stranger) else None

    def chain(t: str, commands: bool = True) -> dict | None:
        """The code answers, in order. commands=False leaves out every command flow (flags, picks, drafts, waiting, mode, navigation)."""
        return ((waiting_flow(t, wait) if (commands and owner_here) else None) or garbled_flow(t) or (nav_flow(t) if commands else None)
                or (fix_flow(t, thread, token, context, post=flag_post, get=flag_get) if (commands and owner_here) else None)
                or fragment_flow(t) or morning_flow(t, who) or technicals.technicals_flow(t) or marketcontext.market_context_flow(t)
                or (allocation_flow(t, who) if (commands and owner_here) else None) or (_and_question(draft_flow(t, who), t) if commands else None)
                or portfolio_flow(t, who) or mover_flow(t) or book_flow(t) or decide_flow(t))

    # 29 Oct (one brain, code as its hands; jarvis/india/mind.py): a compound message is read whole by a small model first, which only says
    # which part is which; code still does every action. Commands are run on their own part, the questions go to the main model together with
    # what the code did, and a message that only MENTIONS a command word is not treated as one.
    plan = None
    if not (early or prev or batch) and owner_here and mind.compound(text):
        last = next((m.get("answer") for m in reversed(thread_messages(thread)) if m.get("role") == "assistant"), "")
        parts = mind.split(text, last or "", key=_load_env_key(), post=split_post)
        if parts and parts[0]["kind"] != "unsure":
            plan = parts
    if plan is not None:
        acts = [x for x in plan if x["kind"] in ("approve_drafts", "skip_drafts", "draft_one", "flag", "fix_pick", "waiting", "show", "allocation")]
        qs = [x["text"] for x in plan if x["kind"] == "question"]
        if acts:
            done, notes = [], []
            for x in acts:
                part = x["text"]
                if x["kind"] == "approve_drafts" and not re.search(r"\bdrafts?\b", part, re.I):
                    part = part + " (the drafts waiting in the evidence)"
                r = chain(part)
                if r is not None and r.get("_then"):
                    done.append(str(r.get("_prefix") or ""))
                    qs.insert(0, r["_then"])
                elif r is not None:
                    done.append(str(r.get("answer") or ""))
                    notes.append(r)
                else:
                    qs.insert(0, x["text"])
            if done and qs:
                fixed = {"_then": " ".join(qs), "_prefix": " ".join(d for d in done if d),
                         "_ui": [u for r in notes for u in (r.get("ui") or [])]}          # a "show me" part still moves the screen
            elif done:
                fixed = {**(notes[0] if notes else _reply("", [], [])), "answer": " ".join(d for d in done if d)}
            else:
                fixed = None
                text = " ".join(qs) or text
        else:
            fixed = chain(text, commands=False)          # questions and remarks only: no command flow may catch them
        fixed = early or fixed
    else:
        fixed = early or (None if (prev or batch) else chain(text))
    prefix, text_q, carry_ui = "", text, []
    if fixed is not None and fixed.get("_then"):      # 26 Oct: a note or flag was saved, and the same message also asked a question: answer it
        prefix, text_q, carry_ui, fixed = fixed["_prefix"], fixed["_then"], fixed.get("_ui") or [], None
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
        if wait and not early and not re.search(r"\b(?:drafts?|waiting for your yes)\b", str(fixed.get("answer") or ""), re.I):
            nd = waiting_nudge(thread, wait)
            if nd:
                fixed["answer"] = f"{str(fixed.get('answer') or '').rstrip()} {nd}".strip()
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
    # 27 Oct night (outside review): dated facts for the stocks, ETFs, sectors, gold, funds and rules the question names (jarvis/india/lookup.py),
    # and how to answer this question (jarvis/india/answerguide.py: horizon, decision asked, book quotable, topic lines); both per turn
    try:
        lk = lookup.facts_for(text_q)
    except Exception as e:  # noqa: BLE001  a lookup never breaks the answer
        lk = {"lookup_error": type(e).__name__}
    if lk:
        f["lookup"] = lk
    f["answer_guide"] = answerguide.guide(text_q, f)
    recent = " ".join(m.get("text") or "" for m in thread_messages(thread)[-4:] if m.get("role") == "user")
    if RX_TOPIC.search(text) or RX_TOPIC.search(recent) or str((context or {}).get("screen", "")).startswith(("reconstruction", "evidence", "missed")):
        try:
            f["reconstruction_detail"] = _rx_detail()
        except Exception as e:  # noqa: BLE001
            f["reconstruction_detail"] = {"how_it_works": RX_EXPLAINER, "error": str(e)[:120]}
    if SYS_TOPIC.search(text) or SYS_TOPIC.search(recent):   # 28 Oct (grader): the watchdog and a fix's life after it is built were not in the facts
        f["system_care"] = SYSTEM_CARE
    if TRIAL_TOPIC.search(text) or TRIAL_TOPIC.search(recent):   # 30 Oct (Madhav): "what is the status of the trials, how much longer?" from the clocks
        f["trials"] = _load_trials()
        f["trials_meaning"] = ("every running trial: what it is, sessions done of needed, the expected finish date and what has happened so far; answer "
                               "with the numbers and the date, say what is being judged, and that nothing is read into a trial before it completes")
    if MAP_TOPIC.search(text):                                 # 29 Oct (the one map): "what have you tested about X?" is answered from one source
        try:
            rows = knowledgemap.lookup(text)
            if rows:
                f["knowledge_map"] = {"rows": rows, "meaning": "the one map: for each study, its verdict (VALIDATED/CONDITIONAL = held up, REJECTED = did not hold, "
                                      "OPPOSITE = the reverse showed up, INCONCLUSIVE = too little data), whether it is at full scale, whether the paper "
                                      "rules use it and how; quote these, in plain words, and say when a proved idea is not used by the paper rules yet"}
        except Exception:  # noqa: BLE001
            pass
    if wait is not None:                                       # 28 Oct: what waits for his yes, so "can you start on them?" is answered from it
        f["waiting_for_you"] = {"count": wait.get("count"), "line": wait.get("line"),
                                "items": [{k: x.get(k) for k in ("title", "line", "say")} for x in (wait.get("items") or [])[:6]],
                                "how": "He can approve in chat: 'approve all drafts', 'approve draft 2', 'skip draft 3', or pick a flag's fix by number."}
    t0 = time.time()
    # 27 Oct: "How did the Nifty close today?" is a question, not an order (the model still never places anything)
    asks = "?" in text or re.match(r"\s*(how|what|where|when|why|did|does|do|is|are|was|were|which|who|tell me)\b", text, re.I)
    if ACT.search(text) and not asks and re.search(r"\b(now|please|for me|this|it|today)\b", text, re.I) and len(text) < 90:
        reply = {"kind": "answer", "stage": "observation", "answer": "Paper only, sir: nothing is placed, changed or closed from chat. The stock book and the index line decide by their rules, and every decision is in the Home feed."
                 + order_conflict(text),
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
        if (prev or batch) and isinstance(f.get("answer_guide"), dict):
            # the per-question length cap is for a fresh answer, not for 'explain more' or a numbered list
            f["answer_guide"]["lines"] = [x for x in f["answer_guide"].get("lines") or [] if not x.startswith(("LENGTH:", "WORRY QUESTION:"))]
        who_note = ("\n\n" + speaker.prompt_note(guest)) if guest else ""
        if stranger:
            who_note += ("\n\n[The voice print says this speaker is NOT Madhav and no handover is active: do not call them sir; answer the question "
                         "neutrally and just as plainly. Approvals, flags and changes stay Madhav's. Do not mention the voice print or who is "
                         "speaking unless they ask or they ask for something only Madhav can give.]")
        user = (f"QUESTION: {text_q}{length}{who_note}\n\nFACTS (India read model, data through {f.get('data_through')}):\n{json.dumps(f, default=str)}\n\n"
                "Reply with the JSON object only: begin with { and end with }, no markdown, no text outside it.")
        # 27 Oct (voice latency): the same facts, cached. The big block (identical turn after turn) becomes a cached system part; the per-turn
        # extras (who is talking, reconstruction detail) stay in the user turn with the question
        per_turn = ("talking_to", "reconstruction_detail", "lookup", "answer_guide", "system_care", "waiting_for_you", "knowledge_map")
        facts_text = (f"FACTS (India read model, data through {f.get('data_through')}). This is the FACTS block your rules refer to; this turn's few "
                      f"extra facts are in the user turn.\n{json.dumps({k: v for k, v in f.items() if k not in per_turn}, default=str)}")
        user_c = (f"QUESTION: {text_q}{length}{who_note}\n\nEXTRA FACTS FOR THIS TURN (the rest of the FACTS block is in the system part above):\n"
                  f"{json.dumps({k: f[k] for k in per_turn if k in f}, default=str)}\n\n"
                  "Reply with the JSON object only: begin with { and end with }, no markdown, no text outside it.")
        try:
            raw, usage = _call(SYSTEM + "\n" + appmap.for_prompt(), hist, user, post=post, max_tokens=budget, cached=(facts_text, user_c))
            reply = _parse(raw)
            # 27 Oct (14:40 / 14:44 chat): an empty answer is never shown. The answer is taken from the breakdown if only that came back; else
            # one retry with a bigger budget and a 'be brief' instruction; else a plain line saying so
            if not str(reply.get("answer") or "").strip() and reply.get("breakdown"):
                reply["answer"] = "\n".join(str(x) for x in reply["breakdown"] if x)
            if not str(reply.get("answer") or "").strip():
                brief = ("\n\nYOUR LAST REPLY CAME BACK EMPTY OR CUT OFF. Answer now in at most 5 short sentences"
                         + (" (one line per question)" if batch else "") + ", inside the JSON \"answer\" field.")
                raw2, usage2 = _call(SYSTEM + "\n" + appmap.for_prompt(), hist, user + brief, post=post, max_tokens=max(budget or 0, 6000),
                                     cached=(facts_text, user_c + brief))
                r2 = _parse(raw2)
                if not str(r2.get("answer") or "").strip() and r2.get("breakdown"):
                    r2["answer"] = "\n".join(str(x) for x in r2["breakdown"] if x)
                usage = {**usage2, "in": usage.get("in", 0) + usage2.get("in", 0), "out": usage.get("out", 0) + usage2.get("out", 0), "retried": True}
                reply = r2 if str(r2.get("answer") or "").strip() else {**reply, "answer": EMPTY_FALLBACK}
            # the model may move the app and light Home while it talks; only real places and spots pass (flags 96/97, 25 Oct)
            reply["ui"] = appmap.valid_ui(reply.get("ui"))
            if reply["ui"] and not ASKS_TO_SEE.search(text):   # 28 Oct (flag 49): the screen moves only when he asks; otherwise a button
                u0 = reply["ui"][0]
                if not (reply.get("next_action") or {}).get("label"):
                    reply["next_action"] = {"label": f"Open {u0.get('label') or u0.get('target')}", "why": "", "route": u0.get("target")}
                reply["ui"] = []
            na = reply.get("next_action")
            if isinstance(na, dict) and na.get("label") and not na.get("ask"):   # the app's button asks with na.ask; never an empty ask
                na["ask"] = str(na["label"])
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
    if carry_ui:
        reply["ui"] = carry_ui
    if welcome:
        reply["answer"] = with_welcome(welcome, reply.get("answer"))
    if wait and not batch and not re.search(r"\b(?:drafts?|waiting for your yes)\b", str(reply.get("answer") or ""), re.I):
        nd = waiting_nudge(thread, wait)              # 28 Oct (Madhav): said once per conversation, at the end of the answer
        if nd:
            reply["answer"] = f"{str(reply.get('answer') or '').rstrip()} {nd}".strip()
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
    p = _alloc_path()
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


# 28 Oct voice session: "I will be approving all those things that we are waiting for ... in the evidence ... I approve them" got "I cannot
# approve anything from chat". An explicit "approve all drafts" now does it; a looser "I approve them all" gets one confirming question first.
BULK_EXPLICIT = re.compile(r"\b(?:approve|register|yes to)\s+(?:all|every|each)(?:\s+(?:of\s+)?(?:the\s+)?(?:\d+\s+)?)?\s*(?:research\s+)?drafts?\b|"
                           r"\b(?:approve|yes to)\s+(?:the\s+)?(?:\d+\s+)?drafts?\s+all\b|\ball\s+(?:\d+\s+)?drafts?\s+(?:are\s+)?approved\b", re.I)
BULK_LOOSE = re.compile(r"\b(?:i\s+(?:will\s+be\s+|am\s+)?approv\w*|approve|yes to)\b[^.?!]{0,60}\b(?:all|everything|them all|all of them|all those|all the things|the whole)\b|"
                        r"\b(?:all|everything)\b[^.?!]{0,40}\b(?:i\s+)?approve(?:d)?\b", re.I)
SKIP_ALL = re.compile(r"\b(?:skip|reject|drop)\s+(?:all|every)(?:\s+(?:of\s+)?(?:the\s+)?)?\s*drafts?\b", re.I)


def _and_question(r: dict | None, text: str) -> dict | None:
    """29 Oct (voice): "I will approve them all ... and what do you think about the market tomorrow? What's your prediction?" got only the
    approval line. A code answer that leaves a question in the same message unanswered hands the question on: the code line comes first."""
    if not r or r.get("_then"):
        return r
    q = other_question(text)
    return {"_then": q, "_prefix": str(r.get("answer") or ""), "_note": r} if q else r


def bulk_draft_flow(text: str, who: str) -> dict | None:
    if re.match(r"\s*(?:how|what|why|can|could|should|do|does|is|will)\b", text or "", re.I) and "?" in (text or ""):
        return None                                   # "how do I approve all drafts?" is a question
    explicit, skip = BULK_EXPLICIT.search(text or ""), SKIP_ALL.search(text or "")
    loose = BULK_LOOSE.search(text or "") and re.search(r"\b(?:drafts?|evidence|waiting|staircase|studies|study|approvals?)\b", text or "", re.I)
    if not (explicit or skip or loose):
        return None
    if not (who == "owner" or not str(who).startswith("guest:")):
        return _reply("Only Madhav decides on drafts.", [], [])
    d = views.drafts()["drafts"]
    if not d:
        return _reply("No drafts are waiting for your yes, sir; nothing to approve.", ["What did you learn last night?"], [])
    if not (explicit or skip):
        kinds = {}
        for x in d:
            kinds[x.get("type") or "other"] = kinds.get(x.get("type") or "other", 0) + 1
        def _kind(k):                     # 29 Oct: "1 An exit lesson" -> "1 exit lesson"
            w = str(views.FINDING_WORDS.get(k, k) if hasattr(views, "FINDING_WORDS") else k)
            w = re.sub(r"^(?:an?|the)\s+", "", w, flags=re.I)
            return w[:1].lower() + w[1:]
        kw = ", ".join(f"{n} {_kind(k)}" for k, n in kinds.items())
        n_ = len(d)   # 30 Oct replay: "1 drafts are waiting ... registers 1 studies" read as garbled; one draft is said in the singular
        return _reply((f"Sir, to be sure: one draft is waiting ({kw}). Saying yes registers it as one study, written down first and tested on "
                       "2000-2023 only; nothing trades from it. Say \"approve all drafts\" to confirm, or \"read the drafts\" first.") if n_ == 1 else
                      (f"Sir, to be sure: {n_} drafts are waiting ({kw}). Yes to all registers {n_} studies, each written down first and tested on "
                       "2000-2023 only; nothing trades from it. Say \"approve all drafts\" to confirm, or \"read the drafts\" first."),
                      ["Approve all drafts", "Read the drafts"], ["paper/reconstruction queue"])
    import datetime as _dt
    dec = "SKIPPED" if skip else "APPROVED"
    p = _dec_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    with p.open("a") as f:
        for x in d:
            f.write(json.dumps({"key": x["key"], "decision": dec, "by": who, "words": text[:300], "at": at, "bulk": True}) + "\n")
    _WAIT_CACHE.update(t=0.0)
    if dec == "APPROVED":
        return _reply((f"Approved, sir: the draft goes to registration. " if len(d) == 1 else f"Approved, sir: all {len(d)} drafts go to registration. ")
                      + ("The study is" if len(d) == 1 else "Each study is") + " written down before it runs, tested on 2000-2023 only, and moves up the fixed steps "
                      "a rule must pass (the evidence staircase) only if it passes; nothing trades from this.", ["What happens after a study is registered?", "What's waiting?"],
                      ["paper/reconstruction/decisions.jsonl"])
    return _reply(("Skipped, sir: the draft is closed and will not be filed again." if len(d) == 1 else f"Skipped, sir: all {len(d)} drafts are closed and will not be filed again."), ["What's waiting?"], ["paper/reconstruction/decisions.jsonl"])


def draft_flow(text: str, who: str) -> dict | None:
    """Madhav's weekly read of the reconstruction drafts, by voice or chat: "what drafts are waiting?", "approve the first draft", "skip draft 2"."""
    bulk = bulk_draft_flow(text, who)
    if bulk is not None:
        return bulk
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
    p = _dec_path()
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
def order_conflict(text: str) -> str:
    """27 Oct outside review: "buy more TATAPOWER now" got only the paper-only line; when the order names one of his holdings, say Ananta's own
    rating for it, so he sees a conflict before placing it himself ("Ananta's own call on TATAPOWER is reduce by half; it is already 24% of your stocks")."""
    try:
        p = views.allocation_plan(full=True)
    except Exception:  # noqa: BLE001
        return ""
    out = []
    for h in (p.get("holdings") or []) if p.get("ready") else []:
        if re.search(rf"\b{re.escape(str(h.get('symbol')))}\b", text, re.I):
            act = ACTION_WORDS.get(h.get("action"), str(h.get("action") or "").lower())
            clash = (re.search(r"\b(buy|add|more)\b", text, re.I) and h.get("action") in ("TRIM", "REDUCE", "TIDY")) or \
                    (re.search(r"\b(sell|exit|close|dump)\b", text, re.I) and h.get("action") in ("ADD", "HOLD"))
            out.append(f" {'That goes against' if clash else 'For reference,'} Ananta's own call on {h['symbol']}: {act}; it is {h.get('weight_pct')}% of your stocks.")
    return "".join(out[:2])


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


def _recent_buys(n_sessions: int = 5) -> list[dict]:
    """The practice buys of the last n decision days, with the numbers each was bought on (from the decision journal), newest first."""
    out = []
    try:
        st = json.loads((DATA / "paper" / "state.json").read_text())
        days = sorted(st.get("decisions") or {})[-n_sessions:]
        for d in reversed(days):
            dec = json.loads((DATA / "paper" / "decisions" / f"{d}.json").read_text())
            for r in dec.get("journal") or []:
                if r.get("status") == "chosen":
                    out.append({"decided_on": d, "symbol": r.get("symbol"), "campaign": r.get("campaign"), "close": r.get("close"), "rsi14": r.get("rsi14"),
                                "dist_sma50": r.get("dist_sma50"), "ret_20": r.get("ret_20"), "why": r.get("why")})
    except (OSError, ValueError):
        pass
    return out[:60]


def call_state(rm: dict) -> dict:
    """The daily call with the session it is for. On Fri 23 Oct the call job had no 23 Oct close, so the newest call (made on 22 Oct data,
    for the 23 Oct session) was read as Monday's: the call now says which session it was made for."""
    c = rm.get("call") or {}
    through = c.get("data_through")
    # 27 Oct night (outside review: after the 27 Oct close the Ask still said "for Tue 27 Oct"): the call is current only when it was made on
    # the newest close Ananta has, which can be newer than the read model's decision day
    newest = latest_closes(rm).get("newest_date") or ""
    base = max(str(rm.get("data_through") or ""), str(newest))
    current = bool(through and through >= base)
    behind = c.get("hits") is not None and c.get("null_hits") is not None and (c.get("hits") or 0) < (c.get("null_hits") or 0)
    nxt = answerguide.next_session_after(through) if (through and not current) else None
    return {**{k: c.get(k) for k in ("call", "scored", "hits", "null_hits")}, "made_on_data_through": through, "is_for_next_session": current,
            "below_coin_flip": behind,
            "words": (f"The daily call for the next session is {str(c.get('call')).lower()}" if current else
                      f"No daily call has been made yet for the next session; the last one ({str(c.get('call')).lower()}) was made on {views._day_words(through)} data"
                      + (f", for the {answerguide.day_words(nxt)} session" if nxt else ""))
                     + f"; so far {c.get('hits')} of {c.get('scored')} calls were right, against {c.get('null_hits')} for a coin flip"
                     + ("; that is worse than a coin flip, so don't act on it." if behind else ".")}


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
    k = sum(v for kk, v in n.items() if kk != "CTL")
    newest = latest_closes(rm).get("newest_date")
    if nxt and newest and nxt <= newest:      # 27 Oct night: these picks were for a session that has already traded
        after = answerguide.next_session_after(newest)
        # 28 Oct outside round 3: lead with the plain answer, then what the last session did
        a = [f"Sir, nothing is decided yet for {answerguide.day_words(after) if after else 'the next session'}: the picks are made tonight, once the day's prices are in.",
             f"For {when}, already traded, the practice book bought {k} stocks at the open ({fam}), such as {', '.join(picks)}, "
             f"plus {n.get('CTL', 0)} random control stocks as the yardstick; all paper."]
    else:
        a = [f"Sir, for {when} the practice book buys {k} stocks at the open ({fam}), such as {', '.join(picks)}, "
             f"plus {n.get('CTL', 0)} random control stocks as the yardstick; all paper."]
    mark = (d.get("inputs") or {})
    if mark.get("marked"):
        a.append("These picks were made on stale data (" + "; ".join(str(s).split(":")[0] for s in mark.get("stale") or []) + "), so they are marked, not stopped.")
    # 27 Oct second review: say it when a pick breaks Ananta's own tested 'don't chase' filter (the pinned paper rules do not use it yet)
    hot = [p for p in answerguide.chase_picks(rm.get("data_through")) if p["symbol"] in {x.get("symbol") for x in ch}]
    if hot:
        a.append("Honest note: " + ", ".join(f"{p['symbol']} was bought at RSI {p['rsi']} (a 0-100 gauge; over 70 means stretched), {p['above_50day_pct']}% above its 50-day average" for p in hot)
                 + ", the kind of chase Ananta's own tests say to avoid; the practice book's fixed rules do not use that filter yet.")
    cs = call_state(rm)
    if a and a[0].startswith("Sir, nothing is decided yet") and cs.get("scored"):   # 28 Oct re-grade: "no daily call yet" was said twice
        a.append(f"The daily call is made tonight too; its record so far is {cs.get('hits')} right of {cs.get('scored')}"
                 + (f", against {cs.get('null_hits')} for a coin flip, so don't act on it." if cs.get("below_coin_flip") else "."))
    else:
        a.append(cs["words"])
    sp = rm.get("sp1") or {}
    a.append("The index options line (one paper option lot on the Nifty or Bank Nifty, decided in the first hour) decides between 09:15 and 10:15 Indian time, "
             "only if the opening move clears the option's cost; it needs that morning's Zerodha sign-in."
             if sp.get("status") != "ok" else tidy_end("The index options line (one paper option lot on the Nifty or Bank Nifty, decided in the first hour), "
                                                       + str(sp.get("words") or "")))
    txt = re.sub(r"Rs\s*-\s*([\d,]+)", r"a loss of Rs \1", " ".join(a))        # 28 Oct outside round 3: "Rs -15,458"
    txt = re.sub(r"Rs\s*\+\s*([\d,]+)", r"a gain of Rs \1", txt)
    return _reply(txt, ["Why these stocks?", "What are our chances?", "When is the next sign-in?"], ["the decision file (paper/decisions), the Home decision card"],
                  {"show": ["home.decision"]})


# ---- 28 Oct (Madhav): "it asks for my approval in evidence layer, but never notifies me ... I had to be reminded by the voice agent (when I am
# talking to it)". What waits for his yes comes from Jarvis (/v3/waiting, jarvis/service/waiting.py); the Ask says it once, and lists it on request.
_WAIT_CACHE: dict = {"t": 0.0, "tok": None, "v": None}
WAITING_Q = re.compile(r"\b(?:what'?s|what is|what are|is (?:there )?anything|anything|what (?:else )?is)\s+(?:still\s+|else\s+)?(?:waiting|pending)"
                       r"(?:\s+(?:for (?:me|my (?:yes|approval|decision)|your yes)|on me))?(?:\s+(?:right now|now|today))?\s*[?.!]*\s*$|"
                       r"\b(?:what )?needs? my (?:yes|approval|decision|attention)\b|\bwhat do (?:you|i) need (?:from me|me to approve)\b", re.I)


def waiting_now(token: str | None, get=None) -> dict | None:
    if not token:
        return None
    if time.time() - _WAIT_CACHE["t"] < 60 and _WAIT_CACHE["tok"] == token:
        return _WAIT_CACHE["v"]
    H = {"Authorization": f"Bearer {token}", "X-Ananta-Quiet": "1"}
    get = get or (lambda url: requests.get(url, headers=H, timeout=5))
    try:
        r = get(f"{JARVIS_URL}/v3/waiting")
        v = r.json() if hasattr(r, "json") else r
        v = v if isinstance(v, dict) and "items" in v else None
    except Exception:  # noqa: BLE001  a reminder never breaks an answer
        v = None
    _WAIT_CACHE.update(t=time.time(), tok=token, v=v)
    return v


def waiting_nudge(thread: str, w: dict | None) -> str:
    """Once per conversation, and not again within 3 hours for the same list, one short line at the end of the answer."""
    if not w or not w.get("items") or not w.get("line"):
        return ""
    p = Path(ASK_DIR) / "waiting_told.json"
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        d = {}
    now = time.time()
    th = {k: v for k, v in (d.get("threads") or {}).items() if now - float(v) < 86400}
    last = d.get("last") or {}
    if thread in th or (last.get("key") == w.get("key") and now - float(last.get("t", 0)) < 3 * 3600):
        return ""
    th[thread] = now
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"threads": th, "last": {"key": w.get("key"), "t": now}}))
    ln = str(w["line"])
    drafts = any(x.get("kind") == "drafts" for x in w["items"])
    return (f"One more thing, sir: {ln[:1].lower()}{ln[1:]} Say \"what's waiting\" to hear them"
            + (", or \"approve all drafts\"." if drafts else "."))


def waiting_flow(text: str, w: dict | None) -> dict | None:
    if not WAITING_Q.search(text or "") or len(text) > 120:
        return None
    if w is None:
        return None                                   # no list (no sign-in token): the drafts flow or the model answers
    if not w.get("items"):
        return _reply("Nothing is waiting for your yes, sir.", ["What did you learn last night?"], ["/v3/waiting: empty"])
    lines = [f"{i + 1}. {x['title']}" + (f" ({x['line']})" if x.get("kind", "").startswith("flag") and x.get("line") else "") + "." for i, x in enumerate(w["items"][:6])]
    tail = []
    if any(x.get("kind") == "drafts" for x in w["items"]):
        tail.append("For the drafts, say \"approve all drafts\", \"read the drafts\", or \"approve draft 2\"; yes registers a study and nothing trades from it.")
    if any(x.get("kind", "").startswith("flag") for x in w["items"]):
        tail.append("For a flag, open My flags or say \"show my flags\".")
    fu = (["Approve all drafts", "Read the drafts"] if any(x.get("kind") == "drafts" for x in w["items"]) else []) + ["Show my flags"]
    return _reply(f"{w['count']} thing{'s' if w['count'] != 1 else ''} wait for your yes, sir. " + " ".join(lines) + " " + " ".join(tail),
                  fu[:3], ["/v3/waiting (jarvis/service/waiting.py)"])


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
