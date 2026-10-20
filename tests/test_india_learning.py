"""India learning loop (20 Oct 2026), on synthetic data only: the paper_review sealed purpose and its leak rule, the missed-movers classes, the
3-in-10 pattern rule, the nightly SP1 replay's skip paths, and the morning summary (a job that exited 1, a dead token, the 'none' case)."""
from __future__ import annotations

import datetime as dt
import json
import os
import plistlib
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from india import leakcheck, paths, sealed

TOR = ZoneInfo("America/Toronto")
T = dt.date(2026, 10, 19)       # Monday, a session
D = dt.date(2026, 10, 16)       # the paper's first decision day
HOL = dt.date(2026, 10, 20)     # NSE holiday


@pytest.fixture()
def lake(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path / "india"))
    paths.ensure()
    (paths.manifest_dir() / "nse_holidays.json").write_text(json.dumps({"CM": [{"tradingDate": "20-Oct-2026"}, {"tradingDate": "02-Oct-2026"}]}))
    cal = pd.bdate_range("2026-08-03", "2026-10-19")
    (paths.data_dir() / "silver" / "calendar").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": cal.date, "is_trading_day": [d.date() != dt.date(2026, 10, 2) for d in cal]}).to_parquet(
        paths.data_dir() / "silver" / "calendar" / "calendar.parquet")
    return tmp_path / "india"


def _cash(rows: list[dict]) -> None:
    p = paths.data_dir() / "sealed" / "silver" / "cm_bhavcopy" / "year=2026"
    p.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df.to_parquet(p / "part.parquet", index=False)


def _row(day, sym, prev, o, h, l, c, turnover=1e9):
    return {"date": str(day), "symbol": sym, "series": "EQ", "open": o, "high": h, "low": l, "close": c, "prev_close": prev, "volume": 1e6,
            "turnover": turnover, "isin": "IN" + sym}


# ----------------------------------------------------------------------------------------------------------------------------- paper_review
def test_paper_review_refuses_any_date_before_the_paper(lake):
    _cash([_row(d, "AAA", 100, 100, 101, 99, 100) for d in ("2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19")])
    for bad in ("2026-10-15", "2024-01-01", "2026-01-01", "2023-06-30"):
        with pytest.raises(PermissionError, match="before the paper's first day"):
            sealed.read_review("paper_review", bad)
    with pytest.raises(PermissionError, match="purpose"):
        sealed.read_review("paper_lookback", "2026-10-16")
    with pytest.raises(PermissionError):
        sealed.read_cm("paper_review", "2026-10-16")       # the purpose opens nothing else
    with pytest.raises(PermissionError, match="before start"):
        sealed.read_review("paper_review", "2026-10-19", until="2026-10-16")
    df = sealed.read_review("paper_review", "2026-10-16")
    assert sorted({str(x)[:10] for x in df["date"]}) == ["2026-10-16", "2026-10-19"]
    one = sealed.read_review("paper_review", "2026-10-16", until="2026-10-16")
    assert sorted({str(x)[:10] for x in one["date"]}) == ["2026-10-16"]
    log = [json.loads(x) for x in (paths.manifest_dir() / "sealed_access.jsonl").read_text().splitlines()]
    assert [x["purpose"] for x in log] == ["paper_review", "paper_review"] and log[0]["rows"] == 2


def test_leakcheck_paper_review_rule(tmp_path):
    ok, note = leakcheck.check_paper_review()           # the real repository
    assert ok, note
    d = tmp_path / "pkg"
    d.mkdir()
    good = ('"""Mentions paper_review in prose."""\nfrom india import sealed\nREVIEW_START = "2026-10-16"\n\n\n'
            'def f(day):\n    return sealed.read_review("paper_review", REVIEW_START, until=day)\n')
    (d / "missed.py").write_text(good)
    assert leakcheck.check_paper_review(d)[0]
    cases = {
        "early start": good.replace('"2026-10-16"', '"2026-10-15"'),
        "holdout start": good.replace('"2026-10-16"', '"2024-01-01"'),
        "variable start": good.replace("REVIEW_START, until", "day, until"),
        "reassigned": good + 'REVIEW_START = "2024-01-01"\n',
        "shadowed": good.replace("def f(day):", "def f(day, REVIEW_START='2020-01-01'):"),
        "other purpose": good.replace('"paper_review", REVIEW_START', '"paper_lookback", REVIEW_START'),
        "other reader": good + '\n\ndef g():\n    return sealed.read_cm("paper_lookback", "2026-01-01")\n',
        "sealed path": good + 'X = "sealed/silver/cm_bhavcopy"\n',
    }
    for name, src in cases.items():
        (d / "missed.py").write_text(src)
        assert not leakcheck.check_paper_review(d)[0], name
    (d / "missed.py").write_text(good)
    (d / "other.py").write_text('"""paper_review in a docstring is prose."""\nX = 1\n')
    assert leakcheck.check_paper_review(d)[0]
    (d / "other.py").write_text('P = "paper_review"\n')
    assert not leakcheck.check_paper_review(d)[0]
    (d / "other.py").write_text('from india import sealed\nx = sealed.read_review\n')
    assert not leakcheck.check_paper_review(d)[0]


# ----------------------------------------------------------------------------------------------------------------------------- missed movers
def _u(sym, **kw):
    base = {"sid": "S_" + sym, "symbol": sym, "isin": "IN" + sym, "liq_rank": 10, "ret_1": None, "gap": None, "oc": None, "vol_ratio20": 1.2,
            "turnover_vs_med60": 1.5, "breakout20": False, "breakdown20": False, "base20_range": 0.3, "new_high_250": False, "new_low_250": False,
            "rsi14": 50.0, "rsi14_prev": 50.0, "dist_sma20": 0.0, "dist_sma20_prev": 0.0, "dist_sma200": 0.05, "dist_sma200_prev": 0.05,
            "ret_20_prev": 0.02, "atr_pct": 0.02}
    return {**base, **kw}


def _trade(sym, camp, policy, ur, signal=D, entry=T, status="open", **kw):
    return {"id": f"{signal}|{camp}|S_{sym}|{policy}", "book": "exec", "campaign": camp, "sid": "S_" + sym, "symbol": sym, "policy": policy,
            "signal_date": str(signal), "entry_date": str(entry), "status": status, "notional": 50000.0, "unrealised_ret": ur, "last_date": str(T), **kw}


def _seed_book(lake):
    pdir = lake / "paper" / "decisions"
    pdir.mkdir(parents=True, exist_ok=True)
    j16 = [{"campaign": "BRK", "sid": "S_AAA", "symbol": "AAA", "status": "chosen", "reason": None},
           {"campaign": "PULL", "sid": "S_BBB", "symbol": "BBB", "status": "rejected", "reason": "cap_reached"},
           {"campaign": "REV", "sid": "S_EEE", "symbol": "EEE", "status": "chosen", "reason": None},
           {"campaign": "CTL", "sid": "S_HHH", "symbol": "HHH", "status": "chosen", "reason": None}]
    (pdir / f"{D}.json").write_text(json.dumps({"journal": j16, "signals": [], "sha256": "x"}))
    (pdir / f"{T}.json").write_text(json.dumps({"journal": [{"campaign": "BRK", "sid": "S_CCC", "symbol": "CCC", "status": "chosen", "reason": None}],
                                                "signals": [], "sha256": "y"}))
    uni = [_u("AAA", ret_1=0.05), _u("BBB"), _u("CCC", breakout20=True, base20_range=0.10, vol_ratio20=3.5), _u("DDD"), _u("GGG", turnover_vs_med60=0.1),
           _u("HHH"), _u("EEE"), _u("FFF", breakdown20=True, dist_sma200_prev=-0.1), _u("ZZZ")]
    (pdir / f"{T}.universe.json").write_text(json.dumps({"key": str(T), "source": "recorded at decision time", "liq_top": 250, "n": len(uni), "rows": uni}))
    trades = [_trade("AAA", "BRK", "hold_5d", 0.05), _trade("AAA", "BRK", "hold_10d", 0.03), _trade("AAA", "BRK", "random_exit", 0.5),
              _trade("EEE", "REV", "hold_5d", -0.04), _trade("HHH", "CTL", "hold_5d", 0.02)]
    (lake / "paper" / "state.json").write_text(json.dumps({"trades": {t["id"]: t for t in trades}, "decisions": {}}))
    base = pd.DataFrame([{**_trade("BBB", "PULL", "hold_5d", 0.06), "book": "baseline", "journal_status": "rejected", "journal_reason": "cap_reached"}])
    base.to_parquet(lake / "paper" / "baseline.parquet", index=False)
    rows = [_row(T, "AAA", 100, 101, 106, 100.5, 105), _row(T, "BBB", 200, 202, 212, 201, 210), _row(T, "CCC", 50, 52, 54.5, 51.8, 54),
            _row(T, "DDD", 30, 36, 36, 36, 36), _row(T, "GGG", 80, 80.5, 84, 80, 83.6), _row(T, "HHH", 60, 60.6, 63, 60.2, 62.4),
            _row(T, "EEE", 150, 148, 149, 140, 141), _row(T, "FFF", 90, 85, 86, 82, 83), _row(T, "ZZZ", 70, 70, 70.5, 69.8, 70.1),
            _row(D, "AAA", 99, 99, 101, 98, 100), _row(D, "CCC", 49, 49, 50.5, 48, 50)]
    _cash(rows)


def test_missed_movers_classes(lake, tmp_path):
    from india import missed

    _seed_book(lake)
    reg = tmp_path / "reg"
    man = missed.evening(T, reg=reg, log=lambda *a: None)
    assert man["status"] == "ok" and man["window_decisions"] == [str(D)]
    by = {(r["symbol"], r["side"]): r for r in man["movers"]}
    aaa = by[("AAA", "up")]
    assert aaa["status"] == "caught" and aaa["held"][0]["family"] == "BRK" and aaa["held"][0]["entered_on_day"]
    assert aaa["held"][0]["pnl_so_far"]["mean_inr"] == 2000 and aaa["held"][0]["pnl_so_far"]["policies"] == 2   # random_exit left out
    bbb = by[("BBB", "up")]
    assert bbb["class"] == "a" and "cap for the family was full" in bbb["why"] and bbb["baseline_would_have"][0]["pnl_so_far"]["mean_inr"] == 3000
    ccc = by[("CCC", "up")]
    assert ccc["class"] == "b" and ccc["situation_key"] == "up:breakout_base:gap_held" and ccc["fired_on_day_close"] == ["BRK"]
    assert "gapped up +4.0% and held" in ccc["situation"] and "3.5x" in ccc["situation"] and "day's close" in ccc["why"]
    assert by[("DDD", "up")]["class"] == "c" and "20% price band" in by[("DDD", "up")]["why"]
    assert by[("GGG", "up")]["class"] == "c" and "thin day" in by[("GGG", "up")]["why"]
    assert by[("HHH", "up")]["status"] == "caught_by_control"
    eee = by[("EEE", "down")]
    assert eee["status"] == "held_into_fall" and eee["held"][0]["pnl_so_far"]["mean_inr"] == -2000
    fff = by[("FFF", "down")]
    assert fff["class"] == "b" and "no short family" in fff["why"] and fff["situation_key"] == "down:breakdown_range:gap_down_held"
    s = man["summary"]
    assert s["up"]["caught"] == 1 and s["up"]["catches_pnl_so_far_inr"] == 2000 and s["up"]["caught_by_control"] == 1
    assert s["up"]["a"] == 1 and s["up"]["c"] == 2 and s["down"]["held_pnl_so_far_inr"] == -2000
    disk = json.loads((paths.manifest_dir() / f"missed_{T}.json").read_text())
    assert disk["md_line"].startswith(f"| {T} | 7 up | caught 1")
    raw = {"open", "high", "low", "close", "prev_close", "volume", "turnover", "isin"}
    assert not raw & {k for r in disk["movers"] for k in r}          # derived numbers only: no raw price field leaves in the manifest
    missed.evening(T, reg=reg, log=lambda *a: None)          # a re-run replaces its line
    md = (reg / "missed_movers.md").read_text()
    assert md.count(f"| {T} |") == 1 and "| date | gainers |" in md
    log = [json.loads(x)["purpose"] for x in (paths.manifest_dir() / "sealed_access.jsonl").read_text().splitlines()]
    assert set(log) == {"paper_review"}


def test_missed_movers_lists_and_holiday(lake, tmp_path):
    from india import missed

    _seed_book(lake)
    rows = missed.day_rows(T)
    uni = json.loads((lake / "paper" / "decisions" / f"{T}.universe.json").read_text())["rows"]
    mv = missed.movers(rows, uni, top_n=2)
    up, dn = mv[mv["side"] == "up"], mv[mv["side"] == "down"]
    in_list = lambda df, meas: df[df["lists"].map(lambda x: meas in x)]
    assert set(in_list(up, "cc")["symbol"]) == {"DDD", "CCC"}          # the two biggest close-to-close gainers
    assert len(in_list(up, "oc")) == 2 and (in_list(up, "oc")["oc"] > 0.035).all()
    assert set(in_list(dn, "cc")["symbol"]) == {"FFF", "EEE"} and (in_list(dn, "cc")["cc"] < 0).all()
    assert "ZZZ" not in set(mv["symbol"])                               # a small mover is on no list
    man = missed.evening(HOL, reg=tmp_path / "reg", log=lambda *a: None)
    assert man["status"] == "no session (NSE holiday)"
    assert json.loads((paths.manifest_dir() / f"missed_{HOL}.json").read_text())["status"] == "no session (NSE holiday)"
    assert f"| {HOL} | no session (NSE holiday) |" in (tmp_path / "reg" / "missed_movers.md").read_text()


def test_pattern_rule_three_in_ten():
    from india import missed

    days = [str(d.date()) for d in pd.bdate_range("2026-11-02", periods=12)]
    key = "up:breakout_base:gap_held"
    ent = lambda d: {key: {"situation": "gapped up and held, breaking out of a tight 20-day base", "examples": [{"date": d, "symbol": "X"}]}}
    win = days[:10]
    two = {days[0]: ent(days[0]), days[5]: ent(days[5])}
    assert missed.pattern_drafts(days[9], win, two, []) == []
    three = {**two, days[9]: ent(days[9])}
    out = missed.pattern_drafts(days[9], win, three, [])
    assert len(out) == 1 and out[0]["status"] == "DRAFT" and out[0]["days"] == [days[0], days[5], days[9]] and "registry" in out[0]["note"]
    assert missed.pattern_drafts(days[9], win, three, out) == []          # one draft per situation inside the window
    spread = {days[0]: ent(days[0]), days[5]: ent(days[5]), days[11]: ent(days[11])}
    assert missed.pattern_drafts(days[11], days[2:12], spread, []) == []   # the first day fell out of the 10-session window
    other = {days[0]: ent(days[0]), days[5]: ent(days[5]), days[9]: {"down:new_52w_low:steady": {"situation": "s", "examples": []}}}
    assert missed.pattern_drafts(days[9], win, other, []) == []            # the same situation, not any situation


def test_pattern_rule_writes_draft_from_manifests(lake, tmp_path):
    from india import missed

    _seed_book(lake)
    key = "up:breakout_base:gap_held"
    for d in ("2026-10-14", "2026-10-15"):
        (paths.manifest_dir() / f"missed_{d}.json").write_text(json.dumps({"date": d, "status": "ok", "movers": [
            {"class": "b", "situation_key": key, "situation": "w", "symbol": "Q", "cc": 0.05, "oc": 0.02}]}))
    reg = tmp_path / "reg"
    man = missed.evening(T, reg=reg, log=lambda *a: None)
    assert key in man["drafts_written"]
    again = missed.evening(T, reg=reg, log=lambda *a: None)
    assert again["drafts_written"] == []
    drafts = [json.loads(x) for x in (reg / "missed_drafts.jsonl").read_text().splitlines()]
    assert [x["key"] for x in drafts].count(key) == 1 and drafts[0]["status"] == "DRAFT"


# ----------------------------------------------------------------------------------------------------------------------------- nightly replay
@pytest.fixture()
def sp1(lake, tmp_path, monkeypatch):
    from india import sp1paper

    root = tmp_path / "sp1"
    monkeypatch.setattr(sp1paper, "ROOT", root)
    monkeypatch.setattr(sp1paper, "DECISIONS", root / "decisions.jsonl")
    monkeypatch.setattr(sp1paper, "OUTCOMES", root / "outcomes.jsonl")
    return sp1paper


def test_replay_skip_paths(sp1, monkeypatch, tmp_path):
    from india import kite, sp1nightly

    q = lambda *a: None
    assert sp1nightly.run(HOL, q)["status"] == "skipped (holiday)"
    wk = sp1nightly.run(dt.date(2026, 10, 24), q)
    assert wk["status"] == "skipped (holiday)" and wk["detail"] == "weekend"
    r = sp1nightly.run(dt.date(2026, 10, 21), q)
    assert r["status"] == "skipped (no ledger rows)" and "no SP1 paper decision" in r["detail"]
    sp1._append(sp1.DECISIONS, {"kind": "error", "date": "2026-10-23", "error": "Kite token not valid at the open"})
    r = sp1nightly.run(dt.date(2026, 10, 23), q)
    assert r["status"] == "skipped (no ledger rows)" and "token not valid" in r["detail"]
    sp1._append(sp1.DECISIONS, {"kind": "decision", "date": "2026-10-22", "index": "NIFTY", "point": "D0", "choice": None})
    monkeypatch.setattr(kite, "TOKEN_FILE", tmp_path / "no_token.json")
    assert sp1nightly.run(dt.date(2026, 10, 22), q)["status"] == "skipped (no token)"
    monkeypatch.setattr(kite, "token", lambda: {})

    def dead(day, log=print):
        raise kite.NeedLogin("Kite token rejected (TokenException): sign in again")
    monkeypatch.setattr(sp1, "replay_ledger", dead)
    assert sp1nightly.run(dt.date(2026, 10, 22), q)["status"] == "skipped (no token)"

    def boom(day, log=print):
        raise RuntimeError("Kite did not answer")
    monkeypatch.setattr(sp1, "replay_ledger", boom)
    r = sp1nightly.run(dt.date(2026, 10, 22), q)
    assert r["status"] == "ERROR" and "Kite did not answer" in r["detail"]
    monkeypatch.setattr(sp1, "replay_ledger", lambda day, log=print: {"compared": 1, "mismatches": []})
    assert sp1nightly.run(dt.date(2026, 10, 22), q)["status"] == "PASS"
    monkeypatch.setattr(sp1, "replay_ledger", lambda day, log=print: {"compared": 1, "mismatches": [{"what": "NIFTY D0 choice", "live": 3, "replay": None}]})
    assert sp1nightly.run(dt.date(2026, 10, 22), q)["status"] == "FAIL"
    man = json.loads((paths.manifest_dir() / "sp1_nightly_replay.json").read_text())
    assert man["status"] == "FAIL" and man["replay"]["mismatches"][0]["what"] == "NIFTY D0 choice"
    lines = (paths.manifest_dir() / "sp1_nightly_replay.jsonl").read_text().splitlines()
    assert len(lines) == 9
    # a broken ledger chain is a FAIL even on a holiday
    txt = sp1.DECISIONS.read_text().replace("Kite token not valid", "edited")
    sp1.DECISIONS.write_text(txt)
    assert sp1nightly.run(HOL, q)["status"] == "FAIL (ledger check); replay skipped (holiday)"


# ----------------------------------------------------------------------------------------------------------------------------- morning summary
def _ts(y, mo, d, h, mi):
    return dt.datetime(y, mo, d, h, mi, tzinfo=TOR).timestamp()


def _job(agents, logs, name, cal, out_text="", err_text="", out_at=None, err_at=None, wrap=False):
    lab = f"com.ananta.india.{name}"
    out, err = logs / f"{name}.log", logs / f"{name}.err"
    out.write_text(out_text)
    err.write_text(err_text)
    if out_at:
        os.utime(out, (out_at, out_at))
    if err_at:
        os.utime(err, (err_at, err_at))
    (agents / f"{lab}.plist").write_bytes(plistlib.dumps({"Label": lab, "ProgramArguments": ["/bin/zsh", "-c", "x"] if wrap else ["python"],
                                                          "StandardOutPath": str(out), "StandardErrorPath": str(err), "StartCalendarInterval": cal}))


PAPER_TB = """Traceback (most recent call last):
  File "<frozen runpy>", line 203, in _run_module_as_main
  File "/Users/x/code/ananta-records/india/paper.py", line 610, in <module>
    {"run": run}[cmd]()
_duckdb.CatalogException: Catalog Error: Table with name paper_marks does not exist!
"""
TOKEN_TB = """Traceback (most recent call last):
  File "/Users/x/code/ananta-records/india/spreads.py", line 183, in <module>
    print(json.dumps(sample()), flush=True)
  File "/Users/x/code/ananta-records/india/kite.py", line 98, in get
    raise NeedLogin("Kite token rejected (TokenException): sign in again")
india.kite.NeedLogin: Kite token rejected (TokenException): sign in again
"""
NIGHTLY_OK = '{"window": "x"}\n{\n "window": "2026-10-12..2026-10-19",\n "fetch": "ok",\n "catalog": "ok",\n "seconds": 437\n}\n'


def test_morning_summary_shows_exit_1_and_dead_token(lake, tmp_path):
    from india import morning

    agents, logs = tmp_path / "agents", tmp_path / "logs"
    agents.mkdir()
    logs.mkdir()
    dec = lake / "paper" / "decisions"
    dec.mkdir(parents=True, exist_ok=True)
    (dec / f"{T}.json").write_text(json.dumps({"signals": [1, 2], "decided_at": "2026-10-20T02:30:12+00:00"}))
    _job(agents, logs, "paper", {"Hour": 22, "Minute": 30}, "{}", PAPER_TB, _ts(2026, 10, 19, 22, 31), _ts(2026, 10, 19, 22, 31))
    _job(agents, logs, "spreads", [{"Weekday": w, "Hour": 22, "Minute": 35} for w in range(5)], "", TOKEN_TB, _ts(2026, 10, 19, 22, 35), _ts(2026, 10, 19, 23, 44), wrap=True)
    _job(agents, logs, "nightly", {"Hour": 2, "Minute": 30}, NIGHTLY_OK, "", _ts(2026, 10, 20, 2, 37), _ts(2026, 10, 19, 2, 30))
    _job(agents, logs, "recorder_noon", [{"Weekday": w, "Hour": 12, "Minute": 30} for w in range(1, 6)], "{}", "", _ts(2026, 10, 17, 12, 35), _ts(2026, 10, 17, 12, 35))
    lc = ("PID\tStatus\tLabel\n-\t1\tcom.ananta.india.paper\n-\t1\tcom.ananta.india.spreads\n-\t0\tcom.ananta.india.nightly\n"
          "-\t0\tcom.ananta.india.recorder_noon\n867\t0\tcom.ananta.explorer\n")
    now = dt.datetime(2026, 10, 20, 7, 0, tzinfo=TOR)
    r = morning.build(now=now, launchctl_text=lc, agents=agents, reg=tmp_path / "reg")
    md = (tmp_path / "reg" / "india_morning.md").read_text()
    assert "## Lost or empty runs" in md and "- none" not in md.split("## Jobs")[0]
    lost = "\n".join(r["lost"])
    assert "paper: exit 1: india.paper: _duckdb.CatalogException" in lost
    assert "paper: empty run" in lost                                  # the decision exists, the marks were never written
    assert "spreads: exit 1: token dead, expected" in lost and "next sign-in Tue 20 Oct 22:00-23:40 Toronto" in lost
    assert "recorder_noon: lost run: due Mon 19 Oct 12:30" in lost
    assert not any(x.startswith("nightly") for x in r["lost"])
    assert "missed movers: no manifest for 2026-10-19" in lost and "SP1 nightly replay: no result file" in lost
    assert "explorer" not in md


def test_morning_summary_none_when_all_ran(lake, tmp_path):
    from india import missed, morning

    agents, logs = tmp_path / "agents", tmp_path / "logs"
    agents.mkdir()
    logs.mkdir()
    dec = lake / "paper" / "decisions"
    dec.mkdir(parents=True, exist_ok=True)
    (dec / f"{T}.json").write_text(json.dumps({"signals": [1], "decided_at": "2026-10-20T02:30:12+00:00"}))
    (lake / "paper" / "marks.jsonl").write_text(json.dumps({"at": "2026-10-20T02:30:12+00:00"}) + "\n")
    _job(agents, logs, "paper", {"Hour": 22, "Minute": 30}, "{}", "", _ts(2026, 10, 19, 22, 31), _ts(2026, 10, 19, 22, 30))
    _job(agents, logs, "nightly", {"Hour": 2, "Minute": 30}, NIGHTLY_OK, "", _ts(2026, 10, 20, 2, 37), _ts(2026, 10, 20, 2, 30))
    man = {"date": str(T), "status": "ok", "md_line": f"| {T} | 30 up | caught 1 | a 1 / b 20 / c 1 | 28 down | x | 0 |"}
    (paths.manifest_dir() / f"missed_{T}.json").write_text(json.dumps(man))
    (paths.manifest_dir() / "sp1_nightly_replay.json").write_text(json.dumps({"date": str(T), "status": "skipped (no ledger rows)", "verify": {"ok": True}}))
    lc = "-\t0\tcom.ananta.india.paper\n-\t0\tcom.ananta.india.nightly\n"
    r = morning.build(now=dt.datetime(2026, 10, 20, 7, 0, tzinfo=TOR), launchctl_text=lc, agents=agents, reg=tmp_path / "reg")
    assert r["lost"] == []
    md = (tmp_path / "reg" / "india_morning.md").read_text()
    assert "## Lost or empty runs\n\n- none" in md and f"| {T} | 30 up |" in md and "skipped (no ledger rows)" in md
    assert missed.MD_HEAD.splitlines()[-2] in md                        # the missed-movers table header


def test_last_due_and_signin():
    from india import morning

    now = dt.datetime(2026, 10, 20, 7, 0, tzinfo=TOR)   # Tuesday
    assert morning.last_due({"Hour": 22, "Minute": 30}, now) == dt.datetime(2026, 10, 19, 22, 30, tzinfo=TOR)
    assert morning.last_due([{"Weekday": 5, "Hour": 12, "Minute": 30}], now) == dt.datetime(2026, 10, 16, 12, 30, tzinfo=TOR)
    assert morning.last_due([{"Weekday": 0, "Hour": 22, "Minute": 35}], now) == dt.datetime(2026, 10, 18, 22, 35, tzinfo=TOR)
    hol = {HOL}
    assert morning.next_signin(now, hol).startswith("Tue 20 Oct 22:00-23:40 Toronto")
    fri = dt.datetime(2026, 10, 23, 7, 0, tzinfo=TOR)   # after Friday's session: the next is Monday, signed in Sunday evening Toronto
    assert morning.next_signin(fri, hol).startswith("Sun 25 Oct 22:00-23:40 Toronto")
