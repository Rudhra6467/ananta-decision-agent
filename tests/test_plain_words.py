"""Plan 2.3: plain words everywhere. Internal codes (E4, H07, T3, P02, V02, TK3...) must never reach a screen.

1. The service's rewriter turns codes in sentences and labels into display names and keeps pure identifiers for the app.
2. No screen in the app has a code written into its text.
3. Every /v3 answer passes through the rewriter (the middleware is installed).
"""
import re
from pathlib import Path

from jarvis.service import plain

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app"
CODE = re.compile(r"\b(E\d{1,2}|H\d{2}|T\d{1,2}|P\d{2}|V\d{2}|TK\d+)\b")


def test_sentences_carry_names_not_codes():
    cases = {
        "BTC: Momentum continuation (E4) has all its conditions met.": "BTC: Momentum continuation has all its conditions met.",
        "Waiting for 20 live E5 trades.": "Waiting for 20 live squeeze breakout trades.",
        "T3 live tracking": "Trend portfolio live tracking",
        "Dip setups E6-E8 are watched only": "Dip setups are watched only",
        "yes (V02)": "yes",
        "the dip trade (H07-T30) has given 2 signals": "the dip trade has given 2 signals",
        "Correlated positions follow P02": "Correlated positions follow moves that go together count as one bet",
    }
    for raw, want in cases.items():
        got = plain.text(raw)
        assert got == want, (raw, got)
        assert not CODE.search(got), got


def test_identifiers_are_kept_for_the_app_and_named_by_the_dictionary():
    out = plain.scrub({"id": "BCH-1791504000-E6-86", "setup": "E1", "why": "seen: E8", "link": "/trade/X-E6-1"})
    assert out["id"] == "BCH-1791504000-E6-86" and out["setup"] == "E1" and out["link"] == "/trade/X-E6-1"
    assert not CODE.search(out["why"])
    for code in ("E1", "E4", "E6", "H07", "T3", "T30", "V02", "P02", "TK13"):
        assert not CODE.search(plain.name(code)), (code, plain.name(code))


def test_old_name_becomes_ananta():
    assert plain.text("Jarvis evidence trade") == "Ananta evidence trade"


def test_no_screen_has_a_code_in_its_text():
    bad = []
    for p in list((APP / "app").rglob("*.tsx")) + list((APP / "src").rglob("*.ts*")):
        if p.name == "names.ts":                                     # the dictionary itself
            continue
        for n, line in enumerate(p.read_text().split("\n"), 1):
            code_part = line.split("//")[0] if "://" not in line else line
            for lit in re.findall(r'"([^"\n]*)"|`([^`\n]*)`|>([^<>{}\n]+)<', code_part):
                text = next((x for x in lit if x), "")
                text = re.sub(r"\d{4}-\d\d-\d\dT\d", "", text)          # a date-time like 2026-10-05T12:00
                if " " in text and CODE.search(text):
                    bad.append(f"{p.relative_to(APP)}:{n}: {text[:80]}")
    assert not bad, "codes written into screens:\n" + "\n".join(bad)


def test_every_v3_answer_goes_through_the_rewriter():
    from jarvis.service import app as A
    assert any(getattr(m, "kwargs", {}).get("dispatch").__name__ == "plain_words" for m in A.app.user_middleware
               if getattr(m, "kwargs", {}).get("dispatch")), "plain_words middleware missing"
