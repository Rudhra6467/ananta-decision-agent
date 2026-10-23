"""The India reconstruction process, RX-IN v1 (Madhav, 23 Oct 2026; design: claude/design-2026-10-23-india-reconstruction-process.md).

  python -m india.reconstruct evening [YYYY-MM-DD]   one session card, the trade reviews, the findings, the queue, the staircase, the page
  python -m india.reconstruct show                   prints the latest card as plain text
  python -m india.reconstruct stairs                 rebuilds registrations/evidence_staircase.json and prints it

Madhav: "it sees around the net, sees what people are doing, notes everything, sees what Ananta did and did not do, and based on findings forwards
things to the repair shop ... where we collect proofs and evidence to forward to the live evidence layer, which can then be used by the allocated
paper capital too." Run every evening after the paper engine, the missed-movers review and the reference-traders league, before the read model.

THE CARD (paper/reconstruction/<session>.json, one per session, never rewritten; registrations/reconstruction.md is the page)
  A market       what the session did: regime, breadth, VIX, the movers with their situation words
  B people       what others did, from public point-in-time records stamped at their public time: bulk/block deals, FII/DII cash, participant
                 open interest, exchange announcements on universe names, registered events, the reference-traders league. Yardstick and event
                 generator only; never a teacher, never copied (crypto rule D8).
  C ananta       what it chose, rejected, filled, exited, called, forecast and moved
  D not_done     what it did not do and whether that was right: the missed movers (a/b/c), the falls it held into, the rejected candidates'
                 counterfactual from the baseline book (labelled hindsight), the league's coverage, the call's score
  E reviews      every trade closed REVIEW_WAIT sessions ago, tagged from its own marks and the after-exit close of its longest-lived sibling
                 policy (the same entry kept open under a longer exit in the same book): no new price read, no new leak path
  F findings     typed rows with a fixed rule each (BARS), a dedupe key, the evidence behind it and a lane decided by code
  G forwarding   what went where: SAFE rows to the repair board (filed by the agent-side script scripts/india_findings.py), DECISION rows to
                 registrations/reconstruction_queue.jsonl as DRAFT or NOTE for Madhav's weekly read
THE STAIRCASE (registrations/evidence_staircase.json): NOTED -> DRAFT -> REGISTERED -> TESTED -> SHADOW -> ADMITTED -> LIVE_ELIGIBLE. The bars
are fixed below (STAIRS). The allocator reads admitted() and may size only ADMITTED rules; nothing is ADMITTED until Madhav says so.
Nothing here reads sealed data, calls the broker or writes a trade. Every bar in BARS and STAIRS was written on 23 Oct 2026 before the first card.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from india import paths

RULES = "rx-in-v1-2026-10-23"
REG = Path(__file__).parent / "registrations"
QUEUE = REG / "reconstruction_queue.jsonl"
STAIRS_FILE = REG / "evidence_staircase.json"
PAGE = REG / "reconstruction.md"
REF_POLICY = "hold_20d"
RESEARCH = ("BRK", "PULL", "REV")
FAMILY_WORDS = {"BRK": "20-session breakout on volume", "PULL": "pullback in an uptrend", "REV": "oversold reversal", "CTL": "random control"}
REVIEW_WAIT = 3                      # sessions after the exit before a trade is reviewed (the after-exit path needs them)
TAG_WORDS = {"STOPPED_THEN_RAN": "stopped out, then the price was a full risk unit above the entry three sessions later (stop too tight, or entered early)",
             "GAVE_BACK": "was up one and a half risk units at some point and still closed at or under the entry (no plan to protect a winner)",
             "NEVER_WORKED": "never got a quarter of a risk unit above the entry (the entry timing was poor)",
             "LEFT_ON_TABLE": "a win, and the price went another risk unit past the exit within three sessions (sold too early)",
             "COSTS_ATE": "the price moved less than the round-trip costs (the trade could not pay)",
             "CLEAN": "a win that kept at least half of its best move",
             "LOST_SMALL": "a loss smaller than a risk unit with no better path on record"}
BARS = {"pattern_days": 3, "pattern_window": 7, "exit_lesson_n": 5, "exit_lesson_window": 20, "held_into_fall_n": 5, "held_days": 3, "held_window": 7,
        "call_window": 20, "alloc_wrong_n": 3, "alloc_window": 20, "alloc_horizon": 5, "options_n": 5, "options_window": 10, "event_notes_to_draft": 3,
        "safe_per_night": 3, "safe_refile_sessions": 7, "data_stale_sessions": 2}
STAIRS = {"version": "stairs-v1-2026-10-23", "shadow_sessions": 20, "admitted_independent_sessions": 10,
          "steps": ["NOTED", "DRAFT", "REGISTERED", "TESTED", "SHADOW", "ADMITTED", "LIVE_ELIGIBLE"],
          "who": {"DRAFT": "code (BARS)", "REGISTERED": "Madhav", "TESTED": "code (india.registry)", "SHADOW": "code (20 recorded sessions)",
                  "ADMITTED": "Madhav (beats RANDOM and MARKET on 10+ independent sessions net of costs; leak check passes; pinned in the lock)",
                  "LIVE_ELIGIBLE": "Madhav (the India gate and the live-readiness rules)"}}


# ------------------------------------------------------------------------------------------------------------------------------- small helpers

def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _data() -> Path:
    return paths.data_dir()


def _paper() -> Path:
    return _data() / "paper"


def _rx() -> Path:
    d = _paper() / "reconstruction"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _jsonl(p: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def _append(p: Path, row: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")


def _r(x, n=4):
    try:
        return None if x is None or x != x else round(float(x), n)
    except (TypeError, ValueError):
        return None


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:+.1f}%"


def _missing(src) -> dict:
    return {"status": "missing", "source": str(src)}


def sessions() -> list[str]:
    """The live sessions the paper book knows, oldest first: every decision day plus every session a trade was marked, entered or exited on."""
    days: set[str] = set()
    for p in (_paper() / "decisions").glob("????-??-??.json"):
        days.add(p.stem)
    st = _load(_paper() / "state.json", {}) or {}
    for t in (st.get("trades") or {}).values():
        for k in ("entry_date", "last_date", "exit_date"):
            if t.get(k):
                days.add(str(t[k]))
    return sorted(days)


def _names() -> dict:
    """symbol -> universe row from the newest universe file."""
    fs = sorted((_paper() / "decisions").glob("*.universe.json"))
    if not fs:
        return {}
    j = _load(fs[-1], {}) or {}
    return {r["symbol"]: r for r in j.get("rows", [])}


# ------------------------------------------------------------------------------------------------------------------------------- A: the market

def section_market(day: str, rm: dict) -> dict:
    src = _paper() / "decisions" / f"{day}.json"
    d = _load(src, {}) or {}
    c = d.get("context") or {}
    if not c:
        return _missing(src)
    man = _load(_data() / "manifests" / f"missed_{day}.json", {}) or {}
    movers = man.get("movers") or []
    up = sorted([m for m in movers if m.get("side") == "up"], key=lambda m: -(m.get("cc") or 0))[:8]
    down = sorted([m for m in movers if m.get("side") == "down"], key=lambda m: (m.get("cc") or 0))[:8]
    trend = {"above_both": "uptrend: above its 50- and 200-day averages", "below_both": "downtrend: below both averages", "mixed": "mixed: between its averages"}
    ts = "above_both" if (c.get("nifty_vs_sma50") or 0) > 0 and (c.get("nifty_vs_sma200") or 0) > 0 else ("below_both" if (c.get("nifty_vs_sma50") or 0) < 0 and (c.get("nifty_vs_sma200") or 0) < 0 else "mixed")
    words = (f"Nifty {c.get('nifty_close'):,.0f}, {trend[ts]} ({_pct(c.get('nifty_vs_sma50'))} vs 50-day, {_pct(c.get('nifty_vs_sma200'))} vs 200-day); "
             f"{100 * (c.get('breadth200_liq') or 0):.0f}% of the liquid 250 above their 200-day; VIX {c.get('vix_close')}.")
    return {"status": "ok", "source": str(src), "nifty_close": c.get("nifty_close"), "trend_state": ts, "nifty_vs_sma50": _r(c.get("nifty_vs_sma50")), "nifty_vs_sma200": _r(c.get("nifty_vs_sma200")),
            "breadth200_liq": _r(c.get("breadth200_liq")), "breadth50_liq": _r(c.get("breadth50_liq")), "vix_close": c.get("vix_close"), "vix_vs_sma50": _r(c.get("vix_vs_sma50")),
            "words": words, "movers_source": str(_data() / "manifests" / f"missed_{day}.json") if man else "missing",
            "movers_up": [{"symbol": m["symbol"], "cc": _r(m.get("cc")), "situation": m.get("situation"), "status": m.get("status"), "class": m.get("class")} for m in up],
            "movers_down": [{"symbol": m["symbol"], "cc": _r(m.get("cc")), "situation": m.get("situation"), "status": m.get("status"), "class": m.get("class")} for m in down]}


# ------------------------------------------------------------------------------------------------------------------------------- B: what people did

def _deals(day: str, names: dict) -> dict:
    d8 = day.replace("-", "")
    out, found = {}, False
    for kind in ("bulk", "block"):
        p = _data() / "bronze" / "deals" / "snap" / kind / day[:4] / f"{kind}_{d8}.csv"
        if not p.exists():
            out[kind] = _missing(p)
            continue
        found = True
        rows = []
        try:
            with p.open(newline="") as f:
                for r in csv.DictReader(f):
                    sym = (r.get("Symbol") or "").strip()
                    if sym in names:
                        try:
                            q = float((r.get("Quantity Traded") or "0").replace(",", ""))
                            px = float((r.get("Trade Price / Wght. Avg. Price") or "0").replace(",", ""))
                        except ValueError:
                            q, px = 0.0, 0.0
                        rows.append({"symbol": sym, "client": (r.get("Client Name") or "").strip()[:60], "side": (r.get("Buy/Sell") or "").strip(), "qty": q, "price": px, "value_inr": round(q * px)})
        except OSError:
            out[kind] = _missing(p)
            continue
        rows.sort(key=lambda x: -x["value_inr"])
        out[kind] = {"status": "ok", "source": str(p), "in_universe": len(rows), "top": rows[:10], "public": "after the close, same day"}
    out["status"] = "ok" if found else "missing"
    return out


def _fiidii(day: str) -> dict:
    src = _data() / "manifests" / "fii_dii_cash.jsonl"
    rows = [x for x in _jsonl(src) if x.get("status") == 200]
    if not rows:
        return _missing(src)
    got = {}
    for x in rows:
        for r in x.get("rows") or []:
            if r.get("date") == day and r.get("category") in ("FII", "DII"):
                got[r["category"]] = r.get("net_cr")
    if not got:
        return {"status": "missing", "source": str(src), "note": f"no row for {day} (captured days: {sorted({r.get('date') for x in rows for r in (x.get('rows') or [])})[-3:]})"}
    words = "; ".join(f"{k} net {'bought' if (v or 0) >= 0 else 'sold'} ₹{abs(v or 0):,.0f} crore" for k, v in got.items())
    return {"status": "ok", "source": str(src), "net_cr": got, "words": words, "public": "T evening, provisional (MSEI); confirmed T+1 (NSDL)"}


def _participant_oi(day: str) -> dict:
    d = dt.date.fromisoformat(day)
    p = _data() / "bronze" / "flows" / "participant_oi" / day[:4] / f"fao_participant_oi_{d.strftime('%d%m%Y')}.csv"
    if not p.exists():
        return {"status": "missing", "source": str(p), "note": "the participant OI file for the day is not in the lake (the flows fetch stops where NSE's archive was reachable)"}
    try:
        from india import flows
        df = flows._parse(p)
    except Exception as e:  # noqa: BLE001
        return {"status": "missing", "source": str(p), "note": f"could not parse: {e.__class__.__name__}"}
    out = {}
    for _, r in df.iterrows():
        ct = str(r.get("client_type") or r.get("Client Type") or "").strip()
        if ct in ("FII", "DII", "Client", "Pro"):
            fl, fs = float(r.get("future_index_long") or 0), float(r.get("future_index_short") or 0)
            out[ct] = {"index_fut_long_share": _r(fl / (fl + fs)) if fl + fs else None}
    return {"status": "ok" if out else "missing", "source": str(p), "by_participant": out, "public": "after the close"}


def _announcements(day: str, names: dict, movers: set) -> dict:
    p = _data() / "bronze" / "announce_api" / day[:4] / f"{day.replace('-', '')}.json.gz"
    if not p.exists():
        return {"status": "missing", "source": str(p), "note": "no announcement file for the session (the announce fetch runs with the evening job)"}
    try:
        rows = json.load(gzip.open(p))
    except (OSError, ValueError):
        return _missing(p)
    keep = []
    for r in rows if isinstance(rows, list) else (rows.get("rows") or []):
        sym = str(r.get("symbol") or "").strip()
        if sym in names:
            keep.append({"symbol": sym, "category": r.get("desc"), "text": str(r.get("attchmntText") or "")[:160], "public_ist": r.get("exchdisstime"), "on_mover": sym in movers})
    keep.sort(key=lambda x: (not x["on_mover"], x["symbol"]))
    return {"status": "ok", "source": str(p), "universe_rows": len(keep), "on_movers": [x for x in keep if x["on_mover"]][:12], "others": [x for x in keep if not x["on_mover"]][:8],
            "public": "the exchange's dissemination minute; after 15:30 IST it is tradable the next session"}


def _events(day: str) -> dict:
    p = _data() / "silver" / "events" / "events.parquet"
    if not p.exists():
        return _missing(p)
    try:
        import pandas as pd
        ev = pd.read_parquet(p, columns=["event_id", "title", "category", "first_tradable_session", "status", "known_beforehand"])
        d = dt.date.fromisoformat(day)
        ev["fts"] = pd.to_datetime(ev["first_tradable_session"]).dt.date
        rows = ev[(ev["fts"] >= d - dt.timedelta(days=3)) & (ev["fts"] <= d)]
        return {"status": "ok", "source": str(p), "recent": [{"id": r.event_id, "title": r.title, "category": r.category, "first_session": str(r.fts), "status": r.status} for r in rows.itertuples()][:8]}
    except Exception as e:  # noqa: BLE001
        return {"status": "missing", "source": str(p), "note": f"{e.__class__.__name__}: {str(e)[:80]}"}


def _league(day: str) -> dict:
    src = _data() / "manifests" / f"others_{day}.json"
    o = _load(src, {}) or {}
    h1 = (o.get("by_h") or {}).get("1") or {}
    if not h1:
        return _missing(src)
    best = [{"symbol": b.get("symbol"), "net": _r(b.get("net")), "situation": b.get("situation"), "class": b.get("class"), "why": b.get("why")} for b in (h1.get("best") or [])[:6]]
    rnd = h1.get("random") or {}
    beats = (h1.get("ananta_mean") is not None and rnd.get("median") is not None and h1.get("market_mean") is not None
             and h1["ananta_mean"] > rnd["median"] and h1["ananta_mean"] > h1["market_mean"])
    cov = h1.get("coverage") or {}
    words = (f"Of the day's 20 best one-day trades, Ananta held {cov.get('TAKEN', 0)}, passed on {cov.get('PASSED', 0)} and had no rule for {cov.get('NOT_COVERED', 0)}. "
             f"Its {h1.get('ananta_n')} positions did {_pct(h1.get('ananta_mean'))} against {_pct(h1.get('market_mean'))} for the average stock "
             f"(better than {round(100 * (h1.get('ananta_pct_vs_random') or 0))}% of random picks); the best possible was {_pct(h1.get('hindsight_mean'))}.")
    return {"status": "ok", "source": str(src), "h1": {k: h1.get(k) for k in ("hindsight_mean", "market_mean", "ananta_mean", "ananta_n", "ananta_pct_vs_random", "coverage")}, "random_median": rnd.get("median"),
            "beats_random_and_market": bool(beats), "best": best, "not_covered_situations": {k: v.get("situation") for k, v in (o.get("not_covered") or {}).items()}, "words": words}


def section_people(day: str, names: dict, movers: set) -> dict:
    out = {"deals": _deals(day, names), "fii_dii": _fiidii(day), "participant_oi": _participant_oi(day), "announcements": _announcements(day, names, movers),
           "events": _events(day), "league": _league(day),
           "rule": "yardstick and event generator only: nothing here is a teacher or a copy signal (D8); every item is stamped at its public time"}
    out["status"] = "ok" if any((v or {}).get("status") == "ok" for k, v in out.items() if isinstance(v, dict)) else "missing"
    bits = []
    if out["fii_dii"].get("status") == "ok":
        bits.append(out["fii_dii"]["words"])
    dl = out["deals"]
    n = sum((dl.get(k) or {}).get("in_universe", 0) for k in ("bulk", "block"))
    if dl.get("status") == "ok":
        bits.append(f"{n} bulk/block deals in our universe" + (f" (largest: {dl['bulk']['top'][0]['client']} {dl['bulk']['top'][0]['side']} {dl['bulk']['top'][0]['symbol']} ₹{dl['bulk']['top'][0]['value_inr'] / 1e7:.1f} crore)" if (dl.get("bulk") or {}).get("top") else ""))
    an = out["announcements"]
    if an.get("status") == "ok":
        bits.append(f"{an['universe_rows']} announcements on universe names, {len(an['on_movers'])} on today's movers")
    out["words"] = "; ".join(bits) + "." if bits else "no public record of the session reached the lake yet (deals, flows and announcements are captured by the evening job)."
    return out


# ------------------------------------------------------------------------------------------------------------------------------- C: what Ananta did

def section_ananta(day: str, rm: dict, st: dict, sess: list[str]) -> dict:
    src = _paper() / "decisions" / f"{day}.json"
    d = _load(src, {}) or {}
    journal = d.get("journal") or []
    chosen = [c for c in journal if c.get("status") == "chosen"]
    rejected = [c for c in journal if c.get("status") == "rejected"]
    by_reason = Counter(f"{c.get('campaign')}:{c.get('reason')}" for c in rejected)
    trades = (st.get("trades") or {}).values()
    fills = sorted({(t["symbol"], t["campaign"], t["signal_date"]) for t in trades if t.get("book") == "exec" and t.get("entry_date") == day and t.get("policy") == REF_POLICY})
    exits = [{"symbol": t["symbol"], "campaign": t["campaign"], "reason": t.get("exit_reason"), "net_inr": _r(t.get("net_inr"), 0), "net_ret": _r(t.get("net_ret"))}
             for t in trades if t.get("book") == "exec" and t.get("exit_date") == day and t.get("policy") == REF_POLICY]
    calls = [c for c in _jsonl(_paper() / "calls.jsonl") if c.get("kind") == "call" and c.get("data_through") == day]
    scores = [c for c in _jsonl(_paper() / "calls.jsonl") if c.get("kind") == "score" and c.get("data_through") == day]
    sp1 = [x for x in _jsonl(_paper() / "sp1" / "decisions.jsonl") if str(x.get("date")) == day]
    fc = [x for x in _jsonl(_paper() / "forecasts.jsonl") if x.get("kind") == "score" and str(x.get("scored_at", ""))[:10] >= day][-3:]
    alloc = [x for x in _jsonl(_paper() / "allocation_ledger.jsonl") if x.get("day") == day]
    a = alloc[-1] if alloc else {}
    words = (f"Chose {len([c for c in chosen if c.get('campaign') != 'CTL'])} research signals and {len([c for c in chosen if c.get('campaign') == 'CTL'])} random controls from {len(journal)} candidates; "
             f"{len(rejected)} rejected (most often: {', '.join(k.replace(':', ' ') + ' x' + str(v) for k, v in by_reason.most_common(2))}); "
             f"{len(fills)} fills, {len(exits)} exits at the reference exit; "
             + (f"called the next session {calls[-1]['call']}; " if calls else "no call written; ")
             + (f"index line: {len([x for x in sp1 if x.get('kind') != 'error'])} decisions, {len([x for x in sp1 if x.get('kind') == 'error'])} error; " if sp1 else "index line: nothing recorded; ")
             + (f"allocation ({a.get('mode')}): {len(a.get('moves') or [])} paper move(s)." if a else "allocation: no row."))
    return {"status": "ok" if d else "missing", "source": str(src),
            "chosen": [{"symbol": c.get("symbol"), "campaign": c.get("campaign"), "close": c.get("close"), "liq_rank": c.get("liq_rank")} for c in chosen],
            "rejected_by_reason": dict(by_reason.most_common(12)), "fills": [{"symbol": s, "campaign": c, "signal_date": sd} for s, c, sd in fills], "exits": exits,
            "call": {k: calls[-1].get(k) for k in ("call", "null_call", "rule")} if calls else None, "call_scored": [{k: s.get(k) for k in ("horizon", "move", "score", "null_score")} for s in scores],
            "index_line": sp1[-3:], "forecast_scores": [{k: f.get(k) for k in ("ref", "outcome", "hit", "brier", "brier_coin_flip")} for f in fc],
            "allocation": {k: a.get(k) for k in ("mode", "sleeves_now", "sleeves_after", "moves", "regime")} if a else None, "words": words}


# ------------------------------------------------------------------------------------------------------------------------------- D: what it did not do

def section_not_done(day: str, rm: dict) -> dict:
    man_src = _data() / "manifests" / f"missed_{day}.json"
    man = _load(man_src, {}) or {}
    movers = man.get("movers") or []
    s = man.get("summary") or {}
    # the counterfactual: every research candidate rejected on `day` is followed by the baseline book under the reference exit
    cf_src = _paper() / "baseline.parquet"
    cf = {"status": "missing", "source": str(cf_src)}
    try:
        import pandas as pd
        b = pd.read_parquet(cf_src, columns=["campaign", "symbol", "policy", "signal_date", "journal_status", "journal_reason", "status", "unrealised_ret", "net_ret", "bars_seen"])
        b = b[(b["policy"] == REF_POLICY) & (b["signal_date"] == day) & (b["journal_status"] == "rejected") & (b["campaign"].isin(RESEARCH))]
        if len(b):
            b = b.copy()
            b["ret"] = b["net_ret"].where(b["status"] == "closed", b["unrealised_ret"])
            right = int((b["ret"] <= 0).sum())
            wrong = int((b["ret"] > 0.02).sum())
            top = b.sort_values("ret", ascending=False).head(5)
            cf = {"status": "ok", "source": str(cf_src), "rejected_followed": int(len(b)), "so_far_not_missed": right, "so_far_would_have_paid_2pct": wrong,
                  "best_passes": [{"symbol": r.symbol, "campaign": r.campaign, "reason": r.journal_reason, "ret_so_far": _r(r.ret), "sessions": int(r.bars_seen or 0)} for r in top.itertuples()],
                  "label": "hindsight: the baseline book's path after a rejection; it generates a question, never a verdict"}
        else:
            cf = {"status": "ok", "source": str(cf_src), "rejected_followed": 0, "note": "no rejected research candidate on this day"}
    except Exception as e:  # noqa: BLE001
        cf["note"] = f"{e.__class__.__name__}: {str(e)[:80]}"
    held = [m for m in movers if m.get("status") == "held_into_fall"]
    held_by_family = Counter(g.get("campaign") for m in held for g in (m.get("held") or []) if isinstance(g, dict))
    up, down = s.get("up") or {}, s.get("down") or {}
    words = (f"Of the top {up.get('movers', 0)} rises the book held {up.get('caught', 0)} (plus {up.get('caught_by_control', 0)} by the random control), "
             f"missed {up.get('a', 0)} after a family fired (class a), {up.get('b', 0)} with no family positioned (b), {up.get('c', 0)} untradeable (c); "
             f"it held into {down.get('held_into_fall', 0)} of the top {down.get('movers', 0)} falls (₹{abs(down.get('held_pnl_so_far_inr') or 0):,.0f} against it so far). "
             + (f"Of {cf['rejected_followed']} research candidates it rejected, {cf['so_far_not_missed']} have not run away and {cf['so_far_would_have_paid_2pct']} are up 2%+ (hindsight)." if cf.get("status") == "ok" and cf.get("rejected_followed") else ""))
    return {"status": "ok" if man else "missing", "source": str(man_src), "summary": s, "b_situations": s.get("b_situations") or {},
            "held_into_fall": [{"symbol": m["symbol"], "cc": _r(m.get("cc")), "families": sorted({g.get("campaign") for g in (m.get("held") or []) if isinstance(g, dict)})} for m in held][:10],
            "held_into_fall_by_family": dict(held_by_family), "counterfactual": cf, "words": words}


# ------------------------------------------------------------------------------------------------------------------------------- E: trade reviews

def _risk(t: dict) -> float:
    e = float(t.get("entry_adj") or 0)
    rf = float(t.get("risk_frac") or 0)
    low = float(t.get("bar_low_raw") or 0)
    r = e * rf if rf > 0 else (e - low if 0 < low < e else e * 0.02)
    return max(r, e * 0.005)


def reviews(day: str, st: dict, sess: list[str]) -> dict:
    """Tag every reference-exit trade closed REVIEW_WAIT sessions before `day`. After-exit path = the close on `day` of the longest-lived sibling
    (same signal, family and stock, another exit policy, in the same book) that is still marked; the row says how many sessions after the exit it looked."""
    if day not in sess or sess.index(day) < REVIEW_WAIT:
        return {"status": "missing", "source": str(_paper() / "state.json"), "note": f"fewer than {REVIEW_WAIT} sessions on record after an exit"}
    target = sess[sess.index(day) - REVIEW_WAIT]
    trades = [t for t in (st.get("trades") or {}).values() if t.get("book") == "exec"]
    by_key = defaultdict(list)
    for t in trades:
        by_key[(t["signal_date"], t["campaign"], t["sid"])].append(t)
    out = []
    for t in trades:
        if t.get("policy") != REF_POLICY or t.get("status") != "closed" or t.get("exit_date") != target:
            continue
        e, x, peak = float(t["entry_adj"]), float(t.get("exit_adj") or t["entry_adj"]), float(t.get("peak_adj") or t["entry_adj"])
        R = _risk(t)
        sib = [s for s in by_key[(t["signal_date"], t["campaign"], t["sid"])] if s is not t and s.get("last_date") and str(s["last_date"]) > str(target)]
        sib.sort(key=lambda s: (str(s.get("last_date")), s.get("bars_seen") or 0), reverse=True)
        after = float(sib[0]["last_close_adj"]) if sib else None
        after_sessions = (sess.index(str(sib[0]["last_date"])) - sess.index(target)) if sib and str(sib[0]["last_date"]) in sess else None
        gross = abs(x - e) * (50000.0 / e)
        cost = float(t.get("cost_inr") or 0)
        win = x > e
        reason = str(t.get("exit_reason") or "")
        if reason.startswith("stop") and after is not None and after >= e + R:
            tag = "STOPPED_THEN_RAN"
        elif peak >= e + 1.5 * R and x <= e:
            tag = "GAVE_BACK"
        elif peak < e + 0.25 * R:
            tag = "NEVER_WORKED"
        elif win and after is not None and after >= x + R:
            tag = "LEFT_ON_TABLE"
        elif gross < cost:
            tag = "COSTS_ATE"
        elif win and (x - e) >= 0.5 * (peak - e):
            tag = "CLEAN"
        elif not win and (e - x) < R:
            tag = "LOST_SMALL"
        else:
            tag = "GAVE_BACK" if peak > e and not win else ("CLEAN" if win else "LOST_SMALL")
        out.append({"id": t["id"], "symbol": t["symbol"], "campaign": t["campaign"], "signal_date": t["signal_date"], "exit_date": target, "reason": reason, "entry": e, "exit": x, "peak": peak,
                    "R": round(R, 2), "net_inr": _r(t.get("net_inr"), 0), "net_ret": _r(t.get("net_ret")), "after_close": after, "after_sessions": after_sessions, "after_policy": sib[0]["policy"] if sib else None,
                    "tag": tag, "words": f"{t['symbol']} ({FAMILY_WORDS.get(t['campaign'], t['campaign'])}): exit {reason}, {_pct(t.get('net_ret'))} net; {TAG_WORDS[tag]}"})
    tags = Counter(r["tag"] for r in out)
    return {"status": "ok", "source": str(_paper() / "state.json"), "reviewed_exit_date": target, "sessions_after": REVIEW_WAIT, "count": len(out), "tags": dict(tags), "trades": out,
            "rule": "R = the trade's own risk unit (entry x risk_frac, else entry minus the signal bar's low); tags fixed 23 Oct 2026 before any trade was tagged; the after-exit path is the sibling policy's close, not a new price read"}


# ------------------------------------------------------------------------------------------------------------------------------- F: findings

def _recent_cards(day: str, n: int) -> list[dict]:
    out = []
    for p in sorted(_rx().glob("????-??-??.json")):
        if p.stem < day:
            out.append(_load(p, {}) or {})
    return out[-n:]


def findings(day: str, card: dict, prior: list[dict], queue_rows: list[dict], fwd: list[dict], rm: dict, sess: list[str]) -> list[dict]:
    out: list[dict] = []
    open_keys = {q["key"] for q in queue_rows if q.get("state") in ("DRAFT", "NOTE", "to_file", "filed", "APPROVED", "SKIPPED", "REGISTERED", "TESTED", "SHADOW")}
    recent_safe = {f["key"] for f in fwd if f.get("day") in sess and day in sess and sess.index(day) - sess.index(f["day"]) < BARS["safe_refile_sessions"]}

    def add(kind, key, words, lane, evidence, state=None, extra=None):
        if key in open_keys or key in recent_safe:
            return
        out.append({"type": kind, "key": key, "words": words, "lane": lane, "evidence": evidence, "state": state or ("to_file" if lane == "SAFE" else "DRAFT"), "day": day, **(extra or {})})

    # SAFE: data gaps, jobs, sign-in
    people = card["people"]
    for name in ("deals", "fii_dii", "announcements"):
        sec = people.get(name) or {}
        if sec.get("status") != "ok":
            what = {"deals": "big single-client trades (bulk and block deals)", "fii_dii": "foreign and domestic institutions' buying and selling",
                    "announcements": "company announcements"}.get(name, name)
            add("DATA_GAP", f"DATA_GAP:{name}", f"The {what} for {day} did not reach Ananta, so the nightly review could not say what happened there. The download needs checking.", "SAFE",
                {"source": sec.get("source"), "note": sec.get("note"), "sessions_missing": 1})
    jobs = (rm.get("jobs") or {}).get("jobs") or []
    signin_jobs = []
    for j in jobs:
        if j.get("ok"):
            continue
        text = "; ".join(j.get("problems") or [])
        if any(w in text.lower() for w in ("token", "sign-in", "kite", "depth snapshots", "recorder")) or j.get("label") in ("autologin", "evening"):
            signin_jobs.append(j.get("label"))                                              # one root cause, one row: the sign-in
            continue
        add("JOB_FAIL", f"JOB_FAIL:{j.get('label')}", f"One of Ananta's India jobs ('{j.get('label')}') did not finish properly. It needs checking.", "SAFE", {"job": j, "problem": text[:300]})
    if (rm.get("sp1") or {}).get("status") == "lost" or signin_jobs:
        add("SIGNIN_LOST", "SIGNIN_LOST:kite", f"The morning sign-in to Zerodha was missing for {day}, so the options line could not trade and {len(signin_jobs) or 1} job{'s' if len(signin_jobs) != 1 else ''} had nothing to work with. "
            "The automatic sign-in key (the Zerodha ticket) fixes this for good; until then, a manual sign-in the evening before.", "SAFE",
            {"source": (rm.get("sp1") or {}).get("source"), "jobs": signin_jobs, "error": ((rm.get("sp1") or {}).get("errors") or [""])[0][:200]})

    snapd = paths.data_dir() / "bronze" / "ledger"
    snaps = sorted(snapd.glob("*.json")) if snapd.exists() else []
    upto = [x for x in sess if x <= day]
    if not snaps or (len(upto) >= BARS["data_stale_sessions"] and snaps[-1].stem < upto[-BARS["data_stale_sessions"]]):
        add("DATA_GAP", "DATA_GAP:ledger_snapshot", f"Your account's daily snapshot from Zerodha is more than {BARS['data_stale_sessions']} sessions old (newest: {snaps[-1].stem if snaps else 'none'}), "
            "so Ananta is grading old holdings. It refreshes once the Zerodha sign-in works.", "SAFE", {"newest": snaps[-1].stem if snaps else None})
    for name, sec in card.items():
        if isinstance(sec, dict) and sec.get("status") == "error":
            add("WORDS", f"WORDS:{name}", f"One part of the nightly review ('{name}') failed to build, so it shows as missing instead of guessing. It needs a code fix.", "SAFE", {"section": name, "error": sec.get("error")})

    # DECISION: the index line's direction (5 sessions of 10 recorded with a traded point that went the wrong way)
    outs = _jsonl(_paper() / "sp1" / "outcomes.jsonl")
    by_day: dict[str, bool] = {}
    for o in outs:
        if o.get("kind") == "outcome" and int(o.get("action") or 0) != 0:
            bad = float(((o.get("index_proxy") or {}).get("net_bps")) or 0) < 0
            by_day[o["date"]] = by_day.get(o["date"], False) or bad
    last = sorted(by_day)[-BARS["options_window"]:]
    wrong_days = [d for d in last if by_day[d]]
    if len(last) >= BARS["options_window"] and len(wrong_days) >= BARS["options_n"]:
        add("OPTIONS_LINE", "OPTIONS_LINE:SP1", f"The index line traded the wrong way on {len(wrong_days)} of its last {len(last)} recorded sessions. Question for the SP1 playbook (pinned): which decision point misfires, "
            "and does the frozen model still beat its own no-trade baseline?", "DECISION", {"wrong_days": wrong_days, "sessions": len(last)})

    # NOTE -> DRAFT: registered events; the third note of one kind becomes a draft
    ev = ((card.get("people") or {}).get("events") or {}).get("recent") or []
    for e in ev:
        if e.get("first_session") == day:
            cat = e.get("category")
            add("EVENT_NOTE", f"EVENT_NOTE:{cat}:{day}", f"Registered event on {day}: {e.get('title')} ({cat}). Noted; its reaction is compared with the response table when the holdout run is allowed.", "DECISION",
                {"event": e}, state="NOTE")
            n = sum(1 for q in queue_rows if str(q.get("key", "")).startswith(f"EVENT_NOTE:{cat}:")) + 1
            if n >= BARS["event_notes_to_draft"]:
                add("EVENT_SURPRISE", f"EVENT_SURPRISE:{cat}", f"{n} registered '{cat}' events on live sessions so far. Question for a registered study: how does the market respond to this kind of event, "
                    "measured on 2000-2023 from the response table, and does it change what Ananta should hold the day after?", "DECISION", {"notes": n})

    # DECISION: miss patterns (the missed-movers rule, counted over the last 7 cards) and league gaps
    win = (prior + [card])[-BARS["pattern_window"]:]
    seen_b: dict[str, list[str]] = defaultdict(list)
    seen_league: dict[str, list[str]] = defaultdict(list)
    for c in win:
        for k in ((c.get("not_done") or {}).get("b_situations") or {}):
            seen_b[k].append(c.get("day"))
        for k in (((c.get("people") or {}).get("league") or {}).get("not_covered_situations") or {}):
            seen_league[k].append(c.get("day"))
    for k, days in seen_b.items():
        if len(days) >= BARS["pattern_days"]:
            ex = ((card.get("not_done") or {}).get("b_situations") or {}).get(k) or []
            add("MISS_PATTERN", f"MISS_PATTERN:{k}", f"No family was positioned for '{k.split(':', 1)[1].replace(':', ', ').replace('_', ' ')}' on {len(days)} of the last {len(win)} sessions (e.g. {', '.join(ex[:4])}). "
                "Question for a registered study: is there an entry rule, known before the move, for this situation? Development and validation years only.", "DECISION",
                {"days": days, "examples": ex[:8], "rule": f"{BARS['pattern_days']} of {BARS['pattern_window']} sessions"})
    for k, days in seen_league.items():
        if len(days) >= BARS["pattern_days"]:
            add("LEAGUE_GAP", f"LEAGUE_GAP:{k}", f"The reference traders' best trips were '{(((card.get('people') or {}).get('league') or {}).get('not_covered_situations') or {}).get(k, k)}' with no Ananta rule on {len(days)} of {len(win)} sessions. "
                "Question for a registered study: which rule, if any, would have been positioned, and would it have beaten RANDOM at our costs?", "DECISION", {"days": days})

    # DECISION: exit lessons (one tag on 5+ closed trades of one family within 20 sessions)
    tags: Counter = Counter()
    for c in (prior + [card])[-BARS["exit_lesson_window"]:]:
        for t in ((c.get("reviews") or {}).get("trades") or []):
            if t.get("tag") not in ("CLEAN", "LOST_SMALL"):
                tags[(t["campaign"], t["tag"])] += 1
    for (fam, tag), n in tags.items():
        if n >= BARS["exit_lesson_n"]:
            add("EXIT_LESSON", f"EXIT_LESSON:{fam}:{tag}", f"{n} closed {FAMILY_WORDS.get(fam, fam)} trades in the last {BARS['exit_lesson_window']} sessions were tagged {tag}: {TAG_WORDS[tag]}. "
                f"Question for the G01 exit book cell {fam}: does the registered exit that fixes this hold up on the development and validation years?", "DECISION", {"count": n, "family": fam, "tag": tag})

    # DECISION: held into falls
    hf: Counter = Counter()
    for c in (prior + [card])[-BARS["held_window"]:]:
        nd = c.get("not_done") or {}
        if len(nd.get("held_into_fall") or []) >= BARS["held_into_fall_n"]:
            for fam in (nd.get("held_into_fall_by_family") or {}):
                hf[fam] += 1
    for fam, days in hf.items():
        if days >= BARS["held_days"]:
            add("HELD_INTO_FALL", f"HELD_INTO_FALL:{fam}", f"The {FAMILY_WORDS.get(fam, fam)} family held into {BARS['held_into_fall_n']}+ of the session's top-20 falls on {days} of the last {BARS['held_window']} sessions. "
                "Question for the exit book: is a faster exit for this family justified out of sample, or is this the cost of holding?", "DECISION", {"days": days, "family": fam})

    # DECISION: the daily call below the coin flip over 20 scored sessions
    sc = [c for c in _jsonl(_paper() / "calls.jsonl") if c.get("kind") == "score"][-BARS["call_window"]:]
    if len(sc) >= BARS["call_window"]:
        hits = sum(1 for c in sc if (c.get("score") or 0) > 0)
        if hits < len(sc) / 2:
            add("CALL_DRIFT", "CALL_DRIFT:K02", f"The daily call was right {hits} of its last {len(sc)} scored sessions, below the coin flip. The K02 study decides whether the rule stays.", "DECISION", {"hits": hits, "n": len(sc)})

    # DECISION: allocation moves scored at +5 sessions (the stock sleeve is the only sleeve that moves on its own; options and cash hold)
    led = _jsonl(_paper() / "allocation_ledger.jsonl")
    wrong, scored = 0, 0
    for row in led[-BARS["alloc_window"]:]:
        d0 = row.get("day")
        if not d0 or d0 not in sess or day not in sess or sess.index(day) - sess.index(d0) < BARS["alloc_horizon"] or not row.get("moves"):
            continue
        k = sess.index(d0) + BARS["alloc_horizon"]
        later = [x for x in led if x.get("day") == sess[k]] if k < len(sess) else []
        if not later:
            continue
        scored += 1
        for m in row["moves"]:
            if m.get("from") == "stocks" and (later[-1].get("sleeves_now", {}).get("stocks", 0) - (row.get("sleeves_after") or {}).get("stocks", 0)) > m.get("inr", 0):
                wrong += 1
    if wrong >= BARS["alloc_wrong_n"]:
        add("ALLOC_WRONG", "ALLOC_WRONG:regime_table", f"{wrong} allocation moves of the last {scored} scored were wrong at +{BARS['alloc_horizon']} sessions. Question for the regime table (allocation_rule_v1, pinned): which row misfired?", "DECISION", {"wrong": wrong, "scored": scored})

    return out


# ------------------------------------------------------------------------------------------------------------------------------- queue, staircase

def queue() -> list[dict]:
    """Every queue row, with Madhav's latest decision folded in (paper/reconstruction/decisions.jsonl, written by the India service when he says
    yes or skip in the app or by voice): APPROVED = register a study for it; SKIPPED = closed, not refiled."""
    rows = _jsonl(QUEUE)
    dec = {}
    for d in _jsonl(_rx() / "decisions.jsonl"):
        dec[d.get("key")] = d
    for r in rows:
        d = dec.get(r.get("key"))
        if d and r.get("lane") == "DECISION":
            r["state"] = d.get("decision")
            r["decided_at"], r["decided_words"] = d.get("at"), d.get("words")
    return rows


def forwarded() -> list[dict]:
    return _jsonl(_rx() / "forwarded.jsonl")


def write_queue(rows: list[dict]) -> list[dict]:
    written = []
    for r in rows:
        row = {**r, "written_at": _now(), "rules": RULES}
        _append(QUEUE, row)
        written.append(row)
    return written


def staircase(sess: list[str] | None = None) -> dict:
    """Where every rule stands on the stairs, from the files: shadow sessions per family, the league's independent sessions beating RANDOM and
    MARKET, and the ADMITTED list (empty until Madhav's recorded yes)."""
    sess = sess or sessions()
    st = _load(_paper() / "state.json", {}) or {}
    fam_days: dict[str, set] = defaultdict(set)
    for t in (st.get("trades") or {}).values():
        if t.get("book") == "exec" and t.get("policy") == REF_POLICY:
            fam_days[t["campaign"]].add(t["signal_date"])
    beats = 0
    for p in sorted((_data() / "manifests").glob("others_????-??-??.json")):
        o = _load(p, {}) or {}
        h1 = (o.get("by_h") or {}).get("1") or {}
        rnd = h1.get("random") or {}
        if h1.get("ananta_mean") is not None and rnd.get("median") is not None and h1.get("market_mean") is not None and h1["ananta_mean"] > rnd["median"] and h1["ananta_mean"] > h1["market_mean"]:
            beats += 1
    sp1 = _load(_paper() / "sp1" / "book.json", {}) or {}
    prev = _load(STAIRS_FILE, {}) or {}
    adm = prev.get("admitted") or []
    rules = {}
    for fam in RESEARCH:
        n = len(fam_days.get(fam, set()))
        rules[f"stock:{fam}"] = {"what": FAMILY_WORDS[fam], "step": "ADMITTED" if f"stock:{fam}" in adm else ("SHADOW" if n else "TESTED"), "shadow_sessions": n, "shadow_bar": STAIRS["shadow_sessions"],
                                 "independent_sessions_beating_random_and_market": beats, "independent_bar": STAIRS["admitted_independent_sessions"], "registered": "paper-v1 (16 Oct 2026); exits G01 v2"}
    rules["options:SP1"] = {"what": "the index playbook's 1-lot option line", "step": "ADMITTED" if "options:SP1" in adm else "SHADOW", "shadow_sessions": sp1.get("sessions") or 0, "shadow_bar": STAIRS["shadow_sessions"],
                            "independent_sessions_beating_random_and_market": 0, "independent_bar": STAIRS["admitted_independent_sessions"], "registered": "sp1_v2 (21 Oct 2026), pinned"}
    counts = Counter(r.get("state") for r in queue())
    out = {**STAIRS, "built_at": _now(), "rules": rules, "admitted": adm, "queue": dict(counts), "history": prev.get("history") or [],
           "words": (f"No rule has proved itself yet. The stock rules have {max((len(v) for v in fam_days.values()), default=0)} of {STAIRS['shadow_sessions']} trial sessions; "
                     f"the options line has {sp1.get('sessions') or 0}; Ananta beat chance and the average stock on {beats} of the {STAIRS['admitted_independent_sessions']} days needed."
                     if not adm else "Proved and allowed to use your money: " + ", ".join(adm) + ".")}
    STAIRS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAIRS_FILE.write_text(json.dumps(out, indent=1))
    return out


def admitted() -> set[str]:
    """The rules the allocated paper capital may size: stock families as 'stock:BRK' etc. Empty until Madhav's recorded yes in the staircase file."""
    s = _load(STAIRS_FILE, {}) or {}
    return set(s.get("admitted") or [])


# ------------------------------------------------------------------------------------------------------------------------------- the evening run

def build(day: str | None = None) -> dict:
    rm = _load(_data() / "readmodel" / "latest.json", {}) or {}
    sess = sessions()
    day = day or rm.get("data_through") or (sess[-1] if sess else dt.date.today().isoformat())
    st = _load(_paper() / "state.json", {}) or {}
    names = _names()
    try:
        market = section_market(day, rm)
    except Exception as e:  # noqa: BLE001
        market = {"status": "error", "error": f"{e.__class__.__name__}: {str(e)[:140]}"}
    movers = {m["symbol"] for m in (market.get("movers_up") or []) + (market.get("movers_down") or [])}
    def safe(fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001 - a section that cannot build says so; the rest of the card still builds
            return {"status": "error", "error": f"{e.__class__.__name__}: {str(e)[:140]}"}

    card = {"rules": RULES, "day": day, "built_at": _now(), "sessions_on_record": len(sess),
            "market": market, "people": safe(section_people, day, names, movers), "ananta": safe(section_ananta, day, rm, st, sess),
            "not_done": safe(section_not_done, day, rm), "reviews": safe(reviews, day, st, sess)}
    prior = _recent_cards(day, BARS["exit_lesson_window"])
    card["findings"] = findings(day, card, prior, queue(), forwarded(), rm, sess)
    inputs = {"decision": str(_paper() / "decisions" / f"{day}.json"), "missed": str(_data() / "manifests" / f"missed_{day}.json"), "others": str(_data() / "manifests" / f"others_{day}.json"), "state": str(_paper() / "state.json")}
    card["inputs_sha"] = {k: (hashlib.sha256(Path(v).read_bytes()).hexdigest()[:16] if Path(v).exists() else None) for k, v in inputs.items()}
    card["headline"] = _headline(card)
    return card


def _headline(c: dict) -> str:
    """The night in three plain sentences (the Reconstruction screen and the voice read this first; the sections hold the detail)."""
    f = c.get("findings") or []
    safe = sum(1 for x in f if x["lane"] == "SAFE")
    dec = sum(1 for x in f if x["lane"] == "DECISION" and x.get("state") == "DRAFT")
    mk, an, nd, rv = c.get("market") or {}, c.get("ananta") or {}, c.get("not_done") or {}, c.get("reviews") or {}
    try:
        d = dt.date.fromisoformat(c["day"]).strftime("%-d %b")
    except (KeyError, ValueError):
        d = c.get("day", "")
    trend = {"above_both": "in an uptrend", "below_both": "in a downtrend", "mixed": "with no clear trend"}.get(mk.get("trend_state"), "")
    picked = len([x for x in (an.get("chosen") or []) if x.get("campaign") != "CTL"])
    up, down = ((nd.get("summary") or {}).get("up") or {}), ((nd.get("summary") or {}).get("down") or {})
    parts = [f"{d}: Nifty {trend}." if trend else f"{d}."]
    if up or down:
        parts.append(f"Ananta picked {picked} stocks; of the day's {up.get('movers', 0)} biggest rises it held {up.get('caught', 0)} and missed {up.get('b', 0)} that no rule was watching, "
                     f"and it held {down.get('held_into_fall', 0)} of the {down.get('movers', 0)} biggest falls.")
    if rv.get("count"):
        tags = ", ".join(f"{v} {k.lower().replace('_', ' ')}" for k, v in (rv.get("tags") or {}).items())
        parts.append(f"{rv['count']} closed trade{'s' if rv['count'] != 1 else ''} reviewed ({tags}).")
    parts.append((f"{safe} small fix{'es' if safe != 1 else ''} went to the repair shop" if safe else "Nothing went to the repair shop")
                 + (f"; {dec} idea{'s' if dec != 1 else ''} wait{'s' if dec == 1 else ''} for your yes." if dec else "; nothing waits for you."))
    return " ".join(parts)


def evening(day: str | None = None) -> dict:
    card = build(day)
    new = write_queue(card["findings"])
    old = _load(_rx() / f"{card['day']}.json", {}) or {}
    if old.get("findings"):                      # a re-run of the same session keeps what the first run found (the queue already holds those keys)
        keys = {f["key"] for f in card["findings"]}
        card["findings"] = [f for f in old["findings"] if f["key"] not in keys] + card["findings"]
        card["reruns"] = (old.get("reruns") or 0) + 1
        card["headline"] = _headline(card)
    card["forwarding"] = {"queued": [{"key": r["key"], "lane": r["lane"], "state": r["state"]} for r in new],
                          "to_repair_board": [r["key"] for r in new if r["lane"] == "SAFE"][:BARS["safe_per_night"]],
                          "note": "Small fixes go to the repair shop by themselves within the hour; ideas that touch trading wait for your yes."}
    p = _rx() / f"{card['day']}.json"
    p.write_text(json.dumps(card, indent=1, default=str))
    (_rx() / "latest.json").write_text(json.dumps(card, indent=1, default=str))
    st = staircase()
    page()
    _append(_data() / "manifests" / "evidence_log.jsonl", {"date": card["day"], "check": "RX.card", "ok": all((card.get(k) or {}).get("status") != "error" for k in ("market", "people", "ananta", "not_done", "reviews")),
                                                           "metrics": {"findings": len(card["findings"]), "safe": sum(1 for f in card["findings"] if f["lane"] == "SAFE"),
                                                                       "decision": sum(1 for f in card["findings"] if f["lane"] == "DECISION"), "reviews": (card.get("reviews") or {}).get("count", 0),
                                                                       "tags": (card.get("reviews") or {}).get("tags") or {}, "admitted": st.get("admitted") or [], "rules": RULES}})
    return card


# ------------------------------------------------------------------------------------------------------------------------------- the page

def page() -> str:
    c = _load(_rx() / "latest.json", {}) or {}
    if not c:
        return ""
    s = staircase()
    L = [f"# Reconstruction, session {c['day']} (rules {c['rules']}, built {c['built_at'][:16]}Z)", "", c["headline"], "", "## A. The market", (c["market"] or {}).get("words", "missing")]
    for side in ("movers_up", "movers_down"):
        rows = (c["market"] or {}).get(side) or []
        if rows:
            L.append(f"- {side.replace('movers_', '').capitalize()}: " + "; ".join(f"{r['symbol']} {_pct(r['cc'])} ({r.get('status')}{', class ' + r['class'] if r.get('class') else ''})" for r in rows[:6]))
    L += ["", "## B. What people did (public records, stamped at their public time; yardstick only)", (c["people"] or {}).get("words", "missing")]
    lg = (c["people"] or {}).get("league") or {}
    if lg.get("words"):
        L.append("- League: " + lg["words"])
    for k in ("deals", "fii_dii", "participant_oi", "announcements", "events"):
        sec = (c["people"] or {}).get(k) or {}
        if sec.get("status") != "ok":
            L.append(f"- {k}: missing ({sec.get('note') or sec.get('source', '')})")
    notes = _jsonl(_rx() / "netnotes" / f"{c['day']}.jsonl")
    if notes:
        L.append("- Notes from the web (public pages, notes only, never a reason to trade):")
        for n in notes[:8]:
            L.append(f"  - {n.get('symbol')}: {n.get('note')} [{n.get('grade')}] {', '.join(n.get('urls') or [])[:200]}")
    L += ["", "## C. What Ananta did", (c["ananta"] or {}).get("words", "missing"), "", "## D. What it did not do, and was that right", (c["not_done"] or {}).get("words", "missing")]
    cf = (c["not_done"] or {}).get("counterfactual") or {}
    for r in (cf.get("best_passes") or [])[:3]:
        L.append(f"- passed {r['symbol']} ({r['campaign']}, {r['reason']}): {_pct(r['ret_so_far'])} after {r['sessions']} sessions (hindsight)")
    rv = c.get("reviews") or {}
    L += ["", f"## E. Trade reviews ({rv.get('count', 0)} trades closed {rv.get('sessions_after', REVIEW_WAIT)} sessions ago, exit day {rv.get('reviewed_exit_date', '?')})"]
    for t in (rv.get("trades") or [])[:12]:
        L.append(f"- {t['tag']}: {t['words']}")
    L += ["", "## F. Findings"]
    for f in c.get("findings") or []:
        L.append(f"- [{f['lane']} · {f['type']} · {f['state']}] {f['words']}")
    if not c.get("findings"):
        L.append("- none tonight")
    L += ["", "## G. The staircase", s.get("words", "")]
    for k, r in (s.get("rules") or {}).items():
        L.append(f"- {k}: {r['step']} · shadow {r['shadow_sessions']}/{r['shadow_bar']} sessions · beats RANDOM and MARKET on {r['independent_sessions_beating_random_and_market']}/{r['independent_bar']} independent sessions")
    L.append(f"- queue: {dict(Counter(x.get('state') for x in queue()))}")
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text("\n".join(L) + "\n")
    return PAGE.read_text()


def show() -> None:
    print(page() or "no card yet: run `python -m india.reconstruct evening`")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "evening":
        c = evening(sys.argv[2] if len(sys.argv) > 2 else None)
        print(c["headline"])
    elif cmd == "stairs":
        print(json.dumps(staircase(), indent=1))
    else:
        show()
