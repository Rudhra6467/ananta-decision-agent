"""The shadow trader (Phase 4.3 of the 29 Oct 2026 plan; Madhav: "yes, let's build"): an independent model's plan for the session, written
from the same facts as Ananta's morning view but blind to Ananta's plan and words, sealed before the open, scored by the same code.

Its job is to find what Ananta's rules do not consider, not to replace them. Twenty sessions before anything is read into it.

  python -m india.shadow score        score every sealed plan whose session has closed: the stance against the practice book's day, the
                                      watch names at 1, 5 and 20 sessions against the universe; paper/shadow/summary.json and words
  python -m india.shadow status       the summary as it stands

Files: paper/shadow/<session>.json (the plan, its sha256 over the canonical JSON plus the facts' sha, made_at, the deadline), never rewritten;
scores appended under "scores". The take (bull / bear / neutral odds) goes to the forecast ledger with basis "shadow: ..." through india.forecast.write,
which refuses anything written after 09:15 IST, so the seal is the ledger's own hash chain. Paper only; never advice; no order is possible here.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from india import paths   # india.sealed (duckdb) is imported inside _closes only: the India web service seals plans without duckdb, and the name
                         # sealed at module level is the plan check below (a module-level import was shadowed by it)

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STANCES = ("trade_as_planned", "stand_down", "reduce_risk")
NEED = 20
SHADOW_START = "2026-10-30"   # the first sealed shadow plan; a constant start, as india/leakcheck.py requires of a review module


def _dir() -> Path:
    p = paths.data_dir() / "paper" / "shadow"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _canon(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), default=str)


def sealed(session: str) -> bool:
    return (_dir() / f"{session}.json").exists()


def seal(session: str, plan: dict, facts_sha: str, model: str, forecast_id: str | None, raw: str = "") -> dict:
    """Writes the plan once; a second plan for the same session is refused (the first one stands)."""
    p = _dir() / f"{session}.json"
    if p.exists():
        raise ValueError(f"a shadow plan for {session} is already sealed")
    now = dt.datetime.now(dt.timezone.utc)
    deadline = dt.datetime.fromisoformat(session).replace(hour=9, minute=15, tzinfo=IST)
    if now >= deadline:
        raise ValueError(f"too late: the shadow plan for {session} must be sealed before {deadline.isoformat()}")
    if plan.get("stance") not in STANCES:
        raise ValueError(f"stance must be one of {STANCES}")
    rec = {"session": session, "made_at": now.isoformat(timespec="seconds"), "deadline": deadline.isoformat(), "model": model, "facts_sha": facts_sha,
           "plan": plan, "forecast_id": forecast_id, "raw_tail": raw[-400:], "scores": []}
    rec["sha256"] = hashlib.sha256((_canon(plan) + facts_sha).encode()).hexdigest()
    p.write_text(json.dumps(rec, indent=1, default=str))
    return rec


def _closes():
    """Close per (symbol, date) on live paper days: stocks through the shadow's own sealed reader (purpose shadow_score, admitted in the leak
    check by Madhav's yes of 30 Oct 2026) and the two indices through the paper-context reader, so index and stock watch names are both scored."""
    import pandas as pd

    from india import sealed   # the module, not the plan check of the same name above
    parts = []
    try:
        parts.append(sealed.read_shadow("shadow_score", SHADOW_START))
    except Exception:  # noqa: BLE001
        pass
    try:   # the indices from the technicals panel's chart block (already built nightly); a review module calls only its own sealed reader
        tj = json.loads((paths.manifest_dir() / "technicals.json").read_text())
        for name, sym in (("NIFTY 50", "NIFTY"), ("NIFTY BANK", "BANKNIFTY")):
            ch = ((tj.get("indices") or {}).get(name) or {}).get("chart") or {}
            parts.append(pd.DataFrame({"symbol": sym, "date": ch.get("dates") or [], "close": ch.get("closes") or []}))
    except (OSError, ValueError):
        pass
    if not parts:
        return None
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _book_day(session: str) -> float | None:
    """The practice book's (hold_20d reference) day return on the session: bookstats.daily_book_returns keys days by the mark's UTC date; the
    mark for an Indian session is written the evening after it in Toronto, i.e. on the next UTC date."""
    from india import bookstats
    p = paths.data_dir() / "paper" / "marks.jsonl"
    if not p.exists():
        return None
    marks = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    series = dict(bookstats.daily_book_returns(marks))
    nxt = (dt.date.fromisoformat(session) + dt.timedelta(days=1)).isoformat()
    return series.get(nxt)


def score() -> dict:
    cl = _closes()
    out = {"scored": 0, "sessions": []}
    for p in sorted(_dir().glob("20*.json")):
        rec = json.loads(p.read_text())
        session = rec["session"]
        done = {s["what"] for s in rec.get("scores", [])}
        changed = False
        if "stance" not in done:
            br = _book_day(session)
            if br is not None:
                st = rec["plan"].get("stance")
                hit = (br < 0) if st in ("stand_down", "reduce_risk") else (br >= 0)
                rec["scores"].append({"what": "stance", "book_day_return": br, "stance": st, "hit": bool(hit), "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
                changed = True
        if cl is not None:
            sd = dt.date.fromisoformat(session)
            days = sorted(d for d in cl["date"].unique() if d >= sd)
            for h in (1, 5, 20):
                key = f"watch_{h}"
                if key in done or len(days) <= h:
                    continue
                d0, dh = days[0], days[h]
                base = cl[cl["date"] == d0].set_index("symbol")["close"]
                end = cl[cl["date"] == dh].set_index("symbol")["close"]
                uni = (end / base - 1).dropna()
                uni = uni[(base.reindex(uni.index) > 10)]
                rows = []
                for w in rec["plan"].get("watch") or []:
                    sym = str(w.get("symbol", "")).upper()
                    if sym in uni.index:
                        r = float(uni[sym]) * (1 if w.get("direction", "up") == "up" else -1)
                        u = float(uni.drop(["NIFTY", "BANKNIFTY"], errors="ignore").mean()) if len(uni) else 0.0
                        rows.append({"symbol": sym, "direction": w.get("direction", "up"), "signed_return": r, "right_way": bool(r > 0),
                                     "beat_universe": bool(r > u * (1 if w.get("direction", "up") == "up" else -1))})
                rec["scores"].append({"what": key, "from": str(d0), "to": str(dh), "universe_mean": float(uni.mean()) if len(uni) else None, "names": rows,
                                      "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
                changed = True
        if changed:
            p.write_text(json.dumps(rec, indent=1, default=str))
            out["scored"] += 1
        out["sessions"].append(session)
    return {**out, **summary()}


def summary() -> dict:
    recs = [json.loads(p.read_text()) for p in sorted(_dir().glob("20*.json"))]
    n = len(recs)
    stance = [s for r in recs for s in r.get("scores", []) if s["what"] == "stance"]
    watch1 = [x for r in recs for s in r.get("scores", []) if s["what"] == "watch_1" for x in s["names"]]
    watch5 = [x for r in recs for s in r.get("scores", []) if s["what"] == "watch_5" for x in s["names"]]
    stances = {k: sum(1 for r in recs if r["plan"].get("stance") == k) for k in STANCES}
    silent = sum(1 for r in recs if r["plan"].get("silent"))
    s = {"sessions_sealed": n, "need": NEED, "complete": n >= NEED, "stances": stances, "silent_days": silent,
         "stance_scored": len(stance), "stance_hits": sum(1 for x in stance if x["hit"]),
         "watch_1_names": len(watch1), "watch_1_right_way": sum(1 for x in watch1 if x.get("right_way")),
         "watch_5_names": len(watch5), "watch_5_right_way": sum(1 for x in watch5 if x.get("right_way")),
         "watch_1_beat_universe": sum(1 for x in watch1 if x.get("beat_universe")),
         "note": "watch names scored by direction and against the average stock (stocks through the shadow's own sealed reader, admitted 30 Oct)",
         "blind_spots": [r["plan"].get("blind_spot") for r in recs[-5:] if r["plan"].get("blind_spot")],
         "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    if n == 0:
        s["words"] = "the shadow trader has no sealed plan yet"
    elif n < NEED:
        s["words"] = (f"the shadow trader (a second model, blind to Ananta's plan) has {n} of {NEED} sessions sealed; nothing is read into it before {NEED}. "
                      f"So far: {stances['trade_as_planned']} 'trade as planned', {stances['stand_down']} 'stand down', {stances['reduce_risk']} 'reduce risk'")
    else:
        s["words"] = (f"the shadow trader has {n} sessions: its stance was right on {s['stance_hits']} of {s['stance_scored']} scored days; "
                      f"its index calls went the right way {s['watch_1_right_way']} of {s['watch_1_names']} times the next day")
    (_dir() / "summary.json").write_text(json.dumps(s, indent=1, default=str))
    return s


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    print(json.dumps(score() if cmd == "score" else summary(), indent=1, default=str))
