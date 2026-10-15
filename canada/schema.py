"""The Canada lake's tables (development and validation years) and the sealed holdout file (2024+).

Index and sector membership are stored as spans (asset, start, end) so a stock counts only on the days
it was actually a member. Every row that came from a vendor carries the pull_id of its manifest.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

LAKE = """
CREATE TABLE IF NOT EXISTS manifests (pull_id TEXT PRIMARY KEY, source TEXT, package TEXT, ndu_version TEXT,
  pkg_version TEXT, pulled_utc TEXT, padding TEXT, adjustment TEXT, git_commit TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS manifest_files (pull_id TEXT, path TEXT, sha256 TEXT, rows INTEGER,
  PRIMARY KEY (pull_id, path));
CREATE TABLE IF NOT EXISTS securities (asset_id INTEGER PRIMARY KEY, symbol TEXT, name TEXT, subtype TEXT,
  first_quoted TEXT, last_quoted TEXT, delisted INTEGER, pull_id TEXT);
CREATE TABLE IF NOT EXISTS calendar (day TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS bars (asset_id INTEGER, day TEXT, open REAL, high REAL, low REAL, close REAL,
  volume REAL, turnover REAL, close_raw REAL, close_tr REAL, dividend REAL, capital_event INTEGER, pull_id TEXT,
  PRIMARY KEY (asset_id, day));
CREATE TABLE IF NOT EXISTS index_spans (index_name TEXT, asset_id INTEGER, start_day TEXT, end_day TEXT,
  pull_id TEXT, PRIMARY KEY (index_name, asset_id, start_day));
CREATE TABLE IF NOT EXISTS classification_snapshots (asset_id INTEGER, scheme TEXT, level INTEGER, label TEXT,
  taken_on TEXT, pull_id TEXT, PRIMARY KEY (asset_id, scheme, level, taken_on));
CREATE TABLE IF NOT EXISTS macro (series TEXT, day TEXT, value REAL, source TEXT, PRIMARY KEY (series, day));
CREATE TABLE IF NOT EXISTS cost_estimates (asset_id INTEGER, day TEXT, cs_spread REAL, one_way REAL,
  label TEXT DEFAULT 'ESTIMATE', PRIMARY KEY (asset_id, day));
CREATE TABLE IF NOT EXISTS validation_runs (run_id TEXT, check_id TEXT, t TEXT, passed INTEGER, detail TEXT,
  PRIMARY KEY (run_id, check_id));
"""

HOLDOUT = """
CREATE TABLE IF NOT EXISTS seal (note TEXT, sealed_utc TEXT);
CREATE TABLE IF NOT EXISTS bars (asset_id INTEGER, day TEXT, open REAL, high REAL, low REAL, close REAL,
  volume REAL, turnover REAL, close_raw REAL, close_tr REAL, dividend REAL, capital_event INTEGER, pull_id TEXT,
  PRIMARY KEY (asset_id, day));
CREATE TABLE IF NOT EXISTS index_spans (index_name TEXT, asset_id INTEGER, start_day TEXT, end_day TEXT,
  pull_id TEXT, PRIMARY KEY (index_name, asset_id, start_day));
"""


def create(path: Path, ddl: str) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.executescript(ddl)
    con.commit()
    return con


def create_lake(path: Path) -> sqlite3.Connection:
    return create(path, LAKE)


def create_holdout(path: Path, sealed_utc: str) -> sqlite3.Connection:
    con = create(path, HOLDOUT)
    if not con.execute("SELECT 1 FROM seal").fetchone():
        con.execute("INSERT INTO seal VALUES (?, ?)", ("2024+ holdout: no return, signal or performance number "
                                                      "may be computed from this file until the seal is broken "
                                                      "with Madhav's recorded approval", sealed_utc))
        con.commit()
    return con
