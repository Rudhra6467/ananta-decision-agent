"""Canada's own registry (namespace CA): review status, the frozen bundle, the holdout seal.

It is a separate file from crypto's strategy_status.json on purpose: Canada shares no files with crypto.
  load() / save()                 the registry
  freeze_bundle(regs, doc, ...)   at Madhav's approval: write the five registrations and the whole C0 document
                                  verbatim, then hash them TOGETHER with the code that holds the thresholds and
                                  cost formula (and its tests) as one bundle. Refused without an approval note,
                                  and refused a second time: a change is a new, separately approved registration.
  verify()                        [] while every file in the bundle still hashes to its recorded value
  seal_broken()                   True only after Madhav's recorded approval to open the holdout
  assert_research_dates(a, b)     research code calls this; dates in the holdout are refused while sealed
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canada.paths import HOLDOUT_START

ROOT = Path(__file__).resolve().parent            # canada/
REPO = ROOT.parent
REG_PATH = ROOT / "registry" / "canada_status.json"
REG_DIR = ROOT / "registrations"
RULE_CODE = ("canada/validation.py", "canada/costs.py", "tests/test_canada_isolation.py")
REVIEWS = ("CA1", "CA2", "CA3", "CA4", "CA5")
STATUSES = ("DRAFT_AWAITING_APPROVAL", "FROZEN", "RUNNING", "VERDICT")
VERDICTS = ("ENOUGH", "WEAK", "FAIL", "INSUFFICIENT EVIDENCE", "NOT RUN")


class HoldoutSealed(RuntimeError):
    pass


def load() -> dict:
    return json.loads(REG_PATH.read_text())


def save(d: dict) -> None:
    REG_PATH.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bundle_sha(files: dict[str, str]) -> str:
    return sha256_text("\n".join(f"{p}:{h}" for p, h in sorted(files.items())))


def freeze_bundle(registrations: dict[str, str], document: str, approved: str, day: str) -> str:
    """Freeze CA1-CA5 + the C0 document + the rule code as one bundle; returns the bundle hash."""
    if not approved or not approved.strip():
        raise PermissionError("freeze refused: no approval note (who approved, where)")
    if set(registrations) != set(REVIEWS):
        raise ValueError(f"exactly {REVIEWS} must be frozen together")
    d = load()
    if d.get("bundle"):
        raise PermissionError("already frozen; a change is a new, separately approved registration")
    REG_DIR.mkdir(exist_ok=True)
    files: dict[str, str] = {}
    for rid, text in registrations.items():
        (REG_DIR / f"{rid}.md").write_text(text)
        files[f"canada/registrations/{rid}.md"] = sha256_text(text)
    (REG_DIR / "C0_document.md").write_text(document)
    files["canada/registrations/C0_document.md"] = sha256_text(document)
    for rel in RULE_CODE:
        files[rel] = sha256_text((REPO / rel).read_text())
    bundle = _bundle_sha(files)
    d["bundle"] = {"sha256": bundle, "files": files, "approved": approved, "frozen_on": day}
    for rid in REVIEWS:
        d["reviews"][rid].update(status="FROZEN", registration=f"registrations/{rid}.md",
                                 sha256=files[f"canada/registrations/{rid}.md"], bundle_sha256=bundle)
    save(d)
    return bundle


def verify() -> list[str]:
    """[] while nothing frozen has changed; otherwise the changed or missing files."""
    b = load().get("bundle")
    if not b:
        return []
    bad = [rel for rel, h in b["files"].items()
           if not (REPO / rel).exists() or sha256_text((REPO / rel).read_text()) != h]
    if not bad and _bundle_sha(b["files"]) != b["sha256"]:
        bad.append("bundle record")
    return bad


def seal_broken() -> bool:
    h = load().get("holdout") or {}
    return (not h.get("sealed", True)) and bool(h.get("approved_by")) and bool(h.get("broken_on"))


def assert_research_dates(start: str, end: str) -> None:
    """Research code must call this before reading prices; the holdout is refused while sealed."""
    if (end >= HOLDOUT_START or start >= HOLDOUT_START) and not seal_broken():
        raise HoldoutSealed(f"{start}..{end} reaches into the sealed holdout ({HOLDOUT_START} onward)")
