"""The Trading Knowledge Library (src/research/library.py, Oct 16) is research material: external teaching, hypotheses only.
Nothing that trades, decides, answers as the agent or scores the gate may read it (the crypto lock's Rule B: no new crypto
strategies during the evidence window; the research rules: a teacher's idea is never evidence)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nothing_in_the_agent_reads_the_library():
    bad = []
    for base in ("jarvis", "src/intelligence", "worker", "canada"):
        for p in (ROOT / base).rglob("*.py"):
            t = p.read_text(errors="ignore")
            if "docs/library" in t or "research.library" in t or "research import library" in t:
                bad.append(str(p.relative_to(ROOT)))
    assert not bad, f"these read the knowledge library: {bad}"


def test_transcripts_never_reach_the_repo():
    from src.research import library

    assert str(library.WORK).startswith(str(Path.home())) and "ananta_runs" in str(library.WORK)
    assert str(library.TX).startswith(str(Path.home()))
    out = ROOT / "docs" / "library"
    if out.exists():
        assert not list(out.rglob("*.vtt")) and not list(out.rglob("*.json")), "only paraphrased chapters belong in docs/library"


def test_every_concept_file_gathers_known_topics():
    from src.research import library

    for name, tops in library.FILES:
        assert tops and all(t in library.TOPICS for t in tops), name
    assert {t for _, tops in library.FILES for t in tops} == set(library.TOPICS)   # every topic lands in one chapter
