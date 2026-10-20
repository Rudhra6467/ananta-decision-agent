"""SP3, the positional playbook (registrations/sp3_v1.json). This file holds the PRE-FREEZE steps only; nothing here reads an outcome.

  python -m india.sp3 prep coverage     the coverage rule (presence only, from the download manifests; no data file is read)
                                        -> manifests/sp3_prep_coverage.json
  python -m india.sp3 prep counts       stage-1 candidate counts on the families that survive coverage (family x year, no outcomes)   [next]
  python -m india.sp3 prep stops        the 2005-2023 permanent-stop list and the mechanical rule's agreement                          [next]

The study itself (stages 2-6) is written after the freeze and cross-checked by india/checks/sp3_crosscheck.py before any result is read.
Leak check: this file may call only sealed.coverage / sealed.coverage_summary (india/leakcheck.py).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from india import paths, sealed

HERE = Path(__file__).parent
SPEC = HERE / "registrations" / "sp3_v1.json"
H0, H1 = "2024-01-01", "2026-09-30"

# every source an SP3 family or feature depends on, with the manifest that records its downloads (stage_1 / stage_3 / in_window_events)
SOURCES = [
    {"source": "cash market prices (all families, holding bars)", "manifest": "cm_bhavcopy", "used_by": ["ALL"]},
    {"source": "delivery share", "manifest": "delivery", "used_by": ["feature:delivery_share"]},
    {"source": "participant OI (FII index-futures long share)", "manifest": "flows_participant_oi", "used_by": ["feature:fii_long_share"]},
    {"source": "F&O bhavcopy (F&O membership, index futures)", "manifest": "fo_bhavcopy", "used_by": ["feature:fo_member", "INDEX"]},
    {"source": "PR zips (price-band hits, board meetings, dividend records)", "manifest": "pr_zip", "used_by": ["BAND", "GAPD", "feature:band_hit_5", "feature:results_meeting_10"]},
    {"source": "corporate actions (adjustment factors, scheme records)", "manifest": "corporate_actions", "used_by": ["ALL"]},
    {"source": "announcements (holdout permanent-stop records)", "manifest": "announce_api", "used_by": ["in_window_events.holdout_permanent_stops"]},
    {"source": "Nasdaq (QQQ) close", "manifest": "us_close", "match": {"symbol": "QQQ"}, "used_by": ["feature:qqq"]},
] + [{"source": f"index {n} (day)", "manifest": "kite_index", "match": {"symbol": n, "interval": "day"}, "used_by": u} for n, u in (
    ("NIFTY 50", ["feature:nifty_trend", "feature:nifty_ret20", "INDEX"]), ("NIFTY BANK", ["INDEX"]), ("INDIA VIX", ["feature:vix"]),
    ("NIFTY SMLCAP 100", ["feature:small_vs_large"]), ("NIFTY 100", ["feature:small_vs_large"]))]

# results filings: the exchange replaced the old results index with integrated filings in April 2025 (old index: about 14k quarterly filings a
# year to 2024, 14 in Apr 2025, near zero after; integrated API: none before Apr 2025). The rule needs one meaning of 'broadcast time' across the
# holdout, checked on 200 filings present in BOTH sources in 2018-2023 (coverage_rule); there are none, so the check cannot pass.
RESULTS = {"source": "results filings (broadcast times)", "manifests": ["results_index", "results_index_integrated_v2"],
           "used_by": ["RESU", "RESD", "feature:results_filed_5"], "switch": "2025-04-01"}


def coverage() -> dict:
    rows = []
    for s in SOURCES:
        r = sealed.coverage_summary(s["manifest"], H0, H1, s.get("match"))
        rows.append({**s, **r})
    # results: presence of a status-200 window is not enough when a source was retired, so each era counts only its own source
    old = set(sealed.coverage("results_index", H0, "2025-03-31"))
    new = set(sealed.coverage("results_index_integrated_v2", RESULTS["switch"], H1))
    allsess = sealed.coverage_summary("cm_bhavcopy", H0, H1)["sessions"]
    share = len(old | new) / allsess if allsess else 0.0
    rows.append({**RESULTS, "share_present": round(share, 4), "comparison_200": {
        "rule": "lowest 200 of hash(filing_id, 19) among 2018-2023 filings present in both sources; pass if at least 190 match to the minute",
        "result": "NOT POSSIBLE: the integrated API has no filing before 2025-04, so no 2018-2023 filing is in both sources", "pass": False},
        "verdict": "FAIL", "why": "the source changes inside the holdout (2025-04) and the broadcast-time meaning cannot be checked across the change"})
    struck_fam = sorted({u for r in rows if r["verdict"] == "FAIL" for u in r["used_by"] if not u.startswith(("feature:", "ALL", "INDEX", "in_window"))})
    struck_feat = sorted({u.split(":", 1)[1] for r in rows if r["verdict"] == "FAIL" for u in r["used_by"] if u.startswith("feature:")})
    fatal = [r["source"] for r in rows if r["verdict"] == "FAIL" and any(u in ("ALL", "INDEX") or u.startswith("in_window") for u in r["used_by"])]
    out = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "window": [H0, H1], "rule": "PASS at >= 99% of sessions present and no gap over 5 sessions; presence from the download manifests only",
           "sources": rows, "struck_families": struck_fam, "struck_features": struck_feat, "fatal": fatal}
    (paths.manifest_dir() / "sp3_prep_coverage.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    if a[:2] == ["prep", "coverage"]:
        o = coverage()
        for r in o["sources"]:
            print(f"{r['verdict']:4s}  {r.get('share_present', 0):7.2%}  gap {str(r.get('longest_gap', '-')):>3s}  {r['source']}")
        print("struck families:", o["struck_families"], " struck features:", o["struck_features"], " FATAL:", o["fatal"])
    else:
        print(__doc__)
