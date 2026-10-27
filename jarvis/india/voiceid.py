"""Who is speaking, from the voice itself (Madhav, 27 Oct 2026: "Yes for speaker recognition model").

The voice server (jarvis/voice/server.py /stt) scores every clip against Madhav's enrolled voice print with the local speaker service
(jarvis/voice/speaker.py: SpeechBrain ECAPA, Apache-2.0) and returns {"speaker": "madhav" | "not_madhav" | "unknown", "score", "enrolled"}.
jarvis.india.voice.turn passes it to the Ask as context["voice_id"]. This module turns that into one word for the Ask's handover logic.

How ask.py should use it (wired after the handover work lands):
  - typed messages: no voice, identify() returns "unknown"; nothing changes (the handover phrases decide).
  - a voice turn with identify() == "madhav": the speaker is Madhav (owner), even without "it's me": if a handover is active, Madhav is back
    (switch talking_to to Madhav, "Welcome back, sir"), unless he is clearly relaying for the guest ("my mom asks ...").
  - a voice turn with identify() == "other" while a handover is active: it is the guest; keep talking to them.
  - a voice turn with identify() == "other" and no handover: answer general questions normally, but for anything about the account, flags,
    approvals, fixes or "yes to all", ask once: "Who am I speaking with?" (never act on it as Madhav).
  - "unknown" (not enrolled, too short, the service down, or in the doubtful band): fall back to the words (handover phrases), as before.
"""
from __future__ import annotations

import re

OWNER_COMMANDS = ("flag", "yes to all", "approve", "fix ", "use fix", "my account", "my holdings", "reset", "sell", "trim")   # kept for old imports
# 27 Oct (17:20, the grader's voice session): substring matching asked "Who am I speaking with?" on a quiz question whose remark said "the
# intraday sell before delivery point". Only real owner requests count now, with word boundaries: approvals, fix picks, flags, a trade or a
# change asked FOR him, a reset, or a request to see his own account; a word inside a quiz question or a remark never does.
OWNER_REQ = re.compile(
    r"\b(?:yes to (?:all|everything|your (?:recommendations?|suggestions?|fixes?))|i (?:say )?yes to\b|i approve|approved\b|approve (?:it|this|that|the|fix|all)\b|"
    r"(?:pick|choose|use|go with) (?:fix|option) ?(?:\d|one|two|three)\b|^\s*fix (?:\d|one|two|three)\b|flag (?:this|it|that)\b|note (?:this|it) for research|"
    r"(?:file|log|raise) (?:a |the )?(?:flag|bug)\b|"
    r"(?:sell|trim|buy|exit|move) (?:my|the) (?:holdings?|account|capital|money)\b|reset (?:my|the) (?:account|book|books|plan|voice|everything)\b|"
    r"(?:show|open|check|read out|tell me about) (?:me )?my (?:account|holdings|portfolio|flags|money)\b|what(?:'s| is| are) (?:in )?my (?:account|holdings|portfolio)\b|"
    r"how (?:is|are) my (?:account|holdings|portfolio)\b|change (?:the|my) (?:rules?|allocation|plan))", re.I)

# a trade asked FOR him ("sell TATAPOWER for me now"); a question about trading ("should I buy Reliance now?") is a quiz, not an order
TRADE_REQ = re.compile(r"^(?:please |ananta,? |now |just )*(?:sell|trim|buy|exit|add to|cut) (?:my |the |all |half of |some )?[A-Za-z]+(?: shares)?"
                       r"(?: (?:for me|now|right now|today))+\b", re.I)
QUESTION = re.compile(r"\?\s*$|^(?:should|would|could|can|is|are|does|do|did|what|how|when|why|which|who|where)\b", re.I)

def identify(voice_meta: dict | None) -> str:
    """'madhav' | 'other' | 'unknown' from the voice server's speaker field (context["voice_id"])."""
    if not isinstance(voice_meta, dict) or not voice_meta.get("enrolled", True):
        return "unknown"
    s = str(voice_meta.get("speaker") or "")
    if s == "madhav":
        return "madhav"
    if s == "not_madhav":
        return "other"
    return "unknown"


def needs_owner_check(text: str, voice_meta: dict | None, guest_active: bool) -> bool:
    """True when a voice that is not Madhav's asks for an owner-only thing with no handover active: ask 'Who am I speaking with?'."""
    if guest_active or identify(voice_meta) != "other":
        return False
    t = re.sub(r"\s+", " ", (text or "").replace("’", "'")).strip()
    # each sentence on its own, so "Good ... sell before delivery ... Question three ..." is judged sentence by sentence
    for sent in (x.strip() for x in re.split(r"(?<=[.!?])\s+", t) if x.strip()):
        if OWNER_REQ.search(sent) or (not QUESTION.search(sent) and TRADE_REQ.search(sent)):
            return True
    return False


def clearly_other(voice_meta: dict | None, below: float = 0.2) -> bool:
    """The voice print is confident this is NOT Madhav (enrolled, verdict not_madhav, score under `below`): don't call the speaker sir."""
    if identify(voice_meta) != "other":
        return False
    try:
        return float((voice_meta or {}).get("score")) < below
    except (TypeError, ValueError):
        return False
