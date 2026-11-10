#!/bin/zsh
# Writes ~/Library/LaunchAgents/com.ananta.records.plist (the day's records saved to git, 06:50 Toronto) from scripts/launchd/ and loads it.
set -e
REPO="${ANANTA_LIVE_REPO:-$HOME/code/ananta-agent-research}"
SRC="$(cd "$(dirname "$0")" && pwd)/launchd/com.ananta.records.plist"
DEST="$HOME/Library/LaunchAgents/com.ananta.records.plist"
TMP="$(mktemp)"
sed -e "s#__HOME__#$HOME#g" -e "s#__REPO__#$REPO#g" "$SRC" > "$TMP"
plutil -lint "$TMP"
cp "$TMP" "$DEST"; rm -f "$TMP"
launchctl bootout "gui/$(id -u)/com.ananta.records" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "loaded: com.ananta.records (daily 06:50)"
