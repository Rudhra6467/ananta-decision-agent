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
import time
import uuid

DAY = 86400
RULES = "rx-cr-v1-2026-10-24"
BARS = {"gave_back_n": 3, "gave_back_days": 7, "miss_pattern_n": 3, "miss_pattern_days": 30, "bleed_pct": 0.02, "bleed_days": 7,
        "bleed_min_closed": 5, "selection_n": 1, "safe_per_night": 3}
KIND_WORDS = {"GAVE_BACK": "winners that became losers (no plan protected them)", "MISS_PATTERN": "a kind of move we keep missing",
              "BOOK_BLEED": "a book losing more than its bar over a week", "LAYER_CONFLICT": "two layers wanting different things",
              "SELECTION": "a buy the selection floor refused", "WAIT_ARRIVED": "a pass whose condition came true"}
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
        rows = j.db.execute("SELECT id, coin, action, confidence, plan, note FROM brain_decisions WHERE t >= ? ORDER BY t", (day0,)).fetchall()
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
        fills = j.db.execute("SELECT coin, side, sleeve, qty, px, why FROM book500_fills WHERE t >= ? ORDER BY t", (day0,)).fetchall()
        out["account"] = {"value_cad": s.get("value"), "cash_cad": round(float(s.get("cash") or 0), 2), "core_plan": (s.get("core_plan") or {}).get("words"),
                          "dial_state": (s.get("core_plan") or {}).get("state"), "fills_today": [{"coin": c, "side": sd, "sleeve": sl, "cad": round(q * p, 2), "why": w} for c, sd, sl, q, p, w in fills]}
    except Exception as exc:  # noqa: BLE001
        out["account_error"] = str(exc)[:120]
    try:
        opened = j.db.execute("SELECT watch, COUNT(*) FROM evidence_trades WHERE signal_t >= ? GROUP BY watch", (day0,)).fetchall()
        closed = j.db.execute("SELECT watch, COUNT(*), ROUND(SUM(net_usd),2) FROM evidence_trades WHERE status='CLOSED' AND exit_t >= ? GROUP BY watch", (day0,)).fetchall()
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
        rows = j.db.execute("SELECT book, watch, coin, net_usd, best_pct, tags FROM trade_reviews WHERE t >= ? ORDER BY t", (day0,)).fetchall()
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


def findings(j, day0: int, market: dict, ananta: dict, not_done: dict, reviews: dict) -> list[dict]:
    from jarvis.service import discipline, missed

    out: list[dict] = []
    b = BARS
    try:  # GAVE_BACK: 3+ in one book over 7 days, after the protect rule went in (so a repeat says the rule is not holding)
        since = day0 - b["gave_back_days"] * DAY
        rows = j.db.execute("SELECT book, COUNT(*) FROM trade_reviews WHERE t >= ? AND tags LIKE '%GAVE_BACK%' GROUP BY book", (since,)).fetchall()
        for book, n in rows:
            if n >= b["gave_back_n"]:
                out.append(_f("GAVE_BACK", f"gave_back:{book}", f"{book}: {n} trades were up and gave it back in {b['gave_back_days']} days; the protect rule should hold these",
                              {"book": book, "n": n, "days": b["gave_back_days"]}))
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
                    out.append(_f("BOOK_BLEED", f"bleed:{bk['book']}", f"{bk['book']}: {bk['n']} closed, net ${bk['net_usd']:,.0f} in {b['bleed_days']} days "
                                  f"(the bar is -${b['bleed_pct'] * 100 * bk['n']:,.0f}); pause it, or say why it keeps running", bk))
    except Exception:  # noqa: BLE001
        pass
    for cf in ananta.get("layer_conflicts") or []:
        out.append(_f("LAYER_CONFLICT", f"conflict:{cf.get('between')}", cf.get("words") or "", cf))
    for d in not_done.get("floor_refused") or []:
        out.append(_f("SELECTION", f"floor:{d['coin']}", f"the brain wanted {d['coin']}; the selection floor refused it (tier, zone top or stop)", d))
    for a in not_done.get("wait_for_arrived") or []:
        out.append(_f("WAIT_ARRIVED", f"wait:{a['decision']}", f"a pass's condition came true ({'; '.join(a.get('hit') or [])}): the brain is woken again", a))
    return out


# ------------------------------------------------------------------------------------------------------------------------- forwarding

def forward(j, day: str, rows: list[dict]) -> dict:
    from jarvis.service import brain, fixflow

    out = {"safe": [], "decision": [], "note": 0, "skipped": []}
    safe_n = 0
    for f in rows:
        key = f["key"]
        if f["lane"] == "NOTE":
            out["note"] += 1
            continue
        if j.db.execute("SELECT 1 FROM rx_queue WHERE key=? AND state IN ('OPEN','FILED')", (key,)).fetchone():
            out["skipped"].append(key)
            continue
        if f["lane"] == "DECISION" and j.db.execute("SELECT 1 FROM rx_queue WHERE key=? AND state='DECIDED' AND decided_t>?", (key, int(j.now()) - 7 * 86400)).fetchone():
            out["skipped"].append(f"{key}: decided this week")        # a decision is not asked again for 7 days
            continue
        rid = uuid.uuid4().hex[:10]
        if f["lane"] == "SAFE":
            if f["kind"] == "WAIT_ARRIVED":                       # item 6: wake the brain again, no repair request
                try:
                    did = (f.get("evidence") or {}).get("decision")
                    r = j.db.execute("SELECT coin FROM brain_decisions WHERE id=?", (did,)).fetchone()
                    if r:
                        brain.wake(j, r[0], "wait_arrived", {"decision": did, "hit": (f.get("evidence") or {}).get("hit")})
                except Exception:  # noqa: BLE001
                    pass
                j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", (rid, day, int(j.now()), f["kind"], "SAFE", key, f["words"],
                                                                                  json.dumps(f["evidence"], default=str), "DONE", int(j.now()), "the brain was woken again"))
                out["safe"].append(key)
                continue
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
    _table(j)
    now = int(j.now())
    day = _day(now)
    if not force and j.db.execute("SELECT 1 FROM rx_cards WHERE day=?", (day,)).fetchone():
        return None
    day0 = now - now % DAY
    market = section_market(j, day0)
    ananta = section_ananta(j, day0)
    not_done = section_not_done(j, day0, ananta)
    reviews = section_reviews(j, day0)
    rows = findings(j, day0, market, ananta, not_done, reviews)
    fwd = forward(j, day, rows)
    head = _headline(market, ananta, reviews, rows)
    card = {"day": day, "t": now, "rules": RULES, "bars": BARS, "headline": head, "market": market, "ananta": ananta, "not_done": not_done,
            "reviews": reviews, "findings": rows, "forwarding": fwd}
    j.db.execute("INSERT OR REPLACE INTO rx_cards VALUES (?,?,?,?)", (day, now, RULES, json.dumps(card, default=str)))
    j.db.commit()
    return {"day": day, "findings": len(rows), "forwarded": fwd, "headline": head}


def _headline(market: dict, ananta: dict, reviews: dict, rows: list[dict]) -> str:
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
    return "; ".join(bits) + "."


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
