"""23 Nov 2026 (Madhav): crypto on hold. The paid crypto work runs weekly, and one phone note goes out when the dial opens."""
import sqlite3
from datetime import datetime

from jarvis.service import crypto_hold


class J:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT)")


def test_weekly_day_only_on_sunday_when_on(monkeypatch):
    monkeypatch.setenv("CRYPTO_HOLD_IN_TESTS", "1")
    monkeypatch.setattr(crypto_hold, "settings", lambda: {"on": True})
    assert crypto_hold.weekly_day(datetime(2026, 11, 29))        # Sunday
    assert not crypto_hold.weekly_day(datetime(2026, 11, 24))    # Tuesday
    monkeypatch.setattr(crypto_hold, "settings", lambda: {"on": False})
    assert crypto_hold.weekly_day(datetime(2026, 11, 24))


def test_one_note_when_the_dial_opens(monkeypatch):
    monkeypatch.setenv("CRYPTO_HOLD_IN_TESTS", "1")
    monkeypatch.setattr(crypto_hold, "settings", lambda: {"on": True})
    j, sent = J(), []
    shut = {"dial": 0.0, "why": ["below"]}
    assert crypto_hold.turnover(j, lambda t, b: sent.append(b), state=shut)["told"] is False
    opened = {"dial": 1.0, "why": ["Bitcoin closed 2026-12-01 at 80,000", "above its 50-day average", "above its 200-day average"]}
    r = crypto_hold.turnover(j, lambda t, b: sent.append(b), state=opened)
    assert r["told"] and len(sent) == 1 and "daily" in sent[0]
    crypto_hold.turnover(j, lambda t, b: sent.append(b), state=opened)
    assert len(sent) == 1                                          # told once


def test_the_hold_file_is_on():
    assert crypto_hold.settings().get("on") is True


def test_brief_only_sunday_morning(monkeypatch):
    monkeypatch.setenv("CRYPTO_HOLD_IN_TESTS", "1")
    from jarvis.service import alerts
    monkeypatch.setattr(crypto_hold, "settings", lambda: {"on": True})

    class A(alerts.Alerts if hasattr(alerts, "Alerts") else object):
        pass
    fn = None
    for name in dir(alerts):
        obj = getattr(alerts, name)
        if isinstance(obj, type) and hasattr(obj, "due_brief"):
            fn = obj.due_brief
    assert fn is not None

    class Fake:
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE briefings (day TEXT, kind TEXT)")

        def __init__(self, t):
            self._t = t

        def now(self):
            return self._t
    tue = datetime(2026, 11, 24, 9, 0).timestamp() + 5 * 3600
    sun = datetime(2026, 11, 29, 9, 0).timestamp() + 5 * 3600
    assert fn(Fake(tue)) is None
    assert fn(Fake(sun)) == "morning"
