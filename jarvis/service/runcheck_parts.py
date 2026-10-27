"""Every part of Ananta that runs by itself, with when it should run and what proves it ran AND did its work (Oct 20 silent-failure
audit). Data only: jarvis/service/runcheck.py reads this list, read-only, and reports every run that is missing, failed or did nothing.

Why it exists: between Oct 14 22:02 and Oct 15 08:26 UTC the brain paid for 226 decisions and saved none (an 18-value INSERT met a
20-column table; process() caught the error and wrote it only into brain_queue.state). The health watchdog checks that each part is
ALIVE, the morning review greps the service log for tracebacks; neither counts WORK, so a loop that runs and does nothing looks healthy.
Every entry below therefore names a minimum amount of work, not just a heartbeat.

One entry:
  id, name        a short key and the plain name the review prints
  job             the launchd label or the loop that runs it (LOCK.md section 2), so the list can be checked against the jobs
  area            "crypto" or "india" (India is read-only and reported on its own line)
  severity        high (evidence or money lost), medium (a record goes stale), low (housekeeping)
  since / until   the first (and last) UTC date the part is expected to run
  cadence         {"every": seconds, "offset": s} | {"daily": "HH:MM", "tz": ..., "days": "0123456" (Mon=0)} |
                  {"weekly": weekday (Mon=0), "at": "HH:MM", "tz": ...}; "grace": seconds after the scheduled time before a run counts
                  as missing (default: the period for "every", 3 hours otherwise)
  proof           where the evidence is (all read-only):
                    {"sql": db, "query": ...}        rows (t, work[, error[, detail]]); named params :t0 (oldest time needed),
                                                     :now, and :inst (the scheduled run being judged; latest_only parts)
                    {"log": file, "regex": ...}      group t (a time, "time_format", "tz") or d (a date); optional work and err groups
                    {"files": template}              one file per scheduled run; {date} is the run's date in the cadence's tz,
                                                     shifted by "date_shift" days; optional min_bytes, must_contain, err_regex
                    {"sqlite_files": template, "query": ...}  a database per date (the worker's days); rows as for "sql"
                    {"reconcile": {"a": query, "b": query, "db": ...}}   per run, a (e.g. paid calls) must not exceed b (saved rows)
                    {"outages": db}                  every outage the health watchdog recorded (health_log)
                    {"mtime": file, "err_file": f}   only the latest run: the log was written, and stderr was not
                    {"none": why}                    no dated proof exists: listed every time under "cannot be checked"
  min_work        the least work a run must show (rows, coins, minutes); below it the run is "empty"
  errors_only     true: absence is fine, only error rows are misses (FAILED queue items, unreadable replies)
  zero_means      "empty" when each row is a unit of work (a decision), so no rows means the part ran and did nothing
  latest_only     true: only the latest scheduled run can be judged (the proof is a single current value)
  from_first      true: the proof began with a code change (Oct 21), so runs before its first dated record are not judged; with no
                  record yet the part is listed under "cannot be checked" with the proof's "before_first" reason
Paths: {agent} the agent folder (databases), {runs} ~/ananta_runs, {repo} this checkout, {worker} the worker's pulled days,
{backups} ~/ananta_backups.
"""
from __future__ import annotations

TOR = "America/Toronto"
IST = "Asia/Kolkata"
J = "{agent}/jarvis.sqlite"

PARTS: list[dict] = [
    # ---------------------------------------------------------------- the brain (the Oct 14-15 incident)
    {"id": "brain_saved", "name": "Brain: every paid decision call has a saved decision", "job": "com.ananta.jarvis (brain worker)",
     "severity": "high", "since": "2026-10-04", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3600},
     "proof": {"reconcile": {"db": J,
                             "a": "SELECT t, 1, cost_usd FROM ask_messages WHERE thread='brain' AND note='decision brain' "
                                  "AND COALESCE(ms, 1) != 0 AND t >= :t0",
                             "b": "SELECT t, 1 FROM brain_decisions WHERE t >= :t0"}},
     "tolerance": 0, "what": "paid calls", "against": "saved decisions",
     "note": "a retry after an unreadable reply is logged with ms=0 and is one decision, so it is not counted twice"},
    {"id": "brain_failed", "name": "Brain: decisions that raised an error", "job": "com.ananta.jarvis (brain worker)",
     "severity": "high", "since": "2026-10-04", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 0}, "errors_only": True,
     "proof": {"sql": J, "query": "SELECT t, 1, state FROM brain_queue WHERE state LIKE 'FAILED%' AND t >= :t0"}},
    {"id": "brain_stuck", "name": "Brain: wakes stuck half-decided", "job": "com.ananta.jarvis (brain worker)",
     "severity": "medium", "since": "2026-10-04", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3600}, "errors_only": True,
     "proof": {"sql": J, "query": "SELECT t, 1, 'still ' || state || ' after an hour (' || coin || ')' FROM brain_queue "
                                  "WHERE state IN ('DECIDING', 'NEW') AND t < :now - 3600 AND t >= :t0"}},
    {"id": "brain_unreadable", "name": "Brain: paid replies it could not read", "job": "com.ananta.jarvis (brain worker)",
     "severity": "medium", "since": "2026-10-04", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 0}, "errors_only": True,
     "proof": {"sql": J, "query": "SELECT t, 1, COALESCE(note, 'unreadable reply') FROM brain_decisions WHERE action='ERROR' AND t >= :t0"}},
    {"id": "brain_decides", "name": "Brain: at least one decision a day", "job": "com.ananta.jarvis (brain worker)",
     "severity": "medium", "since": "2026-10-04", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "zero_means": "empty", "proof": {"sql": J, "query": "SELECT t, 1 FROM brain_decisions WHERE action != 'ERROR' AND t >= :t0"}},
    {"id": "brain_wakes", "name": "Brain: moments reach its queue", "job": "eye, Explorer, daily watches -> brain.wake",
     "severity": "high", "since": "2026-10-04", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 10,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM brain_queue WHERE t >= :t0"}},
    {"id": "stance", "name": "Brain's daily stance written by the brain (not 'facts only')", "job": "15-minute jobs after the daily close",
     "severity": "medium", "since": "2026-10-15", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT t, CASE WHEN source='brain' THEN 1 ELSE 0 END, NULL, note FROM stance WHERE t >= :t0"}},
    {"id": "bold", "name": "Bold book's daily decision", "job": "15-minute jobs after the daily close", "severity": "low",
     "since": "2026-10-15", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM bold_decisions WHERE t >= :t0"}},

    # ---------------------------------------------------------------- the Explorer and the always-on loops
    {"id": "explorer_scans", "name": "Explorer: a scan of all 10 coins every 15 minutes", "job": "com.ananta.explorer",
     "severity": "high", "since": "2026-10-03", "cadence": {"every": 900, "grace": 600}, "min_work": 10,
     "proof": {"log": "{runs}/explorer_live.log", "time_format": "%Y-%m-%d %H:%M", "tz": "UTC",
               "regex": r"^\[(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d)\] scans=(?P<work>\d+).*errors=(?P<err>.*)$", "ok_err": "[]"}},
    {"id": "explorer_daily", "name": "Explorer: its daily page", "job": "com.ananta.explorer", "severity": "low",
     "since": "2026-10-01", "cadence": {"daily": "21:01", "tz": TOR, "grace": 2 * 3600},
     "proof": {"files": "{agent}/explorer_daily/{date}.md", "min_bytes": 200}},
    {"id": "jobs_loop", "name": "Jarvis: the 15-minute loop (value history, then the jobs)", "job": "com.ananta.jarvis",
     "severity": "high", "since": "2026-10-01", "cadence": {"every": 1800, "grace": 600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM snapshots WHERE t >= :t0"},
     "note": "checked per 30 minutes: the loop sleeps 15 minutes AFTER its work, so it drifts past some 15-minute marks"},
    {"id": "universe_5m", "name": "Universe feed: 5-minute candles for at least 300 coins", "job": "com.ananta.jarvis (feed)",
     "severity": "high", "since": "2026-10-09", "cadence": {"every": 300, "grace": 900}, "min_work": 300,
     "proof": {"sql": "{agent}/universe_bars.sqlite", "query": "SELECT t, COUNT(*) FROM m5 WHERE t >= :t0 GROUP BY t"}},
    {"id": "universe_shadow", "name": "Universe Explorer: the 5-minute shadow step makes orders every hour", "job": "com.ananta.jarvis (feed)",
     "severity": "medium", "since": "2026-10-10", "cadence": {"every": 3600, "grace": 900}, "min_work": 1,
     "proof": {"sql": "{agent}/universe_explorer.sqlite", "query": "SELECT t, 1 FROM events WHERE t >= :t0"}},
    {"id": "health_outages", "name": "Outages the health watchdog recorded",
     "job": "com.ananta.jarvis (health watchdog: explorer, eye, jobs, feed, candles, tier30, com.ananta.voice, hands, com.ananta.tunnel, "
            "disk, worker)",
     "severity": "medium", "since": "2026-10-04", "cadence": {"every": 120}, "proof": {"outages": J}},

    # ---------------------------------------------------------------- the daily close (about 00:05 UTC)
    {"id": "daily_candles", "name": "Daily candles for at least 300 universe coins", "job": "com.ananta.jarvis (feed, daily close)",
     "severity": "high", "since": "2026-10-01", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 26 * 3600}, "min_work": 300,
     "proof": {"sql": "{agent}/universe_bars.sqlite", "query": "SELECT t, COUNT(*) FROM d1 WHERE t >= :t0 GROUP BY t"}},
    {"id": "tier30_candles", "name": "30-coin tier: daily candles", "job": "15-minute jobs (tier30.run)", "severity": "medium",
     "since": "2026-10-04", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 27 * 3600}, "min_work": 28,
     "proof": {"sql": "{agent}/tier30_bars.sqlite", "query": "SELECT t, COUNT(*) FROM bars WHERE t >= :t0 GROUP BY t"},
     "note": "28 of 30: TON has had no Binance daily candle since Jun 30 (TK13); raise to 30 once replaced"},
    {"id": "lab10_rules", "name": "Daily rules evaluated on all 10 lab coins up to yesterday", "job": "15-minute jobs (watch_engine.run)",
     "severity": "high", "since": "2026-10-09", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 10,
     "latest_only": True,
     "proof": {"sql": J, "query": "SELECT :inst, COUNT(DISTINCT substr(substr(k, 8), instr(substr(k, 8), ':') + 1)) FROM engine_state "
                                    "WHERE k LIKE 'last_t:%H07,M1a,%' AND CAST(v AS INTEGER) >= :inst - 86400"},
     "note": "the key lists the lab watches in name order, so a new watch sorting before H07 (BRK, Oct 24) moves H07 off the front; one count per coin"},
    {"id": "universe_round", "name": "Universe round: rules, zones, rebuild (one rebuild record)", "job": "com.ananta.jarvis (run_daily)",
     "severity": "high", "since": "2026-10-09", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM universe_rebuilds WHERE t >= :t0"}},
    {"id": "universe_page", "name": "Universe round: its nightly page and the steps that failed", "job": "com.ananta.jarvis (run_daily)",
     "severity": "medium", "since": "2026-10-09", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600},
     "proof": {"files": "{repo}/docs/repair_shop/daily/universe_{date}.md", "min_bytes": 200,
               "err_regex": r"steps that failed tonight: (?!none\b)(?P<err>.+)"}},
    {"id": "rebuilds", "name": "Nightly re-checks: five books rebuilt and matched", "job": "com.ananta.jarvis (run_daily)",
     "severity": "high", "since": "2026-10-16", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 5,
     "proof": {"sql": J, "query": "SELECT t, 1, CASE WHEN match THEN NULL ELSE source || ' did not match its rebuild' END FROM rebuild_log WHERE t >= :t0"}},
    {"id": "explorer_compare", "name": "Side-by-side check of the two Explorers", "job": "com.ananta.jarvis (run_daily)",
     "severity": "low", "since": "2026-10-15", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM explorer_compare WHERE t >= :t0"}},
    {"id": "book500", "name": "The $500 book stepped on the latest close", "job": "com.ananta.jarvis (run_daily)", "severity": "high",
     "since": "2026-10-11", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1, "latest_only": True,
     "proof": {"sql": J, "query": "SELECT CAST(json_extract(v, '$.last_step_t') AS INTEGER), 1 FROM book500 WHERE k='state'"}},
    {"id": "missed_live", "name": "Missed-move review of the live 10 (one record per day)", "job": "15-minute jobs (missed.run)",
     "severity": "high", "since": "2026-10-03", "cadence": {"daily": "00:30", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT CAST(strftime('%s', substr(k, 8, 10)) AS INTEGER) + 86400 + 1800, 1 FROM engine_state "
                                  "WHERE k GLOB 'missed:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'"}},
    {"id": "missed_t30", "name": "Missed-move review of the 30-coin tier", "job": "15-minute jobs (missed.run_t30)",
     "severity": "medium", "since": "2026-10-04", "cadence": {"daily": "00:30", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT CAST(strftime('%s', substr(k, 12, 10)) AS INTEGER) + 86400 + 1800, 1, "
                                  "CASE WHEN v LIKE '%error%' THEN v END FROM engine_state WHERE k LIKE 'missed_t30:%'"}},
    {"id": "shadow_lane", "name": "Blind shadow lane: at least one row a day and its hash chain intact", "job": "com.ananta.jarvis (run_daily, shadow)",
     "severity": "medium", "since": "2026-10-21", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600},
     "min_work": 1,
     "proof": {"log": "{runs}/shadow/run.log", "time_format": "%Y-%m-%d %H:%M", "tz": "UTC",
               "regex": r"^\[(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d)\] daily rows=(?P<work>\d+) status=(?P<err>.*)$", "ok_err": "ok"},
     "note": "OD-SHADOW-LANE: status is ok only when verify() found the chain intact and no rule failed; the lane shows counts only"},
    {"id": "chronos_shadow", "name": "Chronos shadow (Hugging Face forecaster, blind): BTC and ETH forecast each day, chain intact",
     "job": "com.ananta.chronosshadow", "severity": "low", "since": "2026-10-26", "cadence": {"daily": "04:20", "tz": TOR, "grace": 3 * 3600,
                                                                                                    "early": 8 * 3600},
     "min_work": 1,
     "proof": {"log": "{runs}/shadow_chronos/run.log", "time_format": "%Y-%m-%d %H:%M", "tz": "UTC",
               "regex": r"^\[(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d)\] daily rows=(?P<work>\d+) status=(?P<err>.*)$", "ok_err": "ok"},
     "note": "Madhav 25 Oct ('add both'): a blind forward record only; counts here, no outcome until PW-HF-CHRONOS after 14 Dec. "
             "early (27 Oct): the UTC day closes at 20:00 Toronto, so a run from 20:20 the evening before (a catch-up by hand) "
             "does that day's work; the 04:20 run then finds it already written"},
    {"id": "polymarket_shadow", "name": "Polymarket shadow (crowd vs Ananta on crypto price questions, read-only): questions recorded each day, chain intact",
     "job": "com.ananta.polymarketshadow", "severity": "low", "since": "2026-10-27", "cadence": {"daily": "04:45", "tz": TOR, "grace": 3 * 3600},
     "min_work": 1,
     "proof": {"log": "{runs}/shadow_polymarket/run.log", "time_format": "%Y-%m-%d %H:%M", "tz": "UTC",
               "regex": r"^\[(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d)\] daily rows=(?P<work>\d+) status=(?P<err>.*)$", "ok_err": "ok"},
     "note": "Madhav 27 Oct 00:05 ('yes'): record-only shadow, not evidence until 30+ settled; counts here, no score until 15 Dec"},
    {"id": "hfnews_shadow", "name": "News-model shadow (Hugging Face FinBERT, blind): the stored news-check headlines rated each day",
     "job": "com.ananta.hfnews.shadow", "severity": "low", "since": "2026-10-26", "cadence": {"daily": "05:10", "tz": TOR, "grace": 3 * 3600},
     "min_work": 1,
     "proof": {"log": "{runs}/shadow_hfnews/run.log", "time_format": "%Y-%m-%d %H:%M", "tz": "UTC",
               "regex": r"^\[(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d)\] daily rows=(?P<work>\d+) status=(?P<err>.*)$", "ok_err": "ok"},
     "note": "Madhav 25 Oct ('add both'): a blind forward record only; rows = the coin-days of stored headlines it found to rate (0 means the news check stored nothing new); no outcome until PW-HF-NEWS after 14 Dec"},
    {"id": "evening_review", "name": "Evening review", "job": "15-minute jobs (reviews.evening)", "severity": "low",
     "since": "2026-10-05", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM daily_reviews WHERE t >= :t0"}},
    {"id": "officer_note", "name": "Officer's note", "job": "com.ananta.jarvis (run_daily)", "severity": "low", "since": "2026-10-14",
     "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM officer_notes WHERE t >= :t0"}},
    {"id": "news_credit", "name": "News check and credit record for the 10 coins", "job": "15-minute jobs", "severity": "low",
     "since": "2026-10-03", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 20,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM news_log WHERE t >= :t0 UNION ALL SELECT t, 1 FROM credit_records WHERE t >= :t0"}},
    {"id": "briefs", "name": "Morning and evening briefs", "job": "15-minute jobs", "severity": "low", "since": "2026-10-01",
     "cadence": {"daily": "00:00", "tz": "UTC", "grace": 14 * 3600}, "min_work": 2,
     "proof": {"sql": J, "query": "SELECT t, 1 FROM briefings WHERE t >= :t0"}},
    {"id": "lesson_count", "name": "Lessons counted when they mature (weekly tickets filed by themselves)", "job": "com.ananta.jarvis (run_daily, lessons)",
     "severity": "low", "since": "2026-10-22", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 3 * 3600}, "min_work": 1,
     "proof": {"sql": J, "query": "SELECT CAST(json_extract(v, '$.t') AS INTEGER), 1 FROM engine_state WHERE k GLOB 'learning:count:[0-9]*'"},
     "note": "learning.count_lessons (Oct 21): one record a night, even when nothing matured"},
    {"id": "weekly_review", "name": "Weekly situation review (Sundays)", "job": "com.ananta.jarvis (run_daily, Sundays)",
     "severity": "low", "since": "2026-10-18", "cadence": {"weekly": 6, "at": "00:00", "tz": "UTC", "grace": 3 * 3600},
     "proof": {"files": "{repo}/docs/repair_shop/weekly/{date}.md", "min_bytes": 200}},

    # ---------------------------------------------------------------- nightly jobs, the worker and the reviews
    {"id": "backup", "name": "Database backups", "job": "com.ananta.backup", "severity": "high", "since": "2026-10-11",
     "cadence": {"daily": "03:40", "tz": TOR, "grace": 2 * 3600},
     "proof": {"files": "{backups}/{date}/jarvis.sqlite", "min_bytes": 1_000_000}},
    {"id": "backup_r2", "name": "Sunday backup copy to R2", "job": "com.ananta.backup", "severity": "medium", "since": "2026-10-11",
     "cadence": {"weekly": 6, "at": "03:40", "tz": TOR, "grace": 2 * 3600},
     "min_work": 1, "proof": {"log": "{runs}/backup.log", "regex": r"'folder': '[^']*/(?P<d>\d{4}-\d\d-\d\d)'.*'r2': 'backups/"}},
    {"id": "mongo_archive", "name": "Old app's database archive", "job": "com.ananta.mongoarchive", "severity": "low",
     "since": "2026-10-03", "cadence": {"daily": "03:20", "tz": TOR, "grace": 2 * 3600}, "min_work": 1,
     "proof": {"log": "{runs}/mongo_archive/archive.log", "time_format": "%Y-%m-%d %H:%M", "tz": TOR,
               "regex": r"^\[(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d)\] ananta data size"}},
    {"id": "worker_minutes", "name": "Worker Mac: NDAX quotes every minute (at least 1,380 minutes a day)", "job": "worker Mac recorder",
     "severity": "high", "since": "2026-10-12", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 34 * 3600}, "min_work": 1380,
     "proof": {"sqlite_files": "{worker}/l1_{date}.sqlite", "query": "SELECT (t / 60) * 60, 1 FROM ndax GROUP BY t / 60"},
     "note": "a day arrives with the next night's backup pull, so it is judged about 34 hours after it starts"},
    {"id": "public_site", "name": "Public page answered (seen from the worker, at least 1,380 minutes a day)", "job": "com.ananta.website + com.ananta.tunnel",
     "severity": "medium", "since": "2026-10-12", "cadence": {"daily": "00:00", "tz": "UTC", "grace": 34 * 3600}, "min_work": 1380,
     "proof": {"sqlite_files": "{worker}/l1_{date}.sqlite", "query": "SELECT t, 1 FROM site WHERE ok = 1"}},
    {"id": "morning_review", "name": "Morning review page", "job": "scheduled task 07:25 Toronto", "severity": "medium",
     "since": "2026-10-10", "cadence": {"daily": "07:25", "tz": TOR, "grace": 3 * 3600},
     "proof": {"files": "{repo}/docs/repair_shop/daily/{date}.md", "must_contain": "## Overnight"}},
    {"id": "lake", "name": "Research lake extended (Sundays)", "job": "com.ananta.lake", "severity": "low", "since": "2026-10-04",
     "cadence": {"weekly": 6, "at": "02:15", "tz": TOR, "grace": 6 * 3600}, "latest_only": True,
     "proof": {"mtime": "{runs}/lake_weekly.log"}},
    {"id": "exam_weekly", "name": "Agent exam (Sundays 07:10)", "job": "com.ananta.exam", "severity": "medium", "since": "2026-10-25",
     "cadence": {"weekly": 6, "at": "07:10", "tz": TOR, "grace": 6 * 3600}, "latest_only": True,
     "proof": {"mtime": "{runs}/exam_weekly.log"},
     "note": "OD-EXAM-CADENCE (a), Madhav Oct 20; the gate's exam checks read the run itself (a pass counts for 8 days)"},
    {"id": "others_daily", "name": "Other traders: yesterday's trades rebuilt and sorted (04:30)", "job": "com.ananta.othersdaily",
     "severity": "low", "since": "2026-10-21", "cadence": {"daily": "04:30", "tz": TOR, "grace": 3 * 3600}, "latest_only": True,
     "proof": {"mtime": "{runs}/others_daily.log"},
     "note": "OD-HL-FILLS (a), Madhav Oct 20; it has little to sort until the worker's capture runs"},

    # ---------------------------------------------------------------- dated from Oct 21 (live-code reliability fixes)
    # from_first: the proof starts with that code change, so each is judged from its first dated record; before it exists the part
    # is listed under "cannot be checked" with before_first as the reason.
    {"id": "outside_watchdog", "name": "Outside watchdog (a look at least every 10 minutes; it runs every 5)", "job": "com.ananta.watchdog",
     "severity": "medium", "since": "2026-10-04", "cadence": {"every": 600, "grace": 600}, "min_work": 1, "from_first": True,
     "proof": {"log": "{runs}/watchdog.log", "time_format": "%Y-%m-%d %H:%M", "tz": "UTC",
               "regex": r"^\[(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d):\d\d UTC\] \{",
               "before_first": "watchdog.log has no dated line yet (scripts/jarvis_watchdog.py dates its lines from Oct 21)"},
     "note": "per 10 minutes: launchd's 5-minute interval does not line up with the checker's slots"},
    {"id": "health_loop", "name": "Health watchdog's own checks (the last round under 10 minutes old)", "job": "com.ananta.jarvis (health watchdog)",
     "severity": "medium", "since": "2026-10-04", "cadence": {"every": 600, "grace": 300}, "min_work": 1, "latest_only": True,
     "from_first": True,
     "proof": {"sql": J, "query": "SELECT last_push, 1 FROM health_state WHERE part='_last_check' AND last_push IS NOT NULL",
               "before_first": "health_state has no _last_check row yet (health.watch records it from Oct 21)"}},
    {"id": "jobs_steps", "name": "Each step inside the 15-minute jobs (its *_error keys)", "job": "com.ananta.jarvis (background_jobs)",
     "severity": "high", "since": "2026-10-01", "cadence": {"every": 900, "grace": 600}, "errors_only": True, "from_first": True,
     "proof": {"log": "{runs}/jobs_steps.jsonl", "time_format": "%Y-%m-%d %H:%M", "tz": "UTC",
               "regex": r'^\{"t": "(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d):\d\d", "n": \d+, "errors": (?P<err>\{.*\})\}$', "ok_err": "{}",
               "before_first": "jobs_steps.jsonl not written yet (the 15-minute loop records every *_error from Oct 21)"},
     "note": "reliability.record_job_errors: one line per run; a run with no line at all shows under jobs_loop"},

    # ---------------------------------------------------------------- parts with no dated proof (listed every time)
    {"id": "eye_loop", "name": "The eye (live prices every 10 seconds)", "job": "com.ananta.jarvis (eye)", "severity": "medium",
     "since": "2026-10-01", "cadence": {"every": 120},
     "proof": {"none": "the eye keeps its last look in memory only; its outages show under health_outages"}},
    {"id": "telugu", "name": "Telugu speech server", "job": "com.ananta.telugu", "severity": "low", "since": "2026-10-11",
     "cadence": {"every": 3600}, "proof": {"none": "it logs only when used and the health watchdog does not check it"}},
    {"id": "hands", "name": "Hands (the paper order service), kept alive by launchd", "job": "com.ananta.hands", "severity": "high",
     "since": "2026-10-20", "cadence": {"every": 3600},
     "proof": {"none": "a server with no dated record of its own; the health watchdog checks it every 2 minutes and its outages show under health_outages (#71)"}},
    {"id": "worker_hl", "name": "Worker Mac: other traders' fills, every finished UTC day (hourly)", "job": "com.ananta.worker.hlcapture",
     "severity": "low", "since": "2026-10-20", "cadence": {"every": 3600},
     "proof": {"none": "installs itself when the worker Mac is back online (#72); its day files are not pulled to the main Mac yet"}},
    {"id": "awake", "name": "Keep-awake", "job": "com.ananta.awake", "severity": "low", "since": "2026-10-11", "cadence": {"every": 3600},
     "proof": {"none": "no record of its own; a sleeping Mac shows as gaps in jobs_loop and explorer_scans"}},

    {"id": "worker_pull_retry", "name": "Worker pull retry (hourly 04:20-09:20 Toronto until the day lands)", "job": "com.ananta.workerpull",
     "severity": "low", "since": "2026-10-24", "from_first": True, "cadence": {"daily": "04:20", "tz": TOR, "grace": 6 * 3600}, "min_work": 1,
     "proof": {"log": "{runs}/workerpull.log", "regex": r"^(?P<t>\d{4}-\d\d-\d\d \d\d:\d\d) retry pull (?P<err>.*\"error\": \"[^n][^\"]*\")?",
               "tz": TOR, "before_first": "first retry runs the night of Oct 23-24"}},

    # ---------------------------------------------------------------- India (read-only): session proofs (Oct 23, plan "to the review point")
    # Each is a dated file or row the India jobs write for a session; cadence "holidays": True skips NSE holidays (the lake's own list).
    {"id": "india_sp1_session", "name": "India SP1 index line: the session's decisions recorded (09:15-10:15 IST)", "job": "com.ananta.india.sp1paper",
     "area": "india", "severity": "high", "since": "2026-10-21",
     "cadence": {"daily": "09:15", "tz": IST, "days": "01234", "holidays": True, "grace": 3 * 3600}, "min_work": 1,
     "proof": {"log": "{india}/paper/sp1/decisions.jsonl",
               "regex": r'"kind": "(?P<k>[a-z_]+)", "date": "(?P<d>\d{4}-\d\d-\d\d)"(?:, "at": "[^"]*", "error": "(?P<err>[^"]{0,140}))?',
               "tz": IST}},
    {"id": "india_ledger", "name": "India ledger snapshot (gate counter D16; 12:30 Toronto, session days)", "job": "com.ananta.india.recorder_noon",
     "area": "india", "severity": "high", "since": "2026-10-21",
     "cadence": {"daily": "12:30", "tz": TOR, "days": "01234", "holidays": True, "grace": 3 * 3600},
     "proof": {"files": "{india}/bronze/ledger/{date}.json", "min_bytes": 1000}},
    {"id": "india_decisions", "name": "India stock paper book: the session's decision journal", "job": "com.ananta.india.paper", "area": "india",
     "severity": "high", "since": "2026-10-21", "cadence": {"daily": "22:30", "tz": TOR, "days": "01234", "holidays": True, "grace": 3 * 3600},
     "proof": {"files": "{india}/paper/decisions/{date}.json", "min_bytes": 500}},
    {"id": "india_readmodel", "name": "India read model built with no missing section (what the app, Ask and voice read)", "job": "com.ananta.india.paper",
     "area": "india", "severity": "medium", "since": "2026-10-21",
     "cadence": {"daily": "22:30", "tz": TOR, "days": "01234", "holidays": True, "grace": 3 * 3600},
     "proof": {"files": "{india}/readmodel/{date}.json", "min_bytes": 2000, "must_contain": '"missing": []'}},
    {"id": "india_call", "name": "India daily call written (K02)", "job": "com.ananta.india.paper", "area": "india", "severity": "medium",
     "since": "2026-10-19", "cadence": {"daily": "22:30", "tz": TOR, "days": "01234", "holidays": True, "grace": 3 * 3600}, "min_work": 1,
     "proof": {"log": "{india}/paper/calls.jsonl", "regex": r'"kind": "call", .*?"data_through": "(?P<d>\d{4}-\d\d-\d\d)"', "tz": TOR}},
    {"id": "india_league", "name": "India reference-traders league page", "job": "com.ananta.india.paper", "area": "india", "severity": "medium",
     "since": "2026-10-19", "cadence": {"daily": "22:30", "tz": TOR, "days": "01234", "holidays": True, "grace": 3 * 3600},
     "proof": {"files": "{india}/manifests/others_{date}.json", "min_bytes": 500, "must_contain": '"status": "ok"'}},
    {"id": "india_missed", "name": "India missed-movers review", "job": "com.ananta.india.paper", "area": "india", "severity": "medium",
     "since": "2026-10-19", "cadence": {"daily": "22:30", "tz": TOR, "days": "01234", "holidays": True, "grace": 3 * 3600},
     "proof": {"files": "{india}/manifests/missed_{date}.json", "min_bytes": 500, "must_contain": '"status": "ok"'}},
    {"id": "india_recorder", "name": "India option recorder: minutes saved for the session (noon and evening fetches)", "job": "com.ananta.india.recorder_noon",
     "area": "india", "severity": "medium", "since": "2026-10-19",
     "cadence": {"daily": "12:30", "tz": TOR, "days": "01234", "holidays": True, "grace": 10 * 3600}, "min_work": 1_000_000,
     "proof": {"log": "{india}/manifests/kite_1m_fo.jsonl",
               "regex": r'"fetched_at": "(?P<t>\d{4}-\d\d-\d\dT\d\d:\d\d)[^\n]*?"n": (?P<work>\d+), "status": "(?P<err>\w+)"',
               "time_format": "%Y-%m-%dT%H:%M", "tz": "UTC", "ok_err": "ok"}},
    {"id": "india_report", "name": "India evening portfolio report", "job": "com.ananta.india.evening", "area": "india", "severity": "low",
     "since": "2026-10-19", "cadence": {"daily": "19:00", "tz": TOR, "days": "01234", "holidays": True, "grace": 3 * 3600},
     "proof": {"files": "{india}/reports/portfolio_{date}.md", "min_bytes": 200}},
    {"id": "india_autologin", "name": "India Kite auto sign-in (21:40 and 21:52 Toronto, Sun-Thu)", "job": "com.ananta.india.autologin",
     "area": "india", "severity": "high", "since": "2026-10-23", "from_first": True,
     "cadence": {"daily": "21:40", "tz": TOR, "days": "01236", "grace": 3600}, "min_work": 1,
     "proof": {"log": "{runs}/kite_autologin.log", "regex": r"^(?P<t>\d{4}-\d\d-\d\dT\d\d:\d\d)[^ ]* auto sign-in (?P<err>FAILED.{0,120})?",
               "time_format": "%Y-%m-%dT%H:%M", "tz": "UTC", "before_first": "no dated sign-in record yet; the first run writes it"}},

    # ---------------------------------------------------------------- India (read-only; each job's latest run)
    {"id": "india_nightly", "name": "India nightly", "job": "com.ananta.india.nightly", "area": "india", "severity": "medium",
     "since": "2026-10-18", "cadence": {"daily": "02:30", "tz": TOR, "grace": 2 * 3600}, "latest_only": True,
     "proof": {"mtime": "{runs}/india_nightly.log", "err_file": "{runs}/india_nightly.err"}},
    {"id": "india_evening", "name": "India evening chain (17 steps; launchd sees only the last one's exit)", "job": "com.ananta.india.evening",
     "area": "india", "severity": "medium", "since": "2026-10-19", "cadence": {"daily": "19:00", "tz": TOR, "grace": 2 * 3600},
     "latest_only": True, "proof": {"mtime": "{runs}/india_evening.log", "err_file": "{runs}/india_evening.err"}},
    {"id": "india_recorder_noon", "name": "India noon recorder (weekdays)", "job": "com.ananta.india.recorder_noon", "area": "india",
     "severity": "medium", "since": "2026-10-19", "cadence": {"daily": "12:30", "tz": TOR, "days": "01234", "grace": 2 * 3600},
     "latest_only": True, "proof": {"mtime": "{runs}/india_recorder_noon.log", "err_file": "{runs}/india_recorder_noon.err"}},
    {"id": "india_paper", "name": "India stock paper book", "job": "com.ananta.india.paper", "area": "india", "severity": "medium",
     "since": "2026-10-18", "cadence": {"daily": "22:30", "tz": TOR, "grace": 2 * 3600}, "latest_only": True,
     "proof": {"mtime": "{runs}/india_paper.log", "err_file": "{runs}/india_paper.err"}},
    {"id": "india_spreads", "name": "India spread sample (Sun-Thu)", "job": "com.ananta.india.spreads", "area": "india",
     "severity": "low", "since": "2026-10-19", "cadence": {"daily": "22:35", "tz": TOR, "days": "01236", "grace": 2 * 3600},
     "latest_only": True, "proof": {"mtime": "{runs}/india_spreads.log", "err_file": "{runs}/india_spreads.err"}},
    {"id": "india_sp1paper", "name": "India SP1 index paper", "job": "com.ananta.india.sp1paper", "area": "india", "severity": "low",
     "since": "2026-10-19", "cadence": {"daily": "22:00", "tz": TOR, "grace": 2 * 3600}, "latest_only": True,
     "proof": {"mtime": "{runs}/sp1paper/run.log", "err_file": "{runs}/sp1paper/run.err"}},
    {"id": "india_sp1score", "name": "India SP1 score", "job": "com.ananta.india.sp1paper.score", "area": "india", "severity": "low",
     "since": "2026-10-20", "cadence": {"daily": "07:00", "tz": TOR, "grace": 2 * 3600}, "latest_only": True,
     "proof": {"mtime": "{runs}/sp1paper/score.log", "err_file": "{runs}/sp1paper/score.err"}},
]
