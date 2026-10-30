"""Plain-words write-ups generated from the test ledger (29 Oct 2026 audit, map classes B and G).

The one map found 23 studies "done, not noted" (variants recorded, no results page, no plain name) and 26 notable results the screens do not
show. A researcher's write-up is better than a generated one, but a generated one beats silence: this page says, for every study in the
ledger, what was claimed, what was tried and what the registry concluded, in the registry's own numbers.

  python -m india.writeups            registrations/ledger_results.md  and  manifests/notable_results.json
  india.writeups.notable()            the notable (VALIDATED / CONDITIONAL / OPPOSITE) latest results, for the read model

Nothing here changes a verdict or a rule; it reads the ledger and writes words.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

from india import paths, registry

VERB = {"VALIDATED": "held up in both periods", "CONDITIONAL": "held up, weaker in one period", "OPPOSITE": "came out the opposite way",
        "REJECTED": "did not hold", "INCONCLUSIVE": "had too little data to judge", "SUPPORTED_SEEN": "supported on seen years (not confirmation)",
        "NOT_SUPPORTED_SEEN": "not supported on seen years", "CONFIRMED": "confirmed on the sealed years", "NOT_CONFIRMED": "not confirmed on the sealed years"}
NOTABLE = ("VALIDATED", "CONDITIONAL", "OPPOSITE", "CONFIRMED")
AUTO_MARK = "generated from the ledger by india.writeups"


def _latest() -> tuple[dict, dict]:
    regs, res = {}, {}
    for r in registry._rows():
        if r.get("kind") == "registration":
            regs[r["study"]] = r          # the latest registration wins (versions append)
        elif r.get("kind") == "result":
            res[(r["study"], r["variant"])] = r
    return regs, res


def _num(x) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "-"
    return f"{v:+.2%}" if abs(v) < 1 else f"{v:+.2f}"


def _row_words(r: dict, title: str) -> str:
    d, v = r["dev"], r["val"]
    return (f"{title}, variant {r['variant']}: {VERB.get(r['verdict'], r['verdict'])} "
            f"(2000-17 mean {_num(d[0])}, t {float(d[1]):+.1f}; 2018-23 mean {_num(v[0])}, t {float(v[1]):+.1f}; bar {r.get('z')})")


def notable() -> list[dict]:
    """Every latest result with a notable verdict, with the registration's title and one plain sentence."""
    regs, res = _latest()
    out = []
    for (s, var), r in sorted(res.items()):
        if r["verdict"] not in NOTABLE:
            continue
        title = (regs.get(s) or {}).get("title") or s
        out.append({"study": s, "family": r["family"], "variant": var, "verdict": r["verdict"], "title": title,
                    "dev": r["dev"], "val": r["val"], "z": r.get("z"), "rule": r.get("rule", "standard"), "at": r.get("at"),
                    "words": _row_words(r, title)})
    return out


def build() -> dict:
    regs, res = _latest()
    by_study = defaultdict(list)
    for (s, var), r in res.items():
        by_study[s].append(r)
    fam_of = {s: rows[0]["family"] for s, rows in by_study.items()}
    by_family = defaultdict(list)
    for s, fam in fam_of.items():
        by_family[fam].append(s)
    lines = [f"# Every study in the ledger, in plain words ({AUTO_MARK}, {dt.date.today().isoformat()})", "",
             "HISTORICAL BACKTEST only: development 2000-2017, validation 2018-2023; the 2024+ years are sealed. A verdict here is the registry's "
             "rule applied to the registered numbers (one family-wide bar for every variant ever tried in that family); it is evidence, not a "
             "decision, and nothing is in the paper book because of this page. A researcher's write-up (the *_results_v1.md pages) is the "
             "better source where one exists; this page exists so that no finished study is unwritten.", ""]
    n_studies = 0
    for fam in sorted(by_family):
        lines.append(f"## {fam} ({len(by_family[fam])} studies)")
        lines.append("")
        for s in sorted(by_family[fam]):
            rows = sorted(by_study[s], key=lambda r: r["variant"])
            reg = regs.get(s) or {}
            cnt = defaultdict(int)
            for r in rows:
                cnt[r["verdict"]] += 1
            n_studies += 1
            lines.append(f"### {s}: {reg.get('title') or '(no registration title)'}")
            if reg.get("hypothesis"):
                lines.append(f"Claim before the run: {reg['hypothesis']}")
            lines.append("Outcome: " + ", ".join(f"{n} {VERB.get(k, k)}" for k, n in sorted(cnt.items(), key=lambda t: -t[1])) +
                         f" across {len(rows)} variants.")
            best = [r for r in rows if r["verdict"] in NOTABLE]
            if best:
                lines.append("")
                lines.append("| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |")
                lines.append("|---|---|---|---|---|---|---|")
                for r in sorted(best, key=lambda r: -abs(float(r["val"][1]) if r["val"][1] == r["val"][1] else 0))[:12]:
                    lines.append(f"| {r['variant'].replace('|', ' · ')} | {r['verdict']} | {_num(r['dev'][0])} | {float(r['dev'][1]):+.1f} | {_num(r['val'][0])} | {float(r['val'][1]):+.1f} | {r.get('z')} |")
            lines.append("")
    out_md = Path(__file__).resolve().parent / "registrations" / "ledger_results.md"
    out_md.write_text("\n".join(lines))
    nb = notable()
    (paths.manifest_dir() / "notable_results.json").write_text(json.dumps({"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                                                                           "n": len(nb), "rows": nb}, indent=1, default=str))
    return {"studies": n_studies, "families": len(by_family), "notable": len(nb), "page": str(out_md)}


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
