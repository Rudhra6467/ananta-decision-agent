"""The nightly yardstick: one line, is Ananta better than luck? (Madhav, 23 Nov 2026: "Yes, let's do it" to keeping the comparison
nightly and short, adding the options line to it, and moving the search for new ideas to a weekly check-up.)

Reads what is already computed, adds nothing to any rule:
  stocks   the reference-traders league (india.others, manifests/others_<date>.json): the research picks against RANDOM at 1, 5 and 20 sessions
  options  the SP1 index line's own scored trades (paper/sp1/outcomes.jsonl): its net move per trade after costs against two plain
           yardsticks on the same days: always long the index (no choice of side) and a coin flip (zero before costs, so minus the cost)
Reference only, never a signal. india.morning prints the line; the reconstruction card and the Ask can read line()."""
from __future__ import annotations

import json
from pathlib import Path

from india import paths


def _json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def stocks(day: str, D: Path | None = None) -> dict | None:
    D = D or paths.data_dir()
    m = None                                       # the newest session's league on or before the day (a weekend has none of its own)
    for p in sorted((D / "manifests").glob("others_????-??-??.json"), reverse=True):
        if p.stem[7:] <= day:
            x = _json(p)
            if x and x.get("status") == "ok":
                m = x
                break
    if not m:
        return None
    out = {"_day": m.get("date")}
    for h in ("1", "5", "20"):
        x = (m.get("league") or {}).get(h) or {}
        if x.get("sessions"):
            out[h] = {"sessions": x["sessions"], "ananta": x.get("ANANTA"), "random": x.get("RANDOM"), "pct": x.get("ananta_pct_vs_random")}
    return out or None


def options(D: Path | None = None) -> dict | None:
    D = D or paths.data_dir()
    rows = []
    try:
        for line in (D / "paper" / "sp1" / "outcomes.jsonl").read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    except (OSError, ValueError):
        return None
    t = [r for r in rows if isinstance(r.get("index_proxy"), dict) and r.get("dir") in (1, -1)]
    if not t:
        return None
    net = [float(r["index_proxy"].get("net_bps") or 0) for r in t]
    cost = [float(r["index_proxy"].get("cost_bps") or 0) for r in t]
    raw = [float(r["index_proxy"].get("gross_bps") or 0) * r["dir"] for r in t]          # the index's own move over the trade
    longs = [raw[k] - cost[k] for k in range(len(t))]
    opt = [((r.get("legs") or {}).get("option") or {}).get("net_rs_realistic") for r in t]
    opt = [float(x) for x in opt if x is not None]
    n = len(t)
    return {"trades": n, "ananta_bps": sum(net) / n, "always_long_bps": sum(longs) / n, "coin_bps": -sum(cost) / n,
            "right_side": sum(1 for k in range(n) if raw[k] * t[k]["dir"] > 0), "option_rs": sum(opt),
            "option_rs_without_best": (sum(opt) - max(opt)) if opt else None}


def _p(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:+.2f}%"


def line(day: str, D: Path | None = None) -> str:
    """One plain line for the morning page."""
    parts = []
    s = stocks(day, D)
    if s:
        sday = s.pop("_day", None)
        bits = [f"{h} day{'s' if h != '1' else ''} {_p(v['ananta'])} vs random {_p(v['random'])}"
                f" ({'better' if (v['ananta'] or 0) > (v['random'] or 0) else 'worse'}; {round(100 * (v['pct'] or 0))}th percentile, {v['sessions']} sessions)"
                for h, v in s.items()]
        if bits:
            parts.append(f"Stocks (through {sday}): " + "; ".join(bits))
    o = options(D)
    if o:
        parts.append(f"Options line: {o['trades']} trades, {o['ananta_bps']:+.0f} bp a trade after costs vs always long {o['always_long_bps']:+.0f} bp and a coin flip "
                     f"{o['coin_bps']:+.0f} bp; right side {o['right_side']} of {o['trades']}; one lot Rs {o['option_rs']:,.0f}"
                     + (f" (Rs {o['option_rs_without_best']:,.0f} without its best trade)" if o.get("option_rs_without_best") is not None else ""))
    return ". ".join(parts) + "." if parts else "no yardstick yet for this session"
