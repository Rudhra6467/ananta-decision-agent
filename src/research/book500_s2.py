"""Worker stage S2 (plan of Oct 11): the $500 book's backtest, rerun with the cost each coin really has on NDAX.

src/research/book500.py charges every coin the cost the registry assumes: NDAX's 0.20% fee plus an assumed half-spread (the median of 5 order-book
snapshots for the ten lab coins, a floor for the rest; src/intelligence/ndax_costs.py). Since Oct 11 the worker Mac has recorded NDAX's
bid and ask every minute (jarvis/service/ndax_spreads.py). This reruns the same backtest, rule for rule (book500.py is not touched),
with each coin's cost per side = the 0.20% fee + its 75th-percentile half-spread over the last 14 full days.

The reading rule, written before the run and not changed after it:
  1. A coin is MEASURED when it has at least MIN_MINUTES (10,000, about 7 days) of quotes. The others keep the assumed cost and are
     listed as not measured.
  2. The whole book is rerun on both periods (DISCOVERY 2018-2023, CONFIRM 2024-) under the assumed cost and under the measured one;
     both lines are shown side by side.
  3. Each tier-A coin's own H07 setups are run alone over the whole history under both costs. A coin is FLAGGED when its average trade
     after costs is above zero under the assumed cost and zero or below under the measured one (its edge was the cost assumption).
     A coin with fewer than MIN_TRADES (5) trades is not judged.
  4. Nothing changes by itself: the coin list, registry.cost() and the live book stay as they are. A flagged coin is a question for
     Madhav, never a change.

    python3 ~/ananta_runs/svc_env_run.py "from src.research import book500_s2 as S; S.main(['run', '--request'])"
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from src.intelligence.ndax_costs import NDAX_FEE
from src.research import book500 as B

MIN_MINUTES = 10_000
MIN_TRADES = 5
WHOLE = ("2018-01-01", "2099-01-01")
KEEP = ("from", "to", "end_cad", "return_pct", "max_fall_pct", "setup_trades", "setup_win_rate", "setup_avg_pct", "brakes_fired", "sizes_ok")
DEFAULT_OUT = "~/ananta_runs/book500_s2"
DEFAULT_FX = "~/ananta_runs/book500/usdcad.json"        # the Bank of Canada series the Oct 11 backtest used


def measured_costs(tab: dict, assumed: dict, min_minutes: int = MIN_MINUTES) -> tuple[dict, dict]:
    """(cost per side for the rerun, what was seen per coin). A coin with too few quotes keeps its assumed cost."""
    cost, seen = dict(assumed), {}
    by = {r["coin"]: r for r in tab.get("coins", [])}
    for c, a in assumed.items():
        r = by.get(c)
        ok = bool(r) and r["minutes"] >= min_minutes and r.get("half_spread_p75_pct") is not None
        seen[c] = {"assumed_pct": round(100 * a, 3), "minutes": r["minutes"] if r else 0, "measured": ok}
        if ok:
            cost[c] = NDAX_FEE + r["half_spread_p75_pct"] / 100
            seen[c]["s2_pct"] = round(100 * cost[c], 3)
    return cost, seen


def judge_coin(base: dict, s2: dict) -> dict:
    """One coin alone. base and s2 are simulate() results of a book that trades only this coin's H07 setups, under the two costs."""
    n = s2.get("setup_trades") or 0
    a, b = base.get("setup_avg_pct"), s2.get("setup_avg_pct")
    row = {"trades": n, "avg_pct_assumed": a, "avg_pct_measured": b, "win_rate_measured": s2.get("setup_win_rate")}
    if n < MIN_TRADES or a is None or b is None:
        row["verdict"] = "TOO_FEW_TRADES"
    elif a > 0 and b <= 0:
        row["verdict"] = "FLAGGED"
    elif b > 0:
        row["verdict"] = "HOLDS"
    else:
        row["verdict"] = "NEVER_HAD_EDGE"                # already zero or below under the assumed cost
    return row


def sentence(rep: dict) -> str:
    """The result in plain words (for the console and for the one request that tells Madhav)."""
    c = rep["book"].get("CONFIRM") or next(iter(rep["book"].values()), None) or {}
    a, m = (c.get("assumed") or {}).get("end_cad"), (c.get("measured") or {}).get("end_cad")
    flagged = rep["flagged"]
    return (f"S2 finished: NDAX's measured cost on {rep['days_measured']} full days, {len(rep['measured'])} of "
            f"{len(rep['measured']) + len(rep['not_measured'])} coins measured. The $500 book over the confirm period "
            f"({(c.get('assumed') or {}).get('from')} on) ends at C${a} with the assumed costs and C${m} with the measured ones. "
            + (f"Coins whose own edge is gone at the measured cost: {', '.join(flagged)}." if flagged
               else "No coin's edge disappears at its measured cost.")
            + " Nothing was changed; the coin list is your decision.")


def file_request(j, rep: dict) -> bool:
    """One repair-board request telling Madhav the result, once per run date. True when it was filed now."""
    key = "kb:s2_request:" + rep["written"][:10]
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
        return False
    from jarvis.service import requests_log

    requests_log.add(j, "data", sentence(rep) + " Full result: " + rep["file"], about="worker stage S2", by="ananta-auto")
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?, ?)", (key, str(int(j.now()))))
    j.db.commit()
    return True


def run(out: Path, days: int = 14, fx: Path | None = None, get=None, table_fn=None, request: bool = False) -> dict:
    from jarvis.service import core, ndax_spreads, registry

    j = core.from_env()
    reg = registry.load(j)
    tier_a = sorted(c for c, k in reg["coins"].items() if k.get("ndax") and k.get("tier") == "A")
    inst = B.instruments(get)
    C = B.load(sorted(set(tier_a) | set(B.CORE)), Path(os.path.expanduser(str(fx or DEFAULT_FX))))
    assumed = {c: registry.cost(c, reg) for c in C}
    tab = (table_fn or ndax_spreads.table)(days)
    s2, seen = measured_costs(tab, assumed)
    rep: dict = {"written": time.strftime("%Y-%m-%d %H:%M"), "days_measured": len(tab.get("days", [])), "days": tab.get("days", []),
                 "min_minutes": MIN_MINUTES, "min_trades": MIN_TRADES, "rule": __doc__.split("The reading rule")[1].split("python3")[0].strip(),
                 "measured": sorted(c for c, v in seen.items() if v["measured"]), "not_measured": sorted(c for c, v in seen.items() if not v["measured"]),
                 "book": {}, "coins": []}
    for name, (a, b) in B.SPLITS.items():
        t0, t1 = B._t(a), B._t(b)
        x, y = B.simulate(C, tier_a, inst, assumed, t0, t1), B.simulate(C, tier_a, inst, s2, t0, t1)
        rep["book"][name] = {"assumed": {k: x.get(k) for k in KEEP}, "measured": {k: y.get(k) for k in KEEP},
                             "benchmarks_assumed": B.bench(C["BTC"], assumed["BTC"], t0, t1),
                             "benchmarks_measured": B.bench(C["BTC"], s2["BTC"], t0, t1)}
    t0, t1 = B._t(WHOLE[0]), B._t(WHOLE[1])
    for c in sorted(set(tier_a) & set(C)):
        row = {"coin": c, **seen[c]}
        if seen[c]["measured"]:
            row.update(judge_coin(B.simulate(C, [c], inst, assumed, t0, t1), B.simulate(C, [c], inst, s2, t0, t1)))
        else:
            row["verdict"] = "NOT_MEASURED"
        rep["coins"].append(row)
    rep["flagged"] = [r["coin"] for r in rep["coins"] if r["verdict"] == "FLAGGED"]
    out.mkdir(parents=True, exist_ok=True)
    rep["file"] = str(out / "s2_result.json")
    rep["line"] = sentence(rep)
    Path(rep["file"]).write_text(json.dumps(rep, indent=1))
    if request:
        file_request(j, rep)
        try:
            from jarvis.service import due_list

            due_list.mark_done(j, "S2-SPREADS", note=rep["line"][:200])
        except Exception as exc:  # noqa: BLE001 - the result is written; the due list must not hide it
            rep["due_list_error"] = str(exc)[:200]
    return rep


def main(argv: list[str]) -> int:
    if not argv or argv[0] != "run":
        print(__doc__)
        return 2
    out = Path(os.path.expanduser(argv[argv.index("--out") + 1] if "--out" in argv else DEFAULT_OUT))
    rep = run(out, request="--request" in argv)
    print(rep["line"])
    for r in rep["coins"]:
        print(f"{r['coin']:>6} {r['verdict']:<15} assumed {r.get('assumed_pct')}%  measured {r.get('s2_pct')}%  trades {r.get('trades')}  "
              f"avg {r.get('avg_pct_assumed')} -> {r.get('avg_pct_measured')}")
    print("written", rep["file"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
