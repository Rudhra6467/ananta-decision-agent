"""What changed since the plan was written (9 Nov 2026; Madhav, 18:25 Toronto: "how to make sure the agent adjusts itself according to the given
situation without sticking to old decisions when new challenges are being faced").

The morning view is written at 08:30 IST from what is known then. It was never looked at again: if the open came in the other way, Ananta
still read the 08:30 view as it stood. This module is the one owner of the second look. At each later moment it lays what the view was
written with beside what is true now, and says in plain words what changed and what the options line's own plan says for the new situation:

  at_preopen(view, pre, plan)      09:09 IST: the pre-open's matched prices against the overnight read the view had (GIFT Nifty at 08:30, or none)
  at_opening(view, pre, live, d0)  10:20 IST: the first hour against the pre-open, and the options line's own read of the open against the
                                   pre-open's (a read-only cross-check: on 6 Nov 2026 the line read Bank Nifty's open 0.46% below the official one)

What adjusts by itself is the read: what Ananta says and leads with. What does not adjust by itself is a rule: the options line, the managed
book and the practice book keep their written rules; when the situation is one a rule was not written for, this says so and it goes to Madhav.
Read-only; nothing is placed and no rule reads this.
"""
from __future__ import annotations

GAP_LINE = 0.25        # per cent: the options line's own gap lines (down <= -0.25%, up >= +0.25%)
DIFFER = 0.30          # per cent points between two reads of the same open before it is called a change
BIG_GAP = 1.0          # per cent
NAME = {"NIFTY": "Nifty", "BANKNIFTY": "Bank Nifty", "NIFTY 50": "Nifty", "NIFTY BANK": "Bank Nifty"}


def bucket(pct: float | None) -> str | None:
    if pct is None:
        return None
    return "down" if pct <= -GAP_LINE else ("up" if pct >= GAP_LINE else "flat")


def _view_gift(view: dict) -> float | None:
    g = (view.get("premarket") or {}).get("gift") or {}
    return g.get("change_pct") if str(g.get("taken_at") or "")[:10] == str(view.get("session")) else None


def at_preopen(view: dict | None, pre: dict, plan: dict | None = None) -> dict:
    """The 09:09 IST second look. view: the morning view's facts for today (or None); pre: the pre-open read; plan: sp1plan.words(...)."""
    idx = pre.get("indexes") or {}
    n, b = idx.get("NIFTY 50") or {}, idx.get("NIFTY BANK") or {}
    p = n.get("chg_pct")
    if p is None or not pre.get("index_moved"):
        return {"at": "pre_open", "changed": False, "points": [], "words": None, "note": "the pre-open gave no index reading"}
    view = view if view and str(view.get("session")) == str(pre.get("day")) else None
    pts, changed = [], False
    both = f"Nifty {p:+.1f}%" + (f", Bank Nifty {b['chg_pct']:+.1f}%" if b.get("chg_pct") is not None else "")
    g = _view_gift(view) if view else None
    if view is None:
        pts.append(f"No morning view was written for today; the pre-open indicates {both}.")
    elif g is None:
        changed = bucket(p) != "flat"
        pts.append(f"The 08:30 view was written with no overnight read; the pre-open now indicates {both}"
                   + (": that is new since the view." if changed else ": a flat open, as the view assumed."))
    elif bucket(g) != bucket(p) or abs(p - g) >= DIFFER:
        changed = True
        pts.append(f"At 08:30 GIFT Nifty pointed to {g:+.1f}%; the pre-open now indicates {both}: the open is "
                   f"{'stronger' if p > g else 'weaker'} than the view was written with.")
    else:
        pts.append(f"The pre-open ({both}) agrees with what GIFT Nifty showed at 08:30 ({g:+.1f}%): the view stands.")
    lv = ((view or {}).get("setup") or {}).get("scenario_levels") or {}
    last = n.get("last")
    if last and lv.get("up_above") and last > lv["up_above"]:
        pts.append(f"Nifty would open near {last:,.0f}, already above the line that makes it an up day ({lv['up_above']:,.0f}).")
    elif last and lv.get("down_below") and last < lv["down_below"]:
        pts.append(f"Nifty would open near {last:,.0f}, already below the line that makes it a down day ({lv['down_below']:,.0f}).")
    if abs(p) >= BIG_GAP:
        changed = True
        pts.append("A gap of 1% or more: the first 15 to 30 minutes show whether it holds or fills; the managed book skips any buy that opens more than 2% up.")
    for sym in ("NIFTY", "BANKNIFTY"):
        r = ((plan or {}).get("row") or {}).get(sym)
        if r:
            pts.append("Options line: " + r["words"])
    return {"at": "pre_open", "changed": changed, "points": pts, "words": " ".join(pts),
            "how_to_say_it": ("the morning view was written at 08:30 IST; this is the 09:09 second look. When changed is true, lead with the change and say "
                              "the view is overtaken on that point; the options line follows its own written plan for the open it gets")}


def crosscheck(d0_rows: list[dict], pre: dict | None) -> list[dict]:
    """The options line's own read of the 09:15 open beside the pre-open's matched open, per index. Read-only: the line's decision stands."""
    out = []
    idx = (pre or {}).get("indexes") or {}
    for r in d0_rows or []:
        st = r.get("state") or {}
        name = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}.get(str(r.get("index")))
        pv = idx.get(name) or {}
        if st.get("gap") is None or pv.get("chg_pct") is None:
            continue
        lg = round(100 * st["gap"], 2)
        same = bucket(lg) == bucket(pv["chg_pct"])
        row = {"index": r.get("index"), "line_open": st.get("open"), "line_gap_pct": lg, "line_row": bucket(lg), "preopen_open": pv.get("last"),
               "preopen_gap_pct": pv["chg_pct"], "preopen_row": bucket(pv["chg_pct"]), "same_row": same}
        row["words"] = (f"The options line read {NAME.get(r.get('index'))}'s open as {st.get('open'):,.0f} ({lg:+.2f}%, its '{bucket(lg)}' row); the pre-open's matched open was "
                        f"{pv.get('last'):,.0f} ({pv['chg_pct']:+.2f}%, '{bucket(pv['chg_pct'])}')"
                        + (": the same row of its plan." if same else ": a different row of its plan. Its decision stands as taken; this is noted for Madhav's review."))
        out.append(row)
    return out


def at_opening(view: dict | None, pre: dict | None, index_rows: dict, d0_rows: list[dict] | None = None) -> dict:
    """The 10:20 IST second look: the first hour against the pre-open, and the options line's read of the open against the pre-open's."""
    pts, changed = [], False
    idx = (pre or {}).get("indexes") or {}
    for name in ("NIFTY 50", "NIFTY BANK"):
        now, was = (index_rows.get(name) or {}).get("change_pct"), (idx.get(name) or {}).get("chg_pct")
        if now is None or was is None:
            continue
        if bucket(was) == "flat":
            how = "has stayed near flat" if bucket(now) == "flat" else f"has moved {'up' if now > 0 else 'down'} from a flat open"
        elif (now > 0) != (was > 0) and bucket(now) != "flat":
            how, changed = "has reversed", True
        elif abs(now) < 0.5 * abs(was):
            how, changed = "has given back more than half of its opening gap", True
        elif abs(now) >= abs(was):
            how = "has held or extended its opening gap"
        else:
            how = "has held most of its opening gap"
        pts.append(f"{NAME[name]} was indicated {was:+.1f}% before the open and is {now:+.1f}% after the first hour: it {how}.")
    cc = crosscheck(d0_rows or [], pre)
    for c in cc:
        if not c["same_row"]:
            changed = True
            pts.append(c["words"])
    return {"at": "opening", "changed": changed, "points": pts, "words": " ".join(pts) or None, "crosscheck": cc}
