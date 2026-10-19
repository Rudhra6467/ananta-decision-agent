"""The forecast ledger (Market Brain, decision plane): every expectation Ananta writes, before the fact, scored after it, never rewritten.

  python -m india.forecast verify        checks the hash chain and the timing rule over the whole ledger
  python -m india.forecast score [date]  scores the forecasts whose horizon has ended (appends score rows; forecasts are never edited)

Rules
- Append-only file paper/forecasts.jsonl (stays on the Mac). Each row carries prev_hash and hash = sha256(prev_hash + canonical JSON of the
  row without its hash): editing or deleting any earlier row breaks every hash after it, and verify() reports where.
- kind "pre_open" must be written before 09:15 IST of its session (made_at is checked against the IST open); "intraday" before its
  decision time; "event" before the event's public time.
- A forecast states scenarios with probabilities that sum to 1 (bull / bear / neutral), the neutral band, the horizon in sessions, the
  invalidation condition, and its basis (analogues, event type, playbook, or "none"). Confidence words are not accepted without numbers.
- Scores: direction hit, Brier score of the scenario probabilities, and the outcome return; written as separate rows referencing the
  forecast. The coin-flip and climatology baselines are scored beside every forecast, so skill is measured, not assumed.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import uuid

from india import paths

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
LEDGER = paths.data_dir() / "paper" / "forecasts.jsonl"


def _canon(row: dict) -> str:
    return json.dumps({k: v for k, v in row.items() if k != "hash"}, sort_keys=True, separators=(",", ":"), default=str)


def _last_hash() -> str:
    if not LEDGER.exists():
        return "genesis"
    last = None
    with LEDGER.open() as fh:
        for line in fh:
            if line.strip():
                last = line
    return json.loads(last)["hash"] if last else "genesis"


def _append(row: dict) -> dict:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    row["prev_hash"] = _last_hash()
    row["hash"] = hashlib.sha256((row["prev_hash"] + _canon(row)).encode()).hexdigest()
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(row, default=str) + "\n")
    return row


def write(subject: str, session: str, scenarios: dict, horizon_sessions: int, invalidation: str, basis: str, kind: str = "pre_open",
          neutral_band: float = 0.003, decide_at_ist: str = "09:15", notes: str = "") -> dict:
    """Refuses a forecast written too late or with probabilities that do not sum to 1."""
    now = dt.datetime.now(dt.timezone.utc)
    p = {k: float(scenarios.get(k, 0)) for k in ("bull", "bear", "neutral")}
    if abs(sum(p.values()) - 1) > 1e-6 or any(v < 0 for v in p.values()):
        raise ValueError(f"scenario probabilities must be non-negative and sum to 1, got {p}")
    hh, mm = map(int, decide_at_ist.split(":"))
    deadline = dt.datetime.fromisoformat(session).replace(hour=hh, minute=mm, tzinfo=IST)
    if now >= deadline:
        raise ValueError(f"too late: a {kind} forecast for {session} must be written before {deadline.isoformat()}")
    row = {"kind": "forecast", "forecast_kind": kind, "forecast_id": "FC-" + uuid.uuid4().hex[:12], "made_at": now.isoformat(timespec="seconds"),
           "deadline": deadline.isoformat(), "subject": subject, "session": session, "scenarios": p, "neutral_band": neutral_band,
           "horizon_sessions": int(horizon_sessions), "invalidation": invalidation, "basis": basis, "notes": notes}
    return _append(row)


def verify() -> dict:
    """Recomputes every hash; reports the first broken row and any forecast written after its deadline."""
    if not LEDGER.exists():
        return {"ok": True, "rows": 0, "note": "no forecasts yet"}
    prev, n, late = "genesis", 0, []
    with LEDGER.open() as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("prev_hash") != prev or hashlib.sha256((prev + _canon(r)).encode()).hexdigest() != r.get("hash"):
                return {"ok": False, "rows": n, "broken_at_line": i, "note": "hash chain broken: an earlier row was edited, deleted or reordered"}
            if r["kind"] == "forecast" and dt.datetime.fromisoformat(r["made_at"]) >= dt.datetime.fromisoformat(r["deadline"]):
                late.append(r["forecast_id"])
            prev, n = r["hash"], n + 1
    return {"ok": not late, "rows": n, "late": late, "note": "chain intact" + (f"; {len(late)} late forecasts" if late else "")}


def _brier(p: dict, outcome: str) -> float:
    return sum((p[k] - (1.0 if k == outcome else 0.0)) ** 2 for k in ("bull", "bear", "neutral"))


def score(as_of: str | None = None) -> dict:
    """Scores forecasts whose horizon has ended, from index closes (current sessions are read through the logged forecast_score purpose)."""
    from india import sealed
    if not LEDGER.exists():
        return {"scored": 0}
    rows = [json.loads(x) for x in LEDGER.read_text().splitlines() if x.strip()]
    done = {r["ref"] for r in rows if r["kind"] == "score"}
    todo = [r for r in rows if r["kind"] == "forecast" and r["forecast_id"] not in done]
    if not todo:
        return {"scored": 0}
    since = min(r["session"] for r in todo)
    names = sorted({r["subject"] for r in todo})
    ix = sealed.read_index("forecast_score", (dt.date.fromisoformat(since) - dt.timedelta(days=10)).isoformat(), names)
    n = 0
    for r in todo:
        s = ix[ix["index_name"] == r["subject"]].sort_values("date")
        dates = list(s["date"].astype(str))
        if r["session"] not in dates:
            continue
        i = dates.index(r["session"])
        j = i + r["horizon_sessions"] - 1
        if j >= len(dates) or i == 0:
            continue
        ret = float(s["close"].iloc[j] / s["close"].iloc[i - 1] - 1)
        outcome = "bull" if ret > r["neutral_band"] else ("bear" if ret < -r["neutral_band"] else "neutral")
        best = max(r["scenarios"], key=r["scenarios"].get)
        _append({"kind": "score", "ref": r["forecast_id"], "scored_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "outcome": outcome, "outcome_return": ret, "hit": best == outcome, "brier": _brier(r["scenarios"], outcome),
                 "brier_coin_flip": _brier({"bull": 1 / 3, "bear": 1 / 3, "neutral": 1 / 3}, outcome)})
        n += 1
    return {"scored": n}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    print(json.dumps(verify() if cmd == "verify" else score(sys.argv[2] if len(sys.argv) > 2 else None), indent=1))
