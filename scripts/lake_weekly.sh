#!/bin/zsh
# Weekly lake update (launchd com.ananta.lake, Sundays 02:15): new daily and monthly Binance files for the chosen universe,
# rebuilt and checked, futures context refreshed, the agent pack rebuilt, at low priority so the live system is never slowed. Log: ~/ananta_runs/lake_weekly.log
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
export PYTHONPATH="$REPO"
set -a; source "$HOME/code/ananta-decision-agent/.env"; set +a      # R2 keys for the sync (never printed)
nice -n 15 "$HOME/ananta_venvs/lake/bin/python" -u -c "
import json
from src.lake import cli, root
u = json.loads((root() / 'reports' / 'universe_v1.json').read_text())
cli.main(['all'] + u['chosen'])
from src.lake import futures as F, research as L
coins = [L.base(s) for s in u['chosen']]
for c in coins:                                   # futures context: funding for all, open interest for the 30 most traded
    try:
        F.pull_funding(c)
        if c in coins[:30]:
            F.pull_metrics(c)
    except Exception as e:
        print('futures', c, e)
cli.main(['pack'])                                # the lake -> agent hand-off (universe.json + daily.sqlite)
cli.main(['sync'])
" >> "$HOME/ananta_runs/lake_weekly.log" 2>&1
# engine plan U7.1: every other coin Ananta watches, at 15-minute to daily detail (new months only)
nice -n 15 "$HOME/ananta_venvs/lake/bin/python" -u scripts/lake_extend.py >> "$HOME/ananta_runs/lake_extend.log" 2>&1
