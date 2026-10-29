"""28 Oct 2026 (Madhav's voice session and his notification request): the grader question asked once, the Whisper names for the grader, spoken
clarify choices, one hedge per answer, the screen moving only when asked, what waits for his yes, approve-all drafts, and the watchdog's restart."""
import importlib.util
import json
from pathlib import Path

from jarvis.india import ask, speaker
from jarvis.service import waiting

ROOT = Path(__file__).resolve().parents[1]


def _watchdog():
    spec = importlib.util.spec_from_file_location("jw", ROOT / "scripts" / "jarvis_watchdog.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_one_hedge_keeps_only_the_first():
    a = "As far as I know, NSE has weekly expiries. Stock options are physically settled, as far as I know, so close them."
    out = ask.one_hedge(a)
    assert out.lower().count("as far as i know") == 1
    assert out.startswith("As far as I know, NSE")
    assert "physically settled, so close them" in out or "physically settled so close them" in out
    assert ask.one_hedge("No hedge here.") == "No hedge here."


def test_clarify_options_are_spoken():
    r = ask.finish({"kind": "clarify", "answer": "Could you say which of these it is?", "options": ["Repeat the last answer", "Next question"]}, "holder", model=True)
    assert "1. Repeat the last answer." in r["answer"] and "2. Next question." in r["answer"]
    r2 = ask.finish({"kind": "clarify", "answer": "Do you mean Repeat the last answer or Next question?", "options": ["Repeat the last answer", "Next question"]}, "x", model=True)
    assert "1." not in r2["answer"]


def test_screen_moves_only_when_asked():
    assert ask.ASKS_TO_SEE.search("show me the evidence tab")
    assert ask.ASKS_TO_SEE.search("open my flags")
    assert not ask.ASKS_TO_SEE.search("I will be approving all those things that we are waiting for in the evidence")


def test_grader_whisper_names_and_is_asking():
    assert speaker.observer("great rai")["id"] == "grader"
    r = speaker.route("t-gr", "Ananta, the Great Rai is asking questions. Start.")
    assert r and r["kind"] == "handover" and r["person"]["id"] == "grader"


def test_affirm_rest_carries_the_next_question():
    assert speaker.affirm_rest("Yes, you're speaking with me.") == ""
    rest = speaker.affirm_rest("Yes, still the greater, and that's a pass. Question 30. What is theta?")
    assert rest is not None and rest.startswith("Question 30")
    assert speaker.affirm_rest("What is theta?") is None


def test_grader_question_kept_asked_after_madhav_speaks(tmp_path, monkeypatch):
    monkeypatch.setattr(ask, "ASK_DIR", tmp_path)
    speaker.stranger_tick("th1")
    speaker.stranger_mark_asked("th1")
    speaker.stranger_reset("th1")                     # Madhav's voice in between
    assert speaker.stranger_tick("th1")["asked"] is True


def test_accountish_only_for_account_talk():
    assert ask.ACCOUNTISH.search("how is my portfolio doing")
    assert not ask.ACCOUNTISH.search("What is the difference between a call option and a put option?")


def test_waiting_line_words():
    items = [{"kind": "drafts", "count": 12, "title": "12 research drafts wait"}, {"kind": "flag_pick", "count": 1, "title": "Flag 49: pick a fix"}]
    assert waiting.line(items) == "12 research drafts and flag 49 are waiting for your yes."
    assert waiting.line([{"kind": "flag_pick", "count": 1, "title": "Flag 50: pick a fix"}]) == "Flag 50 is waiting for your yes."


def test_waiting_flow_and_nudge(tmp_path, monkeypatch):
    monkeypatch.setattr(ask, "ASK_DIR", tmp_path)
    w = {"items": [{"id": "india:drafts", "kind": "drafts", "count": 12, "title": "12 research drafts wait for your yes or skip", "line": "", "say": ""}],
         "count": 12, "key": "k1", "line": "12 research drafts are waiting for your yes."}
    r = ask.waiting_flow("What's waiting for me?", w)
    assert r and "12 things wait" in r["answer"] and "approve all drafts" in r["answer"]
    assert ask.waiting_flow("What is the waiting period for ELSS?", w) is None
    n1 = ask.waiting_nudge("thread-a", w)
    assert "12 research drafts are waiting" in n1 and "approve all drafts" in n1
    assert ask.waiting_nudge("thread-a", w) == ""          # once per conversation
    assert ask.waiting_nudge("thread-b", w) == ""          # and not again for 3 hours for the same list


def test_bulk_drafts(tmp_path, monkeypatch):
    rows = [{"n": 1, "key": "k1", "type": "MISS_PATTERN", "day": "2026-10-27", "words": "a"}, {"n": 2, "key": "k2", "type": "REVIEW_TAG", "day": "2026-10-27", "words": "b"}]
    monkeypatch.setattr(ask.views, "drafts", lambda: {"drafts": rows})
    monkeypatch.setattr(ask, "DATA", tmp_path)
    assert ask.bulk_draft_flow("How do I approve all drafts?", "owner") is None
    loose = ask.bulk_draft_flow("I will be approving all those things that we are waiting for in the evidence, I approve them", "owner")
    assert loose and "to be sure" in loose["answer"] and not (tmp_path / "paper" / "reconstruction" / "decisions.jsonl").exists()
    done = ask.bulk_draft_flow("Approve all drafts", "owner")
    assert done and "all 2 drafts" in done["answer"]
    lines = (tmp_path / "paper" / "reconstruction" / "decisions.jsonl").read_text().splitlines()
    assert [json.loads(x)["decision"] for x in lines] == ["APPROVED", "APPROVED"]
    assert ask.bulk_draft_flow("approve all drafts", "guest:a@b.c")["answer"] == "Only Madhav decides on drafts."


def test_waiting_remind_tells_new_once(tmp_path, monkeypatch):
    monkeypatch.setattr(waiting, "STATE", tmp_path / "w.json")
    items = [{"id": "india:drafts", "kind": "drafts", "count": 3, "title": "3 research drafts wait", "line": ""}]
    monkeypatch.setattr(waiting, "collect", lambda j, now=None: {"items": items, "count": 3, "key": "a", "line": waiting.line(items)})
    sent = []
    r1 = waiting.remind(None, push=lambda t, b: sent.append((t, b)), now=1_800_000_000)
    assert r1["sent"] and len(sent) == 1
    r2 = waiting.remind(None, push=lambda t, b: sent.append((t, b)), now=1_800_000_900)
    assert r2["sent"] is None and len(sent) == 1
    items[0]["count"] = 4                                  # a new draft arrives
    r3 = waiting.remind(None, push=lambda t, b: sent.append((t, b)), now=1_800_001_800)
    assert r3["sent"] and len(sent) == 2


def test_watchdog_restarts_after_three_looks(tmp_path, monkeypatch):
    jw = _watchdog()
    monkeypatch.setattr(jw, "STATE", tmp_path / "st.json")
    monkeypatch.setattr(jw, "STALLS", tmp_path / "stalls")
    calls, sent = [], []

    class R:
        returncode, stdout = 0, "123"

    def run(cmd, **k):
        calls.append(cmd[0])
        return R()

    def down(url):
        raise TimeoutError()
    for i in range(3):
        out = jw.main([], get=down, now=1000 + i * 300, send=lambda *a: sent.append(a) or "200", heal_run=run)
    assert out.get("healed") == "restarted" and "launchctl" in calls
    out4 = jw.main([], get=down, now=1000 + 3 * 300, send=lambda *a: "200", heal_run=run)
    assert "healed" not in out4                            # at most once an hour
    stuck = jw.look(get=lambda u: {"health_checks_s_ago": 30, "jobs_s_ago": 50 * 60})
    assert stuck[0] == "stuck"


def test_an_approval_with_a_question_answers_both():
    r = ask._and_question(ask._reply("Approved, sir: all 3 drafts go to registration.", [], []),
                          "Yeah, I will approve them all. Let's proceed. It's going to go up or down tomorrow? What's your prediction?")
    assert r["_then"].startswith("It's going to go up or down tomorrow?") and r["_prefix"].startswith("Approved, sir")
    plain = ask._reply("Approved.", [], [])
    assert ask._and_question(plain, "Approve all drafts. Confirm.") is plain
