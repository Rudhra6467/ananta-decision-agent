"""Point-in-time universe (review #22): which coins were the most traded AT EACH MONTH, using only earlier months.

Universe rule v1 ranks each coin on its own last 24 months, so a coin that was huge in 2021 and collapsed but kept trading
thinly (LUNA, FTT) ranks low today and is missing from "today's top 30". This builds the month-by-month ranking instead.

  monthly_values()   traded value (USD) per coin per month for every eligible symbol of rule v1 (the small monthly 1d files,
                     cached in reports/monthly_values.json)
  membership(n)      for each month M: the top n coins by the sum of traded value in the 3 months BEFORE M (no look-ahead),
                     same exclusions as rule v1 (the eligible table); written to reports/pit_top{n}.json
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

from src.lake import root
from src.lake import binance_vision as bv
from src.lake import universe as U


def monthly_values(workers: int = 12, log=print) -> dict:
    p = root() / "reports" / "monthly_values.json"
    have = json.loads(p.read_text()) if p.exists() else {}
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())
    syms = [r["symbol"] for r in u["table"]]

    def one(s: str):
        if s in have:
            return s, have[s]
        keys = sorted(k for k, _ in bv.list_keys(f"data/spot/monthly/klines/{s}/1d/") if k.endswith(".zip"))
        out = {}
        for k in keys:
            v = U._month_value(k, bv._get)
            if v is not None:
                out[re.search(r"-(\d{4}-\d{2})\.zip$", k).group(1)] = v
        return s, out

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (s, v) in enumerate(pool.map(one, syms)):
            have[s] = v
            if i % 25 == 0:
                log(f"monthly values {i + 1} of {len(syms)}")
                p.write_text(json.dumps(have))
    p.write_text(json.dumps(have))
    return have


def _months(a: str, b: str) -> list[str]:
    y, m = map(int, a.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def membership(n: int = 30, look: int = 3) -> dict:
    mv = json.loads((root() / "reports" / "monthly_values.json").read_text())
    allm = sorted({m for v in mv.values() for m in v})
    months = _months(allm[0], allm[-1])
    out = {}
    for i, M in enumerate(months):
        prev = months[max(0, i - look): i]
        if len(prev) < look:
            continue
        score = {s: sum(v.get(m, 0.0) for m in prev) for s, v in mv.items() if all(m in v for m in prev)}
        out[M] = [s for s, _ in sorted(score.items(), key=lambda x: -x[1])[:n]]
    ever = sorted({s for v in out.values() for s in v})
    res = {"rule": f"top {n} by traded value over the {look} months before each month (earlier data only)", "months": out, "ever": ever}
    (root() / "reports" / f"pit_top{n}.json").write_text(json.dumps(res, indent=1))
    return res
