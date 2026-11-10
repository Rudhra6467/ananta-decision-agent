"""The night test for crypto (Madhav, 10 Nov 2026: "yes, lets build it"): asks Ananta tonight's questions in test mode and marks every answer
(jarvis/service/nightcheck.py). Started by the service after the officer's note (universe_watch.start_night_test); can be run by hand.
Writes docs/repair_shop/nightcheck/ and one line to ~/ananta_runs/nightcheck.log; sends a phone note only when an answer was wrong."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        from scripts.run_agent_exam import load_env

        load_env()
    from jarvis.service import ask, core, nightcheck

    ask.CACHE_1H = False          # the night's questions are seconds apart: the 5-minute cache is enough and costs less to write
    j = core.from_env()
    only = [x for x in sys.argv[1:] if not x.startswith("-")] or None
    out = nightcheck.run(j, only=only, save="--dry" not in sys.argv, file_flags="--dry" not in sys.argv)
    print(time.strftime("%Y-%m-%d %H:%M"), out["line"], f"cost ${out['cost_usd']:.3f} (answers ${out['cost_answers_usd']:.3f}, grader ${out['cost_grader_usd']:.3f})",
          f"{out['minutes']} min", flush=True)
    for w in out["wrong"]:
        print("  WRONG", w["id"], "|", w["why"], "|", w["answer"][:240].replace("\n", " "))
    for x in out["look"]:
        print("  LOOK ", x["id"], "|", ", ".join(x["figures"]))
    if out["wrong"] and "--dry" not in sys.argv:
        try:
            from src.intelligence.paper_watch import push_phone

            push_phone("Ananta's night test", out["line"][:220], level="EVENT")
        except Exception as exc:  # noqa: BLE001
            print("  push failed:", str(exc)[:120])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
