"""The crypto lock (docs/LOCK.md, docs/knowledge/crypto_lock.json): what must not change during the evidence window without
Madhav's recorded yes.

Each pin is a sha256 over what it freezes. For code the hash covers the lines of code only: comments, docstrings, blank lines and
trailing spaces do not count, so a note can be corrected; a changed number, name or line of logic does. Data files (json) are hashed whole,
and the research rules by their headings. When a pin fails, a frozen rule was changed. Either undo the change, or - Madhav's decision
only - add an entry to that pin's `history` in crypto_lock.json with his approval, a note quoting what he decided, and the new hash.
The test checks that the pin, the newest history entry and the live file agree, so a re-pin without a recorded approval fails too.

    python tests/test_crypto_lock.py        # prints the current hash of every pin (to copy into a recorded decision)
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs" / "knowledge" / "crypto_lock.json"


def _sha(text: str) -> str:
    norm = "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").split("\n")).strip("\n") + "\n"
    return hashlib.sha256(norm.encode()).hexdigest()


def _src(rel: str) -> str:
    return (ROOT / rel).read_text()


def _clean(src: str) -> str:
    """Python source without comments, docstrings, blank lines and trailing spaces - the lines of code only."""
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
    """The code of the named top-level definitions or assignments of a file, in the order given (comments and docstrings left out)."""
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


def _json(rel: str, fn=lambda d: d) -> str:
    return json.dumps(fn(json.loads(_src(rel))), sort_keys=True, indent=1)


def _headings(rel: str) -> str:
    return "\n".join(line for line in _src(rel).split("\n") if line.startswith("#"))


def current() -> dict[str, str]:
    """The hash of every pin as the files stand now."""
    status = lambda d: {  # noqa: E731
        "strategies": {k: {x: v.get(x) for x in ("status", "verdict", "wakes_brain")} for k, v in d["strategies"].items()},
        "evidence_window": d["evidence_window"], "account": d["account"]}
    gate = lambda d: [{x: c.get(x) for x in ("id", "area", "check", "measure", "pass_mark")} for c in d["checks"]]  # noqa: E731
    return {
        "book500_rules": _sha(_code("src/research/book500.py")),
        "exposure_dial": _sha(_code("src/research/review25.py") + "\n#--\n" + _top("jarvis/service/exposure.py", ["START", "BOOKS", "ROLE"])),
        "measured_edges": _sha(_json("docs/research/review26.json") + "\n#--\n" + _json("docs/research/review29.json")),
        "paper_costs": _sha(_top("src/intelligence/ndax_costs.py", ["NDAX_FEE", "HALF_SPREAD", "DEFAULT_HS", "EXPENSIVE_HS"]) + "\n#--\n"
                            + _top("jarvis/service/registry.py", ["TIER_A", "FLOOR", "NDAX_FEE", "cost"]) + "\n#--\n"
                            + _top("src/intelligence/paper_exit.py", ["COST_PROFILES"])),
        "t3_rule": _sha(_code("src/intelligence/portfolio_layer.py")),
        "strategy_verdicts": _sha(_json("docs/knowledge/strategy_status.json", status)),
        "gate_definition": _sha(_json("docs/knowledge/acceptance_gate.json", gate)),
        "exam_judges": _sha(_top("jarvis/service/exam.py", ["KNOWS", "WHY", "WHY_PASS", "UNKNOWNS", "DONT_KNOW", "CONSISTENCY",
                                                           "REASON", "VOICE", "judge_known", "judge_unknown", "label", "judge_pair"])),
        "research_rules": _sha(_headings("docs/research/RESEARCH_RULES.md")),
        # Oct 15, after the independent check: the logic that decides money or the verdict and sat outside the nine pins
        "live_logic": _sha("\n#--\n".join([
            _top("jarvis/service/exposure.py", ["state", "dial_by_day"]),                       # how the dial is read and used
            _top("jarvis/service/ndax_book.py", ["passed_rules", "edge_signals"]),               # what may enter the $500 book's edge sleeve
            _top("jarvis/service/trade_guard.py", ["LIVE_PRICE_S", "BAR_PRICE_S", "DAILY_S", "FAIL_MEMORY_S", "PATHS"]),
            _top("jarvis/service/exam.py", ["KNOWS_PASS", "UNKNOWNS_PASS", "VOICE_PASS", "run", "rejudge", "voice"]),  # the pass marks
            _top("jarvis/service/evidence_live.py", ["EXAM_FRESH_DAYS", "_exam_age", "SIZING_ENTRIES", "CITES_N", "CITES_PASS",
                                                      "OUTAGE_MIN", "ALERT_WITHIN_S", "GOAL_EVENTS"]),
            # Oct 20, Madhav "2. yes": engine_execution against the worker's independent NDAX quote, and the realism test it rests on
            _top("jarvis/service/evidence_live.py", ["EXEC_SINCE", "EXEC_FILLS", "EXEC_ACHIEVABLE", "EXEC_MEDIAN_BPS", "execution_reading"]),
            _top("jarvis/service/realism.py", ["NDAX_FEE", "TOLERANCE_BPS", "MAX_QUOTE_GAP_S", "optimism_bps", "score"]),
            _top("jarvis/service/ev.py", ["fidelity"]),                                          # Rule A's "within 3 points"
            _top("src/intelligence/paper_exit.py", ["settings_for"]),                            # which cost profile a book gets by default
            _json("docs/knowledge/acceptance_gate.json", lambda d: [{x: c.get(x) for x in ("id", "status")} for c in d["checks"]]),
        ])),
    }


def _lock() -> dict:
    return json.loads(LOCK.read_text())


def test_every_pin_matches_the_files_and_its_recorded_approval():
    lock, now = _lock(), current()
    assert set(lock["pins"]) == set(now), "a pin was added or dropped without a recorded decision"
    for name, pin in lock["pins"].items():
        hist = pin["history"]
        assert hist, f"{name}: no recorded approval"
        for h in hist:
            assert h["approved_by"] == "Madhav (in chat)" and len(h["note"]) >= 20 and '"' in h["note"] \
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", h["date"]), \
                f"{name}: every history entry needs the date, approved_by exactly 'Madhav (in chat)' and a note quoting his words"
        assert pin["sha256"] == hist[-1]["sha256"], f"{name}: the pin and its newest recorded approval differ"
        assert now[name] == pin["sha256"], (
            f"FROZEN: {name} changed ({pin['what']}). The evidence window is running. If Madhav decided this, add a history entry to "
            f"docs/knowledge/crypto_lock.json with his approval and the new hash {now[name]}; otherwise undo the change.")


def test_the_lock_names_what_each_pin_freezes_and_where_the_page_is():
    lock = _lock()
    assert (ROOT / "docs" / "LOCK.md").exists() and (ROOT / "docs" / "GRANTS.md").exists()
    for name, pin in lock["pins"].items():
        assert pin["what"] and pin["files"], name
        for f in pin["files"]:
            assert (ROOT / f).exists(), f"{name}: {f} is gone"
    text = (ROOT / "docs" / "LOCK.md").read_text()
    for name in lock["pins"]:
        assert f"`{name}`" in text, f"docs/LOCK.md does not list the frozen item `{name}`"


def test_a_code_pin_ignores_notes_and_catches_changes():
    base = 'X = 1.5  # why\n\ndef f(a):\n    """doc"""\n    return a * X  # note\n'
    notes = '"""module words"""\nX = 1.5\n\n\ndef f(a):\n    """other doc\n    over two lines"""\n    # a new comment\n    return a * X   \n'
    number = base.replace("1.5", "1.6")
    logic = base.replace("a * X", "a + X")
    assert _sha(_clean(base)) == _sha(_clean(notes))
    assert _sha(_clean(base)) != _sha(_clean(number))
    assert _sha(_clean(base)) != _sha(_clean(logic))


if __name__ == "__main__":
    json.dump(current(), sys.stdout, indent=1)
    print()
