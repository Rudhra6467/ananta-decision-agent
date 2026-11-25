"""25 Nov 2026: NC1 (after news, does a confirmed move continue or fade?) is a study only, by Madhav's word. The one map names its place, so
its VALIDATED rows read as "noted, not used" and are not raised as a decision still waiting for him."""
from jarvis.india import knowledgemap


def test_nc1_is_noted_not_used():
    role = knowledgemap.PAPER_LINKS["NC1"]
    assert "study only" in role and "not used in any paper rule" in role
