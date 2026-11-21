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


def test_every_commit_a_live_audit_line_names_is_a_real_commit():
    """21 Nov 2026 (the outside lock review): four lines named words instead of commits, five named only a commit that changed the change
    book, and one named the wrong repo's commit, while the check above only asked that the field be filled. Every id of a live line from
    12 Nov on must now be a commit that git finds in one of the checkouts beside this one (the agent's, the records', the old backend's;
    an optional "records " prefix). The records checkout is not named here: the India firewall's static scan allows its name only in
    listed files."""
    import re
    import subprocess

    home = BOOK.parents[3]                                      # ~/code (the tests may move HOME)
    repos = [BOOK.parents[2]] + sorted(p for p in home.iterdir() if p.is_dir() and (p / ".git").exists())   # every checkout beside this one

    def found(h: str) -> bool:
        return any(subprocess.run(["git", "-C", str(r), "cat-file", "-e", h + "^{commit}"], capture_output=True).returncode == 0 for r in repos)

    bad = []
    for r in _rows():
        if r["date"] < "2026-11-12" or r.get("status") != "live":
            continue
        for c in r.get("commits") or []:
            m = re.fullmatch(r"(?:records |backend )?([0-9a-f]{7,40})", str(c))
            if not m or not found(m.group(1)):
                bad.append((r["date"], r["words"][:50], c))
    assert bad == []
