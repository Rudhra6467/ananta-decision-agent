#!/bin/bash
# Install or update the Ananta worker on the second Mac, from the main Mac, over SSH. Safe to run again (it updates in place).
#   bash ~/code/ananta-agent-research/worker/install_worker.sh
# Needs the "ananta-worker" SSH alias with key login (worker/README.md, step 2).
# Two jobs: the collector (every minute: NDAX, Binance, USD/CAD, the public page) and, since Oct 20, the capture of other traders'
# fills (every hour, data only: decision OD-HL-FILLS (a)). The capture's account list is the fixed sample of review #2; it is built
# once on this Mac from ~/ananta_runs/hl_bench/hl_bench.sqlite into ~/ananta_runs/hl_daily/hl_accounts.json and never rebuilt.
set -euo pipefail
H="${ANANTA_WORKER_HOST:-ananta-worker}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
LABEL=com.ananta.worker.collector
HL_LABEL=com.ananta.worker.hlcapture
HL_ACCOUNTS="${ANANTA_HL_ACCOUNTS:-$HOME/ananta_runs/hl_daily/hl_accounts.json}"
HL_BENCH="$HOME/ananta_runs/hl_bench/hl_bench.sqlite"

echo "1/7 Connecting to $H ..."
if ! ssh -o BatchMode=yes "$H" true 2>/dev/null; then
  echo "    Key login to $H does not work yet. Do worker/README.md step 2, then run this again."
  exit 1
fi

echo "2/7 Finding Python 3.8 or newer on the worker ..."
PY=$(ssh "$H" 'for p in /Library/Developer/CommandLineTools/usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
  if [ -x "$p" ] && "$p" -c "import sys, sqlite3, ssl; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then echo "$p"; exit 0; fi
done; exit 1') || { echo "    No Python 3.8+ there. On the old Mac open Terminal, type: xcode-select --install   click Install, wait, then run this again."; exit 1; }
RHOME=$(ssh "$H" 'echo $HOME')
echo "    $PY"

echo "3/7 The other-traders account list (fixed, review #2's sample) ..."
HL_OK=1
if [ ! -s "$HL_ACCOUNTS" ]; then
  if [ -s "$HL_BENCH" ]; then
    PYM="$HOME/ananta_venvs/jarvis/bin/python"; [ -x "$PYM" ] || PYM=python3
    mkdir -p "$(dirname "$HL_ACCOUNTS")"
    (cd "$REPO" && "$PYM" -m src.research.others_daily accounts --hl "$HL_BENCH" --file "$HL_ACCOUNTS") \
      || { echo "    Could not build the account list; the fills capture is skipped this time."; HL_OK=0; }
  else
    echo "    $HL_BENCH is not on this Mac, so there is no account list; the fills capture is skipped this time."; HL_OK=0
  fi
else
  echo "    $HL_ACCOUNTS (kept as it is)"
fi

echo "4/7 Copying the collector, the fills capture and their launchd jobs ..."
ssh "$H" 'mkdir -p ~/ananta_worker/data ~/ananta_worker/logs ~/Library/LaunchAgents'
scp -q "$HERE/collector.py" "$H:ananta_worker/collector.py"
scp -q "$HERE/hl_capture.py" "$H:ananta_worker/hl_capture.py"
[ "$HL_OK" = 1 ] && scp -q "$HL_ACCOUNTS" "$H:ananta_worker/hl_accounts.json"
for L in "$LABEL" "$HL_LABEL"; do
  TMP=$(mktemp)
  sed -e "s#__PY__#$PY#g" -e "s#__HOME__#$RHOME#g" "$HERE/$L.plist" > "$TMP"
  scp -q "$TMP" "$H:Library/LaunchAgents/$L.plist"
  rm -f "$TMP"
done
# the one-line check: the collector's line (its exit code is the worker's health, as before) and the fills capture's line
printf '#!/bin/sh\n%s "$HOME/ananta_worker/collector.py" status; rc=$?\n[ -f "$HOME/ananta_worker/hl_capture.py" ] && [ -f "$HOME/ananta_worker/hl_accounts.json" ] && %s "$HOME/ananta_worker/hl_capture.py" status\nexit $rc\n' "$PY" "$PY" \
  | ssh "$H" 'cat > ~/ananta_worker/status && chmod +x ~/ananta_worker/status'
printf '#!/bin/sh\nexec %s "$HOME/ananta_worker/collector.py" alert-test\n' "$PY" | ssh "$H" 'cat > ~/ananta_worker/alert-test && chmod +x ~/ananta_worker/alert-test'

echo "5/7 One test round of the collector ..."
ssh "$H" "$PY ~/ananta_worker/collector.py once >/dev/null && $PY ~/ananta_worker/collector.py status" || { echo "    The test round failed; see ~/ananta_worker/logs/collector.log on the worker."; exit 1; }

echo "6/7 One test request for the fills capture ..."
if [ "$HL_OK" = 1 ]; then
  ssh "$H" "$PY ~/ananta_worker/hl_capture.py ping" || { echo "    The info API did not answer from the worker; the capture is installed and will retry every hour."; }
else
  echo "    skipped (no account list)"
fi

echo "7/7 Starting both under launchd (the collector restarts if it stops; the capture runs every hour and at every login) ..."
for L in "$LABEL" "$HL_LABEL"; do
  [ "$L" = "$HL_LABEL" ] && [ "$HL_OK" != 1 ] && continue
  ssh "$H" "launchctl bootout gui/\$(id -u)/$L 2>/dev/null; sleep 2; launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/$L.plist" \
    || echo "    $L not started now (is someone logged in on the worker's screen?). It starts at the next login."
done
sleep 5
ssh "$H" "launchctl print gui/\$(id -u)/$LABEL 2>/dev/null | grep -E '^\s*(state|pid) =' || true"
echo
echo "Done. The one-line check from this Mac, any time:"
echo "    ssh $H '~/ananta_worker/status'"
echo "The first fills capture catches up the last 7 finished days (about 10 to 15 minutes); its line says 'hl OK' when it holds them."
