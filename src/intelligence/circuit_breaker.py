"""Loss-streak circuit breaker (pre-live safety, 2026-09-30).

Plan (operator): "4-5 straight losses -> pause, notify with evidence, human approval to resume".
Hands has no such breaker (its circuit_breaker.py is a macro/news VETO layer that never fires by
design; it has a manual kill switch and a 10% daily-loss stop). This is the account-level breaker.

Rules (per book):
  TRIP when the last N closed trades are all losses (default N=4), or when the book's $ drawdown
  from its peak P&L reaches DD_LIMIT of starting capital (default 20%).
  TRIPPED: no new entries for that book. Open positions keep being managed (exits always work).
  RESUME: only a human, by CLI, with a name recorded. Never automatic.
  LIVE (future): when mode=LIVE, tripping also engages the Hands manual kill switch via the API.
  In PAPER it never touches Hands.

CLI:
    python -m src.intelligence.circuit_breaker status
    python -m src.intelligence.circuit_breaker resume --book candidate_v1_book.sqlite --by "Vamsi"
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

STATE = Path("breaker_state.json")
LOSS_STREAK = 4
DD_LIMIT = 0.20


def _load(path: Path = STATE) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save(st: dict, path: Path = STATE) -> None:
    path.write_text(json.dumps(st, indent=1))


def is_tripped(book: str, path: Path = STATE) -> bool:
    return (_load(path).get(book) or {}).get("status") == "TRIPPED"


def evaluate(book: str, closed: list[dict], start_capital: float, *, path: Path = STATE,
             streak_n: int = LOSS_STREAK, dd_limit: float = DD_LIMIT) -> dict[str, Any]:
    """closed: closed trades with 'net_usd' and 'exit_ms'. Returns the book's breaker state (and trips it)."""
    st = _load(path)
    cur = st.get(book) or {"status": "ARMED"}
    trades = sorted(closed, key=lambda t: t.get("exit_ms") or 0)
    since = cur.get("resumed_after_ms") or 0
    recent = [t for t in trades if (t.get("exit_ms") or 0) > since]  # a human resume starts a fresh count
    streak = 0
    for t in reversed(recent):
        if (t.get("net_usd") or 0) < 0:
            streak += 1
        else:
            break
    pnl, peak, dd = 0.0, 0.0, 0.0
    for t in recent:
        pnl += t.get("net_usd") or 0.0
        peak = max(peak, pnl)
        dd = max(dd, peak - pnl)
    cur.update(consecutive_losses=streak, drawdown_usd=round(dd, 4), drawdown_pct_of_start=round(100 * dd / start_capital, 2),
               checked_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    newly = False
    if cur.get("status") != "TRIPPED":
        reason = None
        if streak >= streak_n:
            reason = f"{streak} losses in a row (limit {streak_n})"
        elif dd >= dd_limit * start_capital:
            reason = f"drawdown ${dd:.2f} = {100 * dd / start_capital:.1f}% of start (limit {100 * dd_limit:.0f}%)"
        if reason:
            cur.update(status="TRIPPED", reason=reason, tripped_at=cur["checked_at"],
                       evidence=[{k: t.get(k) for k in ("id", "coin", "net_usd", "exit_reason", "exit_ms")} for t in recent[-streak_n:]])
            newly = True
    st[book] = cur
    _save(st, path)
    return {**cur, "newly_tripped": newly}


def resume(book: str, by: str, path: Path = STATE) -> dict[str, Any]:
    if not by.strip():
        raise ValueError("a human name is required to resume")
    st = _load(path)
    cur = st.get(book) or {}
    if cur.get("status") != "TRIPPED":
        return {"book": book, "status": cur.get("status", "ARMED"), "note": "not tripped"}
    now_ms = time.time() * 1000
    cur.setdefault("history", []).append({"tripped_at": cur.get("tripped_at"), "reason": cur.get("reason"),
                                          "resumed_by": by, "resumed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    cur.update(status="ARMED", resumed_after_ms=now_ms, reason=None, evidence=None)
    st[book] = cur
    _save(st, path)
    return {"book": book, "status": "ARMED", "resumed_by": by}


def engage_hands_kill_switch() -> dict[str, Any]:
    """LIVE only: set Hands manual_kill_switch=True (halts all new entries; Hands pushes its own alert)."""
    import requests

    from src.tools import ananta_api

    tok = ananta_api.login()
    r = requests.put(f"{ananta_api.BASE_URL}/api/settings", json={"manual_kill_switch": True},
                     headers=ananta_api.get_headers(tok.get("token")), timeout=20)
    return {"status_code": r.status_code, "ok": r.status_code == 200}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "resume"])
    ap.add_argument("--book")
    ap.add_argument("--by", default="")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        st = _load()
        if not st:
            print("no breaker state yet (nothing tripped)")
        for book, cur in st.items():
            print(f"{book}: {cur.get('status')}  losses_in_a_row={cur.get('consecutive_losses')}  "
                  f"drawdown={cur.get('drawdown_pct_of_start')}% of start  reason={cur.get('reason')}")
    else:
        if not a.book:
            raise SystemExit("--book is required")
        print(json.dumps(resume(a.book, a.by), indent=1))


if __name__ == "__main__":
    main()
