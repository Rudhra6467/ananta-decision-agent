"""Fixes from the 25 Oct 2026 process audit: stale inputs are marked (never stopped), the sign-in line reads the automatic sign-in log, the gate
counts consecutive clean sessions, and verdict counts take each version once."""
import datetime as dt
from pathlib import Path

import pandas as pd

from india import morning, paper, readmodel, tracker


def test_stale_inputs_are_marked_not_stopped():
    ctx = {"nifty_status": "stale: last row 2026-10-22", "vix_status": "ok", "small_ratio_status": "missing or stale"}
    m = paper.input_check(ctx, 1950, pd.Timestamp("2026-10-23"))
    assert m["marked"] and any("Nifty 50" in s for s in m["stale"]) and any("small-cap" in s for s in m["stale"])
    assert not any("India VIX" in s for s in m["stale"])
    assert paper.input_check({"nifty_status": "ok", "vix_status": "ok"}, 400, pd.Timestamp("2026-10-23"))["marked"]   # a thin cash file is stale too
    # the mark never enters the hashed decision fields
    body = {"rules": "r", "data_through": "d", "signals": [], "journal": [], "config_sha": "c"}
    assert paper._sha(body) == paper._sha({**body, "inputs": m})


def test_old_decisions_are_marked_from_their_context():
    j = {"context": {"nifty_status": "stale: last row 2026-10-22", "vix_status": "ok"}}
    m = readmodel.decision_inputs(j)
    assert m["marked"] and m["derived"] == "from the recorded context"
    assert not readmodel.decision_inputs({"context": {"nifty_status": "ok", "vix_status": "ok"}})["marked"]


def test_signin_line_reads_the_automatic_log(tmp_path: Path):
    now = dt.datetime(2026, 10, 25, 12, 0, tzinfo=morning.TOR)
    log = tmp_path / "kite_autologin.log"
    log.write_text("2026-10-25T13:58:48+00:00 auto sign-in FAILED: password step refused\n2026-10-25T14:02:57+00:00 auto sign-in ok: user X until ...\n")
    s = morning.autologin_state(now, log)
    assert s["ok"] and "Sun 25 Oct" in s["at"]
    log.write_text("2026-10-25T14:02:57+00:00 auto sign-in FAILED: KITE_TOTP_SECRET is a 6-digit code\n")
    s = morning.autologin_state(now, log)
    assert not s["ok"] and "6-digit" in s["why"]
    assert morning.autologin_state(now, tmp_path / "none.log") is None


def test_gate_counts_consecutive_sessions():
    runs = [pd.Timestamp("2026-10-21 12:50"), pd.Timestamp("2026-10-23 02:35"), pd.Timestamp("2026-10-23 12:50")]
    n = tracker.consecutive_sessions(runs, today="2026-10-25 10:00")
    assert n >= 1           # 23 Oct clean (12:50 run); 22 Oct clean (02:35 next morning); 21 Oct clean
    assert tracker.consecutive_sessions([], today="2026-10-25 10:00") == 0


def test_rerun_reason_and_dirty_code_are_recorded(monkeypatch, tmp_path: Path):
    from india import registry

    led = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(registry, "_ledger_path", lambda: led)
    monkeypatch.setattr(registry, "_stamp", lambda study: {"code": {"git": "abc123", "dirty": ["india/x.py"], "dirty_py": {"india/x.py": "f00"}, "dirty_fingerprint": "deadbeef0001"}})
    monkeypatch.delenv("ANANTA_RERUN_REASON", raising=False)
    r1 = registry.register("ZZ1", family="zz", title="t", hypothesis="h", variants=["a"])
    assert "version" not in r1 and "rerun_reason" not in r1
    r2 = registry.register("ZZ1", family="zz", title="t", hypothesis="h", variants=["a"])
    assert r2["version"] == 2 and r2["rerun_reason"] == "no reason given"
    monkeypatch.setenv("ANANTA_RERUN_REASON", "fixed the date join")
    r3 = registry.register("ZZ1", family="zz", title="t", hypothesis="h", variants=["a"])
    assert r3["rerun_reason"] == "fixed the date join"
    line = registry.record(r3, "a", (0.01, 2.0, 20), (0.01, 2.0, 20))
    assert line["code"] == "abc123+dirty:deadbeef0001" and line["registration_version"] == 3 and line["rerun_reason"] == "fixed the date join"


def test_dirty_python_files_change_the_code_fingerprint(monkeypatch):
    from india import lineage

    calls = {"status": " M india/paper.py\n M india/registrations/verification.md\n", "head": "abc", "hash": "111"}

    def fake_git(*args):
        if args[0] == "rev-parse":
            return calls["head"]
        if args[0] == "status":
            return calls["status"]
        if args[0] == "hash-object":
            return calls["hash"] * 4
        return ""
    monkeypatch.setattr(lineage, "_git", fake_git)
    a = lineage.code_version()
    assert list(a["dirty_py"]) == ["india/paper.py"]          # generated registration files do not count as code
    calls["hash"] = "222"
    b = lineage.code_version()
    assert a["git"] == b["git"] and a["dirty_fingerprint"] != b["dirty_fingerprint"]


def test_missing_reconstruction_card_is_a_lost_run(tmp_path: Path):
    dec = tmp_path / "paper" / "decisions"
    rx = tmp_path / "paper" / "reconstruction"
    dec.mkdir(parents=True)
    rx.mkdir(parents=True)
    (dec / "2026-10-23.json").write_text("{}")
    (rx / "2026-10-22.json").write_text("{}")
    out = morning.reconstruction_problems(tmp_path)
    assert out and "2026-10-23" in out[0] and "2026-10-22" in out[0]
    (rx / "2026-10-23.json").write_text("{}")
    assert morning.reconstruction_problems(tmp_path) == []
