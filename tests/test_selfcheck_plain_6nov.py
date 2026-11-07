"""6 Nov morning review: the self-check line at the end of an answer reached Madhav with code words in it ('india evening chain
(launchd sees only the last step's exit)', '1x india_evening.err written during the run', 'the watchdog restarted it'); the nightly
replay marked it JARGON and the India exam's plain-words judge failed it."""
from jarvis import selfcheck


def test_job_name_and_detail_lose_their_code_words(monkeypatch):
    from jarvis.service import runcheck

    miss = {"name": "India evening chain (launchd sees only the last step's exit)", "kind": "errored", "t": 1793950000,
            "detail": "1x india_evening.err written during the run", "area": "india", "severity": "medium"}
    monkeypatch.setattr(runcheck, "run", lambda now=None: {"windows": {"24h": {"misses": [miss]}}})
    what = selfcheck._runs(1793950000)[0]["what"]
    assert what.startswith("India evening chain ran with an error at ")
    for bad in ("launchd", ".err", "india_evening", "("):
        assert bad not in what


def test_plain_detail_keeps_plain_words():
    assert selfcheck._plain_detail("no output since 21:30") == "no output since 21:30"
    assert selfcheck._plain_detail("see ~/ananta_runs/x.log") == ""


def test_restart_line_has_no_watchdog_word(tmp_path, monkeypatch):
    stalls = tmp_path / "ananta_runs" / "stalls"
    stalls.mkdir(parents=True)
    (stalls / "india_1.txt").write_text("stack")
    monkeypatch.setattr(selfcheck, "HOME", tmp_path)
    import time
    what = selfcheck._restarts(time.time())[0]["what"]
    assert "watchdog" not in what and "restarted automatically" in what


def test_down_line_names_the_part_in_words(monkeypatch):
    """7 Nov review: two of five 'a part was down' lines named no part (the code name had an underscore)."""
    from jarvis.service import runcheck

    misses = [{"name": "Outages the health watchdog recorded", "kind": "down", "t": 1794000000, "area": "crypto", "severity": "medium",
               "detail": d} for d in ("hands_login: 64 min (login refused (HTTP 500))", "universe_feed: 63 min (prices 5 min old)",
                                       "tunnel: 64 min (no answer (ConnectionError))")]
    monkeypatch.setattr(runcheck, "run", lambda now=None: {"windows": {"24h": {"misses": misses}}})
    whats = [x["what"] for x in selfcheck._runs(1794000000)]
    assert whats[0].endswith("(Hands sign-in: 64 min)")
    assert whats[1].endswith("(the universe feed: 63 min)")
    assert whats[2].endswith("(the public address: 64 min)")
    for w in whats:
        assert "_" not in w
