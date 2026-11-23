"""23 Nov 2026 (Madhav's cost review): the four big fact sections go to the model only when the question is about them."""
from jarvis.india import ask

F = {"teacher_libraries": ["x"] * 50, "technicals": {"rsi": 1}, "account_allocation": {"h": 1}, "reference_traders_league": {"l": 1},
     "brief": ["Nifty 25,801"], "index_line_sp1": {"x": 1}}


def test_an_options_question_leaves_the_big_four_out():
    out = ask.lean_facts(F, "How did the options line do today?")
    for k in ask.LEAN_TOPICS:
        assert isinstance(out[k], str) and out[k].startswith("(left out")
    assert out["brief"] == F["brief"] and out["index_line_sp1"] == F["index_line_sp1"]


def test_each_topic_brings_its_section():
    assert ask.lean_facts(F, "what does the RSI say about Nifty?")["technicals"] == F["technicals"]
    assert ask.lean_facts(F, "how is my portfolio doing?")["account_allocation"] == F["account_allocation"]
    assert ask.lean_facts(F, "what did the teachers' library say about breakouts?")["teacher_libraries"] == F["teacher_libraries"]
    assert ask.lean_facts(F, "how do we compare with the reference traders?")["reference_traders_league"] == F["reference_traders_league"]


def test_the_original_is_not_changed():
    ask.lean_facts(F, "hello")
    assert F["technicals"] == {"rsi": 1}
