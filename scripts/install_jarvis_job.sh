#!/bin/zsh
# Writes (or repairs) the launchd file of Ananta's main service, ~/Library/LaunchAgents/com.ananta.jarvis.plist, from the template in
# scripts/launchd/, and checks it with plutil. It does NOT touch the running job: launchd keeps its own copy in memory.
# Usage: zsh scripts/install_jarvis_job.sh            # write the file and lint it (the running service is left alone)
#        zsh scripts/install_jarvis_job.sh --reload   # also unload and load the job (this restarts the service)
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents/com.ananta.jarvis.plist"
mkdir -p "$HOME/ananta_runs" "$HOME/Library/LaunchAgents"
TMP="$(mktemp)"
sed -e "s#__HOME__#$HOME#g" -e "s#__REPO__#$REPO#g" "$REPO/scripts/launchd/com.ananta.jarvis.plist" > "$TMP"
plutil -lint "$TMP"
cp "$TMP" "$DEST"
rm -f "$TMP"
plutil -lint "$DEST"
echo "written: $DEST (the running job was not touched)"
if [ "$1" = "--reload" ]; then
  launchctl bootout "gui/$(id -u)/com.ananta.jarvis" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$DEST"
  echo "reloaded: com.ananta.jarvis"
fi
