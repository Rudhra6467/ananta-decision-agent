"""9 Nov 2026 morning review: the brain's daily counts were judged 3 hours into the UTC day they count (a false 'empty' each morning)."""
from datetime import datetime, timezone

from jarvis.service import runcheck
from jarvis.service.runcheck_parts import PARTS


def _part(pid):
    return next(p for p in PARTS if p["id"] == pid)


def test_daily_counts_wait_for_their_day_to_close():
    for pid in ("brain_decides", "brain_wakes"):
        assert runcheck.grace(_part(pid)["cadence"]) >= 24 * 3600 + 3 * 3600


def test_an_open_utc_day_is_not_judged(tmp_path):
    import sqlite3
    db = tmp_path / "j.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE brain_decisions (t INTEGER, action TEXT, note TEXT)")
    con.commit(); con.close()
    part = {**_part("brain_decides"), "since": "2026-11-01", "proof": {**_part("brain_decides")["proof"], "sql": str(db)}}
    now = int(datetime(2026, 11, 9, 12, 30, tzinfo=timezone.utc).timestamp())
    res = runcheck.judge(part, {}, now, 24 * 3600)
    assert not any(runcheck._utc_day(m["t"]) == "Nov 9" for m in res["misses"])
