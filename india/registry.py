"""Study registry and multiple-testing ledger. Every study is registered before it is run; every variant it tries is counted.

  from india import registry
  reg = registry.register("E02", family="exit", title="...", hypothesis="...", variants=[...])   # before the run
  registry.record(reg, variant="atr_trail_3", dev=(mean, t, n), val=(mean, t, n), extra={...})   # for each variant, after the run
  python -m india.registry status

Verdicts (one rule for every study, fixed here so no study picks its own bar):
  threshold z(family) = Bonferroni-style two-sided 5% over every variant ever tried in that family  -> NormalDist().inv_cdf(1 - 0.025 / k)
  VALIDATED    dev t >= z and val t >= z, same sign, val mean has the dev sign
  CONDITIONAL  dev t >= z, val t >= 1.65 same sign (holds out of sample, not by the strict bar), or val passes z with dev t >= 1.65
  OPPOSITE     (only when the hypothesis has a direction) significantly the other way in dev and the same way in val
  REJECTED     dev t < 1.65 or the val sign differs from dev, or the effect has the wrong sign without significance
  Also: with a direction, a VALIDATED/CONDITIONAL needs the dev mean to have that sign.
  INCONCLUSIVE otherwise (including too few dates)
The ledger is append-only (manifests/test_ledger.jsonl) and mirrored in the catalog table test_ledger. Results are evidence, not decisions: a VALIDATED
exit rule still has to pass the paper book before it is used.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from statistics import NormalDist

from india import catalog, paths

MIN_DATES = 16  # quarter blocks per period (validation has 24)


def _ledger_path():
    return paths.manifest_dir() / "test_ledger.jsonl"


def _rows() -> list[dict]:
    p = _ledger_path()
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def family_count(family: str) -> int:
    return len({(r["study"], r["variant"]) for r in _rows() if r["kind"] == "result" and r["family"] == family})


def threshold(k: int) -> float:
    k = max(1, k)
    return NormalDist().inv_cdf(1 - 0.025 / k)


def register(study: str, family: str, title: str, hypothesis: str, variants: list[str], note: str = "", bar_families: list[str] | None = None,
             union_k: int | None = None, holdout_k: int | None = None, rerun_reason: str | None = None) -> dict:
    """Writes the registration line (what was claimed before the run). Re-registering an id appends a new version.
    bar_families / union_k / holdout_k (SP3 review, 20 Oct 2026): a study whose bar spans several families stores the list and the k pinned at its
    freeze, so the bar cannot drift as rows are recorded; record() uses union_k for the standard and seen rules and holdout_k for holdout rows.
    rerun_reason (25 Oct audit): a study id registered before gets a version number and the reason for running it again (the argument, or the
    ANANTA_RERUN_REASON environment variable); with neither, the row says "no reason given", so a quiet re-run is visible in the ledger."""
    import os

    reg = {"kind": "registration", "study": study, "family": family, "title": title, "hypothesis": hypothesis, "variants": list(variants), "note": note,
           "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    before = sum(1 for r in _rows() if r.get("kind") == "registration" and r.get("study") == study)
    if before:
        reg["version"] = before + 1
        reg["rerun_reason"] = rerun_reason or os.getenv("ANANTA_RERUN_REASON") or "no reason given"
    if bar_families:
        reg["bar_families"] = sorted(set(bar_families) | {family})
    if union_k:
        reg["union_k"] = int(union_k)
    if holdout_k:
        reg["holdout_k"] = int(holdout_k)
    reg["stamp"] = _stamp(study)
    with _ledger_path().open("a") as fh:
        fh.write(json.dumps(reg, default=str) + "\n")
    return reg


def _stamp(study: str) -> dict:
    """Code version and the fingerprints of the datasets this study reads (from the tracker's data needs), so every result can be traced to its inputs."""
    try:
        from india import lineage

        base = study.split("-")[0]
        return lineage.stamp(lineage.datasets_for(base), lineage.CODE.get(base[0], []))
    except Exception as e:  # provenance is recorded, never a reason to stop a study
        return {"error": f"{type(e).__name__}: {e}"}


def verdict(dev_t: float, val_t: float, dev_mean: float, val_mean: float, dates_dev: int, dates_val: int, z: float, expect: int = 0) -> str:
    if min(dates_dev, dates_val) < MIN_DATES or any(x != x for x in (dev_t, val_t)):
        return "INCONCLUSIVE"
    same = (dev_mean > 0) == (val_mean > 0)
    if expect and abs(dev_t) >= 1.65 and (dev_mean > 0) != (expect > 0) and same:
        return "OPPOSITE"  # significantly the other way round, in both periods: evidence against the hypothesis, and worth reading
    if abs(dev_t) < 1.65 or not same or (expect and (dev_mean > 0) != (expect > 0)):
        return "REJECTED"
    if abs(dev_t) >= z and abs(val_t) >= z:
        return "VALIDATED"
    if (abs(dev_t) >= z and abs(val_t) >= 1.65) or (abs(val_t) >= z and abs(dev_t) >= 1.65):
        return "CONDITIONAL"
    return "INCONCLUSIVE"


def verdict_seen(val_t: float, val_mean: float, dates_val: int, z: float, expect: int) -> str:
    """Rule for rows on years whose earlier results shaped the design (SP1 review, 19 Oct 2026): the dev year is reported but does not gate.
    SUPPORTED_SEEN: validation t at or beyond the family z with the expected sign; OPPOSITE: at or beyond z the other way; NOT_SUPPORTED_SEEN
    otherwise; INCONCLUSIVE with too few dates. Seen-period support is never confirmation: only the registered holdout run confirms."""
    if dates_val < MIN_DATES or val_t != val_t:
        return "INCONCLUSIVE"
    if abs(val_t) >= z and (val_mean > 0) == (expect > 0):
        return "SUPPORTED_SEEN"
    if abs(val_t) >= z:
        return "OPPOSITE"
    return "NOT_SUPPORTED_SEEN"


def verdict_holdout(val_t: float, val_mean: float, dates_val: int, z: float, expect: int) -> str:
    """The single confirmatory run on a sealed holdout: CONFIRMED when t reaches the family z with the expected sign; OPPOSITE when it reaches z
    the other way; NOT_CONFIRMED otherwise; INCONCLUSIVE with too few dates."""
    if dates_val < MIN_DATES or val_t != val_t:
        return "INCONCLUSIVE"
    if val_t * (1 if expect >= 0 else -1) >= z:
        return "CONFIRMED"
    if val_t * (1 if expect >= 0 else -1) <= -z:
        return "OPPOSITE"
    return "NOT_CONFIRMED"


def record(reg: dict, variant: str, dev: tuple, val: tuple, extra: dict | None = None, expect: int = 0, rule: str = "standard") -> dict:
    """dev / val = (mean, t_stat, dates). Counts the variant into its family, then scores it against the family threshold.
    rule: 'standard' (verdict below) or 'seen_val_only' (verdict_seen)."""
    fam = reg["family"]
    rows = _rows()
    if rule == "holdout_one_sided" and reg.get("holdout_k"):
        k, k_src = int(reg["holdout_k"]), "holdout_k"  # frozen at registration: the confirmatory claims on the sealed period (exploratory holdout rows are not counted)
    elif rule != "holdout_one_sided" and reg.get("union_k"):
        k, k_src = int(reg["union_k"]), "union_k"  # frozen at registration: the rows of every family in bar_families plus the study's own
    else:
        fams = set(reg.get("bar_families") or [fam])
        seen = {(r["study"], r["variant"]) for r in rows if r["family"] in fams and r["kind"] == "result"}
        k = len(seen | {(reg["study"], variant)})
        k_src = "bar_families" if reg.get("bar_families") else "family"
    z = threshold(k)
    if rule == "holdout_one_sided":
        v = verdict_holdout(val[1], val[0], val[2], z, expect)
    elif rule == "seen_val_only":
        v = verdict_seen(val[1], val[0], val[2], z, expect)
    else:
        v = verdict(dev[1], val[1], dev[0], val[0], dev[2], val[2], z, expect)
    if (extra or {}).get("min_trades_ok") is False:
        v = "INCONCLUSIVE"  # a pre-registered minimum trade count was not reached (e.g. SP1: 100 validation trades per index)
    code = (reg.get("stamp") or {}).get("code", {})
    code_id = code.get("git") or None
    if code_id and code.get("dirty_fingerprint"):
        code_id += f"+dirty:{code['dirty_fingerprint']}"
    line = {"kind": "result", "study": reg["study"], "family": fam, "variant": variant, "k_in_family": k, "k_source": k_src, "z": round(z, 3), "dev": list(dev), "val": list(val),
            "verdict": v, "rule": rule, "extra": extra or {}, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "registered_at": reg.get("at"),
            # 25 Oct audit: uncommitted code shows as git+dirty fingerprint, so a result can always be traced to the exact code that made it
            "code": code_id}
    if reg.get("version"):
        line["registration_version"], line["rerun_reason"] = reg["version"], reg.get("rerun_reason")
    with _ledger_path().open("a") as fh:
        fh.write(json.dumps(line, default=str) + "\n")
    return line


def mirror_to_catalog() -> int:
    con = catalog.connect()
    con.execute("create table if not exists test_ledger (study varchar, family varchar, variant varchar, k_in_family integer, z double, dev_mean double, dev_t double, dev_dates integer, "
                "val_mean double, val_t double, val_dates integer, verdict varchar, logged_at varchar, extra varchar)")
    con.execute("delete from test_ledger")
    rs = [r for r in _rows() if r["kind"] == "result"]
    con.executemany("insert into test_ledger values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [[r["study"], r["family"], r["variant"], r["k_in_family"], r["z"], r["dev"][0], r["dev"][1], r["dev"][2], r["val"][0], r["val"][1], r["val"][2],
                      r["verdict"], r["at"], json.dumps(r["extra"], default=str)] for r in rs])
    con.close()
    return len(rs)


def status() -> None:
    rows = _rows()
    regs = [r for r in rows if r["kind"] == "registration"]
    res = [r for r in rows if r["kind"] == "result"]
    print(f"registrations {len(regs)}  results {len(res)}")
    fams = sorted({r["family"] for r in res})
    for f in fams:
        rs = [r for r in res if r["family"] == f]
        counts: dict[str, int] = {}
        for r in rs:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        print(f"  {f:10s} variants tried {family_count(f):3d}  z now {threshold(family_count(f)):.2f}  {counts}")
    mirror_to_catalog()


if __name__ == "__main__":
    paths.ensure()
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        status()
