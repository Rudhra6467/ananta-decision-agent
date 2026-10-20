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
Paths: {agent} the agent folder (databases), {runs} ~/ananta_runs, {repo} this checkout, {worker} the worker's pulled days,
{backups} ~/ananta_backups.
"""
from __future__ import annotations

TOR = "America/Toronto"
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
     "proof": {"sql": J, "query": "SELECT :inst, COUNT(*) FROM engine_state WHERE k LIKE 'last_t:H07,M1a,%' AND CAST(v AS INTEGER) >= :inst - 86400"}},
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

    # ---------------------------------------------------------------- parts with no dated proof (listed every time)
    {"id": "outside_watchdog", "name": "Outside watchdog (every 5 minutes)", "job": "com.ananta.watchdog", "severity": "medium",
     "since": "2026-10-04", "cadence": {"every": 300},
     "proof": {"none": "watchdog.log lines carry no time, so a missed look cannot be dated"}},
    {"id": "health_loop", "name": "Health watchdog's own checks (every 2 minutes)", "job": "com.ananta.jarvis (health watchdog)",
     "severity": "medium", "since": "2026-10-04", "cadence": {"every": 120},
     "proof": {"none": "health_state keeps no time of the last check; only outages are dated (health_outages)"}},
    {"id": "jobs_steps", "name": "Each step inside the 15-minute jobs", "job": "com.ananta.jarvis (background_jobs)",
     "severity": "high", "since": "2026-10-01", "cadence": {"every": 900},
     "proof": {"none": "background_jobs() returns every step's *_error key and the loop throws the result away"}},
    {"id": "eye_loop", "name": "The eye (live prices every 10 seconds)", "job": "com.ananta.jarvis (eye)", "severity": "medium",
     "since": "2026-10-01", "cadence": {"every": 120},
     "proof": {"none": "the eye keeps its last look in memory only; its outages show under health_outages"}},
    {"id": "telugu", "name": "Telugu speech server", "job": "com.ananta.telugu", "severity": "low", "since": "2026-10-11",
     "cadence": {"every": 3600}, "proof": {"none": "it logs only when used and the health watchdog does not check it"}},
    {"id": "awake", "name": "Keep-awake", "job": "com.ananta.awake", "severity": "low", "since": "2026-10-11", "cadence": {"every": 3600},
     "proof": {"none": "no record of its own; a sleeping Mac shows as gaps in jobs_loop and explorer_scans"}},

    # ---------------------------------------------------------------- India (read-only; only the latest run has dated proof)
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
