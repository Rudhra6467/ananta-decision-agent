"""12 Nov 2026 (the interim outside review of the keen audit's repairs): repair 4's copy held seven stale copies of repair 1's change-book
lines, two of them "built" and five "live" with no commit, which a merge would have carried into the live book (G-73's kind again). The
change book is read by both voices and replaced line by line on its first 60 characters, so no two lines may share them; and from the
audit repairs on (12 Nov), a line that says "live" names the commit that carries it. Copied into tests/ of the live checkout when repair
2 goes live (13 Nov)."""
import json
from collections import Counter
from pathlib import Path

BOOK = Path(__file__).resolve().parents[1] / "docs" / "knowledge" / "changes.jsonl"


def _rows():
    return [json.loads(x) for x in BOOK.read_text().splitlines() if x.strip()]


def test_no_two_change_book_lines_share_their_key():
    keys = Counter(r["words"][:60] for r in _rows())
    assert [k for k, n in keys.items() if n > 1] == []


def test_every_live_line_from_the_audit_repairs_on_names_its_commit():
    assert [r["words"][:60] for r in _rows() if r["date"] >= "2026-11-12" and r.get("status") == "live" and not r.get("commits")] == []


def test_the_change_book_is_in_date_order():
    dates = [r["date"] for r in _rows()]
    assert [i for i in range(1, len(dates)) if dates[i] < dates[i - 1]] == []
