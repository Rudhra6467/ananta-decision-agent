"""The nightly job: fetch the last week's NSE files (resumable, so a missed night heals), rebuild this year's silver, rebuild the catalog,
back up to R2, write one heartbeat row. launchd com.ananta.india.nightly runs it at 12:45 Toronto on weekdays (after NSE posts the day's files) and at 02:30 every day as the heal run.

  python -m india.nightly [--no-sync]
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import traceback

from india import actions, backfill, catalog, delivery, paths, silver

DATASETS = ("cm_bhavcopy", "fo_bhavcopy", "delivery")


def _fo_year(y):
    from india import fo
    return fo.build_year(y)


def _greeks_year(y):
    from india import greeks
    return greeks.build_year(y)


def _kite_index_silver():
    from india import kite_index
    return kite_index.silver()


def _results_integrated(since):
    from india import results
    return results.index_integrated(since.isoformat())


def _fundamentals():
    from india import fundamentals
    return fundamentals.build()


def _flows():
    from india import flows
    return flows.fetch(dt.date.today().year), flows.build()


def _surveil():
    from india import surveil
    return surveil.snapshot(), surveil.build()


def _pr_silver():
    from india import przip
    today = dt.date.today()
    backfill.run("pr_zip", today - dt.timedelta(days=8), today - dt.timedelta(days=1), 1.0)
    return przip.build()


def last_published_day(now_utc: dt.datetime | None = None) -> dt.date:
    """The newest NSE session whose end-of-day files should be out: today in India once it is past 19:00 there (NSE posts the bhavcopy
    and the F&O files by about 18:30-19:30), else yesterday in India. Weekends and holidays come back as "no file" and are skipped.
    Fixed 24 Oct 2026: the job ran only at 02:30 Toronto (12:00 in India, the day after) and fetched up to "yesterday in Toronto", so a
    session's close reached the read model only after the NEXT session had already traded: every plan and morning view ran one session late."""
    now = (now_utc or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    return now.date() if now.hour >= 19 else now.date() - dt.timedelta(days=1)


def run(sync: bool = True) -> dict:
    paths.ensure()
    t0 = time.time()
    today = dt.date.today()
    end = last_published_day()
    start = end - dt.timedelta(days=8)
    out: dict = {"window": f"{start}..{end}"}
    steps = [
        ("fetch", lambda: {ds: backfill.run(ds, start, end, 1.0) for ds in DATASETS}),
        ("corporate_actions_fetch", lambda: actions.fetch([today.year])),
        ("silver_cm", lambda: silver.build_cm_year(today.year)),
        ("silver_delivery", lambda: delivery.build_year(today.year)),
        ("actions_build", lambda: (actions.build_b(), actions.build_a(), actions.build_factors())),
        ("catalog", catalog.build),
        # added 18 Oct: keep F&O, Greeks and index silver current for the paper context and the options book, and the point-in-time fundamentals
        ("silver_fo", lambda: _fo_year(today.year)),
        ("greeks", lambda: _greeks_year(today.year)),
        ("kite_index_silver", _kite_index_silver),
        ("results_integrated", lambda: _results_integrated(today - dt.timedelta(days=14))),
        ("fundamentals", _fundamentals),
        ("flows", _flows),
        ("pr_silver", _pr_silver),
        ("surveillance", _surveil),
        # 19 Oct: the firewall proof is re-run every night; a FAIL is a gate result recorded in manifests/firewall.json, not a build failure
        ("firewall", lambda: {k: v["ok"] for k, v in __import__("india.firewall", fromlist=["run"]).run().items() if not k.startswith("_")}),
    ]
    if sync:
        from india import r2sync
        steps.append(("r2_sync", r2sync.sync))
    ok = True
    for name, fn in steps:
        try:
            res = fn()
            out[name] = "ok" if name in ("fetch", "corporate_actions_fetch", "actions_build", "catalog") else res
        except Exception as e:  # one failed step must not hide the others; the heartbeat says which
            ok = False
            out[name] = f"FAILED {type(e).__name__}: {e}"
            print(traceback.format_exc(), flush=True)
    out["seconds"] = round(time.time() - t0)
    catalog.heartbeat("india.nightly", ok, json.dumps(out, default=str))
    print(json.dumps(out, default=str, indent=1), flush=True)
    return out


if __name__ == "__main__":
    r = run(sync="--no-sync" not in sys.argv)
    sys.exit(0 if all(not str(v).startswith("FAILED") for v in r.values()) else 1)
