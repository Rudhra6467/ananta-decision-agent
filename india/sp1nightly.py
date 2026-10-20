"""The nightly SP1 replay check (India learning loop, approved by Madhav 20 Oct 2026; the crypto loop's nightly rebuild, carried over).

  python -m india.sp1nightly [YYYY-MM-DD]     default: today's date on the Mac (Toronto), i.e. the IST session that closed this Toronto morning

Every evening it re-runs the session the SP1 paper decided that morning through the live code (india.sp1paper.replay_ledger: Kite candles cut at
each decision time) and compares it with the live decision ledger, then checks both ledgers' hash chains and the timing rule (sp1paper.verify).
It writes manifests/sp1_nightly_replay.json (and one line in manifests/sp1_nightly_replay.jsonl) with PASS, FAIL or the reason it was skipped.
It never crashes on an expected condition:
  skipped (holiday)        the date is a weekend or an NSE holiday: nothing was decided
  skipped (no ledger rows) no SP1 paper decision for the date (before the paper start, 21 Oct 2026, or a session the ledger shows as an error)
  skipped (no token)       the Kite token is missing, expired or rejected (a replay needs Kite candles); the ledger check still runs
Anything else unexpected is written as ERROR with the message (exit 1), so the morning summary shows it. Kite is read with GET only.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import traceback

from india import dayplan, kite, paths, sp1paper

OUT = "sp1_nightly_replay"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _non_session(day: dt.date) -> str | None:
    if day.weekday() >= 5:
        return "weekend"
    try:
        hol = dayplan.holidays(refresh=False)
    except Exception:  # the holiday file is unreadable: treat the day as a session and let the ledger decide
        hol = set()
    return "NSE holiday" if day in hol else None


def run(day: dt.date | None = None, log=print) -> dict:
    day = day or dt.date.today()
    out: dict = {"date": day.isoformat(), "at": _now()}
    try:
        out["verify"] = sp1paper.verify()
    except Exception as e:
        out["verify"] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
    status = None
    why = _non_session(day)
    if why:
        status, out["detail"] = "skipped (holiday)", why
    else:
        led = [r for r in sp1paper._rows(sp1paper.DECISIONS) if r.get("date") == day.isoformat()]
        dec = [r for r in led if r.get("kind") == "decision"]
        if not dec:
            errs = [r.get("error") for r in led if r.get("kind") == "error"]
            status = "skipped (no ledger rows)"
            out["detail"] = (f"the ledger shows errors for {day}: {errs}" if errs else
                             f"no SP1 paper decision for {day}" + (f" (paper starts {sp1paper.PAPER_START})" if day < sp1paper.PAPER_START else ""))
            out["ledger_errors"] = errs
        else:
            try:
                kite.token()   # the file's own expiry first: no API call, no phone nudge
                rep = sp1paper.replay_ledger(day, log)
                out["replay"] = rep
                status = "PASS" if not rep["mismatches"] else "FAIL"
            except kite.NeedLogin as e:
                status, out["detail"] = "skipped (no token)", str(e)[:200]
            except Exception as e:
                status, out["detail"] = "ERROR", f"{type(e).__name__}: {e}"[:300]
                out["trace"] = traceback.format_exc()[-1500:]
    if not out["verify"].get("ok", False):
        out["verify_failed"] = True
        if status in ("PASS",) or status.startswith("skipped"):
            status = f"FAIL (ledger check){'; replay ' + status if status != 'PASS' else ''}"
    out["status"] = status
    paths.manifest_dir().mkdir(parents=True, exist_ok=True)
    (paths.manifest_dir() / f"{OUT}.json").write_text(json.dumps(out, indent=1, default=str))
    with (paths.manifest_dir() / f"{OUT}.jsonl").open("a") as fh:
        fh.write(json.dumps({k: out.get(k) for k in ("date", "at", "status", "detail")}, default=str) + "\n")
    log(f"sp1 nightly replay {day}: {status}" + (f" ({out.get('detail')})" if out.get("detail") else ""))
    return out


if __name__ == "__main__":
    paths.ensure()
    d = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    r = run(d)
    print(json.dumps({k: r.get(k) for k in ("date", "status", "detail")}, indent=1, default=str))
    sys.exit(1 if r["status"] == "ERROR" or r["status"].startswith("FAIL") else 0)
