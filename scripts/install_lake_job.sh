#!/bin/zsh
# Install (or reinstall) the weekly lake update as a launchd job. Usage: zsh scripts/install_lake_job.sh
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents/com.ananta.lake.plist"
mkdir -p "$HOME/ananta_runs" "$HOME/Library/LaunchAgents"
sed -e "s#__REPO__#$REPO#g" "$REPO/scripts/launchd/com.ananta.lake.plist" > "$DEST"
launchctl bootout "gui/$(id -u)/com.ananta.lake" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "installed: $DEST (weekly lake update, Sundays 02:15; log ~/ananta_runs/lake_weekly.log)"
