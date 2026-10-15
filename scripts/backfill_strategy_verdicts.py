"""Fill strategy_verdicts (jarvis/service/strategy_status.py) from the register file's git history, once (Oct 15, research audit LOSSES:
each losing trade is classed by the verdict in force when it was entered, so the history of verdict changes must exist).

    cd ~/code/ananta-agent-research && python3 ~/ananta_runs/svc_env_run.py 'exec(open("scripts/backfill_strategy_verdicts.py").read())'

Each commit that touched docs/knowledge/strategy_status.json is read oldest first; a row is added whenever a strategy's (status, verdict)
differs from the one before, stamped with that commit's time. Safe to run again (rows are keyed by strategy and time).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
from jarvis.service import core  # noqa: E402
from jarvis.service import strategy_status as S  # noqa: E402

FILE = "docs/knowledge/strategy_status.json"
j = core.from_env()
S._verdict_table(j)
log = [ln.split() for ln in subprocess.run(["git", "log", "--reverse", "--format=%H %ct", "--", FILE], capture_output=True, text=True, check=True).stdout.splitlines()
       if ln.strip()]
last, added = {}, 0
for sha, ct in log:
    raw = subprocess.run(["git", "show", f"{sha}:{FILE}"], capture_output=True, text=True).stdout
    try:
        strategies = json.loads(raw).get("strategies") or {}
    except ValueError:
        continue
    for sid, s in strategies.items():
        cur = (s.get("status"), s.get("verdict"))
        if last.get(sid) != cur:
            j.db.execute("INSERT OR IGNORE INTO strategy_verdicts (sid, t, status, verdict, source) VALUES (?,?,?,?,?)", (sid, int(ct), cur[0], cur[1], f"git:{sha[:7]}"))
            last[sid] = cur
            added += 1
j.db.commit()
print(f"{added} verdict rows from {len(log)} commits of {FILE}")
