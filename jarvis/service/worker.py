"""The worker Mac, stage S1 (Oct 15; plan: Project note plan-2026-10-11-worker-mac.md). A read-only second machine on the home
network that records, once a minute, what cannot be fetched again later (NDAX's and Binance's bid and ask, USD/CAD, whether
Ananta's public page answers). The main Mac pulls from it; it never connects to the main Mac and holds one secret only: the phone
note topic (alert.json, mode 600, Oct 15), which can do nothing but send notes to Madhav's phone when the public page is down.

  status()              its one-line status over SSH, cached 5 minutes: {"ok", "state", "line", "checked_t"} (a part of system health)
  pull()                every finished UTC day the main Mac does not hold yet copied into ~/ananta_worker_data, checked, never twice:
                        the collector's l1_YYYY-MM-DD.sqlite and, since Oct 20, other traders' fills hl_YYYY-MM-DD.sqlite (data only,
                        decision OD-HL-FILLS (a); worker/hl_capture.py writes a day only when it is whole)
  push_backups(n=3)     the newest n nightly backups to the worker, WITHOUT the tables that hold logins, sessions, push tokens,
                        people or conversations and without the guests' practice books (the worker is an old, unpatched Mac: no
                        secrets on it), only while it has more than 20 GB free; the copy is integrity-checked there
  outside_view(days)    the worker's site checks: minutes the public page did not answer, as outage windows (the outside view),
                        and the alerts it recorded (armed each day, test, down, still_down, back)
  alert_armed_now()     whether its status line says the outside alert is on (cached status only)
Run by scripts/backup_db.py at 03:40 (pull and push) and by health.py (status).
"""
from __future__ import annotations

import json
import shlex
import sqlite3
import subprocess
import time
from pathlib import Path

HOST = "ananta-worker"
DEST = Path.home() / "ananta_worker_data"
REMOTE_DATA = "~/ananta_worker/data"
REMOTE_BACKUPS = "~/ananta_backup_copy"
MIN_FREE_GB = 20
SECRET_TABLES = ("users", "sessions", "owner_auth", "push_tokens", "web_push_subs", "failed_logins", "invites", "people_session",
                 "visitor_profile", "ask_messages", "ask_chips", "ask_misunderstood", "feedback", "account_activity")
_CACHE: dict = {}


def _ssh(cmd: str, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, cmd], capture_output=True, text=True, timeout=timeout)


def status(max_age_s: int = 300) -> dict:
    """The worker's own check: exit 0 = its last round is under 3 minutes old, 1 = stale, 2 = never; unreachable = no answer."""
    now = time.time()
    if _CACHE.get("status") and now - _CACHE["status"]["checked_t"] < max_age_s:
        return _CACHE["status"]
    try:
        r = _ssh("~/ananta_worker/status", timeout=20)
        state = {0: "OK", 1: "STALE", 2: "NEVER"}.get(r.returncode, "ERROR")
        lines = (r.stdout or r.stderr).strip().splitlines()      # the collector's line; since Oct 20 the fills capture's line too
        hl = next((ln for ln in lines if ln.startswith("hl ")), None)
        out = {"ok": r.returncode == 0, "state": state, "line": (lines[0] if lines else "")[:300], "checked_t": now}
        if hl:
            out["hl"] = hl[:300]
    except Exception as exc:  # noqa: BLE001
        out = {"ok": False, "state": "UNREACHABLE", "line": str(exc)[:200], "checked_t": now}
    _CACHE["status"] = out
    return out


_LAST_SSH_ERROR = ""


PREFIXES = ("l1_", "hl_")
CHECK_TABLES = {"l1_": ("ndax", "binance", "fx", "site"), "hl_": ("fills", "accounts")}


def _remote_files() -> dict[str, int]:
    global _LAST_SSH_ERROR
    try:                                    # find, not a shell glob: a pattern with no file is an error in zsh and would hide the others
        r = _ssh(f"cd {REMOTE_DATA} && find . -maxdepth 1 -type f \\( -name 'l1_*.sqlite' -o -name 'hl_*.sqlite' \\) -exec stat -f '%N %z' {{}} +",
                 timeout=30)
    except Exception as exc:  # noqa: BLE001  (a timeout is the usual one)
        _LAST_SSH_ERROR = f"ssh: {str(exc)[:160]}"
        return {}
    _LAST_SSH_ERROR = "" if r.returncode == 0 else f"ssh rc {r.returncode}: {(r.stderr or '').strip()[:160]}"
    out = {}
    for line in (r.stdout or "").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            name = parts[0][2:] if parts[0].startswith("./") else parts[0]
            if name[:3] in PREFIXES and name.endswith(".sqlite"):
                out[name] = int(parts[1])
    return out


def pull(dest: Path | None = None) -> dict:
    """Copy each finished UTC day (its file name's day before today, UTC) the main Mac does not hold yet; a file is kept only when
    it opens and its tables have rows. Never overwrites a day already pulled."""
    dest = dest or DEST
    dest.mkdir(parents=True, exist_ok=True)
    today = time.strftime("%Y-%m-%d", time.gmtime())
    got, skipped, bad = [], [], []
    for name, size in sorted(_remote_files().items()):
        day, kind = name[3:13], name[:3]
        if day >= today:
            continue
        if (dest / name).exists():
            skipped.append(day)
            continue
        part = dest / (name + ".part")
        r = subprocess.run(["scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", f"{HOST}:{REMOTE_DATA}/{name}", str(part)],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0 or not part.exists() or part.stat().st_size != size:
            bad.append({"day": day, "file": name, "why": (r.stderr or "size differs").strip()[:120]})
            part.unlink(missing_ok=True)
            continue
        try:
            con = sqlite3.connect(f"file:{part}?mode=ro", uri=True)
            n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in CHECK_TABLES.get(kind, CHECK_TABLES["l1_"])}
            if kind == "hl_" and not con.execute("SELECT 1 FROM meta WHERE k='finished_at'").fetchone():
                con.close()
                raise sqlite3.DatabaseError("not marked finished")
            con.close()
        except sqlite3.Error as exc:
            bad.append({"day": day, "file": name, "why": str(exc)[:120]})
            part.unlink(missing_ok=True)
            continue
        part.rename(dest / name)
        got.append({"day": day, **n} if kind == "l1_" else {"day": day, "file": "hl", **n})
    out = {"pulled": got, "already_here": len(skipped), "failed": bad, "dest": str(dest)}
    if _LAST_SSH_ERROR:                      # Oct 16: the first night's pull found nothing and said nothing; now it says why
        out["error"] = _LAST_SSH_ERROR
    return out


def _free_gb() -> float | None:
    try:
        r = _ssh("df -k ~ | tail -1", timeout=20)
        return int(r.stdout.split()[3]) / 1e6
    except Exception:  # noqa: BLE001
        return None


def push_backups(n: int = 3, src: Path | None = None) -> dict:
    src = src or Path.home() / "ananta_backups"
    free = _free_gb()
    if free is None or free < MIN_FREE_GB:
        return {"pushed": [], "note": (f"not pushed: the worker has {round(free, 1)} GB free (needs {MIN_FREE_GB})" if free is not None
                                        else "not pushed: the worker could not be reached to read its free space")}
    days = sorted(p for p in src.iterdir() if p.is_dir())[-n:]
    _ssh(f"mkdir -p {REMOTE_BACKUPS}")
    pushed = []
    for d in days:
        stage = Path.home() / "ananta_runs" / "worker_copy" / d.name
        stage.mkdir(parents=True, exist_ok=True)
        for f in sorted(d.glob("*.sqlite")):
            if f.name.startswith("jarvis_guest_"):          # guests' practice books stay off the worker (their file names are emails)
                continue
            out = stage / f.name
            out.unlink(missing_ok=True)
            with sqlite3.connect(f"file:{f}?mode=ro", uri=True) as a, sqlite3.connect(out) as b:
                a.backup(b)
            with sqlite3.connect(out) as b:
                for t in SECRET_TABLES:
                    b.execute(f"DROP TABLE IF EXISTS {t}")
                b.commit()
                b.execute("VACUUM")
        _ssh(f"rm -rf {REMOTE_BACKUPS}/{shlex.quote(d.name)}")          # each day's copy is replaced whole, never merged
        r = subprocess.run(["scp", "-q", "-r", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", str(stage), f"{HOST}:{REMOTE_BACKUPS}/"],
                           capture_output=True, text=True, timeout=1800)
        ok = r.returncode == 0
        chk = _ssh(f"sqlite3 {REMOTE_BACKUPS}/{d.name}/jarvis.sqlite 'PRAGMA integrity_check'", timeout=120).stdout.strip() if ok else ""
        pushed.append({"day": d.name, "ok": ok and chk == "ok", "check": chk[:40]})
        for f in stage.glob("*.sqlite"):
            f.unlink(missing_ok=True)
        stage.rmdir()
    keep = {d.name for d in days}
    _ssh(f"cd {REMOTE_BACKUPS} && for d in */; do d=${{d%/}}; case \" {' '.join(sorted(keep))} \" in *\" $d \"*) ;; *) rm -rf -- \"$d\";; esac; done")
    return {"pushed": pushed, "free_gb": round(free, 1), "kept_on_worker": sorted(keep)}


def outside_view(days: int = 7, dest: Path | None = None) -> dict:
    """From the pulled days: minutes the public page did not answer, grouped into outage windows (consecutive failed minutes)."""
    dest = dest or DEST
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    checks = fails = 0
    windows: list[list[int]] = []
    alerts: list[dict] = []
    for f in sorted(dest.glob("l1_*.sqlite")):
        if f.name[3:13] < since:
            continue
        con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        try:
            for t, ok in con.execute("SELECT t, ok FROM site ORDER BY t"):
                checks += 1
                if not ok:
                    fails += 1
                    if windows and t - windows[-1][1] <= 120:
                        windows[-1][1] = t
                    else:
                        windows.append([t, t])
            try:                               # collector v1.1 (Oct 15) records its alerts: armed (each day), test, down, still_down, back
                alerts += [{"t": t, "kind": k, "result": r} for t, k, r in con.execute("SELECT t, kind, result FROM alerts ORDER BY t")]
            except sqlite3.OperationalError:    # a day recorded by v1.0: no alert existed
                pass
        finally:
            con.close()
    return {"days": days, "checks": checks, "failed": fails, "alerts": alerts,
            "windows": [{"from": time.strftime("%Y-%m-%d %H:%M", time.gmtime(a)), "t0": a, "minutes": round((b - a) / 60) + 1}
                        for a, b in windows][-20:]}


def alert_armed_now() -> bool | None:
    """Whether the worker says its outside alert is on, from the cached status line (never a new SSH call): True, False, or None
    when the status has not been read."""
    s = _CACHE.get("status")
    if not s or s.get("state") in ("UNREACHABLE", "ERROR"):
        return None
    line = str(s.get("line") or "")
    return True if "outside alert on" in line else False if "outside alert off" in line else None


if __name__ == "__main__":
    print(json.dumps({"status": status(0), "pull": pull()}, indent=1))
