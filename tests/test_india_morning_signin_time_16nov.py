"""16 Nov 2026 morning review: the morning summary said the automatic Kite sign-in runs at 06:05 IST (19:35 Toronto) after it had moved
to 06:40 IST on 15 Nov (the plist runs at 20:10, 20:20 and 20:40 Toronto in winter)."""
import datetime as dt

from india import morning


def test_next_signin_says_the_new_time(monkeypatch):
    monkeypatch.setattr(morning, "autologin_state", lambda now, log=None: {"ok": True, "at": "Sun 15 Nov 20:19 Toronto"})
    now = dt.datetime(2026, 11, 16, 12, 48, tzinfo=dt.timezone.utc)          # Mon 07:48 Toronto, 18:18 IST
    words = morning.next_signin(now, hol=set())
    assert "automatic at 20:10 Toronto, 06:40 IST" in words
    assert "06:05" not in words and "19:35" not in words
