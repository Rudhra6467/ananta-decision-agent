"""Study registry and multiple-testing ledger. Every study is registered before it is run; every variant it tries is counted.

  from india import registry
  reg = registry.register("E02", family="exit", title="...", hypothesis="...", variants=[...])   # before the run
  registry.record(reg, variant="atr_trail_3", dev=(mean, t, n), val=(mean, t, n), extra={...})   # for each variant, after the run
  python -m india.registry status

Verdicts (one rule for every study, fixed here so no study picks its own bar):
  threshold z(family) = Bonferroni-style two-sided 5% over every variant ever tried in that family  -> NormalDist().inv_cdf(1 - 0.025 / k)
  VALIDATED    dev t >= z and val t >= z, same sign, val mean has the dev sign
  CONDITIONAL  dev t >= z, val t >= 1.65 same sign (holds out of sample, not by the strict bar), or val passes z with dev t >= 1.65
  REJECTED     dev t < 1.65 or the val sign is opposite
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

MIN_DATES = 60


def _ledger_path():
    return paths.manifest_dir() / "test_ledger.jsonl"


def _rows() -> list[dict]:
    p = _ledger_path()
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def family_count(family: str) -> int:
    return len({(r["study"], r["variant"]) for r in _rows() if r["family"] == family})


def threshold(k: int) -> float:
    k = max(1, k)
    return NormalDist().inv_cdf(1 - 0.025 / k)


def register(study: str, family: str, title: str, hypothesis: str, variants: list[str], note: str = "") -> dict:
    """Writes the registration line (what was claimed before the run). Re-registering an id appends a new version."""
    reg = {"kind": "registration", "study": study, "family": family, "title": title, "hypothesis": hypothesis, "variants": list(variants), "note": note,
           "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    with _ledger_path().open("a") as fh:
        fh.write(json.dumps(reg) + "\n")
    return reg


def verdict(dev_t: float, val_t: float, dev_mean: float, val_mean: float, dates_dev: int, dates_val: int, z: float) -> str:
    if min(dates_dev, dates_val) < MIN_DATES or any(x != x for x in (dev_t, val_t)):
        return "INCONCLUSIVE"
    same = (dev_mean > 0) == (val_mean > 0)
    if abs(dev_t) < 1.65 or not same:
        return "REJECTED"
    if abs(dev_t) >= z and abs(val_t) >= z:
        return "VALIDATED"
    if (abs(dev_t) >= z and abs(val_t) >= 1.65) or (abs(val_t) >= z and abs(dev_t) >= 1.65):
        return "CONDITIONAL"
    return "INCONCLUSIVE"


def record(reg: dict, variant: str, dev: tuple, val: tuple, extra: dict | None = None) -> dict:
    """dev / val = (mean, t_stat, dates). Counts the variant into its family, then scores it against the family threshold."""
    fam = reg["family"]
    rows = _rows()
    seen = {(r["study"], r["variant"]) for r in rows if r["family"] == fam and r["kind"] == "result"}
    k = len(seen | {(reg["study"], variant)})
    z = threshold(k)
    v = verdict(dev[1], val[1], dev[0], val[0], dev[2], val[2], z)
    line = {"kind": "result", "study": reg["study"], "family": fam, "variant": variant, "k_in_family": k, "z": round(z, 3), "dev": list(dev), "val": list(val),
            "verdict": v, "extra": extra or {}, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
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
