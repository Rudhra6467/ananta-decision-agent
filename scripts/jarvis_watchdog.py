"""The outside watchdog: Jarvis cannot report its own death, so launchd runs this every 5 minutes (com.ananta.watchdog).

It asks Jarvis's /health on the Mac. Two failed looks in a row -> a phone note "Jarvis is not answering"; Jarvis answering but
its inside health checks (jarvis/service/health.py) silent for 10 minutes -> "health checks stopped"; a note again when it is
back. Standard library only (it must work when everything else is broken); the phone topic comes from the .env the launchd
wrapper loads. Since Oct 28 (flag 48) it heals one thing: Jarvis not answering, or its 15-minute jobs stuck, for 3 looks in a
row gets a stack snapshot (ananta_runs/stalls) and a launchd restart, at most once an hour. Nothing else is ever touched.

    python3 scripts/jarvis_watchdog.py            one look (what launchd runs)
    python3 scripts/jarvis_watchdog.py --test     send a test note
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

URL = os.getenv("JARVIS_HEALTH_URL", "http://127.0.0.1:8100/health")
STATE = Path(os.path.expanduser(os.getenv("WATCHDOG_STATE", "~/ananta_runs/watchdog_state.json")))
REMIND_S = 3 * 3600


def push(title: str, body: str, priority: str = "4") -> str:
    topic = os.getenv("ANANTA_NTFY_TOPIC", "").strip()
    if not topic:
        return "off"
    server = os.getenv("ANANTA_NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    req = urllib.request.Request(f"{server}/{topic}", data=body[:500].encode(), method="POST",
                                 headers={"Title": title.encode("ascii", "replace").decode()[:100], "Priority": priority, "Tags": "warn"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:  # noqa: S310 (fixed https server)
            return str(r.status)
    except Exception as exc:  # noqa: BLE001
        return f"failed: {exc}"


def look(get=None) -> tuple[str, str]:
    """('ok' | 'down' | 'blind', detail)"""
    try:
        if get:
            h = get(URL)
        else:
            with urllib.request.urlopen(URL, timeout=8) as r:  # noqa: S310 (localhost)
                h = json.loads(r.read().decode())
    except Exception as exc:  # noqa: BLE001
        return "down", f"no answer ({type(exc).__name__})"
    a = h.get("health_checks_s_ago")
    if a is not None and a > 600:
        return "blind", f"Jarvis answers, but its health checks have not run for {a / 60:.0f} minutes"
    b = h.get("jobs_s_ago")                               # Oct 28 (flag 48): the 15-minute loop can stall while the service answers
    if b is not None and b > STUCK_LOOP_S:
        return "stuck", f"Jarvis answers, but its 15-minute jobs have not started for {b / 60:.0f} minutes"
    return "ok", "answers"


STUCK_LOOP_S = 45 * 60
HEAL_AFTER = 3                                            # looks in a row (about 15 minutes) before a restart
HEAL_GAP_S = 3600                                         # at most one restart an hour
STALLS = Path(os.path.expanduser("~/ananta_runs/stalls"))


def heal(now: float, run=None) -> str:
    """Oct 28 (flag 48, 27 Oct 11:40-13:37 stall): capture what the stuck process was doing, then restart it through launchd.
    Service only: it never touches trading, rules or data."""
    import subprocess

    run = run or subprocess.run
    STALLS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime(now))
    try:
        pids = run(["pgrep", "-f", "uvicorn jarvis.service.app:app"], capture_output=True, text=True, timeout=10).stdout.split()
        for pid in pids[:1]:
            run(["/usr/bin/sample", pid, "5", "-file", str(STALLS / f"jarvis_{stamp}.txt")], capture_output=True, timeout=30)
    except Exception:  # noqa: BLE001  the snapshot is a bonus; the restart matters
        pass
    try:
        r = run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.ananta.jarvis"], capture_output=True, text=True, timeout=30)
        return "restarted" if r.returncode == 0 else f"restart failed ({r.returncode})"
    except Exception as exc:  # noqa: BLE001
        return f"restart failed ({type(exc).__name__})"


def main(argv: list[str], get=None, now: float | None = None, send=push, heal_run=None) -> dict:
    if "--test" in argv:
        return {"sent": send("Ananta watchdog: test", "The outside watchdog can reach your phone.", "3")}
    now = now or time.time()
    try:
        st = json.loads(STATE.read_text())
    except (OSError, ValueError):
        st = {}
    res, detail = look(get)
    fails = st.get("fails", 0)
    out = {"result": res, "detail": detail, "sent": None}
    if res == "ok":
        if st.get("down_t"):
            out["sent"] = send("Back: Jarvis", f"Answering again after about {(now - st['down_t']) / 60:.0f} minutes.", "3")
        st = {"fails": 0, **({"heal_t": st["heal_t"]} if st.get("heal_t") else {})}
    else:
        fails += 1
        st["fails"] = fails
        if res in ("down", "stuck") and fails >= HEAL_AFTER and (not st.get("heal_t") or now - st["heal_t"] >= HEAL_GAP_S) and (get is None or heal_run):
            st["heal_t"] = now
            out["healed"] = heal(now, run=heal_run)
            out["sent"] = send("Ananta restarted Jarvis", f"{detail} for about {fails * 5} minutes, so the watchdog restarted it "
                               f"({out['healed']}). A snapshot of what it was stuck on is in ananta_runs/stalls.", "3")
        title = {"down": "Ananta: Jarvis is not answering", "stuck": "Ananta: Jarvis's 15-minute jobs are stuck"}.get(
            res, "Ananta: Jarvis's health checks stopped")
        body = (f"{detail}. The phone app, the eye, alerts and the health checks are off until it is back. Restart Jarvis "
                "(python3 ~/ananta_runs/restart_jarvis.py).")
        if fails >= 2 and not st.get("down_t"):
            st["down_t"] = st["last_push"] = now
            out["sent"] = send(title, body)
        elif st.get("down_t") and now - st.get("last_push", 0) >= REMIND_S:
            st["last_push"] = now
            out["sent"] = send("Still down: Jarvis", f"Down for {(now - st['down_t']) / 3600:.1f} hours. " + body)
    if get is None:                                       # Oct 11 (G23): the website and the public address are watched too
        st["sites"] = sites(st.get("sites") or {}, now, send, out)
    else:
        st.pop("sites", None)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st))
    return out


SITES = (("the website on the Mac", os.getenv("WATCH_SITE_LOCAL", "http://127.0.0.1:8300/")),
         ("livetrading247.com", os.getenv("WATCH_SITE_PUBLIC", "https://livetrading247.com/")),
         ("the app's address (api.livetrading247.com)", os.getenv("WATCH_API_PUBLIC", "https://api.livetrading247.com/v3/public/status")))


def site_up(url: str, opener=None) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Ananta watchdog)"})   # Cloudflare refuses Python's default
        with (opener or urllib.request.urlopen)(req, timeout=12) as r:  # noqa: S310
            return 200 <= r.status < 400
    except Exception:  # noqa: BLE001
        return False


def sites(st: dict, now: float, send, out: dict, opener=None) -> dict:
    """Two failed looks in a row at a site = a phone note; a note again when it is back (the Oct 10 outages sent none)."""
    for name, url in SITES:
        s = st.get(name) or {}
        if site_up(url, opener):
            if s.get("down_t"):
                out.setdefault("sites_sent", []).append(send(f"Back: {name}", f"Answering again after about {(now - s['down_t']) / 60:.0f} minutes.", "3"))
            st[name] = {}
            continue
        s["fails"] = s.get("fails", 0) + 1
        if s["fails"] >= 2 and not s.get("down_t"):
            s["down_t"] = s["last_push"] = now
            out.setdefault("sites_sent", []).append(send(f"Ananta: {name} is down", f"{url} did not answer twice in a row. If the Mac is "
                                                         "asleep or offline, wake it; launchd restarts the website and the service by itself."))
        elif s.get("down_t") and now - s.get("last_push", 0) >= REMIND_S:
            s["last_push"] = now
            out.setdefault("sites_sent", []).append(send(f"Still down: {name}", f"Down for {(now - s['down_t']) / 3600:.1f} hours."))
        st[name] = s
    return st


def line(out: dict, now: float | None = None) -> str:
    """One watchdog.log line: its UTC time first (Oct 21), so the run checker can date every look (jarvis/service/runcheck_parts.py)."""
    return f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() if now is None else now))} UTC] {json.dumps(out)}"


if __name__ == "__main__":
    print(line(main(sys.argv[1:])))
