"""12 Nov 2026, the keen outside audit (G-57: "the tests' phone-off switch is an empty variable that three helpers bypass by reading the
topic from the .env file, and test isolation is a list of nine past leaks, not a wall"). tests/conftest.py and tests/wall.py put up the
wall before any of Ananta's modules is imported. The outside check of the same morning got through the first version four ways (a full
path to the live database and the .env file, the C-level socket, a UDP datagram, a curl from a test); each of those is a check here, and
each failed against the first version. Nothing here reads a live file: every check is refused before anything is opened.

12 Nov, later: every check now aims at a name that does not exist inside the private place (and a write at a folder that does not exist),
so if the wall ever failed, nothing could be read, made, moved or changed: the wall decides by the path, so that is the same check. Proving
the newer checks failed against the older wall had let two of them read a real private file inside a test (thrown away unseen)."""
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


@pytest.fixture(autouse=True)
def _only_real_refusals_in_the_summary():
    """What these checks provoke on purpose is not listed at the end of the run; what other tests reach for still is."""
    before = list(WALL.REFUSED)
    yield
    WALL.REFUSED[:] = before


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


NONE = "zz_wall_no_such"                         # a name that is never there: if the wall failed, nothing is read, made or changed


@pytest.mark.parametrize("where", [f"code/ananta-decision-agent/{NONE}.env", f"code/ananta-decision-agent/{NONE}.sqlite", f"ananta_private/{NONE}.json",
                                   f"ananta_data/{NONE}.json", f"ananta_runs/{NONE}.log", f".ananta/{NONE}.json", f"code/ananta-agent-research/{NONE}.env"])
def test_a_full_path_to_a_private_file_is_refused_before_anything_is_opened(where):
    p = REAL_HOME / where
    with pytest.raises(PermissionError, match="the tests' wall"):
        fd = os.open(p, os.O_RDONLY)
        os.close(fd)                                                                    # only reached if the wall failed: nothing is read
    with pytest.raises(PermissionError, match="the tests' wall"):
        p.read_bytes()


def test_the_live_database_and_a_private_folder_cannot_be_opened_or_listed():
    db = REAL_HOME / "code" / "ananta-decision-agent" / f"{NONE}_dir" / "jarvis.sqlite"   # the live database's folder (a missing one in it)
    with pytest.raises(PermissionError, match="the tests' wall"):
        sqlite3.connect(str(db)).close()
    with pytest.raises(PermissionError, match="the tests' wall"):
        sqlite3.connect(f"file:{db}?mode=ro", uri=True).close()
    with pytest.raises(PermissionError, match="the tests' wall"):
        os.listdir(REAL_HOME / "ananta_private" / f"{NONE}_dir")


def test_nothing_is_written_under_the_real_home_even_in_the_checkouts():
    for p in (REAL_HOME / "ananta_runs" / f"{NONE}_dir" / "probe.txt", CHECKOUT / "docs" / "knowledge" / f"{NONE}_dir" / "probe.json",
              REAL_HOME / f"{NONE}_dir" / "probe.txt"):
        with pytest.raises(PermissionError, match="the tests' wall"):
            p.write_text("probe")
        assert not p.parent.exists()
    with pytest.raises(PermissionError, match="the tests' wall"):
        os.rename(CHECKOUT / "docs" / "knowledge" / f"{NONE}.jsonl", CHECKOUT / "docs" / "knowledge" / f"{NONE}_moved.jsonl")
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
        subprocess.run(["curl", "-s", "--max-time", "1", "http://127.0.0.1:9/"], capture_output=True, timeout=10)  # it reached the live India service once
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run("curl -s --max-time 1 http://127.0.0.1:9/", shell=True, capture_output=True, timeout=10)
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run(["launchctl", "list"], capture_output=True, timeout=10)
    with pytest.raises(PermissionError, match="the tests' wall"):
        os.system("curl -s --max-time 1 http://127.0.0.1:9/")
    child = ("import socket, pathlib, pwd, os\n"
             "for f in (lambda: socket.create_connection(('127.0.0.1', 8110), 3),\n"
             "          lambda: pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir, 'ananta_runs', 'zz_wall_no_such_dir', 'probe.txt').write_text('x')):\n"
             "    try:\n"
             "        f(); print('THROUGH')\n"
             "    except OSError as e:\n"
             "        print('REFUSED' if \"tests' wall\" in str(e) else 'OTHER ' + type(e).__name__)\n")
    r = subprocess.run([sys.executable, "-c", child], capture_output=True, text=True, timeout=60)
    assert r.stdout.split() == ["REFUSED", "REFUSED"], (r.stdout, r.stderr[-400:])
    assert not (REAL_HOME / "ananta_runs" / "zz_wall_no_such_dir").exists()


def test_what_the_wall_refused_is_kept_and_never_shows_a_private_file_name():
    try:
        os.open(REAL_HOME / "code" / "ananta-decision-agent" / f"{NONE}.sqlite", os.O_RDONLY)
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



# ---- 12 Nov 2026, the second outside check read more ways through the second wall (its N2, N3, N8, N17 and the smaller notes) ----------
# None was tried then; each is a check here, refused before anything is opened, sent or started. The targets are harmless if the wall
# failed: the discard port 9 on this Mac, a folder that does not exist, a name that cannot resolve.

def test_a_name_opened_relative_to_an_open_folder_is_checked_against_that_folder():
    home = os.open(REAL_HOME, os.O_RDONLY)                                              # the home folder itself is not refused, only what is in it
    try:
        with pytest.raises(PermissionError, match="the tests' wall"):
            os.close(os.open(f"ananta_runs/{NONE}.log", os.O_RDONLY, dir_fd=home))
        with pytest.raises(PermissionError, match="the tests' wall"):
            os.close(os.open(f"{NONE}_dir/probe.txt", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=home))
    finally:
        os.close(home)
    assert not (REAL_HOME / f"{NONE}_dir").exists()


def test_a_relative_name_in_a_tests_own_folder_still_opens(tmp_path):
    d = os.open(tmp_path, os.O_RDONLY)
    try:
        fd = os.open("ok.txt", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=d)                # read against its own folder, not the current one
        os.write(fd, b"x")
        os.close(fd)
    finally:
        os.close(d)
    assert (tmp_path / "ok.txt").read_bytes() == b"x"


OFF = "http://127.0.0.1:9/"


@pytest.mark.parametrize("argv", [
    ["nice", "-n", "5", "curl", "-s", "--max-time", "1", OFF], ["caffeinate", "-i", "curl", "-s", "--max-time", "1", OFF],
    ["arch", "-arm64", "curl", "--max-time", "1", OFF], ["xcrun", "curl", "--max-time", "1", OFF], ["timeout", "5", "wget", "-q", OFF],
    ["env", "A=1", "nscurl", OFF], ["git", "-C", "/nonexistent-wall-probe", "fetch", "origin"], ["git", "-C", "/nonexistent-wall-probe", "push"],
    ["git", "ls-remote", OFF + "x.git"], ["ping", "-c", "1", "-t", "1", "127.0.0.1"], ["dig", "@127.0.0.1", "-p", "9", "example.invalid"],
    ["nslookup", "example.invalid", "127.0.0.1"], ["host", "-W", "1", "example.invalid", "127.0.0.1"],
    ["sh", "-c", f"nice curl -s --max-time 1 {OFF}"], ["bash", "-c", f"echo hi; echo $(curl -s --max-time 1 {OFF})"],
])
def test_a_network_program_is_refused_also_through_a_wrapper(argv):
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run(argv, capture_output=True, timeout=20)


@pytest.mark.parametrize("argv", [
    ["touch", "{d}/probe.txt"], ["cp", "/etc/hosts", "{d}/probe.txt"], ["mv", "{d}/a", "{d}/b"], ["rm", "-f", "{d}/probe.txt"],
    ["mkdir", "{d}/sub"], ["ln", "-s", "/etc/hosts", "{d}/link"], ["sqlite3", "{d}/x.sqlite", "select 1"], ["tee", "{d}/probe.txt"],
    ["dd", "if=/dev/zero", "of={d}/probe.txt", "count=1"], ["sed", "-i", "", "s/a/b/", "{c}/{n}.md"], ["chmod", "600", "{c}/{n}.md"],
    ["tar", "-xf", "/{n}.tar", "-C", "{d}"], ["unzip", "/{n}.zip", "-d", "{d}"], ["sh", "-c", "echo x > {d}/probe.txt"],
    ["sh", "-c", "echo x >> {d}/probe.txt"], ["zsh", "-c", "cd /tmp && rm -f {d}/probe.txt"],
    ["cat", "{h}/ananta_private/{n}.json"], ["head", "-c", "1", "{h}/code/ananta-decision-agent/{n}.env"],
])
def test_a_program_that_would_write_under_the_home_or_read_a_private_place_is_refused(argv):
    argv = [a.format(h=REAL_HOME, c=CHECKOUT, n=NONE, d=REAL_HOME / f"{NONE}_dir") for a in argv]
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run(argv, capture_output=True, timeout=20)
    assert not (REAL_HOME / f"{NONE}_dir").exists()


def test_the_same_programs_still_work_in_the_tests_own_folders(tmp_path):
    f = tmp_path / "a.txt"
    subprocess.run(["touch", str(f)], check=True, timeout=20)
    subprocess.run(["cp", str(CHECKOUT / "tests" / "wall.py"), str(tmp_path / "b.py")], check=True, timeout=20)   # reading code is free
    subprocess.run(["sh", "-c", f"echo x > {tmp_path}/c.txt"], check=True, timeout=20)
    assert f.exists() and (tmp_path / "b.py").exists() and (tmp_path / "c.txt").read_text() == "x\n"
    assert subprocess.run(["git", "-C", str(CHECKOUT), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True,
                          timeout=20).stdout.strip() == "true"                          # git on this machine is fine; only its network is refused


def test_the_two_ports_that_run_only_at_times_are_closed_too():
    for port in (8210, 8081):                                                           # the Telugu voice and the app's development server
        with pytest.raises(ConnectionRefusedError, match="the tests' wall"):
            socket.create_connection(("127.0.0.1", port), timeout=1)


def test_only_an_sqlite_address_that_says_read_only_is_read_only():
    assert WALL._sqlite_read_only("file:/x/y.sqlite?mode=ro") and WALL._sqlite_read_only("file:y.sqlite?immutable=1")
    assert not WALL._sqlite_read_only("/x/mode=ro.sqlite") and not WALL._sqlite_read_only("file:/x/mode=ro.sqlite")
    with pytest.raises(PermissionError, match="the tests' wall"):
        sqlite3.connect(str(CHECKOUT / f"{NONE}_dir" / "mode=ro.sqlite")).close()       # a name that only contains the words is a write
    assert not (CHECKOUT / f"{NONE}_dir").exists()


def test_a_python_that_would_skip_the_wall_is_not_started():
    for flags in (["-I"], ["-S"], ["-E"], ["-IB"], ["-B", "-s", "-S"]):
        with pytest.raises(PermissionError, match="the tests' wall"):
            subprocess.run([sys.executable, *flags, "-c", "print(1)"], capture_output=True, timeout=30)
    with pytest.raises(PermissionError, match="the tests' wall"):
        subprocess.run([sys.executable, "-c", "print(1)"], env={"PATH": "/usr/bin:/bin"}, capture_output=True, timeout=30)
    r = subprocess.run([sys.executable, "-c", "print(1)"], env={**os.environ, "X": "1"}, capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "1"                                                      # an environment that keeps the wall is fine


def test_a_fault_in_the_wall_itself_is_written_down_and_never_silent(monkeypatch):
    def broken(event, args):
        raise ValueError("a fault")

    monkeypatch.setattr(WALL, "_check", broken)
    os.listdir(CHECKOUT / "tests")                                                      # the call goes on
    assert any("its own check failed on os.listdir (ValueError)" in x for x in WALL.REFUSED)
