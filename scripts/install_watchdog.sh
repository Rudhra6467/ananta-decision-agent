#!/bin/zsh
# Install (or reinstall) the outside watchdog as a launchd job: every 5 minutes, is Jarvis answering?
# Usage: zsh scripts/install_watchdog.sh   (from the checkout Jarvis runs from)
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents/com.ananta.watchdog.plist"
mkdir -p "$HOME/ananta_runs" "$HOME/Library/LaunchAgents"
sed -e "s#__HOME__#$HOME#g" -e "s#__REPO__#$REPO#g" "$REPO/scripts/launchd/com.ananta.watchdog.plist" > "$DEST"
launchctl bootout "gui/$(id -u)/com.ananta.watchdog" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "installed: $DEST (runs $REPO/scripts/jarvis_watchdog.py every 5 minutes; log ~/ananta_runs/watchdog.log)"
