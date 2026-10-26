"""The morning view (Madhav, 23 Oct 2026, 20:23 Toronto): before every Indian open, a clean view of the day — what happened overnight, what the
market looks like, what Ananta is doing today, our chances said honestly, what to watch — and a scorecard of yesterday's predictions against what
happened, so the next view knows what to change.

  python -m india.morningview build [YYYY-MM-DD]   the facts and the plain lines for the next session -> paper/morningview/<session>.json (+ latest.json)
  python -m india.morningview show

Madhav: "See what's good in the day to trade, what are the possibilities, positives, analyse their chances ... give me a clean market view for the day
and our chances ... so Ananta can help me by already loading in the start of the morning. It stays alert too that way." And: "verify your review with
Ananta review and predictions ... compare its predictions, reviews with performance and notify it what to change for the next session."

Three layers, kept apart so each can be judged:
  1. FACTS (this module, by rule, no model): every number names its file; a missing source says missing.
  2. WORDS (scripts/india_morningview.py, agent side): a trader's morning note written from the facts by the model, then checked by a second, separate
     reviewer call that corrects it against the facts and writes its own scenario odds to the forecast ledger as "reviewer" - a prediction with a
     deadline, scored the same way as Ananta's rule forecast, so the two can be compared on the record.
  3. SCORECARD (here, from the ledgers): yesterday's forecast against the close, the reviewer against the rule against the coin flip, yesterday's
     picks' first day, the options line - and the lessons that go into the next morning's prompt. Nothing here changes a rule: a rule change is a
     draft on the proving steps (india/reconstruct.py); the lessons only change what the writer is told.
Paper only. Nothing here calls the broker or reads sealed data. "Chances" are always given beside their baseline (the coin flip, chance, the market).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from india import paths

RULES = "morningview-v1-2026-10-23"
REG = Path(__file__).parent / "registrations"
PAGE = REG / "morningview.md"
REF_POLICY = "hold_20d"
FAMILY = {"BRK": "breakout", "PULL": "pullback", "REV": "reversal", "CTL": "random pick"}
FAMILY_WHY = {"BRK": "broke above its one-month high on heavy volume", "PULL": "a strong stock resting at its one-month average", "REV": "sold too hard, due a bounce"}
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _data() -> Path:
    return paths.data_dir()


def _paper() -> Path:
    return _data() / "paper"


def _dir() -> Path:
    d = _paper() / "morningview"
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


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _dw(d) -> str:
    try:
        return dt.date.fromisoformat(str(d)[:10]).strftime("%-d %b")
    except (TypeError, ValueError):
        return str(d or "")


def _pct(x, nd=1) -> str:
    return "n/a" if x is None else f"{100 * float(x):+.{nd}f}%"


# ------------------------------------------------------------------------------------------------------------------------------ sections

def overnight(plan: dict) -> dict:
    """What moved while India slept: the US close (Tiingo, fresh), India's own last close, the fear gauge, yesterday's institutional flows."""
    out = {"status": "ok", "us": {}, "india": {}, "flows": {}, "notes": []}
    p = _data() / "silver" / "us" / "us_close.parquet"
    try:
        import pandas as pd
        df = pd.read_parquet(p)
        for sym, name in (("SPY", "S&P 500"), ("QQQ", "Nasdaq 100")):
            rows = df[df["symbol"] == sym].sort_values("date")
            if len(rows):
                r = rows.iloc[-1]
                prev2 = rows.iloc[-2] if len(rows) > 1 else None
                out["us"][name] = {"date": str(r["date"]), "close": float(r["close"]), "ret": float(r["ret"]) if r["ret"] == r["ret"] else None,
                                   "two_day": (float(r["close"]) / float(rows.iloc[-3]["close"]) - 1) if len(rows) > 2 else None}
    except Exception as e:  # noqa: BLE001
        out["notes"].append(f"US close missing: {e.__class__.__name__}")
    ov = plan.get("overnight") or {}
    for k, name in (("NIFTY 50", "Nifty"), ("NIFTY BANK", "Bank Nifty"), ("INDIA VIX", "fear gauge")):
        v = ov.get(k)
        if v:
            out["india"][name] = {"date": v.get("date"), "close": v.get("close"), "d1": v.get("d1"), "vs_sma50": v.get("vs_sma50"), "vs_sma200": v.get("vs_sma200")}
    # 26 Oct: the day plan for Mon 26 Oct was written on Fri 23 Oct at 19:00, before that day's index close arrived, so the view said "Nifty
    # 22,688 (-0.5%)" (the 22 Oct close) while the 23 Oct close was 22,600. The newest close is now read at build time and its date is kept.
    try:
        from india import technicals
        fresh = technicals.latest_index(["NIFTY 50", "NIFTY BANK", "INDIA VIX"])
    except Exception as e:  # noqa: BLE001  the plan's rows stand, and the note says why
        fresh = {}
        out["notes"].append(f"newest index close not read: {e.__class__.__name__}")
    for k, name in (("NIFTY 50", "Nifty"), ("NIFTY BANK", "Bank Nifty"), ("INDIA VIX", "fear gauge")):
        f, have = fresh.get(k), out["india"].get(name) or {}
        if f and str(f.get("date")) > str(have.get("date") or ""):
            if have:
                out["notes"].append(f"{name}: the day plan had the {have.get('date')} close; the newest is {f['date']}")
            out["india"][name] = {**f, "plan_close": have.get("close"), "plan_date": have.get("date")}
    fd = ov.get("FII_DII") or {}
    for k, name in (("FII/FPI", "foreign institutions"), ("DII", "domestic institutions")):
        v = fd.get(k)
        if v:
            out["flows"][name] = {"date": v.get("date"), "net_crore": v.get("net_crore")}
    # FRED series arrive days late: kept only when fresh enough to mean something this morning
    for k, name in (("BRENT_SPOT_EUROPE", "Brent crude"), ("USDINR", "rupee per dollar"), ("US10Y", "US 10-year yield")):
        v = ov.get(k) or {}
        try:
            age = (dt.date.today() - dt.date.fromisoformat(str(v.get("date")))).days
        except (TypeError, ValueError):
            age = 99
        if age <= 3:
            out["us"][name] = {"date": v.get("date"), "close": v.get("value"), "ret": v.get("change") if v.get("unit") == "return" else None}
    if not out["us"] and not out["india"]:
        out["status"] = "missing"
    return out


def setup(session: str, plan: dict, rm: dict) -> dict:
    m = rm.get("market") or {}
    fc = plan.get("forecast") or {}
    prev = (plan.get("overnight") or {}).get("NIFTY 50", {}).get("close") or m.get("nifty_close")
    band = 0.003
    exp = {"today": [], "next": None}
    try:
        import pandas as pd
        df = pd.read_parquet(_data() / "silver" / "fo_calendar" / "expiries.parquet")
        df["expiry"] = pd.to_datetime(df["expiry"]).dt.date
        d0 = dt.date.fromisoformat(session)
        idx = df[(df["instrument"] == "OPTIDX") & (df["symbol"].isin(["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]))]
        exp["today"] = sorted(set(idx[idx["expiry"] == d0]["symbol"]))
        nxt = idx[idx["expiry"] > d0].sort_values("expiry")
        if len(nxt):
            e = nxt.iloc[0]["expiry"]
            exp["next"] = {"date": str(e), "symbols": sorted(set(nxt[nxt["expiry"] == e]["symbol"])), "monthly": bool(nxt.iloc[0]["is_monthly_last"])}
    except Exception as e:  # noqa: BLE001
        exp["note"] = f"expiry calendar missing: {e.__class__.__name__}"
    events = {"scheduled_today": False, "recent": []}
    try:
        from india import scenario
        events["scheduled_today"] = dt.date.fromisoformat(session) in scenario.scheduled_dates()
    except Exception:  # noqa: BLE001
        pass
    try:
        import pandas as pd
        ev = pd.read_parquet(_data() / "silver" / "events" / "events.parquet", columns=["event_id", "title", "category", "first_tradable_session"])
        ev["fts"] = pd.to_datetime(ev["first_tradable_session"]).dt.date
        d0 = dt.date.fromisoformat(session)
        rows = ev[(ev["fts"] >= d0 - dt.timedelta(days=4)) & (ev["fts"] <= d0)].sort_values("fts")
        events["recent"] = [{"title": r.title, "category": r.category, "session": str(r.fts)} for r in rows.itertuples()][-5:]
    except Exception:  # noqa: BLE001
        pass
    return {"status": "ok" if m else "missing", "trend_state": m.get("trend_state"), "nifty_prev_close": prev, "nifty_vs_sma50": m.get("nifty_vs_sma50"), "nifty_vs_sma200": m.get("nifty_vs_sma200"),
            "breadth_200d": m.get("breadth_200d_liquid"), "breadth_50d": m.get("breadth_50d_liquid"), "vix": m.get("vix_close"), "vix_vs_sma50": m.get("vix_vs_sma50"),
            "scenarios": {"bull": fc.get("bull"), "bear": fc.get("bear"), "neutral": fc.get("neutral")}, "scenario_text": plan.get("scenarios_text") or {},
            "scenario_levels": {"up_above": round(prev * (1 + band), 0) if prev else None, "down_below": round(prev * (1 - band), 0) if prev else None,
                                # the day's forecast was written with these lines, so they stay; the close they came from is named (26 Oct)
                                "set_from_date": (plan.get("overnight") or {}).get("NIFTY 50", {}).get("date"), "set_from_close": prev},
            "forecast_basis": "climatology: how often Nifty closed up, down or flat on 2005-2023 sessions (no skill claimed)", "forecast_id": plan.get("forecast_id"),
            "limits": plan.get("limits") or [], "expiry": exp, "events": events, "market_words": m.get("words")}


def plan_today(session: str, rm: dict) -> dict:
    """What Ananta does today: the picks it buys at the open (decided last night), the options line's state, and what it suggests on the holdings."""
    day = rm.get("data_through")
    d = _load(_paper() / "decisions" / f"{day}.json", {}) or {}
    picks = [{"symbol": x.get("symbol"), "family": FAMILY.get(x.get("campaign"), x.get("campaign")), "why": FAMILY_WHY.get(x.get("campaign"), ""), "last": x.get("close"), "rank": x.get("liq_rank")}
             for x in d.get("signals", []) if x.get("campaign") != "CTL"]
    n_ctl = sum(1 for x in d.get("signals", []) if x.get("campaign") == "CTL")
    by = Counter(p["family"] for p in picks)
    signed_in = False
    try:
        from india import kite
        signed_in = kite._read_token() is not None
    except Exception:  # noqa: BLE001
        pass
    sp1 = [x for x in _jsonl(_paper() / "sp1" / "decisions.jsonl") if str(x.get("date")) == session]
    sp1_plan = next((x for x in sp1 if x.get("kind") == "plan"), None)
    opt = {"signed_in": signed_in, "plan_written": sp1_plan is not None,
           "words": ("The options line decides between 09:15 and 10:15 Indian time: a Nifty or Bank Nifty option, one lot, only if the opening move clears the option's cost." if signed_in or sp1_plan
                     else "The options line cannot trade today: the morning sign-in to Zerodha is missing, so it has no live prices.")}
    av = _load(_paper() / "allocation_view.json", {}) or {}
    sug = [{"symbol": s.get("symbol"), "action": s.get("action"), "why": s.get("why")} for s in (av.get("suggestions") or [])[:4]]
    ab = _load(_paper() / "account" / "view.json", {}) or {}
    return {"status": "ok" if d else "missing", "decided_on": day, "picks": picks, "picks_by_family": dict(by), "random_picks": n_ctl, "options_line": opt,
            "holdings_suggestions": sug, "allocation_headline": av.get("headline"), "account_words": ab.get("words"), "moves_today": [m.get("why") for m in (av.get("moves") or [])][:2]}


def scorecard(rm: dict) -> dict:
    """Predictions against what happened, on the record: the rule forecast, the reviewer's forecast and the coin flip; the daily call; the picks'
    first day; the options line. The honest 'our chances'."""
    rows = _jsonl(_paper() / "forecasts.jsonl")
    fcs = {r["forecast_id"]: r for r in rows if r.get("kind") == "forecast"}
    scores = [r for r in rows if r.get("kind") == "score"]
    rec = {"rule": {"n": 0, "hits": 0, "brier": []}, "reviewer": {"n": 0, "hits": 0, "brier": []}, "chronos": {"n": 0, "hits": 0, "brier": []},
           "coin_flip_brier": []}
    for s in scores:
        f = fcs.get(s.get("ref")) or {}
        who = _who(f)
        if who == "chronos" and not (f.get("subject") == "NIFTY 50" and int(f.get("horizon_sessions") or 0) == 1):
            continue                       # the scorecard compares like with like: Nifty 50, next session (the other Chronos rows stay in the ledger)
        rec[who]["n"] += 1
        rec[who]["hits"] += 1 if s.get("hit") else 0
        if s.get("brier") is not None:
            rec[who]["brier"].append(float(s["brier"]))
        if s.get("brier_coin_flip") is not None and who == "rule":
            rec["coin_flip_brier"].append(float(s["brier_coin_flip"]))
    for k in ("rule", "reviewer", "chronos"):
        b = rec[k].pop("brier")
        rec[k]["brier_mean"] = round(sum(b) / len(b), 3) if b else None
    cf = rec.pop("coin_flip_brier")
    rec["coin_flip_brier_mean"] = round(sum(cf) / len(cf), 3) if cf else None
    c = rm.get("call") or {}
    call = {"scored": c.get("scored", 0), "hits": c.get("hits", 0), "coin_flip_hits": c.get("null_hits", 0)}
    marks = {}
    for m in _jsonl(_paper() / "marks.jsonl"):
        if m.get("book") == "exec" and m.get("policy") == REF_POLICY:
            marks[m["campaign"]] = m
    book = {FAMILY.get(k, k): {"closed": v.get("closed", 0), "open": v.get("open", 0), "realised_inr": round(v.get("realised_inr") or 0), "win_rate": v.get("win_rate")} for k, v in marks.items()}
    sp1 = (rm.get("sp1") or {}).get("book") or {}
    st = _load(REG / "evidence_staircase.json", {}) or {}
    return {"forecasts": rec, "daily_call": call, "stock_book": book, "options_sessions": sp1.get("sessions") or 0, "staircase_words": st.get("words"),
            "words": _chances_words(rec, call, book, sp1.get("sessions") or 0)}


def _who(f: dict) -> str:
    """Who wrote a forecast: the morning-view reviewer, the Hugging Face Chronos model (25 Oct 2026), or Ananta's rule (the day plan)."""
    b = str(f.get("basis", ""))
    return "reviewer" if b.startswith("reviewer") else ("chronos" if b.startswith("chronos") else "rule")


def _chances_words(rec: dict, call: dict, book: dict, opt_sessions: int) -> str:
    r = rec["rule"]
    bits = []
    if r["n"]:
        bits.append(f"Ananta's rule forecast has been right {r['hits']} of {r['n']} sessions" + (f" (its error score {r['brier_mean']} against {rec['coin_flip_brier_mean']} for a coin flip; lower is better)" if r.get("brier_mean") is not None and rec.get("coin_flip_brier_mean") is not None else ""))
    else:
        bits.append("Ananta's forecast has no scored session yet")
    v = rec["reviewer"]
    if v["n"]:
        bits.append(f"the reviewer's forecast {v['hits']} of {v['n']}")
    ch = rec.get("chronos") or {}
    if ch.get("n"):
        bits.append(f"the Chronos model (a free Hugging Face forecaster) {ch['hits']} of {ch['n']}")
    if call.get("scored"):
        bits.append(f"the daily call {call['hits']} of {call['scored']} against {call['coin_flip_hits']} for the coin flip")
    closed = sum(b.get("closed", 0) for b in book.values())
    if closed:
        net = sum(b.get("realised_inr", 0) for b in book.values())
        bits.append(f"the research book has closed {closed} practice trades for {'+' if net >= 0 else '−'}₹{abs(net):,.0f} net")
    bits.append(f"the options line has {opt_sessions} session{'s' if opt_sessions != 1 else ''} on record")
    return "; ".join(bits) + ". No rule has proved itself yet, so every chance here is a chance, not an edge."


def yesterday(rm: dict) -> dict:
    """What happened against what was predicted, for the last session on record: the lesson the next view carries."""
    day = rm.get("data_through")
    rows = _jsonl(_paper() / "forecasts.jsonl")
    fcs = [r for r in rows if r.get("kind") == "forecast" and r.get("session") == day]
    scores = {s.get("ref"): s for s in rows if s.get("kind") == "score"}
    preds = []
    for f in fcs:
        s = scores.get(f["forecast_id"]) or {}
        top = max((f.get("scenarios") or {}).items(), key=lambda kv: kv[1])[0] if f.get("scenarios") else None
        preds.append({"who": _who(f), "favoured": top, "p": (f.get("scenarios") or {}).get(top),
                      "outcome": s.get("outcome"), "hit": s.get("hit"), "basis": str(f.get("basis", ""))[:120]})
    m = rm.get("market") or {}
    c = rm.get("call") or {}
    call_score = next((x for x in reversed(_jsonl(_paper() / "calls.jsonl")) if x.get("kind") == "score" and x.get("data_through") == day), None)
    st = _load(_paper() / "state.json", {}) or {}
    first_day = []
    for t in (st.get("trades") or {}).values():
        if t.get("book") == "exec" and t.get("policy") == REF_POLICY and t.get("entry_date") == day and t.get("campaign") != "CTL" and t.get("entry_adj") and t.get("last_close_adj"):
            first_day.append({"symbol": t["symbol"], "ret": round(t["last_close_adj"] / t["entry_adj"] - 1, 4)})
    avg = round(sum(x["ret"] for x in first_day) / len(first_day), 4) if first_day else None
    rx = rm.get("reconstruction") or {}
    sp1 = rm.get("sp1") or {}
    les = []
    for p in preds:
        if p.get("hit") is False:
            les.append(f"The {p['who']} forecast favoured '{p['favoured']}' and the session closed '{p['outcome']}': wrong.")
        elif p.get("hit"):
            les.append(f"The {p['who']} forecast favoured '{p['favoured']}' and was right.")
    if call_score:
        les.append(f"The daily call was {'right' if (call_score.get('score') or 0) > 0 else 'wrong'} (Nifty moved {_pct(call_score.get('move'), 2)}).")
    if avg is not None:
        les.append(f"The research book's {len(first_day)} practice buys at that open averaged {_pct(avg)} by the close.")
    if sp1.get("status") == "lost":
        les.append("The options line had no session: the morning sign-in was missing.")
    return {"session": day, "nifty_move": m.get("nifty_ret1") if m.get("nifty_ret1") is not None else None, "predictions": preds, "call": {"call": c.get("call"), "right": (call_score.get("score") or 0) > 0 if call_score else None},
            "picks_first_day": {"n": len(first_day), "avg_ret": avg, "best": sorted(first_day, key=lambda x: -x["ret"])[:3], "worst": sorted(first_day, key=lambda x: x["ret"])[:3]},
            "options_line": sp1.get("status"), "review_headline": rx.get("headline"), "lessons": les}


def lessons_for_writer(sc: dict, y: dict) -> list[str]:
    """What the next morning's writer is told to change, from the record (never a rule change: those are drafts on the proving steps)."""
    out = []
    r = sc["forecasts"]["rule"]
    if r["n"] >= 3 and r["hits"] <= r["n"] / 2:
        out.append("Do not lean on the direction forecast: it has no record of being right. Give the odds with the coin flip beside them.")
    c = sc["daily_call"]
    if c.get("scored", 0) >= 3 and c.get("hits", 0) < c.get("coin_flip_hits", 0):
        out.append("The daily call is behind the coin flip so far: say so plainly whenever it is quoted.")
    if sc.get("options_sessions", 0) == 0:
        out.append("The options line has no record: describe what it would do, never what it will earn.")
    out += [x for x in y.get("lessons", []) if "wrong" in x]
    out.append("Every number comes from the facts; nothing is advice; paper only.")
    return out


# ------------------------------------------------------------------------------------------------------------------------------ plain lines

def lines(f: dict) -> dict:
    """The view in plain words, by rule, so the morning exists even without a model. Four short parts and a watch list."""
    ov, s, p, sc, y = f["overnight"], f["setup"], f["plan"], f["scorecard"], f["yesterday"]
    view = []
    us = ov.get("us") or {}
    if us.get("S&P 500"):
        sp, nq = us["S&P 500"], us.get("Nasdaq 100") or {}
        fmt = lambda r: "flat" if r is not None and abs(r) < 0.0005 else _pct(r)   # noqa: E731
        view.append(f"US: the S&P 500 closed {fmt(sp.get('ret'))} ({_dw(sp.get('date'))})" + (f", the Nasdaq {fmt(nq.get('ret'))}" if nq else "") + ".")
    ind = ov.get("india") or {}
    n = ind.get("Nifty") or {}
    if n:
        tr = {"above_both": "in an uptrend", "below_both": "in a downtrend", "mixed": "with no clear trend"}.get(s.get("trend_state"), "")
        view.append(f"Nifty closed at {n['close']:,.0f} on {_dw(n.get('date'))} ({_pct(n.get('d1'))}), {tr}: {_pct(n.get('vs_sma50'))} against its ten-week average, {_pct(n.get('vs_sma200'))} against its long-term average; "
                    f"{100 * (s.get('breadth_200d') or 0):.0f}% of the 250 most-traded stocks are above their long-term average.")
    v = ind.get("fear gauge") or {}
    if v:
        view.append(f"The fear gauge is at {v['close']}, {_pct(v.get('vs_sma50'), 0)} against its ten-week average" + (" — options are pricing more movement than usual." if (v.get("vs_sma50") or 0) > 0.15 else "."))
    fl = ov.get("flows") or {}
    if fl:
        view.append("Yesterday " + " and ".join(f"{k} {'bought' if (x.get('net_crore') or 0) >= 0 else 'sold'} ₹{abs(x.get('net_crore') or 0):,.0f} crore" for k, x in fl.items()) + ".")
    sc_ = s.get("scenarios") or {}
    if sc_.get("bull") is not None:
        lv = s.get("scenario_levels") or {}
        view.append(f"Odds for today, from how Nifty has behaved since 2005: up {100 * sc_['bull']:.0f}% (a close above {lv.get('up_above'):,.0f}), down {100 * sc_['bear']:.0f}% (below {lv.get('down_below'):,.0f}), flat {100 * sc_['neutral']:.0f}%. "
                    "These are base rates, not a read of today.")
    plan = []
    picks = p.get("picks") or []
    if picks:
        by = p.get("picks_by_family") or {}
        plan.append(f"Ananta's research book makes {len(picks)} practice buys at the open ({', '.join(f'{v} {k}{'s' if v != 1 else ''}' for k, v in by.items())}): " + ", ".join(x["symbol"] for x in picks[:8]) + (" and more" if len(picks) > 8 else "") + ". Practice trades, not your money: a rule must prove itself before it buys for your account.")
    else:
        plan.append("Ananta's research book has no new practice buy at this open.")
    plan.append((p.get("options_line") or {}).get("words", ""))
    if p.get("moves_today"):
        plan.append("Your money: " + p["moves_today"][0] + ".")
    if p.get("holdings_suggestions"):
        plan.append("On your holdings it suggests: " + "; ".join(f"{x['action'].lower()} {x['symbol']}" for x in p["holdings_suggestions"][:3]) + ".")
    chances = [sc.get("words", "")]
    watch = []
    ex = s.get("expiry") or {}
    if ex.get("today"):
        watch.append(f"Expiry day for {', '.join(ex['today'])} options: moves can be sharp in the last hour.")
    elif ex.get("next"):
        watch.append(f"Next options expiry: {_dw(ex['next']['date'])} ({', '.join(ex['next']['symbols'][:3])}{', monthly' if ex['next'].get('monthly') else ''}).")
    if (s.get("events") or {}).get("scheduled_today"):
        watch.append("A scheduled event (policy, budget or results) falls today: the first hour can move on it.")
    for e in ((s.get("events") or {}).get("recent") or [])[-2:]:
        watch.append(f"Recent event: {e['title']} ({_dw(e['session'])}).")
    lv = s.get("scenario_levels") or {}
    if lv.get("up_above"):
        stale_lines = n.get("plan_date") and lv.get("set_from_date") and str(lv["set_from_date"]) < str(n.get("date"))
        watch.append(f"The lines that decide the day's label: above {lv['up_above']:,.0f} is an up day, below {lv['down_below']:,.0f} a down day"
                     + (f" (set when the day's forecast was written, from the {_dw(lv['set_from_date'])} close of {lv['set_from_close']:,.0f}, not the newer {_dw(n.get('date'))} close)." if stale_lines else "."))
    watch.append("Guardrails: a 5% loss stops the day; 22% below the peak pauses new buys.")
    yest = []
    if y.get("lessons"):
        yest = y["lessons"][:4]
    return {"view": view, "plan": plan, "chances": chances, "watch": watch, "yesterday": yest,
            "headline": (view[1] if len(view) > 1 else (view[0] if view else "No market reading yet.")) + " " + (plan[0] if plan else "")}


# ------------------------------------------------------------------------------------------------------------------------------ build

def next_session(after: str | None = None) -> str:
    from india import dayplan
    d = dt.date.fromisoformat(after) + dt.timedelta(days=1) if after else None
    return dayplan.next_session(d).isoformat()


def build(session: str | None = None) -> dict:
    rm = _load(_data() / "readmodel" / "latest.json", {}) or {}
    session = session or rm.get("next_session") or next_session(rm.get("data_through"))
    plan = _load(_paper() / "dayplans" / f"{session}.json", {}) or {}
    f = {"rules": RULES, "session": session, "built_at": _now(), "data_through": rm.get("data_through"), "paper": True,
         "overnight": overnight(plan), "setup": setup(session, plan, rm), "plan": plan_today(session, rm), "scorecard": scorecard(rm), "yesterday": yesterday(rm)}
    f["lessons_for_writer"] = lessons_for_writer(f["scorecard"], f["yesterday"])
    f["lines"] = lines(f)
    f["sources"] = {"dayplan": str(_paper() / "dayplans" / f"{session}.json"), "us_close": str(_data() / "silver" / "us" / "us_close.parquet"), "readmodel": str(_data() / "readmodel" / "latest.json"),
                    "forecasts": str(_paper() / "forecasts.jsonl"), "decisions": str(_paper() / "decisions" / f"{rm.get('data_through')}.json")}
    prev = _load(_dir() / f"{session}.json", {}) or {}
    for k in ("words", "review", "reviewer_scenarios", "words_at", "opening"):     # the model's words and the opening update survive a rebuild
        if prev.get(k) is not None:
            f[k] = prev[k]
    p = _dir() / f"{session}.json"
    p.write_text(json.dumps(f, indent=1, default=str))
    (_dir() / "latest.json").write_text(json.dumps(f, indent=1, default=str))
    page(f)
    return f


def page(f: dict) -> str:
    L = [f"# Morning view, session {_dw(f['session'])} (built {f['built_at'][:16]}Z)", "", f["lines"]["headline"], ""]
    for title, key in (("The view", "view"), ("What Ananta is doing today", "plan"), ("Our chances, honestly", "chances"), ("Watch today", "watch"), ("Yesterday's scorecard", "yesterday")):
        L += [f"## {title}"] + [f"- {x}" for x in f["lines"].get(key) or ["- nothing to say"]] + [""]
    if f.get("words"):
        L += ["## Ananta's note", f["words"], ""]
    if f.get("review"):
        L += ["## Second opinion (the reviewer)", f["review"], ""]
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text("\n".join(L))
    return PAGE.read_text()


def show() -> None:
    f = _load(_dir() / "latest.json", {}) or {}
    print(page(f) if f else "no morning view yet: run `python -m india.morningview build`")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "build":
        f = build(sys.argv[2] if len(sys.argv) > 2 else None)
        print(f["lines"]["headline"])
    else:
        show()
