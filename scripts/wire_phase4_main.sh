#!/usr/bin/env bash
# Run from repo root: bash scripts/wire_phase4_main.sh
set -e
python3 - <<'PY'
from pathlib import Path
p = Path('main.py')
t = p.read_text()
changed = False

if 'print_wavea_snapshot' not in t:
    t = t.replace(
        '    print("  cycles                     → Cycle + opportunity ledger")\n    print("  help                       → Show all commands")',
        '    print("  cycles                     → Cycle + opportunity ledger")\n    print("  wavea / postcycle          → Wave A KEEP/WATCH/CUT suggestions")\n    print("  help                       → Show all commands")',
    )
    t = t.replace(
        '            print("  cycles                     → Cycle + opportunity ledger")\n            print("  performance / stats        → Decision performance summary")',
        '            print("  cycles                     → Cycle + opportunity ledger")\n            print("  wavea / postcycle          → Wave A KEEP/WATCH/CUT suggestions")\n            print("  performance / stats        → Decision performance summary")',
    )
    t = t.replace(
        '        elif user_input in ["cycles", "cycle log", "cycle history"]:',
        '''        elif user_input in ["wavea", "wave a", "postcycle", "post-cycle", "snapshot"]:
            from src.phase4_cli import print_wavea_snapshot
            print_wavea_snapshot()

        elif user_input in ["cycles", "cycle log", "cycle history"]:''',
    )
    changed = True

if 'link_monitor_outcome' not in t:
    old = '''            if len(enabled) >= 5:
                print("Note: Many strategies are enabled. Watch for overlapping signals.")

            print("=" * 55)'''
    new = '''            if len(enabled) >= 5:
                print("Note: Many strategies are enabled. Watch for overlapping signals.")

            from src.phase4_cli import link_monitor_outcome
            link_monitor_outcome(open_count, len(enabled), health, get_portfolio)

            print("=" * 55)'''
    if old not in t:
        raise SystemExit('monitor block not found — main.py layout unexpected')
    t = t.replace(old, new)
    changed = True

if not changed:
    print('Already wired.')
else:
    p.write_text(t)
    print('Wired wavea + monitor outcome link into main.py')
PY
