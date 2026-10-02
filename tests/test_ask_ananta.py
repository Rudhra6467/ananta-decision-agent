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
