"""Daily evidence: every evening, after the recorder, run the checks and studies that are ready and append the results to an evidence log.

  python -m india.evidence run
Two stores, both append-only: manifests/evidence_log.jsonl (one line per check per day) and the catalog table evidence_log. A study joins
the daily run by registering a function in STUDIES below once its tracker state is READY; its result line carries the study id, the data
window, the metric, and the number of days of recorder history behind it, so a result can always be read next to how much data stood behind it.
Nothing here changes a registration: it only records what the data said on that day.
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import json
import sys

from india import catalog, paths

EXPECTED_MINUTES = 375  # 09:15 to 15:29 IST


def _last_session_minutes(path: str) -> tuple[str, int]:
    with gzip.open(path, "rt") as gz:
        lines = gz.read().splitlines()
    candles = json.loads(lines[-1])["candles"]
    days: dict[str, int] = {}
    for c in candles:
        days[c[0][:10]] = days.get(c[0][:10], 0) + 1
    last = max(days)
    return last, days[last]


def check_recorder() -> dict:
    root = paths.bronze("kite_1m_fo")
    out = {"contracts_files": len(glob.glob(str(root / "*" / "*.jsonl.gz")))}
    for name in ("NIFTY 50", "NIFTY BANK", "INDIA VIX"):
        f = root / "indices" / f"{name}.jsonl.gz"
        if f.exists():
            day, n = _last_session_minutes(str(f))
            out[name] = {"last_session": day, "minutes": n, "complete": n >= EXPECTED_MINUTES - 2}
    out["ok"] = all(v.get("complete", True) for v in out.values() if isinstance(v, dict))
    return out


def check_nightly() -> dict:
    con = catalog.connect(read_only=True)
    n = con.execute("select count(*) from heartbeats where job = 'india.nightly' and ok").fetchone()[0]
    con.close()
    return {"nightly_ok_runs": n, "ok": n >= 1}


def check_leaks() -> dict:
    from india import leakcheck
    r = leakcheck.run()
    bad = [k for k, v in r.items() if not k.startswith("_") and not v["ok"]]
    return {"failed": bad, "ok": not bad}


def check_paper() -> dict:
    import json as _json
    p = paths.data_dir() / "paper" / "state.json"
    if not p.exists():
        return {"ok": False, "note": "no paper state yet"}
    st = _json.loads(p.read_text())
    counts: dict = {}
    for t in st["trades"].values():
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    return {"decisions": len(st["decisions"]), "trades": counts, "ok": len(st["decisions"]) >= 1}


def check_integrity() -> dict:
    from india import integrity
    r = integrity.run()
    bad = [k for k, v in r.items() if not k.startswith("_") and not v["ok"]]
    return {"failed": bad, "notes": {k: v["note"][:160] for k, v in r.items() if not k.startswith("_")}, "ok": not bad}


def check_lineage() -> dict:
    from india import lineage
    r = lineage.build()
    return {"data_items": r["data_items"], "mismatches": r["mismatches"], "studies": r["studies"], "git": r["git"]["git"], "dirty_files": len(r["git"]["dirty"]),
            "ok": not r["mismatches"]}


def check_baseline() -> dict:
    p = paths.data_dir() / "paper" / "baseline.parquet"
    if not p.exists():
        return {"ok": True, "note": "no baseline rows yet (first fill is the session after the first decision)"}
    import pandas as pd
    b = pd.read_parquet(p)
    return {"rows": len(b), "status": b["status"].value_counts().to_dict(), "journal": b["journal_status"].value_counts().to_dict(),
            "reasons": b["journal_reason"].value_counts().to_dict(), "ok": True}


CHECKS = {"recorder.minutes": check_recorder, "nightly.runs": check_nightly, "leakcheck": check_leaks, "paper.book": check_paper, "paper.baseline": check_baseline,
          "integrity": check_integrity, "lineage": check_lineage}
STUDIES: dict = {}  # study id -> function returning a metrics dict; filled as studies are registered and READY


def run() -> list[dict]:
    paths.ensure()
    today = dt.date.today().isoformat()
    rows = []
    for name, fn in {**CHECKS, **STUDIES}.items():
        try:
            res = fn()
            ok = bool(res.pop("ok", True))
        except Exception as e:  # a failing check is itself evidence
            res, ok = {"error": f"{type(e).__name__}: {e}"}, False
        rows.append({"date": today, "check": name, "ok": ok, "metrics": res})
    with (paths.manifest_dir() / "evidence_log.jsonl").open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    con = catalog.connect()
    con.execute("create table if not exists evidence_log (date date, \"check\" varchar, ok boolean, metrics varchar)")
    con.executemany("insert into evidence_log values (?, ?, ?, ?)", [[r["date"], r["check"], r["ok"], json.dumps(r["metrics"], default=str)] for r in rows])
    con.close()
    catalog.heartbeat("evidence.run", all(r["ok"] for r in rows), f"{len(rows)} checks")
    for r in rows:
        print(r["check"], "ok" if r["ok"] else "FAIL", json.dumps(r["metrics"], default=str)[:200], flush=True)
    return rows


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run()
