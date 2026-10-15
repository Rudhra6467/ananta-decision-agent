"""Worker Mac stage S1 (Oct 15): its health, the nightly pull of finished days, and the measured NDAX costs."""
import shutil
import sqlite3
import subprocess
import time
import types


def _l1(path, coin_rows, btc=(100.0, 100.5)):
    con = sqlite3.connect(path)
    con.executescript("CREATE TABLE ndax (t INTEGER, coin TEXT, bid REAL, ask REAL, last REAL, notional24_cad REAL, ex_ms INTEGER);"
                      "CREATE TABLE binance (t INTEGER, coin TEXT, bid REAL, ask REAL, bid_qty REAL, ask_qty REAL);"
                      "CREATE TABLE fx (t INTEGER, usdcad REAL, obs_day TEXT); CREATE TABLE site (t INTEGER, ok INTEGER, ms INTEGER, detail TEXT);")
    t0 = int(time.time()) - 2 * 86400
    t0 -= t0 % 86400
    for k, (bid, ask) in enumerate(coin_rows):
        con.execute("INSERT INTO ndax VALUES (?, 'XYZ', ?, ?, NULL, NULL, NULL)", (t0 + 60 * k, bid, ask))
        con.execute("INSERT INTO binance VALUES (?, 'XYZ', ?, ?, 1, 1)", (t0 + 60 * k, 0.99 * bid / 1.4, 0.99 * ask / 1.4))
        con.execute("INSERT INTO binance VALUES (?, 'BTC', ?, ?, 1, 1)", (t0 + 60 * k, btc[0] if k == 0 else btc[1], (btc[0] if k == 0 else btc[1]) + 0.1))
        con.execute("INSERT INTO site VALUES (?, ?, 200, '')", (t0 + 60 * k, 0 if k in (1, 2) else 1))
    con.execute("INSERT INTO fx VALUES (?, 1.4, 'x')", (t0,))
    con.commit()
    con.close()
    return time.strftime("%Y-%m-%d", time.gmtime(t0))


def test_status_is_cached_and_says_why(monkeypatch):
    from jarvis.service import worker

    calls = []

    def ssh(cmd, timeout=20):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "STALE · last good round 400 s ago", "")

    monkeypatch.setattr(worker, "_ssh", ssh)
    worker._CACHE.clear()
    s = worker.status()
    assert s["state"] == "STALE" and not s["ok"] and worker.status() is s and len(calls) == 1      # cached
    monkeypatch.setattr(worker, "_ssh", lambda cmd, timeout=20: (_ for _ in ()).throw(TimeoutError("no route")))
    assert worker.status(max_age_s=0)["state"] == "UNREACHABLE"


def test_pull_takes_each_finished_day_once_and_never_today(tmp_path, monkeypatch):
    from jarvis.service import worker

    src = tmp_path / "remote"
    src.mkdir()
    day = _l1(src / "x.sqlite", [(10.0, 10.1)] * 3)
    shutil.move(src / "x.sqlite", src / f"l1_{day}.sqlite")
    today = time.strftime("%Y-%m-%d", time.gmtime())
    (src / f"l1_{today}.sqlite").write_bytes(b"still being written")
    monkeypatch.setattr(worker, "_remote_files", lambda: {p.name: p.stat().st_size for p in src.iterdir()})

    def fake_run(args, **kw):
        if args[0] == "scp":
            shutil.copy(src / args[-2].rsplit("/", 1)[1], args[-1])
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(worker.subprocess, "run", fake_run)
    dest = tmp_path / "here"
    r = worker.pull(dest)
    assert [x["day"] for x in r["pulled"]] == [day] and r["pulled"][0]["ndax"] == 3 and not r["failed"]
    assert not (dest / f"l1_{today}.sqlite").exists()
    assert worker.pull(dest)["pulled"] == []                                    # never twice
    assert worker.outside_view(7, dest)["failed"] == 2 and worker.outside_view(7, dest)["windows"][0]["minutes"] == 2


def test_measured_cost_per_side_against_the_assumed_one(tmp_path):
    from jarvis.service import ndax_spreads

    _l1(tmp_path / "l1_x.sqlite", [(99.0, 101.0)] * 5)                          # 1% half-spread on a mid of 100
    (tmp_path / "l1_x.sqlite").rename(tmp_path / f"l1_{time.strftime('%Y-%m-%d', time.gmtime(time.time() - 2 * 86400))}.sqlite")
    t = ndax_spreads.table(14, tmp_path, cost_fn=lambda c: 0.006)
    row = t["coins"][0]
    assert row["coin"] == "XYZ" and row["minutes"] == 5 and row["half_spread_median_pct"] == 1.0
    assert row["cost_per_side_measured_pct"] == 1.2 and row["cost_per_side_assumed_pct"] == 0.6 and row["dearer_than_assumed"] is True
    assert abs(row["premium_vs_binance_pct"] - 1.01) < 0.02                       # NDAX mid vs Binance mid x USD/CAD
    assert ndax_spreads.summary(14, tmp_path, cost_fn=lambda c: 0.006)["dearer_than_assumed"] == ["XYZ"]


def test_health_calls_the_worker_quiet_only_after_15_minutes(tmp_path, monkeypatch):
    from jarvis.service import health, worker

    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "ananta_worker").write_text("key")
    monkeypatch.setattr(health.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(worker, "status", lambda: {"ok": False, "state": "UNREACHABLE", "line": "no route", "checked_t": 0})
    monkeypatch.setitem(health.STATE, "check_worker", True)
    health.STATE.pop("worker_bad_t", None)
    j = types.SimpleNamespace(dir=tmp_path)
    get = lambda url, timeout=5.0: (200, {})  # noqa: E731
    t0 = 2_000_000_000
    assert health.checks(j, get=get, now=t0)["worker"]["ok"] is True                 # one bad answer is not an outage
    assert health.checks(j, get=get, now=t0 + 14 * 60)["worker"]["ok"] is True
    w = health.checks(j, get=get, now=t0 + 16 * 60)["worker"]
    assert w["ok"] is False and "unreachable for 16 min" in w["detail"]
    health.STATE.pop("worker_bad_t", None)
