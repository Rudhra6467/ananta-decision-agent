"""Crypto, process only (Phase 6 of the 29 Oct 2026 plan): a read-only scorecard from the existing logs. Judged on whether Ananta did the
right thing, never on money. No new study, no rule change (Rule B until 14 Dec); H07 stays parked.

  python scripts/crypto_process_scorecard.py [days]     -> docs/repair_shop/crypto_process_<day>.md and .json (default window 14 days)

Reads jarvis.sqlite read-only (brain_decisions, trade_guard_log, rx_cards, rx_queue, officer_notes, ask_misunderstood, explorer_compare).
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path("/Users/vamsie/code/ananta-decision-agent/jarvis.sqlite")


def run(days: int = 14) -> dict:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    now = time.time()
    since = now - days * 86400
    day0 = dt.datetime.now(dt.timezone.utc).date().isoformat()
    out: dict = {"day": day0, "window_days": days, "rule": "process only; Rule B (no new crypto study or rule change before 14 Dec); H07 parked"}

    # 1. the brain's decisions: did every PASS say what would make it a TAKE (item 6)? any TAKE against the floor (item 7)?
    dec = [dict(r) for r in con.execute("select t, coin, action, plan from brain_decisions where t>?", (since,))]
    acts = collections.Counter(r["action"] for r in dec)
    passes = [r for r in dec if r["action"] == "PASS"]
    with_wait = 0
    for r in passes:
        try:
            p = json.loads(r["plan"] or "{}") if (r["plan"] or "").startswith("{") else {}
        except ValueError:
            p = {}
        if p.get("wait_for"):
            with_wait += 1
    out["decisions"] = {"total": len(dec), "by_action": dict(acts), "pass_with_wait_for": with_wait,
                        "pass_wait_share": round(with_wait / len(passes), 2) if passes else None}

    # 2. bad takes: entries the guard had to refuse (a take against a parked strategy or an unread kill switch is a process fault)
    guard = [dict(r) for r in con.execute("select day, book, coin, why from trade_guard_log where t>?", (since,))]
    why = collections.Counter((r["why"] or "").split(" (")[0][:60] for r in guard)
    out["guard"] = {"refusals": len(guard), "by_reason": dict(why.most_common(8)), "by_day": dict(collections.Counter(r["day"] for r in guard))}

    # 3. the officer's checks night by night (item 8)
    nights = []
    for r in con.execute("select day, facts from officer_notes where t>? order by day", (since,)):
        try:
            f = json.loads(r["facts"] or "{}")
        except ValueError:
            f = {}
        nights.append({"day": r["day"], "checks": {c.get("id"): c.get("state") for c in (f.get("checks") or [])}, "plan_line": bool(f.get("plan_line")),
                       "wait_arrived": len(f.get("wait_for_arrived") or [])})
    fails = collections.Counter(k for n in nights for k, v in n["checks"].items() if v == "FAIL")
    out["officer"] = {"nights": len(nights), "nights_with_plan_line": sum(1 for n in nights if n["plan_line"]), "fails_by_check": dict(fails), "rows": nights}

    # 4. the reconstruction cards: missed opportunities by class, and what waits for Madhav
    cards = []
    for r in con.execute("select day, card from rx_cards where t>? order by day", (since,)):
        try:
            c = json.loads(r["card"] or "{}")
        except ValueError:
            c = {}
        cards.append({"day": r["day"], "findings": collections.Counter(f.get("kind") for f in (c.get("findings") or []))})
    kinds = collections.Counter(k for c in cards for k, n in c["findings"].items() for _ in range(n))
    queue = [dict(r) for r in con.execute("select day, kind, lane, state, decision, words from rx_queue")]
    out["reconstruction"] = {"cards": len(cards), "findings_by_kind": dict(kinds),
                             "queue": {" | ".join(k): v for k, v in collections.Counter((q["kind"], q["lane"], q["state"]) for q in queue).items()},
                             "open_for_madhav": [q["words"][:160] for q in queue if q["lane"] == "DECISION" and q["state"] == "OPEN"]}

    # 5. the Ask: questions it could not read (misconceptions / communication gaps)
    mis = [dict(r) for r in con.execute("select t, kind, question from ask_misunderstood where t>?", (since,))]
    out["ask"] = {"misunderstood": len(mis), "by_kind": dict(collections.Counter(m["kind"] for m in mis)), "samples": [m["question"][:100] for m in mis[-5:]]}

    # 6. the explorer against the live books (data / agreement)
    ex = [dict(r) for r in con.execute("select t, agreement_pct, like_pct, live_n, mine_n from explorer_compare where t>? order by t", (since,))]
    out["explorer"] = {"compares": len(ex), "agreement_pct_last": ex[-1]["agreement_pct"] if ex else None,
                       "agreement_pct_mean": round(sum(float(e["agreement_pct"] or 0) for e in ex) / len(ex), 1) if ex else None}

    # 7. data gaps named by the guard or the officer
    gaps = []
    kill_days = sorted({r["day"] for r in guard if "kill switch" in (r["why"] or "")})
    if kill_days:
        gaps.append({"what": "kill switch unreadable (new entries paused, exits unaffected)", "when": kill_days,
                     "state": "not seen since discipline v1 (24 Oct)" if kill_days[-1] < "2026-10-24" else "still happening"})
    out["data_gaps"] = gaps

    # the verdicts in plain words
    words = []
    words.append(f"In the last {days} days the brain made {len(dec)} decisions: {acts.get('PASS', 0)} passes, {acts.get('TAKE', 0)} takes; "
                 f"{with_wait} of the passes said what would make them a take ({out['decisions']['pass_wait_share']:.0%} - item 6 is {'working' if (out['decisions']['pass_wait_share'] or 0) >= 0.6 else 'not yet consistent'})."
                 if passes else "the brain made no decision in the window.")
    parked = sum(n for k, n in why.items() if "PARKED" in k.upper() or "paused" in k)
    words.append(f"The guard refused {len(guard)} entries: {parked} against a parked strategy (the right refusal) and {len(guard) - parked} for other reasons" +
                 (f" ({', '.join(k for k in why if 'PARKED' not in k.upper() and 'paused' not in k)})." if len(guard) - parked else "."))
    since24 = sum(1 for n in nights if n["day"] >= "2026-10-24")
    words.append(f"The officer wrote {len(nights)} nightly notes, {out['officer']['nights_with_plan_line']} of the {since24} since the plan line exists (24 Oct) with the one plan line; checks that failed: " +
                 (", ".join(f"{k} on {n} night{'s' if n != 1 else ''}" for k, n in fails.items()) or "none") + ".")
    words.append(f"The reconstruction filed {len(cards)} cards: " + (", ".join(f"{n} {k}" for k, n in kinds.items()) or "no findings") +
                 f"; {len(out['reconstruction']['open_for_madhav'])} decision row{'s' if len(out['reconstruction']['open_for_madhav']) != 1 else ''} wait for Madhav.")
    words.append(f"The Ask could not read {len(mis)} questions ({', '.join(f'{n} {k}' for k, n in out['ask']['by_kind'].items()) or 'none'}).")
    words.append("Money is not judged here (Rule B); the paused books' old trades keep closing and are shown as 'already paused'.")
    out["words"] = words
    p = ROOT / "docs" / "repair_shop" / f"crypto_process_{day0}.json"
    p.write_text(json.dumps(out, indent=1, default=str))
    md = [f"# Crypto, process only: the scorecard for the {days} days to {day0}", "", "Read-only, from the logs; judged on whether Ananta did the right thing, never on money. "
          "Rule B: no new crypto study or rule change before 14 Dec; H07 stays parked.", ""] + [f"- {w}" for w in words] + ["", "## The officer's nights", "",
          "| night | idle cash | core exit | book bleed | explorer costs | plan line | wait-for arrivals |", "|---|---|---|---|---|---|---|"]
    md += [f"| {n['day']} | {n['checks'].get('idle_cash', '-')} | {n['checks'].get('core_exit', '-')} | {n['checks'].get('book_bleed', '-')} | {n['checks'].get('explorer_costs', '-')} | {'yes' if n['plan_line'] else 'no'} | {n['wait_arrived']} |" for n in nights]
    md += ["", "## Waiting for Madhav", ""] + ([f"- {w}" for w in out["reconstruction"]["open_for_madhav"]] or ["- nothing"])
    (ROOT / "docs" / "repair_shop" / f"crypto_process_{day0}.md").write_text("\n".join(md) + "\n")
    return out


if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 14)
    print("\n".join(r["words"]))
