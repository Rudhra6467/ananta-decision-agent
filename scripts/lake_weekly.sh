#!/bin/zsh
# Weekly lake update (launchd com.ananta.lake, Sundays 02:15): new daily and monthly Binance files for the chosen universe,
# rebuilt and checked, at low priority so the live system is never slowed. Log: ~/ananta_runs/lake_weekly.log
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
export PYTHONPATH="$REPO"
set -a; source "$HOME/code/ananta-decision-agent/.env"; set +a      # R2 keys for the sync (never printed)
nice -n 15 "$HOME/ananta_venvs/lake/bin/python" -u -c "
import json
from src.lake import cli, root
u = json.loads((root() / 'reports' / 'universe_v1.json').read_text())
cli.main(['all'] + u['chosen'])
cli.main(['sync'])
" >> "$HOME/ananta_runs/lake_weekly.log" 2>&1
