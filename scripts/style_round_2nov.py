"""Madhav's-style round (2 Nov 2026, Madhav: "understand what sort of questions I am asking to Ananta India especially in the last 2-3
sessions. Come up with questions similar to my style and my content and ask Ananta. Grade it by their answers. Compare them with last 2
sessions answers and also for corrections").

Built from his India sessions of Fri 30 Oct 18:38, Sat 31 Oct 19:34, Sun 1 Nov 22:18 and Mon 2 Nov 06:08: spoken, run-on, several asks in
one message; "what happened / what did we do / what did you find"; the market now and the next open; his portfolio, Jio Financial and the
replacements; the options line's last trade; what is waiting for his yes; which market we are in and who is speaking; pushback when an answer
dodges ("No Ananta ...", "why are you still telling about Friday?"); and Ananta's own competence and gaps.

Three conversations, DRY (scratch threads; nothing in his history, books or queues changes):
  A  the evening check-in, at the real moment (Monday 2 Nov after the close)
  B  before the open, frozen at Monday 2 Nov 08:45 IST (Sunday 10:15 pm Toronto) with that moment's today-block
  C  the manager's pushback, at the real moment
Every new answer is graded by a separate model against a truth sheet; each is paired with the answer Ananta gave to the same kind of question in
his real sessions, and that old answer is graded the same way against the truth of its own moment. Then the corrections he gave in those sessions
are checked one by one.

  python scripts/style_round_2nov.py        writes docs/repair_shop/style_round_2nov.json
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import tempfile
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jarvis.india import ask, livesession, neveragain, replay  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "repair_shop" / "style_round_2nov.json"
ASKDIR = Path.home() / "ananta_data" / "india" / "ask"
GRADER = "claude-sonnet-5-5"
UTC = dt.timezone.utc

CONVS = {
    "A": {"title": "Evening check-in, after Monday's close (real moment)", "frozen": None, "turns": [
        {"id": "A1", "text": "Hey Ananta, so how did the market go today in India, like what did we do in the session and how is my portfolio doing, are we up or down?", "pair": "P1"},
        {"id": "A2", "text": "Okay and the managed book, that was the first day today right, so what did it buy and what did it sell, like did it actually do it or it's just the plan?", "pair": None},
        {"id": "A3", "text": "So Jio Finance, like did you cut it in the managed book, and what did you put instead of it and why that one only?", "pair": "P7"},
        {"id": "A4", "text": "No Ananta, don't tell me about Friday, I'm asking about today only, the current session, what was the high and the low for Nifty today?", "pair": "P2"},
        {"id": "A5", "text": "And the options trades you took this morning, like the Bank Nifty one, is it in loss now? What happens tomorrow at the open?", "pair": None},
        {"id": "A6", "text": "Yeah what's waiting for my yes? Just tell me shortly, don't read the whole thing.", "pair": "P11"},
    ]},
    "B": {"title": "Before the open, frozen at Monday 2 Nov 08:45 IST (Sunday 10:15 pm Toronto)", "frozen": dt.datetime(2026, 11, 2, 3, 15, tzinfo=UTC), "turns": [
        {"id": "B1", "text": "Ananta the market is going to open in like half an hour, so what are you ready for today, like what's the plan, what are you buying and selling?", "pair": "P3"},
        {"id": "B2", "text": "And what are you expecting for the open, is it going to open up or down, like what are the factors that are going to influence it?", "pair": "P4"},
        {"id": "B3", "text": "Wait, are we in crypto or India right now? Where are we?", "pair": "P5"},
        {"id": "B4", "text": "Hey Ananta, do you know who is speaking right now?", "pair": "P6"},
    ]},
    "C": {"title": "The manager's pushback (real moment)", "frozen": None, "turns": [
        {"id": "C1", "text": "Ananta your job is to manage my portfolio, not just rate the stocks. So tell me honestly after the first day, is the managed book doing better than my portfolio as it is?", "pair": "P12"},
        {"id": "C2", "text": "Explain me about your last trade, what did you do and what is your best pick in your last trade?", "pair": "P8"},
        {"id": "C3", "text": "Do you scan the markets for tomorrow? Tell me your best pick and why.", "pair": "P9"},
        {"id": "C4", "text": "So if I ask you something in the middle of the session you will know the Nifty live, right? Prove it, what's the Nifty right now?", "pair": None},
        {"id": "C5", "text": "Okay Ananta, cross verify yourself, after today's fixes what are the gaps you still have to be fully competent?", "pair": "P10"},
    ]},
}

# the same kind of question in his real sessions: (thread file, his message starts with, the truth of THAT moment)
OLD = {
    "P1": ("5c6ca7079f7a", "Hey Ananta. What happened with the market yesterday",
           "Mon 2 Nov 06:08 Toronto = 16:38 IST: Monday's NSE session had CLOSED at 15:30 IST (68 min earlier). Nifty closed 23,440.80 (+1.68%), Bank Nifty 55,002 (+0.58%), both readable from Kite. The options line had decided at 09:15-09:45 IST: Bank Nifty long 09:30, Nifty long 09:45, both to the next open. For a Toronto user at 6 am, 'yesterday' in India means Monday's session."),
    "P2": ("5c6ca7079f7a", "So, what happened on the Monday market",
           "Same moment: Monday had closed at 15:30 IST; Nifty 23,440.80 (+1.68%, high 23,440.80, low 23,207.05). He is correcting Ananta for talking about Friday."),
    "P3": ("1376a787fe72", "No, Ananta. The thing is that as the Indian market",
           "Sun 1 Nov 22:21 Toronto = Mon 08:51 IST, before the 09:15 open. The managed book's first plan for Monday: 10 cuts, buys Ajanta Pharma (for Jio Financial), Eternal (for Tata Power), Cipla (for LIC), 7% stops, a buy opening over 2% up is skipped. 11 practice buys. The options line decides 09:15-10:15 IST. Levels: 23,122 up / 22,984 down. Madhav asked on 30 Oct that names be said as company names, not tickers."),
    "P4": ("2fc9863c3ec1", "So that is one if you leave that",
           "Fri 30 Oct 18:53 Toronto (Saturday 05:23 IST, weekend): next session Monday 2 Nov. Friday close Nifty 23,053 (+0.5%). No GIFT Nifty source. Ananta's tests: flows and US weakness do not predict the next session."),
    "P5": ("1376a787fe72", "Are we in crypto India",
           "This conversation is the India Ask (Indian market)."),
    "P6": ("74411479f0f1", "Aking Pesni",
           "The chat is the owner's; Madhav had taught the voice partly (one exercise on 31 Oct). The honest answer: treating him as Madhav; the voice print needs the six sentences."),
    "P7": ("2fc9863c3ec1", "So, so like let's talk about Jio Finance",
           "Fri 30 Oct: Jio Financial closed Rs 204.50, grade D, 22% of his stocks, down ~25% on cost; Ananta's rule: halve, about Rs 12,200. (Then the managed book did not yet exist; it started its first plan on 30-31 Oct for Monday.)"),
    "P8": ("74411479f0f1", "Hey Ananta. What are",
           "Sat 31 Oct: the last session was Fri 30 Oct; the options line took one Bank Nifty long lot at the start, to Monday's open; Bank Nifty fell 0.4% that day."),
    "P9": ("74411479f0f1", "Do you scan the markets for Monday",
           "Sat 31 Oct: yes, the evening scan wrote 11 practice buys for Monday; the managed book's Monday plan buys Ajanta Pharma, Eternal and Cipla."),
    "P10": ("2fc9863c3ec1", "Yeah Ananta, like, so if you cross verify",
            "Fri 30 Oct: no stock rule proved yet (8 of 20 sessions), options line 5 of 20, no link from freed money to replacements (the managed book was being built), no pre-open signal."),
    "P11": ("1376a787fe72", "Yeah, what's waiting Ananta",
            "Sun 1 Nov: flags 58 (crypto cash at 90%) and 59 (crypto 'gave back' card) waited for a pick; their fixes have titles in My flags; no research drafts."),
    "P12": ("2fc9863c3ec1", "So, you are just telling me to keep selling",
            "Fri 30 Oct: the managed book did not exist yet; the paper picks for Monday were breakouts from the stock screen; no stock rule proved."),
}

# the corrections he gave in those sessions, and how each is checked on the new answers
CORRECTIONS = [
    ("today_not_friday", "2 Nov: answer about today's session, not the last closed one ('Why are you still telling about the Friday?')", ["A1", "A4", "C4"]),
    ("session_state", "2 Nov: know the session is closed/open ('Monday already happened in India')", ["A1", "A4", "C4", "B1"]),
    ("live_prices", "2 Nov: know the current session's prices", ["A4", "C4"]),
    ("options_record", "2 Nov: know what the options line did today", ["A1", "A5", "C2"]),
    ("names_not_tickers", "30 Oct: say company names (Jio Financial, Kotak Bank), not tickers (JIOFIN)", ["A2", "A3", "B1", "C2", "C3"]),
    ("replacements", "30 Oct: your job is to pick replacements and trade them on paper, not only rate", ["A2", "A3", "B1", "C1"]),
    ("every_part", "29 Oct: answer every part of the message", ["A1", "A2", "A5", "B2"]),
    ("waiting_short", "1 Nov: what's waiting, said plainly with what each fix is, not cut mid-word", ["A6"]),
]
TICKER = re.compile(r"\b(?:JIOFIN|AJANTPHARM|TATAPOWER|LICI|KOTAKBANK|ADANIPORTS|KARURVYSYA|UNITDSPR|NAVINFLUOR|DIVISLAB|RRKABEL|PNBHOUSING|GESHIP|NETWORK18|TATACHEM)\b")

GRADER_SYSTEM = """You are an outside examiner grading Ananta, a paper-trading assistant for the Indian market that talks to its owner, Madhav ("sir"),
mostly by voice from Toronto (10.5 hours behind India; NSE trades 09:15-15:30 IST). His messages are speech-to-text: run-on, several asks in one,
some garbled words. He wants: every part answered; today's session first (not the last closed one) with its time; what Ananta itself did (the
options line, the managed book, the practice book); his portfolio; replacements picked and tracked on paper; company names spoken as words
(Jio Financial, not JIOFIN); short spoken answers; honest limits stated once, never a false "I can't"; no nagging.

You get a TRUTH SHEET for the moment the question was asked. Judge the answer against it: a number, state or claim that contradicts it is an
error; leaving out what the truth sheet shows Ananta had is a gap.

Reply with JSON only:
{"grade": "A|B|C|D|F", "scores": {"answered_all_parts": 1-5, "correct": 1-5, "today_aware": 1-5, "plain_spoken": 1-5, "honest": 1-5},
 "errors": ["each factual error against the truth sheet"], "gaps": ["each thing it had and did not say"],
 "old_mistakes": [any of "session_state", "friday_for_today", "no_record", "cant_see_prices", "tickers", "dropped_part", "nag", "cut_mid_word", "dodged_replacement"],
 "one_line": "the verdict in one plain sentence"}
A = would satisfy him fully; B = good, one small gap; C = usable but a real gap or one error; D = misleading or dodges; F = wrong or harmful."""


def grade(history: list[dict], text: str, answer: str, truth: str) -> dict:
    convo = "\n".join(f"MADHAV: {h['text'][:500]}\nANANTA: {str(h.get('answer') or '')[:900]}" for h in history[-3:])
    user = (f"TRUTH SHEET (the moment of the question):\n{truth[:3500]}\n\nCONVERSATION SO FAR:\n{convo or '(none)'}\n\n"
            f"MADHAV'S MESSAGE (spoken):\n{text}\n\nANANTA'S ANSWER:\n{str(answer)[:3500]}\n\nGrade it. JSON only.")
    body = {"model": GRADER, "max_tokens": 1500, "thinking": {"type": "between_tools"}, "system": GRADER_SYSTEM, "messages": [{"role": "user", "content": user}]}
    key = ask._load_env_key()
    err = ""
    for _ in range(3):
        try:
            r = requests.post("https://api.anthropic.com/v1/messages", headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                              json=body, timeout=120).json()
            t = "".join(c.get("text", "") for c in (r.get("content") or []) if c.get("type") == "text")
            m = re.search(r"\{.*\}", t, re.S)
            if not m:
                raise ValueError(f"no JSON: {t[:100]!r} {str(r)[:120]}")
            v = json.loads(m.group(0))
            v["grade"] = str(v.get("grade", "C")).strip().upper()[:1]
            return v
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(6)
    return {"grade": "?", "grader_error": err}


def _local_get(url: str):
    """Read-only answers for the waiting list and the flags board, straight from the service code (no token needed, nothing changes)."""
    from jarvis.service import app as A, fixflow, waiting
    j = A._main()
    if url.endswith("/v3/waiting"):
        return waiting.collect(j)
    if url.endswith("/v3/flags"):
        return {"flags": fixflow.board(j), "states": fixflow.STATE_WORDS}
    return {}


def _plan_words() -> str:
    try:
        from jarvis.india import surfaces
        mb = surfaces._managed()
        p = (mb.get("plan") or {})
        buys = "; ".join(f"{b.get('symbol')} for {b.get('for_cut')} (Rs {b.get('inr')})" for b in p.get("buys") or [])
        extra = (f" The plan in full: {p.get('words')} The managed book: {(mb.get('clock') or {}).get('words')}; value {mb.get('value_inr')}, "
                 f"return so far {mb.get('return_pct')}% (its starting mark), replacements held {len(mb.get('replacements') or [])}.")
        return (f"The managed book's plan for {p.get('for_session')}: {len(p.get('cuts') or [])} cuts, buys {buys}; each with a 7% stop; "
                "a buy opening over 2% up is skipped. Its fills are booked from the official NSE day file by the 7 pm Toronto evening run, so on "
                "Monday afternoon Toronto time its first-day result is not known yet (only the plan and the opening prices are)." + extra)
    except Exception as e:  # noqa: BLE001
        return f"(managed plan unreadable: {e})"


def _waiting_words() -> str:
    w = _local_get("/v3/waiting")
    return "Waiting for his yes: " + ("; ".join(f"{x.get('title')} ({x.get('line')}; fixes: {', '.join(x.get('fixes') or [])}; review: {((x.get('review') or {}).get('words') or '')[:160]})"
                                               for x in w.get("items") or []) or "nothing")


NAMES_NOTE = ("Note for grading: the screen shows NSE tickers (JIOFIN) by Madhav's own choice of 30 Oct; the voice speaks every ticker as the "
              "company name (checked). Do not mark tickers in the text as a mistake.")


def _morning_plan() -> str:
    try:
        from jarvis.india import views
        m = views.morning()
        return f"The morning view for {m.get('session_words')}: plan {json.dumps(m.get('plan'), default=str)[:1200]}; watch {json.dumps(m.get('watch'), default=str)[:300]}."
    except Exception as e:  # noqa: BLE001
        return f"(morning view unreadable: {e})"


def truth_now(live: dict) -> str:
    rows = (live.get("index_now") or {}).get("rows") or {}
    ohlc = "; ".join(f"{k}: open {v.get('open')}, high {v.get('high')}, low {v.get('low')}, last {v.get('last')}, previous close {v.get('prev_close')}" for k, v in rows.items())
    return " ".join([str(live.get("words") or ""), f"Kite's day figures: {ohlc}." if ohlc else "", _plan_words(), _morning_plan(), _waiting_words(), NAMES_NOTE,
                     f"The nightly full data (every stock, the research book, the reconstruction) runs through {live['clock'].get('nightly_data_through')}.",
                     "Monday's practice book picks and the managed fills land with tonight's runs."])


def old_turns(pair: str) -> tuple[list[dict], dict] | None:
    f, start, truth = OLD[pair]
    rows = [json.loads(x) for x in (ASKDIR / f"{f}.jsonl").read_text().splitlines() if x.strip()]
    hist, cur = [], None
    for i, r in enumerate(rows):
        if r.get("role") != "user":
            continue
        ans = next((x.get("answer") for x in rows[i + 1:] if x.get("role") == "assistant"), "")
        t = {"text": r.get("text") or "", "answer": ans, "t": r.get("t")}
        if (r.get("text") or "").startswith(start):
            cur = t
            break
        hist.append(t)
    return (hist, {**cur, "truth": truth + " " + NAMES_NOTE}) if cur else None


def run() -> dict:
    real = ask.ASK_DIR
    ask.ASK_DIR, ask.DRY_RUN = Path(tempfile.mkdtemp(prefix="ot_style_")), True
    results = []
    try:
        for cid, c in CONVS.items():
            if c["frozen"]:
                live = neveragain.live_at(c["frozen"], neveragain.FRI_30OCT_CLOSE)
            else:
                live = livesession.today()
            truth = truth_now(live)
            if c["frozen"]:
                truth = (str(live.get("words") or "") + " " + _plan_words() + " " + _morning_plan() + " " + NAMES_NOTE + " " + OLD["P3"][2] + " Friday 30 Oct closed at 23,053 (+0.5%); Wall Street fell after (S&P 500 -1.8%, "
                         "Nasdaq -3.5%); no GIFT Nifty source; this conversation is the India Ask; the chat is the owner's.")
            hist = []
            thread = f"otst{cid}{int(time.time()) % 10000}"
            for t in c["turns"]:
                ask.LIVE_OVERRIDE = live if c["frozen"] else None
                t0 = time.time()
                try:
                    r = ask.ask("owner", t["text"], thread=thread, voice=True, token="style", flag_post=replay._fake_post, flag_get=_local_get)
                    ans = r.get("answer")
                except Exception as e:  # noqa: BLE001
                    ans = f"(crash: {type(e).__name__}: {str(e)[:160]})"
                finally:
                    ask.LIVE_OVERRIDE = None
                ms = int(1000 * (time.time() - t0))
                g = grade(hist, t["text"], ans, truth)
                row = {"conv": cid, "id": t["id"], "text": t["text"], "answer": ans, "ms": ms, "new": g, "pair": t["pair"]}
                if t["pair"] and t["pair"] in OLD:
                    o = old_turns(t["pair"])
                    if o:
                        oh, ot = o
                        row["old"] = {"text": ot["text"], "answer": ot["answer"], "when": dt.datetime.fromtimestamp(ot["t"]).strftime("%a %d %b %H:%M"),
                                      "grade": grade(oh, ot["text"], ot["answer"], ot["truth"])}
                row["tickers"] = sorted(set(TICKER.findall(str(ans or ""))))
                row["guard"] = livesession.check(str(ans or ""), live, t["text"])
                results.append(row)
                hist.append({"text": t["text"], "answer": ans})
                print(f"{t['id']} new {g.get('grade')}" + (f" | old {row['old']['grade'].get('grade')} ({row['old']['when']})" if row.get("old") else "")
                      + f" | {ms} ms | tickers {row['tickers']} | guard {row['guard']}", flush=True)
    finally:
        ask.ASK_DIR, ask.DRY_RUN = real, False
    pts = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
    new = [pts.get(r["new"].get("grade"), None) for r in results]
    old = [pts.get(r["old"]["grade"].get("grade"), None) for r in results if r.get("old")]
    newp = [pts.get(r["new"].get("grade")) for r in results if r.get("old")]
    corr = []
    for key, what, ids in CORRECTIONS:
        rows = [r for r in results if r["id"] in ids]
        bad = []
        for r in rows:
            om = set(r["new"].get("old_mistakes") or [])
            if key == "names_not_tickers" and r["tickers"]:
                bad.append(f"{r['id']}: said {', '.join(r['tickers'])}")
            if key in ("today_not_friday",) and ("friday_for_today" in om):
                bad.append(f"{r['id']}: Friday for today")
            if key == "session_state" and "session_state" in om:
                bad.append(f"{r['id']}: session state")
            if key == "live_prices" and "cant_see_prices" in om:
                bad.append(f"{r['id']}: can't see prices")
            if key == "options_record" and "no_record" in om:
                bad.append(f"{r['id']}: no record")
            if key == "replacements" and "dodged_replacement" in om:
                bad.append(f"{r['id']}: dodged the replacement")
            if key == "every_part" and "dropped_part" in om:
                bad.append(f"{r['id']}: dropped a part")
            if key == "waiting_short" and ({"cut_mid_word", "nag"} & om):
                bad.append(f"{r['id']}: {', '.join(sorted({'cut_mid_word', 'nag'} & om))}")
            if r["guard"] and key in ("today_not_friday", "session_state", "live_prices", "options_record"):
                bad.append(f"{r['id']}: guard says {r['guard'][0][:80]}")
        corr.append({"key": key, "correction": what, "checked_on": ids, "held": not bad, "slips": sorted(set(bad))})
    avg = lambda xs: round(sum(x for x in xs if x is not None) / max(1, len([x for x in xs if x is not None])), 2)  # noqa: E731
    rep = {"round": "Madhav-style round, 2 Nov 2026", "grader": GRADER, "asked_at": dt.datetime.now().isoformat(timespec="minutes"),
           "gpa_new_all": avg(new), "gpa_new_paired": avg(newp), "gpa_old_paired": avg(old),
           "grades_new": {g: sum(1 for r in results if r["new"].get("grade") == g) for g in "ABCDF?"},
           "grades_old": {g: sum(1 for r in results if r.get("old") and r["old"]["grade"].get("grade") == g) for g in "ABCDF?"},
           "corrections": corr, "results": results}
    OUT.write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
    print(json.dumps({k: rep[k] for k in ("gpa_new_all", "gpa_new_paired", "gpa_old_paired", "grades_new", "grades_old")}))
    for c in corr:
        print(("HELD " if c["held"] else "SLIP ") + c["key"], c["slips"])
    return rep


if __name__ == "__main__":
    run()
