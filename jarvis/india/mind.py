"""One brain, code as its hands (Madhav, 29 Oct 2026: "yes please" to the plan after "why do these small gaps exist?").

The India Ask had two answerers: fixed code flows (approvals, flags, fix picks, "what's waiting", mode switches, navigation) caught a message by
its words and answered only their own part, and the model answered everything else. The gaps sat at the seam: an approval swallowed the question
asked in the same breath, a question that merely mentioned "flag" or "approve" was taken as a command, and a garbled voice phrase hit the wrong
rule. Now, when a message is compound (more than one sentence and at least one command word), a small fast model reads the WHOLE message first
and splits it into parts, each with a kind. Code still does every action (the model never approves, flags or switches anything itself); it only
decides which part is which. Questions are then answered together by the main model, with what the code did put in front.

  split(text, last_answer) -> [{"kind": ..., "text": ...}, ...]    kinds: ACTION_KINDS + "question" + "remark"
  compound(text) -> bool                                          worth splitting (cheap, in code)
"""
from __future__ import annotations

import json
import os
import re

import requests

SPLIT_MODEL = os.getenv("ASK_SPLIT_MODEL", "claude-haiku-5-5")
ACTION_KINDS = ("approve_drafts", "skip_drafts", "draft_one", "flag", "fix_pick", "waiting", "show", "allocation", "handover", "back")
TRIGGER = re.compile(r"\b(approv\w*|yes to|skip|flag|file (?:a|it|this)|note (?:it|this)|fix (?:\d|one|two|three)|option \d|pick|choose|go with|"
                     r"waiting|pending|show me|open|go to|take me|autonomous|advisory|talk to|hand(?:ing)? over|it'?s me|grader|my (?:mom|dad))\b", re.I)

SPLIT_SYSTEM = """You split one message to a trading assistant (Ananta) into its parts. The owner is Madhav; he often speaks by voice, so the text
may be garbled. Do NOT answer anything. For each part give a kind:
approve_drafts (approve all research drafts / "I approve them all"), skip_drafts (skip all drafts), draft_one (approve, skip or read ONE numbered
draft), flag (asks to flag, note or file a problem or a research idea), fix_pick (picks a numbered fix or option offered in the last answer),
waiting (asks what is waiting for his yes), show (asks to open, show or go to a screen), allocation (switch capital allocation to autonomous or
advisory), handover (hands the conversation to someone: "talk to the grader", "my mom is here"), back (Madhav returning: "it's me"),
question (anything to be answered: market, account, knowledge, how Ananta works, a prediction), remark (thanks, praise, small talk, context).
Rules: a sentence that only MENTIONS a command word while asking about it is a question ("how do I approve drafts?", "should I flag this?").
Keep each part's own words (lightly cleaned). If the whole message is one thing, return one part.
Reply with JSON only: {"parts": [{"kind": "...", "text": "..."}]}"""


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


def compound(text: str) -> bool:
    """Worth a split: at least two sentences, at least one command word, and something beyond the command (a question mark or a long tail)."""
    t = (text or "").strip()
    if len(t) < 25 or not TRIGGER.search(t):
        return False
    ss = _sentences(t)
    return len(ss) >= 2 and ("?" in t or len(ss) >= 3)


def split(text: str, last_answer: str = "", key: str = "", post=None) -> list[dict]:
    """The parts of the message; on any failure, one part of kind 'unsure' (the caller then falls back to the code flows as before)."""
    if not key:
        return [{"kind": "unsure", "text": text}]
    user = (f"LAST ANSWER FROM ANANTA (for context, e.g. numbered fixes it offered): {str(last_answer)[:600] or '(none)'}\n\n"
            f"MESSAGE: {text[:1500]}\n\nJSON only.")
    body = {"model": SPLIT_MODEL, "max_tokens": 500, "system": SPLIT_SYSTEM, "messages": [{"role": "user", "content": user}]}
    post = post or (lambda url, headers, b: requests.post(url, headers=headers, json=b, timeout=20).json())
    try:
        r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body)
        raw = "".join(c.get("text", "") for c in (r.get("content") or []) if c.get("type") == "text")
        m = re.search(r"\{.*\}", raw, re.S)
        parts = (json.loads(m.group(0)) if m else {}).get("parts") or []
        out = [{"kind": str(p.get("kind") or "question"), "text": str(p.get("text") or "").strip()} for p in parts if str(p.get("text") or "").strip()]
        return out or [{"kind": "unsure", "text": text}]
    except Exception:  # noqa: BLE001  the split is a help, never a reason to fail the answer
        return [{"kind": "unsure", "text": text}]
