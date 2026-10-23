"""File India's SAFE reconstruction findings on the repair board (RX-IN v1, Madhav 23 Oct 2026: "based on findings, it forwards things to the repair shop").

Run nightly by launchd (com.ananta.india.findings, 22:50 Toronto) through ~/ananta_runs/svc_env_run.py, after the India evening chain has
written the session card. It reads the findings queue from the India service over loopback (GET /v3/reconstruction/queue), files each SAFE
row still 'to_file' as a repair-board request with the Flag flow (jarvis/service/fixflow.py: the request is filed at once and up to three fixes
are offered, each SAFE or DECISION by code), at most SAFE_PER_NIGHT a night, oldest first, and tells the India service the request number
(POST /v3/reconstruction/filed) so the queue shows it and the same key is not filed again for seven sessions. Madhav picks the fix in the app
or by voice ("the first"), as with any flag; the repair worker builds the SAFE ones. Nothing here touches India data directly.
"""
from __future__ import annotations

import json
import sys
import urllib.request

INDIA = "http://127.0.0.1:8110"
SAFE_PER_NIGHT = 3


def _get(path: str) -> dict:
    with urllib.request.urlopen(INDIA + path, timeout=20) as r:
        return json.loads(r.read().decode())


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(INDIA + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def main() -> int:
    from jarvis.service import core, fixflow

    q = _get("/v3/reconstruction/queue")
    todo = [r for r in q.get("rows", []) if r.get("lane") == "SAFE" and r.get("state") == "to_file" and not r.get("request")]
    todo.sort(key=lambda r: (r.get("day") or "", r.get("written_at") or ""))
    cap = int(q.get("safe_per_night") or SAFE_PER_NIGHT)
    if not todo:
        print("india findings: nothing to file")
        return 0
    j = core.from_env()
    n = 0
    for r in todo[:cap]:
        text = f"Reconstruction finding {r.get('type')} ({r.get('day')}): {r.get('words', '')}"[:1500]
        try:
            res = fixflow.flag(j, text, market="india", screen="reconstruction", route="/lab")
        except Exception as exc:  # noqa: BLE001
            print(f"india findings: could not file {r.get('key')}: {exc}")
            continue
        _post("/v3/reconstruction/filed", {"key": r["key"], "num": int(res["num"]), "day": r.get("day") or "", "note": "duplicate" if res.get("duplicate") else "filed"})
        n += 1
        print(f"india findings: {r['key']} -> request #{res['num']}" + (" (duplicate words: same request)" if res.get("duplicate") else ""))
    left = len(todo) - n
    print(f"india findings: filed {n}; {left} wait for the next night" if left > 0 else f"india findings: filed {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
