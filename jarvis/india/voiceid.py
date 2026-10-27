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

OWNER_COMMANDS = ("flag", "yes to all", "approve", "fix ", "use fix", "my account", "my holdings", "reset", "sell", "trim")


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
    t = (text or "").lower()
    return any(k in t for k in OWNER_COMMANDS)
