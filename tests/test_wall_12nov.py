"""12 Nov 2026, the keen outside audit (G-57: "the tests' phone-off switch is an empty variable that three helpers bypass by reading the
topic from the .env file, and test isolation is a list of nine past leaks, not a wall"). tests/conftest.py now puts up two walls before
any of Ananta's modules is imported: the home folder is an empty folder of the tests' own, and the network is closed. These checks fail
if either wall comes down."""
import os
import pwd
import socket
from pathlib import Path

import pytest

REAL_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)


def test_the_home_folder_is_the_tests_own():
    assert Path.home() != REAL_HOME and "ananta-tests-home-" in str(Path.home())
    linked = sorted(p.name for p in (Path.home() / "code").iterdir())
    assert 1 <= len(linked) <= 2 and not any("decision-agent" in n for n in linked)        # code only: this checkout and the records one
    for gone in ("ananta_data", "ananta_private", ".ananta", "code/ananta-decision-agent"):
        assert not (Path.home() / gone / ".env").exists() and not (Path.home() / gone).is_symlink()


def test_no_live_path_a_module_works_out_points_into_the_real_home():
    from jarvis import selfcheck
    from jarvis.india import ask as india_ask
    from src.india import kite_auth

    real = str(REAL_HOME.resolve()) + os.sep
    for name, p in (("the self-check's file", selfcheck.FILE), ("the crypto database", selfcheck.CRYPTO_DB), ("India's data", india_ask.DATA),
                    ("the Kite sign-in's private folder", kite_auth.PRIVATE), ("the sign-in log", kite_auth.LOG_FILE),
                    ("the sign-in attempts stamp", kite_auth.ATTEMPTS_FILE), ("the refused-reads log", selfcheck.KITE_REFUSALS)):
        assert not str(Path(p).resolve()).startswith(real), f"{name} points into Madhav's home folder: {p}"


def test_the_network_is_closed_and_the_live_services_are_out_of_reach():
    with pytest.raises(RuntimeError, match="tests never reach the network"):
        socket.create_connection(("1.1.1.1", 443), timeout=1)
    for port in (8100, 8110):                                    # the crypto and India services running on this Mac
        with pytest.raises(RuntimeError, match="tests never reach the network"):
            socket.create_connection(("127.0.0.1", port), timeout=1)


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
    env.mkdir(parents=True, exist_ok=True)                        # even with a topic in a .env file where the helpers look
    (env / ".env").write_text('ANANTA_NTFY_TOPIC="a-topic-in-the-wall"\n')
    try:
        kite_auth._ntfy("anything")
        replay._ntfy("a title", "a body")
    finally:
        (env / ".env").unlink()
        env.rmdir()
