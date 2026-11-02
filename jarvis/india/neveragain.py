"""Never again (Madhav, 2 Nov 2026: "These are huge mistakes, I want you to take care and make sure these things don't repeat again").

Madhav's own conversations of 1-2 Nov, re-asked every night at the moment he asked them: each case freezes that moment's today-block (the
clock, Kite's index prices, the options line's ledger) and puts it in front of today's code, then checks the answers three ways:
  1. livesession.check: nothing that contradicts the moment (a session "happening" after the close, "no record" of a ledgered decision, "can't
     see today's prices", an older session given for "yesterday");
  2. must / must_not: what the answer has to carry (today's close, the options line's trades, the session state) and must never say;
  3. the nightly grader, like every other replayed answer.
A failure is pushed to his phone the same night (jarvis/india/replay.py run), and the cases never retire.

The 23:00 IST mid-session case uses stand-in prices (a fixture, marked as such): it tests the shape of a live answer, not a real level.
"""
from __future__ import annotations

import datetime as dt
import re

from jarvis.india import livesession as L

UTC = dt.timezone.utc


def _stub(table: dict):
    return lambda syms: {s: {"last_price": table[s][0], "ohlc": {"open": table[s][1], "high": max(table[s][:2]), "low": min(table[s][:2]), "close": table[s][2]}}
                         for s in syms if s in table}


CLOSE_2NOV = {"NSE:NIFTY 50": (23440.8, 23222.3, 23053.1), "NSE:NIFTY BANK": (55002.2, 54837.2, 54686.95), "NSE:INDIA VIX": (15.5, 15.3, 15.3)}
FRI_30OCT_CLOSE = {"NSE:NIFTY 50": (23053.1, 22937.0, 22937.0), "NSE:NIFTY BANK": (54686.95, 54906.6, 54906.6), "NSE:INDIA VIX": (15.3, 15.0, 15.0)}   # last; open, previous close as a stand-in
MID_2NOV_FIXTURE = {"NSE:NIFTY 50": (23331.4, 23222.3, 23053.1), "NSE:NIFTY BANK": (54910.6, 54837.2, 54686.95), "NSE:INDIA VIX": (15.1, 15.3, 15.3)}


def live_at(when: dt.datetime, table: dict | None, holdings_words: str | None = None, managed_words: str | None = None) -> dict:
    clk = L.clock("2026-10-30", when)
    fetch = _stub(table or {})
    L._CACHE.clear()
    out = {"clock": clk, "data_timing": L.data_timing(clk), "index_now": L.index_now(clk, fetch), "options_today": L.options_today(clk, fetch),
           "holdings_today": {"words": holdings_words}, "managed_today": {"words": managed_words}}
    L._CACHE.clear()
    out["words"] = " ".join(x for x in (clk["words"], out["index_now"].get("words"), out["options_today"].get("words"), holdings_words, managed_words) if x)
    out["how_to_say_it"] = ("This block is the truth about today. Answer about clock.latest_session from it first; never contradict its clock, "
                            "never say 'no record' of decisions options_today lists, never say you cannot see prices index_now has.")
    return out


CASES = [
    {"id": "2nov-0608-after-close", "when": dt.datetime(2026, 11, 2, 11, 8, tzinfo=UTC), "table": CLOSE_2NOV,
     "holdings": "Your stocks (the paper copy of the account) are up about Rs 2,172 (+2.24%) today; best TATAPOWER +3.1%, JIOFIN +4.3%, LICI +1.5%; worst KARURVYSYA -3.3%.",
     "managed": "The managed book's first plan was for today: 10 cuts and 3 buys at the open. At today's opening prices these buys stay in (AJANTPHARM opened -0.9%; "
                "ETERNAL opened -0.1%; CIPLA opened +0.3%). The fills are booked from the official NSE day file by the 7 pm Toronto run.",
     "turns": [
         {"text": "Hey Ananta. What happened with the market yesterday? What did we do and what did you see and what did you find?", "voice": True,
          "must": [r"\b(monday|today)\b", r"23,4[34]\d|1\.7\s?%|1\.68\s?%", r"\b(options line|bank nifty)\b"]},
         {"text": "So, what happened on the Monday market? Why are you still telling about the Friday? What about the Monday?", "voice": True,
          "must": [r"23,4[34]\d|1\.7\s?%|1\.68\s?%"]},
         {"text": "But Monday, Monday already happened in India, right? Why didn't you have that data?", "voice": True,
          "must": [r"\bclos(ed|e)\b"], "must_not": [r"\bno monday (prices|data)\b"]},
     ]},
    {"id": "1nov-2218-before-open", "when": dt.datetime(2026, 11, 2, 3, 18, tzinfo=UTC), "table": FRI_30OCT_CLOSE,
     "turns": [
         {"text": "What's up with the market now? Ananta, how is it going? What did you watch?", "voice": True,
          "must": [r"09:15|before the open|not (yet )?(open|started)|opens\b|has not started"]},
         {"text": "As the Indian market is going to start in 30-40 minutes, I want to know what is that you are ready for.", "voice": True,
          "must": [r"\b(managed book|plan)\b"]},
     ]},
    {"id": "2nov-1130ist-mid-session-fixture", "when": dt.datetime(2026, 11, 2, 6, 0, tzinfo=UTC), "table": MID_2NOV_FIXTURE,
     "turns": [
         {"text": "How is the market doing right now?", "voice": True, "must": [r"23,33\d|1\.2\s?%", r"\b(open|right now|so far|live)\b"]},
         {"text": "What did the options line do this morning?", "voice": True, "must": [r"bank nifty", r"09:30|09:45|9:30|9:45"]},
     ]},
]


# ---- the moment harness (2 Nov, Madhav: "make sure these things don't repeat"): the same kinds of question at eight moments of the Indian day,
# each checked against that moment's today-block. The 2 Nov errors were all about WHEN the question was asked, so the moments are the test.
MON_HOLD = CASES[0]["holdings"]
MON_MANAGED = CASES[0]["managed"]
MOMENTS = [
    ("pre-open (Sun 10:15 pm Toronto)", dt.datetime(2026, 11, 2, 3, 15, tzinfo=UTC), FRI_30OCT_CLOSE, None, None),
    ("NSE pre-open 09:05 IST", dt.datetime(2026, 11, 2, 3, 35, tzinfo=UTC), FRI_30OCT_CLOSE, None, None),
    ("mid-session 11:30 IST (stand-in prices)", dt.datetime(2026, 11, 2, 6, 0, tzinfo=UTC), MID_2NOV_FIXTURE, None, MON_MANAGED),
    ("just after the close 15:45 IST", dt.datetime(2026, 11, 2, 10, 15, tzinfo=UTC), CLOSE_2NOV, MON_HOLD, MON_MANAGED),
    ("evening India, 8:30 am Toronto", dt.datetime(2026, 11, 2, 13, 30, tzinfo=UTC), CLOSE_2NOV, MON_HOLD, MON_MANAGED),
    ("after India's midnight, 2 pm Toronto", dt.datetime(2026, 11, 2, 19, 0, tzinfo=UTC), CLOSE_2NOV, MON_HOLD, MON_MANAGED),
    ("weekend, Sat 10 am Toronto", dt.datetime(2026, 10, 31, 14, 0, tzinfo=UTC), FRI_30OCT_CLOSE, None, None),
    ("clock-change Sunday, noon Toronto", dt.datetime(2026, 11, 1, 17, 0, tzinfo=UTC), FRI_30OCT_CLOSE, None, None),
]
MOMENT_QS = ["Ananta how is the market right now, like where is the Nifty?",
             "Hey Ananta, what happened today in the market and what did we do?",
             "Is the Indian market open now or closed? When does it open next?"]


def _moment_checks(q_i: int, answer: str, live: dict) -> list[dict]:
    """What any right answer at this moment must carry, worked out from the moment itself (not a fixed text)."""
    a, clk, out = answer.lower(), live["clock"], []
    rows = (live.get("index_now") or {}).get("rows") or {}
    n = (rows.get("NIFTY 50") or {}).get("last")
    latest_wd = clk["latest_session_words"].split(" ")[0].lower()
    if q_i == 0 and n is not None and not re.search(re.escape(f"{n:,.0f}"[:4]), answer):
        out.append({"code": "MISSING", "why": f"the Nifty at this moment is {n:,.2f} ({live['index_now'].get('kind')}); the answer does not give it"})
    if q_i == 1 and latest_wd not in a and "today" not in a:
        out.append({"code": "MISSING", "why": f"'today' here means {clk['latest_session_words']}; the answer names neither"})
    if q_i == 2:
        want = {"open": r"\bopen\b", "closed": r"\bclosed?\b", "before_open": r"09:15|9:15|not (?:yet )?open|opens", "pre_open": r"pre-?open|09:15|9:15",
                "no_session": r"no (?:nse )?session|closed|weekend|holiday|opens"}[clk["state"]]
        if not re.search(want, a):
            out.append({"code": "MISSING", "why": f"the market is {clk['state'].replace('_', ' ')} at this moment ({clk['words']}); the answer does not say so"})
    return out


def run_moments(replay_conversation) -> list[dict]:
    out = []
    for name, when, table, hold, managed in MOMENTS:
        live = live_at(when, table, hold, managed)
        turns = [{"text": q, "voice": True, "live": live} for q in MOMENT_QS]
        done = replay_conversation(turns, f"mo{when.strftime('%d%H%M')}")
        for i, d in enumerate(done):
            probs = [{"code": "TODAY_WRONG", "why": p} for p in (d.get("today_problems") or [])] + _moment_checks(i, str(d.get("answer") or ""), live)
            out.append({"source": "never_again", "case": f"moment: {name}", "i": i, **d, "live": None, "pass": not probs, "problems": probs})
    return out


def run(ask_mod, replay_conversation, judge) -> list[dict]:
    """Re-ask every case at its own moment. Returns one result row per turn (source 'never_again')."""
    out = []
    for c in CASES:
        live = live_at(c["when"], c["table"], c.get("holdings"), c.get("managed"))
        turns = [{"text": t["text"], "voice": t.get("voice", False), "live": live} for t in c["turns"]]
        done = replay_conversation(turns, f"na{c['id'][:8]}")
        for i, (t, d) in enumerate(zip(c["turns"], done)):
            a = str(d.get("answer") or "")
            probs = [{"code": "TODAY_WRONG", "why": p} for p in (d.get("today_problems") or [])]
            probs += [{"code": "MISSING", "why": f"must say /{m}/"} for m in t.get("must", []) if not re.search(m, a, re.I)]
            probs += [{"code": "FORBIDDEN", "why": f"must not say /{m}/"} for m in t.get("must_not", []) if re.search(m, a, re.I)]
            g = judge(done[:i], d) if not probs else {"pass": False, "problems": probs}
            out.append({"source": "never_again", "case": c["id"], "i": i, **d, "live": None, **g})
    return out + run_moments(replay_conversation)


def main() -> int:
    """python -m jarvis.india.neveragain: the cases alone, now (dry: nothing in his history, books or queues changes)."""
    import json
    import tempfile
    from pathlib import Path

    from jarvis.india import ask, replay
    real = ask.ASK_DIR
    ask.ASK_DIR, ask.DRY_RUN = Path(tempfile.mkdtemp(prefix="ananta_neveragain_")), True
    try:
        rows = run(ask, replay.replay_conversation, replay.judge)
    finally:
        ask.ASK_DIR, ask.DRY_RUN = real, False
    for r in rows:
        print(f"{'PASS' if r['pass'] else 'FAIL'} {r['case']} #{r['i']}: {r['text'][:70]}")
        print("   ", str(r.get("answer") or "")[:700].replace("\n", " "))
        for p in r.get("problems") or []:
            print("    !", p.get("code"), str(p.get("why"))[:200])
    out = replay.OUT / "never_again_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([{k: r.get(k) for k in ("case", "i", "text", "answer", "pass", "problems")} for r in rows], indent=1, ensure_ascii=False))
    return 0 if all(r["pass"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
