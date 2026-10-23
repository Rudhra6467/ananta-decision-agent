"""The India lock (docs/INDIA_LOCK.md, india/registrations/india_lock.json): what must not change on India's paper books during
their evidence window without Madhav's recorded yes. Drafted 23 Oct 2026 (plan "to the review point"); the lock day itself is
about 1 Nov, when SP3's remaining parts and the SZ2 selection are in. Until then only the items already declared frozen are pinned.

Same rules as the crypto lock (tests/test_crypto_lock.py in the agent repo): a code pin covers lines of code only (comments,
docstrings and blank lines do not count), a data pin covers the file whole, a document pin its headings. When a pin fails, a frozen
rule changed: undo it, or - Madhav's decision only - append an entry to that pin's `history` (date, approved_by starting with
Madhav, a note quoting his words, the new sha256) and set the pin's sha256 to it. The test checks that the pin, its newest history
entry and the live file agree, so a re-pin without a recorded approval fails too.

    python tests/test_india_lock.py        # prints the current hash of every pin
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "india" / "registrations" / "india_lock.json"


def _sha(text: str) -> str:
    norm = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip("\n") + "\n"
    return hashlib.sha256(norm.encode()).hexdigest()


def _src(rel: str) -> str:
    return (ROOT / rel).read_text()


def _clean(src: str) -> str:
    """Python source without comments, docstrings, blank lines and trailing spaces: the lines of code only."""
    tree = ast.parse(src)
    kill: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(b[0].value.value, str):
                kill.update(range(b[0].lineno, b[0].end_lineno + 1))
    cut: dict[int, int] = {}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            cut[tok.start[0]] = tok.start[1]
    out = []
    for n, line in enumerate(src.split("\n"), 1):
        if n in kill:
            continue
        if n in cut:
            line = line[: cut[n]]
        line = line.rstrip()
        if line.strip():
            out.append(line)
    return "\n".join(out)


def _code(rel: str) -> str:
    return _clean(_src(rel))


def _top(rel: str, names: list[str]) -> str:
    """The code of the named top-level definitions or assignments of a file, in the order given."""
    src = _src(rel)
    lines = src.split("\n")
    found: dict[str, str] = {}
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            found[node.name] = "\n".join(lines[start - 1: node.end_lineno])
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            text = "\n".join(lines[node.lineno - 1: node.end_lineno])
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        found[n.id] = text
    missing = [n for n in names if n not in found]
    assert not missing, f"{rel}: {missing} not found - the lock cannot pin what has moved or been renamed"
    seen, out = set(), []
    for n in names:
        if found[n] not in seen:
            seen.add(found[n])
            out.append(_clean(found[n]))
    return "\n#--\n".join(out)


def _json(rel: str) -> str:
    return json.dumps(json.loads(_src(rel)), sort_keys=True, indent=1)


def _whole(rel: str) -> str:
    return _src(rel)


def current() -> dict[str, str]:
    """The hash of every pin as the files stand now."""
    return {
        # the stock paper book's rules: families, exits, slots, the Rs 60,000 book and the survival rules (5% day, 22% pause)
        "paper_rules": _sha(_json("india/paper_config.json")),
        # the SP1 index playbook, frozen 21 Oct (4 decision points, futures shadow, 1-lot option line)
        "sp1_playbook": _sha(_json("india/registrations/sp1_v2.json")),
        # the SP3 positional study as frozen 20 Oct (sha 20f9070f3d3a61c9 inside) and its permanent-stops list
        "sp3_spec": _sha(_json("india/registrations/sp3_v1.json") + "\n#--\n" + _whole("india/registrations/sp3_permanent_stops.csv")),
        # the SZ2 sizing study's frozen spec
        "sz2_spec": _sha(_json("india/registrations/sz2_v1.json")),
        # the cost model every paper book and study pays (v1.2, 20 Oct)
        "cost_model": _sha(_code("india/costs.py")),
        # the learning loop's rules: the league's horizons, draws, notional and classes; the missed-movers bands and families
        "learning_rules": _sha(_top("india/others.py", ["RULES", "HORIZONS", "TOP_N", "DRAWS", "NOTIONAL", "PARTICIPANTS", "LEAGUE_WINDOW", "CLASSES"])
                               + "\n#--\n" + _top("india/missed.py", ["TOP_N", "LOOKBACK_SESSIONS", "BANDS", "BASE_TIGHT", "THIN_DAY", "RESEARCH", "CONTROL"])),
        # the capital allocation rule (Madhav, 23 Oct 14:04): options Rs 50,000 fixed, stocks as in the account, the regime table, the move limits, the rating weights
        "allocation_rule": _sha(_json("india/registrations/allocation_rule_v1.json")),
        # no order path: the leak check that forbids every order call until the gate (lines of code)
        "no_order_rule": _sha(_code("india/leakcheck.py")),
    }


def test_every_pinned_india_rule_is_unchanged():
    lock = json.loads(LOCK.read_text())
    now = current()
    assert set(lock["pins"]) == set(now), f"pins differ: {sorted(set(lock['pins']) ^ set(now))}"
    bad = []
    for name, pin in lock["pins"].items():
        hist = pin.get("history") or []
        assert hist and hist[-1]["sha256"] == pin["sha256"], f"{name}: the pin and its newest history entry disagree"
        assert hist[-1]["approved_by"].startswith("Madhav"), f"{name}: a pin needs Madhav's recorded approval"
        if now[name] != pin["sha256"]:
            bad.append(f"{name}: {pin['what']}")
    assert not bad, "a frozen India rule changed (undo it, or record Madhav's decision in india_lock.json):\n  " + "\n  ".join(bad)


def test_the_lock_names_what_waits_for_lock_day():
    lock = json.loads(LOCK.read_text())
    assert lock["lock_day"]["planned"] == "2026-11-01" and lock["lock_day"]["pinned_then"], "the lock day and its pins-to-come must be stated"
    assert "INDIA_LOCK.md" in lock["what"]


if __name__ == "__main__":
    for k, v in current().items():
        print(f"{k}: {v}")
    sys.exit(0)
