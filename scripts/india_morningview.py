"""The morning view's words (Madhav, 23 Oct 2026): a trader's morning note written from Ananta's facts, checked by a separate reviewer, and the
reviewer's own odds put on the record; then the opening update after the first hour.

  python scripts/india_morningview.py morning     (launchd com.ananta.india.morningview, 23:00 Toronto = 08:30 Indian time, after the facts are built)
  python scripts/india_morningview.py opening     (launchd com.ananta.india.openingview, 00:50 Toronto = 10:20 Indian time)

Both run through ~/ananta_runs/svc_env_run.py (the service's environment holds the model key and the phone-push topic). They read the facts from
the India service over loopback (GET /v3/morning/facts), never the lake. Rules, in the prompts and checked after: every number comes from the facts;
chances are always said beside their baseline; nothing is advice; paper only; no internal code reaches the page (jarvis/india/plain.py scrubs the
words again on the way in). The reviewer is a second call with a critic's brief: it corrects the note against the facts and gives its own bull /
bear / neutral odds with a one-line basis; those odds are written to the forecast ledger as "reviewer" (a prediction with a deadline), so the
morning after, the scorecard shows the rule, the reviewer and the coin flip side by side. That is how "compare its predictions with performance
and notify it what to change" works: the lessons (facts.lessons_for_writer) go into the next morning's prompt.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

INDIA = "http://127.0.0.1:8110"
MODEL = os.getenv("MORNING_MODEL", "claude-sonnet-5-5")
REVIEW_MODEL = os.getenv("MORNING_REVIEW_MODEL", "claude-sonnet-5-5")

WRITER = """You are Ananta, Madhav's trading assistant for the Indian market, writing his morning view before the NSE open. Address him as "sir" once, at the start.
Write from the FACTS only: every number you use must appear in them; if the facts lack something, say it is missing. Chances are always said next to their baseline
(the coin flip, chance, the market average). This is paper trading and never advice. Plain words a non-trader follows; explain a technical word in the same sentence.
Shape, in this order, with these exact headings on their own lines:
The view
  3-4 sentences: overnight (US close, flows), where Nifty stands (trend, averages, breadth), the fear gauge, the odds for today with the baseline.
What Ananta is doing today
  2-3 sentences: the research book's practice buys (name a few, say what kind and that they are practice trades, not his money), the options line's state, what it did or suggests with his money.
Our chances, honestly
  2-3 sentences from the scorecard: the forecast record, the daily call against the coin flip, the research book so far, the options line; end with what a good day and a bad day would look like for the account.
Watch today
  2-4 short lines: expiry, events, the levels that label the day, the guardrails.
If you trade today
  Three one-line notes labelled "Options:", "Swing:", "Long-term:" - what the facts say for each style (e.g. the fear gauge and expiry for options; the trend and breadth for swings; the holdings' grades for long-term). Observations, not instructions.
Lessons from yesterday
  1-2 sentences: what was predicted, what happened, what changes in how you read today.
Keep it under 330 words. No bullet symbols; short lines. No internal names or codes (say "the options line", "the research book", "the daily call").
Staying silent is a first-class answer: if the facts you need are missing (no US close, no flows, the data a session behind) or contradict each other, open
"The view" with "No take today:" and the reason in one line, give the base rates only, and keep every other part factual; never fill a gap with a guess.
LESSONS YOU MUST FOLLOW TODAY:
{lessons}

FACTS:
{facts}"""

REVIEWER = """You are an independent reviewer checking a morning market note written by a trading assistant against the FACTS it was written from.
Your job: (1) list every number or claim in the NOTE that is not supported by the FACTS or contradicts them (quote the words, say what the facts say); (2) say what the note
leaves out that a careful trader would want from these facts; (3) give YOUR OWN odds for today's Nifty session as probabilities for "bull" (closes more than 0.3% up),
"bear" (more than 0.3% down) and "neutral" that sum to 1, with a one-line basis drawn only from the facts (the base rates are in the facts; shift them only for a reason
the facts support, and say by how much and why). Be brief and concrete. Reply with JSON only:
{{"corrections": ["..."], "missing": ["..."], "verdict": "<one sentence: is the note fair to the facts?>", "scenarios": {{"bull": 0.0, "bear": 0.0, "neutral": 0.0}}, "basis": "<one line>"}}

FACTS:
{facts}

NOTE:
{note}"""

OPENING = """You are Ananta, writing Madhav's opening update after the first hour of the NSE session (it is about 10:20 Indian time). From the FACTS only, in 2-3 short sentences,
address him as "sir" once: what the options line decided at its decision points (or that it could not run and why), and what the morning view said to watch. If the facts hold no
opening data, say so in one sentence and do not guess what the market did. Paper only, never advice, no internal codes.

FACTS:
{facts}"""


def _get(path: str) -> dict:
    with urllib.request.urlopen(INDIA + path, timeout=30) as r:
        return json.loads(r.read().decode())


def _post(url: str, body: dict, headers: dict | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **(headers or {})}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def claude(prompt: str, model: str, max_tokens: int = 3000) -> str:   # the model thinks inside this budget too: keep it roomy
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("no model key")
    r = _post("https://api.anthropic.com/v1/messages", {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
              {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=120)
    if r.get("error"):
        raise RuntimeError(str(r["error"])[:200])
    return "".join(c.get("text", "") for c in r.get("content") or [] if c.get("type") == "text")


def _facts_for_prompt(f: dict) -> str:
    keep = {k: f.get(k) for k in ("session", "data_through", "overnight", "setup", "plan", "scorecard", "yesterday", "lines")}
    return json.dumps(keep, default=str)[:14000]


def _numbers(s: str) -> set[str]:
    return {x.replace(",", "") for x in re.findall(r"\d[\d,]*\.?\d*", s)}


def _parse_review(raw: str) -> dict | None:
    """The reviewer's JSON object, read tolerantly: code fences, smart quotes and trailing commas are repaired; a bare quote inside a string
    (the 29 Oct failure) is caught by trying every closing brace from the end. None when nothing parses."""
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    s = s.replace("“", "'").replace("”", "'").replace("‘", "'").replace("’", "'")  # quotes inside strings become apostrophes, never JSON quotes
    start = s.find("{")
    if start < 0:
        return None
    ends = [i for i, ch in enumerate(s) if ch == "}"]
    for end in reversed(ends):
        cand = re.sub(r",\s*([}\]])", r"\1", s[start:end + 1])
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if isinstance(obj, dict) and "verdict" in obj:
            return obj
    return None


def _ist_today() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=5, minutes=30))).date().isoformat()


def morning() -> int:
    f = _get("/v3/morning/facts")
    if not f.get("session"):
        print("morning view: no facts yet")
        return 0
    session = f["session"]
    # 24 Oct 2026: a "morning view" for a session that has already traded is not a morning view (the read model ran a session late
    # until the nightly timing fix; on 24 Oct it wrote "This morning · 23 Oct" on a Saturday). Skip and say why in the log.
    if session < _ist_today():
        print(f"morning view: skipped, the read model's next session {session} is before today in India ({_ist_today()}); the data is behind")
        return 0
    lessons = "\n".join(f"- {x}" for x in (f.get("lessons_for_writer") or [])) or "- none yet"
    note = claude(WRITER.format(lessons=lessons, facts=_facts_for_prompt(f)), MODEL)
    # a cheap honesty check by code before the reviewer: numbers in the note that appear nowhere in the facts are flagged in the log
    fact_nums = _numbers(json.dumps(f, default=str))
    stray = [n for n in _numbers(note) if n not in fact_nums and len(n) > 2]
    if stray:
        print(f"morning view: numbers not in the facts: {stray[:8]}")
    review = {"corrections": [], "missing": [], "verdict": "", "scenarios": None, "basis": ""}
    try:
        raw = claude(REVIEWER.format(facts=_facts_for_prompt(f), note=note), REVIEW_MODEL, 2500)
        parsed = _parse_review(raw)
        if parsed is None:  # 29 Oct audit: one malformed answer (a stray quote inside a string) lost the whole review for 29 Oct; ask once more, JSON only
            raw = claude(REVIEWER.format(facts=_facts_for_prompt(f), note=note) + "\n\nReply with one valid JSON object and nothing else; escape any double quote inside a string.",
                         REVIEW_MODEL, 2500)
            parsed = _parse_review(raw)
        if parsed is None:  # keep the reviewer's words rather than nothing; the scenarios stay empty and are not scored
            review["verdict"] = "the reviewer answered but not in a readable form; its words: " + re.sub(r"\s+", " ", raw)[:600]
        else:
            review = {**review, **parsed}
    except Exception as exc:  # noqa: BLE001
        review["verdict"] = f"the reviewer could not run: {str(exc)[:100]}"
    sc = review.get("scenarios") or {}
    try:
        tot = sum(float(sc.get(k, 0)) for k in ("bull", "bear", "neutral"))
        sc = {k: round(float(sc.get(k, 0)) / tot, 4) for k in ("bull", "bear", "neutral")} if tot > 0 else None
    except (TypeError, ValueError):
        sc = None
    review_text = ((review.get("verdict") or "") + (" Corrections: " + "; ".join(review["corrections"][:4]) if review.get("corrections") else "")
                   + (" Missing: " + "; ".join(review["missing"][:3]) if review.get("missing") else "")
                   + (f" The reviewer's own odds: up {100 * sc['bull']:.0f}%, down {100 * sc['bear']:.0f}%, flat {100 * sc['neutral']:.0f}% ({review.get('basis', '')})." if sc else "")).strip()
    res = _post(INDIA + "/v3/morning/words", {"session": session, "words": note, "review": review_text, "reviewer_scenarios": sc, "reviewer_basis": review.get("basis", "")})
    print(f"morning view {session}: {len(note.split())} words; reviewer odds {sc}; ledger {res.get('reviewer_scenarios', {}).get('written') if res.get('reviewer_scenarios') else 'none'}")
    head = (f.get("lines") or {}).get("headline") or ""
    _push(f"Morning view · {session[5:]}", head[:220] + (f" Reviewer: up {100 * sc['bull']:.0f}% / down {100 * sc['bear']:.0f}%." if sc else ""))
    return 0


def opening() -> int:
    f = _get("/v3/morning/facts")
    if not f.get("session"):
        print("opening update: no morning view")
        return 0
    if f["session"] != _ist_today():     # only on the session's own morning (it ran on Saturday 24 Oct and said "sign-in worked this time")
        print(f"opening update: skipped, today in India is {_ist_today()} and the morning view is for {f['session']}")
        return 0
    try:
        from jarvis.india import views as _v  # noqa: F401 - only to confirm the service package is importable in this env
    except Exception:  # noqa: BLE001
        pass
    facts = {"session": f["session"], "watch": (f.get("lines") or {}).get("watch"), "options_line_plan": (f.get("plan") or {}).get("options_line"),
             "opening_decisions": _opening_rows(f["session"]), "scenario_levels": (f.get("setup") or {}).get("scenario_levels")}
    words = claude(OPENING.format(facts=json.dumps(facts, default=str)[:6000]), MODEL, 1500)
    _post(INDIA + "/v3/morning/words", {"session": f["session"], "words": "", "opening": words})
    _push(f"Opening · {f['session'][5:]}", words[:220])
    print(f"opening update {f['session']}: {words[:120]}")
    return 0


def _opening_rows(session: str) -> list[dict]:
    """The options line's decision rows for the session, read through the India service's facts (the service holds the ledger paths)."""
    try:
        o = _get("/v3/options")
        return [x for x in (o.get("decisions_today") or [])] or [{"note": o.get("words")}]
    except Exception as exc:  # noqa: BLE001
        return [{"note": f"no opening data: {str(exc)[:80]}"}]


def _push(title: str, body: str) -> None:
    try:
        from src.intelligence.paper_watch import push_phone

        print("push:", push_phone(title, body, level="EVENT"))
    except Exception as exc:  # noqa: BLE001
        print(f"push skipped: {exc}")


if __name__ == "__main__":
    sys.exit(opening() if (sys.argv[1:] or ["morning"])[0] == "opening" else morning())
