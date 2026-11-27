"""The live path's switches (design part 5).

LIVE_ORDERS  the master switch for every call that could place, change or cancel an order or a GTT. A constant in code, False, so no job
             and no setting can flip it; it changes only by a commit on the live day (design part 7, step 6), after Madhav's written yes.
ENFORCE      the survival rules act on live money (close everything at a 5% day, block entries at 22% under the high-water mark). False:
             record mode only. Turned on for live money only, a week after options (design part 4).
The kill switch is one small file in the live folder. Read before every order call. When it is on, no new order of any kind is sent.
  - A missing file, an unreadable file, or anything but a clean "off" written by Madhav counts as ON.
  - The module turns it on by itself: a reconciliation difference, an unreadable survival check, or two failed order calls in a row.
  - Only Madhav turns it off (turn_off(by="Madhav")).
The live folder is its own place (INDIA_LIVE_DIR, default ~/ananta_live/india), never inside the India data folder, so the paper records,
the read model and the sealed data never see it. Nothing here is created until something writes, and nothing running imports this file.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

LIVE_ORDERS = False
ENFORCE = False
FAILS_TO_KILL = 2
OFF_BY = "Madhav"


class OrdersOff(PermissionError):
    """An order call was refused at the gate: the master switch is off, or the kill switch is on."""


def live_dir() -> Path:
    p = Path(os.path.expanduser(os.getenv("INDIA_LIVE_DIR", "~/ananta_live/india"))).resolve()
    data = Path(os.path.expanduser(os.getenv("INDIA_DATA_DIR", "~/ananta_data/india"))).resolve()
    if p == data or data in p.parents:
        raise RuntimeError(f"refused: the live folder {p} is inside the India data folder")
    return p


def _kill_file() -> Path:
    return live_dir() / "kill_switch.json"


def kill_state() -> dict:
    """The kill switch as written, or {'state': 'on', 'why': ...} when it cannot be read."""
    try:
        d = json.loads(_kill_file().read_text())
    except FileNotFoundError:
        return {"state": "on", "why": "never turned off (no kill switch file): on by default"}
    except Exception as e:  # noqa: BLE001  unreadable counts as on
        return {"state": "on", "why": f"the kill switch could not be read ({type(e).__name__}): counted as on"}
    if not isinstance(d, dict) or d.get("state") not in ("on", "off"):
        return {"state": "on", "why": "the kill switch file holds no clean state: counted as on"}
    if d["state"] == "off" and d.get("by") != OFF_BY:
        return {"state": "on", "why": f"turned off by {d.get('by')!r}, not by {OFF_BY}: counted as on"}
    return d


def kill_on() -> bool:
    return kill_state().get("state") != "off"


def _write(d: dict) -> dict:
    f = _kill_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, sort_keys=True))
    tmp.replace(f)
    return d


def turn_on(why: str, by: str = "ananta") -> dict:
    """Anyone may turn it on: Madhav (app, voice), or the module itself. Telling the phone is the caller's alert path (built on the live day)."""
    return _write({"state": "on", "by": by, "why": why, "t": time.time(), "fails": 0})


def turn_off(by: str, why: str = "") -> dict:
    """Only Madhav turns the kill switch off."""
    if by != OFF_BY:
        raise PermissionError(f"only {OFF_BY} turns the kill switch off (asked by {by!r})")
    return _write({"state": "off", "by": by, "why": why or "turned off by Madhav", "t": time.time(), "fails": 0})


def note_failure(why: str) -> dict:
    """An order call failed. Two in a row turn the kill switch on."""
    d = kill_state()
    fails = int(d.get("fails") or 0) + 1
    if fails >= FAILS_TO_KILL:
        return turn_on(f"{fails} order calls failed in a row; last: {why}")
    if d.get("state") == "off":
        return _write({**d, "fails": fails, "last_fail": why})
    return d


def note_success() -> None:
    d = kill_state()
    if d.get("state") == "off" and int(d.get("fails") or 0):
        _write({**d, "fails": 0})


def may_send() -> tuple[bool, str]:
    """The one question every order call asks first. LIVE_ORDERS is read at call time."""
    if not LIVE_ORDERS:
        return False, "LIVE_ORDERS is off (in code)"
    if kill_on():
        return False, f"the kill switch is on: {kill_state().get('why')}"
    return True, "ok"


def require_send() -> None:
    ok, why = may_send()
    if not ok:
        raise OrdersOff(why)
