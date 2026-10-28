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
    for s in (live.get("strategies") or {}).values():
        if s.get("status_before_park"):
            s["status"] = s.pop("status_before_park")
            s.pop("parked", None)
    p = tmp_path / "strategy_status_as_tested.json"
    p.write_text(_json.dumps(live))
    monkeypatch.setattr(_ss, "_path", lambda: p)
    _ss._CACHE.update(m=None, v={})
