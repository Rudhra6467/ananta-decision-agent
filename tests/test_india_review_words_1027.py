"""27 Oct morning review: two reporting lines read badly ("Ananta ;" with no value, "1 sessions", "the 72th percentile").
Reporting only; no paper rule is touched."""
from india.morning import league_part
from india.readmodel import percentile_words


def test_league_part_without_ananta_value_says_so():
    x = {"sessions": 1, "HINDSIGHT": 0.0344, "MARKET": -0.0502, "ANANTA": None, "coverage": {"TAKEN": 4, "PASSED": 0, "NOT_COVERED": 14}}
    s = league_part("5", x)
    assert "Ananta no pick scored yet;" in s
    assert "(1 session)" in s and "1 sessions" not in s
    assert "Ananta ;" not in s


def test_league_part_with_value_unchanged_shape():
    x = {"sessions": 5, "HINDSIGHT": 0.0258, "MARKET": -0.0131, "ANANTA": -0.0123, "ananta_pct_vs_random": 0.5,
         "coverage": {"TAKEN": 23, "PASSED": 7, "NOT_COVERED": 58}}
    assert league_part("1", x) == ("H1 (5 sessions): hindsight +2.58%, market -1.31%, Ananta -1.23%, Ananta at the 50% point of random; "
                                   "of the best rises: took 23, passed 7, not covered 58")


def test_percentile_ordinals():
    assert percentile_words(0.72).endswith("72nd percentile of random.")
    assert "1st" in percentile_words(0.01) and "11th" in percentile_words(0.11) and "13th" in percentile_words(0.13)
    assert "23rd" in percentile_words(0.23) and "50th" in percentile_words(0.5)
    assert "not scored" in percentile_words(None)
