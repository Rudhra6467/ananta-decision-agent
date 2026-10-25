"""The India exam (records repo india/registrations/india_exam_v1.json; judges in records india/exam.py, loaded by path).
Asks the 30 questions through jarvis/india/ask.py exactly as the app's chat does (owner view, one fresh thread each), in a separate
thread folder (<data>/ask_exam/) so the runs never show in Madhav's chat history or use the Ask's daily cap; judges every answer in
code against the facts the Ask was given; writes <data>/manifests/exam_latest.json and exam_history.jsonl.

  python scripts/run_india_exam.py            run now
  python scripts/run_india_exam.py --if-due   run only when the last full run is 6 or more days old (the India evening job, weekly cadence)
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))
DUE_DAYS = 6


def judges():
    sp = importlib.util.spec_from_file_location("india_exam_judges", RECORDS / "india" / "exam.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def due(ex, now: dt.datetime | None = None) -> bool:
    rs = [r for r in ex.runs() if not r.get("rejudged") and r.get("t")]
    if not rs:
        return True
    last = dt.datetime.fromtimestamp(rs[-1]["t"], dt.timezone.utc)
    return (now or dt.datetime.now(dt.timezone.utc)) - last >= dt.timedelta(days=DUE_DAYS)


def run(ex=None, ask_mod=None) -> dict:
    ex = ex or judges()
    if ask_mod is None:
        from jarvis.india import ask as ask_mod
    from jarvis.india import views

    ask_mod.ASK_DIR = ask_mod.DATA / "ask_exam"          # kept apart from the chat history and the daily cap
    ask_mod.ASK_DIR.mkdir(parents=True, exist_ok=True)
    sp = ex.spec()
    facts = ask_mod.facts(owner=True)
    rm = views.readmodel()
    answers, errors, ms = {}, {}, {}
    stamp = int(time.time())
    for k, q in enumerate(sp["questions"]):
        t0 = time.time()
        try:
            r = ask_mod.ask("owner", q["question"], thread=f"exam-{stamp}-{k}")
            answers[q["id"]] = str(r.get("answer") or "")
            if r.get("note"):
                errors[q["id"]] = f"offline answer: {r['note']}"
        except Exception as e:  # noqa: BLE001
            answers[q["id"]], errors[q["id"]] = "", f"{type(e).__name__}: {e}"
        ms[q["id"]] = int((time.time() - t0) * 1000)
    out = ex.grade(answers, facts, rm, errors, sp)
    for row in out["rows"]:
        row["ms"] = ms.get(row["id"])
    out.update({"t": stamp, "day": dt.date.today().isoformat(), "read_model_built_at": rm.get("built_at"), "data_through": rm.get("data_through"),
                "model": getattr(ask_mod, "MODEL", None), "facts_snapshot": {"facts": facts, "rm": rm}})
    return ex.save(out)


def main(argv: list[str]) -> int:
    ex = judges()
    if "--if-due" in argv and not due(ex):
        print(time.strftime("%Y-%m-%d %H:%M"), "india exam: not due (weekly);", ex.words(ex.latest()), flush=True)
        return 0
    t0 = time.time()
    e = run(ex)
    print(time.strftime("%Y-%m-%d %H:%M"), "INDIA EXAM", ex.words(e), "MINUTES", round((time.time() - t0) / 60, 1), flush=True)
    for r in e["rows"]:
        if not r["ok"] or r["safety"] or r["plain"]:
            print("  MISS", r["kind"], r["id"], "missed", r.get("missed"), "safety", r["safety"], "plain", r["plain"], "->", r["answer"][:200].replace("\n", " "), flush=True)
    try:                                   # the India voice check rides along (free, local): India phrases through India's speech path
        from jarvis.india import voice as india_voice
        v = india_voice.check()
        print(time.strftime("%Y-%m-%d %H:%M"), "INDIA VOICE CHECK", f"{v['understood']} of {v['of']} heard right", "PASS" if v["pass"] else "FAIL", flush=True)
        for r in v["rows"]:
            if not r["ok"]:
                print("  NOT HEARD", r["id"], repr(r["said"]), "->", repr(r["heard"]), flush=True)
    except Exception as exc:  # noqa: BLE001
        print("india voice check failed:", exc, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
