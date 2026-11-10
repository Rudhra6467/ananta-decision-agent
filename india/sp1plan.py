"""The options line's plan for the session, in plain words (9 Nov 2026; Madhav: "yes, lets complete" to the outsider readiness review, fix 2).

Each morning at 07:30 IST the options line writes what it will do at the 09:15 open for each way the market can open (paper/sp1/plans/
<session>.json, d0_by_gap_bucket: down, flat, up), with the inputs it read and which of them were stale. Nothing read that file: the morning
view said only "the options line decides between 09:15 and 10:15". This module reads it and says it; it changes nothing in the line.

  load(session)                 the plan file, or None
  words(plan, indicated=None)   {"by_index", "inputs", "missing", "words", "short", "row"}; indicated: {"NIFTY": pct, "BANKNIFTY": pct}, the
                                indicated gap in per cent (GIFT Nifty, or the 09:08 pre-open), names the row of the plan it points to

Read-only. The gap lines are the line's own (sp1_v2.json opening.gap: down <= -0.25%, flat, up >= +0.25%).
"""
from __future__ import annotations

import datetime as dt
import json

from india import paths

NAME = {"NIFTY": "Nifty", "BANKNIFTY": "Bank Nifty"}
GAP_LINE = 0.25
# the same words the Ask uses for a trade's exit (jarvis/india/livesession.py EXIT_WORDS; a test in the agent repo keeps the two the same)
EXIT_WORDS = {"NEXTOPEN": "closing at the next session's open", "T1130": "closing at 11:30 IST", "T1515": "closing at 15:15 IST",
              "ATRSTOP": "with a stop half a day's average range against it, else closing at 15:15 IST",
              "ORSTOP": "with a stop at the far side of the opening range, else closing at 15:15 IST",
              "TRAIL": "with a trailing stop, else closing at 15:15 IST"}
LEVEL_WORDS = {"trend": {"up": "the trend up", "down": "the trend down", "mixed": "no clear trend"},
               "vix": {"low": "the fear gauge low", "mid": "the fear gauge in its middle range", "high": "the fear gauge high"},
               "us": {"up": "the US up overnight", "down": "the US down overnight", "flat": "the US flat overnight", "missing": "no US close"},
               "positioning": {"low": "foreign investors' futures positioning low", "mid": "foreign investors' futures positioning in its middle range",
                               "high": "foreign investors' futures positioning high", "missing": "no positioning reading"},
               "event": {"none": "no scheduled event", "today": "a scheduled event today", "recent": "a scheduled event in the last three sessions"}}
STALE_WORDS = {"us_qqq": "the US close was not the latest one", "participant_oi": "the futures positioning file was not the latest one",
               "cm_bhavcopy": "the cash-market file for the previous session was missing, so the count of rising stocks it reads after the open has no names"}


def load(session: str) -> dict | None:
    p = paths.data_dir() / "paper" / "sp1" / "plans" / f"{session}.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def bucket(pct: float | None) -> str | None:
    if pct is None:
        return None
    return "down" if pct <= -GAP_LINE else ("up" if pct >= GAP_LINE else "flat")


def _choice(ch: dict | None) -> str:
    if not ch or not ch.get("qualifies", True):
        return "no trade"
    side = "a long (a call option, one lot)" if (ch.get("dir") or 1) > 0 else "a short (a put option, one lot)"
    return f"{side}, {EXIT_WORDS.get(str(ch.get('exit')), str(ch.get('exit')))}"


def _index_words(name: str, by: dict) -> str:
    acts = {b: _choice((by.get(b) or {}).get("choice")) for b in ("down", "flat", "up")}
    if all(a == "no trade" for a in acts.values()):
        return f"{name}: no trade at the open, whichever way it opens."
    if len(set(acts.values())) == 1:
        return f"{name}: {acts['up']}, whichever way it opens."
    how = {"down": "0.25% or more down", "flat": "flat (inside 0.25% either way)", "up": "0.25% or more up"}
    groups: dict[str, list[str]] = {}
    for b in ("down", "flat", "up"):
        groups.setdefault(acts[b], []).append(b)
    take = [f"if it opens {' or '.join(how[b] for b in bs)}, {a}" for a, bs in groups.items() if a != "no trade"]
    rest = groups.get("no trade") or []
    tail = (f"; if it opens {' or '.join(rest)}, no trade" if rest else "")
    return f"{name}: " + "; ".join(take) + tail + "."


def words(plan: dict | None, indicated: dict | None = None) -> dict:
    if not plan or not plan.get("d0_by_gap_bucket"):
        return {"ready": False, "words": None, "short": None}
    d0 = plan["d0_by_gap_bucket"]
    made = str(plan.get("made_at") or "")[11:16]
    by_index = {s: _index_words(NAME.get(s, s), d0[s]) for s in d0}
    lv = ((d0.get("NIFTY") or {}).get("flat") or {}).get("levels") or {}
    on = (plan.get("overnight") or {}).get("NIFTY") or {}
    inputs = [LEVEL_WORDS[k].get(str(lv.get(k)), f"{k} {lv.get(k)}") for k in ("trend", "vix", "us", "positioning", "event") if lv.get(k) is not None]
    if on.get("us_qqq_ret") is not None and on.get("us_qqq_date") and inputs:
        try:
            us_d = dt.date.fromisoformat(str(on["us_qqq_date"])[:10])
            inputs = [x + (f" (the Nasdaq {100 * on['us_qqq_ret']:+.1f}% on {us_d:%a} {us_d.day} {us_d:%b})" if x.startswith("the US") else "") for x in inputs]
        except ValueError:
            pass
    exp = [NAME.get(s, s) for s in d0 if (((d0[s].get("flat") or {}).get("levels") or {}).get("expiry")) == "yes"]
    if exp:
        inputs.append(f"expiry day for {' and '.join(exp)} options")
    missing = [STALE_WORDS.get(k, k) for k, v in (plan.get("stale") or {}).items() if v]
    row = {}
    for s, pct in (indicated or {}).items():
        b = bucket(pct)
        if b and s in d0:
            row[s] = {"indicated_pct": pct, "bucket": b, "choice": _choice((d0[s].get(b) or {}).get("choice")),
                      "words": f"{NAME.get(s, s)} is indicated {pct:+.1f}% ({'flat' if b == 'flat' else b}): for that open the plan says {_choice((d0[s].get(b) or {}).get('choice'))}."}
    body = " ".join(by_index.values())
    full = (f"The options line's plan for the 09:15 open (written {made} IST, on paper, one lot): {body} "
            "It looks again at 09:30, 09:45 and 10:15 from the first hour's bars, so a pass at the open is not a pass for the day."
            + (f" It was planned with {', '.join(inputs)}." if inputs else "")
            + (f" Missing when it was planned: {'; '.join(missing)}." if missing else " No input was stale."))
    quiet = all("no trade at the open" in v for v in by_index.values())
    short = ("Options line at 09:15: no trade whichever way either index opens; it looks again at 09:30, 09:45 and 10:15." if quiet
             else "Options line at 09:15: " + " ".join(v for v in by_index.values() if "no trade at the open" not in v))
    return {"ready": True, "session": plan.get("date"), "made_at": plan.get("made_at"), "by_index": by_index, "inputs": inputs, "missing": missing,
            "row": row, "words": full, "short": short}
