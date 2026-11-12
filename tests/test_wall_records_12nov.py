"""12 Nov 2026, the outside check of audit repair 1 (N4: "the records tests run with the real home and an open network; only the phone and
the sign-in are guarded"). tests/conftest.py now puts up the agent checkout's tests' wall here too, before any records module is imported.
India's data folder may be read (three test files read it on purpose), never written; the sealed data is refused even to a read. These
checks are refused before anything is written or sent, and aim at folders that do not exist, so nothing could be made even if the wall
failed; the sealed folder is checked through the wall's own rule, never opened."""
import os
import pwd
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REAL_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
CHECKOUT = Path(__file__).resolve().parents[1]
WALL = sys.modules.get("ananta_tests_wall")
pytestmark = pytest.mark.skipif(WALL is None, reason="the agent checkout's tests/wall.py is not on this machine")


@pytest.fixture(autouse=True)
def _only_real_refusals_in_the_summary():
    before = list(WALL.REFUSED) if WALL else []
    yield
    if WALL:
        WALL.REFUSED[:] = before


def test_the_wall_is_up_before_the_tests_run():
    assert WALL._state["on"] and WALL._state["home"] == os.path.realpath(REAL_HOME)


def test_nothing_is_written_under_the_home_not_this_checkout_nor_the_runs_folder():
    for p in (CHECKOUT / "india" / "registrations" / "zz_wall_no_such_dir" / "probe.md", REAL_HOME / "ananta_runs" / "zz_wall_no_such_dir" / "probe.txt",
              REAL_HOME / "zz_wall_no_such_dir" / "probe.txt"):
        with pytest.raises(PermissionError, match="the tests' wall"):
            p.write_text("probe")
        assert not p.parent.exists()


def test_india_data_may_be_read_never_written_and_the_sealed_data_is_refused_even_to_a_read():
    india = os.path.join(os.path.realpath(REAL_HOME), "ananta_data", "india")
    assert WALL._file(os.path.join(india, "paper", "managed", "book.json"), write=False) is None            # reading is allowed
    assert WALL._file(os.path.join(india, "paper", "managed", "book.json"), write=True)[2] is PermissionError
    assert WALL._file(os.path.join(india, "sealed", "anything"), write=False)[0] == "opening a sealed or private place"
    for private in ("ananta_private/kite_token.json", "code/ananta-decision-agent/.env", ".appstore/x", "ananta_runs/kite_autologin.log"):
        assert WALL._file(os.path.join(os.path.realpath(REAL_HOME), private), write=False)[2] is PermissionError, private


def test_the_network_and_the_live_services_are_closed():
    with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
        socket.create_connection(("1.1.1.1", 443), timeout=1)
    with pytest.raises(socket.gaierror, match="the tests' wall"):
        socket.getaddrinfo("api.kite.trade", 443)
    for port in (8100, 8110):
        with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
            socket.create_connection(("127.0.0.1", port), timeout=1)
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run(["curl", "-s", "--max-time", "1", "http://127.0.0.1:9/"], capture_output=True, timeout=20)


def test_a_python_a_test_starts_has_the_same_wall():
    child = ("import pathlib, pwd, os\n"
             "try:\n"
             "    pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir, 'ananta_runs', 'zz_wall_no_such_dir', 'probe.txt').write_text('x'); print('THROUGH')\n"
             "except OSError as e:\n"
             "    print('REFUSED' if \"tests' wall\" in str(e) else 'OTHER')\n")
    r = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=60)
    assert r.stdout.split() == ["REFUSED"], (r.stdout, r.stderr[-400:])
    assert not (REAL_HOME / "ananta_runs" / "zz_wall_no_such_dir").exists()
