"""12 Nov 2026, the keen outside audit (G-54, open-list flag 117). Before: any page or question that found the Kite token dead started a
password sign-in to the real account, every time, and a refusal from Kite that was not a sign-in failure left no trace anywhere. Now the
scheduled job owns the sign-in, an on-demand one waits 30 minutes after any attempt and runs at most three times in 24 hours, the phone is
told "Kite login needed" at most once in 30 minutes, and a refused read leaves one line the self-check reads."""
import json
import re
import time
from pathlib import Path

import pytest
import requests

from india import kite


class _R:
    def __init__(self, code, body):
        self.status_code, self._b, self.text = code, body, json.dumps(body)

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


@pytest.fixture
def k(tmp_path, monkeypatch):
    """A Kite client on fakes: no real token, no real sign-in, no phone, every stamp in the test's own folder."""
    (tmp_path / "auto.env").write_text("x")
    (tmp_path / "repo" / "src" / "india").mkdir(parents=True)
    (tmp_path / "repo" / "src" / "india" / "kite_auth.py").write_text("")
    (tmp_path / "py").write_text("")
    for name, val in (("TOKEN_FILE", tmp_path / "t.json"), ("AUTO_ENV", tmp_path / "auto.env"), ("AGENT_REPO", tmp_path / "repo"),
                      ("AGENT_PY", tmp_path / "py"), ("ATTEMPTS_FILE", tmp_path / "attempts.json"), ("REFUSALS_LOG", tmp_path / "refusals.log"),
                      ("NOTE_STAMP", tmp_path / "note.json")):
        monkeypatch.setattr(kite, name, val)
    spawned, posted = [], []
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: spawned.append(args))
    monkeypatch.setattr(kite.requests, "post", lambda *a, **kw: posted.append(a))
    monkeypatch.setattr(kite, "token", lambda: {"api_key": "key", "access_token": "tok", "user_id": "U"})
    c = kite.Kite(rate_per_s=1e9)
    c.spawned, c.posted, c.tmp = spawned, posted, tmp_path
    return c


def test_a_read_asks_for_a_sign_in_only_after_the_pause_and_under_the_limit(k):
    now = time.time()
    assert kite.on_demand_ok(now)                                              # no attempt yet
    assert kite.try_auto_login() is False and len(k.spawned) == 1             # asked once (the fake signs nobody in)
    assert k.spawned[0][-1] == "--on-demand" and "auto" in k.spawned[0]
    kite.ATTEMPTS_FILE.write_text(json.dumps([{"t": int(now - 600), "kind": "scheduled", "ok": False}]))
    assert not kite.on_demand_ok(now)                                          # the scheduled job tried 10 minutes ago: wait
    assert kite.try_auto_login(force=True) is False and len(k.spawned) == 1   # and no process was started
    kite.ATTEMPTS_FILE.write_text(json.dumps([{"t": int(now - h * 3600), "kind": "on_demand", "ok": False} for h in (20, 10, 2)]))
    assert not kite.on_demand_ok(now)                                          # three on-demand sign-ins in 24 hours: no fourth
    assert kite.on_demand_ok(now + 5 * 3600)


def test_the_two_numbers_match_the_sign_in_module():
    src = Path.home() / "code" / "ananta-agent-research" / "src" / "india" / "kite_auth.py"
    if not src.exists():
        pytest.skip("the agent checkout is not on this machine")
    txt = src.read_text()
    assert int(re.search(r"^ON_DEMAND_PAUSE_S = (\d+)", txt, re.M).group(1)) == kite.ON_DEMAND_PAUSE_S
    assert int(re.search(r"^ON_DEMAND_LIMIT = (\d+)", txt, re.M).group(1)) == kite.ON_DEMAND_LIMIT
    assert "kite_auto_attempts.json" in txt and kite.ATTEMPTS_FILE.name == "kite_auto_attempts.json"


def test_a_refused_read_leaves_one_line_without_parameters(k, monkeypatch):
    monkeypatch.setattr(k.s, "get", lambda *a, **kw: _R(403, {"status": "error", "error_type": "PermissionException", "message": "no access"}))
    with pytest.raises(requests.HTTPError):
        k.get("/quote/ohlc", params={"i": ["NSE:SECRETSYMBOL"]})
    line = kite.REFUSALS_LOG.read_text().strip()
    assert re.fullmatch(r"\S+ 403 PermissionException /quote/ohlc", line), line
    assert "SECRETSYMBOL" not in line and "tok" not in line and "no access" not in line


def test_a_dead_token_tells_the_phone_once_in_thirty_minutes_and_is_not_a_refusal_line(k, monkeypatch):
    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "a-test-topic")
    monkeypatch.setattr(k.s, "get", lambda *a, **kw: _R(403, {"status": "error", "error_type": "TokenException"}))
    kite.ATTEMPTS_FILE.write_text(json.dumps([{"t": int(time.time()), "kind": "scheduled", "ok": False}]))   # so no sign-in is asked for
    for _ in range(3):
        with pytest.raises(kite.NeedLogin):
            k.get("/portfolio/holdings")
    assert len(k.posted) == 1                                                  # one phone note, not three
    assert not kite.REFUSALS_LOG.exists() and k.spawned == []


def test_the_tests_phone_switch_is_honoured(k, monkeypatch):
    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "")                                # set and empty: off (it used to read the topic from the .env file)
    kite._ntfy("anything")
    assert k.posted == [] and not kite.NOTE_STAMP.exists()


# ---- 12 Nov 2026, the outside check of that repair: N10 (a stamp that cannot be read or written) and N5 (an on-demand sign-in says so) ----

@pytest.mark.parametrize("text", ["{not json", '{"t": 1}', "[1, 2"])
def test_a_stamp_that_cannot_be_read_says_no_and_starts_nothing(k, text):
    kite.ATTEMPTS_FILE.write_text(text)
    assert kite.on_demand_ok() is False                                        # it said yes, and the pause and the limit stopped working
    assert kite.try_auto_login() is False and k.spawned == []


def test_no_stamp_yet_is_no_attempts(k):
    assert not kite.ATTEMPTS_FILE.exists() and kite.on_demand_ok() is True


def test_two_readers_at_the_same_moment_send_one_note(k):
    import threading

    now, out = time.time(), []
    ts = [threading.Thread(target=lambda: out.append(kite._note_due(now))) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(out) == [False] * 7 + [True]
    assert kite._note_due(now + kite.NOTE_EVERY_S + 1) is True                # and half an hour later, one more


def test_a_note_stamp_that_cannot_be_written_sends_no_note(k, monkeypatch):
    (k.tmp / "a_file").write_text("x")
    monkeypatch.setattr(kite, "NOTE_STAMP", k.tmp / "a_file" / "note.json")    # its folder cannot be made
    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "a-test-topic")
    assert kite._note_due() is False
    kite._ntfy("Kite login needed")
    assert k.posted == []                                                      # without a stamp there would be no limit


def test_the_morning_still_counts_an_on_demand_sign_in_but_not_a_held_back_line(tmp_path):
    import datetime as dt

    from india import morning
    log = tmp_path / "autologin.log"
    now = dt.datetime(2026, 11, 12, 12, 0, tzinfo=morning.TOR)
    log.write_text("2026-11-12T00:35:10+00:00 auto sign-in FAILED: password step refused\n"
                   "2026-11-12T13:10:00+00:00 on-demand sign-in ok until 2026-11-13 06:00 IST\n"
                   "2026-11-12T13:20:00+00:00 on-demand sign-in held back: the last sign-in attempt was 10 minutes ago\n")
    s = morning.autologin_state(now, log)
    assert s["ok"] is True and s["at"].startswith("Thu 12 Nov 08:10")              # the page's sign-in worked after the failed run
    log.write_text(log.read_text() + "2026-11-12T14:00:00+00:00 on-demand sign-in FAILED: two-factor step refused\n")
    s = morning.autologin_state(now, log)
    assert s["ok"] is False and s["why"] == "two-factor step refused"
