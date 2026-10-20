"""Read-only: does the screen show what the voice said? (request #73, Oct 20)

Runs the checker over logged voice turns (a turns.jsonl made by ~/ananta_runs/voice_review/dump_turns.py) twice: as logged, and
with the say-show gate (appmap.say_show) re-applied to each turn's question, spoken words and screen moves.
Run: cd ~/code/ananta-agent-research && PYTHONPATH=. ~/ananta_venvs/jarvis/bin/python scripts/say_vs_show.py [turns.jsonl]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jarvis.service import sayshow  # noqa: E402

path = Path(sys.argv[1] if len(sys.argv) > 1 else "~/ananta_runs/voice_review/turns.jsonl").expanduser()
turns = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
r = sayshow.check(turns)
b, a = r["before"], r["after"]
print(f"turns that moved the screen: {r['moved']}")
print(f"as logged:      matched {b['matched']}; MISMATCH {b['mismatch']}; spoken text names no book {b['unclear']}")
print(f"with the gate:  matched {a['matched']}; MISMATCH {a['mismatch']}; spoken text names no book {a['unclear']}; move dropped {a['dropped']}")
for x in r["rows"]:
    if x["before"] != x["after"] or x["after"] == "mismatch":
        print(f"- {x['t']} heard: {x['heard'][:90]!r}\n    {x['before']} -> {x['after']}: opened {x['opened']}, now {x['opens_now']} ({x['note']})"
              f"\n    said: {x['said'][:160]!r}")
