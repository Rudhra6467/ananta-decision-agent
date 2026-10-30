"""The shadow trader (Phase 4.3 of the 29 Oct 2026 plan; Madhav: "yes, let's build"): a second model writes its own plan for the session from
the same facts as the morning view, blind to Ananta's plan, words, review and lessons; the plan is sealed before the open and scored by the
same code (india.shadow, the forecast ledger). Its job is to find what Ananta's rules do not consider. Twenty sessions before anything is read
into it; never advice; it cannot trade.

  python scripts/india_shadow_trader.py        (launchd com.ananta.india.shadowtrader, 23:06 Toronto = 08:36 Indian time, after the morning view)

Runs through ~/ananta_runs/svc_env_run.py (the service's environment holds the model key). Reads GET /v3/morning/facts_blind, posts the plan to
POST /v3/morning/shadow. "Stay silent" is a first-class answer: stance "stand_down" with silent true when the inputs are missing or contradict.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

INDIA = "http://127.0.0.1:8110"
MODEL = os.getenv("SHADOW_MODEL", "claude-sonnet-5-5")

PROMPT = """You are an independent trader reading a pre-market fact sheet for the Indian market (NSE), before the open. You have NOT seen the house
assistant's plan and you must not guess it. Write YOUR OWN plan for today's session, on paper, from the FACTS only. Every number you use must
appear in the facts. If the facts are missing something you need, or contradict each other, staying silent is the right answer: say so.

Reply with one JSON object and nothing else, with exactly these keys:
{{
 "take": {{"bull": 0.0, "bear": 0.0, "neutral": 0.0}},
 "take_basis": "<one line: which facts moved you off the base rates, and by how much; or 'base rates' if nothing did>",
 "stance": "<one of: trade_as_planned | stand_down | reduce_risk>",
 "stance_why": "<one line>",
 "watch": [{{"symbol": "<a symbol that appears in the facts, or NIFTY / BANKNIFTY>", "direction": "up|down", "why": "<one line>"}}],
 "blind_spot": "<one line: the one thing a rule-based assistant reading these same facts is most likely to miss today>",
 "silent": false
}}
Rules: "bull" means Nifty closes more than 0.3% up, "bear" more than 0.3% down, "neutral" within; the three must sum to 1; the base rates are in the
facts (setup.scenarios) and you shift them only for a reason the facts support. "trade_as_planned" means the day is ordinary for a rule-based swing
book; "stand_down" means no new positions today; "reduce_risk" means cut exposure. At most 3 watch names, each from the facts. Set "silent": true and
stance "stand_down" when you would rather not act on these facts. Paper only; never advice.

FACTS:
{facts}"""


def _get(path: str) -> dict:
    with urllib.request.urlopen(INDIA + path, timeout=30) as r:
        return json.loads(r.read().decode())


def _post(url: str, body: dict, headers: dict | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **(headers or {})}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def claude(prompt: str, model: str, max_tokens: int = 1500) -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("no model key")
    r = _post("https://api.anthropic.com/v1/messages", {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
              {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=120)
    if r.get("error"):
        raise RuntimeError(str(r["error"])[:200])
    return "".join(c.get("text", "") for c in r.get("content") or [] if c.get("type") == "text")


def _parse(raw: str) -> dict | None:
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    s = s.replace("“", "'").replace("”", "'").replace("‘", "'").replace("’", "'")
    start = s.find("{")
    if start < 0:
        return None
    for end in reversed([i for i, ch in enumerate(s) if ch == "}"]):
        try:
            obj = json.loads(re.sub(r",\s*([}\]])", r"\1", s[start:end + 1]))
        except ValueError:
            continue
        if isinstance(obj, dict) and "stance" in obj and "take" in obj:
            return obj
    return None


def _facts_text(f: dict) -> str:
    keep = {k: f.get(k) for k in ("session", "data_through", "overnight", "setup", "scorecard", "yesterday", "lines")}
    return json.dumps(keep, default=str)[:14000]


def _ist_today() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=5, minutes=30))).date().isoformat()


def _symbols_in(f: dict) -> set[str]:
    return set(re.findall(r"\b[A-Z][A-Z0-9&-]{2,}\b", json.dumps(f, default=str))) | {"NIFTY", "BANKNIFTY"}


def main() -> int:
    f = _get("/v3/morning/facts_blind")
    session = f.get("session")
    if not session:
        print("shadow trader: no facts yet")
        return 0
    if session < _ist_today():
        print(f"shadow trader: skipped, the facts' session {session} is before today in India ({_ist_today()})")
        return 0
    raw = claude(PROMPT.format(facts=_facts_text(f)), MODEL)
    plan = _parse(raw)
    if plan is None:
        raw = claude(PROMPT.format(facts=_facts_text(f)) + "\n\nReply with one valid JSON object and nothing else.", MODEL)
        plan = _parse(raw)
    if plan is None:
        plan = {"take": None, "stance": "stand_down", "stance_why": "the model's answer could not be read", "watch": [], "blind_spot": "", "silent": True}
    # code guards: a stance from the allowed list; watch names only from the facts; at most three; numbers not in the facts flagged
    if plan.get("stance") not in ("trade_as_planned", "stand_down", "reduce_risk"):
        plan["stance"], plan["silent"] = "stand_down", True
    allowed = _symbols_in(f)
    plan["watch"] = [w for w in (plan.get("watch") or []) if isinstance(w, dict) and str(w.get("symbol", "")).upper() in allowed][:3]
    fact_nums = {x.replace(",", "") for x in re.findall(r"\d[\d,]*\.?\d*", json.dumps(f, default=str))}
    stray = [n for n in re.findall(r"\d[\d,]*\.?\d*", json.dumps({k: plan.get(k) for k in ("take_basis", "stance_why", "blind_spot")})) if n.replace(",", "") not in fact_nums and len(n) > 2]
    plan["numbers_not_in_facts"] = stray[:8]
    res = _post(INDIA + "/v3/morning/shadow", {"session": session, "plan": plan, "facts_sha": f.get("facts_sha", ""), "model": MODEL, "raw": raw[-400:]})
    print(f"shadow trader: {session} sealed {res.get('sha256', '')[:12]} stance {plan.get('stance')} silent {plan.get('silent')} forecast {res.get('forecast_id')} {res.get('forecast_note', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
