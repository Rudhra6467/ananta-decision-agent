"""The change book Ananta reads about itself (docs/knowledge/changes.jsonl; jarvis/selfknow.py). Madhav, 5 Nov 2026: "how much Ananta does
know about what we did here in the back end? That should always be there."

Every line is well formed and in date order, and no code commit goes without its line: the shared commit-msg hook asks for one, and this
test catches a commit made with --no-verify (the newest code commit not marked "No-change-line:" is no newer than the newest line)."""
import json
import re
import subprocess
from pathlib import Path

from jarvis import selfknow

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(r"sk-ant-|api[_-]?key\s*[:=]|BEGIN [A-Z ]*PRIVATE KEY|token\s*[:=]\s*\w{8,}|password\s*[:=]", re.I)


def _rows() -> list[dict]:
    return [json.loads(x) for x in selfknow.CHANGES.read_text().splitlines() if x.strip()]


def test_every_line_is_well_formed_and_in_date_order():
    rows = _rows()
    assert len(rows) >= 100
    for r in rows:
        assert set(r) == set(selfknow.KEYS), r
        assert re.fullmatch(r"2026-\d\d-\d\d", r["date"]), r
        assert r["market"] in selfknow.MARKETS and r["area"] in selfknow.AREAS and r["status"] in selfknow.STATUSES, r
        assert 20 <= len(r["words"]) <= 600 and isinstance(r["commits"], list), r
        assert not SECRET.search(json.dumps(r)), r
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates)


def test_no_code_commit_without_its_line():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "log", "-40", "--format=%x1e%cs%x1f%B", "--", "jarvis", "scripts"],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return
    newest = max(r["date"] for r in _rows())
    for rec in out.split("\x1e"):
        if not rec.strip():
            continue
        day, body = rec.split("\x1f", 1)
        if "No-change-line:" in body:
            continue
        assert day.strip() <= newest, f"a code commit of {day.strip()} has no line in the change book (its newest line is {newest})"
        break


def test_ananta_finds_its_own_changes_in_the_real_book():
    selfknow._CACHE.clear()
    hits = selfknow.search("do you start speaking while you're still writing the answer")
    assert hits and any(r["area"] == "voice" for r in hits[:3])
