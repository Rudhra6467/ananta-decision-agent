"""Other traders every day (Oct 20, decision OD-HL-FILLS (a) and Madhav's "why wait?"): the worker's capture of Hyperliquid fills
(worker/hl_capture.py), the main Mac's pull of the finished days, and the daily rebuild against Ananta (src/research/others_daily.py).

Covered: synthetic fills and the round trips (with their size-weighted prices), paging and pacing, the atomic day file, catch-up after
missing days, resuming and giving up, the classes (a) (b) (c) (d), the 3-in-7 pattern rule through the repair board's own function on a
temporary database, read-only access to Ananta's files, and that nothing here can place or change an order."""
from __future__ import annotations

import ast
import calendar
import hashlib
import importlib.util
import io
import json
import shutil
import socket
import sqlite3
import subprocess
import time
import tokenize
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DAY = 86400
D = "2026-10-19"
D0 = calendar.timegm(time.strptime(D, "%Y-%m-%d"))
A, B, C, E = "0x" + "a" * 40, "0x" + "b" * 40, "0x" + "c" * 40, "0x" + "e" * 40


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _capture(tmp_path, monkeypatch):
    """A fresh copy of the worker's capture module, its home in tmp_path, its clock and sleep fake (no real waiting)."""
    monkeypatch.setenv("ANANTA_WORKER_HOME", str(tmp_path / "w"))
    spec = importlib.util.spec_from_file_location(f"hl_capture_{uuid.uuid4().hex[:6]}", ROOT / "worker" / "hl_capture.py")
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    clock = {"t": 1000.0, "sleeps": []}
    c._clock = lambda: clock["t"]

    def sleep(s):
        clock["sleeps"].append(s)
        clock["t"] += s
    c._sleep = sleep
    c.CLOCK = clock
    return c


def _accounts_file(path: Path, accts) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": "test", "how_chosen": "test list",
                                "accounts": [{"account": a, "label": lab, "source": lab.split("-")[0], "r2_hft": hft} for a, lab, hft in accts]}))
    return path


_TID = [0]


def hl(t_s: float, coin: str, side: str, px: float, sz: float, start: float, closed: float = 0.0, fee: float = 0.0, **extra) -> dict:
    """One fill in the API's own shape (strings for numbers, as Hyperliquid sends them)."""
    _TID[0] += 1
    f = {"coin": coin, "px": str(px), "sz": str(sz), "side": side, "time": int(t_s * 1000), "startPosition": str(start),
         "dir": "Open Long" if side == "B" else "Open Short", "closedPnl": str(closed), "hash": "0x" + "0" * 63 + "1", "oid": 1000 + _TID[0],
         "crossed": True, "fee": str(fee), "tid": _TID[0], "feeToken": "USDC"}
    f.update(extra)
    return f


def trip(t0: float, t1: float, coin: str, px0: float, px1: float, sz: float = 1.0, short: bool = False) -> list[dict]:
    s = -1.0 if short else 1.0
    pnl = s * (px1 - px0) * sz
    return [hl(t0, coin, "A" if short else "B", px0, sz, 0.0), hl(t1, coin, "B" if short else "A", px1, sz, s * sz, closed=pnl)]


class FakeAPI:
    """The info endpoint: fills by account, in time order, at most PAGE an answer; records every call."""

    def __init__(self, c, fills: dict, fail: dict | None = None):
        self.c, self.fills, self.fail, self.calls = c, fills, fail or {}, []

    def __call__(self, body, timeout=60):
        self.calls.append({"t": self.c.CLOCK["t"], **body})
        f = self.fail.get(body["user"])
        if f:
            raise f() if isinstance(f, type) else f
        xs = sorted((x for x in self.fills.get(body["user"], []) if body["startTime"] <= x["time"] <= body["endTime"]), key=lambda x: x["time"])
        return xs[: self.c.PAGE]


def _write_day(c, day: str, fills_by_acc: dict, statuses: dict | None = None) -> Path:
    """A finished day file written with the capture's own schema and row maker (so the rebuild reads exactly what the worker writes)."""
    c.DATA.mkdir(parents=True, exist_ok=True)
    p = c.final_path(day)
    con = sqlite3.connect(p)
    con.executescript(c.SCHEMA)
    for a, fs in fills_by_acc.items():
        st = (statuses or {}).get(a, "OK")
        con.execute("INSERT INTO accounts (account, label, source, status, fills, pages, truncated, attempts) VALUES (?,?,?,?,?,1,0,1)", (a, "x", "x", st, len(fs)))
        con.executemany(f"INSERT INTO fills VALUES ({','.join('?' * (len(c.KNOWN) + 3))})", [c._row(a, f, 1) for f in fs])
    con.execute("INSERT INTO meta VALUES ('finished_at', '1')")
    con.commit()
    con.close()
    return p


# ---------------------------------------------------------------------------
# round trips
# ---------------------------------------------------------------------------
def test_round_trips_scaled_in_and_out_and_a_flip():
    from src.research import hl_bench as hbm

    rows = [(1000, "BTC", "B", 100.0, 1.0, 0.0, 0.0, 0.1),          # open long 1 @100
            (2000, "BTC", "B", 110.0, 1.0, 1.0, 0.0, 0.1),          # add 1 @110 -> entry vwap 105
            (3000, "BTC", "A", 120.0, 1.0, 2.0, 15.0, 0.1),         # sell 1 @120
            (4000, "BTC", "A", 130.0, 3.0, 1.0, 25.0, 0.1),         # sell 1 @130 to flat and 2 more: a flip to short 2 @130
            (5000, "BTC", "B", 120.0, 2.0, -2.0, 20.0, 0.1),        # cover the short @120
            (6000, "ETH", "A", 50.0, 1.0, 3.0, 0.0, 0.0)]           # ETH opened before the window: not scored
    tr = hbm.round_trips(rows)
    assert [t["dir"] for t in tr] == ["LONG", "SHORT"]
    lng, sht = tr
    assert lng["entry_vwap"] == pytest.approx(105.0) and lng["exit_vwap"] == pytest.approx(125.0)
    assert lng["pnl"] == pytest.approx(40.0) and lng["pnl"] == pytest.approx(2 * (lng["exit_vwap"] - lng["entry_vwap"]))
    assert sht["entry_vwap"] == pytest.approx(130.0) and sht["exit_vwap"] == pytest.approx(120.0) and sht["open_ms"] == 4000
    assert "_vw" not in lng and lng["net"] == pytest.approx(40.0 - 0.4)
    assert hbm.is_hft(hbm.behaviour(tr)) is True                    # these trips last a second each
    slow = hbm.round_trips([(t * 3600, *r[1:]) for t, *rest in rows for r in [(t, *rest)]])     # the same, an hour apart
    assert [round(t["hold_h"], 2) for t in slow] == [3.0, 1.0] and hbm.is_hft(hbm.behaviour(slow)) is False
    many = []
    for k in range(250):                                             # 250 one-minute trips in a day: HFT by review #2's rule
        many += [(k * 120_000, "BTC", "B", 100.0, 1.0, 0.0, 0.0, 0.0), (k * 120_000 + 60_000, "BTC", "A", 100.0, 1.0, 1.0, 0.0, 0.0)]
    assert hbm.is_hft(hbm.behaviour(hbm.round_trips(many))) is True


# ---------------------------------------------------------------------------
# the capture (worker)
# ---------------------------------------------------------------------------
def test_capture_pages_paces_and_keeps_every_field(tmp_path, monkeypatch):
    c = _capture(tmp_path, monkeypatch)
    c.PAGE = 3
    now = D0 + DAY + 3600                                                # 01:00 on the day after D: D is finished
    fills = [hl(D0 + 60 * k, "BTC", "B", 100 + k, 0.1, 0.1 * k) for k in range(5)]
    fills += [hl(D0 + 300, "BTC", "B", 99, 0.1, 0.5)]                  # the same millisecond as a page edge
    fills += [hl(D0 + 400, "kPEPE", "A", 0.01, 5, 0, liquidation={"method": "market"}, builderFee="0.01", newField="kept")]
    fills += [hl(D0 - 10, "BTC", "B", 1, 1, 0), hl(D0 + DAY, "BTC", "B", 1, 1, 0)]   # the days around it are not this day's
    api = FakeAPI(c, {A: fills})
    monkeypatch.setattr(c, "http_post", api)
    acc = _accounts_file(c.HOME / "hl_accounts.json", [(A, "LB_WINNER-01", False)])
    r = c.run(days=1, accounts=acc, now=now)
    assert r["this_run"][0]["finished"] and r["this_run"][0]["fills"] == 7
    assert all(x["type"] == "userFillsByTime" and x["user"] == A for x in api.calls) and len(api.calls) >= 3
    gaps = [b["t"] - a["t"] for a, b in zip(api.calls, api.calls[1:])]
    assert gaps and min(gaps) >= 1.2 - 1e-9                            # at least 1.2 s between calls
    con = sqlite3.connect(c.final_path(D))
    cols = [r[1] for r in con.execute("PRAGMA table_info(fills)")]
    assert {"account", "fetched_at", "start_position", "closed_pnl", "hash", "oid", "crossed", "tid", "fee_token", "builder_fee",
            "liquidation", "cloid", "twap_id", "extra"} <= set(cols)
    assert con.execute("SELECT COUNT(*), COUNT(DISTINCT tid) FROM fills").fetchone() == (7, 7)
    liq, bf, extra = con.execute("SELECT liquidation, builder_fee, extra FROM fills WHERE coin='kPEPE'").fetchone()
    assert json.loads(liq) == {"method": "market"} and bf == 0.01 and json.loads(extra) == {"newField": "kept"}
    assert con.execute("SELECT status, fills FROM accounts").fetchone() == ("OK", 7)
    assert con.execute("SELECT v FROM meta WHERE k='complete'").fetchone()[0] == "all accounts"
    con.close()


def test_capture_backs_off_and_stops_on_rate_limit(tmp_path, monkeypatch):
    c = _capture(tmp_path, monkeypatch)
    api = FakeAPI(c, {}, fail={A: c.RateLimited})
    monkeypatch.setattr(c, "http_post", api)
    acc = _accounts_file(c.HOME / "hl_accounts.json", [(A, "LB_WINNER-01", False), (B, "TAPE-01", False)])
    r = c.run(days=1, accounts=acc, now=D0 + DAY + 3600)
    assert r["rate_limited"] and len(api.calls) == 5                    # 5 tries of one call, then the run stops (B never asked)
    assert c.CLOCK["sleeps"].count(10) == 1 and 80 in c.CLOCK["sleeps"]  # the backoff waits
    assert not c.final_path(D).exists() and c.part_path(D).exists()
    con = sqlite3.connect(c.part_path(D))
    assert dict(con.execute("SELECT account, status FROM accounts")) == {A: "PENDING", B: "PENDING"}   # a 429 is not a failed attempt
    con.close()
    with pytest.raises(ValueError):
        c.post({"type": "clearinghouseState", "user": A})                # it sends one request type only


def test_a_half_written_day_never_looks_finished_then_resumes_and_gives_up(tmp_path, monkeypatch, capsys):
    c = _capture(tmp_path, monkeypatch)
    now = D0 + DAY + 4 * 3600
    seen_final = []

    class API(FakeAPI):
        def __call__(self, body, timeout=60):
            seen_final.append(c.final_path(D).exists())
            return super().__call__(body, timeout)

    api = API(c, {A: trip(D0 + 100, D0 + 200, "BTC", 100, 101)}, fail={B: RuntimeError("HTTP Error 502")})
    monkeypatch.setattr(c, "http_post", api)
    acc = _accounts_file(c.HOME / "hl_accounts.json", [(A, "LB_WINNER-01", False), (B, "TAPE-01", False)])
    c.run(days=1, accounts=acc, now=now)
    assert not any(seen_final) and not c.final_path(D).exists() and c.part_path(D).exists()
    assert c.status(now=now) == 1
    line = capsys.readouterr().out
    assert line.startswith("hl STALE") and "missing " in line and D in line and "last run 0 min ago" in line
    a_calls = sum(1 for x in api.calls if x["user"] == A)
    c.run(days=1, accounts=acc, now=now)                                 # second failure of B
    assert not c.final_path(D).exists() and sum(1 for x in api.calls if x["user"] == A) == a_calls   # A is not fetched again
    c.run(days=1, accounts=acc, now=now)                                 # third: B is recorded as GAVE_UP and the day is finished
    assert c.final_path(D).exists() and not c.part_path(D).exists()
    con = sqlite3.connect(c.final_path(D))
    assert dict(con.execute("SELECT account, status FROM accounts")) == {A: "OK", B: "GAVE_UP"}
    assert con.execute("SELECT v FROM meta WHERE k='complete'").fetchone()[0] == "1 accounts gave up"
    con.close()


def test_catch_up_fetches_only_the_missing_finished_days_oldest_first(tmp_path, monkeypatch, capsys):
    c = _capture(tmp_path, monkeypatch)
    now = D0 + DAY + 5 * 3600
    days = c.finished_days(now)
    assert len(days) == 7 and days[-1] == D and days == sorted(days)
    for d in (days[1], days[3], days[4], days[6]):                       # held already
        _write_day(c, d, {A: []})
    api = FakeAPI(c, {A: []})
    monkeypatch.setattr(c, "http_post", api)
    monkeypatch.setattr(c, "free_gb", lambda: 100.0)
    acc = _accounts_file(c.HOME / "hl_accounts.json", [(A, "LB_WINNER-01", False)])
    assert c.status(now=now) == 2                                        # never ran
    r = c.run(accounts=acc, now=now)
    asked = [time.strftime("%Y-%m-%d", time.gmtime(x["startTime"] / 1000)) for x in api.calls]
    assert asked == [days[0], days[2], days[5]] and r["held_last_7"] == days
    capsys.readouterr()
    assert c.status(now=now) == 0 and "hl OK" in capsys.readouterr().out
    assert c.run(accounts=acc, now=now)["this_run"] == [] and len(api.calls) == 3      # nothing left to do
    old = c.DATA / "hl_2026-08-01.sqlite"
    old.write_bytes(b"x")
    keep = c.DATA / f"hl_{time.strftime('%Y-%m-%d', time.gmtime(now - 40 * DAY))}.sqlite"
    keep.write_bytes(b"x")
    c.prune(now)
    assert not old.exists() and keep.exists()                            # 45 days kept
    assert c.status(now=now + 3 * DAY) == 1                              # three days later and no run: stale


def test_status_line_and_installer_wiring():
    sh = (ROOT / "worker" / "install_worker.sh").read_text()
    assert "hl_capture.py" in sh and "com.ananta.worker.hlcapture" in sh and "hl_accounts.json" in sh
    assert "collector.py\" status; rc=$?" in sh and "exit $rc" in sh     # the collector's exit code stays the worker's health
    pl = (ROOT / "worker" / "com.ananta.worker.hlcapture.plist").read_text()
    assert "<key>StartInterval</key><integer>3600</integer>" in pl and "KeepAlive" not in pl.split("-->", 1)[1]
    if shutil.which("plutil"):
        assert subprocess.run(["plutil", "-lint", str(ROOT / "worker" / "com.ananta.worker.hlcapture.plist")]).returncode == 0


# ---------------------------------------------------------------------------
# the main Mac's nightly pull
# ---------------------------------------------------------------------------
def test_pull_takes_finished_hl_days_and_refuses_an_unfinished_one(tmp_path, monkeypatch):
    from jarvis.service import worker

    c = _capture(tmp_path, monkeypatch)
    _write_day(c, D, {A: trip(D0 + 100, D0 + 200, "BTC", 100, 101)})
    bad_day = "2026-10-18"
    p = _write_day(c, bad_day, {A: []})
    con = sqlite3.connect(p)
    con.execute("DELETE FROM meta WHERE k='finished_at'")
    con.commit()
    con.close()
    src = c.DATA
    out = "\n".join(f"./{f.name} {f.stat().st_size}" for f in src.iterdir()) + "\n./notes.txt 4\n"
    monkeypatch.setattr(worker, "_ssh", lambda cmd, timeout=20: subprocess.CompletedProcess(cmd, 0, out, ""))
    files = worker._remote_files()
    assert set(files) == {f"hl_{D}.sqlite", f"hl_{bad_day}.sqlite"}

    def fake_run(args, **kw):
        if args[0] == "scp":
            shutil.copy(src / args[-2].rsplit("/", 1)[1], args[-1])
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    dest = tmp_path / "here"
    r = worker.pull(dest)
    assert [x["day"] for x in r["pulled"]] == [D] and r["pulled"][0]["fills"] == 2 and r["pulled"][0]["file"] == "hl"
    assert [x["day"] for x in r["failed"]] == [bad_day] and not (dest / f"hl_{bad_day}.sqlite").exists()
    assert worker.pull(dest)["pulled"] == []                              # never twice


def test_worker_status_keeps_the_collector_line_and_reads_the_hl_line(monkeypatch):
    from jarvis.service import worker

    two = "OK · air · last good round 20 s ago · outside alert on · v1.1\nhl OK · other traders' fills: 7 of the last 7 finished days held"
    monkeypatch.setattr(worker, "_ssh", lambda cmd, timeout=20: subprocess.CompletedProcess(cmd, 0, two, ""))
    worker._CACHE.clear()
    s = worker.status(0)
    assert s["ok"] and s["line"].startswith("OK · air") and s["hl"].startswith("hl OK") and worker.alert_armed_now() is True
    worker._CACHE.clear()


# ---------------------------------------------------------------------------
# the daily rebuild (main Mac)
# ---------------------------------------------------------------------------
def _agent(tmp: Path) -> Path:
    """A small agent folder: the registry, the Explorer's scans and book, the universe Explorer, jarvis.sqlite, the dial's candles."""
    ag = tmp / "agent"
    ag.mkdir()
    (ag / "universe_live.json").write_text(json.dumps({"coins": {
        "ARKM": {"status": "LISTED", "tier": "B", "ndax": False, "binance_half_spread": 0.001},
        "PEPE": {"status": "LISTED", "tier": "A", "ndax": False, "binance_half_spread": 0.0005}}}))
    scans = [{"t": D0 + 14 * 3600 - 900, "coin": "SOL", "state": {"S1": "BULL", "S2": "UP", "trend_4h": "UP", "daily_above_ema50": True, "rsi15": 61.2,
                                                                  "in_support": False}, "sightings": [], "setups": []},
             {"t": D0 + 14 * 3600 + 900, "coin": "SOL", "state": {"S1": "BEAR"}, "sightings": [], "setups": []},
             {"t": D0 + 9 * 3600, "coin": "AVAX", "state": {"S1": "BULL"}, "sightings": ["E2", "E5"], "setups": ["E5"]}]
    (ag / "explorer_decisions.jsonl").write_text("".join(json.dumps(s) + "\n" for s in scans))
    con = sqlite3.connect(ag / "explorer_book.sqlite")
    con.executescript("CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT);"
                      "CREATE TABLE trades (id TEXT PRIMARY KEY, coin TEXT, shadow TEXT, exit_t INTEGER, net REAL, json TEXT);")
    ev = [(D0 + 3000, "FILLED", "BTC", "b1", {"setup": "E1"}), (D0 + 20000, "CLOSED", "BTC", "b1", {"setup": "E1"}),
          (D0 + 8 * 3600 - 1800, "ORDER", "ETH", "e1", {"setup": "E4", "shadow": "NO_TYPE"}),
          (D0 + 8 * 3600 - 900, "ORDER", "ETH", "e2", {"setup": "RND", "shadow": "RANDOM"})]
    for t, k, coin, i, extra in ev:
        con.execute("INSERT INTO events (t, kind, coin, id, json) VALUES (?,?,?,?,?)", (t, k, coin, i, json.dumps({"kind": k, "t": t, "coin": coin, "id": i, **extra})))
    con.commit()
    con.close()
    con = sqlite3.connect(ag / "universe_explorer.sqlite")
    con.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT)")
    con.execute("INSERT INTO events (t, kind, coin, id, json) VALUES (?,?,?,?,?)",
                (D0 + 10 * 3600, "ORDER", "ARKM", "u1", json.dumps({"setup": "E2", "shadow": "UNIVERSE", "tags": {"S1": "BULL", "S2": "UP"}})))
    con.commit()
    con.close()
    con = sqlite3.connect(ag / "jarvis.sqlite")
    con.executescript(
        "CREATE TABLE evidence_trades (id TEXT PRIMARY KEY, watch TEXT, coin TEXT, source TEXT, signal_t INTEGER, signal_day TEXT, entry_t INTEGER, entry_day TEXT, "
        "entry REAL, stop REAL, exit_t INTEGER, exit_day TEXT, exit REAL, net_usd REAL, status TEXT, why TEXT, exit_why TEXT, regime TEXT, detail TEXT);"
        "CREATE TABLE eye_events (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, coin TEXT, price REAL, title TEXT, body TEXT, pushed INTEGER, detail TEXT);"
        "CREATE TABLE brain_queue (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, trigger TEXT, detail TEXT, state TEXT);"
        "CREATE TABLE brain_decisions (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, triggers TEXT, action TEXT, confidence REAL, size_pct REAL, price REAL, plan TEXT, "
        "thesis TEXT, knowledge TEXT, model TEXT, cost_usd REAL, trade_id TEXT, random_id TEXT, after_1d_pct REAL, after_5d_pct REAL, note TEXT, after_1d_ex REAL, after_5d_ex REAL);"
        "CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, sleeve TEXT, qty REAL, px REAL, bid REAL, ask REAL, fee REAL, why TEXT);")
    con.execute("INSERT INTO evidence_trades (id, watch, coin, signal_t, entry_t, status) VALUES ('r1', 'RANDOM_10D', 'SOL', ?, ?, 'OPEN')", (D0, D0 + 60))
    con.execute("INSERT INTO brain_queue VALUES ('q1', ?, 'ETH', 'explorer:E4', '', 'NOT_REVIEWED: ranked too low')", (D0 + 8 * 3600 - 1700,))
    con.commit()
    con.close()
    con = sqlite3.connect(ag / "universe_bars.sqlite")
    con.execute("CREATE TABLE d1 (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, qv REAL, PRIMARY KEY (coin, t))")
    con.executemany("INSERT INTO d1 VALUES ('BTC', ?, ?, ?, ?, ?, 1, 1)", [(D0 - k * DAY, 1000 - k, 1001 - k, 999 - k, 1000.5 - k) for k in range(300, 0, -1)])
    con.commit()
    con.close()
    return ag


def _day_fills():
    """The day's trades of account A (a normal trader), with what each should become."""
    from jarvis.service import registry

    ada_cost = registry.cost("ADA")
    return (trip(D0 + 3600, D0 + 5 * 3600, "BTC", 100, 103)                      # (a) the Explorer held BTC
            + trip(D0 + 8 * 3600, D0 + 12 * 3600, "ETH", 50, 52)                  # (b) Explorer E4 blocked: no trade type; the brain did not review
            + trip(D0 + 14 * 3600, D0 + 16 * 3600, "SOL", 20, 21)                 # (c) nothing of ours fired (a random baseline does not count)
            + trip(D0 + 2 * 3600, D0 + 3 * 3600, "DOGE", 0.2, 0.19, short=True)   # (c) a winning short
            + trip(D0 + 4 * 3600, D0 + 6 * 3600, "ADA", 1.0, 1.0 + ada_cost)      # (d) up, but not by our two costs
            + trip(D0 + 9 * 3600 + 300, D0 + 13 * 3600, "AVAX", 10, 11)          # (b) its scan saw E2, which is not in the rules
            + trip(D0 + 10 * 3600 + 600, D0 + 11 * 3600, "ARKM", 1.0, 1.1)        # (b) universe Explorer shadow
            + trip(D0 + 15 * 3600, D0 + 17 * 3600, "kPEPE", 0.01, 0.0105)         # (c) the 30-coin tier
            + trip(D0 + 15 * 3600, D0 + 17 * 3600, "FOOBAR", 1.0, 1.2)            # outside our list
            + trip(D0 + 15 * 3600, D0 + 17 * 3600, "@107", 1.0, 1.2))             # spot: not ours


def _setup_daily(tmp_path, monkeypatch, history: list[dict] | None = None):
    from src.research import others_daily as od

    c = _capture(tmp_path, monkeypatch)
    prev = time.strftime("%Y-%m-%d", time.gmtime(D0 - DAY))
    link = trip(D0 - 2 * 3600, D0 + 3600, "LINK", 10, 11)                         # opened the day before, closed on D: a (c) intraday... 3 h
    swing = trip(D0 - 20 * 3600, D0 + 7 * 3600, "LTC", 50, 55)                    # 27 h: swing
    _write_day(c, prev, {A: [link[0], swing[0], *trip(D0 - 5 * 3600, D0 - 4 * 3600, "XRP", 1, 1.2)], B: [], C: []})
    hft = []
    for k in range(250):
        hft += trip(D0 + 300 * k, D0 + 300 * k + 60, "BTC", 100, 100.5)
    _write_day(c, D, {A: _day_fills() + [link[1], swing[1]], B: hft, C: trip(D0 + 100, D0 + 7200, "SOL", 20, 30), E: []})
    acc = _accounts_file(tmp_path / "hl_accounts.json", [(A, "LB_WINNER-01", False), (B, "TAPE-01", False), (C, "TAPE-02", True), (E, "VAULT-01", False)])
    ag = _agent(tmp_path)
    out = tmp_path / "docs"
    if history:
        od.write_history(out / "repair_shop" / "daily" / "others_history.jsonl", history)
    return od, c, acc, ag, out


def test_the_classes_and_the_page(tmp_path, monkeypatch):
    od, c, acc, ag, out = _setup_daily(tmp_path, monkeypatch)
    r = od.run_day(D, data=c.DATA, accounts=acc, agent=ag, out=out, cases_dir=tmp_path / "cases", requests=False)
    cases = {x["coin"]: x for x in json.loads((tmp_path / "cases" / f"cases_{D}.json").read_text())["cases"]}
    assert cases["BTC"]["class"] == "a" and cases["BTC"]["state"]["held"] == ["Explorer E1 trade"]
    assert cases["ETH"]["class"] == "b" and "no trade type had room to a target" in cases["ETH"]["blocked_by"]
    assert any("ranked too low" in b for b in cases["ETH"]["blocked_by"])
    assert cases["SOL"]["class"] == "c" and cases["SOL"]["situation"] == "LAB10|LONG intraday|OPEN"
    assert cases["SOL"]["state"]["scan"]["t"] == D0 + 14 * 3600 - 900 and cases["SOL"]["state"]["scan"]["S1"] == "BULL"   # never the later scan
    assert cases["DOGE"]["class"] == "c" and cases["DOGE"]["situation"] == "LAB10|SHORT intraday|OPEN"
    assert cases["ADA"]["class"] == "d" and cases["ADA"]["after_our_costs_pct"] < 0
    assert cases["ARKM"]["class"] == "b" and cases["ARKM"]["group"] == "UNIV-B" and "universe Explorer" in cases["ARKM"]["blocked_by"][0]
    assert cases["ARKM"]["state"]["tags"]["S1"] == "BULL"
    assert cases["PEPE"]["class"] == "c" and cases["PEPE"]["group"] == "T30"
    assert cases["LINK"]["class"] == "c" and cases["LTC"]["situation"] == "LAB10|LONG swing|OPEN"     # rebuilt across the day files
    assert "XRP" not in cases                                                     # closed the day before
    assert cases["BTC"]["after_our_costs_pct"] == pytest.approx(100 * (0.03 - 2 * cases["BTC"]["cost_per_side_pct"] / 100), abs=1e-3)
    assert {x["label"] for x in cases.values()} == {"LB_WINNER-01"}               # B (HFT by its trips) and C (review #2's HFT) dropped
    assert cases["AVAX"]["class"] == "b" and cases["AVAX"]["blocked_by"] == ["seen, not in the active rulebook"]
    assert [f["what"] for f in cases["AVAX"]["state"]["fired"]] == ["Explorer E2 sighting"]          # E5 is in the rules: an order would say
    assert r["classes"] == {"a": 1, "b": 3, "c": 5, "d": 1}
    text = (out / "repair_shop" / "daily" / f"others_{D}.md").read_text()
    assert "Reference only (D8)" in text and "2 dropped as market makers or HFT" in text and "outside our list 1" in text
    assert "spot or other markets 1" in text and "## The top 10 cases" in text and A not in text and "0x" not in text
    assert "The dial that day: open." in text
    hist = od.read_history(out / "repair_shop" / "daily" / "others_history.jsonl")
    assert len(hist) == 1 and hist[0]["situations_c"]["LAB10|LONG intraday|OPEN"]["n"] == 2   # SOL and LINK


def _hrow(day, key="LAB10|LONG intraday|OPEN", filed=None):
    return {"day": day, "situations_c": {key: {"n": 1, "median_pct": 1.0, "coins": ["SOL"]}}, "filed": filed or []}


def _d(k):
    return time.strftime("%Y-%m-%d", time.gmtime(D0 - k * DAY))


def test_three_days_in_seven_files_one_draft_finding_through_the_repair_board(tmp_path, monkeypatch):
    from jarvis.service import requests_log

    od, c, acc, ag, out = _setup_daily(tmp_path, monkeypatch, history=[_hrow(_d(2)), _hrow(_d(5)), _hrow(_d(9), "UNIV-C|LONG scalp|OPEN")])
    r = od.run_day(D, data=c.DATA, accounts=acc, agent=ag, out=out, cases_dir=None)
    assert [f["key"] for f in r["filed"]] == ["LAB10|LONG intraday|OPEN"] and r["filed"][0]["num"] == 1
    con = sqlite3.connect(ag / "jarvis.sqlite")
    rows = con.execute("SELECT num, kind, by, status, text, about FROM owner_requests").fetchall()
    assert len(rows) == 1 and rows[0][1:4] == ("idea", "ananta-auto", "OPEN") and rows[0][4].startswith("DRAFT finding")
    assert "not a rule or a signal" in rows[0][4] and "nobody is copied" in rows[0][4] and rows[0][5] == "other traders (daily)"
    con.close()
    assert "request 1" in (out / "repair_shop" / "daily" / f"others_{D}.md").read_text()
    r2 = od.run_day(D, data=c.DATA, accounts=acc, agent=ag, out=out, cases_dir=None)          # the same day again: not filed twice
    assert r2["filed"] == []
    hist = od.read_history(out / "repair_shop" / "daily" / "others_history.jsonl")
    assert [h["day"] for h in hist] == sorted({_d(9), _d(5), _d(2), D}) and hist[-1]["filed"][0]["num"] == 1
    from src.research import others_daily as od2

    seen = []
    monkeypatch.setattr(od2, "run_day", lambda d, **kw: seen.append((d, kw.get("requests"))) or {"day": d})
    od2.run(now=D0 + DAY + 3600, data=c.DATA, out=out)                       # D has a real row; only D - 1 (a day file, no row) runs
    assert seen == [(_d(1), None)]
    hp = out / "repair_shop" / "daily" / "others_history.jsonl"
    od2.write_history(hp, [dict(h, dry_run=True) if h["day"] == D else h for h in od2.read_history(hp)])
    seen.clear()
    od2.run(now=D0 + DAY + 3600, data=c.DATA, out=out)                       # a dry run's row does not count as done
    assert seen == [(_d(1), None), (D, None)]
    j = type("J", (), {"db": sqlite3.connect(ag / "jarvis.sqlite"), "now": staticmethod(time.time)})()
    assert len(requests_log.list_(j)) == 1
    j.db.close()


def test_the_pattern_rule_counts_separate_days_inside_seven_and_waits_thirty_days_to_refile():
    from src.research import others_daily as od

    k = "LAB10|LONG intraday|OPEN"
    assert od.repeats([_hrow(_d(7)), _hrow(_d(8)), _hrow(D)], D) == []              # two of the three are older than 7 days
    assert od.repeats([_hrow(_d(6)), _hrow(_d(3)), _hrow(D)], D)[0]["key"] == k       # day D-6 is still inside the 7
    assert od.repeats([_hrow(_d(1)), _hrow(D)], D) == []                              # 2 days are not 3
    filed = [{"key": k, "num": 4}]
    assert od.repeats([_hrow(_d(20), filed=filed), _hrow(_d(4)), _hrow(_d(2)), _hrow(D)], D) == []     # filed 20 days ago
    assert od.repeats([_hrow(_d(31), filed=filed), _hrow(_d(4)), _hrow(_d(2)), _hrow(D)], D)[0]["key"] == k
    t = od.draft_text({"key": "T30|SHORT swing|CLOSED", "days": [_d(2), _d(1), D], "trips": 5, "median_pct": 2.5, "coins": ["SUI"]}, D)
    assert t.startswith("DRAFT finding") and "Ananta only buys" in t and "the 30-coin tier" in t and "closed" in t


def _hashes(folder: Path) -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}


def _dump(p: Path, skip=("owner_requests",)) -> list:
    con = sqlite3.connect(p)
    out = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        if t not in skip and not t.startswith("sqlite_"):
            out.append((t, sorted(map(repr, con.execute(f"SELECT * FROM {t}")))))
    con.close()
    return out


def test_the_rebuild_only_reads_ananta_and_writes_only_through_the_request_function(tmp_path, monkeypatch):
    od, c, acc, ag, out = _setup_daily(tmp_path, monkeypatch, history=[_hrow(_d(2)), _hrow(_d(5))])

    def no_net(*a, **k):
        raise AssertionError("the daily rebuild never uses the network")

    monkeypatch.setattr(socket.socket, "connect", no_net)
    before, data_before = _hashes(ag), _hashes(c.DATA)
    od.run_day(D, data=c.DATA, accounts=acc, agent=ag, out=out, cases_dir=None, requests=False)
    assert _hashes(ag) == before and _hashes(c.DATA) == data_before          # requests off: not one byte changed
    tables = _dump(ag / "jarvis.sqlite")
    od.run_day(D, data=c.DATA, accounts=acc, agent=ag, out=out, cases_dir=None)          # 3 days in 7: one request is filed
    after = _hashes(ag)
    assert {k for k in after if after[k] != before.get(k)} == {"jarvis.sqlite"} and _hashes(c.DATA) == data_before
    assert _dump(ag / "jarvis.sqlite") == tables                              # every other table as it was
    con = sqlite3.connect(ag / "jarvis.sqlite")
    assert con.execute("SELECT COUNT(*) FROM owner_requests").fetchone()[0] == 1
    con.close()


def test_the_account_list_is_built_once_from_review_2s_collection(tmp_path):
    from src.research import others_daily as od

    hl_db = tmp_path / "hl_bench.sqlite"
    con = sqlite3.connect(hl_db)
    con.executescript("""CREATE TABLE accounts (address TEXT PRIMARY KEY, source TEXT, meta_json TEXT, status TEXT);
        CREATE TABLE fills (address TEXT, tid INTEGER, time INTEGER, coin TEXT, side TEXT, px REAL, sz REAL, start_pos REAL, dir TEXT,
        closed_pnl REAL, fee REAL, PRIMARY KEY (address, tid)); CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);""")
    con.execute("INSERT INTO meta VALUES ('sampling', ?)", (json.dumps({"seed": 20260929}),))
    for a, src, st in ((A, "LB_WINNER", "DONE"), (B, "TAPE", "DONE_TRUNCATED"), (C, "TAPE", "SKIPPED_QUOTA"), (E, "VAULT", "NO_FILLS")):
        con.execute("INSERT INTO accounts VALUES (?,?,?,?)", (a.upper().replace("0X", "0x"), src, "{}", st))
    for k in range(250):                                                       # B trades like a market maker
        con.execute("INSERT INTO fills VALUES (?,?,?,?,?,?,?,?,?,?,?)", (B.upper().replace("0X", "0x"), 2 * k, k * 120_000, "BTC", "B", 100, 1, 0, "", 0, 0))
        con.execute("INSERT INTO fills VALUES (?,?,?,?,?,?,?,?,?,?,?)", (B.upper().replace("0X", "0x"), 2 * k + 1, k * 120_000 + 60_000, "BTC", "A", 100, 1, 1, "", 0, 0))
    con.commit()
    con.close()
    out = tmp_path / "x" / "hl_accounts.json"
    r = od.build_accounts(hl_db, out)
    d = json.loads(out.read_text())
    assert r["accounts"] == 2 and [x["label"] for x in d["accounts"]] == ["LB_WINNER-01", "TAPE-01"]
    assert [x["account"] for x in d["accounts"]] == [A, B] and [x["r2_hft"] for x in d["accounts"]] == [False, True]
    assert "seed 20260929" in d["how_chosen"] and "1 NO_FILLS" in d["how_chosen"] and "1 SKIPPED_QUOTA" in d["how_chosen"]
    with pytest.raises(FileExistsError):
        od.build_accounts(hl_db, out)                                            # fixed: never rebuilt


# ---------------------------------------------------------------------------
# nothing here can place or change an order
# ---------------------------------------------------------------------------
def _strings(src: str) -> list[str]:
    """Every string in the code, docstrings left out (they explain; they do not run)."""
    tree = ast.parse(src)
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
            docs.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


def _comments(src: str) -> list[str]:
    return [t.string for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type == tokenize.COMMENT]


def _imports(src: str) -> set[str]:
    out = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            out.update(f"{n.module}.{a.name}" if n.module and n.module.startswith(("src", "jarvis")) else (n.module or "") for a in n.names)
    return out


def test_nothing_here_can_place_or_change_an_order():
    cap = (ROOT / "worker" / "hl_capture.py").read_text()
    daily = (ROOT / "src" / "research" / "others_daily.py").read_text()
    for src in (cap, daily):
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} \
            | {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        bad = {x for x in names if x.lower().startswith(("place", "submit", "cancel", "modify", "approve", "set_status"))
               or any(w in x.lower() for w in ("order", "kill", "manual", "trade_guard"))}
        assert not bad, bad
    # the capture: one endpoint (info, never exchange), one request type, standard library only
    strs = _strings(cap)
    assert {x for x in strs if "://" in x} == {"https://api.hyperliquid.xyz/info"}
    assert not any("exchange" in x.lower() for x in strs + _comments(cap))
    assert {x for x in strs if x[:4] in ("user", "clea", "orde", "canc", "modi")} <= {"userFillsByTime", "user"}
    assert not {m for m in _imports(cap) if m.startswith(("src", "jarvis", "requests", "httpx"))}
    # the rebuild: no network at all, and only these parts of ours
    imp = _imports(daily)
    assert not {m for m in imp if m.split(".")[0] in ("urllib", "http", "socket", "ssl", "subprocess", "requests", "httpx")}
    ours = {m for m in imp if m.startswith(("src", "jarvis"))}
    assert ours <= {"src.research.hl_bench", "jarvis.service.registry", "jarvis.service.tier30", "jarvis.service.exposure", "jarvis.service.requests_log"}, ours
    # its only read-write database connection is the repair board's request function
    rw = []
    for fn in ast.walk(ast.parse(daily)):
        if isinstance(fn, ast.FunctionDef):
            for n in ast.walk(fn):
                if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "connect":
                    if "mode=ro" not in ast.unparse(n.args[0]):
                        rw.append(fn.name)
    assert set(rw) == {"_file_request", "add"}
    assert "requests_log.add(" in daily and "requests_log.set_status" not in daily
