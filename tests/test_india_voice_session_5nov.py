"""5 Nov 2026 voice session (Madhav): "you are just repeating yourself", and a flag message whose real request ("tell me what are the
flags that are waiting for me") was never answered."""
from jarvis.india import ask


def test_more_detail_anywhere_in_a_short_message_is_an_expand():
    for t in ["I want to know what's in detail.", "Tell me that in detail", "Give me more details please", "I want the details",
              "Can you explain more?", "Okay, elaborate on that", "explain more"]:
        assert ask.wants_detail(t) or ask.EXPAND.search(t), t


def test_a_new_subject_in_detail_is_a_new_question():
    for t in ["Tell me about Jio Financial in detail", "Explain the options line rule in detail", "What is RSI in detail?"]:
        assert not ask.wants_detail(t), t


def test_a_request_without_a_question_mark_is_answered_after_the_flag():
    t = ("Ananta, you are just repeating yourself. You just said the same answer in the above line and again you are telling the same answer. "
         "Why would I need the same answer twice? Flag that as well. And then just tell me what are the flags that are waiting for me and what are "
         "they in detail. That's what I asked. You didn't get me.")
    q = ask.other_question(t)
    assert q.startswith("And then just tell me what are the flags that are waiting for me"), q
    assert "Why would I need the same answer twice?" in q


def test_a_plain_flag_has_no_question():
    assert ask.other_question("Flag that the chart is cut off on the money screen.") == ""


def test_watchdog_restarts_a_frozen_india_service_once_with_its_stack(tmp_path, monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import jarvis_watchdog as w
    monkeypatch.setattr(w, "STALLS", tmp_path / "stalls")    # 5 Nov: the test had written a real stall file dated 2001

    class R:
        def __init__(self, out=""):
            self.stdout, self.returncode = out, 0
    ran, sent = [], []

    def run(cmd, **k):
        ran.append(cmd[0] + " " + cmd[1])
        return R("12345\n" if cmd[0] == "pgrep" else "")

    def down(*a, **k):
        raise OSError("no answer")
    st = w.india({}, 1e9, lambda *a: sent.append(a[0]) or "ok", {}, opener=down, run=run, pause=lambda s: None)
    assert ran == ["pgrep -f", "kill -USR1", "launchctl kickstart"] and sent == ["Ananta restarted the India service"] and st == {"heal_t": 1e9}
    assert w.india(st, 1e9 + 60, lambda *a: "ok", {}, opener=down, run=run, pause=lambda s: None) == st, "at most once in 20 minutes"
