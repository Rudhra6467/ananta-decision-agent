"""The research lake (Madhav's plan, 2026-10-04): the full crypto universe, kept apart from the live system.

  raw/      files exactly as downloaded (Binance Data Vision monthly zips), each checked against Binance's own checksum; never edited
  clean/    one compressed Parquet dataset per source, market and timeframe, partitioned by symbol and year (DuckDB reads it in place,
            on this Mac or later in R2)
  reports/  the quality report per symbol (gaps, duplicates, broken candles) and the manifest of every file

The live system (Jarvis, the Explorer, the eye) never reads the lake while deciding; it gets small result files only.
Location: $ANANTA_LAKE (default ~/ananta_lake).
"""
from __future__ import annotations

import os
from pathlib import Path


def root() -> Path:
    return Path(os.path.expanduser(os.getenv("ANANTA_LAKE", "~/ananta_lake")))
