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


def card(j, d: dict) -> dict:
    """One situation (a brain decision) in four views, plus the lesson the rules draw from it."""
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
    others = {"random_twin": {"coin": twin["coin"], "status": twin["status"], "net_usd": twin["net_usd"]} if twin else None, **_btc_window(j, t, t1)}
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
    if write:
        try:
            f = ROOT / "docs" / "repair_shop" / "weekly" / f"{out['to']}.md"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(_markdown(out))
            out["file"] = str(f.relative_to(ROOT))
        except Exception as exc:  # noqa: BLE001
            out["file_error"] = str(exc)[:120]
    return out


def _markdown(r: dict) -> str:
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
    L += ["## Credit (which knowledge moved decisions)", ""] + [f"- {k}: {json.dumps(v)}" for k, v in list(r["credit"].items())[:12]] + [""]
    L += ["## Change log, after", ""] + [f"- {c['change']}: {c.get('after')}" for c in r["changes"]] + [""]
    L += ["## Due", "", "- " + _due(), ""]
    L += ["## Peers since the brain started", "", f"```\n{json.dumps(r['peers'], indent=1)[:1500]}\n```", ""]
    return "\n".join(L)


def _due() -> str:
    try:
        led = json.loads((ROOT / "docs" / "repair_shop" / "ledger.json").read_text())
        for st in led.get("studies", []):
            sc = st.get("schedule") or {}
            if sc.get("next_due"):
                late = time.strftime("%Y-%m-%d") >= sc["next_due"]
                return f"Quarterly other-traders study ({st.get('id')}): next due {sc['next_due']}" + (" -- DUE NOW" if late else "")
    except Exception:  # noqa: BLE001
        pass
    return "nothing scheduled"


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


def rebuild_brain(j) -> dict:
    """G28: each closed brain trade (and its random twin) re-checked on the daily candles: the exit day's range must contain the exit
    price, and a stop exit needs the day's low at or under the stop. Mismatches are listed, never fixed silently."""
    from jarvis.service import watch_engine as W

    rows = j.db.execute(f"SELECT {', '.join(W.COLS)} FROM evidence_trades WHERE watch IN ('JARVIS','JARVIS_RANDOM') AND status='CLOSED'").fetchall()
    bad, checked = [], 0
    for r in rows:
        t = dict(zip(W.COLS, r))
        D = _daily(j, t["coin"])
        b = _close_on_or_after(D, int(t["exit_t"] or 0))
        if not b or b[0] > (t["exit_t"] or 0) + DAY:
            continue
        checked += 1
        lo, hi = b[3] * 0.995, b[2] * 1.005
        ok = lo <= (t["exit"] or 0) <= hi
        if "stop" in (t.get("exit_why") or "") and t.get("stop"):
            ok = ok and b[3] <= t["stop"] * 1.005
        if not ok:
            bad.append({"id": t["id"], "coin": t["coin"], "exit": t["exit"], "day_low": b[3], "day_high": b[2], "why": t.get("exit_why")})
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
