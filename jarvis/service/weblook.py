"""Web lookup for things outside our data: other stocks and coins, news, the economy, events ("how is Nvidia doing", "what
moved crypto today", "is there a Fed meeting this week"). Madhav asked for this kind of breadth several times (2026-10-02/03).

Free first: Gemini with Google Search grounding. If that is busy or fails: Claude Haiku with Anthropic's web search tool
(about 1 cent a search plus tokens, counted in the AI budget by the caller's answer). Answers always carry their sources and are
labelled "from the web" in the app: never mixed into our own books, setups or evidence.
"""
from __future__ import annotations

import json
import os
import time

GEMINI_ORDER = [m.strip() for m in os.getenv("WEB_GEMINI_MODELS", "gemini-3.1-flash-lite,gemini-3.5-flash,gemini-flash-latest").split(",") if m.strip()]
HAIKU = os.getenv("ASK_HAIKU_MODEL", "claude-haiku-4-5-20251001")
PROMPT = ("Answer this for a crypto trader in Toronto, briefly and factually, from current web results: {q}\n"
          "Give the key facts with numbers and dates (say how recent they are). 4-6 short sentences, plain English, no advice. "
          "If the results do not answer it, say so.")


def _post(url: str, headers: dict, body: dict, timeout: int = 40) -> dict:
    import requests

    r = requests.post(url, headers=headers, json=body, timeout=timeout)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
    return r.json()


def _gemini(q: str, post=_post, prompt: str | None = None) -> dict:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    err = None
    for m in GEMINI_ORDER:
        try:
            r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                     {"x-goog-api-key": key, "content-type": "application/json"},
                     {"contents": [{"role": "user", "parts": [{"text": prompt or PROMPT.format(q=q)}]}], "tools": [{"google_search": {}}],
                      "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1400}})
            cand = (r.get("candidates") or [{}])[0]
            text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts") or [] if not p.get("thought")).strip()
            meta = cand.get("groundingMetadata") or {}
            src = []
            for ch in meta.get("groundingChunks") or []:
                w = ch.get("web") or {}
                if w.get("uri") and len(src) < 5:
                    src.append({"title": w.get("title") or w.get("domain") or "source", "url": w["uri"]})
            if text:
                return {"answer": text, "sources": src, "engine": f"Google Search via {m}", "cost_usd": 0.0}
        except Exception as exc:  # noqa: BLE001
            err = exc
    raise RuntimeError(f"Gemini search failed ({str(err)[:120]})")


def _claude(q: str, post=_post, prompt: str | None = None) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    r = post("https://api.anthropic.com/v1/messages",
             {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
             {"model": HAIKU, "max_tokens": 900, "messages": [{"role": "user", "content": prompt or PROMPT.format(q=q)}],
              "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}]}, timeout=60)
    text, src = "", []
    for b in r.get("content") or []:
        if b.get("type") == "text":
            text += b.get("text", "")
            for c in b.get("citations") or []:
                if c.get("url") and not any(s["url"] == c["url"] for s in src) and len(src) < 5:
                    src.append({"title": c.get("title") or "source", "url": c["url"]})
    u = r.get("usage") or {}
    searches = ((u.get("server_tool_use") or {}).get("web_search_requests") or 0)
    cost = (u.get("input_tokens", 0) * 1.0 + u.get("output_tokens", 0) * 5.0) / 1e6 + 0.01 * searches
    if not text.strip():
        raise RuntimeError("Claude web search returned no text")
    return {"answer": text.strip(), "sources": src, "engine": "Claude web search", "cost_usd": round(cost, 4)}


def lookup(q: str, post=_post) -> dict:
    q = (q or "").strip()[:300]
    if not q:
        raise ValueError("what should I look up?")
    t0 = time.time()
    errors = []
    for fn in (_gemini, _claude):
        try:
            out = fn(q, post)
            out["ms"] = int(1000 * (time.time() - t0))
            out["query"] = q
            out["label"] = "From the web, not from our system"
            return out
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:160])
    return {"error": "Web lookup is not available right now: " + " | ".join(errors), "query": q}


MARKET_PROMPT = (
    "You are the research desk of a cautious, buy-only crypto trading assistant. Today is {today} (UTC). Coin: {coin} ({name}).\n"
    "Search the web for what matters to someone deciding whether to BUY {coin} in the next few days. Look for: news on the coin and "
    "its project, token unlocks or large supply releases in the next 30 days, exchange listings or delistings, hacks or outages, "
    "legal or regulatory actions, and the overall crypto market mood (Bitcoin trend, Fear and Greed, big macro events this week).\n"
    "Reply with JSON only, no prose around it: {{\"facts\": [{{\"kind\": \"news|unlock|exchange|security|regulation|macro|sentiment\", "
    "\"fact\": \"one plain sentence with numbers\", \"date\": \"YYYY-MM-DD or unknown\", \"effect\": \"riskier|safer|neutral\", "
    "\"source\": \"site name\"}}], \"unlock_next_30d\": \"yes|no|unknown\", \"mood\": \"one sentence\"}}. At most 8 facts, newest "
    "first, only things from the last 30 days or scheduled in the next 30. Say unknown rather than guess. No advice.")
_MC: dict = {}


def _json_in(text: str) -> dict:
    a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b + 1]) if a >= 0 and b > a else {}


def market_check(j, coin: str, post=_post, cache_s: int = 6 * 3600) -> dict:
    """Ananta's research desk (Madhav, Oct 10): not just pages, a structured market check in three steps.
      gather    dated facts from the live web, each with a source and whether it makes a buy riskier or safer
      evaluate  against what we measured ourselves: the exposure dial, the coin's tier and costs, the measured edge (review #26)
      explain   one plain verdict on what the web adds. The web can only make Ananta MORE careful: it can turn a yes into a no or
                a smaller trade, never a no into a yes. Our evidence decides; the web is context.
    Free first (Google Search via Gemini), then Claude web search. Cached 6 hours per coin."""
    coin = (coin or "").upper().replace("/USD", "").replace("USDT", "").strip()
    if not coin:
        raise ValueError("which coin?")
    hit = _MC.get(coin)
    if hit and time.time() - hit[0] < cache_s:
        return hit[1]
    name = coin
    try:
        from jarvis.service import registry

        name = (registry.card(j, coin) or {}).get("name") or coin
    except Exception:  # noqa: BLE001
        pass
    prompt = MARKET_PROMPT.format(today=time.strftime("%Y-%m-%d", time.gmtime()), coin=coin, name=name)
    raw, errors = None, []
    for fn in (_gemini, _claude):
        try:
            raw = fn(coin, post, prompt)
            break
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc)[:160])
    if not raw:
        return {"coin": coin, "error": "web research not available right now: " + " | ".join(errors)}
    try:
        got = _json_in(raw["answer"])
    except Exception:  # noqa: BLE001
        got = {}
    facts = [f for f in (got.get("facts") or []) if isinstance(f, dict) and f.get("fact")][:8]
    ours: dict = {}
    try:
        from jarvis.service import ev, exposure, registry

        d = exposure.state(j)
        ours = {"dial": d.get("dial_words"), "tier": registry.tier_of(j, coin) or ("A" if coin in ("BTC", "ETH") else None),
                "cost_per_side_pct": round(100 * registry.cost(coin), 2),
                "measured_edges_now": [r for r in ev.table() if r["state"] == ("OPEN" if d.get("dial") else "CLOSED")]}
    except Exception as exc:  # noqa: BLE001
        ours = {"error": str(exc)[:120]}
    risky = [f for f in facts if f.get("effect") == "riskier"]
    unlock = str(got.get("unlock_next_30d") or "unknown").lower()
    if unlock == "yes" or any(f.get("kind") in ("security", "regulation") and f.get("effect") == "riskier" for f in facts):
        verdict = "CAUTION: the web shows a real risk (an unlock, a hack, or legal trouble); skip or go smaller even if our rules say buy"
    elif len(risky) >= 3:
        verdict = "CAUTION: several recent things make a buy riskier; our rules decide, but lean to PASS or a smaller size"
    elif not facts:
        verdict = "NOTHING NEW: the web found nothing that changes the picture; our evidence decides alone"
    else:
        verdict = "NO RED FLAGS: nothing on the web argues against what our evidence says; the web never adds a reason to buy"
    out = {"coin": coin, "name": name, "facts": facts, "unlock_next_30d": unlock, "mood": got.get("mood"), "ours": ours,
           "verdict": verdict, "sources": raw.get("sources") or [], "engine": raw.get("engine"), "cost_usd": raw.get("cost_usd", 0.0),
           "label": "From the web, checked against our own evidence",
           "rule": "The web can make Ananta more careful, never more aggressive. Our measured evidence decides."}
    _MC[coin] = (time.time(), out)
    return out


if __name__ == "__main__":
    import sys

    print(json.dumps(lookup(" ".join(sys.argv[1:]) or "What moved the crypto market today?"), indent=2)[:3000])
