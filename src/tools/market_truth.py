"""
Independent Market Truth (Stage 1).

Pulls public exchange data (Kraken) so Ananta cannot grade itself.
Ananta regime is NOT used here. System Truth is captured elsewhere.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker"
KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"

# Kraken pair ids → canonical symbols
PAIRS = {
    "XXBTZUSD": "BTC/USD",
    "XETHZUSD": "ETH/USD",
    "SOLUSD": "SOL/USD",
    "XRPUSD": "XRP/USD",
    "LINKUSD": "LINK/USD",
    "ADAUSD": "ADA/USD",
    "AAVEUSD": "AAVE/USD",
    "ARBUSD": "ARB/USD",
    "AVAXUSD": "AVAX/USD",
}

BOOK_PAIRS = list(PAIRS.keys())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _kraken_get(url: str, params: dict, timeout: int = 12) -> Optional[dict]:
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code != 200:
            return None
        body = r.json()
        if body.get("error"):
            return None
        return body.get("result") or {}
    except Exception:
        return None


def _ohlc_metrics(pair: str) -> Dict[str, Any]:
    """1h OHLC metrics: returns, vol proxy, trend/compression flags."""
    result = _kraken_get(KRAKEN_OHLC, {"pair": pair, "interval": 60})
    if not result:
        return {}
    rows = None
    for k, v in result.items():
        if k == "last":
            continue
        if isinstance(v, list) and v:
            rows = v
            break
    if not rows or len(rows) < 5:
        return {}

    closes = [float(x[4]) for x in rows]
    highs = [float(x[2]) for x in rows]
    lows = [float(x[3]) for x in rows]
    last = closes[-1]

    def ret(n: int):
        if len(closes) <= n or closes[-1 - n] == 0:
            return None
        return round((last / closes[-1 - n] - 1.0) * 100.0, 4)

    rets = []
    window = closes[-25:] if len(closes) >= 25 else closes
    for i in range(1, len(window)):
        if window[i - 1]:
            rets.append((window[i] / window[i - 1]) - 1.0)
    vol = None
    if len(rets) >= 5:
        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / len(rets)
        vol = round((var ** 0.5) * 100.0, 4)

    sma_n = 20 if len(closes) >= 20 else max(5, len(closes) // 2)
    sma = sum(closes[-sma_n:]) / sma_n
    trend = "UP" if last > sma * 1.002 else ("DOWN" if last < sma * 0.998 else "FLAT")

    def span(hs, ls):
        return (max(hs) - min(ls)) / last * 100.0 if last else 0.0

    recent = span(highs[-6:], lows[-6:]) if len(highs) >= 6 else None
    longer = span(highs[-30:], lows[-30:]) if len(highs) >= 30 else None
    compression = None
    if recent is not None and longer and longer > 0:
        ratio = recent / longer
        compression = "COMPRESSION" if ratio < 0.45 else ("EXPANSION" if ratio > 0.9 else "NORMAL")

    return {
        "ret_1h_pct": ret(1),
        "ret_4h_pct": ret(4),
        "ret_24h_pct": ret(24),
        "vol_proxy_1h_pct": vol,
        "trend_flag": trend,
        "compression_flag": compression,
        "sma_ref": round(sma, 4),
        "bars_used": len(closes),
    }


def capture_market_truth(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """Independent market snapshot. source=kraken_public (not Ananta regime)."""
    ts = _utc_now()
    ticker = _kraken_get(KRAKEN_TICKER, {"pair": ",".join(BOOK_PAIRS)})
    assets: Dict[str, Any] = {}
    errors: List[str] = []

    if not ticker:
        return {
            "source": "kraken_public",
            "ts": ts,
            "ok": False,
            "error": "ticker_fetch_failed",
            "assets": {},
            "breadth_1h_pct_positive": None,
            "notes": "Market Truth unavailable — do not invent prices",
        }

    for pair_id, canon in PAIRS.items():
        if symbols and canon not in symbols and canon.split("/")[0] not in (symbols or []):
            if canon not in ("BTC/USD", "ETH/USD"):
                continue
        row = ticker.get(pair_id)
        if row is None:
            for k, v in ticker.items():
                if canon.startswith("BTC") and "XBT" in k:
                    row = v
                    break
                if canon[:3] in k:
                    row = v
                    break
        if not row:
            errors.append(f"missing:{canon}")
            continue
        try:
            price = float(row["c"][0])
            ch_24 = None
            try:
                open_p = float(row["o"])
                if open_p:
                    ch_24 = round((price / open_p - 1.0) * 100.0, 4)
            except Exception:
                pass
            vol24 = None
            try:
                vol24 = float(row["v"][1])
            except Exception:
                pass
            metrics = _ohlc_metrics(pair_id)
            assets[canon] = {
                "price": price,
                "change_24h_pct_ticker": ch_24,
                "volume_24h": vol24,
                **metrics,
            }
        except Exception as e:
            errors.append(f"{canon}:{e}")

    pos = 0
    n = 0
    for a in assets.values():
        r = a.get("ret_1h_pct")
        if r is None:
            continue
        n += 1
        if r > 0:
            pos += 1
    breadth = round(100.0 * pos / n, 2) if n else None

    btc = assets.get("BTC/USD") or {}
    eth = assets.get("ETH/USD") or {}

    return {
        "source": "kraken_public",
        "ts": ts,
        "ok": bool(assets),
        "error": None if assets else "no_assets",
        "errors": errors or None,
        "btc": btc or None,
        "eth": eth or None,
        "assets": assets,
        "breadth_1h_pct_positive": breadth,
        "notes": "Independent of Ananta regime. Exchange observables only.",
    }
