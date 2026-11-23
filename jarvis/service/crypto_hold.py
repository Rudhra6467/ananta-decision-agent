"""Crypto on hold (Madhav, 23 Nov 2026: "right now the crypto market, we can keep it aside and we can keep it weekly ... once we see there is
a turnover ... it can ask me the notification if I want to do this test again"; he chose "Yes, as described").

While the hold is on, the PAID crypto work runs once a week instead of daily: the night test only on Sundays (UTC day) and one crypto brief
on Sunday mornings (Toronto). Nothing that trades on paper changes: the books, the dial, the brain and the guards run as before.

The turnover is Ananta's own rule, the exposure dial (review #25: Bitcoin above its 50-day and 200-day averages) turning OPEN. The first
time it does while the hold is on, the phone gets one note asking whether to go back to daily; nothing switches back by itself.

The hold lives in docs/knowledge/crypto_hold.json ("on": true/false). Only Madhav turns it off."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

FILE = Path(__file__).resolve().parents[2] / "docs" / "knowledge" / "crypto_hold.json"
WEEKLY_DAY = 6          # Sunday (datetime.weekday)
TOLD_KEY = "crypto_hold_turnover_told"


def settings() -> dict:
    try:
        return json.loads(FILE.read_text())
    except Exception:  # noqa: BLE001  no file or a bad one: no hold
        return {"on": False}


def on() -> bool:
    import os
    if os.getenv("PYTEST_CURRENT_TEST") and not os.getenv("CRYPTO_HOLD_IN_TESTS"):   # other tests see the system without the hold
        return False
    return bool(settings().get("on"))


def weekly_day(dt: datetime) -> bool:
    """True when the paid weekly work may run on this day: always when there is no hold, Sundays when there is."""
    return (not on()) or dt.weekday() == WEEKLY_DAY


def turnover(j, push=None, state: dict | None = None) -> dict:
    """While on hold: if the dial is OPEN and he has not been told yet, send one phone note. Free (code only)."""
    if not on():
        return {"hold": False}
    if state is None:
        try:
            from jarvis.service import exposure
            state = exposure.state(j)
        except Exception as exc:  # noqa: BLE001  the dial cannot be read tonight: say so, try again tomorrow
            return {"hold": True, "error": str(exc)[:160]}
    dial = state.get("dial")
    told = j.db.execute("SELECT v FROM engine_state WHERE k=?", (TOLD_KEY,)).fetchone()
    if not dial or dial <= 0:
        return {"hold": True, "dial": dial, "told": bool(told)}
    if told:
        return {"hold": True, "dial": dial, "told": True}
    words = ("The crypto market has turned by Ananta's own rule: " + "; ".join(state.get("why") or []) + ". Crypto's paid checks are weekly "
             "since 23 Nov. Do you want the daily night test, briefs and morning review back? Say yes in chat and they come back.")
    sent = None
    if push:
        try:
            sent = push("Crypto turned: daily checks back?", words)
        except Exception as exc:  # noqa: BLE001
            sent = f"push failed: {exc}"
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (TOLD_KEY, str(int(time.time()))))
    j.db.commit()
    return {"hold": True, "dial": dial, "told": True, "sent": str(sent)[:80], "words": words}
