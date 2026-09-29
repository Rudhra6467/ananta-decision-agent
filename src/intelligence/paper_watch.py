"""Unattended hourly paper watch (operator grant 2026-09-29: "unattended paper: yes").

One tick, a couple of minutes after every 1h bar closes:

  1. POST Hands /api/cycle/run  (the same call as the dashboard "Run Cycle Now")
  2. save the envelope (watch_runs/ + /tmp/cycle_all.json)
  3. cycle_ingest.run_envelope  -> L2 + G5 + paper path + SD6 exit manager
  4. append one heartbeat line to watch_heartbeat.jsonl
  5. alert (macOS notification + watch_alerts.jsonl) on anything that matters

Gaps: a closed bar the watch never looked at is recorded as a gap in the
heartbeat. Hands evaluates the live market, so a missed look cannot be
re-run later; it is recorded, never invented. SD6 itself catches up every
closed bar for an open position on the next tick, so exits are not lost.

Laws: paper only. exec=False, live=False, counts_for_m2=False. Never writes
Mongo. Hands down = alert + retry, never a guessed decision.

Run:     python -m src.intelligence.paper_watch            (forever)
         python -m src.intelligence.paper_watch once       (one tick now)
         python -m src.intelligence.paper_watch status     (last looks + gaps)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.intelligence import cycle_ingest, paper_exit

VERSION = "paper.watch.v1"
HOUR_S = 3600
OFFSET_S = 120  # look 2 minutes after the bar closes
RETRY_S = 300
RUNS = Path("watch_runs")
HEARTBEAT = Path("watch_heartbeat.jsonl")
ALERTS = Path("watch_alerts.jsonl")
ENVELOPE = Path("/tmp/cycle_all.json")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def notify(title: str, body: str, *, level: str = "INFO") -> None:
    """Local alert. macOS notification when available; always logged to watch_alerts.jsonl."""
    rec = {"ts": _now().isoformat(), "level": level, "title": title, "body": body}
    with ALERTS.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    if sys.platform == "darwin" and os.getenv("ANANTA_WATCH_NOTIFY", "1") != "0":
        safe = lambda s: s.replace("\\", "\\\\").replace('"', "'")  # noqa: E731
        try:
            subprocess.run(["osascript", "-e", f'display notification "{safe(body)[:220]}" with title "{safe(title)[:60]}"'],
                           timeout=10, check=False, capture_output=True)
        except Exception:  # noqa: BLE001
            pass


TOKEN_FILE = Path(os.getenv("ANANTA_TOKEN_FILE", "/tmp/ananta_login.json"))


def _token() -> tuple[str, str]:
    """Owner token: .env login first, then the saved login file used by the manual cycle client."""
    from src.tools import ananta_api

    tok = ananta_api.login()
    if tok.get("success") and tok.get("token"):
        return tok["token"], "env_login"
    try:
        saved = json.loads(TOKEN_FILE.read_text()).get("token")
    except (OSError, json.JSONDecodeError, AttributeError):
        saved = None
    if saved:
        return saved, "token_file"
    raise RuntimeError(f"LOGIN_FAILED:{str(tok.get('error') or tok.get('status_code'))[:120]} and no {TOKEN_FILE}")


def run_hands_cycle(timeout: int = 180) -> dict[str, Any]:
    import requests

    from src.tools import ananta_api

    token, how = _token()
    r = requests.post(f"{ananta_api.BASE_URL}/api/cycle/run", data=b"{}",
                      headers={**ananta_api.get_headers(token)}, timeout=timeout)
    if r.status_code in (401, 403):
        raise RuntimeError(f"AUTH_REJECTED_{r.status_code} via {how} (fix ANANTA_PASSWORD in .env, or refresh {TOKEN_FILE})")
    r.raise_for_status()
    env = r.json()
    if not isinstance(env, dict) or not env.get("results"):
        raise RuntimeError("EMPTY_ENVELOPE")
    env["_auth"] = how
    return env


def _last_heartbeat() -> dict[str, Any] | None:
    if not HEARTBEAT.exists():
        return None
    last = None
    for line in HEARTBEAT.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("ok"):
            last = rec
    return last


def _bar_ms(env: dict[str, Any]) -> float | None:
    try:
        return float(env.get("last_bar_open"))
    except (TypeError, ValueError):
        return None


def tick(*, cycle: Callable[[], dict] = run_hands_cycle, sd6_kw: dict | None = None) -> dict[str, Any]:
    started = _now()
    try:
        env = cycle()
    except Exception as exc:  # noqa: BLE001
        rec = {"version": VERSION, "ts": started.isoformat(), "ok": False, "error": str(exc)[:300]}
        with HEARTBEAT.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        notify("Ananta watch: Hands unreachable", rec["error"], level="ERROR")
        return rec

    RUNS.mkdir(exist_ok=True)
    cid = str(env.get("cycle_id") or started.strftime("%Y%m%dT%H%M%S"))
    run_path = RUNS / f"{cid}.json"
    run_path.write_text(json.dumps(env))
    try:
        ENVELOPE.write_text(json.dumps(env))
    except OSError:
        pass

    prev = _last_heartbeat()
    bar = _bar_ms(env)
    missed = 0
    if prev and prev.get("last_bar_open") and bar:
        missed = max(0, int(round((bar - float(prev["last_bar_open"])) / (HOUR_S * 1000))) - 1)
    same_bar = bool(prev and bar and prev.get("last_bar_open") == bar)

    report = cycle_ingest.run_envelope(run_path, sd6_kw=sd6_kw)
    board = report.get("board") or []
    issued = {}
    for row in board:
        issued[row.get("issued") or "-"] = issued.get(row.get("issued") or "-", 0) + 1
    sd6 = report.get("sd6") or {}
    sd6_events = [e.get("kind") for m in sd6.get("managed") or [] for e in m.get("events") or []]
    rec = {
        "version": VERSION,
        "ts": started.isoformat(),
        "ok": True,
        "cycle_id": cid,
        "last_bar_open": bar,
        "bar_open_utc": datetime.fromtimestamp(bar / 1000, timezone.utc).isoformat() if bar else None,
        "same_bar_as_previous": same_bar,
        "auth": env.get("_auth"),
        "missed_bars_since_previous": missed,
        "look_class": report.get("look_class"),
        "regimes": {r.get("asset"): r.get("regime") for r in board},
        "issued": issued,
        "takes": [r.get("asset") for r in board if r.get("issued") == "TAKE"],
        "sd6_opened": [o.get("asset") for o in sd6.get("opened") or []],
        "sd6_refused": [o.get("reason") for o in sd6.get("refused") or []],
        "sd6_events": sd6_events,
        "sd6_errors": sd6.get("errors") or sd6.get("error"),
        "book": {k: (sd6.get("ledger") or {}).get(k) for k in ("cash", "realized_pnl", "trade_count", "wins", "losses")},
        "exec": False, "live": False, "counts_for_m2": False,
    }
    with HEARTBEAT.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")

    if env.get("_auth") == "token_file" and not (prev or {}).get("auth") == "token_file":
        notify("Ananta watch: using saved token", "The .env login failed. When the saved token expires the watch stops; fix ANANTA_PASSWORD in .env.", level="WARN")
    if missed:
        notify("Ananta watch: gap", f"{missed} closed 1h bar(s) were never looked at before {rec['bar_open_utc']}", level="WARN")
    if rec["takes"]:
        notify("Ananta: paper TAKE", f"{', '.join(rec['takes'])} — SD6 opened {rec['sd6_opened'] or 'none'} refused {rec['sd6_refused'] or 'none'}", level="EVENT")
    for m in sd6.get("managed") or []:
        for e in m.get("events") or []:
            if e.get("kind") == "CLOSED":
                notify("Ananta: paper exit", f"{m.get('id')} {e.get('module')}/{e.get('exit_reason')} pnl {e.get('pnl')}", level="EVENT")
            elif e.get("kind") in ("TIGHTEN", "PARTIAL", "DATA_STALE"):
                notify(f"Ananta SD6: {e.get('kind')}", str(m.get("id")), level="INFO" if e.get("kind") != "DATA_STALE" else "WARN")
    if rec["sd6_errors"]:
        notify("Ananta SD6 error", str(rec["sd6_errors"])[:200], level="ERROR")
    return rec


def seconds_to_next_look(now: datetime | None = None) -> float:
    now = now or _now()
    s = now.minute * 60 + now.second + now.microsecond / 1e6
    wait = (OFFSET_S - s) % HOUR_S
    return wait if wait > 1 else wait + HOUR_S


def run_forever() -> None:
    notify("Ananta watch started", f"{VERSION}: hourly look at HH:02 UTC, paper only", level="INFO")
    while True:
        rec = tick()
        ok = rec.get("ok")
        print(f"[{rec['ts']}] ok={ok} bar={rec.get('bar_open_utc')} look={rec.get('look_class')} issued={rec.get('issued')} "
              f"takes={rec.get('takes')} sd6={rec.get('sd6_events')} book={rec.get('book')} missed={rec.get('missed_bars_since_previous')}"
              + ("" if ok else f" error={rec.get('error')}"), flush=True)
        time.sleep(RETRY_S if not ok else seconds_to_next_look())


def print_status(n: int = 12) -> None:
    lines = HEARTBEAT.read_text().splitlines() if HEARTBEAT.exists() else []
    recs = [json.loads(x) for x in lines if x.strip()]
    ok = [r for r in recs if r.get("ok")]
    print(f"\nPAPER WATCH  {VERSION}")
    print("=" * 64)
    print(f"  looks={len(ok)} failed={len(recs) - len(ok)} missed_bars_total={sum(r.get('missed_bars_since_previous') or 0 for r in ok)}")
    for r in recs[-n:]:
        if not r.get("ok"):
            print(f"  {r['ts'][:16]}  FAILED {r.get('error')}")
            continue
        print(f"  {str(r.get('bar_open_utc'))[:16]}  {str(r.get('look_class')):<22} {r.get('issued')}  takes={r.get('takes')} sd6={r.get('sd6_events')} missed={r.get('missed_bars_since_previous')}")
    print("=" * 64)
    paper_exit.print_status()


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["run"])[0]
    if cmd == "once":
        print(json.dumps(tick(), indent=2, default=str))
    elif cmd == "status":
        print_status()
    elif cmd == "run":
        run_forever()
    else:
        raise SystemExit(f"unknown command {cmd!r}: use run | once | status")
