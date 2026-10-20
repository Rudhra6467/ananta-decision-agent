"""Lost or empty runs: every part that runs by itself, judged against its schedule for the last 24 hours and the last 7 days.

Oct 20 silent-failure audit: on Oct 14-15 the brain paid for 226 decisions and saved none, and nothing noticed for ten hours: the
health watchdog asks "is it alive?", the morning review greps the service log for tracebacks, and the error was caught and written
only into brain_queue.state. This checker asks a different question for each part in jarvis/service/runcheck_parts.py: for every
scheduled run, is there dated proof that it ran AND did a minimum amount of work? Three kinds of miss, plus two:

  no run    nothing dated inside the run's slot
  errored   the proof itself says the run failed (a FAILED queue item, errors=[...] in the Explorer log, a stderr written)
  empty     it ran but did less than its minimum (0 coins scanned, a 'facts only' stance, 900 of 1,440 minutes)
  lost      two counts that must agree do not (paid brain calls against saved decisions)
  down      an outage the health watchdog recorded

Read-only: every database is opened with mode=ro and query_only; files are only read. It changes nothing, sends nothing and costs
nothing. Parts with no dated proof are never skipped silently: they are listed under "cannot be checked" every time.

    python -m jarvis.service.runcheck            the review section (markdown)
    python -m jarvis.service.runcheck --json     the full result
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from jarvis.service.runcheck_parts import PARTS

DAY = 86400
WINDOWS = (("24h", DAY), ("7d", 7 * DAY))
SHOW_TZ = "America/Toronto"
MAX_LOG_BYTES = 64 * 1024 * 1024
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


def default_paths() -> dict:
    home = Path.home()
    return {"agent": os.getenv("ANANTA_AGENT_DIR", str(home / "code" / "ananta-decision-agent")),
            "runs": os.getenv("ANANTA_RUNS_DIR", str(home / "ananta_runs")),
            "repo": str(Path(__file__).resolve().parents[2]),
            "worker": str(home / "ananta_worker_data"), "backups": str(home / "ananta_backups")}


def _tz(name: str | None):
    return timezone.utc if not name or name == "UTC" else ZoneInfo(name)


def _ro(path: str) -> sqlite3.Connection:
    """A connection that cannot write: the file must exist (mode=ro never creates one) and query_only refuses every change."""
    if not Path(path).is_file():
        raise FileNotFoundError(f"no database at {path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    con.execute("PRAGMA query_only = ON")
    return con


# ---------------------------------------------------------------------------
# the schedule
# ---------------------------------------------------------------------------
def period(cad: dict) -> int:
    return int(cad["every"]) if "every" in cad else 7 * DAY if "weekly" in cad else DAY


def grace(cad: dict) -> int:
    return int(cad["grace"]) if "grace" in cad else int(cad["every"]) if "every" in cad else 3 * 3600


def instants(cad: dict, start: int, end: int) -> list[int]:
    """Every scheduled run time in [start, end] (epoch seconds)."""
    if "every" in cad:
        s, off = int(cad["every"]), int(cad.get("offset", 0))
        first = -(-(start - off) // s) * s + off
        return list(range(first, end + 1, s))
    tz = _tz(cad.get("tz"))
    hh, mm = (int(x) for x in str(cad.get("daily") or cad.get("at")).split(":"))
    d, last = datetime.fromtimestamp(start, tz).date() - timedelta(days=1), datetime.fromtimestamp(end, tz).date() + timedelta(days=1)
    out = []
    while d <= last:
        ok = d.weekday() == int(cad["weekly"]) if "weekly" in cad else ("days" not in cad or str(d.weekday()) in cad["days"])
        if ok:
            t = int(datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz).timestamp())
            if start <= t <= end:
                out.append(t)
        d += timedelta(days=1)
    return out


def _date_of(t: int, cad: dict, shift: int = 0) -> str:
    return (datetime.fromtimestamp(t, _tz(cad.get("tz"))).date() + timedelta(days=shift)).isoformat()


def _since_t(part: dict) -> int:
    s = part.get("since")
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) if s else 0


def _until_t(part: dict) -> int | None:
    u = part.get("until")
    return int(datetime.strptime(u, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) + DAY if u else None


# ---------------------------------------------------------------------------
# the proof, read-only
# ---------------------------------------------------------------------------
def _rows(con: sqlite3.Connection, query: str, params: dict) -> list[tuple]:
    out = []
    for r in con.execute(query, {k: v for k, v in params.items() if f":{k}" in query}):
        if not r or r[0] is None:
            continue
        out.append((int(r[0]), float(r[1]) if len(r) > 1 and r[1] is not None else 1.0,
                    (str(r[2]) if len(r) > 2 and r[2] not in (None, "") else None), (str(r[3]) if len(r) > 3 and r[3] else None)))
    return out


def _sql(path: str, query: str, params: dict) -> list[tuple]:
    con = _ro(path)
    try:
        return _rows(con, query, params)
    finally:
        con.close()


def _log(part: dict, paths: dict) -> list[tuple]:
    pr, cad = part["proof"], part["cadence"]
    p = Path(pr["log"].format(**paths))
    if not p.is_file():
        raise FileNotFoundError(f"no log at {p}")
    with open(p, "rb") as f:
        f.seek(max(0, p.stat().st_size - MAX_LOG_BYTES))
        text = f.read().decode(errors="ignore")
    rx, tz = re.compile(pr["regex"]), _tz(pr.get("tz"))
    hh, mm = (int(x) for x in str(cad.get("daily") or cad.get("at") or "00:00").split(":"))
    out = []
    for line in text.splitlines():
        m = rx.search(line)
        if not m:
            continue
        g = m.groupdict()
        try:
            if g.get("t"):
                t = int(datetime.strptime(g["t"], pr.get("time_format", "%Y-%m-%d %H:%M")).replace(tzinfo=tz).timestamp())
            else:                                        # a date only: the run scheduled on that date
                d = datetime.strptime(g["d"], "%Y-%m-%d")
                t = int(datetime(d.year, d.month, d.day, hh, mm, tzinfo=_tz(cad.get("tz"))).timestamp()) + 1
        except (KeyError, ValueError):
            continue
        work = float(g["work"]) if g.get("work") not in (None, "") else 1.0
        err = g.get("err")
        err = None if err is None or err.strip() == pr.get("ok_err", "") else err.strip()[:160]
        out.append((t, work, err, None))
    return out


def _files(part: dict, paths: dict, slots: list[int]) -> list[tuple]:
    """One event per scheduled run whose file exists: work 1 when it is big enough and says what it must, else 0."""
    pr, cad = part["proof"], part["cadence"]
    out = []
    for t in slots:
        p = Path(pr["files"].format(**paths, date=_date_of(t, cad, pr.get("date_shift", 0))))
        if not p.is_file():
            continue
        size = p.stat().st_size
        text = p.read_text(errors="ignore") if (pr.get("must_contain") or pr.get("err_regex")) and size < MAX_LOG_BYTES else ""
        ok = size >= pr.get("min_bytes", 1) and (not pr.get("must_contain") or pr["must_contain"] in text)
        m = re.search(pr["err_regex"], text) if pr.get("err_regex") else None
        out.append((t + 1, 1.0 if ok else 0.0, (m.group("err") if "err" in m.groupdict() else m.group(0))[:160] if m else None,
                    None if ok else f"{p.name}: {size} bytes" + (f", no '{pr['must_contain']}'" if pr.get("must_contain") else "")))
    return out


def _sqlite_files(part: dict, paths: dict, slots: list[int], params: dict) -> tuple[list[tuple], list[str]]:
    pr, cad = part["proof"], part["cadence"]
    out, bad = [], []
    for t in slots:
        p = Path(pr["sqlite_files"].format(**paths, date=_date_of(t, cad, pr.get("date_shift", 0))))
        if not p.is_file():
            continue
        try:
            out += _sql(str(p), pr["query"], params)
        except sqlite3.Error as exc:
            bad.append(f"{p.name}: {exc}")
    return out, bad


# ---------------------------------------------------------------------------
# judging one part
# ---------------------------------------------------------------------------
def _miss(part: dict, kind: str, t: int, to: int, found: float | None = None, detail: str = "") -> dict:
    cad = part.get("cadence") or {}
    return {"part": part["id"], "name": part["name"], "severity": part.get("severity", "medium"), "area": part.get("area", "crypto"),
            "kind": kind, "t": int(t), "to": int(to), "runs": 1, "found": found, "needed": part.get("min_work"), "detail": detail,
            "utc_day": "daily" in cad and cad.get("tz", "UTC") == "UTC"}


def judge(part: dict, paths: dict, now: int, span: int) -> dict:
    """{expected, ok, misses, not_checked} for the scheduled runs of the last `span` seconds that are complete (past their grace)."""
    cad, pr = part["cadence"], part["proof"]
    res = {"part": part["id"], "name": part["name"], "area": part.get("area", "crypto"), "expected": 0, "ok": 0, "misses": [],
           "not_checked": None}
    if "none" in pr:
        res["not_checked"] = pr["none"]
        return res
    start = max(now - span, _since_t(part))
    until = _until_t(part)
    end = min(now - grace(cad), until) if until else now - grace(cad)
    per = period(cad)
    t0 = start - per - DAY
    params = {"t0": t0, "now": now}

    if "outages" in pr:                                  # outages are judged by their own times, not by slots
        try:
            con = _ro(pr["outages"].format(**paths))
            try:
                rows = con.execute("SELECT part, down_t, up_t, detail FROM health_log WHERE COALESCE(up_t, ?) >= ? AND down_t <= ?",
                                   (now, now - span, now)).fetchall()
            finally:
                con.close()
        except (OSError, sqlite3.Error) as exc:
            res["misses"].append(_miss(part, "no proof", now - span, now, detail=f"the proof could not be read: {exc}"[:200]))
            return res
        for name, down, up, detail in rows:
            mins = round(((up or now) - down) / 60)
            m = _miss(part, "down", down, up or now, detail=f"{name}: {mins} min" + ("" if up else ", still down")
                      + (f" ({detail[:100]})" if detail else ""))
            m["sub"], m["minutes"], m["still"] = name, mins, not up
            res["misses"].append(m)
        res["expected"] = res["ok"] = None
        return res

    slots = instants(cad, start, end)
    if part.get("latest_only"):
        slots = slots[-1:]
    if not slots:
        res["not_checked"] = ("no run due yet in this window (the proof arrives later)" if grace(cad) >= span else
                              "not started yet in this window")
        return res
    allslots = instants(cad, slots[0], end + 2 * per)
    ends = {t: min(nxt, t + per) for t, nxt in zip(allslots, allslots[1:] + [allslots[-1] + per])}

    try:
        if "reconcile" in pr:
            rc = pr["reconcile"]
            a, b = _sql(rc["db"].format(**paths), rc["a"], params), _sql(rc["db"].format(**paths), rc["b"], params)
            events = None
        elif "sql" in pr:
            if part.get("latest_only"):
                params["inst"] = slots[-1]
            events = _sql(pr["sql"].format(**paths), pr["query"], params)
        elif "log" in pr:
            events = _log(part, paths)
        elif "files" in pr:
            events = _files(part, paths, slots)
        elif "sqlite_files" in pr:
            events, bad = _sqlite_files(part, paths, slots, params)
            for b_ in bad:
                res["misses"].append(_miss(part, "no proof", slots[0], ends[slots[-1]], detail=f"unreadable: {b_}"[:200]))
        elif "mtime" in pr:
            events = []
            p = Path(pr["mtime"].format(**paths))
            if p.is_file():
                events.append((int(p.stat().st_mtime), 1.0, None, None))
            ef = Path(pr["err_file"].format(**paths)) if pr.get("err_file") else None
            if ef and ef.is_file() and ef.stat().st_size and int(ef.stat().st_mtime) >= slots[-1] - 120:
                events.append((int(ef.stat().st_mtime), 0.0, f"{ef.name} written during the run", None))
        else:
            raise ValueError(f"unknown proof kind: {sorted(pr)}")
    except (OSError, sqlite3.Error, ValueError, re.error) as exc:
        res["misses"].append(_miss(part, "no proof", slots[0], ends[slots[-1]], detail=f"the proof could not be read: {exc}"[:200]))
        res["expected"] = len(slots)
        return res

    need = part.get("min_work", 1)
    for s in slots:
        lo, hi = s - int(cad.get("early", 0)), ends[s]
        if part.get("latest_only"):
            hi = now + 1                                 # a single current value: anything since the scheduled run counts
        res["expected"] += 1
        if events is None:                               # reconcile
            na = [x for x in a if lo <= x[0] < hi]
            nb = sum(x[1] for x in b if lo <= x[0] < hi)
            ca = sum(x[1] for x in na)
            cost = sum(float(x[2]) for x in na if x[2] not in (None, "")) if na else 0.0
            if ca - nb > part.get("tolerance", 0):
                res["misses"].append(_miss(part, "lost", s, hi, found=nb,
                                           detail=f"{ca:.0f} {part.get('what', 'expected')}, {nb:.0f} {part.get('against', 'found')}: "
                                                  f"{ca - nb:.0f} lost" + (f" (that day's calls cost ${cost:.2f})" if cost else "")))
            else:
                res["ok"] += 1
            continue
        mine = [e for e in events if lo <= e[0] < hi]
        errs = [e for e in mine if e[2]]
        work = sum(e[1] for e in mine if not e[2])
        if part.get("errors_only"):
            if errs:
                res["misses"].append(_miss(part, "errored", s, hi, found=len(errs), detail=f"{len(errs)}x {errs[0][2][:120]}"))
            else:
                res["ok"] += 1
        elif errs:
            res["misses"].append(_miss(part, "errored", s, hi, found=work, detail=f"{len(errs)}x {errs[0][2][:120]}"))
        elif not mine:
            res["misses"].append(_miss(part, part.get("zero_means", "no run"), s, hi, found=0))
        elif work < need:
            det = next((e[3] for e in mine if e[3]), "")
            res["misses"].append(_miss(part, "empty", s, hi, found=work, detail=(det or "")[:160]))
        else:
            res["ok"] += 1
    return res


def merge(misses: list[dict]) -> list[dict]:
    """Back-to-back misses of one part and kind become one line with a run count; three or more outages of one watched part
    become one line with their total and the longest (the worker's SSH link drops often and would bury everything else)."""
    out: list[dict] = []
    by_sub: dict = {}
    for m in misses:
        if m["kind"] == "down":
            by_sub.setdefault((m["part"], m.get("sub")), []).append(m)
    for (_, sub), ms in by_sub.items():
        if len(ms) < 3:
            out += [dict(x) for x in ms]
            continue
        ms = sorted(ms, key=lambda x: x["t"])
        big = max(ms, key=lambda x: x.get("minutes", 0))
        g = dict(ms[0])
        g.update(to=ms[-1]["to"], runs=len(ms),
                 detail=f"{sub}: {len(ms)} outages, {sum(x.get('minutes', 0) for x in ms):,} min in all; the longest {big.get('minutes', 0):,} min "
                        f"from {_when(big['t'])}" + (", still down" if any(x.get("still") for x in ms) else ""))
        out.append(g)
    for m in sorted((x for x in misses if x["kind"] != "down"), key=lambda x: (x["part"], x["kind"], x["t"])):
        p = out[-1] if out else None
        if p and p["part"] == m["part"] and p["kind"] == m["kind"] and m["t"] <= p["to"] and m["kind"] not in ("lost", "down"):
            p["to"], p["runs"] = max(p["to"], m["to"]), p["runs"] + 1
            if m.get("found") is not None:
                p["found_max"] = max(p.get("found_max", p.get("found") or 0), m["found"])
                p["found"] = min(p.get("found") if p.get("found") is not None else m["found"], m["found"])
            if m["detail"] and m["detail"] not in p["detail"] and len(p["detail"]) < 200:
                p["detail"] = (p["detail"] + "; " if p["detail"] else "") + m["detail"]
        else:
            out.append(dict(m))
    return sorted(out, key=lambda x: (SEV_ORDER.get(x["severity"], 9), x["t"]))


def run(paths: dict | None = None, now: float | None = None, parts: list[dict] | None = None) -> dict:
    """Every part, both windows, read-only. Returns {now, windows: {"24h": {...}, "7d": {...}}}."""
    paths = {**default_paths(), **(paths or {})}
    now = int(now or time.time())
    out = {"now": now, "windows": {}}
    for label, span in WINDOWS:
        judged = [judge(p, paths, now, span) for p in (parts if parts is not None else PARTS)]
        misses = merge([m for r in judged for m in r["misses"]])
        out["windows"][label] = {
            "parts": len(judged), "expected": sum(r["expected"] or 0 for r in judged), "ok": sum(r["ok"] or 0 for r in judged),
            "misses": misses, "not_checked": [{"part": r["part"], "name": r["name"], "why": r["not_checked"]} for r in judged if r["not_checked"]],
            "by_part": {r["part"]: {"expected": r["expected"], "ok": r["ok"], "missed": len(r["misses"])} for r in judged}}
    return out


# ---------------------------------------------------------------------------
# the review section
# ---------------------------------------------------------------------------
def _when(t: int) -> str:
    return datetime.fromtimestamp(t, _tz(SHOW_TZ)).strftime("%b %d %H:%M").replace(" 0", " ")


def _utc_day(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%b %d").replace(" 0", " ")


def _line(m: dict) -> str:
    if m.get("utc_day") and m["kind"] != "down":          # a daily-close part: name the UTC day, not a Toronto evening
        span = f"UTC day {_utc_day(m['t'])}" if m["runs"] == 1 else f"UTC days {_utc_day(m['t'])} to {_utc_day(m['to'] - 1)}"
    elif m["runs"] == 1 and m["kind"] not in ("down", "lost"):
        span = _when(m["t"])
    else:
        span = f"{_when(m['t'])} to {_when(m['to'])}"
    runs = f", {m['runs']} runs" if m["runs"] > 1 and m["kind"] != "down" else ""
    found = ""
    if m["kind"] == "empty" and m.get("needed") is not None:
        hi = m.get("found_max", m["found"])
        did = f"{m['found']:g}" if hi == m["found"] else f"{m['found']:g} to {hi:g}"
        found = f", did {did} of at least {m['needed']:g}" + (" a run" if m["runs"] > 1 else "")
    det = f": {m['detail']}" if m.get("detail") else ""
    return f"- **{m['severity']}** {m['name']}: **{m['kind']}** {span}{runs}{found}{det}"


def markdown(res: dict, limit: int = 25) -> str:
    """The morning review's "## Lost or empty runs" section. It is never left out: with nothing missed it says "none"."""
    L = ["## Lost or empty runs", ""]
    w24, w7 = res["windows"]["24h"], res["windows"]["7d"]
    L.append(f"Checked read-only at {_when(res['now'])} Toronto: {w7['parts']} parts (jarvis/service/runcheck.py). "
             "Times are Toronto; daily-close parts name their UTC day.")
    for label, w in (("Last 24 hours", w24), ("Last 7 days", w7)):
        crypto = [m for m in w["misses"] if m["area"] != "india"]
        L.append("")
        if not crypto:
            L.append(f"**{label}: none.** {w['ok']:,} of {w['expected']:,} scheduled runs found with their work done.")
        else:
            L.append(f"**{label}: {len(crypto)} miss{'es' if len(crypto) != 1 else ''}** "
                     f"({w['ok']:,} of {w['expected']:,} scheduled runs found with their work done).")
            L += [_line(m) for m in crypto[:limit]]
            if len(crypto) > limit:
                L.append(f"- ... and {len(crypto) - limit} more (python -m jarvis.service.runcheck --json)")
    india = [m for m in w24["misses"] if m["area"] == "india"]
    L += ["", "**India (read-only, latest run of each job):** " + ("none." if not india else "")]
    L += [_line(m) for m in india]
    nc = [n for n in w24["not_checked"] if n["why"] and not n["why"].startswith(("no run due", "not started"))]
    if nc:
        L += ["", "**Cannot be checked (no dated proof):** " + "; ".join(f"{n['name']} ({n['why']})" for n in nc) + "."]
    late = [n["name"] for n in w24["not_checked"] if n["why"] and n["why"].startswith("no run due")]
    if late:
        L += ["", "Judged only in the 7-day list (their proof arrives a day late): " + ", ".join(late) + "."]
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    res = run(now=float(argv[argv.index("--now") + 1]) if "--now" in argv else None)
    print(json.dumps(res, indent=1, default=str) if "--json" in argv else markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
