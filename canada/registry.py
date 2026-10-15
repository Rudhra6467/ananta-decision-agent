"""Canada's own registry (namespace CA): review status, frozen registration hashes, the holdout seal.

It is a separate file from crypto's strategy_status.json on purpose: Canada shares no files with crypto.
  load() / save()              the registry
  freeze(rid, text, approved)  write the registration verbatim + its SHA-256; refused without an approval note
  verify()                     every frozen registration still matches its hash
  seal_broken()                True only after Madhav's recorded approval to open the holdout
  assert_research_dates(a, b)  research code calls this; dates in the holdout are refused while sealed
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canada.paths import HOLDOUT_START

ROOT = Path(__file__).resolve().parent
REG_PATH = ROOT / "registry" / "canada_status.json"
REG_DIR = ROOT / "registrations"
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


def freeze(rid: str, text: str, approved: str, day: str) -> str:
    """Freeze a registration once Madhav has approved it; returns its hash. Refused if already frozen."""
    if not approved or not approved.strip():
        raise PermissionError("freeze refused: no approval note (who approved, where)")
    d = load()
    r = d["reviews"][rid]
    if r.get("sha256"):
        raise PermissionError(f"{rid} is already frozen; a change is a new registration, not an edit")
    REG_DIR.mkdir(exist_ok=True)
    f = REG_DIR / f"{rid}.md"
    f.write_text(text)
    h = sha256_text(text)
    r.update(status="FROZEN", registration=f"registrations/{rid}.md", sha256=h, approved=approved, frozen_on=day)
    save(d)
    return h


def verify() -> list[str]:
    """Every frozen registration's file still hashes to its recorded value."""
    bad = []
    for rid, r in load()["reviews"].items():
        if r.get("sha256"):
            f = ROOT / r["registration"]
            if not f.exists() or sha256_text(f.read_text()) != r["sha256"]:
                bad.append(rid)
    return bad


def seal_broken() -> bool:
    h = load().get("holdout") or {}
    return (not h.get("sealed", True)) and bool(h.get("approved_by")) and bool(h.get("broken_on"))


def assert_research_dates(start: str, end: str) -> None:
    """Research code must call this before reading prices; the holdout is refused while sealed."""
    if (end >= HOLDOUT_START or start >= HOLDOUT_START) and not seal_broken():
        raise HoldoutSealed(f"{start}..{end} reaches into the sealed holdout ({HOLDOUT_START} onward)")
