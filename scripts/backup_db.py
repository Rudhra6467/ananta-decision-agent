"""Nightly backup of Ananta's databases (plan Batch 1, G25): every .sqlite in the agent folder, copied with SQLite's own backup
(safe while the service writes), into ~/ananta_backups/<date>/; 14 days kept. On Sundays (or with --r2) the day's copy also goes,
zipped, to the R2 bucket under backups/ (keys from the .env, never printed). Run by launchd (com.ananta.backup) at 03:40.

    python scripts/backup_db.py            one backup now
    python scripts/backup_db.py --r2       ... and send it to R2
    python scripts/backup_db.py --check    restore test: open the newest copy of jarvis.sqlite and count its rows
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tarfile
import time
from pathlib import Path

AGENT = Path.home() / "code" / "ananta-decision-agent"
OUT = Path.home() / "ananta_backups"
KEEP_DAYS = 14


def backup(day: str | None = None) -> Path:
    day = day or time.strftime("%Y-%m-%d")
    dst = OUT / day
    dst.mkdir(parents=True, exist_ok=True)
    for src in sorted(AGENT.glob("*.sqlite")):
        with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as a, sqlite3.connect(dst / src.name) as b:
            a.backup(b)
            b.execute("PRAGMA journal_mode=DELETE")         # a copy is one plain file, no -wal or -shm beside it
    for old in sorted(p for p in OUT.iterdir() if p.is_dir())[:-KEEP_DAYS]:
        shutil.rmtree(old, ignore_errors=True)
    return dst


def to_r2(folder: Path) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.lake import r2

    tgz = folder.with_suffix(".tar.gz")
    with tarfile.open(tgz, "w:gz") as t:
        for f in sorted(folder.glob("*.sqlite")):
            t.add(f, arcname=f"{folder.name}/{f.name}")
    key = f"backups/{tgz.name}"
    r2.client().upload_file(str(tgz), r2.bucket(), key)
    tgz.unlink(missing_ok=True)
    return key


def check() -> dict:
    newest = sorted(p for p in OUT.iterdir() if p.is_dir())[-1]
    with sqlite3.connect(f"file:{newest / 'jarvis.sqlite'}?mode=ro", uri=True) as c:
        ok = c.execute("PRAGMA integrity_check").fetchone()[0]
        n = c.execute("SELECT COUNT(*) FROM evidence_trades").fetchone()[0]
    return {"folder": str(newest), "integrity": ok, "evidence_trades": n}


if __name__ == "__main__":
    if "--check" in sys.argv:
        print(check())
        sys.exit(0)
    d = backup()
    files = len(list(d.glob("*.sqlite")))
    mb = sum(p.stat().st_size for p in d.glob("*.sqlite")) / 1e6
    sent = to_r2(d) if ("--r2" in sys.argv or time.localtime().tm_wday == 6) else None
    print({"folder": str(d), "files": files, "mb": round(mb, 1), "r2": sent})
    # worker S1 (Oct 15): the worker's finished days come here, and a copy of the newest backups (without logins, sessions, push
    # tokens, people or conversations) goes to the worker; each step on its own, a failure is printed, never fatal
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if (Path.home() / ".ssh" / "ananta_worker").exists():
        from jarvis.service import worker

        for name, step in (("worker_pull", worker.pull), ("worker_copy", worker.push_backups)):
            try:
                print({name: step()})
            except Exception as exc:  # noqa: BLE001
                print({name + "_error": str(exc)[:200]})
