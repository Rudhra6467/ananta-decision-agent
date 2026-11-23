"""20 Nov 2026 (Madhav, 20:21: "until we trade and do something in this crypto market, is it needed to run all audits and tests on daily
basis"; 20:27 "Let's get this done"): the paid crypto night test runs only when something happened since the last tested night, and at
least once a week. Each test fails on the code before the change (no quiet_night, record_quiet or quiet existed)."""
import json
import time

import pytest

from jarvis.service import nightcheck, quietnight as N

DAY = 86400


class FakeJ:
    def __init__(self, now, db):
        self._now, self.db = now, db

    def now(self):
        return self._now


@pytest.fixture
def world(tmp_path, monkeypatch):
    import sqlite3

    monkeypatch.setattr(N, "OUT", tmp_path)
    monkeypatch.setattr(nightcheck, "OUT", tmp_path)
    monkeypatch.setattr(N, "QUIET", tmp_path / "crypto_quiet.json")
    monkeypatch.setattr(N, "_code_changed_since", lambda t0: False)
    monkeypatch.delenv("NIGHTCHECK_EVERY_NIGHT", raising=False)
    db = sqlite3.connect(":memory:")
    db.executescript("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT); CREATE TABLE book500_fills (t REAL);"
                     "CREATE TABLE alerts (fired_t REAL); CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT);")
    t0 = 1_795_000_000
    db.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"pos": {}, "dial": 0, "value": 498.7, "brakes": {}}),))
    (tmp_path / "crypto_latest.json").write_text(json.dumps({"day": "2026-11-20", "t": t0, "asked": 6, "right": 5, "dial": 0}))
    return FakeJ(t0 + DAY, db), db, t0, tmp_path


def test_a_quiet_night_is_not_tested_and_says_why(world):
    j, db, t0, out = world
    why = N.quiet_night(j)
    assert why and "no paid test" in why and "all in cash" in why
    q = N.record_quiet(why, now=j.now())
    assert q["since_test"] == 1 and N.quiet()["since_test"] == 1
    assert N.record_quiet(why, now=j.now() + DAY)["since_test"] == 2
    hist = [json.loads(x) for x in (out / "crypto_history.jsonl").read_text().splitlines()]
    assert all(h["quiet"] and h["cost_usd"] == 0 for h in hist)


@pytest.mark.parametrize("what", ["coin", "fill", "alert", "brake", "dial", "code", "dirty", "week", "no_dial_on_file", "every_night"])
def test_anything_that_happened_means_tonight_is_tested(world, monkeypatch, what):
    j, db, t0, out = world
    st = {"pos": {}, "dial": 0, "value": 498.7, "brakes": {}}
    if what == "coin":
        st["pos"] = {"BTC": 0.001}
    if what == "brake":
        st["brakes"] = {"paused": True}
    if what == "dial":
        st["dial"] = 0.5
    db.execute("UPDATE book500 SET v=? WHERE k='state'", (json.dumps(st),))
    if what == "fill":
        db.execute("INSERT INTO book500_fills VALUES (?)", (t0 + 60,))
    if what == "alert":
        db.execute("INSERT INTO alerts VALUES (?)", (t0 + 60,))
    if what == "code":
        monkeypatch.setattr(N, "_code_changed_since", lambda t: True)
    if what == "dirty":
        day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
        db.execute("INSERT INTO engine_state VALUES (?, ?)", ("clean_night:" + day, json.dumps({"clean": False, "why": ["x"]})))
    if what == "week":
        j._now = t0 + 7 * DAY
    if what == "no_dial_on_file":
        (out / "crypto_latest.json").write_text(json.dumps({"day": "2026-11-20", "t": t0, "asked": 6, "right": 5}))
    if what == "every_night":
        monkeypatch.setenv("NIGHTCHECK_EVERY_NIGHT", "1")
    assert N.quiet_night(j) is None


def test_git_that_cannot_be_read_means_tested(world, monkeypatch):
    j, *_ = world
    monkeypatch.setattr(N, "_code_changed_since", lambda t0: None)
    assert N.quiet_night(j) is None


def test_a_new_test_ends_the_quiet_run(world):
    j, db, t0, out = world
    N.record_quiet("quiet", now=j.now())
    (out / "crypto_latest.json").write_text(json.dumps({"day": "2026-11-22", "t": t0 + 2 * DAY, "asked": 6, "right": 6, "dial": 0}))
    assert N.quiet() is None


def test_start_night_test_does_not_start_the_paid_run_on_a_quiet_night(world, monkeypatch):
    from jarvis.service import universe_watch as U

    j, db, t0, out = world
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    from jarvis.service import crypto_hold                 # 23 Nov: this test is about quiet nights, not the crypto hold
    monkeypatch.setattr(crypto_hold, "settings", lambda: {"on": False})
    started = []
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: started.append(a))
    assert U.start_night_test(j) is False and not started
    assert N.quiet()["since_test"] == 1
