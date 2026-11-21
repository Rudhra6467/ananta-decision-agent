"""15 Nov 2026, audit repair 6 (open-list flag 122), G-69: the databases' second copy did not leave this Mac for five nights (the worker Mac
out of reach; the R2 copy on Sundays only), and nothing told anyone. Now the R2 copy goes every night, the last 7 nightly copies and every
Sunday's are kept, and the run check counts a night without it as a lost run."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _script():
    spec = importlib.util.spec_from_file_location("backup_db_script", ROOT / "scripts" / "backup_db.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeR2:
    def __init__(self, keys):
        self.keys = list(keys)

    def list_objects_v2(self, Bucket, Prefix):  # noqa: N803
        return {"Contents": [{"Key": k} for k in self.keys if k.startswith(Prefix)]}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.keys.remove(Key)


def test_the_copy_goes_every_night_unless_told_not_to():
    m = _script()
    assert m.sends_to_r2(["backup_db.py"]) and not m.sends_to_r2(["backup_db.py", "--no-r2"])


def test_old_nightly_copies_go_and_sundays_stay():
    m = _script()
    keys = [f"backups/2026-11-{d:02d}.tar.gz" for d in range(1, 16)] + ["backups/notes.txt"]
    cl = FakeR2(keys)
    gone = m.prune_r2(cl, "b", "2026-11-15")
    kept = sorted(cl.keys)
    assert "backups/2026-11-01.tar.gz" in kept and "backups/2026-11-08.tar.gz" in kept      # Sundays stay
    assert "backups/2026-11-07.tar.gz" not in kept and "backups/2026-11-02.tar.gz" in gone
    assert all(f"backups/2026-11-{d:02d}.tar.gz" in kept for d in range(8, 16))             # the last 7 nights and today
    assert "backups/notes.txt" in kept


def test_the_run_check_watches_the_copy_every_night():
    from jarvis.service import runcheck_parts

    job = next(x for x in runcheck_parts.JOBS if x["id"] == "backup_r2") if hasattr(runcheck_parts, "JOBS") else None
    if job is None:
        job = next(x for v in vars(runcheck_parts).values() if isinstance(v, list) for x in v
                   if isinstance(x, dict) and x.get("id") == "backup_r2")
    assert job["cadence"].get("daily") == "03:40" and "weekly" not in job["cadence"] and job["name"].startswith("Nightly")


def test_the_run_check_starts_the_copy_on_the_night_after_go_live():
    """Repair 6 went live on 20 Nov 2026 13:19 Toronto (d94cba9); the nights of 18-20 Nov ran the old Sundays-only copy, so they
    are not lost runs (morning review 21 Nov 2026: the checker listed them as a medium miss)."""
    from jarvis.service import runcheck_parts

    job = next(x for v in vars(runcheck_parts).values() if isinstance(v, list) for x in v
               if isinstance(x, dict) and x.get("id") == "backup_r2")
    assert job["since"] == "2026-11-21"
