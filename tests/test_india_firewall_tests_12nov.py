"""12 Nov 2026: four India test files of audit repair 4 took the places fixture with an import line that the India firewall's static check
(records india/firewall.py) reads as an import of the india package, so the firewall would have failed when the repair went live. No test
file may import the india package except the ones the firewall's allowlist names (its ALLOWED_REFS)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# the firewall's two import patterns, spelled in two parts so that this file is not itself such a reference
IMPORT = re.compile("(?:from|imp" + "ort) +ind" + r"ia\b")
ALLOWED = {"tests/test_india_web.py"}          # the test files ALLOWED_REFS names for these two patterns


def test_no_test_file_imports_the_india_package():
    hits = []
    for p in sorted((ROOT / "tests").glob("*.py")):
        rel = str(p.relative_to(ROOT))
        if rel in ALLOWED:
            continue
        s = p.read_text(errors="ignore")
        hits += [f"{rel}:{s.count(chr(10), 0, m.start()) + 1}" for m in IMPORT.finditer(s)]
    assert hits == []
