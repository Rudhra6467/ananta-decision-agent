"""Tests never push to a real phone, even when run on the laptop where .env holds the ntfy topic; and they never reach the web
or touch the live paid-search counters."""
import importlib.util
import os
import pwd
import sys
import tempfile

import pytest

# 12 Nov 2026 (the outside check of audit repair 1, N4: "the records tests run with the real home and an open network; only the phone and
# the sign-in are guarded"). The agent checkout's tests' wall (tests/wall.py there, on Python's audit hooks) goes up here too, before any
# records module is imported, with one difference: India's data folder may be read (three test files read it on purpose), never written,
# and the sealed data is refused even to a read. Nothing leaves this machine or reaches the live services, nothing under the home is
# written, no private place is opened, and every Python a test starts has the same wall. What it refused is printed at the end of the run.
REAL_HOME = pwd.getpwuid(os.getuid()).pw_dir
READABLE, NEVER = ("ananta_data/india",), ("ananta_data/india/sealed",)
_WALL_FILE = os.path.join(REAL_HOME, "code", "ananta-agent-research", "tests", "wall.py")
wall = None
if os.path.exists(_WALL_FILE):
    _spec = importlib.util.spec_from_file_location("ananta_tests_wall", _WALL_FILE)
    wall = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(wall)
    sys.modules["ananta_tests_wall"] = wall
    _site = os.path.join(tempfile.mkdtemp(prefix="ananta-records-tests-"), ".wall")
    os.makedirs(_site)
    with open(os.path.join(_site, "sitecustomize.py"), "w") as _f:
        _f.write(wall.SITECUSTOMIZE.format(wall=_WALL_FILE, home=REAL_HOME, readable=READABLE, never=NEVER))
    os.environ["PYTHONPATH"] = _site + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
    wall.install(REAL_HOME, readable=READABLE, never=NEVER)


def pytest_terminal_summary(terminalreporter):
    if wall is None:
        terminalreporter.write_sep("-", "the tests' wall is not up: the agent checkout's tests/wall.py is not on this machine")
    elif wall.REFUSED:
        terminalreporter.write_sep("-", f"the tests' wall refused {len(wall.REFUSED)} kind(s) of reach")
        for line in wall.REFUSED[:80]:
            terminalreporter.write_line(line)


os.environ["ANANTA_NTFY_TOPIC"] = ""


@pytest.fixture(autouse=True)
def _no_live_web(tmp_path, monkeypatch):
    """Oct 15: a test that reached the brain's web veto made real requests (with fake keys) and counted against the LIVE paid-search
    cap in ~/ananta_runs/web_paid.json: the brain's 8 background searches for Oct 15 were used up by 04:32, partly by test runs.
    Now every test keeps its counters in its own folder, and weblook's network call refuses."""
    from jarvis.service import weblook

    monkeypatch.setenv("WEB_PAID_FILE", str(tmp_path / "web_paid.json"))
    monkeypatch.setenv("WEB_PAID_LOG", str(tmp_path / "web_paid_log.jsonl"))

    def _no_web(*a, **k):
        raise RuntimeError("tests never reach the web")

    monkeypatch.setattr(weblook, "_post", _no_web)
    weblook._MC.clear()


@pytest.fixture(autouse=True)
def _no_live_kite_sign_in(tmp_path, monkeypatch):
    """12 Nov 2026 (the keen outside audit, G-54 and G-57): on the Mac, a test that asked india.kite for a token with none on disk could
    start the real password sign-in (test_kite_token_expiry did, since 22 Oct), and the phone note read its topic from the .env file
    whatever the tests' switch said. No test starts a sign-in, writes the live attempt, refusal or note stamps, or reaches the phone."""
    try:
        from india import kite
    except Exception:  # noqa: BLE001  a checkout without the India package
        return
    monkeypatch.setattr(kite, "AUTO_ENV", tmp_path / "no_auto_sign_in.env")
    monkeypatch.setattr(kite, "ATTEMPTS_FILE", tmp_path / "kite_auto_attempts.json")
    monkeypatch.setattr(kite, "REFUSALS_LOG", tmp_path / "kite_refusals.log")
    monkeypatch.setattr(kite, "NOTE_STAMP", tmp_path / "kite_note_stamp.json")
    monkeypatch.setattr(kite, "TOKEN_FILE", tmp_path / "no_kite_token.json")   # 12 Nov: the wall's first run showed a test reading the real one


@pytest.fixture(autouse=True)
def _no_private_people(tmp_path, monkeypatch):
    """12 Nov 2026: the wall's first records run showed tests reading the private people lists (~/ananta_private/people.json and
    india_people.json, which hold family names). The wall refuses them; here they point at the test's own empty folder instead."""
    monkeypatch.setenv("PEOPLE_FILE", str(tmp_path / "people.json"))
    try:
        from india import telugu
    except Exception:  # noqa: BLE001  a checkout without the India package
        return
    monkeypatch.setattr(telugu, "PEOPLE", tmp_path / "india_people.json")
