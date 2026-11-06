"""The crypto reconstruction loop, RX-CR v1 (Madhav, 24 Oct 2026, "Yes to all", discipline item 9; the India loop RX-IN is the model).

Madhav: "it sees around the net, sees what people are doing, notes everything, sees what Ananta did and did not do, and based on
findings forwards things to the repair shop". Crypto logged everything and learned nothing (the 7-day review): this turns the logs into
one card a night with typed findings, each with a fixed rule, a lane decided by code and a place it goes.

  evening(j)   once per UTC day after the daily close (universe_watch.run_daily): the card, the findings, the forwarding
  latest(j)    the newest card, for the app and Ask
  queue(j)     the DECISION rows waiting for Madhav, and what he decided
  decide(j, id, words)   Madhav's word on a queue row (yes / no / later), recorded with the time

THE CARD (rx_cards, one per UTC day, never rewritten)
  A market     Bitcoin's close, the dial's state (CLOSED / FRAGILE / CONFIRMED), the day's biggest moves (caught / seen / missed)
  B ananta     what it did: the brain's decisions (with what each PASS waits for), the bold book, the account's fills, the books
  C not_done   what it did not do: the missed moves, the wait_for conditions that arrived, the TAKEs the floor turned into a PASS
  D reviews    every trade reviewed today, by tag (reviews.py: GAVE_BACK, NEVER_WORKED, COSTS_ATE ...)
  E findings   typed rows (BARS), each with its evidence and its lane
  F forwarding SAFE rows to the repair board (fixflow), DECISION rows to the queue for Madhav, NOTE rows kept on the card
Paper only. Nothing here reads the broker or writes a trade; it only wakes the brain again for a wait_for that arrived (item 6).
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import time
import uuid

DAY = 86400
RULES = "rx-cr-v2-2026-11-06"   # v2 (Madhav's yes, 6 Nov 2026, the reconstruction audit E2/E3/E5): Rule B answers new-family questions, wakes are a count, the card measures its value
BARS = {"gave_back_n": 3, "gave_back_days": 7, "miss_pattern_n": 3, "miss_pattern_days": 30, "bleed_pct": 0.02, "bleed_days": 7,
        "bleed_min_closed": 5, "selection_n": 1, "safe_per_night": 3}
KIND_WORDS = {"GAVE_BACK": "winners that became losers (no plan protected them)", "MISS_PATTERN": "a kind of move we keep missing",
              "BOOK_BLEED": "a book losing more than its bar over a week", "LAYER_CONFLICT": "two layers wanting different things",
              "SELECTION": "a buy the selection floor refused", "WAIT_ARRIVED": "a pass whose condition came true"}
REPO = Path(__file__).resolve().parents[2]
RULE_B_ENDS = "2026-12-14"      # Rule B (15 Oct lock): no new crypto families before the day-60 checkpoint
LANE = {"GAVE_BACK": "SAFE", "MISS_PATTERN": "DECISION", "BOOK_BLEED": "DECISION", "LAYER_CONFLICT": "NOTE", "SELECTION": "NOTE",
        "WAIT_ARRIVED": "SAFE"}


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS rx_cards (day TEXT PRIMARY KEY, t INTEGER, rules TEXT, card TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS rx_queue (id TEXT PRIMARY KEY, day TEXT, t INTEGER, kind TEXT, lane TEXT, key TEXT, words TEXT, "
                 "evidence TEXT, state TEXT, decided_t INTEGER, decision TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")


def _day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


# ------------------------------------------------------------------------------------------------------------------------- sections

def section_market(j, day0: int) -> dict:
    from jarvis.service import discipline, feed, universe_watch

    out: dict = {}
    try:
        btc = feed.daily(j, "BTC")
        if btc:
            closes = [b[4] for b in btc]
            out["btc_close"] = closes[-1]
            out["btc_day_pct"] = round(100 * (closes[-1] / closes[-2] - 1), 2) if len(closes) > 1 else None
            out["dial_state"] = discipline.dial_state(closes)
            out["dial_words"] = discipline.STATE_WORDS.get(out["dial_state"] or "", "the dial could not be read")
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:120]
    try:
        mv = universe_watch.missed(j, day0 - DAY)
        out["movers"] = [{"coin": m.get("coin"), "label": m.get("label"), "pct": m.get("pct") or m.get("move_pct"), "tier": m.get("tier")} for m in (mv or [])[:8]]
    except Exception as exc:  # noqa: BLE001
        out["movers_error"] = str(exc)[:120]
    return out


def section_ananta(j, day0: int) -> dict:
    from jarvis.service import discipline, ndax_book

    out: dict = {}
    try:
        rows = j.db.execute("SELECT id, coin, action, confidence, plan, note FROM brain_decisions WHERE t >= ? AND t < ? ORDER BY t", (day0, day0 + DAY)).fetchall()
        dec = []
        for did, coin, action, conf, plan, note in rows:
            w = discipline._wait_for(plan)
            dec.append({"id": did, "coin": coin, "action": action, "confidence": conf, "wait_for": (w or {}).get("words") if w else None,
                        "floor": "selection floor" in (note or "")})
        out["brain"] = {"n": len(dec), "by_action": {a: sum(1 for d in dec if d["action"] == a) for a in {d["action"] for d in dec}}, "decisions": dec[:30]}
    except Exception as exc:  # noqa: BLE001
        out["brain_error"] = str(exc)[:120]
    try:
        r = j.db.execute("SELECT action, coin, stop, note FROM bold_decisions WHERE day=? ORDER BY t DESC LIMIT 1", (_day(day0),)).fetchone()
        out["bold"] = {"action": r[0], "coin": r[1], "stop": r[2], "note": r[3]} if r else None
    except Exception:  # noqa: BLE001
        out["bold"] = None
    try:
        s = ndax_book._get(j, "state") or {}
        fills = j.db.execute("SELECT coin, side, sleeve, qty, px, why FROM book500_fills WHERE t >= ? AND t < ? ORDER BY t", (day0, day0 + DAY)).fetchall()
        out["account"] = {"value_cad": s.get("value"), "cash_cad": round(float(s.get("cash") or 0), 2), "core_plan": (s.get("core_plan") or {}).get("words"),
                          "dial_state": (s.get("core_plan") or {}).get("state"), "fills_today": [{"coin": c, "side": sd, "sleeve": sl, "cad": round(q * p, 2), "why": w} for c, sd, sl, q, p, w in fills]}
    except Exception as exc:  # noqa: BLE001
        out["account_error"] = str(exc)[:120]
    try:
        opened = j.db.execute("SELECT watch, COUNT(*) FROM evidence_trades WHERE signal_t >= ? AND signal_t < ? GROUP BY watch", (day0, day0 + DAY)).fetchall()
        closed = j.db.execute("SELECT watch, COUNT(*), ROUND(SUM(net_usd),2) FROM evidence_trades WHERE status='CLOSED' AND exit_t >= ? AND exit_t < ? GROUP BY watch",
                              (day0, day0 + DAY)).fetchall()
        prot = j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE status='OPEN' AND detail LIKE '%protect:%'").fetchone()[0]
        out["books"] = {"opened": {w: n for w, n in opened}, "closed": {w: {"n": n, "net_usd": net} for w, n, net in closed}, "open_with_protected_stop": prot}
    except Exception as exc:  # noqa: BLE001
        out["books_error"] = str(exc)[:120]
    try:  # the setups board: what the scan found and what the brain did with the setups it was sent
        from jarvis.service import setups

        b = setups.latest(j)
        if b:
            sent = j.db.execute("SELECT coin, action, triggers, note FROM brain_decisions WHERE t >= ? AND triggers LIKE '%board%'", (day0 - DAY,)).fetchall()
            out["board"] = {"day": b.get("day"), "words": b.get("words"), "fired": b.get("fired"), "close": b.get("close"), "woke": b.get("woke"),
                            "by_family": b.get("by_family"), "touched_today": setups.touched_today(j),
                            "brain_on_board": [{"coin": c, "action": a, "note": (n or "")[:160]} for c, a, _t, n in sent]}
    except Exception as exc:  # noqa: BLE001
        out["board_error"] = str(exc)[:120]
    pl = discipline.latest_plan(j)
    out["plan_line"] = (pl or {}).get("line")
    out["layer_conflicts"] = (pl or {}).get("conflicts") or []
    return out


def section_not_done(j, day0: int, ananta: dict) -> dict:
    from jarvis.service import missed

    out: dict = {}
    try:
        r = missed.recent(j, 1)
        out["missed"] = {k: r.get(k) for k in ("counts", "moves") if k in r} if isinstance(r, dict) else r
    except Exception as exc:  # noqa: BLE001
        out["missed_error"] = str(exc)[:120]
    try:
        rows = j.db.execute("SELECT k, v FROM engine_state WHERE k LIKE 'wait:%'").fetchall()
        arrived = []
        for k, v in rows:
            d = json.loads(v or "{}")
            if int(d.get("t") or 0) >= day0 - DAY:
                arrived.append({"decision": k[5:], "hit": d.get("hit")})
        out["wait_for_arrived"] = arrived
    except Exception:  # noqa: BLE001
        out["wait_for_arrived"] = []
    out["floor_refused"] = [d for d in ((ananta.get("brain") or {}).get("decisions") or []) if d.get("floor")]
    return out


def section_reviews(j, day0: int) -> dict:
    out: dict = {"by_tag": {}, "by_book": {}, "rows": []}
    try:
        rows = j.db.execute("SELECT book, watch, coin, net_usd, best_pct, tags FROM trade_reviews WHERE t >= ? AND t < ? ORDER BY t", (day0, day0 + 2 * DAY)).fetchall()
        for book, watch, coin, net, best, tags in rows:
            tg = [t for t in str(tags or "").replace("[", "").replace("]", "").replace('"', "").split(",") if t.strip()]
            tg = [t.strip() for t in tg]
            out["rows"].append({"book": book, "watch": watch, "coin": coin, "net_usd": net, "best_pct": best, "tags": tg})
            out["by_book"].setdefault(book, 0)
            out["by_book"][book] += 1
            for t in tg:
                out["by_tag"][t] = out["by_tag"].get(t, 0) + 1
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:120]
    return out


# ------------------------------------------------------------------------------------------------------------------------- findings

def _f(kind: str, key: str, words: str, evidence: dict) -> dict:
    return {"kind": kind, "lane": LANE[kind], "key": key, "words": words, "evidence": evidence, "rule": RULES}


PROTECT_SINCE = 1792800000      # 2026-10-24 00:00 UTC: the protect rule went in (discipline item 3, Madhav's "Yes to all")


def _be_r() -> float:
    from jarvis.service import discipline

    return float((discipline.rules().get("protect") or {}).get("breakeven_r", 1.5))


def gave_back_past_protect(j, since: int) -> dict[str, int]:
    """#140 (Madhav's yes, 3 Nov 2026): the GAVE_BACK finding says the protect rule is not holding, so it counts only the trades the rule
    could act on: entered on or after 24 Oct (the rule's start), with a first stop under the entry, whose best price reached +1.5 R (the
    rule's break-even step), and still closed at a loss. Before, every 'was up 3%' trade counted, and with stops 4-18% away none of the 10
    on 2 Nov had reached +1.5 R: the card said the rule failed where it never applied. {book: n}, by the trade's watch."""
    be = _be_r()
    out: dict[str, int] = {}
    rows = j.db.execute("SELECT r.watch, r.entry, r.best_pct, r.net_usd, e.stop, e.detail, e.entry_t FROM trade_reviews r "
                        "JOIN evidence_trades e ON r.id = 'ev:' || e.id WHERE r.t >= ? AND r.tags LIKE '%GAVE_BACK%'", (since,)).fetchall()
    for watch, entry, best, net, stop, det, entry_t in rows:
        try:
            d = json.loads(det or "{}")
            stop0 = float(d.get("stop0") or stop or 0)
            entry, best = float(entry), float(best)
        except (TypeError, ValueError):
            continue
        if not entry_t or int(entry_t) < PROTECT_SINCE or not stop0 or stop0 >= entry or (net or 0) >= 0:
            continue
        if (best / 100 * entry) / (entry - stop0) >= be:
            out[watch] = out.get(watch, 0) + 1
    return out


def findings(j, day0: int, market: dict, ananta: dict, not_done: dict, reviews: dict) -> list[dict]:
    from jarvis.service import discipline, missed

    out: list[dict] = []
    b = BARS
    try:  # GAVE_BACK: 3+ in one book over 7 days, after the protect rule went in (so a repeat says the rule is not holding)
        since = day0 - b["gave_back_days"] * DAY
        for book, n in gave_back_past_protect(j, since).items():
            if n >= b["gave_back_n"]:
                out.append(_f("GAVE_BACK", f"gave_back:{book}", f"{book}: {n} trades reached the protect rule's +{_be_r():g} R and still closed at a loss in "
                              f"{b['gave_back_days']} days; the protect rule should hold these", {"book": book, "n": n, "days": b["gave_back_days"]}))
    except Exception:  # noqa: BLE001
        pass
    try:  # MISS_PATTERN: the same kind of move missed 3+ times in 30 days -> a family to draft (Madhav decides)
        for p in missed.patterns(j, b["miss_pattern_days"])[:5]:
            if int(p.get("times") or 0) >= b["miss_pattern_n"]:
                out.append(_f("MISS_PATTERN", f"miss:{p.get('said')}", f"we keep missing: {p.get('said')} ({p.get('times')} times in {b['miss_pattern_days']} days, "
                              f"average move {p.get('avg_move_pct')}%); draft a family for it or say why not",
                              {"said": p.get("said"), "times": p.get("times"), "coins": p.get("coins"), "avg_move_pct": p.get("avg_move_pct")}))
    except Exception:  # noqa: BLE001
        pass
    try:  # BOOK_BLEED: a book family down more than its bar over 7 days (the officer's check, as a finding with its own key)
        for c in discipline.officer_checks(j):
            if c["id"] == "book_bleed" and c["state"] == "FAIL":
                for bk in c.get("books") or []:          # one row per live book, so each gets its own yes / no
                    if bk.get("decided"):                # Madhav already decided on this book (the check says so): not a finding again
                        continue
                    out.append(_f("BOOK_BLEED", f"bleed:{bk['book']}", f"{bk['book']}: {bk['n']} closed, net ${bk['net_usd']:,.0f} in {b['bleed_days']} days "
                                  f"(the bar is -${b['bleed_pct'] * 100 * bk['n']:,.0f}); pause it, or say why it keeps running", bk))
    except Exception:  # noqa: BLE001
        pass
    for cf in ananta.get("layer_conflicts") or []:
        out.append(_f("LAYER_CONFLICT", f"conflict:{cf.get('between')}", cf.get("words") or "", cf))
    for d in not_done.get("floor_refused") or []:
        out.append(_f("SELECTION", f"floor:{d['coin']}", f"the brain wanted {d['coin']}; the selection floor refused it (tier, zone top or stop)", d))
    closed = str((market or {}).get("dial_state") or "").upper() == "CLOSED"
    try:                                                 # 1 Nov: words only; a wake-up already on last night's card says so
        prev = j.db.execute("SELECT card FROM rx_cards WHERE day < ? ORDER BY day DESC LIMIT 1", (time.strftime("%Y-%m-%d", time.gmtime(day0)),)).fetchone()
        seen = {f.get("key") for f in (json.loads(prev[0]).get("findings") or [])} if prev else set()
    except Exception:  # noqa: BLE001
        seen = set()
    for a in not_done.get("wait_for_arrived") or []:
        key = f"wait:{a['decision']}"
        what = ("noted, but the closed dial holds it back from a new review" if closed else "the brain is woken again")
        out.append(_f("WAIT_ARRIVED", key, f"a pass's condition came true ({'; '.join(a.get('hit') or [])}): {what}" + (" (also on last night's card)" if key in seen else ""), a))
    return out


# ------------------------------------------------------------------------------------------------------------------------- forwarding

def forward(j, day: str, rows: list[dict]) -> dict:
    from jarvis.service import brain, fixflow

    out = {"safe": [], "decision": [], "note": 0, "skipped": [], "woken": 0, "rule_b": []}
    safe_n = 0
    for f in rows:
        key = f["key"]
        if f["lane"] == "NOTE":
            out["note"] += 1
            continue
        if f["kind"] == "WAIT_ARRIVED":                           # item 6: wake the brain again, no repair request
            # 6 Nov 2026 (Madhav's yes, the reconstruction audit E5): a wake is counted on the card, not kept as a queue row (38 of the
            # first 48 rows were wakes and crowded the queue and the Ask's answers); the brain is still woken exactly as before.
            try:
                did = (f.get("evidence") or {}).get("decision")
                r = j.db.execute("SELECT coin FROM brain_decisions WHERE id=?", (did,)).fetchone()
                if r:
                    brain.wake(j, r[0], "wait_arrived", {"decision": did, "hit": (f.get("evidence") or {}).get("hit")})
            except Exception:  # noqa: BLE001
                pass
            out["woken"] += 1
            continue
        if j.db.execute("SELECT 1 FROM rx_queue WHERE key=? AND state IN ('OPEN','FILED')", (key,)).fetchone():
            out["skipped"].append(key)
            continue
        if f["lane"] == "DECISION" and j.db.execute("SELECT 1 FROM rx_queue WHERE key=? AND state='DECIDED' AND decided_t>?", (key, int(j.now()) - 7 * 86400)).fetchone():
            out["skipped"].append(f"{key}: decided this week")        # a decision is not asked again for 7 days
            continue
        rid = uuid.uuid4().hex[:10]
        if f["lane"] == "DECISION" and f["kind"] == "MISS_PATTERN" and day < RULE_B_ENDS:
            # 6 Nov 2026 (Madhav's yes, E2): under Rule B no new crypto family is drafted before 14 Dec, so the job answers a new-family
            # question itself instead of leaving it in Needs you; the same key is not asked again inside the window; after 14 Dec it is OPEN again.
            if j.db.execute("SELECT 1 FROM rx_queue WHERE key=? AND decision LIKE '%Rule B:%'", (key,)).fetchone():
                out["skipped"].append(f"{key}: Rule B")
                continue
            j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rid, day, int(j.now()), f["kind"], "DECISION", key, f["words"],
                                                                              json.dumps(f["evidence"], default=str), "DECIDED", int(j.now()),
                                                                              f"Rule B: snoozed to {RULE_B_ENDS} (no new crypto family before the day-60 checkpoint); answered by the job, Madhav's yes of 6 Nov"))
            out["rule_b"].append(key)
            continue
        if f["lane"] == "SAFE":
            if safe_n >= BARS["safe_per_night"]:
                out["skipped"].append(key)
                continue
            try:
                r = fixflow.flag(j, f"Reconstruction ({f['kind']}): {f['words']}", market="crypto", screen="reconstruction", use_ai=False)
                j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rid, day, int(j.now()), f["kind"], "SAFE", key, f["words"],
                                                                                  json.dumps(f["evidence"], default=str), "FILED", None, f"request #{r.get('num')}"))
                out["safe"].append(key)
                safe_n += 1
            except Exception as exc:  # noqa: BLE001
                out["skipped"].append(f"{key}: {str(exc)[:60]}")
        else:
            j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rid, day, int(j.now()), f["kind"], "DECISION", key, f["words"],
                                                                              json.dumps(f["evidence"], default=str), "OPEN", None, None))
            out["decision"].append(key)
    j.db.commit()
    return out


# ------------------------------------------------------------------------------------------------------------------------- the card

def evening(j, force: bool = False) -> dict | None:
    """One card per UTC day (the `day` it is made on, after the close); its sections describe the UTC day that just CLOSED (about_day).
    6 Nov 2026 (the reconstruction audit): since the card went live every scheduled card had read `t >= today 00:00` at 00:05, so "what
    Ananta did" held the new day's first five minutes (0 brain decisions on 13 cards) and the missed moves were read before the nightly
    review had found them (0 moves on every card). The window is now [closed day 00:00, closed day 24:00), and the 15-minute loop makes
    the card after that review (00:30 UTC or later), not run_daily at 00:05."""
    _table(j)
    now = int(j.now())
    day = _day(now)
    if not force and j.db.execute("SELECT 1 FROM rx_cards WHERE day=?", (day,)).fetchone():
        return None
    day0 = now - now % DAY - DAY                 # the closed UTC day
    market = section_market(j, day0)
    ananta = section_ananta(j, day0)
    not_done = section_not_done(j, day0, ananta)
    reviews = section_reviews(j, day0)
    rows = findings(j, day0, market, ananta, not_done, reviews)
    fwd = forward(j, day, rows)
    wakes = [r for r in rows if r["kind"] == "WAIT_ARRIVED"]                 # 6 Nov (E5): wakes are one count on the card, not findings
    rows = [r for r in rows if r["kind"] != "WAIT_ARRIVED"]
    value = value_line(j)
    head = _headline(market, ananta, reviews, rows, len(wakes), value)
    card = {"day": day, "about_day": _day(day0), "t": now, "rules": RULES, "bars": BARS, "headline": f"About {_day(day0)}: {head}", "market": market,
            "ananta": ananta, "not_done": not_done, "reviews": reviews, "findings": rows, "wakes": {"n": len(wakes), "items": wakes}, "value": value,
            "forwarding": fwd}
    j.db.execute("INSERT OR REPLACE INTO rx_cards VALUES (?,?,?,?)", (day, now, RULES, json.dumps(card, default=str)))
    j.db.commit()
    return {"day": day, "about_day": _day(day0), "findings": len(rows), "forwarded": fwd, "headline": card["headline"]}


def value_line(j) -> dict:
    """6 Nov 2026 (Madhav's yes, the reconstruction audit E3): one line per card that measures the job's own value, counted, not argued:
    findings that changed a rule (none can, without Madhav), decisions that changed what runs (a book paused on a finding), families drafted."""
    _table(j)
    try:
        rows = j.db.execute("SELECT kind, key, decision, day FROM rx_queue WHERE state='DECIDED' ORDER BY decided_t").fetchall()
    except Exception:  # noqa: BLE001
        rows = []
    try:                                                   # what runs is read from the status book, never from the words of a decision
        status = {k: (v.get("status") if isinstance(v, dict) else "") for k, v in (json.loads((REPO / "docs" / "knowledge" / "strategy_status.json").read_text()).get("strategies") or {}).items()}
    except Exception:  # noqa: BLE001
        status = {}
    paused = []
    for kind, k, dec, d in rows:
        if kind != "BOOK_BLEED" or (dec or "").startswith("superseded"):
            continue
        book = k.split(":", 1)[-1].split(":")[0].strip()
        st = status.get(book) or status.get(book.replace("JARVIS_", "")) or ""
        if st in ("PARKED", "RETIRED"):
            paused.append(f"{book} {st.lower()} ({d})")
    drafted = [m.group(1) for kind, k, dec, d in rows if kind == "MISS_PATTERN" and dec and (m := re.search(r"drafted as (\w+)", dec))]
    drafted = [f"{x} ({status.get(x, 'unknown').lower()})" for x in drafted]
    rule_b = sum(1 for kind, k, dec, d in rows if dec and "Rule B:" in dec)   # a hand decision through decide() is prefixed "<by>: "
    words = (f"Value since 24 Oct: 0 findings changed a rule; {len(paused)} decision{'s' if len(paused) != 1 else ''} changed what runs"
             + (f" ({', '.join(paused)})" if paused else "") + f"; {len(drafted)} famil{'ies' if len(drafted) != 1 else 'y'} drafted from a finding" + (f" ({', '.join(drafted)})" if drafted else "")
             + (f"; {rule_b} new-family question{'s' if rule_b != 1 else ''} held by Rule B until {RULE_B_ENDS}" if rule_b else "") + ".")
    return {"rules_changed": 0, "paused_books": paused, "families_drafted": drafted, "held_by_rule_b": rule_b, "words": words}


def _headline(market: dict, ananta: dict, reviews: dict, rows: list[dict], wakes: int = 0, value: dict | None = None) -> str:
    bits = [market.get("dial_words") or "dial unread"]
    br = ananta.get("brain") or {}
    if br.get("n"):
        bits.append("the brain " + ", ".join(f"{a.lower()} {n}" for a, n in sorted((br.get("by_action") or {}).items())))
    if reviews.get("by_tag"):
        bits.append("reviews: " + ", ".join(f"{t} {n}" for t, n in sorted(reviews["by_tag"].items())))
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    bits.append(("findings: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items()))) if kinds else "no findings")
    if wakes:
        bits.append(f"woke the brain {wakes} time{'s' if wakes != 1 else ''} for a wait that came true")
    out = "; ".join(bits) + "."
    if value and value.get("words"):
        out += " " + value["words"]
    return out


def latest(j) -> dict | None:
    _table(j)
    r = j.db.execute("SELECT card FROM rx_cards ORDER BY day DESC LIMIT 1").fetchone()
    return json.loads(r[0]) if r else None


def cards(j, n: int = 7) -> list[dict]:
    _table(j)
    return [json.loads(r[0]) for r in j.db.execute("SELECT card FROM rx_cards ORDER BY day DESC LIMIT ?", (n,))]


def queue(j, n: int = 40) -> list[dict]:
    _table(j)
    cols = ("id", "day", "t", "kind", "lane", "key", "words", "evidence", "state", "decided_t", "decision")
    rows = [dict(zip(cols, r)) for r in j.db.execute("SELECT * FROM rx_queue ORDER BY CASE state WHEN 'OPEN' THEN 0 ELSE 1 END, t DESC LIMIT ?", (n,))]
    for r in rows:
        try:
            r["evidence"] = json.loads(r["evidence"] or "{}")
        except ValueError:
            pass
        r["kind_words"] = KIND_WORDS.get(r["kind"], r["kind"])
    return rows


def decide(j, rid: str, words: str, by: str = "owner") -> dict:
    _table(j)
    r = j.db.execute("SELECT state FROM rx_queue WHERE id=?", (rid,)).fetchone()
    if not r:
        raise KeyError(rid)
    j.db.execute("UPDATE rx_queue SET state='DECIDED', decided_t=?, decision=? WHERE id=?", (int(j.now()), f"{by}: {words}"[:300], rid))
    j.db.commit()
    return {"id": rid, "state": "DECIDED", "decision": words}
