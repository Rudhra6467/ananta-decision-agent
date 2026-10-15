"""Where Canada's data lives: outside every crypto folder, the holdout in its own sealed file."""
from __future__ import annotations

import os
from pathlib import Path

DEV = ("2000-01-01", "2017-12-31")
VAL = ("2018-01-01", "2023-12-31")
HOLDOUT_START = "2024-01-01"
CRYPTO_DIRS = ("~/code/ananta-decision-agent", "~/code/ananta-agent-research", "~/code/Ananta")


def data_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("CANADA_DATA_DIR", "~/ananta_data/canada"))).resolve()


def lake_path() -> Path:
    return data_dir() / "canada_lake.sqlite"


def holdout_path() -> Path:
    return data_dir() / "sealed" / "canada_holdout.sqlite"


def raw_dir() -> Path:
    return data_dir() / "raw"


def manifest_dir() -> Path:
    return data_dir() / "manifests"


def check_isolated(p: Path | None = None) -> Path:
    """Refuse a Canada data folder inside any crypto folder."""
    p = (p or data_dir()).resolve()
    for c in CRYPTO_DIRS:
        root = Path(os.path.expanduser(c)).resolve()
        if p == root or root in p.parents:
            raise RuntimeError(f"Canada data folder {p} is inside a crypto folder ({root}); refused")
    return p
