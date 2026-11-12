"""12 Nov 2026, the keen outside audit (G-57: "the tests' phone-off switch is an empty variable that three helpers bypass by reading the
topic from the .env file, and test isolation is a list of nine past leaks, not a wall"). tests/conftest.py and tests/wall.py put up the
wall before any of Ananta's modules is imported. The outside check of the same morning got through the first version four ways (a full
path to the live database and the .env file, the C-level socket, a UDP datagram, a curl from a test); each of those is a check here, and
each failed against the first version. Nothing here reads a live file: every check is refused before anything is opened."""
import asyncio
import os
import pwd
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path

import _socket
import pytest

REAL_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
CHECKOUT = Path(__file__).resolve().parents[1]
WALL = sys.modules["ananta_tests_wall"]


def test_the_home_folder_is_the_tests_own():
    assert Path.home() != REAL_HOME and "ananta-tests-home-" in str(Path.home())
    linked = sorted(p.name for p in (Path.home() / "code").iterdir())
    assert 1 <= len(linked) <= 2 and not any("decision-agent" in n for n in linked)        # code only: this checkout and the records one


def test_no_live_path_a_module_works_out_points_into_the_real_home():
    from jarvis import selfcheck
    from jarvis.india import ask as india_ask
    from src.india import kite_auth

    real = str(REAL_HOME.resolve()) + os.sep
    for name, p in (("the self-check's file", selfcheck.FILE), ("the crypto database", selfcheck.CRYPTO_DB), ("India's data", india_ask.DATA),
                    ("the India Ask's .env file", india_ask.ENV_FILE), ("the Kite sign-in's private folder", kite_auth.PRIVATE),
                    ("the sign-in log", kite_auth.LOG_FILE), ("the sign-in attempts stamp", kite_auth.ATTEMPTS_FILE),
                    ("the refused-reads log", selfcheck.KITE_REFUSALS)):
        assert not str(Path(p).resolve()).startswith(real), f"{name} points into Madhav's home folder: {p}"


@pytest.mark.parametrize("where", ["code/ananta-decision-agent/.env", "code/ananta-decision-agent/jarvis.sqlite", "ananta_private/kite_token.json",
                                   "ananta_data/selfcheck.json", "ananta_runs/kite_autologin.log", ".ananta/expo_push_tokens.json"])
def test_a_full_path_to_a_private_file_is_refused_before_anything_is_opened(where):
    p = REAL_HOME / where
    with pytest.raises(PermissionError, match="the tests' wall"):
        fd = os.open(p, os.O_RDONLY)
        os.close(fd)                                                                    # only reached if the wall failed: nothing is read
    with pytest.raises(PermissionError, match="the tests' wall"):
        p.read_bytes()


def test_the_live_database_and_a_private_folder_cannot_be_opened_or_listed():
    with pytest.raises(PermissionError, match="the tests' wall"):
        sqlite3.connect(str(REAL_HOME / "code" / "ananta-decision-agent" / "jarvis.sqlite")).close()
    with pytest.raises(PermissionError, match="the tests' wall"):
        sqlite3.connect(f"file:{REAL_HOME / 'code' / 'ananta-decision-agent' / 'jarvis.sqlite'}?mode=ro", uri=True).close()
    with pytest.raises(PermissionError, match="the tests' wall"):
        os.listdir(REAL_HOME / "ananta_private")


def test_nothing_is_written_under_the_real_home_even_in_the_checkouts():
    for p in (REAL_HOME / "ananta_runs" / "zz_wall_probe.txt", CHECKOUT / "docs" / "knowledge" / "zz_wall_probe.json", REAL_HOME / "zz_wall_probe.txt"):
        with pytest.raises(PermissionError, match="the tests' wall"):
            p.write_text("probe")
        assert not p.exists()
    with pytest.raises(PermissionError, match="the tests' wall"):
        os.rename(CHECKOUT / "docs" / "knowledge" / "changes.jsonl", CHECKOUT / "docs" / "knowledge" / "zz_moved.jsonl")
    assert (CHECKOUT / "docs" / "knowledge" / "changes.jsonl").exists()
    assert "def install" in (CHECKOUT / "tests" / "wall.py").read_text()                 # reading code stays free


def test_the_network_is_closed_however_it_is_reached():
    with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
        socket.create_connection(("1.1.1.1", 443), timeout=1)
    with pytest.raises(socket.gaierror, match="the tests' wall"):
        socket.getaddrinfo("example.com", 443)
    for port in (8100, 8110):                                                           # the live crypto and India services on this Mac
        with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
            socket.create_connection(("127.0.0.1", port), timeout=1)
        s = _socket.socket(socket.AF_INET, socket.SOCK_STREAM)                          # the C-level socket (it got through the first wall)
        try:
            with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
                s.connect(("127.0.0.1", port))
        finally:
            s.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                           # the base class's connect, called directly
        try:
            with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
                _socket.socket.connect(s, ("127.0.0.1", port))
        finally:
            s.close()
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)                                # a datagram (it got through the first wall)
    try:
        with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
            u.sendto(b"x", ("1.1.1.1", 53))
        with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
            u.sendto(b"x", ("127.0.0.1", 8110))
    finally:
        u.close()

    async def _open():
        await asyncio.open_connection("127.0.0.1", 8110)

    with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
        asyncio.run(_open())


def test_no_network_or_service_program_is_started_and_a_child_python_has_the_wall_too():
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run(["curl", "-s", "http://127.0.0.1:8110/health"], capture_output=True, timeout=10)  # it reached the live India service
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run("curl -s http://127.0.0.1:8100/health", shell=True, capture_output=True, timeout=10)
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run(["launchctl", "list"], capture_output=True, timeout=10)
    with pytest.raises(PermissionError, match="the tests' wall"):
        os.system("curl -s http://127.0.0.1:8110/health")
    child = ("import socket, pathlib, pwd, os\n"
             "for f in (lambda: socket.create_connection(('127.0.0.1', 8110), 3),\n"
             "          lambda: pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir, 'ananta_runs', 'zz_wall_probe.txt').write_text('x')):\n"
             "    try:\n"
             "        f(); print('THROUGH')\n"
             "    except OSError as e:\n"
             "        print('REFUSED' if \"tests' wall\" in str(e) else 'OTHER ' + type(e).__name__)\n")
    r = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=60)
    assert r.stdout.split() == ["REFUSED", "REFUSED"], (r.stdout, r.stderr[-400:])
    assert not (REAL_HOME / "ananta_runs" / "zz_wall_probe.txt").exists()


def test_what_the_wall_refused_is_kept_and_never_shows_a_private_file_name():
    try:
        os.open(REAL_HOME / "code" / "ananta-decision-agent" / "jarvis.sqlite", os.O_RDONLY)
    except PermissionError:
        pass
    deep = [x for x in WALL.REFUSED if "~/code/ananta-decision-agent" in x]
    assert deep and all(x.endswith("/...)") for x in deep)                             # the folder, never the file in it
    assert not any("@" in x for x in WALL.REFUSED)


def test_the_phone_switch_is_honoured_by_the_helpers_that_read_the_env_file(monkeypatch):
    """Set and empty means off. Two helpers in this checkout (the Kite sign-in's note and the nightly replay's note) fell through to the
    .env file's topic; the third is the records checkout's Kite client (its own test: tests/test_india_kite_ondemand.py there)."""
    import requests

    from jarvis.india import replay
    from src.india import kite_auth

    def _never(*a, **k):
        raise AssertionError("a test reached for the phone")

    monkeypatch.setenv("ANANTA_NTFY_TOPIC", "")
    monkeypatch.setattr(requests, "post", _never)
    env = Path.home() / "code" / "ananta-decision-agent"
    env.mkdir(parents=True, exist_ok=True)                                              # even with a topic in a .env file where the helpers look
    (env / ".env").write_text('ANANTA_NTFY_TOPIC="a-topic-in-the-wall"\n')
    try:
        kite_auth._ntfy("anything")
        replay._ntfy("a title", "a body")
    finally:
        (env / ".env").unlink()
        env.rmdir()
