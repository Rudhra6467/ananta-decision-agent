"""The weekly agent exam (OD-EXAM-CADENCE (a), approved by Madhav 2026-10-20: one run then, then every Sunday; about $1.30 a run).
Run by launchd (com.ananta.exam, Sundays 07:10 Toronto) from the live checkout; writes docs/repair_shop/exam/latest.json and history.jsonl,
which the gate's agent_knows, agent_unknowns and ux_why read. Prints a short summary for ~/ananta_runs/exam_weekly.log."""
from __future__ import annotations

import json
import time

from jarvis.service import core, exam


def main() -> int:
    j = core.from_env()
    t0 = time.time()
    e = exam.run(j)
    print(time.strftime("%Y-%m-%d %H:%M"), "KNOWS", e["known"], "of", e["known_of"], "UNKNOWNS", e["unknown"], "of", e["unknown_of"],
          "WHY", e.get("why"), "of", e.get("why_of"), "CONSISTENT", e.get("consistent"), "of", e.get("consistent_of"), "EXAM_PASS", e.get("exam_pass"))
    for r in e["rows"]:
        if not r["ok"]:
            print("  MISS", r["kind"], r["question"], "->", str(r.get("answer", ""))[:240].replace("\n", " "))
    print("FLIP_RATE", json.dumps(exam.flip_rate()), "MINUTES", round((time.time() - t0) / 60, 1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
