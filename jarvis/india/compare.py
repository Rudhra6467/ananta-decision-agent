"""The managed book against your holdings and the Nifty 500, over the same days.

5 Nov 2026 (the 20-day synopsis): the managed book counts from its start (the 29 Oct close), while "as you have it" and the Nifty 500
counted from 22 Oct, so Ananta said "+1.51% against +2.52%" and the Money screen said "same start" for three different windows. On the
same days the managed book was about 2.3 points behind, not 1. One owner for the comparison: the Ask, Money and Today all read same_window().
"""
from __future__ import annotations

import json
from pathlib import Path

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _data() -> Path:
    """The India data folder every India screen reads (views.DATA, which follows ANANTA_INDIA_DATA). 12 Nov 2026 (the confirm check of
    repair 4, C6): this file alone was fixed to the home folder's copy, so a check run on a copy mixed the copy's total with the live
    comparison."""
    from jarvis.india import views

    return Path(views.DATA)


def _day(d: str) -> str:
    y, m, dd = str(d).split("-")
    return f"{int(dd)} {MONTHS[int(m) - 1]}"


def same_window(data: Path | None = None) -> dict:
    """Managed, your holdings as you have them, and the Nifty 500, all from the close before the managed book's first session."""
    given, data = data is not None, Path(data) if data is not None else _data()
    try:
        v = json.loads((data / "paper" / "account" / "view.json").read_text()).get("benchmark") or {}
        rows = [json.loads(x) for x in (data / "paper" / "account" / "benchmark.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return {"ready": False, "words": "the comparison is not built yet"}
    start = v.get("managed_start_day")
    rows = [r for r in rows if r.get("day")]
    base = [r for r in rows if str(r["day"]) < str(start or "")]
    last = rows[-1] if rows else {}
    if not start or not base or last.get("managed_ret_pct") is None or not base[-1].get("frozen_inr") or not last.get("frozen_inr"):
        return {"ready": False, "words": "the managed book has no session scored yet"}
    b = base[-1]
    # 12 Nov 2026 (the keen outside audit, G-12): the first benchmark row, labelled 29 Oct, was written after the 30 Oct close and holds
    # that close's prices, the very prices the managed book opened at (its value there is the book's start); the Nifty 500 in it runs only
    # to 29 Oct. So the book and your holdings counted from the 30 Oct close, the index from 29 Oct, and the foot said "the 29 Oct close"
    # for all three. The index now counts from the managed book's start day too (the row labelled that day carries the index through that
    # day's close), and the window is named by that day.
    bi = next((r for r in rows if str(r["day"]) == str(start) and r.get("nifty500_ret_pct") is not None), b)
    yours = (last["frozen_inr"] / b["frozen_inr"] - 1) * 100
    n500 = ((1 + (last.get("nifty500_ret_pct") or 0) / 100) / (1 + (bi.get("nifty500_ret_pct") or 0) / 100) - 1) * 100
    managed = float(last["managed_ret_pct"])
    s = v.get("managed_sessions") or last.get("managed_sessions")
    # and the three lines are not equally invested (G-12): the managed book and your holdings keep cash and the options money, the index is
    # all stocks; your holdings are also said stock for stock (their cash and options money never move)
    exp: dict = {}
    try:
        fz = json.loads((data / "paper" / "account" / "frozen.json").read_text())
        held = float(fz.get("cash_inr") or 0) + float(fz.get("options_inr") or 0)
        if 0 < held < float(b["frozen_inr"]):
            exp["yours_stock_pct"] = round(100 * (last["frozen_inr"] - held) / last["frozen_inr"])
            exp["yours_stock_for_stock_pct"] = round(((last["frozen_inr"] - held) / (b["frozen_inr"] - held) - 1) * 100, 2)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        mv = json.loads((data / "paper" / "managed" / "view.json").read_text())
        exp["managed_stock_pct"] = round(100 * float(mv["stocks_inr"]) / float(mv["value_inr"]))
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError):
        pass
    ew = ""
    if "managed_stock_pct" in exp and "yours_stock_pct" in exp:
        ew = (f"Not equally in stocks: the managed book about {exp['managed_stock_pct']}%, your holdings about {exp['yours_stock_pct']}%, the index all"
              + (f"; stock for stock, your holdings {exp['yours_stock_for_stock_pct']:+.2f}%." if "yours_stock_for_stock_pct" in exp else "."))
    # 12 Nov 2026 (the outside check of repair 4, N2): from G-11 the managed book's figure carries the options line's paper result, while
    # your holdings keep their options money flat; said beside it, with the book like for like (its options money flat too)
    # 12 Nov 2026 (the confirm check of repair 4, C3): the comparison's managed figure holds the options line's result, so it says what it
    # leaves out, as every total does (G-01), counted as the totals count it
    try:
        from jarvis.india import surfaces as _sf

        lo = len(_sf._sp1_unscored(data) if given else _sf._sp1_unscored())
    except Exception:  # noqa: BLE001
        lo = 0
    # the second confirm check (D3): a figure written before the options line was counted (no managed_options_inr in its row) holds no
    # options result, so nothing is "left out" of it
    counts_options = "managed_options_inr" in last
    left_words = f"{lo} options trade{'s' if lo != 1 else ''} left out" if lo and counts_options else ""
    ow, like = "", None
    opt = last.get("managed_options_inr")
    pm = lambda x, d=2: f"{x:+.{d}f}".replace("-", "−")      # noqa: E731   a minus sign, as the money beside it (D4)
    if isinstance(opt, (int, float)) and opt and last.get("managed_inr"):
        start_v = float(last["managed_inr"]) / (1 + managed / 100)
        pts = 100 * float(opt) / start_v
        like = managed - pts
        sign = f"{'+' if opt >= 0 else '−'}₹{abs(opt):,.0f}"
        ow = (f"The book counts the options line's result ({sign}, about {abs(pts):.1f} points); with options flat, like yours, {pm(like)}%; "
              f"{left_words}." if left_words else
              f"The book counts the options line's result ({sign}, about {abs(pts):.1f} points); with its options flat, as yours are, it is "
              f"{pm(like)}%.")
    return {"ready": True, "since": str(start), "since_words": _day(start), "through": last["day"], "through_words": _day(last["day"]),
            "managed_pct": round(managed, 2), "yours_pct": round(yours, 2), "nifty500_pct": round(n500, 2),
            "managed_minus_yours_pts": round(managed - yours, 2), "sessions": s, "exposure": exp, "exposure_words": ew,
            "managed_options_inr": opt if isinstance(opt, (int, float)) else None,
            "managed_like_for_like_pct": round(like, 2) if like is not None else None, "options_words": ow,      # a screen's line: 22 words at most
            "left_out": lo, "left_out_words": left_words,
            "words": (f"From the {_day(start)} close (the managed book's start) to {_day(last['day'])}: the managed book {managed:+.2f}%, "
                      f"your holdings as you have them {yours:+.2f}%, the Nifty 500 {n500:+.2f}% (price index). "
                      + (ow + " " if ow else (f"{left_words}. " if left_words else ""))
                      + (ew + " " if ew else "") + f"Session {s} of 60; nothing is read into the gap before session 60.")}
