"""Oct 15: a repair-shop request is filed only when the person asked to flag something (or said yes to the offer). The agent exams
had filed placeholders, "duplicate check" notes and flags nobody asked for (#53-#69)."""
import json

from jarvis.service import ask


def _filing(j, question):
    seen = {}

    def fake(s, h, u, t, log):
        seen["out"] = t.call("log_request", {"kind": "idea", "text": f"test request for: {question}"})
        return json.dumps({"kind": "answer", "answer": "ok"}), {"in": 1, "out": 1}

    ask.Ask(j, providers={"gemini": fake}).ask("o", question, mode="everyday")
    n = j.db.execute("SELECT COUNT(*) FROM owner_requests WHERE text LIKE ?", (f"%{question}%",)).fetchone()[0]
    return seen["out"], n


def test_no_flag_words_no_request():
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    out, n = _filing(j, "What win rate did the E9 setup have in 2019?")
    assert "error" in out and "Not filed" in out["error"] and n == 0
    out, n = _filing(j, "That answer was wrong, flag it for the repair shop")
    assert out.get("num") and n == 1
    out, n = _filing(j, "yes please")                        # yes to the offer
    assert out.get("num") and n == 1
