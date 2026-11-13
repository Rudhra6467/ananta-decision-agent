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


def _board_meetings():
    # 3 Nov 2026 (data audit step 3): NSE's board-meetings calendar, the next 60 days as known tonight, plus any month not yet in the history
    # Like _data_gaps, an outside site's bad evening is reported as text and never fails the nightly build (the gate's clean-run count).
    from india import boardmeetings
    out = {}
    for k, fn in (("ahead", lambda: boardmeetings.ahead().get("rows")), ("history", boardmeetings.history), ("build", boardmeetings.build)):
        try:
            out[k] = fn()
        except Exception as e:  # noqa: BLE001
            out[k] = f"problem {type(e).__name__}: {e}"
    return out


def _results_html():
    # 3 Nov 2026 (D20b): the 2010-2017 HTML result pages, at most 1,000 a night, so the fetch keeps moving if the background run stops;
    # resumable and skipped once every page is in (pages already fetched are never asked again). Never fails the build.
    from india import results_html
    try:
        return {"fetch": results_html.fetch(2010, 2017, limit=1000), "build": results_html.build()}
    except Exception as e:  # noqa: BLE001
        return f"problem {type(e).__name__}: {e}"


def _flows():
    from india import flows
    return flows.fetch(dt.date.today().year), flows.build()


def _data_gaps():
    """25 Oct 2026 audit (data gaps): the Nifty valuation series for this year, NSDL's FPI archive for last month and this one, and today's
    sector-list snapshot (the map is point in time only from its first snapshot, so a missed day is a hole in that history)."""
    # Each part reports its own problem as text and never fails the nightly build: an outside site's bad evening must not reset the gate's
    # clean-run count (the coverage reports show the holes).
    from india import fiidii, sectormap, valuation
    today = dt.date.today()
    prev = (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    quiet = lambda *_: None
    parts = {"valuation": lambda: (valuation.fetch(today.year, log=quiet), valuation.build().get("rows")),
             "fpi_archive": lambda: (fiidii.history(prev, log=quiet), fiidii.build().get("rows")),
             "sector_map": lambda: (sectormap.snapshot(log=quiet), sectormap.build().get("labels"))}
    out = {}
    for k, fn in parts.items():
        try:
            out[k] = fn()
        except Exception as e:  # noqa: BLE001
            out[k] = f"problem (not a build failure) {type(e).__name__}: {str(e)[:150]}"
    return out


def _surveil():
    from india import surveil
    return surveil.snapshot(), surveil.build()


def _pr_silver():
    from india import przip
    today = dt.date.today()
    backfill.run("pr_zip", today - dt.timedelta(days=8), today - dt.timedelta(days=1), 1.0)
    return przip.build()


def _managed_mark() -> dict:
    """12 Nov evening (repair 2's outside check, N2): a failure was swallowed and the step counted as ok, so nobody was told. It still does
    not fail the data build (the evening run marks the book anyway, and a failed build would drop the night from the evidence counts), but it
    now writes one line to the job's error file, which the app's run check reads, so the failure shows as the India nightly's problem."""
    try:
        from india import managed
        return managed.mark_after_close()
    except Exception as e:  # noqa: BLE001
        why = f"{type(e).__name__}: {str(e)[:160]}"
        print(f"india.nightly managed_mark FAILED {why} (the evening run will mark the book instead)", file=sys.stderr, flush=True)
        return {"status": "error", "why": why}


def last_published_day(now_utc: dt.datetime | None = None) -> dt.date:
    """The newest NSE session whose end-of-day files should be out: today in India once it is past 19:00 there (NSE posts the bhavcopy
    and the F&O files by about 18:30-19:30), else yesterday in India. Weekends and holidays come back as "no file" and are skipped.
    Fixed 24 Oct 2026: the job ran only at 02:30 Toronto (12:00 in India, the day after) and fetched up to "yesterday in Toronto", so a
    session's close reached the read model only after the NEXT session had already traded: every plan and morning view ran one session late."""
    now = (now_utc or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    return now.date() if now.hour >= 19 else now.date() - dt.timedelta(days=1)


def _r2_verify(r2sync) -> dict:
    r = r2sync.verify()
    r["checked_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "r2_verify.json").write_text(json.dumps(r, indent=1, default=str))
    return {k: r[k] for k in ("local_files", "backed_up_same_size", "changed_since_upload", "missing_in_bucket", "size_mismatch")}


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
        # 29 Oct audit: the calendar is built from the cash manifest, so it is rebuilt right after the cash files land; before this it was only
        # rebuilt by the 22:00 paper job, and the integrity calendar check failed every afternoon with "a cash file on a non-trading day"
        ("calendar", silver.build_calendar),
        ("silver_delivery", lambda: delivery.build_year(today.year)),
        ("actions_build", lambda: (actions.build_b(), actions.build_a(), actions.build_factors())),
        ("catalog", catalog.build),
        # added 18 Oct: keep F&O, Greeks and index silver current for the paper context and the options book, and the point-in-time fundamentals
        ("silver_fo", lambda: _fo_year(today.year)),
        ("greeks", lambda: _greeks_year(today.year)),
        ("kite_index_silver", _kite_index_silver),
        ("results_integrated", lambda: _results_integrated(today - dt.timedelta(days=14))),
        ("fundamentals", _fundamentals),
        ("board_meetings", _board_meetings),
        ("results_html", _results_html),
        ("flows", _flows),
        # 12 Nov 2026 (the keen outside audit, G-03): the managed book is filled and marked as soon as the day file and the factors are in,
        # not 15 hours later in the evening run; the next plan stays with the evening run. Its result is reported here, never a failed build.
        ("managed_mark", _managed_mark),
        ("pr_silver", _pr_silver),
        ("surveillance", _surveil),
        ("data_gaps", _data_gaps),
        # 19 Oct: the firewall proof is re-run every night; a FAIL is a gate result recorded in manifests/firewall.json, not a build failure
        ("firewall", lambda: {k: v["ok"] for k, v in __import__("india.firewall", fromlist=["run"]).run().items() if not k.startswith("_")}),
    ]
    if sync:
        from india import r2sync
        steps.append(("r2_sync", r2sync.sync))
        # 25 Oct audit: after the upload, every backed-up file is checked against the bucket by size; the result is kept in manifests/r2_verify.json
        steps.append(("r2_verify", lambda: _r2_verify(r2sync)))
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
