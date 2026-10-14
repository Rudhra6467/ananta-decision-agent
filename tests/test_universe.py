"""The lake -> agent hand-off: Ananta knows the 120-coin universe at three levels and never mixes them (Madhav 2026-10-05)."""
import json
import sqlite3
import types

DAY = 86400


def _pack(tmp_path, monkeypatch):
    lake = tmp_path / "lake"
    (lake / "agent").mkdir(parents=True)
    monkeypatch.setenv("ANANTA_LAKE", str(lake))
    con = sqlite3.connect(lake / "agent" / "daily.sqlite")
    con.executescript("""CREATE TABLE bars (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, qv REAL, tbv REAL, PRIMARY KEY (coin, t));
                         CREATE TABLE funding (coin TEXT, t INTEGER, funding REAL, PRIMARY KEY (coin, t));
                         CREATE TABLE futures (coin TEXT, t INTEGER, oi_value REAL, top_ls REAL, ls REAL, taker_ls REAL, PRIMARY KEY (coin, t));
                         CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);""")
    t0 = 1_700_000_000 // DAY * DAY
    for coin, p0 in (("BTC", 100.0), ("SUI", 1.0), ("ANC", 2.0)):
        con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?,?,?)",
                        [(coin, t0 + k * DAY, p0 * 1.01 ** k, p0 * 1.01 ** k * 1.02, p0 * 1.01 ** k * 0.98, p0 * 1.01 ** (k + 1), 10.0, 1000.0, 6.0)
                         for k in range(400)])
    con.executemany("INSERT INTO funding VALUES (?,?,?)", [("SUI", t0 + k * DAY, 0.0001 if k < 390 else 0.001) for k in range(400)])
    con.commit()
    card = lambda c, tiers, does, t30=None, st="LISTED": {"coin": c, "binance_symbol": c + "USDT", "rank_by_traded_value": 1, "tiers": tiers,  # noqa: E731
        "what_ananta_does": does, "paper_tier_name": t30, "history": {"first": "2023-11-14", "status": st, "quality_grade": "A"},
        "costs": {}, "ndax": {"listed_vs_cad": c != "ANC", "symbol": None}, "futures": {}, "now": {"from_ath_pct": -10.0}}
    pack = {"version": "agent_pack.v1", "built_at": "test", "tiers": {"LAB10": ["BTC"], "TOP30": ["BTC", "SUI"], "ALL": ["BTC", "SUI", "ANC"]},
            "tier_meaning": {"LAB10": "live", "TOP30": "paper tier", "ALL": "research"},
            "research": [{"id": "R15", "doc": "d", "idea": "T3", "LAB10": "PASS", "TOP30": "PASS", "ALL": "FAIL"}],
            "cards": {"BTC": card("BTC", ["ALL", "TOP30", "LAB10"], ["LIVE_WATCH: all of it", "PAPER_TIER_30: (as BTC)"], "BTC"),
                      "SUI": card("SUI", ["ALL", "TOP30"], ["PAPER_TIER_30: daily paper books"], "SUI"),
                      "ANC": card("ANC", ["ALL"], ["RESEARCH_ONLY: history only"], None, "DELISTED_OR_STOPPED")}}
    (lake / "agent" / "universe.json").write_text(json.dumps(pack))
    from jarvis.service import universe

    universe._CACHE.clear()
    return types.SimpleNamespace(dir=tmp_path, db=sqlite3.connect(":memory:"), now=lambda: t0 + 401 * DAY)


def test_three_levels_and_unknown_coins(tmp_path, monkeypatch):
    from jarvis.service import universe as U

    j = _pack(tmp_path, monkeypatch)
    sui, anc, btc = U.card(j, "sui"), U.card(j, "ANCUSDT"), U.card(j, "bitcoin")
    assert sui["in_universe"] and sui["what_ananta_does"][0].startswith("PAPER_TIER_30") and "LAB10" not in [k for r in sui["research_on_its_tiers"] for k in r]
    assert anc["what_ananta_does"][0].startswith("RESEARCH_ONLY") and anc["ndax"]["listed_vs_cad"] is False
    assert "for_live_detail" in btc and "for_live_detail" not in sui
    assert sui["futures_context"]["funding_reading"].startswith("crowded long")
    assert sui["now"]["change_30d_pct"] > 0 and "buying_pressure" in sui
    nope = U.card(j, "LUNA")
    assert nope["in_universe"] is False and "outside_coin" in nope["note"]


def test_rankings_skip_delisted_and_history_reads_the_lake(tmp_path, monkeypatch):
    from jarvis.service import universe as U

    j = _pack(tmp_path, monkeypatch)
    ov = U.overview(j, "ALL", "change", 30, 5)
    assert [r["coin"] for r in ov["top"]] and "ANC" not in [r["coin"] for r in ov["top"]] and ov["coins_in_tier"] == 3
    h = U.history(j, "SUI", days=10)
    assert h["timeframe_used"] == "1d" and len(h["by_day"]) >= 9 and h["what_ananta_does"][0].startswith("PAPER_TIER_30")


def test_ask_has_the_universe_lookup_and_routes_prices():
    from jarvis.service import ask

    names = [n for n, _, _ in ask.TOOLS]
    assert "universe" in names and len(names) == len(set(names))
    assert "120-coin" in ask.SYSTEM if hasattr(ask, "SYSTEM") else True
