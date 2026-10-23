"""The India morning summary (India learning loop, approved by Madhav 20 Oct 2026): did every India job run, and did it do its work?

  python -m india.morning        writes india/registrations/india_morning.md and prints it

For every launchd job named com.ananta.india.* it reads the last exit code (`launchctl list`), the plist (schedule, log files) and the log tails,
works out when the job was last due, and checks proof of work against what that job should have produced (the paper decision and marks, the SP1
ledger rows, the recorder's manifest rows, the depth snapshots, the nightly build's step results). The section "Lost or empty runs" is never
left out: it says "none" when there are none. Always listed there: a job whose last exit was not 0, a job with no output since it was due, a
job that ran without its proof of work, a failed step inside a chained job, a missing missed-movers manifest and a nightly replay that did not
pass. A Kite token rejected after Zerodha's morning flush is named as such, with the next sign-in window, not left as a traceback.
It also carries the latest missed-movers line and the nightly SP1 replay result. It reads files and `launchctl list` only; it calls no API.
"""
from __future__ import annotations

import datetime as dt
import json
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from india import dayplan, paths

TOR = ZoneInfo("America/Toronto")
IST = ZoneInfo("Asia/Kolkata")
PREFIX = "com.ananta.india."
AGENTS = Path.home() / "Library" / "LaunchAgents"
REG = Path(__file__).parent / "registrations"
SP1_PAPER_START = dt.date(2026, 10, 21)
SIGNIN_FROM, SIGNIN_BY = dt.time(7, 30), dt.time(9, 10)   # IST: after Zerodha's morning token flush (about 07:00-07:30), before SP1's 09:10 cut-off
TOKEN_WORDS = ("TokenException", "NeedLogin", "Kite login needed", "no Kite token on disk", "token expired")
MARK = "=== "   # a run marker line a chained job may print to its error log; the summary reads the error log from the last marker on
GRACE = dt.timedelta(minutes=10)
DEFAULT_DUE = {"paper": {"Hour": 22, "Minute": 30}, "evening": {"Hour": 19, "Minute": 0}}   # used when a plist is missing


# ----------------------------------------------------------------------------------------------------------------------------- helpers
def _holidays() -> set:
    try:
        return dayplan.holidays(refresh=False)
    except Exception:
        return set()


def is_session(d: dt.date, hol: set | None = None) -> bool:
    hol = _holidays() if hol is None else hol
    return d.weekday() < 5 and d not in hol


def next_session(after: dt.date, hol: set | None = None) -> dt.date:
    d = after
    while not is_session(d, hol):
        d += dt.timedelta(days=1)
    return d


def next_signin(now: dt.datetime, hol: set | None = None) -> str:
    """The next Kite sign-in window: on the next session's IST morning, after the flush and before 09:10 IST (SP1's cut-off)."""
    ist = now.astimezone(IST)
    day = ist.date() if (ist.time() < SIGNIN_BY and is_session(ist.date(), hol)) else next_session(ist.date() + dt.timedelta(days=1), hol)
    a = dt.datetime.combine(day, SIGNIN_FROM, IST).astimezone(TOR)
    b = dt.datetime.combine(day, SIGNIN_BY, IST).astimezone(TOR)
    return f"{a:%a %d %b %H:%M}-{b:%H:%M} Toronto (07:30-09:10 IST, for the {day:%a %d %b} session)"


def launchctl_list(text: str | None = None) -> dict[str, dict]:
    if text is None:
        try:
            text = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=20).stdout
        except Exception:
            text = ""
    out = {}
    for line in text.splitlines():
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) >= 3 and parts[2].startswith(PREFIX):
            pid = None if parts[0] == "-" else parts[0]
            try:
                status = int(parts[1])
            except ValueError:
                status = None
            out[parts[2]] = {"pid": pid, "last_exit": status}
    return out


def _plist(agents: Path, label: str) -> dict:
    p = agents / f"{label}.plist"
    if not p.exists():
        return {}
    try:
        return plistlib.loads(p.read_bytes())
    except Exception:
        return {}


def last_due(intervals, now: dt.datetime) -> dt.datetime | None:
    """The latest scheduled time at or before `now` (Toronto) for a StartCalendarInterval (dict or list; launchd Weekday 0 and 7 are Sunday)."""
    if not intervals:
        return None
    if isinstance(intervals, dict):
        intervals = [intervals]
    best = None
    for iv in intervals:
        for back in range(0, 9):
            d = (now - dt.timedelta(days=back)).date()
            if "Weekday" in iv and (iv["Weekday"] % 7) != (d.isoweekday() % 7):
                continue
            t = dt.datetime.combine(d, dt.time(int(iv.get("Hour", 0)), int(iv.get("Minute", 0))), TOR)
            if t <= now and (best is None or t > best):
                best = t
                break
    return best


def _mtime(p: Path | None) -> dt.datetime | None:
    try:
        return dt.datetime.fromtimestamp(p.stat().st_mtime, TOR) if p and p.exists() else None
    except OSError:
        return None


def _tail(p: Path | None, n: int = 400) -> list[str]:
    if not p or not p.exists():
        return []
    try:
        with p.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 200_000))
            lines = fh.read().decode("utf-8", "replace").splitlines()
        return lines[-n:]
    except OSError:
        return []


def _since_marker(lines: list[str]) -> list[str]:
    idx = [i for i, x in enumerate(lines) if x.startswith(MARK)]
    return lines[idx[-1] + 1:] if idx else lines


def _errors(lines: list[str]) -> list[str]:
    """The final line of each traceback (the exception), with the module that was running when the file shows it."""
    out, mod = [], None
    for i, x in enumerate(lines):
        if x.startswith("Traceback"):
            mod = None
        m = re.search(r'/india/(\w+)\.py", line \d+, in <module>', x)
        if m and mod is None:
            mod = "india." + m.group(1)
        if re.match(r"^[\w.]+(Error|Exception|NeedLogin|Exit)\b.*:", x) or re.match(r"^[\w.]*\.(NeedLogin|CatalogException)", x):
            out.append(f"{mod or '?'}: {x.strip()[:200]}")
            mod = None
    return out


def _token_dead(lines: list[str]) -> bool:
    return any(w in x for x in lines for w in TOKEN_WORDS)


def _json_lines(p: Path, n: int = 5000) -> list[dict]:
    out = []
    for x in _tail(p, n):
        try:
            out.append(json.loads(x))
        except ValueError:
            continue
    return out


def _last_json_block(lines: list[str]) -> dict | None:
    """The last JSON object a job printed (india.nightly and india.paper print one, indented)."""
    starts = [i for i, x in enumerate(lines) if x.strip() == "{" and not x.startswith(" ")]
    for s in reversed(starts):
        try:
            return json.loads("\n".join(lines[s:]))
        except ValueError:
            for e in range(len(lines), s, -1):
                if lines[e - 1].startswith("}"):
                    try:
                        return json.loads("\n".join(lines[s:e]))
                    except ValueError:
                        continue
    return None


# ----------------------------------------------------------------------------------------------------------------------------- proof of work
def proof(label: str, due: dt.datetime | None, ctx: dict) -> tuple[bool | None, str]:
    """(ok, what was found) for one job's last due run. ok None: nothing was expected (no session) or there is no check for this job."""
    D, hol, out_lines = ctx["data"], ctx["hol"], ctx["out_lines"]
    if due is None:
        return None, "no schedule"
    d = due.date()
    name = label[len(PREFIX):]
    if name == "paper":
        dec = D / "paper" / "decisions" / f"{d}.json"
        marks = _json_lines(D / "paper" / "marks.jsonl", 600)
        last_mark = max((m.get("at", "") for m in marks), default="")
        marked = last_mark >= due.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
        if is_session(d, hol):
            if not dec.exists():
                return False, f"no decision file for the {d} session; marks {'written' if marked else 'not written'} since {due:%H:%M}"
            b = json.loads(dec.read_text())
            uni = (D / "paper" / "decisions" / f"{d}.universe.json").exists()
            return marked, (f"decision {d}: {len(b.get('signals', []))} signals (written {b.get('decided_at', '?')[:16]}Z); "
                            f"universe file {'yes' if uni else 'no'}; marks {'written' if marked else 'NOT written'} since {due:%H:%M}")
        return marked, f"no session on {d}: no decision expected; marks {'written' if marked else 'NOT written'} since {due:%H:%M}"
    if name == "sp1paper":
        ist_day = due.astimezone(IST).date()
        if not is_session(ist_day, hol) or ist_day < SP1_PAPER_START:
            sk = any('"skipped"' in x for x in out_lines[-20:])
            return (True if sk else None), f"IST {ist_day}: {'no session' if not is_session(ist_day, hol) else 'before the paper start ' + str(SP1_PAPER_START)}; run said skipped: {sk}"
        rows = [r for r in _json_lines(D / "paper" / "sp1" / "decisions.jsonl") if r.get("date") == ist_day.isoformat()]
        dec = [r for r in rows if r.get("kind") == "decision"]
        errs = [r.get("error") for r in rows if r.get("kind") == "error"]
        plan = any(r.get("kind") == "plan" for r in rows)
        ok = bool(dec) and not errs
        return ok, f"IST {ist_day}: plan {'yes' if plan else 'NO'}, {len(dec)} decision rows" + (f", errors {errs}" if errs else "")
    if name == "sp1paper.score":
        b = D / "paper" / "sp1" / "book.json"
        m = _mtime(b)
        ok = m is not None and m >= due - dt.timedelta(minutes=1)
        return ok, f"book.json {'updated ' + format(m, '%d %b %H:%M') if m else 'missing'}"
    if name == "spreads":
        ist_day = due.astimezone(IST).date()
        if not is_session(ist_day, hol):
            return None, f"IST {ist_day}: no session"
        folder = D / "bronze" / "kite_depth" / f"date={ist_day}"
        n = len(list(folder.glob("*"))) if folder.exists() else 0
        return n > 0, f"IST {ist_day}: {n} depth snapshots"
    if name in ("recorder_noon", "evening"):
        lo = due.astimezone(dt.timezone.utc).isoformat(timespec="seconds")
        hi = (due + dt.timedelta(hours=12)).astimezone(dt.timezone.utc).isoformat(timespec="seconds")
        rows = [r for r in _json_lines(D / "manifests" / "kite_1m_fo.jsonl", 6000) if r.get("status") == "ok" and lo <= str(r.get("fetched_at", "")) < hi]
        txt = f"recorder: {len(rows)} contracts saved since {due:%H:%M}"
        if name == "evening":
            nxt = next_session(d + dt.timedelta(days=1), hol)
            plan = (D / "paper" / "dayplans" / f"{nxt}.json").exists()
            txt += f"; day plan for {nxt}: {'yes' if plan else 'no'}"
            return (len(rows) > 0 and plan), txt
        return len(rows) > 0, txt
    if name == "nightly":
        blk = _last_json_block(out_lines)
        if not blk:
            return False, "no result block in the log"
        failed = [k for k, v in blk.items() if str(v).startswith("FAILED")]
        return not failed, f"window {blk.get('window')}, {blk.get('seconds')} s" + (f"; FAILED steps: {', '.join(failed)}" if failed else "; every step ok")
    return None, "no proof-of-work check for this job"


# ----------------------------------------------------------------------------------------------------------------------------- report
def job_report(label: str, lc: dict, agents: Path, now: dt.datetime, ctx: dict) -> dict:
    pl = _plist(agents, label)
    out_p = Path(pl["StandardOutPath"]) if pl.get("StandardOutPath") else None
    err_p = Path(pl["StandardErrorPath"]) if pl.get("StandardErrorPath") else None
    due = last_due(pl.get("StartCalendarInterval"), now - GRACE)   # a run due in the last few minutes is judged next time
    last_out = max((m for m in (_mtime(out_p), _mtime(err_p)) if m), default=None)
    out_lines = _tail(out_p)
    err_all = _tail(err_p)
    err_mt = _mtime(err_p)
    fresh_err = err_mt is not None and due is not None and err_mt >= due - dt.timedelta(minutes=1)
    err_lines = _since_marker(err_all) if fresh_err else []
    ok, found = proof(label, due, {**ctx, "out_lines": _since_marker(out_lines)})
    r = {"label": label, "pid": lc.get("pid"), "last_exit": lc.get("last_exit"), "due": due, "last_output": last_out, "proof_ok": ok, "proof": found,
         "errors": _errors(err_lines), "token_dead": _token_dead(err_lines), "problems": []}
    running = r["pid"] is not None
    if pl.get("KeepAlive") and not pl.get("StartCalendarInterval"):       # a service (the India web app), not a job: healthy means running now
        r["service"] = True
        if not running:
            r["problems"].append("service not running")
        else:
            r["problems_note"] = f"running now (pid {r['pid']})"
        return r
    if r["last_exit"] not in (0, None):
        if r["token_dead"]:
            r["problems"].append(f"exit {r['last_exit']}: token dead" + (", expected (the token was flushed before the session)" if label.endswith(".spreads") else "")
                                 + f"; next sign-in {ctx['signin']}")
        else:
            r["problems"].append(f"exit {r['last_exit']}: " + ("; ".join(r["errors"][-2:]) if r["errors"] else "no error line in the log tail"))
    if due is not None and not running and (last_out is None or last_out < due - dt.timedelta(minutes=1)):
        r["problems"].append(f"lost run: due {due:%a %d %b %H:%M}, no output since {last_out:%a %d %b %H:%M}" if last_out else f"lost run: due {due:%a %d %b %H:%M}, no log at all")
    elif ok is False and not running:
        r["problems"].append(f"empty run: {found}")
    if r["last_exit"] == 0 and r["errors"]:
        mods = sorted({e.split(":")[0] for e in r["errors"]})
        r["problems"].append(f"steps failed inside the job ({', '.join(mods)})" + (f": token dead; next sign-in {ctx['signin']}" if r["token_dead"] else f": {r['errors'][-1]}"))
    if running:
        r["problems_note"] = f"running now (pid {r['pid']})"
    return r


def build(now: dt.datetime | None = None, launchctl_text: str | None = None, agents: Path | None = None, reg: Path | None = None) -> dict:
    now = (now or dt.datetime.now(TOR)).astimezone(TOR)
    agents = agents or AGENTS
    reg = reg or REG
    D = paths.data_dir()
    hol = _holidays()
    ctx = {"data": D, "hol": hol, "signin": next_signin(now, hol)}
    lc = launchctl_list(launchctl_text)
    labels = sorted(set(lc) | {p.stem for p in agents.glob(PREFIX + "*.plist")})
    jobs = [job_report(lb, lc.get(lb, {"pid": None, "last_exit": None, "not_loaded": True}), agents, now, ctx) for lb in labels]
    for j in jobs:
        if j["label"] not in lc:
            j["problems"].insert(0, "plist present but the job is not loaded in launchd")
    lost = [f"{j['label'][len(PREFIX):]}: {p}" for j in jobs for p in j["problems"]]
    # the learning loop's own outputs. india.missed runs after the stock paper run (22:30 Toronto) for that Toronto date; india.sp1nightly runs in
    # the evening job (19:00 Toronto) for that date. Each writes a result for every date it runs, a holiday included.
    due_of = lambda name: next((j["due"] for j in jobs if j["label"] == PREFIX + name and j["due"]), None) or last_due(DEFAULT_DUE[name], now - GRACE)
    mday = due_of("paper").date()
    mm = D / "manifests" / f"missed_{mday}.json"
    missed_line = None
    if mm.exists():
        man = json.loads(mm.read_text())
        missed_line = man.get("md_line")
        if not missed_line:
            p = reg / "missed_movers.md"
            missed_line = next((x for x in (p.read_text().splitlines() if p.exists() else []) if x.startswith(f"| {mday} |")), None)
        if man.get("status") != "ok" and not str(man.get("status")).startswith("no session"):
            lost.append(f"missed movers {mday}: {man.get('status')}")
    else:
        lost.append(f"missed movers: no manifest for {mday} (india.missed did not run after the paper run)")
    # the reference-traders review (india.others, 22 Oct 2026) runs right after india.missed in the same job
    om = D / "manifests" / f"others_{mday}.json"
    others_line = None
    if om.exists():
        oman = json.loads(om.read_text())
        if oman.get("status") == "ok":
            lg = oman.get("league", {})
            parts = []
            for h in ("1", "5", "20"):
                x = lg.get(h) or {}
                if x.get("sessions"):
                    cv = x.get("coverage", {})
                    pct = "" if x.get("ananta_pct_vs_random") is None else f", Ananta at the {x['ananta_pct_vs_random']:.0%} point of random"
                    parts.append(f"H{h} ({x['sessions']} sessions): hindsight {x['HINDSIGHT']:+.2%}, market {x['MARKET']:+.2%}, Ananta "
                                 f"{'' if x.get('ANANTA') is None else format(x['ANANTA'], '+.2%')}{pct}; of the best rises: took {cv.get('TAKEN', 0)}, "
                                 f"passed {cv.get('PASSED', 0)}, not covered {cv.get('NOT_COVERED', 0)}")
            others_line = "; ".join(parts) if parts else "no horizon has two live sessions yet"
            if oman.get("drafts_written"):
                others_line += f"; drafts: {', '.join(oman['drafts_written'])}"
        elif not str(oman.get("status")).startswith("no session"):
            lost.append(f"reference traders {mday}: {oman.get('status')}")
    else:
        lost.append(f"reference traders: no manifest for {mday} (india.others did not run after the paper run)")
    rday = due_of("evening").date()
    rp = D / "manifests" / "sp1_nightly_replay.json"
    replay = json.loads(rp.read_text()) if rp.exists() else None
    history = _json_lines(D / "manifests" / "sp1_nightly_replay.jsonl", 400) + ([replay] if replay else [])
    mine = next((x for x in reversed(history) if x.get("date") == rday.isoformat()), None)
    if replay is None and not history:
        lost.append(f"SP1 nightly replay: no result file (india.sp1nightly has not run; expected for {rday})")
    elif mine is None:
        lost.append(f"SP1 nightly replay: no result for {rday} (the latest is for {history[-1].get('date')}: {history[-1].get('status')})")
    else:
        st = str(mine.get("status"))
        if not (st == "PASS" or st == "skipped (holiday)" or st.startswith("skipped (no ledger rows)")):
            lost.append(f"SP1 nightly replay {rday}: {st}" + (f" ({mine.get('detail')})" if mine.get("detail") else "")
                        + (f"; next sign-in {ctx['signin']}" if st == "skipped (no token)" else ""))
    res = {"at": now, "jobs": jobs, "lost": lost, "missed_line": missed_line, "others_line": others_line, "missed_session": str(mday), "replay": replay, "signin": ctx["signin"]}
    reg.mkdir(parents=True, exist_ok=True)
    md = markdown(res)
    (reg / "india_morning.md").write_text(md)
    res["markdown"] = md
    return res


def _fmt(t: dt.datetime | None) -> str:
    return format(t, "%a %d %b %H:%M") if t else "-"


def markdown(r: dict) -> str:
    at = r["at"]
    L = [f"# India morning summary ({at:%a %d %b %Y %H:%M} Toronto, {at.astimezone(IST):%H:%M} IST)", "",
         "Generated by `python -m india.morning` from `launchctl list`, the job plists, their log tails and each job's proof of work.", "",
         "## Lost or empty runs", ""]
    L += [f"- {x}" for x in r["lost"]] or ["- none"]
    L += ["", f"Next Kite sign-in window: {r['signin']}.", "", "## Jobs", "", "| job | last exit | due | last output | proof of work | note |", "|---|---|---|---|---|---|"]
    for j in r["jobs"]:
        pf = {True: "ok", False: "MISSING", None: "n/a"}[j["proof_ok"]]
        note = j.get("problems_note") or ("; ".join(j["problems"]) if j["problems"] else "")
        L.append(f"| {j['label'][len(PREFIX):]} | {j['last_exit'] if j['last_exit'] is not None else '-'} | {_fmt(j['due'])} | {_fmt(j['last_output'])} | "
                 f"{pf}: {j['proof']} | {note} |")
    L += ["", f"## Reference traders against Ananta ({r['missed_session']})", "", f"- {r.get('others_line') or 'no reference-traders result for the session'}",
          "", f"## Missed movers ({r['missed_session']})", ""]
    if r["missed_line"]:
        L += ["| date | gainers | catches (P&L so far) | gainer misses | losers | top (b) situations | drafts |", "|---|---|---|---|---|---|---|", r["missed_line"]]
    else:
        L.append("no line for this session")
    rp = r["replay"]
    L += ["", "## SP1 nightly replay", ""]
    if rp:
        L.append(f"- {rp.get('date')}: **{rp.get('status')}**" + (f" ({rp.get('detail')})" if rp.get("detail") else ""))
        v = rp.get("verify") or {}
        L.append(f"- ledger check (sp1paper.verify): {'ok' if v.get('ok') else 'NOT ok'}; decisions {v.get('decisions')}, outcomes {v.get('outcomes')}")
        for m in (rp.get("replay") or {}).get("mismatches", [])[:10]:
            L.append(f"- mismatch: {json.dumps(m, default=str)[:300]}")
    else:
        L.append("- no result file yet")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    paths.ensure()
    out = build()
    print(out["markdown"])
    sys.exit(0)
