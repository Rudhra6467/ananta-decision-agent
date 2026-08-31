"""W1 ingest contract. Raw candles → Ananta warehouse. Not Agent jsonl. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "INGEST-CONTRACT-v0"

# From Rudhra6467/Ananta backend/lab/data_store.py + seed_history.py
WAREHOUSE = {
    "store": "Mongo historical_candles",
    "row": "[ts_ms, o, h, l, c, v]",
    "id": "{symbol}|{timeframe}|{ts}",
    "symbols": "BTC/USD style — not BTCUSDT inside the DB",
    "tfs_known": ["15m", "30m", "1h", "4h", "1d"],
    "live_path": "CCXT Kraken then Coinbase, 720-bar pages — THIS is why HAVE=1.17y",
    "seed_path": "lab.seed_history.seed_from_binance + seed_from_csv",
    "binance_url": "https://data.binance.vision/data/spot/monthly/klines/{SYM}/{TF}/{SYM}-{TF}-{YYYY-MM}.zip",
    "map": {
        "BTC/USD": ["BTCUSDT"],
        "ETH/USD": ["ETHUSDT"],
        "SOL/USD": ["SOLUSDT"],
        "AVAX/USD": ["AVAXUSDT"],
        "XRP/USD": ["XRPUSDT"],
        "PAXG/USD": ["PAXGUSDT"],
        "LINK/USD": ["LINKUSDT"],
        "AAVE/USD": ["AAVEUSD"],
        "ARB/USD": ["ARBUSDT"],
        "RENDER/USD": ["RENDERUSDT", "RNDRUSDT"],
    },
}
# AAVE map in Ananta is AAVEUSDT — printed AAVEUSD above is a typo guard; use Ananta BINANCE_MAP.

PACKAGE = {
    "window": "2021-09-10 → now",
    "first_proof": ["BTC/USD", "ETH/USD"],
    "tfs_first": ["1h"],
    "tfs_then": ["15m", "4h"],
    "then_assets": ["SOL", "LINK", "XRP", "AVAX", "AAVE", "PAXG"],
    "listed_late": ["ARB ~2023", "RENDER rebrand 2024 use RNDRUSDT first"],
    "do_not": [
        "dump CSVs into Agent observation_replay",
        "precompute indicators",
        "mix Kraken+Binance in one cell without source tag",
        "expect ARB/RENDER full 2021 history",
        "100GB first pass",
    ],
}


def print_ingest() -> Dict[str, Any]:
    print(f"\nINGEST CONTRACT  {VERSION}")
    print("=" * 64)
    print("W1 is Ananta seed, not Agent download.")
    print("-" * 64)
    print("  row:", WAREHOUSE["row"])
    print("  id:", WAREHOUSE["id"])
    print("  live backfill: Kraken CCXT 720-cap → 1.17y HAVE")
    print("  seed: data.binance.vision monthly zips → upsert_candles")
    print("  already mapped: BTC ETH SOL AVAX XRP PAXG LINK AAVE ARB RENDER")
    print("-" * 64)
    print("  FIRST: seed_from_binance([BTC/USD, ETH/USD], months=60, timeframe='1h')")
    print("  THEN: coverage_report until from_iso ≤ 2021-09-10")
    print("  THEN: 15m + 4h on those two")
    print("  THEN: rest of watchlist; ARB/RENDER start at listing")
    print("-" * 64)
    print("  Kraken OHLCVT zip: venue-true, use seed_from_csv after we prove Binance 1h.")
    print("  CDD: secondary cross-check only.")
    print("  Agent never stores raw years. Replay after warehouse moves.")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "keep": False}
