"""Ask Ananta: lookups over real Explorer state, both provider loops (fake HTTP), JSON layers, clarify limit, views."""
import json

from jarvis.service import ask, core, views
from tests.test_jarvis_core import FakeHands


def _jarvis():
    from tests.test_explorer_live import _advance, _mk

    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 4 * 24 * 2)
    j = core.Jarvis(d, owner_email="o@x.com", password_hash=core.hash_password("pw pw pw pw 1"), secret="k" * 40,
                    hands=FakeHands(), now=lambda: clock["now"])
    return j, ex


def test_lookups_and_views_run_on_real_state():
    j, ex = _jarvis()
    L = ask.Lookups(j)
    coin = next(iter(ex.st["engines"]))
    for name, args in [("overview", {}), ("market", {"coin": coin}), ("market", {}), ("setups", {"coin": coin}), ("setups", {}),
                       ("strategy", {"name": "hunter"}), ("strategy", {"name": "explorer"}), ("strategy", {"name": "t3"}),
                       ("trades", {"status": "all"}), ("portfolio", {}), ("evidence", {}), ("knowledge", {"query": "T3 drawdown"}),
                       ("changes", {"hours": 72}), ("report", {"kind": "daily"}), ("history", {"setup": "E1"})]:
        out = L.call(name, args)
        json.dumps(out, default=str)
        assert not (isinstance(out, dict) and "error" in out and name not in ("history", "report")), (name, out)
    s = L.call("setups", {"coin": coin})["coins"][coin]["explorer"]
    assert {r["setup"] for r in s} >= {"E1", "E2", "E3", "E4", "E5"} and all("missing" in r for r in s)
    assert "error" in L.call("market", {"coin": "NOPE"})
    assert "error" in L.call("nope", {})
    # views
    h = views.day_summary(j)
    assert h["paper_value"] > 0 and h["sentence"]
    assert isinstance(views.feed(j), list)
    hv = views.holdings(j)
    assert "holdings" in hv and hv["rule_plain"]
    ec = views.evidence_collected(j)
    assert ec["tracker"] and ec["shop"]["summary"] and ec["forwarded"]
    ef = views.evidence_forwarded(j)
    assert ef["in_use"][0]["id"] == "T3"
    c = views.cockpit(j)
    assert {w["key"] for w in c["switches"]} == {"kill_switch", "portfolio_auto", "live_trading"}
    trades = [t for e in ex.st["engines"].values() for t in list(e.trades) + list(e.actual_closed) if t.shadow is None]
    if trades:
        td = views.trade_detail(j, trades[0].id)
        assert td["plan"] and td["chart"]["points"] and td["why_bought"]


def _fake_claude(script):
    calls = []

    def post(url, headers, body, timeout=90):
        calls.append(json.loads(json.dumps(body)))
        step = script[len(calls) - 1]
        return step

    return post, calls


def test_claude_loop_calls_lookups_then_answers():
    j, ex = _jarvis()
    final = {"kind": "answer", "stage": "observation", "answer": "BTC is in no clear trend.", "breakdown": ["a"], "evidence": [], "follow_ups": []}
    post, calls = _fake_claude([
        {"content": [{"type": "tool_use", "id": "t1", "name": "market", "input": {"coin": "BTC"}}], "usage": {"input_tokens": 10, "output_tokens": 5}},
        {"content": [{"type": "text", "text": "```json\n" + json.dumps(final) + "\n```"}], "usage": {"input_tokens": 20, "output_tokens": 30}},
    ])
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test"
    A = ask.Ask(j, providers={"sonnet": lambda s, h, u, t, log: ask.run_claude(s, h, u, t, log, post=post)})
    r = A.ask("o@x.com", "how is btc?", provider="claude")
    assert r["answer"] == final["answer"] and r["lookups"] == ["market"] and r["stage"] == "observation"
    tool_result = calls[1]["messages"][-1]["content"][0]
    assert tool_result["type"] == "tool_result" and "trend_1h" in tool_result["content"]
    # follow-up carries history
    post2, calls2 = _fake_claude([{"content": [{"type": "text", "text": json.dumps(final)}], "usage": {}}])
    A.providers["sonnet"] = lambda s, h, u, t, log: ask.run_claude(s, h, u, t, log, post=post2)
    A.ask("o@x.com", "why?", thread=r["thread"], provider="claude")
    assert calls2[0]["messages"][0]["content"] == "how is btc?" and len(calls2[0]["messages"]) == 3
    st = A.stats()
    assert st["providers"]["sonnet"]["answers"] == 2
    A.rate(r["id"], 1)
    assert A.stats()["providers"]["sonnet"]["thumbs_up"] == 1


def test_gemini_loop_and_clarify_limit():
    j, ex = _jarvis()
    import os
    os.environ["GEMINI_API_KEY"] = "test"
    clar = {"kind": "clarify", "answer": "Did you mean?", "options": ["the Explorer", "the portfolio"]}
    seq = []

    def post(url, headers, body, timeout=90):
        seq.append(json.loads(json.dumps(body)))
        if len(seq) == 1:
            return {"candidates": [{"content": {"role": "model", "parts": [{"functionCall": {"name": "overview", "args": {}}, "thoughtSignature": "abc"}]}}]}
        return {"candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(clar)}]}}], "usageMetadata": {"promptTokenCount": 3}}

    A = ask.Ask(j, providers={"gemini": lambda s, h, u, t, log: ask.run_gemini(s, h, u, t, log, post=post)})
    r1 = A.ask("o@x.com", "how's it?", provider="gemini")
    assert r1["kind"] == "clarify" and r1["options"]
    assert seq[1]["contents"][-2]["parts"][0]["thoughtSignature"] == "abc"          # signature returned
    assert "functionResponse" in seq[1]["contents"][-1]["parts"][0]
    seq.clear()
    r2 = A.ask("o@x.com", "the thing", thread=r1["thread"], provider="gemini")
    assert r2["kind"] == "clarify"
    seq.clear()
    r3 = A.ask("o@x.com", "you know", thread=r1["thread"], provider="gemini")
    assert r3["kind"] == "not_understood" and r3["follow_ups"]
    assert "failed 2 time" in seq[0]["contents"][-1]["parts"][0]["text"]
    assert len(A.stats()["misunderstood"]) == 3
    # provider failure is reported, not raised
    A.providers["gemini"] = lambda *a: (_ for _ in ()).throw(RuntimeError("429 quota"))
    r4 = A.ask("o@x.com", "x", provider="gemini")
    assert "error" in r4 and "429" in r4["error"]


def test_parse_is_lenient():
    assert ask.parse("plain words")["answer"] == "plain words"
    d = ask.parse('Here: {"answer": "ok", "breakdown": "one"} thanks')
    assert d["answer"] == "ok" and d["breakdown"] == ["one"] and d["kind"] == "answer"


def test_coin_watch():
    j, ex = _jarvis()
    coin = next(iter(ex.st["engines"]))
    w = views.coin_watch(j, coin)
    assert w["ready"] and len(w["setups"]) == 5 and w["market"]["trend_1h"]


def test_trades_list():
    j, ex = _jarvis()
    t = views.trades_list(j)
    assert "open" in t and "closed" in t and t["value"] > 0



def test_modes_budget_second_opinion_and_cost():
    j, ex = _jarvis()
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test"
    calls = []
    ans = {"kind": "answer", "answer": "ok"}

    def fake(key, usage):
        def run(s, h, u, t, log):
            calls.append((key, u))
            if key == "gemini" and "busy" in u:
                raise RuntimeError("503 busy")
            return json.dumps(ans), dict(usage)
        return run

    big = {"in": 100_000, "out": 10_000, "cache_read": 0, "cache_write": 0}
    A = ask.Ask(j, providers={"gemini": fake("gemini", {"in": 5, "out": 5}), "haiku": fake("haiku", big),
                              "sonnet": fake("sonnet", big), "opus": fake("opus", big)})
    r = A.ask("o", "how is btc")                       # auto -> gemini (free)
    assert r["provider"] == "gemini" and r["cost_usd"] == 0 and "Gemini" in r["note"]
    r = A.ask("o", "why did the portfolio lose money?")   # auto -> sonnet
    assert r["provider"] == "sonnet" and abs(r["cost_usd"] - (0.2 + 0.1)) < 1e-6
    r = A.ask("o", "x", mode="max")
    assert r["provider"] == "opus"
    r2 = A.second("o", r["id"])                        # Claude answer -> Gemini second opinion
    assert r2["provider"] == "gemini" and r2["second_of"] == r["id"] and "second opinion" in calls[-1][1]
    r = A.ask("o", "busy now", mode="everyday")        # Gemini busy -> Haiku within budget
    assert r["provider"] == "haiku" and "Haiku" in r["note"]
    sp = A.spend()
    assert sp["today_usd"] > 0.5 and sp["budget_usd"] == 2.0
    A.set_setting("o", "daily_budget_usd", "0.5")      # budget used up -> Gemini answers
    r = A.ask("o", "x", mode="deep")
    assert r["provider"] == "gemini" and "budget" in r["note"]
    A.set_setting("o", "over_budget", "stop")
    try:
        A.ask("o", "x", mode="deep")
    except ValueError as e:
        assert "budget" in str(e)
    else:
        raise AssertionError("budget stop not enforced")
    A.set_setting("o", "ask_enabled", "off")
    try:
        A.ask("o", "x")
    except ValueError as e:
        assert "switched off" in str(e)
    else:
        raise AssertionError("switch not enforced")
    assert ask.cost_usd("sonnet", {"in": 0, "out": 0, "cache_read": 1_000_000}) == 0.2


def test_claude_request_uses_prompt_caching():
    j, ex = _jarvis()
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test"
    bodies = []

    def post(url, headers, body, timeout=90):
        bodies.append(json.loads(json.dumps(body)))
        if len(bodies) == 1:
            return {"content": [{"type": "tool_use", "id": "a", "name": "overview", "input": {}}], "usage": {"input_tokens": 9, "cache_creation_input_tokens": 100}}
        return {"content": [{"type": "text", "text": '{"answer": "fine"}'}], "usage": {"input_tokens": 3, "cache_read_input_tokens": 100, "output_tokens": 5}}

    txt, u = ask.run_claude("sys", [], "hi", ask.Lookups(j), [], post=post, model="m")
    assert u["cache_read"] == 100 and u["cache_write"] == 100
    b = bodies[1]
    marks = sum("cache_control" in blk for m in b["messages"] if isinstance(m["content"], list) for blk in m["content"])
    assert marks == 1 and "cache_control" in b["messages"][-1]["content"][-1]
    assert "cache_control" in b["system"][0] and "cache_control" in b["tools"][-1]
