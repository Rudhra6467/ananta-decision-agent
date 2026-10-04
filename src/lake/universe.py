"""Choosing the 100-120 coins by a written rule, before looking at any result (so the universe cannot be picked to flatter a strategy).

Rule v1 (2026-10-04):
  1. Every Binance spot pair against USDT that Data Vision publishes, delisted ones included (leaving out the coins that died would
     make every strategy look better than it was: survivorship).
  2. Out: stablecoins and fiat (USDC, FDUSD, TUSD, DAI, EUR, ...), leveraged tokens (UP/DOWN/BULL/BEAR), wrapped copies (WBTC, WBETH).
  3. At least 12 months of monthly files.
  4. Ranked by the median of each month's traded value (quote volume, from the daily candles); top N.
The ranking uses the small daily files only (one download per coin-month of about 2 KB), not the 1-minute data.
The chosen list is written to reports/universe_v1.json with every coin's numbers, so the choice can be checked.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from src.lake import root
from src.lake.binance_vision import _get, list_keys

STABLE = {"USDC", "BUSD", "TUSD", "USDP", "DAI", "FDUSD", "PAX", "USDS", "USDSB", "SUSD", "UST", "USTC", "EUR", "GBP", "AUD", "TRY", "BRL",
          "AEUR", "EURI", "PAXG", "XUSD", "USD1", "RLUSD", "BFUSD", "U"}
WRAPPED = {"WBTC", "WBETH", "BETH", "BNSOL", "STETH"}
LEVERAGED = re.compile(r"(UP|DOWN|BULL|BEAR)$")


def candidates(get: Callable = _get) -> list[str]:
    """All USDT spot pairs with monthly 1d files, after the exclusions."""
    syms, marker = [], ""
    while True:
        params = {"prefix": "data/spot/monthly/klines/", "delimiter": "/"}
        if marker:
            params["marker"] = marker
        xml = get("https://s3-ap-northeast-1.amazonaws.com/data.binance.vision", params).text
        found = re.findall(r"<Prefix>data/spot/monthly/klines/([A-Z0-9]+)/</Prefix>", xml)
        syms += found
        if "<IsTruncated>true</IsTruncated>" not in xml or not found:
            break
        marker = f"data/spot/monthly/klines/{found[-1]}/"
    out = []
    for s in syms:
        if not s.endswith("USDT"):
            continue
        base = s[:-4]
        if not base or base in STABLE or base in WRAPPED or LEVERAGED.search(base):
            continue
        out.append(s)
    return sorted(set(out))


def rank(symbols: list[str], top: int = 120, min_months: int = 12, get: Callable = _get, log: Callable = print) -> dict:
    """Median monthly traded value from the daily files; top N with at least min_months of history."""
    import io
    import statistics
    import zipfile

    rows = []
    for k, s in enumerate(symbols):
        ms = [x for x in list_keys(f"data/spot/monthly/klines/{s}/1d/", get) if x[0].endswith(".zip")]
        if len(ms) < min_months:
            continue
        vols, first, last = [], None, None
        for key, _ in ms:
            r = get(f"https://data.binance.vision/{key}")
            if r.status_code != 200:
                continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                txt = z.read(z.namelist()[0]).decode()
            qv = 0.0
            for line in txt.splitlines():
                f = line.split(",")
                if len(f) > 7 and f[0].isdigit():
                    qv += float(f[7])
            vols.append(qv)
            m = re.search(r"-(\d{4}-\d{2})\.zip$", key).group(1)
            first, last = first or m, m
        if vols:
            rows.append({"symbol": s, "months": len(vols), "first": first, "last": last, "median_month_usd": round(statistics.median(vols))})
        if k % 25 == 0:
            log(f"ranked {k + 1} of {len(symbols)}")
    rows.sort(key=lambda r: -r["median_month_usd"])
    chosen = rows[:top]
    out = {"rule": "v1", "candidates": len(symbols), "eligible": len(rows), "top": top, "chosen": [r["symbol"] for r in chosen], "table": rows}
    p = root() / "reports"
    p.mkdir(parents=True, exist_ok=True)
    (p / "universe_v1.json").write_text(json.dumps(out, indent=1))
    return out
