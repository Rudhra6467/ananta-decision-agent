"""India's capital allocator (Madhav, 23 Oct 2026): rate, rank and suggest on the account; in autonomous mode, move capital between sleeves on paper.

  python -m india.allocator run [YYYY-MM-DD]    one allocation decision for the session after the latest read model; writes paper/allocation_view.json
  python -m india.allocator show                prints the latest view as plain text

Madhav's words (23 Oct, 14:04): "If I allocate capital separately, it will be 50000 to options and what's already there in my account for stocks. It has to
evaluate, rate, rank and suggest modifications for me. And if I say everything is autonomous, it should be able to move the capital here and there, do
adjustments and keep track for upcoming changes and market moves to keep tracing current positions and for new opportunities."

Two modes (paper/allocation.json, set on the Options card):
  advisory    the split is fixed: options Rs 50,000, stocks = the account's holdings as the daily ledger snapshot last saw them. Ananta rates and ranks every
              holding, suggests changes (hold / trim / reduce / add) with a reason and a "wrong if", and says where the fixed split sits against its own
              reading of the market. It moves nothing.
  autonomous  one pool (stocks + options + cash). Each session Ananta sets the split from the regime table in registrations/allocation_rule_v1.json and moves
              capital between the three sleeves, at most 10% of the pool a session, never for less than Rs 2,000, and writes every move to the ledger.
Both modes are PAPER: this module places no order and reads no broker (the no-order rule, india/leakcheck.py). A suggestion is advice; a paper move is a ledger
line. Real execution waits for the gate. The account snapshot is bronze/ledger (read-only, daily); this module never calls Kite.
Nothing sealed is read. Every number traces to a file named in the view's `sources`.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from india import paths

REG = Path(__file__).parent / "registrations"
RULE_FILE = REG / "allocation_rule_v1.json"
GRADES = (("A", 70), ("B", 55), ("C", 40), ("D", 0))


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


def rule() -> dict:
    return json.loads(RULE_FILE.read_text())


def _paper() -> Path:
    return paths.data_dir() / "paper"


def settings() -> dict:
    """paper/allocation.json normalised: mode is 'advisory' or 'autonomous' (the older 'fixed' and 'ananta' words map to them)."""
    a = _load(_paper() / "allocation.json", {}) or {}
    r = rule()
    mode = {"fixed": "advisory", "advisory": "advisory", "ananta": "autonomous", "autonomous": "autonomous"}.get(a.get("mode"), r["default_mode"])
    return {"mode": mode, "options_inr": float(a.get("options_inr") or r["options_inr"]), "set_at": a.get("set_at"), "set_by": a.get("set_by")}


def account() -> dict:
    """The newest daily ledger snapshot (Madhav's Zerodha holdings and funds, read-only): holdings, cash, and how old it is."""
    d = paths.data_dir() / "bronze" / "ledger"
    files = sorted(d.glob("*.json")) if d.exists() else []
    if not files:
        return {"status": "missing", "holdings": [], "cash_inr": 0.0, "source": str(d), "words": "no account snapshot yet: the daily ledger job has not saved one"}
    j = _load(files[-1], {}) or {}
    eq = ((j.get("margins") or {}).get("equity") or {}).get("available") or {}
    taken = j.get("taken_at")
    return {"status": "ok", "taken_at": taken, "day": files[-1].stem, "source": str(files[-1]), "holdings": j.get("holdings") or [],
            "cash_inr": float(eq.get("live_balance", eq.get("cash", 0)) or 0), "words": f"account snapshot of {files[-1].stem}"}


def _universe() -> tuple[dict, dict, str | None]:
    """The liquid-250 feature rows of the newest decision day, by symbol and by isin."""
    fs = sorted((_paper() / "decisions").glob("*.universe.json"))
    if not fs:
        return {}, {}, None
    j = _load(fs[-1], {}) or {}
    by_sym = {r["symbol"]: r for r in j.get("rows", [])}
    by_isin = {r.get("isin"): r for r in j.get("rows", []) if r.get("isin")}
    return by_sym, by_isin, fs[-1].name.split(".")[0]


def grade(score: float) -> str:
    return next(g for g, lo in GRADES if score >= lo)


WRONG_STEP = 0.10    # when no average sits on the right side of the price: a further 10% move


def wrong_down(last: float, levels: list, tail: str = "") -> str:
    """What would prove a keep / watch / add call wrong: a close under a level that is still BELOW today's price (27 Oct: TMPV said
    "wrong if it closes under ₹338, its long-term average" while it was at ₹263.70, a line already crossed). The first level under the price,
    else a further 10% fall."""
    for lv, name in levels:
        if lv and last and lv < last:
            return f"it closes under ₹{lv:,.0f}, {name}{tail}"
    if not last:
        return "it turns down"
    return f"it falls another {WRONG_STEP:.0%}, under ₹{last * (1 - WRONG_STEP):,.0f} (it is already below its averages){tail}"


def wrong_up(last: float, levels: list, tail: str = "") -> str:
    """What would prove a reduce / trim call wrong: a climb back above a level still ABOVE today's price, else a further 10% rise."""
    for lv, name in levels:
        if lv and last and lv > last:
            return f"it climbs back above ₹{lv:,.0f}, {name}{tail}"
    if not last:
        return "it turns up" + tail
    return f"it climbs another {WRONG_STEP:.0%}, above ₹{last * (1 + WRONG_STEP):,.0f} (it is already above its averages){tail}"


def wrong_if_already_true(x: dict) -> bool:
    """A check for every suggestion: a 'wrong if' line must not already be true at the price it was written at."""
    import re
    m = re.search(r"(closes under|climbs back above) ₹([\d,]+)", x.get("wrong_if") or "")
    if not m or not x.get("last"):
        return False
    lv = float(m.group(2).replace(",", ""))
    return x["last"] <= lv if m.group(1) == "closes under" else x["last"] >= lv


def rate_holding(h: dict, weight: float, row: dict | None, trend: str, r: dict) -> dict:
    """Score one holding 0-100 from its own tape, the market regime, the account's concentration and the cost to leave. Every part is in `parts`."""
    w = r["rating_weights"]
    last, avg, qty = float(h.get("last_price") or 0), float(h.get("average_price") or 0), float(h.get("quantity") or 0)
    value = last * qty
    pnl_pct = 100 * (last / avg - 1) if avg else None
    parts: dict[str, float] = {}
    notes: list[str] = []
    if row:
        d20, d200, rsi, atr = row.get("dist_sma20"), row.get("dist_sma200"), row.get("rsi14"), row.get("atr_pct")
        t = 0.0
        t += w["above_200d"] if (d200 or 0) > 0 else 0
        t += w["above_20d"] if (d20 or 0) > 0 else 0
        t += w["rsi_healthy"] if rsi is not None and 40 <= rsi <= 70 else 0
        parts["trend"] = t
        # in a market below both averages a stock still above its own 200-day is relative strength; one below it is trading with the tide
        rf = w["regime_fit"]
        parts["regime"] = rf if (d200 or 0) > 0 else (rf * 0.5 if trend != "below_both" else 0.0)
        parts["volatility"] = w["volatility"] if atr is not None and atr <= 0.03 else (w["volatility"] * 0.5 if atr is not None and atr <= 0.05 else 0.0)
        parts["liquidity"] = w["liquidity"] if (row.get("liq_rank") or 999) <= 50 else (w["liquidity"] * 0.6 if (row.get("liq_rank") or 999) <= 150 else w["liquidity"] * 0.3)
        sma20 = last / (1 + d20) if d20 is not None else None
        sma200 = last / (1 + d200) if d200 is not None else None
        notes.append(_tape_words(d20, d200, rsi))
        rated = True
    else:
        # outside the liquid 250 the research has no tape on it; it is graded on what the account itself shows, and says so
        parts.update({"trend": 0.0, "regime": 0.0, "volatility": 0.0, "liquidity": w["liquidity"] * 0.3})
        sma20 = sma200 = None
        notes.append("not among the 250 most-traded stocks, so Ananta has no price study on it: graded on its size in your account and its result only")
        rated = False
    wt = 100 * weight
    parts["concentration"] = w["concentration"] if wt <= r["weight_ok_pct"] else (w["concentration"] * 0.5 if wt <= r["weight_high_pct"] else 0.0)
    pp = w["result"]
    parts["result"] = pp if (pnl_pct or 0) >= 5 else (pp * 0.6 if (pnl_pct or 0) >= 0 else (pp * 0.3 if (pnl_pct or 0) >= -10 else 0.0))
    score = round(sum(parts.values()), 1)
    if not rated:                      # an unrated holding cannot reach A on thin evidence: cap at B
        score = min(score, r["unrated_cap"])
    g = grade(score)
    sym = h.get("tradingsymbol")
    act, why, wrong = "HOLD", "", ""
    on_cost = (f", {pnl_pct:+.0f}% on what you paid" if pnl_pct is not None else "")
    if value < r["tiny_inr"]:
        act = "TIDY"
        why = f"Only ₹{value:,.0f}{on_cost}: too small to matter either way. Sell it and put the money to work, or add to it on purpose."
        wrong = "you want to keep it as a small deliberate stake (then say so and it stays)"
    elif g == "D":
        act = "REDUCE"
        why = f"Weak ({score:.0f}/100): {notes[0] or 'poor result'}. It is {wt:.0f}% of your stocks{on_cost}. Halving it limits the damage if the slide continues."
        wrong = wrong_up(last, [(sma20, "its one-month average"), (sma200, "its long-term average")], " on good volume")
    elif g == "C":
        if wt > r["weight_ok_pct"]:
            act = "TRIM"
            why = f"Middling ({score:.0f}/100) but {wt:.0f}% of your stocks{on_cost}: more than a middling stock should be. Trim it toward {r['weight_ok_pct']:.0f}%."
            wrong = wrong_up(last, [(sma20, "its one-month average"), (sma200, "its long-term average")])
        else:
            act = "WATCH"
            why = f"Middling ({score:.0f}/100): not weak enough to sell, not strong enough to add. {notes[0]}"
            wrong = wrong_down(last, [(sma200, "its long-term average"), (sma20, "its one-month average")])
    elif g == "A" and wt <= r["add_below_weight_pct"] and trend != "below_both":
        act = "ADD"
        why = f"Strong ({score:.0f}/100) and only {wt:.0f}% of your stocks, with the market not in a downtrend: room to add."
        wrong = wrong_down(last, [(sma20, "its one-month average"), (sma200, "its long-term average")])
    else:
        act = "HOLD"
        why = f"{'Strong' if g == 'A' else 'Fine'} ({score:.0f}/100): {notes[0] or 'result and size are acceptable'}{on_cost}. Keep it."
        wrong = wrong_down(last, [(sma200, "its long-term average"), (sma20, "its one-month average")])
    if act == "TIDY":
        size = value
    elif act == "REDUCE":
        size = value * 0.5
    elif act == "TRIM":
        size = value * (1 - r["weight_ok_pct"] / wt) if wt else 0
    elif act == "ADD":
        size = value * 0.25
    else:
        size = 0
    size = round(size / 100) * 100
    return {"symbol": sym, "exchange": h.get("exchange"), "qty": qty, "value_inr": round(value), "weight_pct": round(wt, 1), "avg": avg, "last": last, "suggest_inr": size,
            "pnl_pct": None if pnl_pct is None else round(pnl_pct, 1), "pnl_inr": round(float(h.get("pnl") or 0)), "score": score, "grade": g, "rated": rated,
            "action": act, "why": why, "wrong_if": wrong, "parts": {k: round(v, 1) for k, v in parts.items()}}


def _tape_words(d20, d200, rsi) -> str:
    """What the chart says, in words a person uses: against the long-term average, against the last month, and momentum."""
    bits = []
    if d200 is not None:
        bits.append(f"{abs(100 * d200):.0f}% {'above' if d200 > 0 else 'below'} its long-term average")
    if d20 is not None:
        bits.append("flat over the last month" if abs(d20) < 0.015 else f"{abs(100 * d20):.0f}% {'up' if d20 > 0 else 'down'} over the last month")
    if rsi is not None:
        bits.append("momentum " + ("strong" if rsi >= 60 else "weak" if rsi <= 40 else "neutral"))
    return ", ".join(bits)


def rate_options(rm: dict, r: dict, opt_value: float) -> dict:
    s = (rm.get("sp1") or {})
    sessions = (s.get("book") or {}).get("sessions") or 0
    lost = s.get("status") == "lost"
    vix = (rm.get("market") or {}).get("vix_close")
    sc = 0.0
    sc += 30 if sessions >= 20 else (15 if sessions >= 5 else 0)
    sc += 20 if not lost else 0
    sc += 25 if (vix is not None and vix <= 18) else 10
    sc += 25 if opt_value >= r["options_inr"] * 0.9 else 12
    g = grade(sc)
    why = (f"{sessions} session{'s' if sessions != 1 else ''} traded so far" if sessions else "nothing traded on options yet") + ("; the last session was missed because the morning sign-in to Zerodha failed" if lost else "") + (f"; the fear gauge is at {vix:.1f}" if vix is not None else "")
    return {"score": round(sc), "grade": g, "sessions": sessions, "why": why,
            "action": "KEEP SMALL" if sessions < r["evidence_sessions"] else "HOLD",
            "words": (f"₹{opt_value:,.0f} is set aside for options. Ananta trades one lot at a time there, and it earns a bigger share only after {r['evidence_sessions']} sessions are on record ({sessions} so far); until then most of this money waits as cash."
                      if sessions < r["evidence_sessions"] else "The options line has a track record; its size follows the sizing study.")}


def _regime(rm: dict) -> str:
    return ((rm.get("market") or {}).get("trend_state")) or "mixed"


def targets(r: dict, trend: str, sessions: int, fired: bool) -> dict:
    t = dict(r["regime_table"].get(trend) or r["regime_table"]["mixed"])
    opt = t["options_max"]
    if sessions < r["evidence_sessions"]:
        opt = min(opt, r["unproven_options_max"])
    return {"options": opt, "cash_min": t["cash_min"], "stocks": round(1 - opt - t["cash_min"], 4), "regime": trend, "no_new_entries": fired}


def _moves(sleeves: dict, tg: dict, ratings: list[dict], cands: list[dict], r: dict, fired: bool) -> list[dict]:
    """Paper moves toward the target split: options and weak stocks release capital into cash; cash goes to the best-rated stocks only when the stock
    sleeve is under target and no guardrail has fired. At most max_shift_frac of the pool a session, never a move under min_move_inr."""
    pool = sum(sleeves.values())
    if pool <= 0:
        return []
    budget = r["max_shift_frac"] * pool
    band = r["band_frac"] * pool
    moves: list[dict] = []
    opt_gap = sleeves["options"] - tg["options"] * pool
    if opt_gap > band:
        amt = min(opt_gap, budget)
        amt = round(amt / 100) * 100
        if amt >= r["min_move_inr"]:
            regime = {"below_both": "in a downtrend", "above_both": "in an uptrend", "mixed": "with no clear trend"}.get(tg["regime"], "")
            moves.append({"kind": "sleeve", "from": "options", "to": "cash", "inr": amt,
                          "why": f"options were {100 * sleeves['options'] / pool:.0f}% of your money; {regime} Ananta keeps them at or under {100 * tg['options']:.0f}%"
                                 + (", and the options line has not yet earned a bigger share" if tg["options"] <= r["unproven_options_max"] else "")})
            budget -= amt
    stock_gap = sleeves["stocks"] - tg["stocks"] * pool
    if stock_gap > band and budget >= r["min_move_inr"]:
        weak = [x for x in sorted(ratings, key=lambda x: x["score"]) if x["action"] in ("REDUCE", "TRIM", "TIDY")]
        left = min(stock_gap, budget)
        for x in weak:
            if left < r["min_move_inr"]:
                break
            part = min(left, x["value_inr"] * (0.5 if x["action"] == "TRIM" else 1.0))
            part = round(part / 100) * 100
            if part >= r["min_move_inr"]:
                moves.append({"kind": "stock_sell", "symbol": x["symbol"], "from": "stocks", "to": "cash", "inr": part,
                              "why": f"{x['symbol']} is a weak holding ({x['score']:.0f}/100) and stocks are over their {100 * tg['stocks']:.0f}% share"})
                left -= part
                budget -= part
    elif -stock_gap > band and not fired and tg["regime"] != "below_both" and budget >= r["min_move_inr"]:
        good = [x for x in sorted(ratings, key=lambda x: -x["score"]) if x["action"] == "ADD"]
        picks = [("holding", x["symbol"], x["grade"]) for x in good[:2]] + [("candidate", c["symbol"], c.get("campaign")) for c in cands[:2]]
        if picks:
            each = round(min(-stock_gap, budget) / len(picks) / 100) * 100
            if each >= r["min_move_inr"]:
                for kind, sym, tag in picks:
                    moves.append({"kind": "stock_buy", "symbol": sym, "from": "cash", "to": "stocks", "inr": each, "family": tag if kind == "candidate" else "GRADE",
                                  "why": f"{'a strong holding with room to add' if kind == 'holding' else 'a fresh ' + str(tag).lower() + ' signal from a proved rule'}; stocks are under their {100 * tg['stocks']:.0f}% share"})
    return moves


def watch(rm: dict, ratings: list[dict], snap: dict, trend: str) -> list[dict]:
    m = rm.get("market") or {}
    out = []
    n50, n200 = m.get("nifty_vs_sma50"), m.get("nifty_vs_sma200")
    if n50 is not None and n200 is not None:
        tw = {"below_both": "a downtrend", "above_both": "an uptrend", "mixed": "no clear trend"}.get(trend, trend.replace("_", " "))
        out.append({"what": "The market's trend", "now": tw,
                    "flips_if": (f"Nifty climbs about {100 * abs(min(n50, n200)):.0f}%: it is back above its averages and Ananta allows more in options and less in cash" if n50 < 0 or n200 < 0
                                 else "Nifty closes under its ten-week average: Ananta keeps less in options and more in cash"), "why": "how much goes to options and how much stays in cash follow the trend"})
    v = m.get("vix_vs_sma50")
    if v is not None:
        out.append({"what": "The fear gauge (India VIX)", "now": f"{m.get('vix_close')} ({100 * v:+.0f}% against its ten-week average)", "flips_if": "it jumps more than 30% above its ten-week average: options get expensive and Ananta buys fewer", "why": "buying options when fear spikes means paying too much"})
    near = [x["symbol"] for x in ratings if x.get("rated") and abs(x["score"] - 55) < 4 or abs(x["score"] - 40) < 4]
    if near:
        out.append({"what": "Holdings close to a different rating", "now": ", ".join(near[:6]), "flips_if": "a few points either way moves them between keep, watch and trim", "why": "every holding is re-rated each evening"})
    taken = snap.get("taken_at")
    try:
        taken_w = dt.datetime.fromisoformat(taken).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%-d %b %H:%M") + " Indian time" if taken else "never"
    except ValueError:
        taken_w = str(taken)[:16]
    out.append({"what": "Your account's snapshot from Zerodha", "now": f"taken {taken_w}", "flips_if": "it gets more than a day old: the ratings use old holdings", "why": "the ratings are only as fresh as the snapshot"})
    out.append({"what": "The options line's record", "now": f"{((rm.get('sp1') or {}).get('book') or {}).get('sessions') or 0} sessions", "flips_if": f"it reaches {rule()['evidence_sessions']} sessions: options can earn a bigger share", "why": "options earn their share by a track record, not by hope"})
    return out


def build(day: str | None = None) -> dict:
    r = rule()
    rm = _load(paths.data_dir() / "readmodel" / "latest.json", {}) or {}
    day = day or rm.get("data_through") or dt.date.today().isoformat()
    cfg = settings()
    snap = account()
    by_sym, by_isin, uni_day = _universe()
    trend = _regime(rm)
    fired = bool((rm.get("guardrails") or {}).get("fired"))
    hs = [h for h in snap["holdings"] if (h.get("quantity") or 0) > 0]
    stock_value = sum((h.get("last_price") or 0) * h["quantity"] for h in hs)
    ratings = []
    for h in hs:
        row = by_sym.get(h.get("tradingsymbol")) or by_isin.get(h.get("isin"))
        wgt = ((h.get("last_price") or 0) * h["quantity"]) / stock_value if stock_value else 0
        ratings.append(rate_holding(h, wgt, row, trend, r))
    ratings.sort(key=lambda x: (-x["score"], -x["value_inr"]))
    for i, x in enumerate(ratings, 1):
        x["rank"] = i
    sp1 = (rm.get("sp1") or {})
    sessions = ((sp1.get("book") or {}).get("sessions")) or 0
    paper = _paper()
    ledger = [x for x in _jsonl(paper / "allocation_ledger.jsonl") if x.get("day") != day]
    adj = {"stocks": 0.0, "options": 0.0, "cash": 0.0}
    for x in ledger:
        for k, v in (x.get("applied_adj") or {}).items():
            adj[k] += v
    opt_base = cfg["options_inr"]
    sleeves = {"stocks": round(stock_value + adj["stocks"]), "options": round(opt_base + adj["options"]), "cash": round(snap["cash_inr"] + adj["cash"])}
    pool = sum(sleeves.values())
    tg = targets(r, trend, sessions, fired)
    opts = rate_options(rm, r, sleeves["options"])
    dt_ = rm.get("decisions_today")
    chosen = (dt_.get("chosen") if isinstance(dt_, dict) else dt_) or []
    # the evidence staircase (india/reconstruct.py): the allocated capital may buy a fresh signal only from an ADMITTED family; nothing is admitted until Madhav's recorded yes
    try:
        from india import reconstruct
        adm = reconstruct.admitted()
    except Exception:  # noqa: BLE001
        adm = set()
    cands = [{"symbol": d.get("symbol"), "campaign": d.get("campaign")} for d in chosen if isinstance(d, dict) and d.get("symbol") and d.get("campaign") not in (None, "CTL") and f"stock:{d.get('campaign')}" in adm]
    moves = _moves(sleeves, tg, ratings, cands, r, fired)
    applied = cfg["mode"] == "autonomous"
    adj_today = {"stocks": 0.0, "options": 0.0, "cash": 0.0}
    if applied:
        for m in moves:
            adj_today[m["from"]] -= m["inr"]
            adj_today[m["to"]] += m["inr"]
    after = {k: round(sleeves[k] + adj_today[k]) for k in sleeves}
    stale = None
    if snap.get("taken_at"):
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(snap["taken_at"])).days
        stale = age if age >= 2 else None

    def pct(v):
        return round(100 * v / pool, 1) if pool else 0.0

    suggestions = [x for x in ratings if x["action"] not in ("HOLD", "WATCH")]
    regime = {"below_both": "in a downtrend", "above_both": "in an uptrend", "mixed": "with no clear trend"}.get(trend, "")
    if cfg["mode"] == "advisory":
        headline = (f"Advisory: Ananta only suggests. Options are fixed at ₹{opt_base:,.0f}; your stocks stay as they are (₹{sleeves['stocks']:,.0f}). "
                    f"{len(suggestions)} of your {len(ratings)} holdings have a suggested change. {regime.capitalize()}, it would keep options at or under {100 * tg['options']:.0f}% of your money; they are {pct(sleeves['options']):.0f}%.")
    else:
        moved = ", ".join(f"₹{m['inr']:,.0f} {m['from']} → {m['to']}" + (f" ({m['symbol']})" if m.get("symbol") else "") for m in moves)
        headline = (f"Ananta manages the split on paper. {regime.capitalize()}, it keeps options at or under {100 * tg['options']:.0f}% and at least {100 * tg['cash_min']:.0f}% in cash. "
                    + (f"Today it moved {moved}." if moves else "Nothing to move today: every part is within its band."))
    view = {"rules": r["version"], "day": day, "for_session": rm.get("next_session"), "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "mode": cfg["mode"], "paper": True, "headline": headline,
            "sleeves": {"now": sleeves, "now_pct": {k: pct(v) for k, v in sleeves.items()}, "after": after, "after_pct": {k: pct(v) for k, v in after.items()}, "pool_inr": pool,
                        "target_pct": {"options_max": round(100 * tg["options"], 1), "cash_min": round(100 * tg["cash_min"], 1), "stocks": round(100 * tg["stocks"], 1)}},
            "regime": tg, "options": opts, "holdings": ratings,
            "suggestions": [{"symbol": x["symbol"], "action": x["action"], "grade": x["grade"], "why": x["why"], "wrong_if": x["wrong_if"], "value_inr": x["value_inr"], "suggest_inr": x["suggest_inr"]} for x in suggestions],
            "moves": moves, "moves_applied": applied, "watch": watch(rm, ratings, snap, trend),
            "snapshot": {"status": snap["status"], "taken_at": snap.get("taken_at"), "stale_days": stale, "holdings": len(hs), "cash_inr": snap["cash_inr"]},
            "yardstick": "Ananta's research book keeps trading every rule at research size in the background; it is the yardstick and nothing here changes it.",
            "words": "Paper only: no order goes to your broker. A suggestion is advice; a move happens on the paper copy of your account; real trades wait for the gate and your yes.",
            "sources": {"readmodel": str(paths.data_dir() / "readmodel" / "latest.json"), "account_snapshot": snap.get("source"), "universe": uni_day, "rule": str(RULE_FILE)}}
    return view | {"_applied_adj": adj_today}


def run(day: str | None = None) -> dict:
    v = build(day)
    paper = _paper()
    paper.mkdir(parents=True, exist_ok=True)
    adj = v.pop("_applied_adj")
    row = {"day": v["day"], "for_session": v["for_session"], "mode": v["mode"], "rules": v["rules"], "built_at": v["built_at"], "sleeves_now": v["sleeves"]["now"],
           "sleeves_after": v["sleeves"]["after"], "target_pct": v["sleeves"]["target_pct"], "moves": v["moves"], "applied_adj": adj, "regime": v["regime"]["regime"],
           "grades": {x["symbol"]: [x["grade"], x["score"], x["action"]] for x in v["holdings"]}, "score_at": ["+1 session", "+5 sessions", "+20 sessions"]}
    rows = [x for x in _jsonl(paper / "allocation_ledger.jsonl") if x.get("day") != v["day"]] + [row]
    rows.sort(key=lambda x: x["day"])
    (paper / "allocation_ledger.jsonl").write_text("\n".join(json.dumps(x) for x in rows) + "\n")
    (paper / "allocation_view.json").write_text(json.dumps(v, indent=1))
    try:                                   # the account book (india/account.py) applies the final days' paper moves and marks the twin
        from india import account as acct
        v["account_book"] = acct.run().get("words")
    except Exception as e:  # noqa: BLE001
        v["account_book"] = f"the account book could not run: {e.__class__.__name__}: {str(e)[:100]}"
    return v


def show() -> None:
    v = _load(_paper() / "allocation_view.json", {}) or {}
    if not v:
        print("no allocation view yet: run `python -m india.allocator run`")
        return
    print(v["headline"])
    print("sleeves now", v["sleeves"]["now"], "after", v["sleeves"]["after"])
    for x in v["holdings"]:
        print(f"{x['rank']:>2} {x['symbol']:<12} {x['grade']} {x['score']:>5}  {x['action']:<7} ₹{x['value_inr']:>7,} {x['weight_pct']:>5}%  {x['why'][:90]}")
    for m in v["moves"]:
        print("MOVE", m)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "run":
        run(sys.argv[2] if len(sys.argv) > 2 else None)
        show()
    else:
        show()
