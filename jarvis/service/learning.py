"""The learning loop (plan Batch 4b, Oct 11): every decision seen four ways, a weekly review that turns them into tickets, credit for
the knowledge that moved each decision, the brain's trades rebuilt from raw candles, Madhav's own trades as worked examples, and two
classic playbooks as daily peers.

  card(j, row)            one situation: what we did / what if / what else / what others did / lesson
  weekly_review(j)        the week's situations -> docs/repair_shop/weekly/<day>.md, each ending in a ticket or "no change, because"
  credit(j)               knowledge id -> how the decisions that cited it turned out
  rebuild_brain(j)        closed brain trades re-checked against the daily candles (G28)
  close_counterfactuals(j) every OPEN "what if we had traded" case in the hourly watch's store, scored and labelled (G7)
  worked_examples()       Madhav's casebook trades, short, for the brain's pack (G30)
  peers(j, start)         BREAKOUT20 and ROTATE5 paper books on tier-A coins since start (G14)
  changes_after(j)        the change log's after-metrics (ledger.json "changes")
Paper only; nothing here trades.
"""
from __future__ import annotations

import calendar
import json
import statistics
import time
from pathlib import Path

DAY = 86400
ROOT = Path(__file__).resolve().parents[2]


def _daily(j, coin: str) -> list[tuple]:
    from jarvis.service import feed

    try:
        return feed.daily(j, coin)
    except Exception:  # noqa: BLE001
        return []


def _close_on_or_after(D: list[tuple], t: int) -> tuple | None:
    for b in D:
        if b[0] >= t - t % DAY:
            return b
    return None


def _pct(a: float | None, b: float | None) -> float | None:
    return round(100 * (b / a - 1), 2) if a and b else None


def _trade(j, tid: str | None) -> dict | None:
    if not tid:
        return None
    from jarvis.service import watch_engine as W

    r = j.db.execute(f"SELECT {', '.join(W.COLS)} FROM evidence_trades WHERE id=?", (tid,)).fetchone()
    return dict(zip(W.COLS, r)) if r else None


def _btc_window(j, t0: int, t1: int) -> dict:
    """What Bitcoin and the benchmark (Bitcoin above its 50-day, GATE50) did over the same window."""
    out: dict = {}
    D = _daily(j, "BTC")
    a, b = _close_on_or_after(D, t0), _close_on_or_after(D, t1)
    if a and b:
        out["btc_pct"] = _pct(a[1], b[4])
    try:
        from src.intelligence.explorer_engine import HALF_SPREAD, NDAX_FEE
        from src.research import review25 as R

        if len(D) > 210:
            out["benchmark_pct"] = R.run([x[:5] for x in D], R.targets([x[:5] for x in D], "GATE50"), NDAX_FEE + HALF_SPREAD["BTC"], int(t0), int(t1))["total_pct"]
    except Exception:  # noqa: BLE001
        pass
    return out


def card(j, d: dict, light: bool = False) -> dict:
    """One situation (a brain decision) in four views, plus the lesson the rules draw from it. light: without Bitcoin's and the
    benchmark's window (the nightly lesson count needs only the lesson and the twin)."""
    t = int(d["t"])
    coin = d["coin"]
    plan = json.loads(d.get("plan") or "{}") if isinstance(d.get("plan"), str) else (d.get("plan") or {})
    tr = _trade(j, d.get("trade_id"))
    twin = _trade(j, d.get("random_id"))
    did = {"action": d["action"], "coin": coin, "price": d.get("price"), "exit_plan": plan.get("exit_plan"),
           "thesis": (d.get("thesis") or "")[:200], "knowledge": json.loads(d.get("knowledge") or "[]")}
    if tr:
        did.update(status=tr["status"], net_usd=tr["net_usd"], exit_why=tr.get("exit_why"))
    # what if: the other choice
    what_if: dict = {}
    D = _daily(j, coin)
    if d["action"] == "PASS":
        what_if = {"had_we_bought_1d_pct": d.get("after_1d_pct"), "had_we_bought_5d_pct": d.get("after_5d_pct")}
    elif tr and tr.get("entry"):
        e = _close_on_or_after(D, t + 10 * DAY)
        what_if = {"held_10_days_no_stop_pct": _pct(tr["entry"], e[4]) if e and e[0] <= time.time() - DAY else None}
        if tr["status"] == "CLOSED" and tr.get("exit_t"):
            a = _close_on_or_after(D, int(tr["exit_t"]) + 5 * DAY)
            what_if["price_5_days_after_exit_vs_exit_pct"] = _pct(tr.get("exit"), a[4]) if a and a[0] <= time.time() - DAY else None
    # what else: the other signals that day
    day = time.strftime("%Y-%m-%d", time.gmtime(t))
    rows = j.db.execute("SELECT watch, coin, status, net_usd FROM evidence_trades WHERE signal_day=? AND watch NOT LIKE 'JARVIS%' AND watch NOT LIKE 'RANDOM%'",
                        (day,)).fetchall()
    closed = [r for r in rows if r[2] == "CLOSED"]
    what_else = {"signals_that_day": len(rows), "closed": len(closed),
                 "avg_closed_usd": round(statistics.mean([r[3] or 0 for r in closed]), 2) if closed else None,
                 "best": max(closed, key=lambda r: r[3] or 0)[:2] if closed else None}
    # what others did
    t1 = int(tr["exit_t"]) if tr and tr.get("exit_t") else int(time.time())
    others = {"random_twin": {"coin": twin["coin"], "status": twin["status"], "net_usd": twin["net_usd"]} if twin else None,
              **({} if light else _btc_window(j, t, t1))}
    # the lesson the rules draw
    lesson = None
    if d["action"] == "PASS" and (d.get("after_5d_pct") or 0) >= 5:
        lesson = "missed winner: the pass rose 5%+ in 5 days"
    elif tr and tr["status"] == "CLOSED" and (tr["net_usd"] or 0) < 0 and "stop" in (tr.get("exit_why") or "") and \
            (what_if.get("price_5_days_after_exit_vs_exit_pct") or 0) > 3:
        lesson = "stopped at the low: the price was 3%+ higher 5 days after the stop"
    elif tr and tr["status"] == "CLOSED" and twin and twin["status"] == "CLOSED":
        lesson = ("pick beat random" if (tr["net_usd"] or 0) > (twin["net_usd"] or 0) else "random beat the pick")
    return {"id": d["id"], "t": t, "day": day, "what_we_did": did, "what_if": what_if, "what_else": what_else, "what_others_did": others,
            "lesson": lesson}


def _decisions(j, since: int) -> list[dict]:
    cols = ["id", "t", "coin", "action", "price", "plan", "thesis", "knowledge", "trade_id", "random_id", "after_1d_pct", "after_5d_pct"]
    return [dict(zip(cols, r)) for r in j.db.execute(f"SELECT {', '.join(cols)} FROM brain_decisions WHERE t >= ? AND action != 'ERROR' ORDER BY t",
                                                     (since,)).fetchall()]


def weekly_review(j, days: int = 7, write: bool = True) -> dict:
    since = int(j.now()) - days * DAY
    cards = [card(j, d) for d in _decisions(j, since)]
    closed = [c for c in cards if c["what_we_did"].get("status") == "CLOSED"]
    pick = sorted(closed, key=lambda c: c["what_we_did"].get("net_usd") or 0)
    passes = sorted([c for c in cards if c["what_we_did"]["action"] == "PASS" and c["what_if"].get("had_we_bought_5d_pct") is not None],
                    key=lambda c: -(c["what_if"]["had_we_bought_5d_pct"] or 0))
    chosen, seen = [], set()
    for c in pick[-2:][::-1] + pick[:2] + passes[:2] + passes[-1:]:
        if c["id"] not in seen:
            chosen.append(c)
            seen.add(c["id"])
    lessons: dict = {}
    for c in cards:
        if c["lesson"]:
            lessons[c["lesson"].split(":")[0]] = lessons.get(c["lesson"].split(":")[0], 0) + 1
    tickets = [f"{k}: {n} times this week. Proposed: a pre-registered review of this pattern before any change."
               for k, n in lessons.items() if n >= 3 and k in ("stopped at the low", "missed winner", "random beat the pick")]
    for c in chosen:
        k = (c["lesson"] or "").split(":")[0]
        c["ends_in"] = (f"ticket: {k} ({lessons.get(k)} times this week)" if k and lessons.get(k, 0) >= 3 else
                        "no change, because " + ("one case is not a pattern (fewer than 3 this week)" if k else "nothing here argues for a change"))
    out = {"from": time.strftime("%Y-%m-%d", time.gmtime(since)), "to": time.strftime("%Y-%m-%d", time.gmtime(j.now())),
           "decisions": len(cards), "takes": sum(c["what_we_did"]["action"] == "TAKE" for c in cards), "situations": chosen,
           "lessons": lessons, "tickets": tickets, "credit": credit(j, since), "changes": changes_after(j), "peers": peers(j)}
    try:  # Oct 21: the lessons of earlier weeks that matured since the last review (counted nightly by count_lessons), and auto-filed tickets
        out["matured"] = lessons_summary(j, since)
        out["auto_tickets"] = auto_requests(j, since)
    except Exception as exc:  # noqa: BLE001
        out["matured"] = {"error": str(exc)[:120]}
    if write:
        try:
            f = ROOT / "docs" / "repair_shop" / "weekly" / f"{out['to']}.md"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(_markdown(out, j))
            out["file"] = str(f.relative_to(ROOT))
        except Exception as exc:  # noqa: BLE001
            out["file_error"] = str(exc)[:120]
    return out


def _markdown(r: dict, j=None) -> str:
    L = [f"# Weekly situation review, {r['from']} to {r['to']}", "",
         f"{r['decisions']} brain decisions ({r['takes']} buys). Lessons counted: " + (", ".join(f"{k} x{n}" for k, n in r["lessons"].items()) or "none") + ".", ""]
    for c in r["situations"]:
        w = c["what_we_did"]
        L += [f"## {c['day']} · {w['coin']} · {w['action']}" + (f" ({w.get('exit_plan')})" if w.get("exit_plan") else ""), "",
              f"- **What we did:** {w['action']} at {w.get('price')}; " + (f"{w.get('status')}, ${w.get('net_usd')} ({w.get('exit_why')})" if w.get("status") else "no trade")
              + f". {w.get('thesis', '')}",
              f"- **What if:** {json.dumps(c['what_if'])}",
              f"- **What else:** {c['what_else']['signals_that_day']} other signals that day; closed ones averaged ${c['what_else']['avg_closed_usd']}",
              f"- **What others did:** {json.dumps(c['what_others_did'])}",
              f"- **Lesson:** {c['lesson'] or 'none drawn'}",
              f"- **Ends in:** {c['ends_in']}", ""]
    L += ["## Tickets", ""] + ([f"- {t}" for t in r["tickets"]] or ["- None this week: no pattern reached 3 cases."]) + [""]
    m = r.get("matured")
    if m is not None:
        L += ["## Lessons that matured since the last review", ""]
        if m.get("error"):
            L += [f"- (not read: {m['error']})"]
        else:
            L += [f"- {m['counted']} decisions' lessons matured and were counted under their own week ({m['late']} after that week's review had run)"
                  + (": " + ", ".join(f"{k} x{n}" for k, n in m["kinds"].items()) if m["kinds"] else "") + ".",
                  f"- {m['sealed_waiting']} matured inside the forward window and stay unlabelled until 2026-12-15 (pre-registered reviews #31, #33, #34).",
                  "- Filed on the repair board by themselves this week (weekly lessons, missed-move patterns, fidelity, the ledger check): "
                  + (", ".join(f"#{t['num']} ({t['about'] or 'no topic'}, {t['status']})" for t in r.get("auto_tickets") or []) or "none") + "."]
        L += [""]
    L += ["## Credit (which knowledge moved decisions)", ""] + [f"- {k}: {json.dumps(v)}" for k, v in list(r["credit"].items())[:12]] + [""]
    L += ["## Change log, after", ""] + [f"- {c['change']}: {c.get('after')}" for c in r["changes"]] + [""]
    L += ["## Due", ""] + [f"- {x}" for x in _due(j)] + [""]
    L += ["## Peers since the brain started", "", f"```\n{json.dumps(r['peers'], indent=1)[:1500]}\n```", ""]
    return "\n".join(L)


def _due(j=None) -> list[str]:
    """What the review says is owed. Oct 15 (research audit): it used to stop at the first study with a schedule, so only R2 could ever show.
    Now every ledger study with a schedule is listed, then the due list (docs/knowledge/due_list.json): overdue, due this week, the decisions
    waiting for Madhav, what waits for evidence, and how many items wait for the end of the window."""
    out: list[str] = []
    today = time.strftime("%Y-%m-%d", time.gmtime(j.now() if j is not None else time.time()))
    try:
        led = json.loads((ROOT / "docs" / "repair_shop" / "ledger.json").read_text())
        for st in led.get("studies", []):
            sc = st.get("schedule") or {}
            if sc.get("next_due"):
                out.append(f"Study {st.get('id')} ({st.get('title', 'no title')}), every {sc.get('every', 'period')}: next due {sc['next_due']}"
                           + (" -- DUE NOW" if today >= sc["next_due"] else ""))
    except Exception as exc:  # noqa: BLE001
        out.append(f"(the ledger's schedules could not be read: {str(exc)[:80]})")
    if j is not None:
        try:
            from jarvis.service import due_list

            r = due_list.check(j)
            by = {x["id"]: x for x in r["rows"]}
            out += [f"OVERDUE {i} (was due {by[i]['due']}): {by[i]['what']}" for i in r["overdue"]]
            out += [f"due {by[i]['due']}: {i} ({by[i]['owner'] or 'Claude'}) - {by[i]['what']}" for i in r["soon"]]
            waiting = [x["id"] for x in r["rows"] if x["owner_decision"] and x["state"] in ("later", "soon", "overdue")]
            if waiting:
                out.append(f"decisions waiting for Madhav: {', '.join(waiting)}")
            if r["waiting_for_evidence"]:
                out.append(f"waiting for evidence: {', '.join(r['waiting_for_evidence'])}")
            out.append(f"after the window ({r['window_end']}): {len(r['post_window'])} items" + (" -- THE WINDOW IS OVER, decide their order" if r["window_over"] else ""))
            if r["problems"]:
                out.append("the due list disagrees with its own rules: " + "; ".join(r["problems"][:3]))
        except Exception as exc:  # noqa: BLE001
            out.append(f"(the due list could not be read: {str(exc)[:80]})")
    return out or ["nothing scheduled"]


# ---------------------------------------------------------------------------
# lessons counted when they mature; the weekly tickets filed by themselves (Oct 21, decision map sections 3 and 5)
# ---------------------------------------------------------------------------
# The weekly review counts the lessons of the week's decisions on Sunday, but a buy's lesson needs both legs closed (and a stop's, the
# price 5 days later), and a pass's needs its 5-day move: most mature after the review has run and were never counted. The Oct 14
# review's ticket ("random beat the pick", 3 times) was never filed, and its fourth case (VTHO, bought Oct 9) matured on Oct 15.
# count_lessons() runs at every daily close: each decision whose lesson has matured since the last count is labelled once, exactly as
# card() labels it, under the week whose review it belongs to; a kind that reaches 3 in one week files one repair-board request with its
# evidence. Reporting only (Rule B): a lesson or a ticket never changes a trading rule.
# Forward window (docs/research/PREREG_WINDOW_2026-10-20.md): every lesson kind is the object of a pre-registered review (#31, #33,
# #34), so a decision made from 2026-10-21 is counted as matured but NOT labelled before 2026-12-15 (labelling compares a pair's
# values, which is a look); its label and any ticket follow at the first count after the seal lifts.
TICKET_KINDS = ("stopped at the low", "missed winner", "random beat the pick")
TICKET_MIN = 3
PREREG = {"random beat the pick": "#33 (does Jarvis's pick beat a random coin?)", "stopped at the low": "#31 (the written close stop against the coded touch stop)",
          "missed winner": "#34 (are the brain's PASSes right?)"}
WINDOW_FROM_T = calendar.timegm((2026, 10, 21, 0, 0, 0))
SEALED_UNTIL_T = calendar.timegm((2026, 12, 15, 0, 0, 0))
MATURE_AFTER_EXIT = 6 * DAY          # card() reads the close 5 days after a stop exit once that day is complete
UNFILLED_AFTER = 30 * DAY            # a leg never filled (WAITING) stops holding its decision back after 30 days
REVIEW_SLACK = 1800                  # the Sunday review runs just after the 00:00 UTC close


def _lessons_table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS learning_lessons (decision_id TEXT PRIMARY KEY, t INTEGER, coin TEXT, action TEXT, week TEXT, "
                 "matured_t INTEGER, counted_t INTEGER, lesson TEXT, sealed INTEGER, late INTEGER, ticket TEXT, evidence TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")


def _has_table(j, name: str) -> bool:
    return bool(j.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def _week_of(t: int) -> str:
    """The Sunday whose weekly review covers a decision at t (the review runs at the Sunday 00:00 UTC close over the 7 days before)."""
    day0 = int(t) - int(t) % DAY
    wd = time.gmtime(day0).tm_wday                                    # Monday 0 .. Sunday 6
    return time.strftime("%Y-%m-%d", time.gmtime(day0 + ((6 - wd) if wd != 6 else 7) * DAY))


def _maturity(j, d: dict, now: int) -> int | None:
    """When the decision's lesson can no longer change (None: not yet). Reads statuses and times only, never a result, so it is not a
    look at a sealed review: a PASS once its 5-day move is settled; a TAKE once its trade and its random twin are closed (a leg never
    filled lets go after 30 days) and 6 days have passed since the last exit."""
    t = int(d["t"])
    if d["action"] != "TAKE":
        return min(now, t + 6 * DAY) if d.get("after_5d_pct") is not None else None
    last = t
    for tid in (d.get("trade_id"), d.get("random_id")):
        if not tid:
            continue
        r = j.db.execute("SELECT status, exit_t FROM evidence_trades WHERE id=?", (tid,)).fetchone()
        if r is None:
            continue
        if r[0] == "CLOSED":
            last = max(last, int(r[1] or t))
        elif r[0] == "OPEN" or now < t + UNFILLED_AFTER:
            return None
    m = last + MATURE_AFTER_EXIT
    return m if now >= m else None


def _sealed(j, d: dict, now: int) -> bool:
    """Inside the forward window until the seal lifts: a decision made from 2026-10-21 (reviews #33, #34), or one with a leg that exited
    from 2026-10-21 (review #31 counts every stop exit in the window, whenever it was opened; #33 reports the pairs open at the push)."""
    if now >= SEALED_UNTIL_T:
        return False
    if int(d["t"]) >= WINDOW_FROM_T:
        return True
    for tid in (d.get("trade_id"), d.get("random_id")):
        if tid:
            r = j.db.execute("SELECT exit_t FROM evidence_trades WHERE id=?", (tid,)).fetchone()
            if r and r[0] and int(r[0]) >= WINDOW_FROM_T:
                return True
    return False


def _evidence(c: dict) -> dict:
    w, o = c["what_we_did"], c["what_others_did"]
    tw = o.get("random_twin") or {}
    return {"coin": w["coin"], "day": c["day"], "action": w["action"], "net_usd": w.get("net_usd"), "twin": tw.get("coin"), "twin_net_usd": tw.get("net_usd"),
            "after_5d_pct": c["what_if"].get("had_we_bought_5d_pct"), "after_stop_5d_pct": c["what_if"].get("price_5_days_after_exit_vs_exit_pct")}


def _label(j, d: dict) -> tuple[str | None, str]:
    c = card(j, d, light=True)
    return ((c["lesson"] or "").split(":")[0] or None), json.dumps(_evidence(c))


def count_lessons(j, now: float | None = None) -> dict:
    """The nightly count (run_daily, step 'lessons'): every decision whose lesson matured since the last count is recorded once in
    learning_lessons under its week; then file_lesson_tickets(). Returns what was counted tonight."""
    now = int(now if now is not None else j.now())
    out: dict = {"matured": 0, "late": 0, "sealed": 0, "unsealed": 0, "by_kind": {}, "tickets": []}
    if not _has_table(j, "brain_decisions"):
        return {**out, "note": "no brain decisions yet"}
    _lessons_table(j)
    have = dict(j.db.execute("SELECT decision_id, sealed FROM learning_lessons").fetchall())
    for d in _decisions(j, 0):
        prev = have.get(d["id"])
        if prev == 0:
            continue
        seal = _sealed(j, d, now)
        if prev == 1:                                                  # matured inside the window: labelled once the seal has lifted
            if seal:
                continue
            lesson, ev = _label(j, d)
            j.db.execute("UPDATE learning_lessons SET lesson=?, evidence=?, sealed=0, counted_t=? WHERE decision_id=?", (lesson, ev, now, d["id"]))
            out["unsealed"] += 1
            out["by_kind"][lesson or "none drawn"] = out["by_kind"].get(lesson or "none drawn", 0) + 1
            continue
        m = _maturity(j, d, now)
        if m is None:
            continue
        week = _week_of(int(d["t"]))
        late = int(m > calendar.timegm(time.strptime(week, "%Y-%m-%d")) + REVIEW_SLACK)
        lesson, ev = (None, None) if seal else _label(j, d)
        j.db.execute("INSERT INTO learning_lessons (decision_id, t, coin, action, week, matured_t, counted_t, lesson, sealed, late, ticket, evidence) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (d["id"], int(d["t"]), d["coin"], d["action"], week, m, now, lesson, int(seal), late, None, ev))
        out["matured"] += 1
        out["late"] += late
        if seal:
            out["sealed"] += 1
        else:
            out["by_kind"][lesson or "none drawn"] = out["by_kind"].get(lesson or "none drawn", 0) + 1
    j.db.commit()
    out["tickets"] = file_lesson_tickets(j, now)
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    j.db.execute("INSERT OR REPLACE INTO engine_state (k, v) VALUES (?,?)", (f"learning:count:{day}", json.dumps({**out, "t": now})))
    j.db.commit()
    return out


def _ledger_lessons() -> tuple[dict[str, str], dict[str, str]]:
    """Lesson tickets in the hand-written ledger (a ticket row with "lesson" and "decisions"): {decision id: ticket id} and, per lesson
    kind, the ticket still open (status not DONE or WONT). The loop never files what the ledger already holds."""
    try:
        led = json.loads((ROOT / "docs" / "repair_shop" / "ledger.json").read_text())
    except Exception:  # noqa: BLE001
        return {}, {}
    by_dec, open_kind = {}, {}
    for t in led.get("tickets", []):
        if not t.get("lesson"):
            continue
        for did in t.get("decisions") or []:
            by_dec[str(did)] = str(t.get("id"))
        if t.get("status") not in ("DONE", "WONT"):
            open_kind.setdefault(t["lesson"], str(t.get("id")))
    return by_dec, open_kind


def _open_request(j, kind: str) -> str | None:
    """The repair-board request this loop filed for a lesson kind, while it is still OPEN or PLANNED."""
    st = j.db.execute("SELECT v FROM engine_state WHERE k=?", (f"learning:ticket:{kind}",)).fetchone()
    if not st:
        return None
    num = json.loads(st[0]).get("request")
    r = j.db.execute("SELECT status FROM owner_requests WHERE num=?", (int(num),)).fetchone() if str(num or "").isdigit() and _has_table(j, "owner_requests") else None
    return str(num) if r and r[0] in ("OPEN", "PLANNED") else None


def _case_words(kind: str, ev: dict) -> str:
    if kind == "random beat the pick":
        return f"{ev.get('coin')} {ev.get('day')}: ${ev.get('net_usd')} against the random {ev.get('twin')} ${ev.get('twin_net_usd')}"
    if kind == "stopped at the low":
        return f"{ev.get('coin')} {ev.get('day')}: stopped at ${ev.get('net_usd')}, {ev.get('after_stop_5d_pct'):+}% five days later" \
            if ev.get("after_stop_5d_pct") is not None else f"{ev.get('coin')} {ev.get('day')}: stopped at ${ev.get('net_usd')}"
    return f"{ev.get('coin')} {ev.get('day')}: PASS, {ev.get('after_5d_pct'):+}% in 5 days" if ev.get("after_5d_pct") is not None \
        else f"{ev.get('coin')} {ev.get('day')}: PASS"


def file_lesson_tickets(j, now: float | None = None) -> list[dict]:
    """A lesson kind reaching TICKET_MIN cases in one week becomes ONE repair-board request (by ananta-auto) carrying its evidence, and is
    never filed twice: while that kind has an open ticket (a ledger ticket row, or the request this loop filed, still OPEN or PLANNED)
    every new case of the kind joins it (learning_lessons.ticket) instead of filing another. Only after the ticket is closed can a later
    week that reaches TICKET_MIN again file a new one. Sealed rows are never read."""
    from jarvis.service import requests_log

    now = int(now if now is not None else j.now())
    _lessons_table(j)
    by_dec, open_kind = _ledger_lessons()
    rows = j.db.execute(f"SELECT decision_id, week, lesson, evidence FROM learning_lessons WHERE sealed=0 AND ticket IS NULL "
                        f"AND lesson IN ({','.join('?' * len(TICKET_KINDS))}) ORDER BY t", TICKET_KINDS).fetchall()
    cases: dict[str, list] = {}
    for did, week, kind, ev in rows:
        if by_dec.get(did):
            j.db.execute("UPDATE learning_lessons SET ticket=? WHERE decision_id=?", (by_dec[did], did))
        else:
            cases.setdefault(kind, []).append((did, week, json.loads(ev or "{}")))
    out = []
    for kind in TICKET_KINDS:
        cs = cases.get(kind) or []
        if not cs:
            continue
        weeks: dict[str, int] = {}
        for _, w, _ in cs:
            weeks[w] = weeks.get(w, 0) + 1
        tk = open_kind.get(kind) or _open_request(j, kind)
        if tk is None:
            if max(weeks.values()) < TICKET_MIN:
                continue
            per_week = ", ".join(f"{n} in the week to {w}" for w, n in sorted(weeks.items()))
            shown = "; ".join(_case_words(kind, ev) for _, _, ev in cs[:6]) + ("; and more" if len(cs) > 6 else "")
            text = (f"Weekly lesson \"{kind}\": {len(cs)} cases ({per_week}), each counted when it matured: {shown}. The question is "
                    f"pre-registered as review {PREREG[kind]}, scored once at CHECKPOINT-60, so nothing is proposed before then. "
                    "Rule B: a ticket never changes a trading rule. Filed by the learning loop (learning.count_lessons).")
            r = requests_log.add(j, "idea", text, about="weekly lessons", by="ananta-auto")
            tk = str(r.get("num"))
            prev = j.db.execute("SELECT v FROM engine_state WHERE k=?", (f"learning:ticket:{kind}",)).fetchone()
            j.db.execute("INSERT OR REPLACE INTO engine_state (k, v) VALUES (?,?)",
                         (f"learning:ticket:{kind}", json.dumps({"request": tk, "t": now, "cases": [d for d, _, _ in cs],
                                                                 "before": (json.loads(prev[0]).get("before") or []) + [json.loads(prev[0]).get("request")] if prev else []})))
            out.append({"kind": kind, "request": tk, "cases": len(cs), "weeks": weeks, "filed": True})
        else:
            out.append({"kind": kind, "request": tk, "cases": len(cs), "weeks": weeks, "filed": False})
        for did, _, _ in cs:
            j.db.execute("UPDATE learning_lessons SET ticket=? WHERE decision_id=?", (str(tk), did))
    j.db.commit()
    return out


def lessons_summary(j, since: int) -> dict | None:
    """Read-only: what the nightly count recorded since `since` (counts, late ones, sealed ones, kinds of unsealed ones) and when it last ran."""
    if not _has_table(j, "learning_lessons"):
        return None
    rows = j.db.execute("SELECT lesson, sealed, late FROM learning_lessons WHERE counted_t >= ?", (int(since),)).fetchall()
    kinds: dict = {}
    for lesson, sealed, _ in rows:
        if not sealed:
            kinds[lesson or "none drawn"] = kinds.get(lesson or "none drawn", 0) + 1
    last = j.db.execute("SELECT MAX(k) FROM engine_state WHERE k LIKE 'learning:count:%'").fetchone()[0] if _has_table(j, "engine_state") else None
    return {"counted": len(rows), "late": sum(1 for r in rows if r[2]), "sealed": sum(1 for r in rows if r[1]), "kinds": kinds,
            "sealed_waiting": j.db.execute("SELECT COUNT(*) FROM learning_lessons WHERE sealed=1").fetchone()[0],
            "last_count": last[len("learning:count:"):] if last else None}


def auto_requests(j, since: int) -> list[dict]:
    """Read-only: repair-board requests the system filed by itself since `since` (weekly lessons, missed-move patterns, fidelity, ledger)."""
    if not _has_table(j, "owner_requests"):
        return []
    return [{"num": n, "about": a, "status": s} for n, a, s in
            j.db.execute("SELECT num, about, status FROM owner_requests WHERE by='ananta-auto' AND t >= ? ORDER BY num", (int(since),))]


def credit(j, since: int = 0) -> dict:
    """For each piece of knowledge the brain cited: its buys (closed, average $), its passes (average move 5 days later)."""
    try:                                                           # excess over the universe median (columns exist once settle_passes has run)
        ex5 = dict(j.db.execute("SELECT id, after_5d_ex FROM brain_decisions WHERE t >= ?", (since,)).fetchall())
    except Exception:  # noqa: BLE001
        ex5 = {}
    out: dict = {}
    for d in _decisions(j, since):
        tr = _trade(j, d.get("trade_id"))
        for k in json.loads(d.get("knowledge") or "[]"):
            c = out.setdefault(k, {"buys": 0, "buys_closed": 0, "buy_usd": [], "passes": 0, "pass_5d": [], "pass_5d_ex": []})
            if d["action"] == "TAKE":
                c["buys"] += 1
                if tr and tr["status"] == "CLOSED":
                    c["buys_closed"] += 1
                    c["buy_usd"].append(tr["net_usd"] or 0)
            else:
                c["passes"] += 1
                if d.get("after_5d_pct") is not None:
                    c["pass_5d"].append(d["after_5d_pct"])
                    if ex5.get(d["id"]) is not None:
                        c["pass_5d_ex"].append(ex5[d["id"]])
    for c in out.values():
        c["avg_buy_usd"] = round(statistics.mean(c.pop("buy_usd")), 2) if c["buy_usd"] else None
        p = c.pop("pass_5d")
        c["avg_move_after_pass_pct"] = round(statistics.mean(p), 2) if p else None
        e = c.pop("pass_5d_ex")
        # against the whole market's move over the same days: negative = the passed coins did worse than the market (a good pass)
        c["avg_excess_after_pass_pct"] = round(statistics.mean(e), 2) if e else None
    return dict(sorted(out.items(), key=lambda kv: -(kv[1]["buys"] + kv[1]["passes"])))


def _day_bars(j, cache: dict, coin: str, when: int) -> list[tuple[str, tuple]]:
    """The candle of `when`'s UTC day from each source a book decides on: the feed's Binance daily candles, and the Explorer's own
    candles (watch_engine's daily exits of the brain's, the eye's and the 10-coin trades read those). Oct 15: XRP's Oct 14 low was
    1.302 in the Explorer's candles and 1.319 on Binance, so a twin stopped at 1.303 was right by the candles it was judged on;
    a check on Binance alone would call it a mismatch. Only complete days count (today's candle is still moving)."""
    if when - when % DAY >= int(j.now()) // DAY * DAY:
        return []
    if coin not in cache:
        from jarvis.service import watch_engine as W

        try:
            ex = W._daily(j, coin)
        except Exception:  # noqa: BLE001
            ex = []
        cache[coin] = (("binance", _daily(j, coin)), ("explorer", ex))
    out = []
    for name, D in cache[coin]:
        b = _close_on_or_after(D, when)
        if b and b[0] == when - when % DAY:
            out.append((name, b))
    return out


def _leg_ok(bars: list[tuple[str, tuple]], px, stop=None) -> bool:
    """A price inside the day's range (0.5% leeway) of at least one source, and for a stop exit that source's low at or under the stop."""
    return any(b[3] * 0.995 <= (px or 0) <= b[2] * 1.005 and (stop is None or b[3] <= stop * 1.005) for _, b in bars)


def rebuild_brain(j) -> dict:
    """G28: each closed brain trade (and its random twin) re-checked on the daily candles: the exit day's range must contain the exit
    price, and a stop exit needs the day's low at or under the stop. Mismatches are listed, never fixed silently."""
    from jarvis.service import watch_engine as W

    rows = j.db.execute(f"SELECT {', '.join(W.COLS)} FROM evidence_trades WHERE watch IN ('JARVIS','JARVIS_RANDOM') AND status='CLOSED'").fetchall()
    bad, checked, cache = [], 0, {}
    for r in rows:
        t = dict(zip(W.COLS, r))
        bars = _day_bars(j, cache, t["coin"], int(t["exit_t"] or 0))
        if not bars:
            continue
        checked += 1
        stop = t["stop"] if "stop" in (t.get("exit_why") or "") and t.get("stop") else None
        if not _leg_ok(bars, t["exit"], stop):
            b = bars[0][1]
            bad.append({"id": t["id"], "coin": t["coin"], "exit": t["exit"], "day_low": b[3], "day_high": b[2], "why": t.get("exit_why"),
                        "sources": {n: [x[3], x[2]] for n, x in bars}})
    out = {"checked": checked, "mismatches": len(bad), "list": bad[:20], "match": not bad}
    # The live rebuild_log has 8 columns (evidence_live._rebuild_table); a 4-value insert used to fail silently here,
    # so no brain run was ever logged (audit 2026-10-14). Write the real schema and let a failure surface to the
    # caller's learning_error instead of vanishing.
    from jarvis.service import evidence_live

    evidence_live._rebuild_table(j)
    t = int(j.now())
    while j.db.execute("SELECT 1 FROM rebuild_log WHERE t=?", (t,)).fetchone():
        t += 1                                                     # t is the primary key; step past an explorer row in the same second
    j.db.execute("INSERT INTO rebuild_log VALUES (?,?,?,?,?,?,?,?)",
                 (t, "brain", int(not bad), len(rows), checked, len(bad), 0, json.dumps(out)[:4000]))
    j.db.commit()
    return out


def rebuild_trades(j) -> dict:
    """Gate ops_reconstructable (Oct 15): EVERY paper trade of every evidence book (daily rules, zone touches, H07, the 30-coin dip
    trade, Jarvis's and the bold book with their random twins) re-checked on the daily candles: the entry price must lie inside its
    day's range, a closed trade's exit inside the exit day's range, and a stop exit needs the day's low at or under the stop (0.5%
    leeway; Binance's or the Explorer's candles, as _day_bars). Only complete days are checked; a coin without candles is counted,
    never guessed. Mismatches are listed, never fixed silently. Written to rebuild_log as source 'trades'."""
    from jarvis.service import watch_engine as W

    today0 = int(j.now()) // DAY * DAY
    rows = [dict(zip(W.COLS, r)) for r in j.db.execute(f"SELECT {', '.join(W.COLS)} FROM evidence_trades WHERE entry_t IS NOT NULL")]
    cache: dict = {}
    bad, checked, no_candles, not_yet = [], 0, 0, 0
    by_watch: dict = {}
    for t in rows:
        legs = [("entry", int(t["entry_t"]), t["entry"])]
        if t["status"] == "CLOSED" and t.get("exit_t"):
            legs.append(("exit", int(t["exit_t"]), t["exit"]))
        for leg, when, px in legs:
            if when - when % DAY >= today0:
                not_yet += 1
                continue
            bars = _day_bars(j, cache, t["coin"], when)
            if not bars:
                no_candles += 1
                continue
            checked += 1
            w = by_watch.setdefault(t["watch"], [0, 0])
            w[0] += 1
            stop = t["stop"] if leg == "exit" and "stop" in (t.get("exit_why") or "") and t.get("stop") else None
            if not _leg_ok(bars, px, stop):
                w[1] += 1
                bad.append({"id": t["id"], "watch": t["watch"], "coin": t["coin"], "leg": leg, "price": px,
                            "sources": {n: [b[3], b[2]] for n, b in bars}, "why": t.get("exit_why") if leg == "exit" else t.get("why")})
    out = {"trades": len(rows), "checked": checked, "mismatches": len(bad), "no_candles": no_candles, "today_not_checked": not_yet,
           "by_watch": {k: {"checked": v[0], "mismatches": v[1]} for k, v in sorted(by_watch.items())}, "list": bad[:20], "match": not bad}
    from jarvis.service import evidence_live

    evidence_live._rebuild_table(j)
    t = int(j.now())
    while j.db.execute("SELECT 1 FROM rebuild_log WHERE t=?", (t,)).fetchone():
        t += 1
    j.db.execute("INSERT INTO rebuild_log VALUES (?,?,?,?,?,?,?,?)",
                 (t, "trades", int(not bad), len(rows), checked, len(bad), 0, json.dumps(out)[:4000]))
    j.db.commit()
    return out


def rebuild_t3(j, db: str = "portfolio_book.sqlite", daily_fn=None, source: str = "trend") -> dict:
    """Gate ops_reconstructable (Oct 15): the trend books re-derived from the candles they decide on: the 10-coin books (T3 MAIN
    and SHADOW, portfolio_book.sqlite) on the Explorer's own daily candles; the 30-coin book (portfolio_book_t30.sqlite, source
    'trend30') on its own Binance daily candles (tier30.daily). For every logged daily decision each rated coin's close must equal
    that day's candle (0.05%), and its hold flag must follow T3's rule (close above its 20- and 50-day averages while Bitcoin is
    above its 50-day), recomputed with the Explorer's own average. A flag within 0.1% of a threshold counts as matched at the
    edge, not a mismatch (the averages are re-seeded from older candles). Every fill's price must lie inside its day's range."""
    import sqlite3

    from jarvis.service import watch_engine as W
    from src.intelligence.explorer_engine import Ema

    daily_fn = daily_fn or W._daily
    p = Path(j.dir) / db
    if not p.exists():
        return {"note": "no trend book", "match": True, "checked": 0}
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        decisions = [(int(t), json.loads(js)) for t, js in con.execute("SELECT day_t, json FROM decisions ORDER BY day_t")]
        fills = [json.loads(js) for (js,) in con.execute("SELECT json FROM fills ORDER BY seq")]
    finally:
        con.close()
    series: dict = {}

    def view(coin: str, day_t: int):
        if coin not in series:
            e20, e50, out = Ema(20), Ema(50), {}
            for b in daily_fn(j, coin):
                out[int(b[0])] = (b[4], e20.up(b[4]), e50.up(b[4]))
            series[coin] = out
        return series[coin].get(day_t - DAY)              # the last closed day before the decision

    bad, edge, checked = [], 0, 0
    for day_t, d in decisions:
        btc = view("BTC", day_t)
        if not btc:
            continue
        btc_on = btc[0] > btc[2]
        for coin, r in (d.get("ratings") or {}).items():
            v = view(coin, day_t)
            if not v:
                continue
            checked += 1
            close, e20, e50 = v
            hold = close > e50 and close > e20 and btc_on
            ok_close = not r.get("close") or abs(close / r["close"] - 1) < 5e-4
            if ok_close and hold == bool(r.get("hold")):
                continue
            if ok_close and min(abs(close / e20 - 1), abs(close / e50 - 1), abs(btc[0] / btc[2] - 1)) < 1e-3:
                edge += 1
                continue
            bad.append({"day": time.strftime("%Y-%m-%d", time.gmtime(day_t - DAY)), "coin": coin, "logged_hold": r.get("hold"), "rebuilt_hold": hold,
                        "logged_close": r.get("close"), "candle_close": close})
    cache: dict = {}
    f_checked, f_bad = 0, []
    for f in fills:
        bars = _day_bars(j, cache, f["coin"], int(f["t"]))
        if not bars and int(f["t"]) // DAY * DAY < int(j.now()) // DAY * DAY:   # a coin only the book's own candles hold
            own = _close_on_or_after(daily_fn(j, f["coin"]), int(f["t"]))
            bars = [("own", own)] if own and own[0] == int(f["t"]) // DAY * DAY else []
        if not bars:
            continue
        f_checked += 1
        if not _leg_ok(bars, f.get("px")):
            f_bad.append({"t": f["t"], "book": f.get("book"), "coin": f["coin"], "px": f.get("px"), "sources": {n: [b[3], b[2]] for n, b in bars}})
    out = {"decisions": len(decisions), "checked": checked, "at_the_edge": edge, "mismatches": len(bad) + len(f_bad), "fills": len(fills),
           "fills_checked": f_checked, "list": (bad + f_bad)[:20], "match": not bad and not f_bad}
    from jarvis.service import evidence_live

    evidence_live._rebuild_table(j)
    t = int(j.now())
    while j.db.execute("SELECT 1 FROM rebuild_log WHERE t=?", (t,)).fetchone():
        t += 1
    j.db.execute("INSERT INTO rebuild_log VALUES (?,?,?,?,?,?,?,?)",
                 (t, source, int(out["match"]), len(decisions), checked + f_checked, out["mismatches"], 0, json.dumps(out)[:4000]))
    j.db.commit()
    return out


def _iso_t(s) -> int | None:
    import datetime as _dt

    try:
        return int(_dt.datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except (ValueError, TypeError):
        return None


def close_counterfactuals(j, horizon_hours: float | None = None, limit: int = 5000) -> dict:
    """G7, closed at last: every OPEN counterfactual ("what if we had traded this refusal") in the hourly watch's
    decision store is scored at its horizon - forward return, best and worst excursion from the next bar's open -
    and labelled by the original close_case rule. Cases had been opened on every refusal since Sep 19 and never
    closed (audit 2026-10-14: 2,997 open, 0 closed; close_case was only ever called from tests)."""
    import sqlite3

    from src.intelligence.counterfactual import close_case

    p, bp = Path(j.dir) / "agent_decisions.sqlite", Path(j.dir) / "explorer_bars.sqlite"
    if not p.exists() or not bp.exists():
        return {"closed": 0, "skipped": 0, "note": "decision store or bars missing"}
    bars = sqlite3.connect(f"file:{bp}?mode=ro", uri=True, timeout=30)
    cache: dict[str, list[tuple]] = {}

    def series(coin: str) -> list[tuple]:
        if coin not in cache:
            cache[coin] = bars.execute("SELECT t, o, h, l, c FROM bars WHERE coin=? AND tf='1h' ORDER BY t", (coin,)).fetchall()
        return cache[coin]

    con = sqlite3.connect(str(p), timeout=30)
    closed = skipped = 0
    labels: dict[str, int] = {}
    now = int(j.now())
    try:
        rows = con.execute("SELECT id, payload_json FROM decisions WHERE payload_json LIKE '%\"counterfactual\"%' "
                           "AND payload_json LIKE '%\"status\": \"OPEN\"%' LIMIT ?", (limit,)).fetchall()
        for did, pj in rows:
            try:
                pay = json.loads(pj or "{}")
            except json.JSONDecodeError:
                skipped += 1
                continue
            case = pay.get("counterfactual") or {}
            coin = str(case.get("asset") or "").split("-")[0].split("/")[0]
            t0 = _iso_t(case.get("issued_at"))
            hz = float(horizon_hours or case.get("horizon_hours") or 4.0)
            S = series(coin) if coin else []
            if case.get("status") != "OPEN" or not S or not t0 or now < t0 + hz * 3600:
                skipped += 1
                continue
            win = [b for b in S if t0 <= b[0] < t0 + hz * 3600]
            if not win or win[-1][0] < t0 + (hz - 1.5) * 3600 or not win[0][1]:
                skipped += 1                                       # bars missing around the case: left OPEN, tried again next night
                continue
            p0 = win[0][1]                                         # the next bar's open: what a trade then would have paid
            fwd = 100 * (win[-1][4] / p0 - 1)
            mfe = 100 * (max(b[2] for b in win) / p0 - 1)
            mae = 100 * (min(b[3] for b in win) / p0 - 1)
            pay["counterfactual"] = close_case(case, fwd_return_pct=round(fwd, 2), mfe_pct=round(mfe, 2), mae_pct=round(mae, 2))
            con.execute("UPDATE decisions SET payload_json=? WHERE id=?", (json.dumps(pay, default=str), did))
            lab = pay["counterfactual"].get("label") or "?"
            labels[lab] = labels.get(lab, 0) + 1
            closed += 1
        con.commit()
    finally:
        con.close()
        bars.close()
    return {"closed": closed, "skipped": skipped, "labels": labels}


def worked_examples(n: int = 4) -> list[dict]:
    """G30: Madhav's own buys, rebuilt from candles (docs/casebook), as short worked examples: his read, his reasons, what followed."""
    try:
        cases = json.loads((ROOT / "docs" / "casebook" / "cases.json").read_text()).get("cases", [])
    except Exception:  # noqa: BLE001
        return []
    after = {}
    try:
        rb = json.loads((Path.home() / "ananta_runs" / "casebook" / "casebook_rebuild.json").read_text())
        for x in rb if isinstance(rb, list) else rb.get("cases", []):
            cid = (x.get("case") or {}).get("id") if isinstance(x.get("case"), dict) else x.get("case")
            after[cid] = x.get("after") or {}
    except Exception:  # noqa: BLE001
        pass
    out = []
    for c in cases[:n]:
        a = after.get(c["id"]) or {}
        out.append({"id": c["id"], "coin": c["coin"], "date": c["date"], "read": c.get("read"), "lot": c.get("lot_role"),
                    "his_reasons": c.get("his_reasons", [])[:4],
                    "after_30d_pct": (a.get("30d") or {}).get("close_pct"), "deepest_drop_after_pct": (a.get("deepest_drop_after") or {}).get("pct")})
    return out


def peers(j, start: str = "2026-10-04") -> dict:
    """G14: two classic playbooks on paper, tier-A coins, from start, NDAX costs (0.20% + the tier-A spread floor a side):
    BREAKOUT20  buy the next open after a close above the prior 20-day high; sell after a close under the prior 10-day low, or 20 days.
    ROTATE5     each Monday hold the 5 tier-A coins with the best 28-day return (equal weights), only while the exposure dial is open."""
    from jarvis.service import registry

    t0 = int(time.mktime(time.strptime(start, "%Y-%m-%d"))) - time.timezone
    k = 0.004
    try:
        coins = registry.members(j, "A")
    except Exception:  # noqa: BLE001
        coins = []
    data = {c: _daily(j, c) for c in coins}
    data = {c: D for c, D in data.items() if len(D) > 60}
    trades = []
    for c, D in data.items():
        i, n = 25, len(D)
        while i < n - 1:
            if D[i][0] >= t0 and D[i][4] > max(b[2] for b in D[i - 20:i]):
                e, entry = i + 1, D[i + 1][1]
                x = None
                for d in range(e, min(n, e + 20)):
                    if D[d][4] < min(b[3] for b in D[d - 10:d]):
                        x = d
                        break
                if x is None and e + 20 < n:
                    x = e + 20
                if x is None:
                    trades.append({"coin": c, "open": True, "pct": _pct(entry, D[-1][4])})
                    break
                trades.append({"coin": c, "open": False, "pct": round(100 * (D[x][4] / entry * (1 - k) ** 2 - 1), 2)})
                i = x
            i += 1
    closed = [t["pct"] for t in trades if not t["open"]]
    b20 = {"trades": len(trades), "closed": len(closed), "avg_closed_pct": round(statistics.mean(closed), 2) if closed else None,
           "open_now": sum(t["open"] for t in trades)}
    # ROTATE5
    try:
        from jarvis.service import exposure

        dial = exposure.dial_by_day(j)
    except Exception:  # noqa: BLE001
        dial = {}
    eq, weeks = 1.0, 0
    btc = _daily(j, "BTC")
    mondays = [b[0] for b in btc if b[0] >= t0 and time.gmtime(b[0]).tm_wday == 0]
    for m in mondays:
        if dial.get(time.strftime("%Y-%m-%d", time.gmtime(m))) == 0:
            continue
        ranks = []
        for c, D in data.items():
            ix = {b[0]: q for q, b in enumerate(D)}
            q = ix.get(m)
            if q is not None and q >= 28 and q + 7 < len(D):
                ranks.append((D[q][4] / D[q - 28][4] - 1, c, D[q + 1][1], D[q + 7][1]))
        top = sorted(ranks, reverse=True)[:5]
        if top:
            eq *= 1 + statistics.mean(b / a * (1 - k) ** 2 - 1 for _, _, a, b in top)
            weeks += 1
    return {"since": start, "coins": len(data), "BREAKOUT20": b20, "ROTATE5": {"weeks_held": weeks, "return_pct": round(100 * (eq - 1), 2)}}


def changes_after(j) -> list[dict]:
    """The change log (ledger.json "changes"), each with its after-metric where one can be measured."""
    try:
        led = json.loads((ROOT / "docs" / "repair_shop" / "ledger.json").read_text())
    except Exception:  # noqa: BLE001
        return []
    out = []
    for c in led.get("changes", []):
        x = dict(c)
        try:
            since = int(time.mktime(time.strptime(c["date"], "%Y-%m-%d")))
            if c.get("metric") == "brain_no_room":
                x["after"] = {"no_room_buys": j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch='JARVIS' AND detail LIKE '%\"no_room\": true%'").fetchone()[0]}
            elif c.get("metric") == "brain_dip":
                r = j.db.execute("SELECT COUNT(*), AVG(net_usd) FROM evidence_trades WHERE watch='JARVIS' AND status='CLOSED' AND entry_t >= ? "
                                 "AND detail LIKE '%invalidation%'", (since,)).fetchone()
                x["after"] = {"dip_trades_closed": r[0], "avg_usd": round(r[1], 2) if r[1] is not None else None}
            elif c.get("metric") == "brain_decisions":
                x["after"] = {"decisions_since": j.db.execute("SELECT COUNT(*) FROM brain_decisions WHERE t >= ? AND action != 'ERROR'", (since,)).fetchone()[0]}
        except Exception:  # noqa: BLE001
            pass
        out.append(x)
    return out

