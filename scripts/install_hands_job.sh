#!/bin/zsh
# Writes the launchd file of Hands (the App backend, port 8001), ~/Library/LaunchAgents/com.ananta.hands.plist, from scripts/launchd/, and
# checks it with plutil (repair request #71, approved by Madhav 2026-10-20).
# Usage: zsh scripts/install_hands_job.sh            # write and lint only
#        zsh scripts/install_hands_job.sh --swap     # also stop a hand-started Hands on port 8001 and start the launchd job, then check /health
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents/com.ananta.hands.plist"
mkdir -p "$HOME/ananta_runs" "$HOME/Library/LaunchAgents"
TMP="$(mktemp)"
sed -e "s#__HOME__#$HOME#g" "$REPO/scripts/launchd/com.ananta.hands.plist" > "$TMP"
plutil -lint "$TMP"
cp "$TMP" "$DEST"
rm -f "$TMP"
plutil -lint "$DEST"
echo "written: $DEST"
if [ "$1" = "--swap" ]; then
  OLD="$(lsof -nP -t -iTCP:8001 -sTCP:LISTEN 2>/dev/null | head -1)"
  launchctl bootout "gui/$(id -u)/com.ananta.hands" 2>/dev/null || true
  if [ -n "$OLD" ]; then kill "$OLD"; for i in $(seq 1 20); do lsof -nP -iTCP:8001 -sTCP:LISTEN >/dev/null 2>&1 || break; sleep 0.5; done; fi
  launchctl bootstrap "gui/$(id -u)" "$DEST"
  for i in $(seq 1 40); do curl -fsS -m 2 http://127.0.0.1:8001/health >/dev/null 2>&1 && { echo "hands healthy under launchd after ${i}x0.5s"; exit 0; }; sleep 0.5; done
  echo "HANDS DID NOT COME UP under launchd: starting it by hand again" >&2
  launchctl bootout "gui/$(id -u)/com.ananta.hands" 2>/dev/null || true
  cd "$HOME/code/Ananta/backend" && nohup .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8001 --workers 1 >> hands.log 2>&1 &
  exit 1
fi
