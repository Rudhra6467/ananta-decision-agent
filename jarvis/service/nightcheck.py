"""The night test (Madhav, 10 Nov 2026: "What is other best way to test Ananta other than I use voice agent ... it cost me something" ...
"yes, lets build it").

Every night, after the officer's note, Ananta is asked a short list of questions the same way the app asks them (test mode: it reads
everything and saves nothing) and every answer is marked. Madhav no longer has to be the tester.

  the bank      docs/knowledge/nightcheck_crypto.json: one list of questions; each says how it is marked
  code marks    free: the answer is checked against the $500 book, the dial and the rule files as they stand (truth)
  the grader    the smallest Claude model, only for answers code cannot judge; it is given the same truth and the question's own rubric
  the look list money and percent figures in an answer that are in nothing Ananta read for it (not counted as wrong; a person looks)
  the budget    NIGHTCHECK_BUDGET_USD a night (answers plus grader); the run stops there and says so
  the rotation  core questions every night; the rest about once in two weeks; a question that failed is asked every night until it has
                passed FIXED_AFTER nights in a row

  python scripts/run_nightcheck.py            the night's run (started by universe_watch.run_daily after the note)
Writes docs/repair_shop/nightcheck/crypto_latest.json, crypto_<day>.json, crypto_history.jsonl and crypto_state.json.
Paper only: nothing here reads the broker or writes an order."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANK = ROOT / "docs" / "knowledge" / "nightcheck_crypto.json"
OUT = ROOT / "docs" / "repair_shop" / "nightcheck"
BUDGET_USD = float(os.getenv("NIGHTCHECK_BUDGET_USD", "0.40"))
GRADER = os.getenv("NIGHTCHECK_GRADER", "haiku")
WEEK = 14                 # the rest of the bank comes round once in this many nights
FIXED_AFTER = 3
NO = r"\bno\b|\bnot\b|n't\b|\bnever\b|\bcannot\b|\bonly buys?\b|\bnone\b"


# ---------------------------------------------------------------- the truth, by code
def truth(j) -> dict:
    """What is true right now, read by code from the book, the dial and the rule files. The code marks and the grader both use it."""
    from jarvis.service import discipline, exposure, feed, ndax_book, officer, strategy_status, surfaces
    from src.research import book500 as B

    try:
        live = float((feed.prices(j) or {}).get("BTC") or 0) or None
    except Exception:  # noqa: BLE001
        live = None

    s = ndax_book.status(j)
    closed = (ndax_book._get(j, "state") or {}).get("closed") or []
    d = exposure.state(j)
    n = surfaces._dial_numbers(d)
    value, cash = float(s.get("value_cad") or 0), float(s.get("cash_cad") or 0)
    close, a50, a200 = n.get("close"), n.get("avg50"), n.get("avg200")
    since = time.time() - 14 * 86400
    reg = strategy_status.load().get("strategies") or {}
    core = discipline.rules().get("core") or {}
    return {"paper_only": True, "start_cad": B.START_CAD, "value_cad": round(value, 2), "cash_cad": round(cash, 2), "coins_cad": round(value - cash, 2),
            "return_pct": float(s.get("return_pct") or 0), "holdings": sorted(s.get("positions") or {}),
            "closed_trades": len(closed), "closed_won": sum(1 for c in closed if (c.get("pnl_cad") or 0) > 0),
            "dial_open": (d.get("dial") or 0) > 0, "candle_day": d.get("as_of_day"), "btc_close": close, "avg50": a50, "avg200": a200,
            "btc_live": live, "btc_live_vs_avg50_pct": round(100 * (live / a50 - 1), 1) if live and a50 else None,
            "btc_live_vs_avg200_pct": round(100 * (live / a200 - 1), 1) if live and a200 else None,
            "btc_vs_avg50_pct": round(100 * (close / a50 - 1), 1) if close and a50 else None,
            "btc_vs_avg200_pct": round(100 * (close / a200 - 1), 1) if close and a200 else None,
            "core_mode": str(core.get("mode") or "thirds"), "core_weights_pct": {c: round(100 * w) for c, w in B.CORE.items()},
            "core_rule": "all_in: the whole core is bought at once when the dial opens and all of it sold when the dial closes; no thirds, no trims"
                         if core.get("mode") == "all_in" else "thirds: bought in three steps (core-v2 of 24 Oct)",
            "safety_stops_pct": {k: round(100 * float(B.BRAKES[k]), 1) for k in ("day_loss", "week_loss", "fall_from_peak")},
            "strategies": {k: v.get("status") for k, v in reg.items()},
            "short_dip_rule": {"big_coins": (reg.get("H07") or {}).get("status"), "small_coins": (reg.get("H07_SMALL") or {}).get("status"),
                               "words": "EVIDENCE = paper record only: it never trades for the $500 account"},
            "reviews": {"39": "FAIL: buying the core in thirds did not beat all-in for 2024-2026", "40": "FAIL: waiting two closes cut too few entries"},
            "window_day": surfaces._window()["day"], "window_of": surfaces.WINDOW_DAYS, "round_trips_needed": 50,
            "clean_nights": officer.clean_nights(j),
            "repairs": (s.get("repairs") or [])[-2:],
            "fills_last_14_days": [{"day": time.strftime("%Y-%m-%d", time.gmtime(f["t"])), "side": f["side"], "coin": f["coin"],
                                    "cad": round((f.get("qty") or 0) * (f.get("px") or 0), 2)}
                                   for f in (s.get("recent_fills") or []) if (f.get("t") or 0) >= since],
            "open_list": _open_counts(j),
            "cannot": "the book never sells short and never places a real order; it buys or it holds cash"}


def _open_counts(j) -> dict:
    try:
        from jarvis.service import openlist

        d = openlist.collect(j)
        return {"line": d["line"], "needs_your_yes": d["counts"]["YOU"], "work_to_do": d["counts"]["WORK"], "names": [str(x["id"]) for x in d["you"]][:8]}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)[:120]}


# ---------------------------------------------------------------- code marks
def _x():
    from jarvis.service import exam

    return exam


def _has_n(text: str, n: int) -> bool:
    """The whole number n is said, as a figure or a word ("0", "zero", "none")."""
    X = _x()
    words = [w for w, v in X._WORDS.items() if v == n]
    return bool(re.search(r"(?<![\w.,])" + str(n) + r"(?![\w,]|\.\d)", text or "")) or any(re.search(rf"\b{w}\b", text or "", re.I) for w in words)


def _thirds_said_as_now(text: str) -> bool:
    for sent in re.split(r"(?<=[.!?])\s+", text or ""):
        if re.search(r"\bthirds?\b|\bthree steps\b|\btranche", sent, re.I) and not re.search(
                NO + r"|\bwas\b|\bwere\b|\bused to\b|\bold\b|\bearlier\b|\bbefore\b|\buntil\b|switched off|\boff\b|fail|replac|instead|no longer|back to|stopped", sent, re.I):
            return True
    return False


def _m_value(t, T):
    return _x()._near(t, T["value_cad"], max(1.0, 0.01 * T["value_cad"]))


def _m_cash(t, T):
    X, v, c = _x(), T["value_cad"], T["cash_cad"]
    coins = v - c
    return X._near(t, c, max(1.0, 0.01 * c)) and (X._near(t, coins, max(1.0, 0.01 * v)) or (
        coins < 0.5 and bool(re.search(r"\bno coins\b|\bnothing\b|\bnone\b|\ball (?:of it )?(?:is )?(?:in )?cash\b|\bzero\b", t, re.I))))


def _m_return(t, T):
    ret = T["return_pct"]
    way = r"\bdown\b|\bloss\b|\blost\b|\bminus\b|\bnegative\b|[-−]\s?\d" if ret < 0 else r"\bup\b|\bgain|\bplus\b|\bpositive\b|\+\s?\d"
    return _x()._near(t, ret, 0.3) and bool(re.search(way, t, re.I))


def _m_closed(t, T):
    X = _x()
    return X._count_before(t, T["closed_trades"], r"trades?|closed|round trips?") and X._count_before(
        t, T["closed_won"], r"won|wins?|winners?|made money|were profitable|profitable|in profit")


def _m_dial_close(t, T):
    c = T.get("btc_close")
    words = r"dial\W+(?:\w+\W+){0,4}?open|buying is on" if T["dial_open"] else r"dial\W+(?:\w+\W+){0,4}?closed|buying is off|no new buys"
    return bool(c) and _x()._near(t, c, 0.005 * c) and bool(re.search(words, t, re.I))


def _m_holdings(t, T):
    from jarvis.service import surfaces

    held = T["holdings"]
    if not held:
        return bool(re.search(r"\bno coins?\b|\bnothing\b|\bnone\b|\ball (?:of it |of the book )?(?:is |sits )?(?:in )?cash\b|\bholds? no\b|\bnot holding\b|"
                              r"\bno (?:open )?(?:positions?|holdings?)\b|\bfully in cash\b|\bentirely in cash\b|\b100\s?% cash\b|\bin cash\b", t, re.I))
    return all(re.search(rf"\b{c}\b|\b{surfaces.COIN_NAME.get(c, c)}\b", t, re.I) for c in held)


def _m_core_rule(t, T):
    w = T["core_weights_pct"]
    ok = all(re.search(rf"(?<!\d){p}\s?%|(?<!\d){p} per ?cent", t, re.I) for p in w.values()) and bool(re.search(r"bitcoin|\bBTC\b", t, re.I)) and bool(
        re.search(r"ether|\bETH\b", t, re.I))
    return ok and not (T["core_mode"] == "all_in" and _thirds_said_as_now(t))


def _m_reopen(t, T):
    X = _x()
    if T["dial_open"]:
        return bool(re.search(r"\bopen\b|buying is on|already on", t, re.I))
    need = [a for a, pct in ((T.get("avg50"), T.get("btc_vs_avg50_pct")), (T.get("avg200"), T.get("btc_vs_avg200_pct"))) if a and pct is not None and pct < 0]
    return bool(re.search(r"50.day", t, re.I)) and bool(re.search(r"200.day", t, re.I)) and all(X._near(t, a, 0.006 * a) for a in need)


def _m_short(t, T):
    return bool(re.search(NO, t, re.I)) and not re.match(r"\W*yes\b", t or "", re.I)


def _m_orders(t, T):
    return bool(re.search(r"\bpaper\b|simulat|practice|no real|not real|never plac|does(?: not|n't) place|do(?: not|n't) place|cannot place|can't place", t, re.I)) \
        and not re.match(r"\W*yes\b", t or "", re.I)


def _m_short_dip(t, T):
    """Asked whether the short-dip rule buys for the account: the answer is no (10 Nov road test: a right "No, it isn't buying for your $500
    account" failed while this also asked for the word "paper")."""
    first = re.split(r"(?<=[.!?])\s+", (t or "").strip())
    first = " ".join(first[:2]) if re.match(r"\W*(good )?(morning|afternoon|evening|hello|hi)\b", first[0] if first else "", re.I) else (first[0] if first else "")
    return bool(re.search(NO, first, re.I)) and not re.search(r"\byes\b", first, re.I)


def _m_review39(t, T):
    return bool(re.search(r"\bfail|did(?: not|n't) pass|not pass|didn't beat|did not beat|\bworse\b", t, re.I)) and not re.match(r"\W*(yes|right|correct)\b", t or "", re.I)


def _m_unknown(t, T):
    return _x().judge_unknown(t)


def _m_clean(t, T):
    cn = T.get("clean_nights") or {}
    return _has_n(t, int(cn.get("in_a_row") or 0)) and _has_n(t, int(cn.get("need") or 30))


def _m_window(t, T):
    return _has_n(t, int(T["window_day"])) and _has_n(t, int(T["window_of"]))


def _m_round_trips(t, T):
    return _has_n(t, int(T["closed_trades"])) and _has_n(t, int(T["round_trips_needed"]))


def _m_stops(t, T):
    return all(re.search(rf"(?<![\d.]){v:g}\s?%|(?<![\d.]){v:g} per ?cent", t, re.I) for v in T["safety_stops_pct"].values())


def _m_open_yes(t, T):
    """How many things wait for his yes, as the open list counts them (or that nothing does)."""
    n = int((T.get("open_list") or {}).get("needs_your_yes") or 0)
    if n == 0:
        return bool(re.search(r"\bnothing\b|\bnone\b|\bno (?:items?|things?|decisions?)\b|\bzero\b|isn't anything|is not anything", t, re.I))
    return _has_n(t, n)


MARKS = {"open_yes": (_m_open_yes, lambda T: f"{(T.get('open_list') or {}).get('needs_your_yes', 0)} waiting for your yes"),
         "value": (_m_value, lambda T: f"C${T['value_cad']:.2f}"),
         "cash": (_m_cash, lambda T: f"C${T['cash_cad']:.2f} cash, C${T['coins_cad']:.2f} in coins"),
         "return": (_m_return, lambda T: f"{T['return_pct']:+.1f}%"),
         "closed": (_m_closed, lambda T: f"{T['closed_trades']} closed, {T['closed_won']} made money"),
         "dial_close": (_m_dial_close, lambda T: f"{T.get('btc_close')}, buying {'on' if T['dial_open'] else 'off'}"),
         "holdings": (_m_holdings, lambda T: ", ".join(T["holdings"]) or "no coins, all cash"),
         "core_rule": (_m_core_rule, lambda T: f"{T['core_weights_pct']}, {T['core_mode']}"),
         "reopen": (_m_reopen, lambda T: f"a close above the 50-day ({T.get('avg50')}) and the 200-day ({T.get('avg200')})"),
         "short": (_m_short, lambda T: "no: it only buys or holds cash"),
         "orders": (_m_orders, lambda T: "no: paper only"),
         "short_dip": (_m_short_dip, lambda T: "no: a paper record only, big coins"),
         "review39": (_m_review39, lambda T: "review 39 FAILED; the core is all-in"),
         "unknown": (_m_unknown, lambda T: "says it cannot know"),
         "clean": (_m_clean, lambda T: f"{(T.get('clean_nights') or {}).get('in_a_row', 0)} of {(T.get('clean_nights') or {}).get('need', 30)}"),
         "window": (_m_window, lambda T: f"day {T['window_day']} of {T['window_of']}"),
         "round_trips": (_m_round_trips, lambda T: f"{T['closed_trades']} of {T['round_trips_needed']}"),
         "stops": (_m_stops, lambda T: str(T["safety_stops_pct"]))}


# ---------------------------------------------------------------- the look list: figures that are in nothing Ananta read
_FIG = r"\d[\d,]*(?:\.\d+)?"


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def money_and_percent(text: str) -> list[tuple[str, float, int]]:
    """The money amounts and percentages an answer states: (as written, value, decimals written). Dates, counts and day-averages are left out."""
    out = []
    for m in re.finditer(rf"(?:C\$|US\$|\$)\s?({_FIG})(?!\s?-?day)|({_FIG})\s?(?:%|per ?cent\b)", text or ""):
        raw = m.group(1) or m.group(2)
        try:
            out.append((m.group(0).strip(), _num(raw), len(raw.split(".")[1]) if "." in raw else 0))
        except ValueError:
            continue
    return out


def unsourced(answer: str, evidence: str, T: dict | None = None) -> list[str]:
    """Money and percent figures in the answer that match nothing Ananta read for it: not its lookups, not its brief, not the question, not the
    book (nor a plain difference or share of the book's own figures). A figure matches when it is the same once rounded as the answer wrote it,
    or within 0.6%. This is a list for a person to look at, not a verdict: a fair sum of two figures also lands here."""
    have = set()
    for x in re.findall(r"(?<![\w])" + _FIG, evidence or ""):
        try:
            have.add(abs(_num(x)))
        except ValueError:
            pass
    key = [float(v) for v in ((T or {}).get(k) for k in ("start_cad", "value_cad", "cash_cad", "coins_cad", "btc_close", "btc_live", "avg50", "avg200")) if v]
    have |= set(key)
    for a in key:
        for b in key:
            if a > b:
                have.add(a - b)
                have.add(100 * (a / b - 1))
                have.add(100 * (1 - b / a))
                have.add(100 * b / a)
    have |= {0.0, 100.0}
    miss = []
    for raw, v, dec in money_and_percent(answer):
        if not any(abs(v - h) <= max(0.5 * 10 ** -dec, 0.006 * abs(h)) for h in have):
            miss.append(raw)
    return list(dict.fromkeys(miss))


# ---------------------------------------------------------------- the grader (the smallest Claude model)
GRADER_RULES = """You mark one answer from Ananta, a paper-trading assistant for crypto, given to its owner Madhav. You are given the QUESTION, the TRUTH
(read by code from the book and the rule files a moment ago; it is correct but NOT complete), the RUBRIC for this question, and the ANSWER.

Mark the answer WRONG only if one of these holds:
1. It breaks the RUBRIC: a "must" is missing, or a "must not" happens.
2. A figure in it CONTRADICTS a figure in the TRUTH that measures the same thing.
3. It says or implies a real order was or will be placed (everything is paper), or promises a price or a profit.
Otherwise mark it RIGHT.

How to read figures:
- Rounding is never a contradiction. "about C$468" agrees with 467.55. "down 6.5%" agrees with -6.49. "about 75,400" agrees with 75368.
  "about C$28" agrees with 28.06. Treat any figure within 1% of the TRUTH, or equal to it once rounded as the answer wrote it, as agreeing.
- The TRUTH is not complete. Ananta reads far more than you are shown. A fact, trade, price or figure that is simply NOT IN the TRUTH is not
  wrong and must not be marked down: you cannot check it. Only a figure that the TRUTH states differently is a contradiction.
- A live price and a daily close are different things; an answer may use either when the TRUTH carries both.
- Do not mark down for style, greeting, length, extra detail or an offer to say more, unless the RUBRIC asks.
When you are not sure, mark it RIGHT.

Reply with one JSON object and nothing else: {"ok": true or false, "why": "one short plain sentence naming the rubric line broken or the figure contradicted"}"""


def grade(q: dict, T: dict, answer: str, post=None) -> dict:
    from jarvis.service import ask, brain

    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key and post is None:
        return {"ok": None, "why": "no Claude key for the grader", "cost_usd": 0.0}
    m = ask.MODELS[GRADER]
    user = ("QUESTION:\n" + q["q"] + "\n\nTRUTH (JSON):\n" + json.dumps(T, default=str, ensure_ascii=False)[:9000] + "\n\nRUBRIC:\n"
            + "\n".join(f"- must: {x}" for x in q.get("must") or []) + "\n" + "\n".join(f"- must not: {x}" for x in q.get("must_not") or [])
            + "\n\nANSWER:\n" + (answer or "")[:6000])
    try:
        r = (post or ask._post)("https://api.anthropic.com/v1/messages",
                                {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                                {"model": m["model"], "max_tokens": 300, "system": GRADER_RULES, "messages": [{"role": "user", "content": user}]})
    except Exception as exc:  # noqa: BLE001
        return {"ok": None, "why": f"the grader could not be reached: {str(exc)[:120]}", "cost_usd": 0.0}
    u = r.get("usage") or {}
    cost = ask.cost_usd(GRADER, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0) or 0,
                                 "cache_write": u.get("cache_creation_input_tokens", 0) or 0})
    text = "".join(c.get("text", "") for c in r.get("content") or [] if c.get("type") == "text")
    try:
        d = json.loads(brain._json_block(text) or "")
        return {"ok": bool(d["ok"]) if isinstance(d.get("ok"), bool) else None, "why": str(d.get("why") or "")[:300], "cost_usd": cost}
    except (ValueError, KeyError, TypeError):
        return {"ok": None, "why": "the grader's reply could not be read", "cost_usd": cost}


# ---------------------------------------------------------------- the bank, the rotation, the run
def bank() -> list[dict]:
    return (json.loads(BANK.read_text()).get("questions") or []) if BANK.exists() else []


def _state() -> dict:
    p = OUT / "crypto_state.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def due(qs: list[dict], day: str, state: dict) -> list[dict]:
    """Tonight's questions: the core ones, the night's share of the rest (each once in WEEK nights), and every question that failed and has
    not yet passed FIXED_AFTER nights in a row."""
    n = dt.date.fromisoformat(day).toordinal()
    out, k = [], 0
    for q in qs:
        st = state.get(q["id"]) or {}
        watch = st.get("failed") and int(st.get("streak") or 0) < FIXED_AFTER
        if q.get("core"):
            out.append(q)
            continue
        if watch or (n + k) % WEEK == 0:
            out.append(q)
        k += 1
    return out


def mark(q: dict, T: dict, answer: str, post=None) -> dict:
    how = str(q.get("mark") or "grader")
    if how.startswith("code:"):                      # one paid answer may carry several marks: "code:value+cash+return"
        names = how.split(":", 1)[1].split("+")
        missed = [n for n in names if not MARKS[n][0](answer or "", T)]
        out = {"ok": not missed, "want": "; ".join(MARKS[n][1](T) for n in names), "by": "code", "cost_usd": 0.0, "marks": len(names)}
        if missed:
            out["why"] = "wrong or missing: " + "; ".join(f"{n.replace('_', ' ')} (wanted {MARKS[n][1](T)})" for n in missed)
        return out
    g = grade(q, T, answer, post=post)
    return {"ok": g["ok"], "why": g.get("why"), "by": "grader", "cost_usd": g.get("cost_usd") or 0.0}


def line(out: dict) -> str:
    """The one plain line for the Today screen and the phone."""
    if not out.get("asked"):
        return "Night test: no question was asked" + (f" ({out['error']})" if out.get("error") else "") + "."
    s = f"Night test: {out['right']} of {out['asked']} answers right"
    wrong = out.get("wrong") or []
    if wrong:
        s += ". Wrong: " + "; ".join(w["name"] for w in wrong[:4]) + (f" and {len(wrong) - 4} more" if len(wrong) > 4 else "")
    if out.get("ungraded"):
        s += f". {out['ungraded']} could not be marked"
    if out.get("stopped_for_budget"):
        s += f". Stopped at the night's budget (${out['budget_usd']:.2f}) with {out['not_asked']} not asked"
    return s + "."


def run(j, ask=None, post=None, day: str | None = None, budget: float | None = None, only: list[str] | None = None, save: bool = True,
        file_flags: bool = True) -> dict:
    """Ask tonight's questions, mark each, keep the result. `ask` and `post` are stand-ins for tests; `only` asks just those ids."""
    from jarvis.service import ask as askmod

    X = _x()
    t0 = time.time()
    day = day or time.strftime("%Y-%m-%d", time.gmtime())
    budget = BUDGET_USD if budget is None else budget
    state = _state() if save else {}
    qs = bank()
    todo = [q for q in qs if q["id"] in only] if only else due(qs, day, state)
    out = {"market": "crypto", "day": day, "t": int(t0), "budget_usd": budget, "asked": 0, "right": 0, "wrong": [], "look": [], "ungraded": 0,
           "cost_usd": 0.0, "cost_answers_usd": 0.0, "cost_grader_usd": 0.0, "stopped_for_budget": False, "not_asked": 0, "rows": [], "grader": GRADER}
    try:
        T = truth(j)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"the book could not be read: {str(exc)[:160]}"
        todo, T = [], {}
    a = ask or (askmod.Ask(j) if todo else None)
    for k, q in enumerate(todo):
        if out["cost_usd"] >= budget:
            out["stopped_for_budget"], out["not_asked"] = True, len(todo) - k
            break
        askmod.EVIDENCE.clear()
        r = X._ask(a, q["q"], 700 + k)
        txt = str(r.get("answer") or "")
        c_ans = float(r.get("cost_usd") or 0)
        row = {"id": q["id"], "name": q.get("name") or q["id"], "question": q["q"], "answer": txt[:1500], "cost_usd": round(c_ans, 5)}
        if r.get("error") or not txt:
            row.update(ok=None, by="none", why=f"no answer: {str(r.get('error') or 'empty')[:160]}")
        else:
            m = mark(q, T, txt, post=post)
            row.update({k2: v for k2, v in m.items() if k2 != "cost_usd"})
            out["cost_grader_usd"] += m["cost_usd"]
            miss = unsourced(txt, q["q"] + " " + json.dumps(T, default=str) + " " + " ".join(askmod.EVIDENCE), T)
            if re.search(r"\bflag", txt, re.I) and not re.search(r"\bflag", q["q"], re.I):
                miss.append("talks about a flag nobody asked for")       # 10 Nov: test answers kept mentioning a flag they tried to file
            if miss:
                row["look"] = miss[:8]
                out["look"].append({"id": q["id"], "name": row["name"], "figures": miss[:8]})
        out["cost_answers_usd"] += c_ans
        out["cost_usd"] = round(out["cost_answers_usd"] + out["cost_grader_usd"], 5)
        out["asked"] += 1
        if row["ok"] is True:
            out["right"] += 1
        elif row["ok"] is False:
            out["wrong"].append({"id": q["id"], "name": row["name"], "question": q["q"], "why": row.get("why") or f"wanted {row.get('want')}", "answer": txt[:500]})
        else:
            out["ungraded"] += 1
        out["rows"].append(row)
        st = state.setdefault(q["id"], {})
        if row["ok"] is not None:
            st.update(last=day, last_ok=row["ok"], streak=(int(st.get("streak") or 0) + 1) if row["ok"] else 0)
            if not row["ok"]:
                st.update(failed=True, first_failed=st.get("first_failed") or day)
            elif st.get("failed") and st["streak"] >= FIXED_AFTER:
                st.update(failed=False, fixed_on=day)
    askmod.EVIDENCE.clear()
    for k2 in ("cost_usd", "cost_answers_usd", "cost_grader_usd"):
        out[k2] = round(out[k2], 4)
    out["minutes"] = round((time.time() - t0) / 60, 1)
    out["line"] = line(out)
    if save:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "crypto_latest.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        (OUT / f"crypto_{day}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        (OUT / "crypto_state.json").write_text(json.dumps(state, indent=1, ensure_ascii=False))
        with (OUT / "crypto_history.jsonl").open("a") as f:
            f.write(json.dumps({k2: out[k2] for k2 in ("day", "t", "asked", "right", "ungraded", "cost_usd", "cost_answers_usd", "cost_grader_usd",
                                                         "stopped_for_budget", "not_asked", "minutes")}
                               | {"wrong": [w["id"] for w in out["wrong"]], "look": len(out["look"])}) + "\n")
    if file_flags and out["wrong"]:
        try:
            out["filed"] = file_wrong(j, out["wrong"])
        except Exception as exc:  # noqa: BLE001
            out["filed_error"] = str(exc)[:160]
    return out


def file_wrong(j, wrong: list[dict]) -> list[int]:
    """A wrong answer becomes a repair-board request, once a week per question (as the officer's failed checks are)."""
    from jarvis.service import fixflow, requests_log

    nums = []
    week = time.strftime("%Y-W%W", time.gmtime(j.now()))
    requests_log._table(j)
    for w in wrong:
        key = f"nightcheck:{w['id']}:{week}"
        if j.db.execute("SELECT 1 FROM owner_requests WHERE about=?", (key,)).fetchone():
            continue
        r = fixflow.flag(j, f"Night test: Ananta answered '{w['question'][:140]}' wrongly ({str(w.get('why'))[:160]})", market="crypto", screen="night test",
                         use_ai=False, topic=f"nightcheck:{w['id']}", waits="WORK")
        if r.get("joined"):                                   # still wrong on a later night: the same item, seen again
            continue
        j.db.execute("UPDATE owner_requests SET about=? WHERE num=?", (key, r["num"]))
        j.db.commit()
        nums.append(r["num"])
    return nums


def latest() -> dict | None:
    try:
        return json.loads((OUT / "crypto_latest.json").read_text())
    except (OSError, ValueError):
        return None
