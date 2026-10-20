#!/bin/zsh
# Writes ~/Library/LaunchAgents/com.ananta.exam.plist (the weekly agent exam, Sundays 07:10) from scripts/launchd/ and loads it.
set -e
REPO="${ANANTA_LIVE_REPO:-$HOME/code/ananta-agent-research}"
SRC="$(cd "$(dirname "$0")" && pwd)/launchd/com.ananta.exam.plist"
DEST="$HOME/Library/LaunchAgents/com.ananta.exam.plist"
TMP="$(mktemp)"
sed -e "s#__HOME__#$HOME#g" -e "s#__REPO__#$REPO#g" "$SRC" > "$TMP"
plutil -lint "$TMP"
cp "$TMP" "$DEST"; rm -f "$TMP"
launchctl bootout "gui/$(id -u)/com.ananta.exam" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "loaded: com.ananta.exam (Sundays 07:10)"
