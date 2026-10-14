"""Engine plan U7.1: history for every coin Ananta watches, not only the 120 of rule v1.

For each registry coin outside the 120 (and each coin in the lake's 120 as before, untouched), pull Binance Data Vision's own
15-minute, hourly, 4-hour and daily monthly files (no 1-minute files: those stay for the 120 only, D5), check each against
Binance's checksum, and build clean Parquet in the same lake folders. Safe to re-run: only new months are downloaded.

  ~/ananta_venvs/lake/bin/python scripts/lake_extend.py [--max N]      (low priority; log: ~/ananta_runs/lake_extend.log)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

INTERVALS = ("1d", "4h", "1h", "15m")


def main(argv: list[str]) -> None:
    from src.lake import binance_vision as BV
    from src.lake import root

    agent_dir = Path(os.getenv("JARVIS_AGENT_DIR", os.path.expanduser("~/code/ananta-decision-agent")))
    reg = json.loads((agent_dir / "universe_live.json").read_text())
    chosen = set(json.loads((root() / "reports" / "universe_v1.json").read_text())["chosen"])
    todo = [k["symbol"] for c, k in sorted(reg["coins"].items(), key=lambda x: -(x[1].get("median_usd_30d") or 0))
            if k.get("status") == "LISTED" and k.get("symbol") not in chosen]
    if "--max" in argv:
        todo = todo[: int(argv[argv.index("--max") + 1])]
    print(f"[{time.strftime('%Y-%m-%d %H:%M')}] {len(todo)} coins outside the 120", flush=True)
    done = {"ok": 0, "errors": {}}
    for i, s in enumerate(todo, 1):
        for iv in INTERVALS:
            try:
                BV.pull(s, iv, log=lambda *a: None)
                BV.build(s, iv)
            except Exception as exc:  # noqa: BLE001  one coin or interval failing never stops the rest
                done["errors"][f"{s}:{iv}"] = str(exc)[:120]
        done["ok"] += 1
        if i % 20 == 0:
            print(f"  {i}/{len(todo)} coins, {len(done['errors'])} errors", flush=True)
    out = root() / "reports" / "lake_extend.json"
    out.write_text(json.dumps({"t": int(time.time()), "coins": len(todo), "errors": done["errors"], "intervals": INTERVALS}, indent=1))
    print(f"[{time.strftime('%Y-%m-%d %H:%M')}] done: {done['ok']} coins, {len(done['errors'])} errors -> {out}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
