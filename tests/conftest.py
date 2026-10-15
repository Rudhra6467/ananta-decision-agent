"""Tests never push to a real phone, even when run on the laptop where .env holds the ntfy topic; and they never reach the web
or touch the live paid-search counters."""
import os

import pytest

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
