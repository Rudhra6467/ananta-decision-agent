"""The managed book's decision audit, every evening after its score (Madhav, 14 Nov 2026 22:17 Toronto: "audits like these needs to be
done often I guess before finalising v1"). It repeats, from the book's own records, the checks of the 14 Nov review that found the 2 Nov
cuts 0 of 10, a replacement behind its cut, ₹27,614 idle through a rally and eight sessions of no change.

It reads only paper/managed/* and changes nothing: no rule, no plan, no fill. Each check says OK, WATCH or FLAG with one plain sentence;
a FLAG is a finding for the next review, not an action.

  python -m india.managed_audit           writes paper/managed/audit.json, appends paper/managed/audit_history.jsonl, writes
                                          reports/managed_audit_<day>.md
"""
from __future__ import annotations

import datetime as dt
import json
import sys

from india import managed as m
from india import paths

LIMITS = {"cuts_min_scored": 5, "cuts_right_floor_pct": 40, "reps_min_scored": 3, "idle_cash_pct": 10, "idle_sessions": 5,
          "no_change_watch": 5, "no_change_flag": 10, "crowd_share_pct": 30, "lag_market_pts": 2.0}


def _check(name: str, status: str, words: str, **facts) -> dict:
    return {"check": name, "status": status, "words": words, **facts}


def _scored(rows: list[dict], side: str, h: str, key: str) -> list[float]:
    return [x for x in ((r.get("scored") or {}).get(h, {}).get(key) for r in rows if r.get("side") == side and r.get("filled")) if x is not None]


def audit() -> dict:
    d = m._dir()
    view = m._load(d / "view.json", {}) or {}
    book = m._load(d / "state.json", {}) or {}
    led = m._jsonl(d / "ledger.jsonl")
    plans = m._plans()
    day = str(view.get("day") or "")
    L = LIMITS
    out = []

    # 1. cuts against the market, at 5 and 20 sessions
    for h in ("+5", "+20"):
        xs = _scored(led, "SELL", h, "vs_market_pct")
        right = sum(1 for x in xs if x < 0)
        if len(xs) < L["cuts_min_scored"]:
            out.append(_check(f"cuts_vs_market_{h[1:]}", "OK", f"{len(xs)} cut{'s' if len(xs) != 1 else ''} scored at {h} sessions: too few to judge.", right=right, scored=len(xs)))
            continue
        pct = 100 * right / len(xs)
        st = "FLAG" if pct < L["cuts_right_floor_pct"] else "OK"
        out.append(_check(f"cuts_vs_market_{h[1:]}", st, f"{right} of {len(xs)} cuts did worse than the Nifty 500 after {h[1:]} sessions ({pct:.0f}%)"
                          + (": the cuts are selling names that then beat the market." if st == "FLAG" else "."), right=right, scored=len(xs), right_pct=round(pct, 1)))

    # 2. each replacement against the cut it replaced
    for h in ("+5", "+20"):
        xs = _scored(led, "BUY", h, "minus_cut_pct")
        beat = sum(1 for x in xs if x > 0)
        if len(xs) < L["reps_min_scored"]:
            out.append(_check(f"replacements_vs_cut_{h[1:]}", "OK", f"{len(xs)} replacement{'s' if len(xs) != 1 else ''} scored at {h} sessions: too few to judge.", beat=beat, scored=len(xs)))
            continue
        st = "FLAG" if beat < len(xs) / 2 else "OK"
        worst = min(((r["symbol"], r.get("for_cut"), r["scored"][h]["minus_cut_pct"]) for r in led if r.get("side") == "BUY" and "minus_cut_pct" in (r.get("scored") or {}).get(h, {})), key=lambda t: t[2])
        out.append(_check(f"replacements_vs_cut_{h[1:]}", st, f"{beat} of {len(xs)} replacements did better than the stock they replaced after {h[1:]} sessions; "
                          f"the worst, {worst[0]} for {worst[1]}, by {worst[2]:+.1f} points.", beat=beat, scored=len(xs)))

    # 3. idle cash: share of the stock book in cash, and sessions since the book last bought
    sp = view.get("split") or {}
    share = sp.get("cash_share_pct")
    buys = sorted(r["for_session"] for r in led if r.get("side") == "BUY" and r.get("filled"))
    since = m.sessions_between(buys[-1], day) if buys and day > buys[-1] else (len(book.get("sessions") or []) if not buys else 0)
    if share is None:
        out.append(_check("idle_cash", "WATCH", "The cash share could not be read from the view.", sessions_since_buy=since))
    else:
        st = "FLAG" if share > L["idle_cash_pct"] and since >= L["idle_sessions"] else ("WATCH" if share > L["idle_cash_pct"] else "OK")
        out.append(_check("idle_cash", st, f"₹{sp.get('cash_inr', 0):,.0f} in cash, {share:.0f}% of stocks and cash; the last buy was {since} session{'s' if since != 1 else ''} ago"
                          + (", so freed money is sitting out the market." if st == "FLAG" else "."), cash_inr=sp.get("cash_inr"), cash_share_pct=share, sessions_since_buy=since))

    # 4. how many plans in a row said no change
    streak = 0
    for p in reversed(plans):
        if p.get("error") or not p.get("no_change"):
            break
        streak += 1
    st = "FLAG" if streak >= L["no_change_flag"] else ("WATCH" if streak >= L["no_change_watch"] else "OK")
    out.append(_check("no_change_streak", st, f"{streak} plan{'s' if streak != 1 else ''} in a row with no change"
                      + (" while money is idle: check that the book can still act." if st != "OK" else "."), streak=streak))

    # 5. crowded cutting: one plan cutting a large share of the holdings at once
    def held_before(session: str) -> int:
        """The book's holdings just before a plan filled, walked back from today through the ledger."""
        s = set((book.get("positions") or {}).keys())
        for r in sorted((r for r in led if r.get("filled") and r.get("for_session", "") >= session), key=lambda r: r["for_session"], reverse=True):
            if r.get("side") == "BUY":
                s.discard(r["symbol"])
            else:
                s.add(r["symbol"])
        return len(s)
    worst = None
    for p in plans:
        n_cut = len([c for c in p.get("cuts") or [] if c.get("kind") not in ("stop", "weak")])
        pos = held_before(p["for_session"]) if n_cut else 0
        if n_cut and pos:
            sh = 100 * n_cut / pos
            if worst is None or sh > worst[1]:
                worst = (p["for_session"], sh, n_cut)
    if worst and worst[1] > L["crowd_share_pct"]:
        out.append(_check("crowded_cuts", "FLAG", f"The plan for {worst[0]} cut {worst[2]} holdings at once (about {worst[1]:.0f}% of the book): "
                          "on history, cuts made when many names look weak together do no better than chance.", session=worst[0], cuts=worst[2]))
    else:
        out.append(_check("crowded_cuts", "OK", "No plan has cut a large share of the book at once."))

    # 6. the stock book against the market
    lag = sp.get("stocks_vs_market_pct")
    if lag is None:
        out.append(_check("stocks_vs_market", "WATCH", "The stock book's result against the Nifty 500 could not be counted."))
    else:
        st = "WATCH" if lag < -L["lag_market_pts"] else "OK"
        out.append(_check("stocks_vs_market", st, f"Stocks and cash {sp['stocks_cash_pct']:+.1f}% against the Nifty 500's {sp['market_pct']:+.1f}% "
                          f"({lag:+.1f} points); options {sp['options_inr']:+,} rupees on top.", stocks_vs_market_pct=lag))

    # 7. the plan chain
    ok, chain = m.chain_ok()
    out.append(_check("plan_chain", "OK" if ok else "FLAG", chain))

    flags = [c for c in out if c["status"] == "FLAG"]
    res = {"built_at": m._now(), "day": day, "session": (view.get("clock") or {}).get("sessions"), "limits": L, "checks": out,
           "flags": len(flags), "watches": sum(1 for c in out if c["status"] == "WATCH"),
           "words": (f"{len(flags)} finding{'s' if len(flags) != 1 else ''} for review: " + " ".join(c["words"] for c in flags)) if flags else "No findings: the book's decisions pass every check."}
    return res


def words(a: dict) -> str:
    L = [f"# Managed book audit, {a['day']} (session {a.get('session')})", "", a["words"], "", "| check | status | what it found |", "|---|---|---|"]
    L += [f"| {c['check']} | {c['status']} | {c['words']} |" for c in a["checks"]]
    return "\n".join(L) + "\n\nPaper only. The audit changes nothing; a FLAG goes to the next review.\n"


def main() -> dict:
    a = audit()
    d = m._dir()
    (d / "audit.json").write_text(json.dumps(a, indent=1))
    hist = [r for r in m._jsonl(d / "audit_history.jsonl") if r.get("day") != a["day"]]
    hist.append({"day": a["day"], "built_at": a["built_at"], "flags": a["flags"], "watches": a["watches"],
                 "status": {c["check"]: c["status"] for c in a["checks"]}})
    m._write_jsonl(d / "audit_history.jsonl", hist)
    rep = paths.data_dir() / "reports"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / f"managed_audit_{a['day'] or dt.date.today().isoformat()}.md").write_text(words(a))
    return a


if __name__ == "__main__":
    print(words(main()) if (sys.argv[1:] or ["run"])[0] == "run" else "usage: python -m india.managed_audit")
