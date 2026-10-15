"""Fix A6 (Oct 15): Ask's rules at about half the size, each kind of question with its own small set of lookups, the SITUATION line
first. The router is code; more_lookups is the escape when a kind's list lacks the lookup needed."""
import json

from jarvis.service import ask, ask_prompt as AP

OLD_CHARS = 82385     # rules + lookups every question carried before A6 (Oct 15 measurement)


def test_every_lookup_is_reachable_and_every_listed_name_exists():
    names = {n for n, _, _ in ask.TOOLS}
    listed = set(AP.BASE).union(*AP.FAMILIES.values())
    assert listed <= names, listed - names                      # no family names a lookup that does not exist
    assert names <= listed, names - listed                      # every lookup belongs to some kind
    assert "more_lookups" not in names                          # the escape is offered only with a short list


def test_the_router():
    k = AP.kinds_of
    assert k("Can we buy today?") == ["market"]
    assert k("How is the 500 dollar book doing?") == ["books"]
    assert "know" in k("What did review 27 find about stops on dip buys?")
    assert k("Is everything running?") == ["system"]
    assert "act" in k("Set a stop on my Solana at 140") and "act" in k("tell me if BTC drops below 80k")
    assert "act" in k("add swing trades up to 2 weeks to my styles") and "act" in k("That was wrong, flag it")
    assert "outside" in k("What's the weather in Toronto?") and "outside" in k("why are the markets going red?")
    assert k("Go back") == ["app"] and k("hey") == ["chat"]
    assert k("how are we doing today", screen="home") == ["books", "app"] and k("hey", screen="ananta") == ["chat"]   # on a screen: point at it
    r = AP.rules(["books", "app"], "home")
    assert "home.value" in r and "evidence.gate" not in r and "evidence.gate" in AP.rules(["full"])
    assert k("why?", prev=["market"]) == ["market"]                     # a short follow-up keeps the last topic
    assert k("I am thinking about something quite different today, honestly") == ["full"]     # long and unmatched: every lookup
    assert set(k("hello", guest=True)) >= {"people", "outside"}


def test_kinds_get_short_lists_and_full_gets_everything():
    assert AP.tool_names(["full"]) is None and AP.tool_names([]) is None
    m = AP.tool_names(["market"])
    assert {"market", "setups", "chain", "exposure", "ui_go", "log_request"} <= m and "propose_paper_order" not in m
    assert {"propose_paper_order", "propose_levels", "remember"} <= AP.tool_names(["act"])
    assert len(AP.tool_names(["chat"])) == len(AP.BASE)

    class L:
        allowed = m
    specs = ask.tool_specs(L)
    assert [s[0] for s in specs][-1] == "more_lookups" and len(specs) == len(m) + 1
    L.allowed = None
    assert ask.tool_specs(L) is ask.TOOLS


def test_rules_are_about_half_and_full_keeps_every_module():
    full = AP.rules(["full"])
    assert all(v.replace("{spots}", AP.SPOTS) in full for v in AP.MODULES.values()) and "120-coin" in ask.SYSTEM and ask.SYSTEM == full
    for kinds in (["market"], ["books"], ["know"], ["system"], ["chat"]):
        r = AP.rules(kinds)
        tools = json.dumps([{"name": n, "description": d, "input_schema": s} for n, d, s in ask.TOOLS if n in AP.tool_names(kinds)])
        assert (len(r) + len(tools)) / OLD_CHARS < 0.5, kinds
        assert AP.OUTPUT in r and "SITUATION" in r and "more_lookups" in r
    assert "POINT AT WHAT YOU TALK ABOUT" in AP.rules(["app"]) and "POINT AT" not in AP.rules(["market"])
    assert "THE REPAIR SHOP" in AP.rules(["act"]) and "never a test, placeholder or duplicate" in AP.CORE


def test_more_lookups_opens_every_lookup_for_the_next_round(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    bodies = []
    final = json.dumps({"kind": "answer", "answer": "done"})
    replies = [{"content": [{"type": "tool_use", "id": "t1", "name": "more_lookups", "input": {}}], "usage": {}},
               {"content": [{"type": "text", "text": final}], "usage": {}}]

    def post(url, headers, body, timeout=60):
        bodies.append(json.loads(json.dumps(body)))
        return replies[len(bodies) - 1]

    L = ask.Lookups(None, allowed={"market", "knowledge"})
    txt, _ = ask.run_claude("sys", [], "hi", L, [], post=post, model="m")
    first = [t["name"] for t in bodies[0]["tools"]]
    assert first == ["market", "knowledge", "more_lookups"] or sorted(first) == sorted(["market", "knowledge", "more_lookups"])
    assert "cache_control" in bodies[0]["tools"][-1]
    assert len(bodies[1]["tools"]) == len(ask.TOOLS) and L.allowed is None and ask.parse(txt)["answer"] == "done"


def test_books_block_comes_from_the_one_list(tmp_path):
    k = tmp_path / "knowledge"
    k.mkdir()
    (k / "strategy_status.json").write_text(json.dumps({"account": "B", "strategies": {
        "B": {"name": "The $500 NDAX book", "status": "ACTIVE"}, "X": {"name": "15-minute Explorer", "status": "EVIDENCE", "verdict": "wont_take_again"},
        "H": {"name": "Hourly watch", "status": "PARKED"}}}))
    b = AP.books_block(tmp_path)
    assert "THE ACCOUNT is The $500 NDAX book" in b and "15-minute Explorer, won't take again" in b and "Parked" in b and "Hourly watch" in b


def test_plain_words_only_the_terms_asked_plus_a_kind_default(tmp_path):
    k = tmp_path / "knowledge"
    k.mkdir()
    terms = [{"term": t, "plain": "p", "meaning": "m", "ours": "o"} for t in ("RSI (relative strength index)", "ATR (average true range)",
                                                                               "50-day average (MA50)", "MAR ratio")]
    (k / "glossary.json").write_text(json.dumps({"terms": terms}))
    w = AP.plain_words(tmp_path, "what is the ATR?", ["know"])
    assert "ATR (average" in w and "RSI" not in w and "MAR ratio" not in w
    assert "RSI" in AP.plain_words(tmp_path, "can we buy?", ["market"]) and "50-day average" in AP.plain_words(tmp_path, "x", ["market"])
    assert all(t["term"] in AP.plain_words(tmp_path, "x", ["full"]) for t in terms)


def test_the_situation_line_is_code_and_never_blocks(monkeypatch):
    from jarvis.service import exposure, ndax_book, stance

    monkeypatch.setattr(exposure, "state", lambda j: {"dial_words": "CLOSED: no new buys", "why": ["Bitcoin closed under its 200-day"]})
    monkeypatch.setattr(stance, "latest", lambda j: {"day": "2026-10-16", "source": "brain", "view": "Cautious: wait for the dial."})
    monkeypatch.setattr(ndax_book, "status", lambda j: {"value_cad": 480.0, "return_pct": -4.0, "started": "2026-10-11", "positions": {},
                                                        "brakes": {"paused": False, "fired": {}}})
    s = AP.situation_line(None)
    assert s.startswith("SITUATION (live, one line): The exposure dial is CLOSED: no new buys") and "Cautious: wait" in s and "only cash" in s

    def boom(j):
        raise RuntimeError("down")
    monkeypatch.setattr(exposure, "state", boom)
    monkeypatch.setattr(stance, "latest", boom)
    monkeypatch.setattr(ndax_book, "status", boom)
    assert "could not be read" in AP.situation_line(None)


def test_ask_sends_the_kind_its_lookups_and_the_situation_first(monkeypatch):
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    monkeypatch.setattr(AP, "situation_line", lambda jj: "SITUATION (live, one line): The exposure dial is OPEN.")
    seen = {}

    def fake(s, h, u, t, log):
        seen.update(system=s, user=u, allowed=t.allowed)
        return json.dumps({"kind": "answer", "answer": "Yes, the dial is open."}), {"in": 1, "out": 1}

    A = ask.Ask(j, providers={"gemini": fake})
    r = A.ask("o", "Can we buy today?", mode="everyday")
    assert seen["user"].startswith("SITUATION (live, one line)") and "QUESTION: Can we buy today?" in seen["user"]
    assert seen["allowed"] == AP.tool_names(["market"]) and "HOW ANANTA REASONS" in seen["system"] and "THE ACTIONS" not in seen["system"]
    tm = r["timing"]
    assert tm["kinds"] == ["market"] and tm["lookups_offered"] == len(AP.tool_names(["market"])) + 1 and tm["rules_chars"] == len(seen["system"])
    A.ask("o", "and before that?", thread=r["thread"], mode="everyday")     # a short follow-up keeps the kind
    assert seen["allowed"] == AP.tool_names(["market"])
    A.ask("o", "why?", thread=r["thread"], mode="everyday")                 # "why?" becomes "explain ... the decision-chain gates"
    assert AP.tool_names(["market"]) <= seen["allowed"] and "knowledge" in seen["allowed"]
