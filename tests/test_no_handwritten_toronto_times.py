"""Independent audit, 2 Nov 2026: Toronto clock times written by hand into what Ananta says ("22:30 Toronto", "the 7 pm Toronto run") went
stale at the clock change, and some were never right. Job times are read from the launchd jobs (jarvis/india/schedule.py). This test fails if a
string Ananta can say names a Toronto clock time by hand again. Historical events ("the 27 Oct stall, 11:40-12:37 Toronto") are dated, so allowed."""
import ast
import io
import pathlib
import re
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = [p for p in (ROOT / "jarvis" / "india").glob("*.py") if p.name not in ("schedule.py", "neveragain.py")]
CLOCK = re.compile(r"(?<![\\\w])\d{1,2}(?::\d{2})?\s?(?:am|pm)?\s+Toronto\b|\(\d{1,2}:\d{2} Toronto\)", re.I)
DATED = re.compile(r"\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b|\d{1,2}:\d{2}-\d{1,2}:\d{2} Toronto|in (?:winter|summer)")


def _docstring_lines(path: pathlib.Path) -> set[int]:
    out = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
                out.add(first.lineno)
    return out


def _strings(path: pathlib.Path):
    for tok in tokenize.generate_tokens(io.StringIO(path.read_text()).readline):
        if tok.type == tokenize.STRING or getattr(tokenize, "FSTRING_MIDDLE", -1) == tok.type:
            yield tok.start[0], tok.string


def test_no_handwritten_toronto_clock_times_in_what_ananta_says():
    bad = []
    for p in FILES:
        docs = _docstring_lines(p)
        for line, s in _strings(p):
            if line in docs:
                continue                                # docstrings describe; they are not said
            if CLOCK.search(s) and not DATED.search(s):
                bad.append(f"{p.name}:{line}: {s[:120]}")
    assert not bad, "hand-written Toronto times (use jarvis.india.schedule.at):\n" + "\n".join(bad)


def test_day_words_are_read_from_the_jobs(tmp_path, monkeypatch):
    import plistlib
    from jarvis.india import schedule
    monkeypatch.setattr(schedule, "AGENTS", tmp_path)
    (tmp_path / "com.ananta.india.paper.plist").write_bytes(plistlib.dumps({"StartCalendarInterval": {"Hour": 21, "Minute": 30}}))
    assert schedule.at("com.ananta.india.paper").startswith("9:30 pm Toronto (")
    w = schedule.day_words()
    assert "9:30 pm Toronto" in w and "practice book's picks" in w and "7 pm" not in w
