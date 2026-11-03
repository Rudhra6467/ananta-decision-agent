"""3 Nov 2026 (Madhav: yes): the morning checker calls a job that runs on with no output for 12 hours stuck, not busy.
The weekly Kite candle fill waited 70 hours on itself (31 Oct-3 Nov) and the checker only said "running now"."""
import datetime as dt
import os
import plistlib
from zoneinfo import ZoneInfo

from india import morning

TOR = ZoneInfo("America/Toronto")


def _fake(agents, logs, out_at):
    lab = "com.ananta.india.kitefill"
    out, err = logs / "kitefill.log", logs / "kitefill.err"
    out.write_text("BSE windows=18\n")
    err.write_text("")
    for p in (out, err):
        os.utime(p, (out_at, out_at))
    (agents / f"{lab}.plist").write_bytes(plistlib.dumps({"Label": lab, "ProgramArguments": ["/bin/zsh", "-lc", "x"], "StandardOutPath": str(out),
                                                          "StandardErrorPath": str(err), "StartCalendarInterval": {"Weekday": 6, "Hour": 10, "Minute": 0}}))
    old = dt.datetime(2026, 10, 1, tzinfo=TOR).timestamp()
    os.utime(agents / f"{lab}.plist", (old, old))
    return lab


def test_running_with_no_output_for_12_hours_is_stuck(tmp_path):
    agents, logs = tmp_path / "a", tmp_path / "l"
    agents.mkdir()
    logs.mkdir()
    now = dt.datetime(2026, 11, 3, 7, 46, tzinfo=TOR)
    lab = _fake(agents, logs, dt.datetime(2026, 10, 31, 10, 0, tzinfo=TOR).timestamp())
    r = morning.job_report(lab, {"pid": 21251, "last_exit": 0}, agents, now, {"signin": "x", "data": tmp_path, "hol": set()})
    assert r["problems_note"] == "running now (pid 21251)"
    assert any(p.startswith("stuck: running (pid 21251) with no output for 69 h, since Sat 31 Oct 10:00") for p in r["problems"])


def test_running_and_writing_is_not_stuck(tmp_path):
    agents, logs = tmp_path / "a", tmp_path / "l"
    agents.mkdir()
    logs.mkdir()
    now = dt.datetime(2026, 11, 3, 7, 46, tzinfo=TOR)
    lab = _fake(agents, logs, dt.datetime(2026, 11, 3, 7, 40, tzinfo=TOR).timestamp())
    r = morning.job_report(lab, {"pid": 96520, "last_exit": 0}, agents, now, {"signin": "x", "data": tmp_path, "hol": set()})
    assert not [p for p in r["problems"] if p.startswith("stuck")]


def test_a_chained_steps_own_failed_line_is_an_error():
    # 3 Nov (the Map's change 8): on 2 Nov the evening's Zerodha calls failed at 05:30 IST and nobody noticed; each step now prints "<step> failed"
    assert morning._errors(["=== 2026-11-03_20:00:04 evening_zerodha", "recorder failed", "some output"]) == ["step: recorder failed"]
    assert morning._errors(["the recorder saved 449 contracts, none failed today"]) == []
