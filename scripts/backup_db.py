"""Nightly backup of Ananta's databases (plan Batch 1, G25): every .sqlite in the agent folder, copied with SQLite's own backup
(safe while the service writes), into ~/ananta_backups/<date>/; 14 days kept. Beside them go the few files that are not databases and
cannot be rebuilt (`extras`: the Explorer's live state and the paid-search log and counter; research audit, Oct 15). Every night the day's
copy also goes, zipped, to the R2 bucket under backups/ (keys from the .env, never printed); the last 7 nightly copies and every Sunday's
are kept there. Until 15 Nov 2026 it went on Sundays only, and with the worker Mac out of reach the second copy did not leave this Mac for
five nights (audit repair 6, G-69). Run by launchd (com.ananta.backup) at 03:40.

    python scripts/backup_db.py            one backup now, and its copy to R2
    python scripts/backup_db.py --no-r2    ... without the R2 copy
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


def extras() -> list[Path]:
    """Files that are not databases but cannot be rebuilt, the ones that exist today. The Explorer's live state holds trades that have
    finished but are not yet saved to its book (the Evidence page counts them); the paid-search log and counter start where the file starts.
    Nothing here holds a key or a login."""
    runs = Path.home() / "ananta_runs"
    return [p for p in (AGENT / "explorer_state.pkl", runs / "web_paid_log.jsonl", runs / "web_paid.json") if p.exists()]


def backup(day: str | None = None) -> Path:
    day = day or time.strftime("%Y-%m-%d")
    dst = OUT / day
    dst.mkdir(parents=True, exist_ok=True)
    for src in sorted(AGENT.glob("*.sqlite")):
        with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as a, sqlite3.connect(dst / src.name) as b:
            a.backup(b)
            b.execute("PRAGMA journal_mode=DELETE")         # a copy is one plain file, no -wal or -shm beside it
    for extra in extras():
        shutil.copy2(extra, dst / extra.name)
    for old in sorted(p for p in OUT.iterdir() if p.is_dir())[:-KEEP_DAYS]:
        shutil.rmtree(old, ignore_errors=True)
    return dst


def pack(folder: Path) -> Path:
    """The day's folder as one .tar.gz: every file in it (the databases and the extras)."""
    tgz = folder.with_suffix(".tar.gz")
    with tarfile.open(tgz, "w:gz") as t:
        for f in sorted(p for p in folder.iterdir() if p.is_file()):
            t.add(f, arcname=f"{folder.name}/{f.name}")
    return tgz


def to_r2(folder: Path) -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.lake import r2

    tgz = pack(folder)
    key = f"backups/{tgz.name}"
    r2.client().upload_file(str(tgz), r2.bucket(), key)
    tgz.unlink(missing_ok=True)
    return key


KEEP_NIGHTLY = 7


def sends_to_r2(argv: list[str]) -> bool:
    """Every night (15 Nov 2026, G-69); it was Sundays only."""
    return "--no-r2" not in argv


def prune_r2(cl, bucket: str, today: str, keep: int = KEEP_NIGHTLY) -> list[str]:
    """Nightly copies older than `keep` days go; a Sunday's copy stays, as every copy did before 15 Nov. Returns the keys removed."""
    import datetime as dt

    cut = dt.date.fromisoformat(today) - dt.timedelta(days=keep)
    gone = []
    for o in (cl.list_objects_v2(Bucket=bucket, Prefix="backups/").get("Contents") or []):
        name = o["Key"].rsplit("/", 1)[-1].split(".")[0]
        try:
            day = dt.date.fromisoformat(name)
        except ValueError:
            continue
        if day < cut and day.weekday() != 6:
            cl.delete_object(Bucket=bucket, Key=o["Key"])
            gone.append(o["Key"])
    return gone


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
    mb = sum(p.stat().st_size for p in d.iterdir() if p.is_file()) / 1e6
    sent, err, pruned = None, None, []
    if sends_to_r2(sys.argv):
        try:
            sent = to_r2(d)
            from src.lake import r2

            pruned = prune_r2(r2.client(), r2.bucket(), d.name)
        except Exception as exc:  # noqa: BLE001  said in the log; the run check reads the log
            err = f"{type(exc).__name__}: {str(exc)[:160]}"
    print({"folder": str(d), "files": files, "extras": [p.name for p in extras()], "mb": round(mb, 1), "r2": sent,
           **({"r2_error": err} if err else {}), **({"r2_pruned": len(pruned)} if pruned else {})})
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
