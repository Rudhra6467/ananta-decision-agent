"""21 Nov 2026 (flag 203): India's nightly answer replay started 15 Nov 23:20 was still running on 21 Nov at full processor use inside a
regular expression, so six nightly checks never ran. Now a turn stops after TURN_SECONDS and is recorded as a finding, a slow judge is a
failed check that says so, and the whole run has a processor-time cap. Each test fails on the code before (no _deadline, _judged or
_cap_the_run)."""
import re
import time

from jarvis.india import replay


def test_a_turn_stuck_in_a_regular_expression_is_stopped_and_recorded(monkeypatch):
    monkeypatch.setattr(replay, "TURN_SECONDS", 1)

    def stuck(*a, **k):
        re.sub(r"(a+)+$", "", "a" * 60 + "b")          # catastrophic backtracking: minutes or more
        return {"answer": "never"}
    monkeypatch.setattr(replay.ask, "ask", stuck)
    t0 = time.time()
    out = replay.replay_conversation([{"text": "what happened today?"}], "t1")
    assert time.time() - t0 < 10
    assert out[0]["answer"] is None and out[0]["error"].startswith("TurnTimeout") and "what happened today?" in out[0]["error"]


def test_a_judge_past_its_deadline_is_a_failed_check_that_says_so(monkeypatch):
    monkeypatch.setattr(replay, "TURN_SECONDS", 1)
    monkeypatch.setattr(replay, "judge", lambda h, t, post=None: (time.sleep(5), {"pass": True})[1])
    g = replay._judged([], {"text": "how is my book?", "answer": "fine"})
    assert g["pass"] is False and g["problems"][0]["code"] == "TIMEOUT" and "how is my book?" in g["problems"][0]["why"]


def test_a_quick_turn_is_untouched_and_the_alarm_is_cleared(monkeypatch):
    import signal

    monkeypatch.setattr(replay, "TURN_SECONDS", 1)
    monkeypatch.setattr(replay.ask, "ask", lambda *a, **k: {"answer": "ok", "kind": "answer"})
    out = replay.replay_conversation([{"text": "hi"}], "t2")
    assert out[0]["answer"] == "ok" and signal.getitimer(signal.ITIMER_REAL)[0] == 0


def test_the_run_gets_a_processor_time_cap():
    import resource

    before = resource.getrlimit(resource.RLIMIT_CPU)
    try:
        replay._cap_the_run()
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        assert soft != resource.RLIM_INFINITY and soft <= replay.RUN_CPU_SECONDS
    finally:
        resource.setrlimit(resource.RLIMIT_CPU, before)
