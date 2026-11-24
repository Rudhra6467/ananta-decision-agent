"""24 Nov 2026 (Madhav: "Both"): the worker is asked at its fixed address first; its Bonjour name is the fallback."""
import subprocess

from jarvis.service import worker


def _ssh(cmd):
    """The same command _ssh builds (conftest keeps tests from calling _ssh itself)."""
    return worker._run(lambda route: ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", *route, worker.HOST, cmd], 20)


def _fake(rcs, seen):
    def run(args, **kw):
        seen.append(args)
        return subprocess.CompletedProcess(args, rcs[len(seen) - 1], "OK · line", "")
    return run


def test_the_fixed_address_is_tried_first(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "ADDR", "192.168.2.39")
    monkeypatch.setattr(worker.subprocess, "run", _fake([0], seen))
    assert _ssh("true").returncode == 0
    assert len(seen) == 1 and "HostName=192.168.2.39" in seen[0] and seen[0][-2:] == ["ananta-worker", "true"]


def test_the_name_is_tried_when_the_address_does_not_connect(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "ADDR", "192.168.2.39")
    monkeypatch.setattr(worker.subprocess, "run", _fake([255, 0], seen))
    assert _ssh("true").returncode == 0
    assert len(seen) == 2 and not any(a.startswith("HostName=") for a in seen[1])


def test_a_command_that_ran_and_failed_is_not_retried(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "ADDR", "192.168.2.39")
    monkeypatch.setattr(worker.subprocess, "run", _fake([1, 0], seen))
    assert _ssh("~/ananta_worker/status").returncode == 1 and len(seen) == 1     # the worker answered: STALE, not unreachable


def test_no_address_means_the_name_only(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "ADDR", "")
    monkeypatch.setattr(worker.subprocess, "run", _fake([255], seen))
    assert _ssh("true").returncode == 255 and len(seen) == 1


def test_scp_uses_the_same_routes(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "ADDR", "192.168.2.39")
    monkeypatch.setattr(worker.subprocess, "run", _fake([255, 0], seen))
    r = worker._run(lambda route: ["scp", "-q", *route, "ananta-worker:~/x", "/tmp/x"], 10)
    assert r.returncode == 0 and "HostName=192.168.2.39" in seen[0] and seen[1][-2:] == ["ananta-worker:~/x", "/tmp/x"]
