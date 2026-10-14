"""The outside watchdog: Jarvis cannot report its own death, so launchd runs this every 5 minutes (com.ananta.watchdog).

It asks Jarvis's /health on the Mac. Two failed looks in a row -> a phone note "Jarvis is not answering"; Jarvis answering but
its inside health checks (jarvis/service/health.py) silent for 10 minutes -> "health checks stopped"; a note again when it is
back. Standard library only (it must work when everything else is broken); the phone topic comes from the .env the launchd
wrapper loads. Read-only: it never restarts anything.

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
    return "ok", "answers"


def main(argv: list[str], get=None, now: float | None = None, send=push) -> dict:
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
        st = {"fails": 0}
    else:
        fails += 1
        st["fails"] = fails
        title = "Ananta: Jarvis is not answering" if res == "down" else "Ananta: Jarvis's health checks stopped"
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


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1:])))
