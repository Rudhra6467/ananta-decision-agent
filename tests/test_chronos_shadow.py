"""The Chronos shadow (Madhav, 25 Oct 2026): blind, append-only, hash-chained, no outcome kept, sealed until 15 Dec, and read by nothing."""
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from src.research import chronos_shadow as S

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANTA_CHRONOS_SHADOW_DIR", str(tmp_path / "shadow"))
    db = tmp_path / "daily.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE bars (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, qv REAL, tbv REAL, PRIMARY KEY (coin, t))")
    t_last = int(datetime(2026, 10, 25, tzinfo=timezone.utc).timestamp())
    for coin in S.COINS:
        con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?,?,?)", [(coin, t_last - k * 86400, 1, 1, 1, 100.0 + k, 1, 1, 1) for k in range(400)])
    con.commit()
    con.close()
    monkeypatch.setenv("ANANTA_LAKE_DAILY", str(db))
    monkeypatch.setattr(S, "predict", lambda ctx: np.tile(np.linspace(0.98, 1.02, 9), (len(ctx), S.PRED_LEN, 1)) * 100.0)
    return datetime(2026, 10, 26, 8, 20, tzinfo=timezone.utc).timestamp()


def test_one_row_per_coin_per_day_and_the_chain(lake):
    r = S.run(now=lake)
    assert sorted(r["written"]) == ["BTC 2026-10-25", "ETH 2026-10-25"] and r["chain"]["ok"]
    assert S.run(now=lake)["written"] == []                                   # a re-run writes nothing
    log = (S.shadow_dir() / S.RUN_LOG).read_text().splitlines()
    assert log[0].endswith("daily rows=2 status=ok") and "already written" in log[-1]


def test_stale_bars_are_skipped(lake):
    r = S.run(now=lake + 3 * 86400)
    assert r["written"] == [] and all("expected" in s for s in r["skipped"])


def test_no_outcome_is_kept_and_editing_breaks_the_chain(lake):
    with pytest.raises(ValueError):
        S.append({"kind": "forecast", "coin": "BTC", "forecast": {"h1": {"hit": True}}})
    S.run(now=lake)
    p = S.shadow_dir() / S.LOG
    rows = p.read_text().splitlines()
    first = json.loads(rows[0])
    first["origin_close"] = 1.0
    p.write_text(json.dumps(first) + "\n" + "\n".join(rows[1:]) + "\n")
    assert S.verify()["ok"] is False


def test_sealed_until_the_window_ends(lake, monkeypatch):
    monkeypatch.setattr(S.time, "time", lambda: S.SEALED_UNTIL - 1)
    with pytest.raises(S.Sealed):
        S.results()


def test_nothing_reads_the_shadow():
    out = subprocess.run(["git", "-C", str(ROOT), "grep", "-l", "-e", "chronos_crypto", "-e", "chronos_shadow", "--", "jarvis", "src", "scripts"],
                         capture_output=True, text=True).stdout.split()
    allowed = {"src/research/chronos_shadow.py", "jarvis/service/runcheck_parts.py"}      # the module itself; the run checker counts run lines only
    untracked = [f for f in ("jarvis", "src", "scripts")]
    assert set(out) <= allowed, f"something reads the Chronos shadow: {set(out) - allowed}"
    for d in untracked:
        for f in (ROOT / d).rglob("*.py"):
            rel = str(f.relative_to(ROOT))
            if rel not in allowed and ("chronos_crypto" in f.read_text(errors="ignore") or "chronos_shadow" in f.read_text(errors="ignore")):
                pytest.fail(f"{rel} mentions the Chronos shadow")
