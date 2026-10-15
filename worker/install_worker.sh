#!/bin/bash
# Install or update the Ananta worker on the second Mac, from the main Mac, over SSH. Safe to run again (it updates in place).
#   bash ~/code/ananta-agent-research/worker/install_worker.sh
# Needs the "ananta-worker" SSH alias with key login (worker/README.md, step 2).
set -euo pipefail
H="${ANANTA_WORKER_HOST:-ananta-worker}"
HERE="$(cd "$(dirname "$0")" && pwd)"
LABEL=com.ananta.worker.collector

echo "1/5 Connecting to $H ..."
if ! ssh -o BatchMode=yes "$H" true 2>/dev/null; then
  echo "    Key login to $H does not work yet. Do worker/README.md step 2, then run this again."
  exit 1
fi

echo "2/5 Finding Python 3.8 or newer on the worker ..."
PY=$(ssh "$H" 'for p in /Library/Developer/CommandLineTools/usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
  if [ -x "$p" ] && "$p" -c "import sys, sqlite3, ssl; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then echo "$p"; exit 0; fi
done; exit 1') || { echo "    No Python 3.8+ there. On the old Mac open Terminal, type: xcode-select --install   click Install, wait, then run this again."; exit 1; }
RHOME=$(ssh "$H" 'echo $HOME')
echo "    $PY"

echo "3/5 Copying the collector and its launchd job ..."
ssh "$H" 'mkdir -p ~/ananta_worker/data ~/ananta_worker/logs ~/Library/LaunchAgents'
scp -q "$HERE/collector.py" "$H:ananta_worker/collector.py"
TMP=$(mktemp)
sed -e "s#__PY__#$PY#g" -e "s#__HOME__#$RHOME#g" "$HERE/$LABEL.plist" > "$TMP"
scp -q "$TMP" "$H:Library/LaunchAgents/$LABEL.plist"
rm -f "$TMP"
printf '#!/bin/sh\nexec %s "$HOME/ananta_worker/collector.py" status\n' "$PY" | ssh "$H" 'cat > ~/ananta_worker/status && chmod +x ~/ananta_worker/status'
printf '#!/bin/sh\nexec %s "$HOME/ananta_worker/collector.py" alert-test\n' "$PY" | ssh "$H" 'cat > ~/ananta_worker/alert-test && chmod +x ~/ananta_worker/alert-test'

echo "4/5 One test round ..."
ssh "$H" "$PY ~/ananta_worker/collector.py once >/dev/null && ~/ananta_worker/status" || { echo "    The test round failed; see ~/ananta_worker/logs/collector.log on the worker."; exit 1; }

echo "5/5 Starting it under launchd (it restarts if it stops, and at every login) ..."
ssh "$H" "launchctl bootout gui/\$(id -u)/$LABEL 2>/dev/null; sleep 2; launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/$LABEL.plist" \
  || echo "    Not started now (is someone logged in on the worker's screen?). It starts at the next login."
sleep 5
ssh "$H" "launchctl print gui/\$(id -u)/$LABEL 2>/dev/null | grep -E '^\s*(state|pid) =' || true"
echo
echo "Done. The one-line check from this Mac, any time:"
echo "    ssh $H '~/ananta_worker/status'"
