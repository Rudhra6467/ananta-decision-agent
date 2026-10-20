"""The blind shadow lane (OD-SHADOW-LANE, Oct 20): a hash-chained, append-only log of each pre-registered rule's trigger state.

It must: chain every row and catch any edit, deletion or reordering; keep no outcome and return no result before 2026-12-15; never
write to the agent folder's databases or reach an order path; and never break the daily close or the 15-minute jobs that call it.
"""
import ast
import calendar
import hashlib
import json
import re
import sqlite3
import types
from pathlib import Path

import pytest

from jarvis.service import shadow

ROOT = Path(__file__).resolve().parents[1]
DAY = 86400
NOW = calendar.timegm((2026, 10, 23, 1, 0, 0))            # in the window: the Oct 22 candle closed an hour ago
T_LAST = calendar.timegm((2026, 10, 22, 0, 0, 0))         # the last closed daily candle (opens Oct 22, closes Oct 23 00:00)
W0 = shadow.WINDOW_START


def _t(y, m, d, h=0, mi=0):
    return calendar.timegm((y, m, d, h, mi, 0))


def _candles(closes, t_last=T_LAST, wick=0.01):
    t0 = t_last - (len(closes) - 1) * DAY
    out, prev = [], closes[0]
    for k, c in enumerate(closes):
        o = prev
        out.append((t0 + k * DAY, o, max(o, c) * (1 + wick), min(o, c) * (1 - wick), c, 100.0))
        prev = c
    return out


def _db(path: Path, ddl: list[str], rows: dict | None = None) -> None:
    con = sqlite3.connect(path)
    for d in ddl:
        con.execute(d)
    for table, rs in (rows or {}).items():
        if rs:
            con.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(rs[0]))})", rs)
    con.commit()
    con.close()


JARVIS_DDL = [
    "CREATE TABLE evidence_trades (id TEXT PRIMARY KEY, watch TEXT, coin TEXT, source TEXT, signal_t INTEGER, signal_day TEXT, entry_t INTEGER, "
    "entry_day TEXT, entry REAL, stop REAL, exit_t INTEGER, exit_day TEXT, exit REAL, net_usd REAL, status TEXT, why TEXT, exit_why TEXT, "
    "regime TEXT, detail TEXT)",
    "CREATE TABLE brain_decisions (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, triggers TEXT, action TEXT, confidence REAL, size_pct REAL, "
    "price REAL, plan TEXT, thesis TEXT, knowledge TEXT, model TEXT, cost_usd REAL, trade_id TEXT, random_id TEXT, after_1d_pct REAL, "
    "after_5d_pct REAL, note TEXT, after_1d_ex REAL, after_5d_ex REAL)",
    "CREATE TABLE brain_queue (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, trigger TEXT, detail TEXT, state TEXT)",
    "CREATE TABLE brain_unreviewed (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, trigger TEXT, score REAL, reason TEXT, price REAL, "
    "after_1d_pct REAL, after_5d_pct REAL, after_1d_ex REAL, after_5d_ex REAL)",
    "CREATE TABLE bold_decisions (id TEXT PRIMARY KEY, day TEXT, t INTEGER, dial REAL, action TEXT, coin TEXT, plan TEXT, price REAL, "
    "stop REAL, thesis TEXT, why TEXT, model TEXT, cost_usd REAL, trade_id TEXT, random_id TEXT, note TEXT)",
    "CREATE TABLE missed_moves (id TEXT PRIMARY KEY, day TEXT, coin TEXT, low_t INTEGER, high_t INTEGER, low REAL, high REAL, move_pct REAL, "
    "move_atr REAL, label TEXT, saw TEXT, kind TEXT, at_zone TEXT, regime TEXT, pattern TEXT, why TEXT, tier TEXT DEFAULT 'LIVE10', "
    "miss_class TEXT, caught_books TEXT, caught_allowed INTEGER, caught_pnl_usd REAL, caught_scored_t INTEGER)",
    "CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, sleeve TEXT, qty REAL, px REAL, bid REAL, ask REAL, fee REAL, why TEXT)",
    "CREATE TABLE manual_fills (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, side TEXT, usd REAL, units REAL, px REAL, cost REAL, reason TEXT, "
    "by TEXT, trigger TEXT)",
    "CREATE TABLE zone_visits (id TEXT PRIMARY KEY, t INTEGER, day TEXT, coin TEXT, bot REAL, top REAL, atr REAL, groups TEXT, history TEXT, "
    "outcome TEXT, outcome_day TEXT)",
]


def _ev(tid, watch, coin, entry_t, entry, stop, exit_t=None, exit_px=None, net=None, why=None, detail=None, source="brain"):
    return (tid, watch, coin, source, entry_t, None, entry_t, None, entry, stop, exit_t, None, exit_px, net,
            "CLOSED" if exit_t else "OPEN", "thesis", why, "ALLOWED", json.dumps(detail or {}))


@pytest.fixture
def agent(tmp_path):
    a = tmp_path / "agent"
    a.mkdir()
    rise = [100 * 1.001 ** k for k in range(300)]
    btc = _candles(rise)
    aaa = _candles([1.0 * 1.001 ** k for k in range(298)] + [1.001 ** 297 * 1.1, 1.001 ** 297 * 1.21])  # two breakouts in a row
    ccc = _candles([1.0] * 300)
    ccc[-2] = (ccc[-2][0], 0.97, 0.99, 0.94, 0.96, 100.0)                  # Oct 21: touched 0.95 live, closed above it
    ccc[-1] = (ccc[-1][0], 0.96, 0.97, 0.92, 0.93, 100.0)                  # Oct 22: closed under it
    d1 = [(c, *b, 50e6) for c, D in (("BTC", btc), ("AAA", aaa), ("CCC", ccc)) for b in D]
    m5 = []
    for c, px in (("BTC", 130.0), ("AAA", 1.3)):
        for k in range(2 * 288 + 12):                                       # Oct 21 and 22 whole, Oct 23 to 00:55
            t = W0 + 300 * k
            h = px * (2.0 if t == _t(2026, 10, 23, 0, 30) and c == "AAA" else 1.001)
            m5.append((c, t, px, h, px * 0.999, px, 1.0))
    _db(a / "universe_bars.sqlite", ["CREATE TABLE d1 (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, qv REAL, PRIMARY KEY (coin, t))",
                                     "CREATE TABLE m5 (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, t))"],
        {"d1": d1, "m5": m5})
    _db(a / "explorer_bars.sqlite", ["CREATE TABLE bars (coin TEXT, tf TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, tf, t))"],
        {"bars": [("BTC", "1d", *b) for b in btc]})
    det = {"days": 15, "trail_atr": 3.0, "atr": 0.02, "stop0": 0.95, "target": 1.3, "stop_moves": []}
    ev = [_ev("tC", "JARVIS", "CCC", _t(2026, 10, 19, 12), 1.0, 0.95, _t(2026, 10, 21, 6), 0.95, -5.4, "stop (live price)", det),
          _ev("tR", "JARVIS_RANDOM", "AAA", _t(2026, 10, 19, 12), 1.2, 1.1, detail=det),
          _ev("tB", "JARVIS_BOLD", "BTC", _t(2026, 10, 21, 0, 10), 120.0, 110.0, detail={"days": 20}),
          _ev("tH", "H07-UA", "BTC", _t(2026, 10, 20, 0), 119.0, None, source="daily")]
    after = (1.0, -3.0, None, 0.5, -1.2)
    bd = [("d0", _t(2026, 10, 20, 3), "ADA", "{}", "PASS", 50, None, 0.6, "{}", "", "[]", "m", 0.02, None, None, *after[:2], None, *after[3:]),
          ("d1", _t(2026, 10, 21, 3), "CCC", json.dumps({"zone_entry": {}, "_rank": {"score": 3.5}}), "TAKE", 45, 25, 1.0, json.dumps({"days": 15}),
           "t", "[]", "m", 0.02, "tC", "tR", *after[:2], None, *after[3:]),
          ("d2", _t(2026, 10, 22, 3), "XRP", json.dumps({"attention_high": {"why": []}}), "PASS", 60, None, 1.3, "{}", "", "[]", "m", 0.02,
           None, None, *after[:2], None, *after[3:])]
    bq = [("q1", _t(2026, 10, 21, 1), "XRP", "attention_high", "{}", "DONE"),
          ("q2", _t(2026, 10, 21, 2), "ADA", "zone_entry", "{}", "FAILED: table brain_decisions has 20 columns"),
          ("q3", _t(2026, 10, 22, 2), "ADA", "zone_entry", "{}", "DROPPED: today's AI budget is used up"),
          ("q4", _t(2026, 10, 23, 0, 10), "ADA", "attention_high", "{}", "DONE")]
    bu = [("u1", _t(2026, 10, 21, 5), "SOL", "zone_entry", 1.9, "ranked too low (1.9: ...)", 150.0, 1.0, 2.0, 0.1, 0.2),
          ("u2", _t(2026, 10, 21, 6), "ARB", "zone_entry", None, "monitoring only: the registry keeps ZONE_TOUCH from waking the brain", 0.2,
           1.0, 2.0, 0.1, 0.2)]
    bold = [("b1", "2026-10-21", _t(2026, 10, 21, 0, 10), 1.0, "TAKE", "BTC", "TREND", 120.0, 110.0,
             "The dial is open and the trend portfolio (T3) is the measured edge.", "others lack the trend", "m", 0.03, "tB", "tBR", None)]
    mm = [("2026-10-21:LIVE10:BTC", "2026-10-21", "BTC", _t(2026, 10, 21, 10), _t(2026, 10, 21, 18), 118.0, 126.0, 6.8, 2.1, "CAUGHT",
           json.dumps({"traded": ["H07-UA evidence trade"], "saw": []}), "breakout", None, "ALLOWED", "breakout | no zone | ALLOWED", "",
           "LIVE10", None, json.dumps([{"book": "H07-UA", "pnl_usd": 3.2}]), 1, 3.2, NOW - 3600)]
    _db(a / "jarvis.sqlite", JARVIS_DDL, {"evidence_trades": ev, "brain_decisions": bd, "brain_queue": bq, "brain_unreviewed": bu,
                                          "bold_decisions": bold, "missed_moves": mm})
    evs = [(1, _t(2026, 10, 20, 12), "ORDER", "BTC", "BTC-old", json.dumps({"kind": "ORDER", "shadow": "NO_TYPE", "tags": {"room": 0.01}})),
           (2, _t(2026, 10, 21, 12), "ORDER", "BTC", "BTC-1", json.dumps({"kind": "ORDER", "setup": "E6", "type": "SHORT_TERM", "limit": 119.0,
                                                                           "shadow": "NO_TYPE", "tags": {"room": 0.004, "type_rule": "NO_TYPE"}})),
           (3, _t(2026, 10, 21, 12, 5), "ORDER", "ETH", "ETH-1", json.dumps({"kind": "ORDER", "setup": "E1", "tags": {"room": 0.04}})),
           (4, _t(2026, 10, 21, 12, 10), "FILLED", "ETH", "ETH-1", json.dumps({"kind": "FILLED", "setup": "E1", "entry": 2400.0, "stop": 2380.0,
                                                                                 "target": 2450.0})),
           (5, _t(2026, 10, 21, 14), "CLOSED", "ETH", "ETH-1", json.dumps({"kind": "CLOSED", "bell": "X1_STOP", "net_usd": -1.5}))]
    _db(a / "explorer_book.sqlite", ["CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT)",
                                     "CREATE TABLE trades (id TEXT PRIMARY KEY, coin TEXT, shadow TEXT, exit_t INTEGER, net REAL, json TEXT)"],
        {"events": evs})
    pf_ddl = ["CREATE TABLE decisions (day_t INTEGER PRIMARY KEY, json TEXT)", "CREATE TABLE fills (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, json TEXT)"]
    _db(a / "portfolio_book.sqlite", pf_ddl,
        {"decisions": [(_t(2026, 10, 21), json.dumps({"ratings": {"BTC": {"rating": "OUT", "hold": False, "why": ["closed below its 20-day"]}}}))],
         "fills": [(1, _t(2026, 10, 20, 0, 5), json.dumps({"t": _t(2026, 10, 20, 0, 5), "book": "MAIN", "coin": "BTC", "side": "BUY", "usd": 200.0,
                                                          "px": 119.0, "cost": 0.6}))]})
    _db(a / "portfolio_book_t30.sqlite", pf_ddl)
    return a


def _j(a, now=NOW):
    return types.SimpleNamespace(dir=a, now=lambda: now)


def _fake_boards(monkeypatch):
    from jarvis.service import reads_watch, zones_watch

    reads = {"coins": [{"coin": "ADA", "reads": [{"variant": "M2a", "name": "the dip", "state": "CLOSE", "met": 3, "of": 4}]}]}
    row = {"coin": "ADA", "day": "2026-10-22", "price": 0.6, "atr": 0.02, "tested": None, "reactions": [{"id": "F6", "present": True}],
           "inside": [{"bot": 0.55, "top": 0.62, "kinds": ["SWING"], "state": "INSIDE", "history": "SUPPORTED",
                       "recent": {"entered": "2026-10-20", "so_far": "OPEN"}, "groups": ["swing"]}]}
    row["attention"] = zones_watch.attention(row, reads["coins"][0])
    monkeypatch.setattr(zones_watch, "board", lambda j: {"coins": [row]})
    monkeypatch.setattr(reads_watch, "board", lambda j: reads)


def _snapshot(d: Path) -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir())}


# ---------------------------------------------------------------------------------------------------------------- the chain
def test_each_row_hash_covers_the_previous_hash_and_its_own_canonical_json(tmp_path):
    root = tmp_path / "lane"
    assert shadow.verify(root) == {"ok": True, "rows": 0, "broken_at_line": None, "note": "no rows yet"}
    shadow.append([{"review": "R31", "x": 1}, {"review": "R32", "y": (1, 2), "z": float("nan")}], root)
    shadow.append([{"review": "R35", "w": "ok"}], root)
    rows = [json.loads(x) for x in (root / shadow.LOG).read_text().splitlines()]
    prev = "genesis"
    for r in rows:
        assert r["prev_hash"] == prev
        body = json.dumps({k: v for k, v in r.items() if k != "hash"}, sort_keys=True, separators=(",", ":"))
        assert r["hash"] == hashlib.sha256((prev + body).encode()).hexdigest()
        prev = r["hash"]
    assert rows[1]["y"] == [1, 2] and rows[1]["z"] is None                    # stored the way it is re-read, so the hash holds
    assert shadow.verify(root) == {"ok": True, "rows": 3, "broken_at_line": None, "note": "chain intact"}
    assert shadow._tail_hash(root / shadow.LOG) == rows[-1]["hash"]


@pytest.mark.parametrize("how", ["edit", "delete", "reorder", "insert", "rehash_one"])
def test_any_tampering_breaks_the_chain_at_that_line(tmp_path, how):
    root = tmp_path / "lane"
    shadow.append([{"review": "R31", "n": k, "price": 1.0 + k} for k in range(5)], root)
    p = root / shadow.LOG
    lines = p.read_text().splitlines()
    if how == "edit":
        lines[2] = lines[2].replace('"price":3.0', '"price":3.5')
        at = 3
    elif how == "delete":
        del lines[1]
        at = 2
    elif how == "reorder":
        lines[1], lines[2] = lines[2], lines[1]
        at = 2
    elif how == "insert":
        lines.insert(3, json.dumps({"review": "R31", "n": 99, "prev_hash": "x", "hash": "y"}))
        at = 4
    else:                                                                    # recompute one row's own hash: the next row still breaks
        r = json.loads(lines[2])
        r["price"] = 9.9
        r["hash"] = hashlib.sha256((r["prev_hash"] + shadow._canon(r)).encode()).hexdigest()
        lines[2] = json.dumps(r)
        at = 4
    p.write_text("\n".join(lines) + "\n")
    v = shadow.verify(root)
    assert not v["ok"] and v["broken_at_line"] == at and "broken" in v["note"]


def test_an_outcome_field_is_refused_and_nothing_is_written(tmp_path):
    root = tmp_path / "lane"
    for bad in ({"review": "R31", "net_usd": -5.4}, {"review": "R38", "allowed_in_it": [{"book": "T3", "pnl_usd": 1.0}]},
                {"review": "R34", "after_5d_ex": 0.3}):
        with pytest.raises(ValueError, match="keeps no outcomes"):
            shadow.append([{"review": "R33", "ok": 1}, bad], root)
    assert not (root / shadow.LOG).exists()


# ---------------------------------------------------------------------------------------------------------------- the date guard
def test_no_result_before_checkpoint_60(tmp_path):
    root = tmp_path / "lane"
    shadow.append([{"review": "R32", "would": "BUY_NEXT_OPEN"}], root)
    assert shadow.SEALED_UNTIL == calendar.timegm((2026, 12, 15, 0, 0, 0))
    for now in (NOW, calendar.timegm((2026, 12, 14, 23, 59, 59)), shadow.SEALED_UNTIL - 1):
        with pytest.raises(shadow.Sealed, match="blind until 2026-12-15"):
            shadow.results(root, now=now)
    with pytest.raises(shadow.Sealed):
        shadow.results(root)                                                 # today's clock (Oct 2026) is sealed too
    got = shadow.results(root, now=shadow.SEALED_UNTIL)
    assert got["verify"]["ok"] and len(got["by_review"]["R32"]) == 1


def test_no_round_returns_or_logs_an_outcome(agent, tmp_path, monkeypatch):
    _fake_boards(monkeypatch)
    root = tmp_path / "lane"
    outs = [shadow.run_daily(_j(agent), root, NOW), shadow.run_15m(_j(agent), root, NOW), shadow.verify(root)]
    for o in outs:
        assert not shadow._keys(json.loads(json.dumps(o))) & shadow.FORBIDDEN
    rows = shadow._rows(root)
    assert rows and not set().union(*(shadow._keys(r) for r in rows)) & shadow.FORBIDDEN
    text = (root / shadow.LOG).read_text()
    assert "-5.4" not in text and "caught_pnl" not in text and "X1_STOP" not in text      # the touch trade's net, the catch money, a result
    public = [n for n, f in vars(shadow).items() if callable(f) and not n.startswith("_") and getattr(f, "__module__", "") == shadow.__name__]
    assert not [n for n in public if re.search(r"total|win|pnl|profit|score|outcome", n, re.I)], "a result function outside results()"


# ---------------------------------------------------------------------------------------------------------------- the rules on fixtures
def test_daily_round_records_each_reviews_trigger_state(agent, tmp_path):
    root = tmp_path / "lane"
    res = shadow.run_daily(_j(agent), root, NOW)
    assert res["errors"] == [] and res["verify_ok"]
    rows = shadow._rows(root)
    by = {}
    for r in rows:
        by.setdefault((r["review"], r["kind"]), []).append(r)
    # R31: the touch, then the close rule: Oct 21 closed above the stop (HOLD, no trail on the touch day), Oct 22 closed under it
    t, = by[("R31", "touch")]
    assert t["trade_id"] == "tC" and t["level_at_touch"] == 0.95 and t["has_minute"] and t["cell"] == "A" and t["in_window"]
    cr = by[("R31", "close_rule")]
    assert [(r["candle_day"], r["would"]) for r in cr] == [("2026-10-21", "HOLD"), ("2026-10-22", "EXIT_AT_CLOSE")]
    assert cr[0]["level_next"] == 0.95 and cr[1]["would_price"] == 0.93
    # R32: three closes since the window start; AAA broke out on the last two, one trade per coin
    days = by[("R32", "close_day")]
    assert len(days) == 3 and all("AAA" in d["eligible_A"] for d in days)
    sig = {(s["rule"], s["candle_t"]): s for s in by[("R32", "signal")] if s["coin"] == "AAA"}
    assert ("R38-D5", T_LAST - DAY) in sig and ("R38-D5", T_LAST) in sig
    s = sig[("R38-D5", T_LAST - DAY)]
    assert s["close_t"] == T_LAST and s["regime"] == "ALLOWED" and s["tier"] == "A" and s["cost_side"] > 0
    if s["would"] == "BUY_NEXT_OPEN":
        assert s["entry_open_t"] == T_LAST and s["exit_open_t"] == T_LAST + 5 * DAY
        assert sig[("R38-D5", T_LAST)]["would"] in ("IGNORED: this coin's trade is still open", "NO_TRADE: at a support zone")
    # R33: the TAKE pair with both legs; R34: decisions and unreviewed wakes since the window, without their after_ columns
    tk, = by[("R33", "take")]
    assert tk["legs"]["pick"]["id"] == "tC" and tk["legs"]["twin"]["watch"] == "JARVIS_RANDOM"
    assert sorted(r["decision_id"] for r in by[("R34", "decision")]) == ["d1", "d2"]
    assert {r["unreviewed_id"]: r["group"] for r in by[("R34", "unreviewed")]} == {"u1": "ranked_out", "u2": "monitoring_only"}
    # R36: orders and fills in the window (the pre-window order and the CLOSED result are never read)
    assert [(r["kind"], r["seq"], r.get("group")) for r in by[("R36", "order")] + by[("R36", "fill")]] == \
        [("order", 2, "NO_TYPE"), ("order", 3, "real"), ("fill", 4, None)]
    # R37: the bold TAKE cites T3, and T3 rated BTC OUT at that close
    b, = by[("R37", "bold")]
    assert b["cites_t3"] and b["t3"]["hold"] is False and b["t3"]["source"] == "T3 lab 10"
    # R38: the frozen allowed books in the move: H07-UA's and the bold book's trades, and the T3 book's BTC holding
    m, = by[("R38", "move")]
    assert m["would"] == "CAUGHT_ALLOWED" and {x["book"] for x in m["allowed_in_it"]} == {"H07", "JARVIS_BOLD", "T3"}
    # the lane's own rows: the brain's wakes by state (lost runs) and one run row
    wk = {r["day"]: r["by_state"] for r in by[("LANE", "wakes_day")]}
    assert wk["2026-10-21"] == {"DONE": 1, "FAILED": 1} and wk["2026-10-22"] == {"DROPPED_BUDGET": 1}
    assert len(by[("LANE", "run")]) == 1
    # the run log line the run checker reads
    line = (root / shadow.RUN_LOG).read_text().strip()
    assert re.fullmatch(r"\[2026-10-23 01:00\] daily rows=\d+ status=ok", line)


def test_a_second_round_adds_no_duplicate_rows(agent, tmp_path):
    root = tmp_path / "lane"
    shadow.run_daily(_j(agent), root, NOW)
    n = len(shadow._rows(root))
    res = shadow.run_daily(_j(agent), root, NOW + 600)
    assert res["rows"] == 1 and len(shadow._rows(root)) == n + 1               # only the run row
    assert shadow.verify(root)["ok"]


def test_one_trade_per_coin_away_from_support(agent, tmp_path, monkeypatch):
    monkeypatch.setattr(shadow, "_zone_hit", lambda D, low, atr: None)
    root = tmp_path / "lane"
    shadow.run_daily(_j(agent), root, NOW)
    sig = {s["candle_t"]: s["would"] for s in shadow._rows(root) if s.get("kind") == "signal" and s["coin"] == "AAA" and s["rule"] == "R38-D5"}
    assert sig == {T_LAST - DAY: "BUY_NEXT_OPEN", T_LAST: "IGNORED: this coin's trade is still open"}


def test_15_minute_round_records_the_attention_board_and_the_intraday_cross(agent, tmp_path, monkeypatch):
    _fake_boards(monkeypatch)
    root = tmp_path / "lane"
    res = shadow.run_15m(_j(agent), root, NOW)
    assert res["errors"] == []
    rows = shadow._rows(root)
    att, = [r for r in rows if r["review"] == "R35"]
    assert att["score"] == 7 and att["level"] == "HIGH" and att["parts_sum_matches"] and att["queued_today"]
    assert att["parts"] == {"in_zone": 1, "supported_kind": 2, "came_down_5d": 1, "market_allowed": 2, "setup": 1}
    x = [r for r in rows if r.get("kind") == "cross_5m"]
    # D5's level is crossed at 00:30; H20 needs yesterday's close at or under its own 20-day high, and AAA closed above it
    assert [(r["coin"], r["rule"], r["bar_t"]) for r in x] == [("AAA", "R38-D5-X5M", _t(2026, 10, 23, 0, 30))]
    assert all(r["prereg"] is False for r in x)
    shadow.run_15m(_j(agent), root, NOW + 60)                               # same slot, same day: nothing new but the run row
    assert len(shadow._rows(root)) == len(rows) + 1


def test_five_minute_bars_are_copied_once_per_complete_day(agent, tmp_path):
    root = tmp_path / "lane"
    shadow.run_daily(_j(agent), root, NOW)
    con = sqlite3.connect(root / "bars5m_2026-10.sqlite")
    assert con.execute("SELECT COUNT(*), MIN(t), MAX(t) FROM bars5m").fetchone() == (2 * 2 * 288, W0, W0 + 2 * DAY - 300)
    con.close()
    shadow.run_daily(_j(agent), root, NOW + 600)
    con = sqlite3.connect(root / "bars5m_2026-10.sqlite")
    assert con.execute("SELECT COUNT(*) FROM bars5m").fetchone()[0] == 2 * 2 * 288       # Oct 23 is not complete yet
    con.close()


# ---------------------------------------------------------------------------------------------------------------- never writes, never orders
def test_the_lane_never_writes_the_agent_folder(agent, tmp_path, monkeypatch):
    _fake_boards(monkeypatch)
    before = _snapshot(agent)
    shadow.run_daily(_j(agent), tmp_path / "lane", NOW)
    shadow.run_15m(_j(agent), tmp_path / "lane", NOW)
    assert _snapshot(agent) == before                                       # same files, same bytes: jarvis.sqlite included
    con = shadow._ro(agent / "jarvis.sqlite")
    with pytest.raises(sqlite3.OperationalError):
        con.execute("INSERT INTO brain_queue VALUES ('x', 1, 'BTC', 'wake', '{}', 'NEW')")
    with pytest.raises(FileNotFoundError):
        shadow._ro(agent / "missing.sqlite")
    assert not (agent / "missing.sqlite").exists()


FORBIDDEN_CALLS = {"close_at", "open_eye_trade", "open_trade", "wake", "wake_brain", "scan", "process", "manage_live", "place", "place_order",
                   "approve", "reject", "set_kill", "set_mode", "step", "decide", "apply", "record_verdicts", "watch", "settle_passes",
                   "settle_unreviewed", "score_catches", "build", "commit_verdict", "save", "plan"}
FORBIDDEN_MODULES = {"hands", "ndax_book", "trade_guard", "account", "bold", "brain", "eye", "manual", "mandate", "books", "strategy_status",
                     "universe_watch", "stance", "officer", "notify", "alerts", "worker", "universe_explorer", "tier30", "evidence_live"}


def test_shadow_py_has_no_order_path_and_no_write_to_the_agent_databases():
    src = (ROOT / "jarvis" / "service" / "shadow.py").read_text()
    tree = ast.parse(src)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            imported |= {a.name for a in n.names} | {(n.module or "").split(".")[-1]}
        elif isinstance(n, ast.Import):
            imported |= {a.name.split(".")[-1] for a in n.names}
    assert not imported & FORBIDDEN_MODULES, imported & FORBIDDEN_MODULES
    calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not calls & FORBIDDEN_CALLS, calls & FORBIDDEN_CALLS
    # every database connection: read-only (_ro) or the lane's own 5-minute copy under its folder
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    owners = {f for f, node in fns.items() for c in ast.walk(node)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "connect"}
    assert owners == {"_ro", "archive_bars5m"}
    assert 'f"file:{path}?mode=ro", uri=True' in ast.get_source_segment(src, fns["_ro"])
    assert "ctx.root /" in ast.get_source_segment(src, fns["archive_bars5m"])
    writes = [s.value for s in ast.walk(tree) if isinstance(s, ast.Constant) and isinstance(s.value, str)
              and re.search(r"\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER)\b", s.value)]
    assert writes and all("bars5m" in w for w in writes), writes


# ---------------------------------------------------------------------------------------------------------------- the wiring
def test_the_hooks_swallow_and_log_a_shadow_exception(agent, tmp_path, monkeypatch):
    monkeypatch.setenv("ANANTA_SHADOW_DIR", str(tmp_path / "lane"))

    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(shadow, "run_daily", boom)
    monkeypatch.setattr(shadow, "run_15m", boom)
    out = {"rules": {"A": 1}}
    shadow.hook_daily(_j(agent), out)
    shadow.hook_15m(_j(agent), out)
    assert out["rules"] == {"A": 1} and "disk full" in out["shadow"]["error"]
    assert not [k for k in out if k.endswith("_error")]                      # the round's own failed-steps list stays as it was
    lines = (tmp_path / "lane" / shadow.ERR_LOG).read_text().splitlines()
    assert len(lines) == 2 and all(re.match(r"\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC\] (daily|15m) round: RuntimeError: disk full", x) for x in lines)


def test_one_failing_rule_never_stops_the_others(agent, tmp_path, monkeypatch):
    monkeypatch.setattr(shadow, "DAILY_RULES", (("R31", lambda c: 1 / 0), ("R33", shadow.r33)))
    root = tmp_path / "lane"
    res = shadow.run_daily(_j(agent), root, NOW)
    assert res["errors"] == ["R31"] and res["rows_by_rule"] == {"R33": 1}
    err = [r for r in shadow._rows(root) if r["kind"] == "error"]
    assert len(err) == 1 and "ZeroDivisionError" in err[0]["error"]
    assert (root / shadow.RUN_LOG).read_text().strip().endswith("status=R31 failed")


def _wrapped_call(path: Path, func: str, attr: str) -> bool:
    """True when `func` calls shadow.<attr> inside a try whose handler catches Exception."""
    tree = ast.parse(path.read_text())
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func)
    for node in ast.walk(fn):
        if isinstance(node, ast.Try) and any(isinstance(h.type, ast.Name) and h.type.id == "Exception" for h in node.handlers):
            if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == attr for b in node.body for c in ast.walk(b)):
                return True
    return False


def test_the_daily_close_and_the_15_minute_jobs_each_make_one_guarded_call():
    uw, app = ROOT / "jarvis" / "service" / "universe_watch.py", ROOT / "jarvis" / "service" / "app.py"
    assert _wrapped_call(uw, "run_daily", "hook_daily")
    assert _wrapped_call(app, "background_jobs", "hook_15m")
    assert uw.read_text().count("shadow.hook_daily(") == 1 and app.read_text().count("shadow.hook_15m(") == 1


# ---------------------------------------------------------------------------------------------------------------- the run checker
def test_the_run_checker_reads_the_lane(tmp_path):
    from jarvis.service import runcheck
    from jarvis.service.runcheck_parts import PARTS

    part = next(p for p in PARTS if p["id"] == "shadow_lane")
    paths = {k: str(tmp_path / k) for k in ("agent", "runs", "repo", "worker", "backups")}
    log = Path(paths["runs"]) / "shadow" / "run.log"
    log.parent.mkdir(parents=True)
    now = calendar.timegm((2026, 10, 26, 12, 0, 0))
    log.write_text("[2026-10-21 00:06] daily rows=41 status=ok\n"
                   "[2026-10-22 00:06] daily rows=40 status=ok\n"
                   "[2026-10-23 00:06] daily rows=37 status=hash chain broken at line 12: an earlier row was edited\n"
                   "[2026-10-25 00:07] daily rows=0 status=ok\n"
                   "[2026-10-26 00:06] daily rows=12 status=ok\n")
    res = runcheck.run(paths, now, [part])
    kinds = sorted((m["kind"], m["from"][:10] if isinstance(m.get("from"), str) else "") for m in res["windows"]["7d"]["misses"])
    got = [m["kind"] for m in res["windows"]["7d"]["misses"]]
    assert sorted(got) == ["empty", "errored", "no run"], kinds              # Oct 23 broken, Oct 24 missing, Oct 25 no rows
