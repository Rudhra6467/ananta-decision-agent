"""Tests never push to a real phone, even when run on the laptop where .env holds the ntfy topic; and they never reach the web
or touch the live paid-search counters."""
import importlib.util
import os
import pwd
import sys
import tempfile

import pytest

# 12 Nov 2026, the keen outside audit (G-57: "test isolation is a list of nine past leaks, not a wall"). Put up before any of Ananta's
# own modules is imported:
# 1. The home folder. Tests run with HOME set to an empty folder of their own; only the two code checkouts are linked in. Every path a
#    module works out from the home folder lands there. The one module that names the live .env file by its full path is pointed there too.
# 2. The wall (tests/wall.py, on Python's audit hooks): nothing under Madhav's private places is opened even by its full path, nothing
#    under his home is written, nothing leaves this machine or reaches the live services, no network or service program is started, and
#    every Python a test starts puts up the same wall. The first version of the morning (a patched socket class) was got through by the
#    outside check four ways; this one is what it could not get through. What it refused is printed at the end of the run.
REAL_HOME = pwd.getpwuid(os.getuid()).pw_dir
TEST_HOME = tempfile.mkdtemp(prefix="ananta-tests-home-")
os.makedirs(os.path.join(TEST_HOME, "code"))
for _repo in ("ananta-agent-research", "ananta-records"):
    if os.path.isdir(os.path.join(REAL_HOME, "code", _repo)):
        os.symlink(os.path.join(REAL_HOME, "code", _repo), os.path.join(TEST_HOME, "code", _repo))
os.environ["HOME"] = TEST_HOME
os.environ["ANANTA_AGENT_ENV"] = os.path.join(TEST_HOME, "code", "ananta-decision-agent", ".env")   # jarvis/india/ask.py ENV_FILE
os.environ["ANANTA_INDIA_DATA"] = os.path.join(TEST_HOME, "ananta_data", "india")

_WALL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wall.py")
_spec = importlib.util.spec_from_file_location("ananta_tests_wall", _WALL_FILE)
wall = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wall)
sys.modules["ananta_tests_wall"] = wall                             # one wall per process: tests read its REFUSED list through this name
_site = os.path.join(TEST_HOME, ".wall")
os.makedirs(_site)
with open(os.path.join(_site, "sitecustomize.py"), "w") as _f:
    _f.write(wall.SITECUSTOMIZE.format(wall=_WALL_FILE, home=REAL_HOME, readable=(), never=()))
os.environ["PYTHONPATH"] = _site + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
wall.install(REAL_HOME)


def pytest_terminal_summary(terminalreporter):
    """What the wall refused during the run: a test that reached for a live file, the network or a service shows here, even when its
    code swallowed the error (the paths are shown only to their first folders)."""
    if wall.REFUSED:
        terminalreporter.write_sep("-", f"the tests' wall refused {len(wall.REFUSED)} kind(s) of reach")
        for line in wall.REFUSED[:80]:
            terminalreporter.write_line(line)

os.environ["ANANTA_NTFY_TOPIC"] = ""
os.environ["ANANTA_APPLE_PUSH"] = "0"
os.environ["ANANTA_EXPO_TOKENS"] = os.path.join(__import__("tempfile").mkdtemp(prefix="ananta-tests-"), "expo_push_tokens.json")


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
def _no_live_worker(tmp_path, monkeypatch):
    """Oct 15 (worker S1): tests never read the worker days pulled onto this Mac or SSH to the worker; each test starts empty."""
    from jarvis.service import ndax_spreads, worker

    monkeypatch.setattr(worker, "DEST", tmp_path / "worker_data")
    monkeypatch.setattr(ndax_spreads, "DEST", tmp_path / "worker_data")
    monkeypatch.setattr(worker, "_ssh", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tests never reach the worker")))
    worker._CACHE.clear()


@pytest.fixture(autouse=True)
def _no_live_kill_switch(monkeypatch):
    """Oct 15 (the trade guard): every new paper position asks Hands for the kill switch, and a read that fails blocks. Tests never
    reach Hands: a real Hands object reads "off" here, without the network (a test's own fake Hands still decides for itself), and
    the guard's memory of a failed read starts empty."""
    from jarvis.service import trade_guard
    from src.intelligence import explorer_live

    monkeypatch.setattr(explorer_live.Hands, "kill_switch_on", lambda self: False)
    trade_guard.reset()
    from jarvis.service import eye

    for k in ("prices", "prices_t", "prices_lim"):            # the eye's last look (with its times) never leaks into the next test
        monkeypatch.delitem(eye.STATE, k, raising=False)


@pytest.fixture(autouse=True)
def _no_live_shadow_log(tmp_path, monkeypatch):
    """Oct 20 (OD-SHADOW-LANE): the nightly round and the 15-minute jobs now call the shadow lane. Tests never append to the real
    ~/ananta_runs/shadow/shadow_log.jsonl: each test gets its own folder."""
    monkeypatch.setenv("ANANTA_SHADOW_DIR", str(tmp_path / "shadow_lane"))


@pytest.fixture(autouse=True)
def _strategy_status_as_tested(tmp_path, monkeypatch, request):
    """28 Oct 2026: Madhav parked H07 in the live strategy file (docs/knowledge/strategy_status.json). The behaviour tests describe the engine with
    each strategy at its designed status, so they read a copy with any Madhav park undone ('status_before_park'); the lock test still reads the
    live file. A test that wants the live file marks itself with @pytest.mark.live_status."""
    if request.node.get_closest_marker("live_status"):
        return
    import json as _json
    from jarvis.service import strategy_status as _ss

    try:
        live = _json.loads(_ss._path().read_text())
    except (OSError, ValueError):
        return
    for sid in [k for k, s in (live.get("strategies") or {}).items() if s.get("split_from")]:
        live["strategies"].pop(sid)                      # 10 Nov 2026: a part split off a rule by a Madhav decision (H07_SMALL) is undone too
    for s in (live.get("strategies") or {}).values():
        if s.get("as_designed"):
            s.update(s.pop("as_designed"))
            s.pop("park_periods", None)
        if s.get("status_before_park"):
            s["status"] = s.pop("status_before_park")
            s.pop("parked", None)
    p = tmp_path / "strategy_status_as_tested.json"
    p.write_text(_json.dumps(live))
    monkeypatch.setattr(_ss, "_path", lambda: p)
    _ss._CACHE.update(m=None, v={})


@pytest.fixture(autouse=True)
def _no_live_split(monkeypatch):
    """29 Oct: the India Ask's message splitter (jarvis/india/mind.py) calls a model; tests never reach the network for it. A test that
    wants a split passes its own `split_post` to ask(), which this fixture leaves alone."""
    from jarvis.india import mind

    real = mind.split
    monkeypatch.setattr(mind, "split", lambda text, last_answer="", key="", post=None: real(text, last_answer, key=key, post=post) if post else
                        [{"kind": "unsure", "text": text}])


@pytest.fixture(autouse=True)
def _no_live_selfcheck(tmp_path, monkeypatch):
    """5 Nov (the self-check): tests never read or write the live ~/ananta_data/selfcheck.json, so no answer in a test carries a real
    'one thing that isn't right' line."""
    from jarvis import selfcheck

    monkeypatch.setattr(selfcheck, "FILE", tmp_path / "selfcheck.json")
    monkeypatch.setattr(selfcheck, "_credit", lambda post=None: [])     # and never call the Anthropic API


@pytest.fixture(autouse=True)
def _no_live_india_timing(tmp_path, monkeypatch):
    """11 Nov 2026 (the keen audit's register, R-041): the test suite wrote its own rows into the real India reports/ask_timing.jsonl,
    which the self-scan reads for slow answers. A timing line written while a test runs goes to that test's own folder; a test that
    points the India data folder somewhere else itself keeps it."""
    from jarvis.india import ask as india_ask

    real, live = india_ask._timing_log, india_ask.DATA

    def _timing_log(*a, **k):
        if india_ask.DATA != live:
            return real(*a, **k)
        with monkeypatch.context() as m:
            m.setattr(india_ask, "DATA", tmp_path / "india_data")
            return real(*a, **k)

    monkeypatch.setattr(india_ask, "_timing_log", _timing_log)


@pytest.fixture
def india_reference(monkeypatch):
    """12 Nov 2026 (the wall found them): four tests read NSE's holiday calendar and the company-name list from Madhav's live India data
    through the code under test. A test that needs them asks for this fixture: a small calendar and name list of the tests' own."""
    import datetime as dt
    import time

    from jarvis.india import answerguide, askwords

    monkeypatch.setattr(answerguide, "_holidays", lambda: {dt.date(2026, 11, 10), dt.date(2026, 11, 24)})   # NSE's: Diwali-Balipratipada, Guru Nanak's birthday
    monkeypatch.setitem(askwords._NAMES, "t", time.time())
    monkeypatch.setitem(askwords._NAMES, "v", {"TATAPOWER": "Tata Power", "JIOFIN": "Jio Financial", "ETERNAL": "Eternal", "LICI": "LIC of India",
                                               "IEX": "Indian Energy Exchange", "IDEA": "Vodafone Idea"})

