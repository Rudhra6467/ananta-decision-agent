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


def _gemini(q: str, post=_post) -> dict:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    err = None
    for m in GEMINI_ORDER:
        try:
            r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                     {"x-goog-api-key": key, "content-type": "application/json"},
                     {"contents": [{"role": "user", "parts": [{"text": PROMPT.format(q=q)}]}], "tools": [{"google_search": {}}],
                      "generationConfig": {"temperature": 0.2, "maxOutputTokens": 900}})
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


def _claude(q: str, post=_post) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    r = post("https://api.anthropic.com/v1/messages",
             {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
             {"model": HAIKU, "max_tokens": 900, "messages": [{"role": "user", "content": PROMPT.format(q=q)}],
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


if __name__ == "__main__":
    import sys

    print(json.dumps(lookup(" ".join(sys.argv[1:]) or "What moved the crypto market today?"), indent=2)[:3000])
