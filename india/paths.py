"""Where India's data lives: outside every crypto folder and outside Canada's, the holdout sealed from 2024-01-01.

Layout (plan of 16 Oct 2026, section 4):
  ~/ananta_data/india/
    bronze/<dataset>/YYYY/...     files exactly as downloaded (zip or csv), never edited
    silver/<dataset>/...          typed point-in-time Parquet
    gold/...                      universes, features, relationships
    manifests/                    one jsonl per dataset: what was fetched, when, status, sha256
    sealed/                       holdout rows (2024-01-01 onward); only the sealed loader reads here
    india.duckdb                  the catalog: security master, calendar, datasets, heartbeats
The folder moves to the external SSD when it arrives; INDIA_DATA_DIR overrides the location.
"""
from __future__ import annotations

import os
from pathlib import Path

DEV = ("2000-01-01", "2017-12-31")
VAL = ("2018-01-01", "2023-12-31")
HOLDOUT_START = "2024-01-01"
OTHER_DIRS = ("~/code/ananta-decision-agent", "~/code/ananta-agent-research", "~/code/Ananta", "~/ananta_lake", "~/ananta_data/canada")

DATASETS = {
    "cm_bhavcopy": "NSE cash-market daily bhavcopy, every listed stock (old cm*bhav and UDiFF files)",
    "fo_bhavcopy": "NSE derivatives daily bhavcopy, every future and option with OI and settlement",
    "delivery": "NSE security-wise delivery positions (sec_bhavdata_full / MTO)",
    "indices": "NSE and NiftyIndices daily index levels and constituent lists",
    "vix": "India VIX daily",
    "flows": "FII and DII daily provisional flows",
    "corporate_actions": "NSE corporate-action files (the cross-check record)",
    "kite_instruments": "Kite instruments master, one copy per day",
    "kite_5m": "Kite Connect 5-minute candles",
    "kite_day": "Kite Connect daily candles (the second record for spot checks)",
    "pr_zip": "NSE daily PR zips: corporate-action text, announcements, board meetings, market cap",
    "results_index": "NSE financial-results filings index by date window (filing timestamps, XBRL links)",
    "xbrl": "XBRL result files for universe names",
    "kite_index": "Kite candles for indices and India VIX, minute, 5-minute and daily",
    "kite_1m_fo": "Kite 1-minute candles for live NIFTY/BANKNIFTY contracts, recorded daily",
    "ledger": "Madhav's Zerodha holdings, positions, orders, funds: daily snapshots, read-only",
}


def data_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("INDIA_DATA_DIR", "~/ananta_data/india"))).resolve()


def bronze(dataset: str) -> Path:
    return data_dir() / "bronze" / dataset


def silver(dataset: str) -> Path:
    return data_dir() / "silver" / dataset


def gold() -> Path:
    return data_dir() / "gold"


def sealed_dir() -> Path:
    return data_dir() / "sealed"


def manifest_dir() -> Path:
    return data_dir() / "manifests"


def catalog_path() -> Path:
    return data_dir() / "india.duckdb"


def private_dir() -> Path:
    return Path(os.path.expanduser("~/ananta_private"))


def check_isolated(p: Path | None = None) -> Path:
    """Refuse an India data folder inside any crypto or Canada folder."""
    p = (p or data_dir()).resolve()
    for c in OTHER_DIRS:
        root = Path(os.path.expanduser(c)).resolve()
        if p == root or root in p.parents:
            raise RuntimeError(f"India data folder {p} is inside another market's folder ({root}); refused")
    return p


def ensure() -> Path:
    root = check_isolated()
    for d in (manifest_dir(), sealed_dir(), gold()):
        d.mkdir(parents=True, exist_ok=True)
    for ds in DATASETS:
        bronze(ds).mkdir(parents=True, exist_ok=True)
    return root
