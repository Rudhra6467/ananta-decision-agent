"""The shadow trader's code guards (Phase 4.4, 30 Oct 2026): the plan is read tolerantly, the stance is forced onto the allowed list, watch names
come only from the facts, stray numbers are flagged, and the blind facts carry nothing of Ananta's plan."""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("india_shadow_trader", Path(__file__).resolve().parents[1] / "scripts" / "india_shadow_trader.py")
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)

FACTS = {"session": "2026-11-02", "setup": {"scenarios": {"bull": 0.4, "bear": 0.33, "neutral": 0.27}, "nifty_prev_close": 22937.0},
         "overnight": {"india": {"Nifty": {"close": 22937.0}}}, "lines": {"view": ["Nifty closed at 22,937 (+1.0%)", "holdings: LICI, MARICO"]}}


def _guard(plan: dict, f: dict) -> dict:
    """The same guards main() applies, lifted here so they can be tested without the service."""
    import re
    if plan.get("stance") not in ("trade_as_planned", "stand_down", "reduce_risk"):
        plan["stance"], plan["silent"] = "stand_down", True
    allowed = st._symbols_in(f)
    plan["watch"] = [w for w in (plan.get("watch") or []) if isinstance(w, dict) and str(w.get("symbol", "")).upper() in allowed][:3]
    fact_nums = {x.replace(",", "") for x in re.findall(r"\d[\d,]*\.?\d*", json.dumps(f, default=str))}
    plan["numbers_not_in_facts"] = [n for n in re.findall(r"\d[\d,]*\.?\d*", json.dumps({k: plan.get(k) for k in ("take_basis", "stance_why", "blind_spot")}))
                                    if n.replace(",", "") not in fact_nums and len(n) > 2][:8]
    return plan


def test_parse_reads_fenced_json_and_rejects_prose():
    raw = 'Sure:\n```json\n{"take": {"bull": 0.4, "bear": 0.4, "neutral": 0.2}, "stance": "stand_down", "stance_why": "x", "watch": [], "blind_spot": "", "silent": true,}\n```'
    assert st._parse(raw)["stance"] == "stand_down"
    assert st._parse("I would stay out today.") is None


def test_unknown_stance_becomes_stand_down_and_silent():
    p = _guard({"take": {"bull": 0.5, "bear": 0.3, "neutral": 0.2}, "stance": "go_all_in", "watch": []}, FACTS)
    assert p["stance"] == "stand_down" and p["silent"] is True


def test_watch_names_only_from_the_facts_and_at_most_three():
    w = [{"symbol": "LICI", "direction": "up"}, {"symbol": "ACMEFAKE", "direction": "up"}, {"symbol": "NIFTY", "direction": "down"},
         {"symbol": "MARICO", "direction": "down"}, {"symbol": "BANKNIFTY", "direction": "up"}]
    p = _guard({"take": {}, "stance": "trade_as_planned", "watch": w}, FACTS)
    assert [x["symbol"] for x in p["watch"]] == ["LICI", "NIFTY", "MARICO"]


def test_numbers_not_in_the_facts_are_flagged():
    p = _guard({"take": {}, "stance": "reduce_risk", "stance_why": "Nifty at 22,937 with fear at 18.5 and flows of 3,400 crore"}, FACTS)
    assert "18.5" in p["numbers_not_in_facts"] and "3,400" in p["numbers_not_in_facts"] and "22,937" not in p["numbers_not_in_facts"]


def test_blind_facts_drop_ananta_plan_and_words():
    from jarvis.india import service
    for k in ("plan", "words", "review", "lessons_for_writer", "reviewer_scenarios", "opening"):
        assert k in service.BLIND_DROP
