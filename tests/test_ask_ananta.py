"""Ask Ananta: lookups over real Explorer state, both provider loops (fake HTTP), JSON layers, clarify limit, views."""
import json

from jarvis.service import ask, core, views
from tests.test_jarvis_core import FakeHands


import pytest


@pytest.fixture(autouse=True)
def _no_local_voice(monkeypatch):
    monkeypatch.setenv("ANANTA_VOICE_LOCAL", "0")     # tests never call the Mac's voice server
    monkeypatch.setenv("ASK_LOCAL", "0")              # ... or the Mac's model server


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
                       ("changes", {"hours": 72}), ("report", {"kind": "daily"}), ("history", {"setup": "E1"}), ("chain", {}),
                       ("reads", {}), ("reads", {"coin": coin})]:
        out = L.call(name, args)
        json.dumps(out, default=str)
        assert not (isinstance(out, dict) and "error" in out and name not in ("history", "report", "reads")), (name, out)
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
    assert ask.parse('{"kind": "answer", "answer": "cut \\"here\\" ok", "breakdown": ["a", "b')["answer"] == 'cut "here" ok'
    try:
        ask.parse("")
    except RuntimeError:
        pass
    else:
        raise AssertionError("empty answer accepted")
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
    assert ask.route("how is btc")[0] == "haiku"         # auto: routine -> Haiku when Claude is set up ...
    del os.environ["ANTHROPIC_API_KEY"]
    r = A.ask("o", "how is btc")                       # ... else free Gemini
    assert r["provider"] == "gemini" and r["cost_usd"] == 0 and "Gemini" in r["note"]
    os.environ["ANTHROPIC_API_KEY"] = "test"
    r = A.ask("o", "compare SOL and ETH: which should we trade?")   # auto -> sonnet (analysis)
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


def test_markets_and_chart():
    j, ex = _jarvis()
    m = views.markets(j)
    assert m["coins"] and m["summary"] and "closest" in m["coins"][0]
    coin = m["coins"][0]["coin"]
    for tf in ("15m", "1h", "4h", "1d"):
        c = views.chart(j, coin, tf)
        assert c["candles"] and {"o", "h", "l", "c", "ema20"} <= set(c["candles"][0])
    try:
        views.chart(j, coin, "2m")
    except ValueError:
        pass
    else:
        raise AssertionError("bad tf accepted")


def test_mandate_and_pending_actions():
    from jarvis.service.mandate import Mandate
    j, ex = _jarvis()
    M = Mandate(j.db, j.now)
    assert M.get()["version"] == 0 and "limits" in M.get()["sections"]
    L = ask.Lookups(j, "th1")
    r = L.call("propose_mandate_change", {"section": "limits", "op": "add", "text": "Never more than $200 per trade."})
    assert r["prepared"]["status"] == "PENDING" and L.created
    assert "Never more than $200" not in M.text()                        # nothing applied yet
    aid = r["prepared"]["id"]
    out = M.decide("o", aid, True, {"mandate": M.apply_mandate_change})
    assert out["status"] == "DONE" and "Never more than $200 per trade." in M.text() and M.get()["version"] == 1
    try:
        M.decide("o", aid, True, {"mandate": M.apply_mandate_change})
    except ValueError:
        pass
    else:
        raise AssertionError("decided twice")
    r2 = L.call("propose_mandate_change", {"section": "nope", "op": "add", "text": "x"})
    assert "error" in r2
    a2 = M.propose("mandate", "x", {"section": "goal", "op": "add", "text": "y"})
    assert M.decide("o", a2["id"], False, {})["status"] == "CANCELLED"
    assert ask._clean_show([{"screen": "coin", "coin": "eth", "label": "Open ETH"}, {"screen": "hack"}, {"screen": "trade", "id": "../x"}]) == \
        [{"screen": "coin", "label": "Open ETH", "coin": "ETH"}]
    # the mandate reaches the model's instructions, and prepared actions come back with the answer
    seen = {}

    def fake(s, h, u, t, log):
        seen["system"] = s
        t.call("propose_mandate_change", {"section": "styles", "op": "add", "text": "Swing trades up to 2 weeks."})
        return json.dumps({"kind": "answer", "answer": "Prepared.", "show": [{"screen": "mandate", "label": "Open mandate"}]}), {"in": 1, "out": 1}

    A = ask.Ask(j, providers={"gemini": fake})
    res = A.ask("o", "add swing trades up to 2 weeks to my styles", mode="everyday")
    assert "Never more than $200 per trade." in seen["system"] and res["actions"][0]["kind"] == "mandate" and res["show"][0]["screen"] == "mandate"



def test_claude_empty_final_answer_is_nudged_once():
    j, ex = _jarvis()
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test"
    replies = [{"content": [{"type": "thinking", "thinking": "", "signature": "x"}], "stop_reason": "end_turn", "usage": {}},
               {"content": [{"type": "text", "text": '{"answer": "here"}'}], "stop_reason": "end_turn", "usage": {}}]
    bodies = []

    def post(url, headers, body, timeout=60):
        bodies.append(body)
        return replies[len(bodies) - 1]

    txt, u = ask.run_claude("sys", [], "hi", ask.Lookups(j), [], post=post, model="m")
    assert ask.parse(txt)["answer"] == "here" and len(bodies) == 2



def test_voice_turn_transcribes_then_answers():
    j, ex = _jarvis()
    import os
    os.environ["GEMINI_API_KEY"] = "test"
    seen = {}

    def fake(s, h, u, t, log):
        seen["u"] = u
        return json.dumps({"kind": "answer", "answer": "Bitcoin is up a little."}), {"in": 1, "out": 1}

    A = ask.Ask(j, providers={"gemini": fake})
    A.transcribe = lambda b64, mime="audio/wav": "how is bitcoin" if b64 == "AAAA" else ""
    r = A.voice_turn("o", "AAAA", "audio/wav", None, "everyday", None)
    assert r["heard"] == "how is bitcoin" and r["answer"] and "voice session" in seen["u"]
    assert A.threads()[0]["voice"] is True
    r2 = A.voice_turn("o", "BBBB", "audio/wav", r["thread"], "everyday", None)
    assert r2["heard"] == "" and "didn't catch" in r2["error"]
    A2 = ask.Ask(j, providers={"gemini": fake})
    A2.set_setting("o", "voice_enabled", "0")
    try:
        A2.transcribe("AAAA")
    except ValueError as e:
        assert "switched off" in str(e)
    else:
        raise AssertionError("voice switch not enforced")
    # real transcribe request shape (fake HTTP)
    A2.set_setting("o", "voice_enabled", "1")
    bodies = []
    out = A2.transcribe("QUJD", "audio/wav", post=lambda url, h, b, timeout=60: bodies.append(b) or {"candidates": [{"content": {"parts": [{"text": " what is hunter doing "}]}}]})
    assert out == "what is hunter doing" and bodies[0]["contents"][0]["parts"][0]["inlineData"]["mimeType"] == "audio/wav"



def test_alerts_by_talking_and_briefs():
    from jarvis.service.alerts import Alerts
    from jarvis.service.mandate import Mandate
    j, ex = _jarvis()
    coin = next(iter(ex.st["engines"]))
    px = ex.prices()[coin]
    L = ask.Lookups(j, "t")
    r = L.call("propose_alert", {"kind": "price_above", "coin": coin, "value": px * 0.5, "note": "test"})
    assert r["prepared"]["kind"] == "alert"
    assert "error" in L.call("propose_alert", {"kind": "price_above", "coin": coin})
    assert "error" in L.call("propose_alert", {"kind": "nope", "coin": coin, "value": 1})
    M, AL = Mandate(j.db, j.now), Alerts(j.db, j.now)
    assert AL.list() == []                                         # nothing active before confirmation
    M.decide("o", r["prepared"]["id"], True, {"alert": AL.create})
    AL.create("o", {"kind": "price_below", "coin": coin, "value": px * 0.5})
    AL.create("o", {"kind": "setup", "coin": coin, "setup": "ANY"})
    pushed = []
    fired = AL.check(ex, push=lambda t, b: pushed.append((t, b)))
    kinds = {f["kind"] for f in fired}
    assert "price_above" in kinds and "price_below" not in kinds and pushed
    assert AL.check(ex) == [] or all(f["kind"] == "setup" for f in AL.check(ex))   # one-shot
    feed = views.feed(j, hours=24 * 400)
    assert any(it["kind"] == "alert" for it in feed)
    # briefs: due once per slot, written by the given ask function
    import datetime as dt
    from zoneinfo import ZoneInfo
    t9 = dt.datetime(2026, 10, 2, 9, 0, tzinfo=ZoneInfo("America/Toronto")).timestamp()
    AB = Alerts(j.db, lambda: t9)
    assert AB.due_brief() == "morning"
    b = AB.write_brief("morning", lambda q: {"answer": "Quiet night.", "kind": "answer"}, push=lambda t, x: None)
    assert b["text"] == "Quiet night." and AB.due_brief() is None and AB.latest_brief()["kind"] == "morning"



def test_manual_paper_orders_journal_and_jobs():
    from jarvis.service.manual import Manual
    from jarvis.service.mandate import Mandate
    j, ex = _jarvis()
    px = ex.prices()
    coin = next(iter(px))
    L = ask.Lookups(j, "t")
    r = L.call("propose_paper_order", {"side": "buy", "coin": coin, "usd": 300, "stop": px[coin] * 0.95, "reason": "testing the flow"})
    assert r["prepared"]["kind"] == "paper_order" and "Paper BUY $300.00" in r["prepared"]["summary"]
    Mn, M = Manual(j.db, j.now), Mandate(j.db, j.now)
    assert Mn.state(px)["positions"] == []                                     # not executed before confirmation
    M.decide("o", r["prepared"]["id"], True, {"paper_order": lambda who, p: Mn.execute(who, p, px)})
    st = Mn.state(px)
    assert st["positions"][0]["coin"] == coin and st["cash"] < 700 and st["positions"][0]["stop"] == px[coin] * 0.95
    assert Mn.journal()[0]["text"] == "testing the flow"
    for bad in ({"side": "buy", "coin": coin, "usd": 5000}, {"side": "buy", "coin": "NOPE", "usd": 10}, {"side": "hold", "coin": coin, "usd": 1},
                {"side": "buy", "coin": coin, "usd": 10, "stop": px[coin] * 2}):
        assert "error" in L.call("propose_paper_order", bad), bad
    low = {c: (p * 0.9 if c == coin else p) for c, p in px.items()}             # price falls through the stop
    sold = Mn.check_stops(low)
    assert sold and sold[0]["side"] == "sell" and Mn.state(low)["positions"] == []
    assert Mn.state(low)["realized"] < 0
    # sell-all without an amount, and a research job
    Mn.execute("o", {"side": "buy", "coin": coin, "usd": 100}, px)
    pv = Mn.preview({"side": "sell", "coin": coin}, px)
    assert abs(pv["order"]["usd"] - Mn.state(px)["positions"][0]["value"]) < 0.01
    jb = Mn.start_job("o", "reconstruction", lambda: {"match": True, "logged_real_events": 3, "rebuilt_real_events": 3}, background=False)
    assert Mn.job(jb["job"])["status"] == "DONE"


def test_shared_db_survives_many_threads():
    import concurrent.futures as cf
    from jarvis.service.manual import Manual
    j, ex = _jarvis()
    Mn = Manual(j.db, j.now)

    def work(i):
        Mn.note("o", "t", str(i), f"note {i}")
        return len(Mn.journal(500)) + len(views.feed(j, hours=24))
    with cf.ThreadPoolExecutor(16) as pool:
        list(pool.map(work, range(200)))
    assert len(Mn.journal(500)) == 200


def test_eval_questions_do_not_use_the_owner_daily_limit():
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": lambda s, h, u, t, log: (json.dumps({"answer": "ok"}), {"in": 1, "out": 1})})
    old = ask.DAILY_LIMIT
    ask.DAILY_LIMIT = 2
    try:
        for _ in range(3):
            A.ask("o", "how is btc", mode="everyday", source="eval")
        assert A.today_count() == 0
        A.ask("o", "how is btc", mode="everyday")
        A.ask("o", "how is btc", mode="everyday")
        try:
            A.ask("o", "how is btc", mode="everyday")
        except ValueError as e:
            assert "limit" in str(e)
        else:
            raise AssertionError("owner limit not enforced")
    finally:
        ask.DAILY_LIMIT = old


def test_wordless_claude_falls_back_to_gemini():
    j, ex = _jarvis()
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test"
    A = ask.Ask(j, providers={"sonnet": lambda s, h, u, t, log: ("", {"in": 10, "out": 5}),
                              "gemini": lambda s, h, u, t, log: (json.dumps({"answer": "from gemini"}), {"in": 1, "out": 1})})
    r = A.ask("o", "why is btc up", mode="deep")
    assert r["answer"] == "from gemini" and r["provider"] == "gemini" and "Gemini answered" in r["note"]


def test_router_and_briefs():
    from jarvis.service import briefs as B
    assert B.route("How is our portfolio doing?") == "portfolio"
    assert B.route("Are we making money or losing money?") == "portfolio"
    assert B.route("How is the market today?") == "market"
    assert B.route("What did the latest scan find?") == "market"
    assert B.route("If the market is bullish, why aren't we taking trades?") == "both"
    assert B.route("Why?", "portfolio") == "portfolio"
    assert B.route("hmm", None) == "both"
    j, ex = _jarvis()
    B.clear()
    p, m = B.portfolio_brief(j), B.market_brief(j)
    assert "explorer_book" in p and "t3_portfolio" in p and "watching" in p
    assert len(m["coins"]) == len(ex.st["engines"]) and "evidence" in m
    assert B.size(p) < 12000 and B.size(m) < 12000, (B.size(p), B.size(m))
    seen = {}

    def fake(s, h, u, t, log):
        seen["u"] = u
        return json.dumps({"answer": "ok"}), {"in": 1, "out": 1}
    A = ask.Ask(j, providers={"gemini": fake})
    r = A.ask("o", "How is our portfolio doing?", mode="everyday")
    assert r["route"] == "portfolio" and "PORTFOLIO_BRIEF" in seen["u"] and "MARKET_BRIEF" not in seen["u"] and "greet" in seen["u"]
    r2 = A.ask("o", "Why?", thread=r["thread"], mode="everyday")
    assert r2["route"] == "portfolio" and "greet" not in seen["u"] and r2["timing"]["brief_ms"] >= 0


def test_app_navigation_quick_and_tools():
    from jarvis.service import appmap
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": lambda s, h, u, t, log: (json.dumps({"answer": "x"}), {"in": 1, "out": 1})})
    for q, want in [("Can you take me to home screen?", "home"), ("take me to markets", "markets"), ("Go to the cockpit", "cockpit"),
                    ("open my trades", "portfolio:mine"), ("show me the evidence", "evidence"), ("open ethereum", None)]:
        r = A.ask("o", q)
        assert r["model_label"] == "Instant" and r["ui"], q
        if want:
            assert r["ui"][0]["target"] == want, (q, r["ui"])
    coin = next(iter(ex.st["engines"]))
    assert A.ask("o", "go back")["ui"][0]["do"] == "back"
    assert appmap.resolve(j, f"coin:{coin}")[0] == f"coin:{coin}"
    assert appmap.resolve(j, "coin:PEPE")[0] is None and appmap.resolve(j, "trade:../x")[0] is None and appmap.resolve(j, "nowhere")[0] is None
    L = ask.Lookups(j, "t")
    assert L.call("ui_go", {"target": "portfolio"})["ok"] and L.ui[-1]["target"] == "portfolio"
    assert not L.call("ui_go", {"target": "coin:PEPE"})["ok"]
    assert "places" in L.call("app_map", {})
    # a model answer carries the screen moves, and the screen context reaches the prompt
    seen = {}

    def fake(s, h, u, t, log):
        seen["u"] = u
        t.call("ui_go", {"target": f"coin:{coin}"})
        return json.dumps({"answer": "Here it is."}), {"in": 1, "out": 1}
    A2 = ask.Ask(j, providers={"gemini": fake})
    r = A2.ask("o", "why is this coin moving", mode="everyday", context={"here": {"screen": "ananta", "label": "Ananta tab"}, "about": None})
    assert r["ui"] == [{"do": "open", "target": f"coin:{coin}", "label": f"{coin} coin page"}] and "Ananta tab" in seen["u"]


def test_screen_claims_are_kept_honest():
    from jarvis.service import appmap
    j, ex = _jarvis()
    ui, ans = appmap.keep_honest(j, "Show me where the evidence is.", "I've moved your screen to the Evidence tab.", [], {"screen": "ananta"})
    assert ui and ui[0]["target"] == "evidence"
    ui, ans = appmap.keep_honest(j, "how are we", "I'm taking you to the moon page.", [], {"screen": "ananta"})
    assert not ui and "couldn't move the screen" in ans
    ui, ans = appmap.keep_honest(j, "where am I", "You're on the Ananta tab.", [{"do": "go_to", "target": "ananta", "label": "Ananta"}], {"screen": "ananta"})
    assert ui == [] and "couldn't" not in ans


def test_spots_and_scroll():
    from jarvis.service import appmap
    j, ex = _jarvis()
    coin = next(iter(ex.st["engines"]))
    assert appmap.valid_spot(j, "home.value") and appmap.valid_spot(j, f"markets.coin:{coin}")
    assert not appmap.valid_spot(j, "markets.coin:PEPE") and not appmap.valid_spot(j, "home.nothing") and not appmap.valid_spot(j, "<script>")
    pts, ui = appmap.plan_points(j, [{"spot": "home.value", "sentence": 0}, {"spot": "bad.spot", "sentence": 1}], [], {"screen": "ananta"}, 2, "show me the value")
    assert pts == [{"spot": "home.value", "sentence": 0}] and ui[0]["target"] == "home"          # app opens Home for the spot
    pts, ui = appmap.plan_points(j, [{"spot": "home.value", "sentence": 0}], [], {"screen": "ananta"}, 2, "where am I")
    assert pts == [] and ui == []                                                               # no move unless he asked to see
    ui, ans = appmap.keep_honest(j, "What's below this?", "I've scrolled to the bottom for you.", [], {"screen": "markets"})
    assert ui and ui[0]["do"] == "scroll" and "couldn't" not in ans
    pts, ui = appmap.plan_points(j, [{"spot": "home.value", "sentence": 5}], [], {"screen": "home"}, 2)
    assert ui == [] and pts[0]["sentence"] == 1
    pts, ui = appmap.plan_points(j, [{"spot": "coin.chart"}], [], {"screen": "home"}, 1)
    assert pts == []                                                                         # coin spots only on a coin page
    pts, ui = appmap.plan_points(j, [{"spot": "coin.chart"}], [{"do": "open", "target": f"coin:{coin}"}], {"screen": "home"}, 1)
    assert pts and len(ui) == 1
    A = ask.Ask(j, providers={"gemini": lambda s, h, u, t, log: (json.dumps({"answer": "x"}), {"in": 1, "out": 1})})
    for q, d in [("scroll down", "down"), ("show me the bottom of the page", "bottom"), ("go to the top", "top"), ("scroll up please", "up")]:
        r = A.ask("o", q)
        assert r["ui"] == [{"do": "scroll", "dir": d, "label": f"Scroll {d}"}], (q, r["ui"])
    seen = {}

    def fake(s, h, u, t, log):
        seen["s"] = s
        return json.dumps({"answer": "The value is up. The feed is quiet.", "points": [{"spot": "home.value", "sentence": 0}, {"spot": "home.activity", "sentence": 1}]}), {"in": 1, "out": 1}
    A2 = ask.Ask(j, providers={"gemini": fake})
    r = A2.ask("o", "how are we doing today", mode="everyday", context={"here": {"screen": "home", "label": "Home"}})
    assert r["points"] == [{"spot": "home.value", "sentence": 0}, {"spot": "home.activity", "sentence": 1}] and r["ui"] == [] and "POINT AT" in seen["s"]


def test_points_survive_a_scroll():
    from jarvis.service import appmap
    j, ex = _jarvis()
    pts, ui = appmap.plan_points(j, [{"spot": "home.value", "sentence": 0}], [{"do": "scroll", "dir": "top"}], {"screen": "home"}, 1, "walk me through this screen")
    assert pts and ui == [{"do": "scroll", "dir": "top"}]


def test_tour_and_proof_links():
    from jarvis.service import appmap
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": lambda s, h, u, t, log: (json.dumps({"answer": "x"}), {"in": 1, "out": 1})})
    r = A.ask("o", "I'm new here, show me around")
    assert r["model_label"] == "Instant" and len(r["tour"]) >= 12
    for st in r["tour"]:
        assert st["say"] and (not st.get("spot") or appmap.valid_spot(j, st["spot"]) or st["spot"].startswith("markets.coin"))
    coin = next(iter(ex.st["engines"]))
    ev = appmap.clean_evidence(j, [{"label": "value", "value": "1", "spot": "portfolio.value"},
                                   {"label": "chart", "value": "2", "spot": "coin.chart", "screen": f"coin:{coin}"},
                                   {"label": "bad", "value": "3", "spot": "coin.chart"}, {"label": "x", "value": "4", "spot": "zzz.q", "screen": "nowhere"}])
    assert ev[0]["screen"] == "portfolio" and ev[1]["screen"] == f"coin:{coin}" and "spot" not in ev[2] and "spot" not in ev[3] and "screen" not in ev[3]


def test_show_me_that_opens_the_proof():
    j, ex = _jarvis()
    replies = [json.dumps({"answer": "The portfolio is up 2 percent.", "evidence": [{"label": "Portfolio return", "value": "+2%", "spot": "portfolio.value"}]}),
               json.dumps({"answer": "It comes from the T3 portfolio."})]

    def fake(s, h, u, t, log):
        return replies.pop(0), {"in": 1, "out": 1}
    A = ask.Ask(j, providers={"gemini": fake})
    r1 = A.ask("o", "how much is the portfolio up?", mode="everyday", context={"here": {"screen": "ananta"}})
    assert r1["evidence"][0]["screen"] == "portfolio" and r1["ui"] == []
    r2 = A.ask("o", "Where did you get that number?", thread=r1["thread"], mode="everyday", context={"here": {"screen": "ananta"}})
    assert r2["ui"][0]["target"] == "portfolio" and r2["points"] == [{"spot": "portfolio.value", "sentence": 0}]
    from jarvis.service import appmap
    ui, ans = appmap.keep_honest(j, "how are we", "I'm showing you the Portfolio screen now.", [], {"screen": "ananta"})
    assert ui and ui[0]["target"] == "portfolio"
    ui, _ = appmap.keep_honest(j, "scroll down and show me the evidence", "ok", [{"do": "scroll", "dir": "down"}, {"do": "go_to", "target": "evidence"}], {"screen": "ananta"})
    assert [u["do"] for u in ui] == ["go_to", "scroll"]


def test_where_am_i_never_moves_and_moves_dedupe():
    from jarvis.service import appmap as am
    here = {"screen": "trade", "id": "BTC-1", "coin": "BTC"}
    mv = {"do": "open", "target": "trade:ETH-2", "label": "ETH trade"}
    ui, _ = am.keep_honest(None, "What am I looking at?", "You're on the BTC trade page.", [mv, mv], here)
    assert ui == []
    ui, _ = am.keep_honest(None, "Open the ETH trade", "Here it is.", [mv, mv, mv], here)
    assert ui == [mv]


def test_highlights_follow_the_sentence_that_names_them():
    from jarvis.service import appmap as am
    ans = "Here is our Bitcoin trade. We bought it at 76,000. The stop is at 74,100. The target is at 80,200."
    pts = am.anchor_points([{"spot": "trade.target", "sentence": 1}, {"spot": "trade.stop", "sentence": 1}], ans)
    assert {p["spot"]: p["sentence"] for p in pts} == {"trade.stop": 2, "trade.target": 3}
    assert [p["sentence"] for p in pts] == sorted(p["sentence"] for p in pts)
    pts = am.anchor_points([{"spot": "portfolio.holding:LTC", "sentence": 0}], "The portfolio is up. Litecoin is strongest.")
    assert pts == [{"spot": "portfolio.holding:LTC", "sentence": 1}]


def test_outside_coin_is_labelled_and_unknown_coin_offers_names():
    from jarvis.service import outside
    fake = {"pepe": {"coins": [{"id": "pepe", "name": "Pepe", "symbol": "pepe", "market_cap_rank": 30}]}}
    detail = {"name": "Pepe", "symbol": "pepe", "market_cap_rank": 30, "description": {"en": "A meme coin. Second line. Third."},
              "market_data": {"current_price": {"usd": 0.00001}, "price_change_percentage_24h": 3.2, "market_cap": {"usd": 4e9}}}
    get = lambda path, p: detail if path.startswith("/coins/") else fake.get(p.get("query", "").lower(), {"coins": []})  # noqa: E731
    outside._cache.clear()
    r = outside.coin("pepe", get=get)
    assert r["found"] and r["symbol"] == "PEPE" and not r["in_our_basket"] and "CoinGecko" in r["source"]
    miss = outside.coin("etherium", get=get)
    assert not miss["found"] and "Ethereum" in miss["similar"]
    reply = {"kind": "answer", "answer": "Here you go.", "evidence": [{"label": "Price", "value": "1"}], "options": []}
    ask._label_outside(reply, [r])
    assert reply["outside"]["source"].startswith("CoinGecko") and reply["evidence"][0]["source"] == "CoinGecko"
    reply = {"kind": "answer", "answer": "Etherium is...", "options": []}
    ask._label_outside(reply, [miss])
    assert reply["kind"] == "clarify" and "couldn't find" in reply["answer"] and "Ethereum" in reply["options"]


def test_guest_practice_sandbox_never_touches_the_owners_books(monkeypatch):
    j, ex = _jarvis()
    j.join(j.invite("Friend", "friend@x.com")["code"], "Friend", "", "guest pass 123")
    tok = j.login("friend@x.com", "guest pass 123")
    assert j.check(tok) == "guest:friend@x.com"
    assert "Practice mode" in ask.Lookups(j, guest=True).call("start_research", {"kind": "reconstruction"})["error"]
    import pytest
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from jarvis.service import app as appmod
    monkeypatch.setattr(appmod, "_J", j)
    monkeypatch.setattr(appmod, "_JG", {})
    monkeypatch.setattr(appmod, "_A", {})
    c = TestClient(appmod.app)
    h = {"Authorization": f"Bearer {tok}"}
    # shared controls stay locked; looking works; the app knows it is practice mode
    assert c.post("/safety/kill", json={"on": True, "confirm": True}, headers=h).status_code == 403
    assert c.post("/portfolio/mode", json={"mode": "auto", "confirm": True}, headers=h).status_code == 403
    assert c.get("/v3/home", headers=h).status_code == 200
    assert c.get("/v3/me", headers=h).json()["guest"] is True
    # a guest's paper order is prepared and confirmed in the guest's own book
    g = appmod._sandbox("guest:friend@x.com")
    assert g is not j and g.sandbox and not j.sandbox
    coin = next(iter(ex.st["engines"]))
    L = ask.Lookups(g, guest=True)
    out = L.call("propose_paper_order", {"side": "buy", "coin": coin, "usd": 100, "reason": "testing"})
    assert "prepared" in out, out
    r = c.post(f"/v3/actions/{out['prepared']['id']}", json={"confirm": True}, headers=h)
    assert r.status_code == 200, r.text
    assert g.db.execute("SELECT count(*) FROM manual_fills").fetchone()[0] == 1
    j.db.executescript("CREATE TABLE IF NOT EXISTS manual_fills (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, side TEXT, usd REAL, units REAL, "
                       "px REAL, cost REAL, reason TEXT, by TEXT, trigger TEXT)")
    assert j.db.execute("SELECT count(*) FROM manual_fills").fetchone()[0] == 0          # Madhav's book untouched
    # the owner's requests still use the owner's book
    otok = j.login("o@x.com", "pw pw pw pw 1")
    assert c.get("/v3/me", headers={"Authorization": f"Bearer {otok}"}).json()["guest"] is False
    # guests get a small Claude budget even if they try to raise it
    c.post("/v3/settings", json={"key": "daily_budget_usd", "value": "40"}, headers=h)
    tok2 = appmod._SANDBOX.set("guest:friend@x.com")
    try:
        assert float(appmod.A().setting("daily_budget_usd")) <= appmod.GUEST_CLAUDE_BUDGET
    finally:
        appmod._SANDBOX.reset(tok2)


def test_session_export_text():
    j, ex = _jarvis()
    a = ask.Ask(j, providers={})
    th = "t-export"
    j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, provider, mode) VALUES ('u1', ?, 1, 'user', 'how is BTC?', 'claude', 'voice:x')", (th,))
    j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, provider, ms) VALUES ('a1', ?, 2, 'assistant', ?, 'claude', 4200)",
                 (th, json.dumps({"kind": "answer", "answer": "BTC is up.", "model_label": "Claude", "ui": [{"do": "open", "label": "BTC page"}],
                                  "points": [{"spot": "coin.chart", "sentence": 0}], "evidence": [{"label": "Price", "value": "76k"}]})))
    t = a.export(th)
    assert "MADHAV (voice): how is BTC?" in t and "BTC is up." in t and "4.2s" in t and "BTC page" in t and "coin.chart" in t


def test_evidence_rows_get_a_place_to_show():
    from jarvis.service import appmap as am
    j, ex = _jarvis()
    out = am.clean_evidence(j, [{"label": "T3 portfolio return", "value": "2.4%"}, {"label": "BTC next resistance", "value": "78,000"},
                                {"label": "Pepe price", "value": "$0.00001", "source": "CoinGecko"}])
    assert out[0]["screen"] == "portfolio" and out[0]["spot"] == "portfolio.value"
    assert out[1]["screen"] == "coin:BTC" and out[1]["spot"] == "coin.levels"
    assert "screen" not in out[2]


def test_every_spot_ananta_can_point_at_exists_in_the_app():
    import pathlib
    import re as _re
    from jarvis.service import appmap as am
    root = pathlib.Path(__file__).resolve().parents[1] / "jarvis" / "app"
    src = "\n".join(p.read_text() for p in list((root / "app").rglob("*.tsx")) + list((root / "src").rglob("*.tsx")))
    in_app = {m.split(":")[0] for m in _re.findall(r'Spot id=\{?["`]([^"`]+)', src)}
    wanted = {k.split(":")[0] for v in am.SPOTS.values() for k in v}
    assert wanted <= in_app, sorted(wanted - in_app)


def test_natural_voice_skips_a_clip_that_says_extra_words(monkeypatch):
    import base64
    from jarvis.service import speech as sp
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    sp._cool.clear()
    calls = []

    def post(m, body):
        calls.append((m, body["contents"][0]["parts"][0]["text"]))
        n = 48000 * (20 if m.startswith("gemini-2.5") else 1)       # the first model "reads the instructions": 20 s for 3 words
        return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "audio/L16;rate=24000", "data": base64.b64encode(b"\0" * n).decode()}}]}}]}

    w = sp._speak("Hello there Madhav.", "Calm", post=post)
    assert sp.duration_s(w) == 1.0 and len(calls) == 2
    assert calls[0][1].startswith("Say in a calm") and calls[1][1] == "Hello there Madhav."
    sp._cool.clear()


def test_local_model_answers_and_escalates_when_unsure():
    j, ex = _jarvis()
    good = json.dumps({"kind": "answer", "answer": "The portfolio is fine.", "evidence": []})
    seen = []

    def fake_local(body):
        seen.append(body)
        if len(seen) == 1:
            return {"message": {"tool_calls": [{"function": {"name": "portfolio", "arguments": {}}}]}, "prompt_eval_count": 10, "eval_count": 2}
        return {"message": {"content": good}, "prompt_eval_count": 20, "eval_count": 5}

    A = ask.Ask(j, providers={"local": lambda s, h, u, t, log: ask.run_local(s, h, u, t, log, post=fake_local, model="m")})
    r = A.ask("o@x.com", "how is the portfolio", provider="local")
    assert r["answer"] == "The portfolio is fine." and r["lookups"] == ["portfolio"] and r["cost_usd"] == 0
    assert "tools" in seen[0] and seen[1]["messages"][-1]["role"] == "tool"
    # router picked the Mac and it made up a number: Haiku answers instead
    bad = json.dumps({"kind": "answer", "answer": "Bitcoin is at $91,234.", "evidence": []})
    fine = json.dumps({"kind": "answer", "answer": "Here is the real answer.", "evidence": []})
    A = ask.Ask(j, providers={"local": lambda *a, **k: (bad, {"in": 1, "out": 1}), "haiku": lambda *a, **k: (fine, {"in": 1, "out": 1})})
    A._pick = lambda text, mode, provider: ("local", "auto", "")
    A._next_level = lambda: "haiku"
    r = A.ask("o@x.com", "where is bitcoin")
    assert r["provider"] == "haiku" and "wasn't sure" in r["note"] and "91,234" in r["note"]


def test_spoken_answer_is_short_and_says_the_choices():
    long = {"kind": "answer", "answer": " ".join(f"Sentence number {i} has exactly seven words here." for i in range(12))}
    t = ask.speak_text(long)
    assert 0 < len(t.split()) <= ask.VOICE_WORDS and t.startswith("Sentence number 0")
    one_huge = {"kind": "answer", "answer": "word " * 90 + "end."}
    assert ask.speak_text(one_huge).endswith("end.")                      # never empty: the first sentence is always said
    c = ask.speak_text({"kind": "clarify", "answer": "Which one do you mean?", "options": ["Bitcoin trade", "Bitcoin coin page"]})
    assert c.endswith("Did you mean Bitcoin trade, or Bitcoin coin page?")


def test_answer_audio_is_one_file_per_answer_and_retries_after_a_failure():
    from jarvis.service import speech
    made = []

    def make(s, v, sp):
        made.append((tuple(s), v, sp))
        return {"audio": b"ID3", "mime": "audio/mpeg", "offsets": [0.0, 1.2], "duration": 2.5, "engine": "kokoro"}

    k1 = speech.prepare_answer(["Hello Madhav.", " Bitcoin is up. ", ""], "Calm", 0.9, make=make)
    k2 = speech.prepare_answer(["Hello Madhav.", "Bitcoin is up."], "Calm", 0.9, make=make)
    assert k1 == k2 and len(made) == 1                                      # same words, voice and speed: made once
    assert speech.answer_meta(k1)["offsets"] == [0.0, 1.2] and speech.answer_audio(k1) == (b"ID3", "audio/mpeg")
    assert speech.prepare_answer(["Hello Madhav.", "Bitcoin is up."], "Deep", 0.9, make=make) != k1

    def down(s, v, sp):
        raise RuntimeError("voice server down")

    k3 = speech.prepare_answer(["Try again."], "Calm", 1.0, make=down)
    try:
        speech.answer_meta(k3)
        assert False, "should fail"
    except RuntimeError:
        pass
    assert speech.prepare_answer(["Try again."], "Calm", 1.0, make=make) == k3 and speech.answer_meta(k3)["engine"] == "kokoro"


def test_voice_answers_carry_spoken_text_and_audio_id(monkeypatch):
    from jarvis.service import speech
    j, ex = _jarvis()
    seen = {}
    monkeypatch.setattr(speech, "prepare_answer", lambda s, v, sp, make=None: seen.setdefault("k", f"id-{len(s)}-{v}-{sp}"))
    long = json.dumps({"kind": "answer", "answer": " ".join(f"Point {i} is about the market today." for i in range(15))})
    A = ask.Ask(j, providers={"gemini": lambda *a, **k: (long, {"in": 1, "out": 1})})
    r = A.ask("o@x.com", "how is the market", mode="everyday", voice=True, context={"here": {"screen": "ananta"}, "tts": {"voice": "Calm", "speed": 0.9}})
    assert r["speak"] and len(r["speak"].split()) <= ask.VOICE_WORDS and r["voice_id"].endswith("-Calm-0.9")
    r2 = A.ask("o@x.com", "how is the market", mode="everyday", context={"here": {"screen": "ananta"}})      # typed: nothing spoken
    assert "speak" not in r2 and "voice_id" not in r2


def test_instant_small_talk_and_repeat():
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": lambda *a, **k: (json.dumps({"kind": "answer", "answer": "Bitcoin is up two percent."}), {"in": 1, "out": 1})})
    r = A.ask("o@x.com", "how is bitcoin", mode="everyday")
    th = r["thread"]
    again = A.ask("o@x.com", "Say that again.", thread=th, mode="everyday")
    assert again["model"] == "instant" and again["answer"] == "Bitcoin is up two percent."
    assert A.ask("o@x.com", "Thank you.", thread=th, mode="everyday")["answer"].startswith("You're welcome")
    assert A.ask("o@x.com", "okay", thread=th, mode="everyday")["answer"] == "Okay."
    assert A.ask("o@x.com", "okay so why is bitcoin up", thread=th, mode="everyday")["model"] != "instant"


def test_knowledge_map_is_complete_and_read_doc_stays_inside(tmp_path, monkeypatch):
    """The knowledge map lists every document; read_doc opens only documents (docs or Madhav's notes), never other files;
    his notes are searched for him and hidden from guests."""
    import pathlib
    import types

    root = pathlib.Path(__file__).resolve().parents[1]
    docs = root / "docs"
    index = (docs / "KNOWLEDGE_INDEX.md").read_text()
    folders = [docs, docs / "knowledge", docs / "knowledge" / "teachers", docs / "casebook", docs / "repair_shop", docs / "research"]
    for f in folders:
        for p in list(f.glob("*.md")) + list(f.glob("hypotheses.json")) + list(f.glob("cases.json")):
            if p.name == "KNOWLEDGE_INDEX.md":
                continue
            assert f"`{p.relative_to(docs)}`" in index, f"{p.relative_to(docs)} is missing from docs/KNOWLEDGE_INDEX.md"
    for ref in __import__("re").findall(r"`([A-Za-z_/0-9.]+\.(?:md|json))`", index):
        assert (docs / ref).exists(), f"the map points at a missing document: {ref}"
    notes = tmp_path / "My notes"
    notes.mkdir()
    (notes / "sol.md").write_text("# SOL\nI like buying SOL when the weekly base holds above 100 CAD.")
    monkeypatch.setenv("ANANTA_NOTES_DIR", str(notes))
    j = types.SimpleNamespace(dir=root)
    L = ask.Lookups(j)
    k = L.call("knowledge", {"query": "weekly base SOL capitulation"})
    assert k["map"] and k["your_notes"] and k["your_notes"][0]["file"] == "your note: sol.md", k
    assert "casebook" in json.dumps(k)
    d = L.call("read_doc", {"file": "knowledge/FRAMEWORK.md", "section": "fail"})
    assert "error" not in d and d["text"]
    assert "weekly base" in L.call("read_doc", {"file": "your note: sol.md"})["text"]
    for bad in ("../jarvis/service/ask.py", "/etc/passwd", "../../.env", "../pyproject.toml"):
        assert "error" in L.call("read_doc", {"file": bad}), bad
    g = ask.Lookups(j, guest=True)
    assert not g.call("knowledge", {"query": "weekly base SOL"})["your_notes"]
    assert "error" in g.call("read_doc", {"file": "sol.md"})
