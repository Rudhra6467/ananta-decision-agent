"""Madhav's yes (7 Nov 2026, 17:18) to the review of his 7 Nov conversation with Ananta: a sleeping Mac is one planned line, not nine faults;
the morning review's findings reach the voice; every India answer records where its time went; 'in detail' is spoken in full; the two
Asks note "I'm turning the laptop off for an hour"."""
from __future__ import annotations

import json
import time

from jarvis import selfcheck, selfknow

PM = """2026-11-07 12:07:43 -0500 Assertions          	PID 351(powerd) Created InternalPreventSleep
2026-11-07 12:08:13 -0500 Sleep               	Entering Sleep state due to 'Clamshell Sleep':TCPKeepAlive=active
2026-11-07 12:08:14 -0500 Wake Requests       	[*process=powerd request=TCPKeepAliveExpiration]
2026-11-07 12:17:42 -0500 DarkWake            	DarkWake from Deep Idle [CDNP] : due to NUB.SPMI0.SW3
2026-11-07 12:17:52 -0500 Sleep               	Entering Sleep state due to 'Maintenance Sleep':TCPKeepAlive=active
2026-11-07 15:10:35 -0500 Wake                	Wake from Deep Idle [CDNVA] : due to smc.sysState.Wake lid
2026-11-07 15:10:35 -0500 WakeDetails         	DriverReason:smc.sysState.Wake
"""


def _t(s):
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M"))


def test_the_sleep_log_gives_one_window_and_the_items_fold_into_one_planned_line(tmp_path, monkeypatch):
    now = _t("2026-11-07 16:00")
    w = selfcheck.asleep_windows(now, log_text=PM)
    assert len(w) == 1 and time.strftime("%H:%M", time.localtime(w[0][0])) == "12:08" and time.strftime("%H:%M", time.localtime(w[0][1])) == "15:10"
    items = [{"market": "crypto", "severity": "high", "source": "lost-runs check", "what": "Explorer: a scan of all 10 coins every 15 minutes did not run at 7 Nov 12:15 Toronto"},
             {"market": "crypto", "severity": "medium", "source": "lost-runs check", "what": "a part was down at 7 Nov 15:13 Toronto (the Explorer: 4 min)"},
             {"market": "crypto", "severity": "medium", "source": "lost-runs check", "what": "Outside watchdog did not run at 7 Nov 12:10 Toronto"},
             {"market": "india", "severity": "medium", "source": "lost-runs check", "what": "India evening, Zerodha part ran with an error at 6 Nov 20:00 Toronto"}]
    out = selfcheck.fold_sleep(items, w, [], now)
    asleep = [x for x in out if x["source"] == "Mac asleep"]
    assert len(out) == 2 and len(asleep) == 1 and asleep[0]["severity"] == "medium" and "nobody said this was planned" in asleep[0]["what"]
    assert "3 parts" in asleep[0]["what"] and "Explorer" in asleep[0]["what"] and "Outside watchdog" in asleep[0]["what"] and any(x["what"].startswith("India evening") for x in out)
    monkeypatch.setattr(selfcheck, "DOWNTIME", tmp_path / "downtime.json")
    selfcheck.note_downtime(1.0, "Can we turn off the laptop for 1 hour?", "Madhav", now=_t("2026-11-07 12:07"))
    out = [x for x in selfcheck.fold_sleep(items, w, selfcheck.downtime_notes(now), now) if x["source"] == "Mac asleep"]
    assert out[0]["planned"] and "planned for about 1 h (Madhav's word), it lasted 3 h 2 min" in out[0]["what"] and out[0]["severity"] == "medium", "planned, but it ran long"
    selfcheck.note_downtime(3.5, "closing the lid for a few hours", "Madhav", now=_t("2026-11-07 12:07"))
    out = [x for x in selfcheck.fold_sleep(items, w, selfcheck.downtime_notes(now), now) if x["source"] == "Mac asleep"]
    assert out[0]["severity"] == "low" and "it lasted" not in out[0]["what"]


def test_madhavs_words_about_the_laptop_are_read_and_answered():
    assert selfcheck.downtime_words("I'm turning the laptop off for an hour") == 1.0
    assert selfcheck.downtime_words("I will shut down the Mac for 45 minutes") == 0.75
    assert selfcheck.downtime_words("Can we turn off the laptop for 1 hour?") == 1.0
    assert selfcheck.downtime_words("turn off the dial") is None and selfcheck.downtime_words("how did the market close today") is None
    assert selfcheck.downtime_words("what happens if I turn off the laptop") is None
    a = selfcheck.downtime_answer(1.0, "crypto", asked=True)
    assert a.startswith("Yes, sir, go ahead") and "planned downtime" in a and "crypto paper books stop watching" in a
    assert selfcheck.downtime_answer(0.75, "india").startswith("Noted, sir: the next 45 minutes")


def test_the_india_ask_notes_the_downtime_without_writing_in_a_dry_run(tmp_path, monkeypatch):
    from jarvis.india import ask

    monkeypatch.setattr(ask, "DRY_RUN", True)
    monkeypatch.setattr(selfcheck, "DOWNTIME", tmp_path / "downtime.json")
    r = ask.downtime_flow("I'm turning the laptop off for an hour", "owner")
    assert r and "planned downtime" in r["answer"] and not (tmp_path / "downtime.json").exists()
    assert ask.downtime_flow("I'm turning the laptop off for an hour", "guest:x") is None
    assert ask.downtime_flow("how did the market close today", "owner") is None


def test_the_morning_review_reaches_the_brief_and_stays_short(tmp_path):
    (tmp_path / "2026-11-06.md").write_text("# Review\n\n## Overnight\nold\n")
    (tmp_path / "2026-11-07.md").write_text("# India review 2026-11-07\n\n## Overnight\n- all parts ran\n\n## Lost or empty runs\n- dump line 1\n\n## Never again\n- (a) guard: 0 catches\n\n"
                                            "## Evidence\n- SP1 replay 6 Nov FAIL: live -0.39% vs replay +0.07%\n\n## Waiting for Madhav\n- nothing\n\n## Fixed today\n- 4527c7d Kite fill on the Mac's clock\n")
    r = selfknow.review_page(tmp_path)
    assert r["day"] == "2026-11-07" and "Lost or empty runs" not in r["sections"]
    assert r["sections"]["Evidence"] == ["SP1 replay 6 Nov FAIL: live -0.39% vs replay +0.07%"] and r["sections"]["Fixed today"][0].startswith("4527c7d")
    assert len(json.dumps(r)) < 2500
    b = selfknow.brief("crypto")
    assert "morning_review" in b


def test_in_detail_is_recognised_and_timing_is_recorded(tmp_path, monkeypatch):
    from jarvis.india import ask

    assert ask.DETAIL_ASK.search("Explain every clock in detail: what each trial is testing")
    assert ask.DETAIL_ASK.search("go through each trial please") and not ask.DETAIL_ASK.search("How is the practice book doing?")
    monkeypatch.setattr(ask, "DATA", tmp_path)
    monkeypatch.setattr(ask, "DRY_RUN", False)
    ask._timing_log("t1", "a question", True, {"facts_ms": 300, "model_ms": 9000, "total_ms": 9400})
    rows = [json.loads(l) for l in (tmp_path / "reports" / "ask_timing.jsonl").read_text().splitlines()]
    assert rows[0]["voice"] is True and rows[0]["model_ms"] == 9000 and rows[0]["q"] == "a question"
