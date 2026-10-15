"""Oct 15 incident guard: a table that ever gets ALTER TABLE ... ADD COLUMN must never be written with a bare
`INSERT INTO t VALUES (...)`, because the added column shifts every position (206 brain decisions were lost that way)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALTER = re.compile(r"ALTER TABLE\s+([A-Za-z_][A-Za-z0-9_]*)\s+ADD COLUMN", re.I)
BARE = re.compile(r"INSERT(?:\s+OR\s+[A-Z]+)?\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\s+VALUES", re.I)


def _sources():
    for g in ("jarvis/**/*.py", "src/**/*.py", "canada/**/*.py"):
        for p in ROOT.glob(g):
            if "__pycache__" not in p.parts:
                yield p


def test_no_positional_insert_into_a_table_that_gains_columns():
    texts = {p: p.read_text(errors="ignore") for p in _sources()}
    altered = {m.group(1).lower() for t in texts.values() for m in ALTER.finditer(t)}
    assert {"brain_decisions", "ask_messages", "owner_requests", "missed_moves"} <= altered, altered
    bad = [f"{p.relative_to(ROOT)}: INSERT INTO {m.group(1)} VALUES" for p, t in texts.items()
           for m in BARE.finditer(t) if m.group(1).lower() in altered]
    assert not bad, "name the columns: " + "; ".join(bad)
