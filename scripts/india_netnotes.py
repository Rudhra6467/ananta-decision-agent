"""Web notes for India's reconstruction card (RX-IN, NET_NOTE; Madhav 23 Oct 2026: "it sees around the net"; agreed as notes only).

Run nightly by launchd (com.ananta.india.netnotes, 22:40 Toronto) through ~/ananta_runs/svc_env_run.py, after the session card is written.
For the session's biggest unexplained moves (the top rises it missed and the top falls, at most NOTES_PER_NIGHT names), it asks Claude with the
web search tool why the stock moved, from public pages published by the end of that IST session, and records a one-line note with its URLs and a
grade (A: an exchange filing or the company itself; B: two independent reputable outlets; C: one source, or the reason is unclear). Each note goes to
the India service (POST /v3/reconstruction/notes) and appears on the card, the Reconstruction screen and in Ask/voice.

Notes only: a note is never a finding by itself and never a reason to trade; nothing behind a login is read. Cost: one Sonnet call with at most
two searches per name, NOTES_PER_NIGHT names a night.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

INDIA = "http://127.0.0.1:8110"
NOTES_PER_NIGHT = 6
MODEL = os.getenv("NETNOTE_MODEL", "claude-sonnet-5-5")

PROMPT = """An NSE-listed Indian stock, {symbol}, closed {move} on {day} (IST). Using web search, find why, from public pages published on or before
the end of {day} IST (exchange announcements, the company, reputable business news). Do not use pages behind a login. If nothing explains it, say so.
Reply with JSON only: {{"note": "<one plain sentence: the reason, or 'no public reason found'>", "grade": "A|B|C", "urls": ["<url>", "<url>"]}}
Grade A = an exchange filing or the company's own statement; B = two independent reputable outlets agree; C = one source or unclear."""


def _get(path: str) -> dict:
    with urllib.request.urlopen(INDIA + path, timeout=20) as r:
        return json.loads(r.read().decode())


def _post(url: str, body: dict, headers: dict | None = None, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", **(headers or {})}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def ask(symbol: str, move: str, day: str) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("no model key")
    r = _post("https://api.anthropic.com/v1/messages",
              {"model": MODEL, "max_tokens": 600, "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}],
               "messages": [{"role": "user", "content": PROMPT.format(symbol=symbol, move=move, day=day)}]},
              {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=120)
    text = "".join(c.get("text", "") for c in r.get("content") or [] if c.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    j = json.loads(m.group(0)) if m else {"note": text.strip()[:240] or "no answer", "grade": "C", "urls": []}
    j["grade"] = j.get("grade") if j.get("grade") in ("A", "B", "C") else "C"
    j["urls"] = [u for u in (j.get("urls") or []) if isinstance(u, str) and u.startswith("http")][:3]
    return j


def main() -> int:
    c = _get("/v3/reconstruction")
    if not c.get("ready"):
        print("india netnotes: no card yet")
        return 0
    day = c["day"]
    have = {n.get("symbol") for n in c.get("net_notes") or []}
    mk = (c.get("sections") or {}).get("market") or {}
    picks = [m for m in (mk.get("movers_up") or []) if m.get("status") == "missed"][:3] + [m for m in (mk.get("movers_down") or [])][:3]
    picks = [m for m in picks if m.get("symbol") not in have][:NOTES_PER_NIGHT]
    n = 0
    for m in picks:
        move = f"{100 * (m.get('cc') or 0):+.1f}%"
        try:
            j = ask(m["symbol"], move, day)
        except Exception as exc:  # noqa: BLE001
            print(f"india netnotes: {m['symbol']}: {exc}")
            continue
        _post(INDIA + "/v3/reconstruction/notes", {"day": day, "symbol": m["symbol"], "note": str(j.get("note"))[:400], "grade": j["grade"], "urls": j["urls"], "asked": f"why {m['symbol']} closed {move}"})
        n += 1
        print(f"india netnotes: {m['symbol']} {move} [{j['grade']}] {j.get('note', '')[:100]}")
    print(f"india netnotes: {n} note(s) for {day}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
