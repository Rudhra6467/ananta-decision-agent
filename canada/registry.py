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


def propose_amendment(rel: str, reason: str, criteria_changed: bool, day: str) -> dict:
    """Record a change to a frozen file as PENDING; it counts only once Madhav approves it (approve_amendment).
    The original bundle hash is never rewritten; amendments sit beside it, each with old and new hashes."""
    d = load()
    b = d.get("bundle") or {}
    if rel not in (b.get("files") or {}):
        raise ValueError(f"{rel} is not in the frozen bundle")
    am = d.setdefault("amendments", [])
    a = {"id": f"A{len(am) + 1}", "file": rel, "old_sha256": _current_expected(d, rel),
         "new_sha256": sha256_text((REPO / rel).read_text()), "reason": reason,
         "criteria_changed": criteria_changed, "proposed_on": day, "approved": None, "approved_on": None}
    am.append(a)
    save(d)
    return a


def approve_amendment(aid: str, approved: str, day: str) -> dict:
    if not approved or not approved.strip():
        raise PermissionError("approval refused: no approval note (who approved, where)")
    d = load()
    a = next(x for x in d.get("amendments", []) if x["id"] == aid)
    if sha256_text((REPO / a["file"]).read_text()) != a["new_sha256"]:
        raise PermissionError(f"{a['file']} changed again after {aid} was proposed; propose a new amendment")
    a.update(approved=approved, approved_on=day)
    save(d)
    return a


def _current_expected(d: dict, rel: str) -> str:
    """The hash a frozen file must have now: the bundle's, or the latest APPROVED amendment's."""
    h = d["bundle"]["files"][rel]
    for a in d.get("amendments", []):
        if a["file"] == rel and a.get("approved"):
            h = a["new_sha256"]
    return h


def verify() -> list[str]:
    """[] while every frozen file matches its bundle hash or its latest approved amendment."""
    d = load()
    b = d.get("bundle")
    if not b:
        return []
    bad = [rel for rel in b["files"]
           if not (REPO / rel).exists() or sha256_text((REPO / rel).read_text()) != _current_expected(d, rel)]
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
