"""Run the Ananta test suite against the running Jarvis service and record everything.

    python -m jarvis.evals.run [--providers gemini,claude] [--only S1,U2] [--no-voice] [--no-stability]

Needs the service on 127.0.0.1:8100 and the agent .env loaded (JARVIS_SECRET, JARVIS_OWNER_EMAIL).
Writes eval_runs/<stamp>.json in JARVIS_AGENT_DIR (shown in the app: Cockpit > Test lab).
Anything the agent prepares during a test (paper orders, alerts, mandate edits) is cancelled right away; the test
also checks nothing was executed. The daily Claude budget is raised to $5 for the run and put back afterwards.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from jarvis.service import core

BASE = os.getenv("JARVIS_URL", "http://127.0.0.1:8100")
CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
MODE = {"gemini": "everyday", "claude": "deep"}


def token(ttl: int = 3 * 3600) -> str:
    return core.make_token(os.environ["JARVIS_SECRET"], os.environ["JARVIS_OWNER_EMAIL"].strip().lower(), time.time(), ttl=ttl)


H = {}


def get(p, **kw):
    return requests.get(BASE + p, headers=H, timeout=kw.pop("timeout", 60), **kw)


def post(p, body, **kw):
    return requests.post(BASE + p, headers=H, json=body, timeout=kw.pop("timeout", 180), **kw)


def text_of(r: dict) -> str:
    parts = [r.get("answer") or "", " ".join(r.get("breakdown") or []), " ".join(str(e.get("value", "")) + " " + str(e.get("label", "")) for e in r.get("evidence") or [])]
    return " ".join(parts)


def grade(exp: dict, r: dict, side: dict) -> list[dict]:
    checks = []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    if r.get("error"):
        ck("answered", False, r["error"][:200])
        return checks
    ck("answered", True)
    kind = r.get("kind")
    if "kind" in exp:
        ck(f"kind = {exp['kind']}", kind == exp["kind"], kind)
    if "kind_any" in exp:
        ck(f"kind in {exp['kind_any']}", kind in exp["kind_any"], kind)
    lk = r.get("lookups") or []
    if "lookups_any" in exp:
        ck(f"used one of {exp['lookups_any']}", any(x in lk for x in exp["lookups_any"]), ",".join(lk))
    if exp.get("no_lookups"):
        ck("used no lookups", not lk, ",".join(lk))
    t = text_of(r)
    if "must_any" in exp:
        ck(f"mentions one of {exp['must_any']}", any(w in t for w in exp["must_any"]))
    for w in exp.get("must_not", []):
        ck(f"does not say '{w}'", w not in (r.get("answer") or ""))
    acts = r.get("actions") or []
    if "actions_kind" in exp:
        ck(f"prepared a {exp['actions_kind']} card", any(a.get("kind") == exp["actions_kind"] for a in acts), ",".join(a.get("kind", "") for a in acts))
    if exp.get("no_actions"):
        ck("prepared no card", not acts)
    for k in exp.get("no_actions_kind", []):
        ck(f"prepared no {k} card", not any(a.get("kind") == k for a in acts))
    if "show_any" in exp:
        ck(f"offered a {exp['show_any']} screen", any(s.get("screen") in exp["show_any"] for s in r.get("show") or []))
    if "route_any" in exp:
        ck(f"looked in the right place ({'/'.join(exp['route_any'])})", r.get("route") in exp["route_any"], r.get("route"))
    ans = (r.get("answer") or "").strip()
    if ans and kind == "answer":
        import re as _re
        sents = [x for x in _re.split(r"(?<=[.!?])\s+", ans) if x.strip()]
        avg = sum(len(x.split()) for x in sents) / max(1, len(sents))
        ck("simple English (short sentences, short answer)", avg <= 22 and len(ans.split()) <= 110, f"{avg:.0f} words/sentence, {len(ans.split())} words")
    ui = r.get("ui") or []
    if "ui_any" in exp:
        ck(f"opened {exp['ui_any']}", any(u.get("target") in exp["ui_any"] for u in ui), ",".join(str(u.get("target") or u.get("do")) for u in ui))
    if "ui_prefix" in exp:
        ck(f"opened a {exp['ui_prefix']}* page", any(str(u.get("target", "")).startswith(exp["ui_prefix"]) for u in ui), ",".join(str(u.get("target")) for u in ui))
    if "ui_do" in exp:
        ck(f"did {exp['ui_do']}", any(u.get("do") == exp["ui_do"] for u in ui))
    pts = r.get("points") or []
    if "points_min" in exp:
        ck(f"pointed at {exp['points_min']}+ things on screen", len(pts) >= exp["points_min"], ",".join(p.get("spot", "") for p in pts))
    if "points_spot" in exp:
        ck(f"highlighted {exp['points_spot']}", any(p.get("spot") == exp["points_spot"] for p in pts), ",".join(p.get("spot", "") for p in pts))
    if exp.get("tour"):
        ck("started the guided tour", len(r.get("tour") or []) >= 8)
    if exp.get("no_ui"):
        ck("did not move the screen", not ui)
    if "max_s" in exp:
        ck(f"answered within {exp['max_s']}s", side["seconds"] <= exp["max_s"], f"{side['seconds']}s")
    ck("nothing executed", side.get("executed_ok", True), side.get("executed_detail", ""))
    return checks


def book_state() -> dict:
    m = get("/v3/manual").json()
    md = get("/v3/mandate").json()
    al = get("/v3/alerts").json()["alerts"]
    return {"fills": len(m["fills"]), "mandate": md["version"], "alerts": sum(1 for a in al if a["status"] == "ACTIVE")}


def run_provider(provider: str, cases: list[dict]) -> list[dict]:
    out, threads = [], {}
    for c in cases:
        before = book_state()
        t0 = time.time()
        body = {"text": c["q"], "mode": MODE[provider], "source": "eval",
                "context": {"here": c.get("here") or {"screen": "ananta", "label": "Ananta tab: this conversation"}}}
        if c.get("after") and threads.get(c["after"]):
            body["thread"] = threads[c["after"]]
        try:
            resp = post("/v3/ask", body)
            r = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"error": resp.text[:200]}
            if resp.status_code >= 400:
                r = {"error": f"HTTP {resp.status_code}: {r.get('detail', r)}"}
        except Exception as exc:  # noqa: BLE001
            r = {"error": f"{type(exc).__name__}: {exc}"[:200]}
        secs = round(time.time() - t0, 1)
        if r.get("thread"):
            threads[c["id"]] = r["thread"]
        cancelled = []
        for a in r.get("actions") or []:
            try:
                st = post(f"/v3/actions/{a['id']}", {"confirm": False}).json().get("status")
            except Exception:  # noqa: BLE001
                st = "?"
            cancelled.append(st)
        after = book_state()
        side = {"seconds": secs, "executed_ok": before == after, "executed_detail": "" if before == after else f"{before} -> {after}"}
        checks = grade(c["expect"], r, side)
        out.append({"id": c["id"], "cat": c["cat"], "q": c["q"], "provider": provider, "seconds": secs,
                    "model": r.get("model_label") or r.get("model"), "cost_usd": r.get("cost_usd"), "kind": r.get("kind"), "stage": r.get("stage"),
                    "answer": r.get("answer"), "breakdown": r.get("breakdown"), "evidence": r.get("evidence"), "lookups": r.get("lookups"),
                    "actions": [a.get("summary") for a in r.get("actions") or []], "cards_cancelled": cancelled, "show": r.get("show"),
                    "options": r.get("options"), "error": r.get("error"), "msg_id": r.get("id"), "route": r.get("route"), "timing": r.get("timing"), "ui": r.get("ui"), "points": r.get("points"),
                    "checks": checks, "passed": all(x["ok"] for x in checks)})
        print(f"[{provider}] {c['id']} {'PASS' if out[-1]['passed'] else 'FAIL'} {secs}s {(r.get('answer') or r.get('error') or '')[:90]}", flush=True)
    return out


def run_voice(provider: str) -> list[dict]:
    out = []
    for v in CASES["voice"]:
        f = Path(tempfile.mkdtemp()) / "q.wav"
        try:
            subprocess.run(["say", "-o", str(f), "--data-format=LEI16@16000", v["say"]], check=True, timeout=30)
        except Exception as exc:  # noqa: BLE001
            out.append({"id": v["id"], "provider": provider, "passed": False, "error": f"could not synthesize speech: {exc}"})
            continue
        t0 = time.time()
        r = post("/v3/voice/turn", {"audio_b64": base64.b64encode(f.read_bytes()).decode(), "mime": "audio/wav", "mode": MODE[provider], "source": "eval"}).json()
        secs = round(time.time() - t0, 1)
        heard = r.get("heard") or ""
        checks = [{"check": "transcribed", "ok": any(w in heard for w in v["expect"]["heard_any"]), "detail": heard},
                  {"check": "answered", "ok": bool(r.get("answer")) and not r.get("error"), "detail": (r.get("error") or "")[:120]},
                  {"check": "spoken answer is short (<= 60 words)", "ok": len((r.get("answer") or "").split()) <= 60, "detail": str(len((r.get("answer") or "").split()))}]
        if "show_any" in v["expect"]:
            checks.append({"check": "put a chart on stage", "ok": any(s.get("screen") in v["expect"]["show_any"] for s in r.get("show") or [])})
        for a in r.get("actions") or []:
            post(f"/v3/actions/{a['id']}", {"confirm": False})
        out.append({"id": v["id"], "cat": "Voice", "q": v["say"], "provider": provider, "seconds": secs, "heard": heard, "answer": r.get("answer"),
                    "model": r.get("model_label"), "cost_usd": r.get("cost_usd"), "show": r.get("show"), "error": r.get("error"),
                    "checks": checks, "passed": all(c["ok"] for c in checks)})
        print(f"[voice {provider}] {v['id']} {'PASS' if out[-1]['passed'] else 'FAIL'} {secs}s heard={heard!r}", flush=True)
    return out


def stability() -> list[dict]:
    res = []

    def ck(name, ok, detail=""):
        res.append({"id": "X" + str(len(res) + 1), "cat": "Stability", "q": name, "passed": bool(ok), "detail": str(detail)[:200]})
        print(f"[stability] {name}: {'PASS' if ok else 'FAIL'} {detail}", flush=True)

    ck("service is up", requests.get(BASE + "/health", timeout=10).ok)
    ck("no token is refused (401)", requests.get(BASE + "/v3/home", timeout=10).status_code == 401)
    ck("forged token is refused (401)", requests.get(BASE + "/v3/home", headers={"Authorization": "Bearer abc.def"}, timeout=10).status_code == 401)
    ck("wrong password is refused", requests.post(BASE + "/auth/login", json={"email": os.environ["JARVIS_OWNER_EMAIL"], "password": "wrong-on-purpose"}, timeout=20).status_code == 401)
    ck("empty question is refused (400)", post("/v3/ask", {"text": "  "}).status_code == 400)
    ck("unknown screen data is refused (400)", get("/v3/chart/NOPE").status_code == 400)
    ck("confirming an unknown card is refused (400)", post("/v3/actions/Anope", {"confirm": True}).status_code == 400)
    ck("mode change without confirm is refused (428)", post("/portfolio/mode", {"mode": "AUTO", "confirm": False}).status_code == 428)
    # switches
    post("/v3/settings", {"key": "ask_enabled", "value": "0"})
    r = post("/v3/ask", {"text": "how is btc", "mode": "everyday"})
    ck("Ask switch off blocks questions", r.status_code == 400 and "switched off" in r.text, r.status_code)
    post("/v3/settings", {"key": "ask_enabled", "value": "1"})
    # speed of every screen
    slow = []
    for p in ["/v3/home", "/v3/markets", "/v3/holdings", "/v3/trades", "/v3/manual", "/v3/evidence/collected", "/v3/evidence/forwarded",
              "/v3/cockpit", "/v3/inbox", "/v3/chart/BTC?tf=1h", "/v3/chart/ETH?tf=1d", "/v3/coin/SOL/watch", "/coin/ADA", "/history?days=30", "/v3/spend"]:
        t0 = time.time()
        code = get(p).status_code
        dt = time.time() - t0
        if code != 200 or dt > 3:
            slow.append(f"{p} {code} {dt:.1f}s")
    ck("every screen loads under 3 s", not slow, "; ".join(slow))
    # concurrency: 12 screen loads at once
    t0 = time.time()
    with cf.ThreadPoolExecutor(12) as ex:
        codes = list(ex.map(lambda p: get(p).status_code, ["/v3/home", "/v3/markets", "/v3/holdings", "/v3/cockpit"] * 3))
    ck("12 screens at once all succeed", all(c == 200 for c in codes), f"{codes} in {time.time() - t0:.1f}s")
    # two questions at once (free model)
    with cf.ThreadPoolExecutor(2) as ex:
        rs = list(ex.map(lambda q: post("/v3/ask", {"text": q, "mode": "everyday", "source": "eval"}).json(), ["How is BTC?", "How is SOL?"]))
    ck("two questions at the same time both answer", all(r.get("answer") for r in rs), [r.get("error") for r in rs])
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="gemini,claude")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-voice", action="store_true")
    ap.add_argument("--no-stability", action="store_true")
    a = ap.parse_args(argv)
    H["Authorization"] = f"Bearer {token()}"
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    cases = [c for c in CASES["cases"] if not only or c["id"] in only or any(c["id"] == d.get("after") for d in [])]
    if only:   # keep the conversation chain intact
        need = set(only)
        for c in CASES["cases"]:
            if c["id"] in need and c.get("after"):
                need.add(c["after"])
        cases = [c for c in CASES["cases"] if c["id"] in need]
    provs = [p.strip() for p in a.providers.split(",") if p.strip()]
    old_budget = get("/v3/spend").json()["settings"]["daily_budget_usd"]
    pending0 = {a["id"] for a in get("/v3/inbox").json().get("actions", [])}
    post("/v3/settings", {"key": "daily_budget_usd", "value": "5"})
    t0 = time.time()
    spend0 = get("/v3/spend").json()["today_usd"]
    try:
        results = []
        if not a.no_stability:
            results += stability()
        with cf.ThreadPoolExecutor(len(provs)) as ex:
            for part in ex.map(lambda p: run_provider(p, cases), provs):
                results += part
        if not a.no_voice:
            for p in provs:
                results += run_voice(p)
    finally:
        post("/v3/settings", {"key": "daily_budget_usd", "value": old_budget})
        for a in get("/v3/inbox").json().get("actions", []):          # anything a failed test left behind
            if a["id"] not in pending0:
                post(f"/v3/actions/{a['id']}", {"confirm": False})
    spend = round(get("/v3/spend").json()["today_usd"] - spend0, 4)
    summ: dict = {}
    for r in results:
        k = r.get("provider", "system")
        s = summ.setdefault(k, {"cases": 0, "passed": 0, "seconds": [], "cost": 0.0})
        s["cases"] += 1
        s["passed"] += r["passed"]
        if r.get("seconds") is not None:
            s["seconds"].append(r["seconds"])
        s["cost"] += r.get("cost_usd") or 0
    for s in summ.values():
        sec = sorted(s.pop("seconds"))
        s["median_s"] = sec[len(sec) // 2] if sec else None
        s["slowest_s"] = sec[-1] if sec else None
        s["cost"] = round(s["cost"], 4)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = {"run": stamp, "version": CASES["version"], "minutes": round((time.time() - t0) / 60, 1), "spend_usd": spend,
           "summary": summ, "results": results}
    d = Path(os.getenv("JARVIS_AGENT_DIR", ".")) / "eval_runs"
    d.mkdir(exist_ok=True)
    (d / f"{stamp}.json").write_text(json.dumps(run, indent=1, default=str))
    print(json.dumps({"run": stamp, "summary": summ, "spend_usd": spend, "minutes": run["minutes"]}, indent=1))


if __name__ == "__main__":
    main()
