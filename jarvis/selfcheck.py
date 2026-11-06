"""Ananta's live self-check: what is not right right now (Madhav, 5 Nov 2026: "it can oversee, it can understand, it can guide, it can
tell if something is not right").

refresh() runs with the crypto service's 15-minute jobs (jarvis/service/app.py) and writes ~/ananta_data/selfcheck.json. Both Asks read
that file through check(); an answer never waits for these checks. It only reads: it changes nothing, sends nothing and costs nothing.

What it looks at:
  runs        every scheduled part of both markets in the last 24 hours (the lost-runs check, jarvis/service/runcheck.py)
  services    the crypto service, the India service, the voice server and the voice-print model answer
  answers     the nightly replay of real answers and the fact map (docs/repair_shop/replay, docs/repair_shop/factmap)
  leftovers   a test card waiting in Madhav's approvals (5 Nov: one sat there for four days)
  watchdog    restarts in the last 24 hours
  credit      a one-word Claude call: an empty API balance is refused at once (5 Nov 14:53)
  mac         free memory, swap and load on the Mac: a starved service looks frozen (5 Nov 19:34)
"""
from __future__ import annotations

import json
import re
import os
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
ROOT = Path(__file__).resolve().parents[1]
FILE = Path(os.getenv("ANANTA_SELFCHECK", str(HOME / "ananta_data" / "selfcheck.json")))
CRYPTO_DB = Path(os.getenv("JARVIS_DB", str(HOME / "code" / "ananta-decision-agent" / "jarvis.sqlite")))
STALE_S = 40 * 60
SERVICES = (("the crypto service", "http://127.0.0.1:8100/health", "crypto"),
            ("the India service", "http://127.0.0.1:8110/health", "india"),
            ("the voice server", "http://127.0.0.1:8200/health", "both"),
            ("the voice-print model", "http://127.0.0.1:8215/health", "both"))
KIND_WORDS = {"no run": "did not run", "errored": "ran with an error", "empty": "ran but did too little", "lost": "lost work",
              "down": "was down"}
SEV = {"high": 0, "medium": 1, "low": 2}


def _when(t: float) -> str:
    lt = time.localtime(t)
    return f"{lt.tm_mday} {time.strftime('%b %H:%M', lt)} Toronto"


def _get(url: str, opener=None) -> dict | None:
    try:
        with (opener or urllib.request.urlopen)(url, timeout=2) as r:
            body = r.read(4000)
            try:
                return json.loads(body)
            except ValueError:
                return {"ok": True}
    except Exception:  # noqa: BLE001  not answering is the finding
        return None


def _runs(now: float) -> list[dict]:
    from jarvis.service import runcheck

    out = []
    r = runcheck.run(now=now)
    for m in (r.get("windows") or {}).get("24h", {}).get("misses") or []:
        det = str(m.get("detail") or "").split(" (")[0][:120]
        if m.get("kind") == "down":
            what = f"a part was down at {_when(m.get('t') or now)}" + (f" ({det})" if det else "")
        else:
            what = f"{m.get('name')} {KIND_WORDS.get(m.get('kind'), m.get('kind'))} at {_when(m.get('t') or now)}" + (f" ({det})" if det else "")
        out.append({"market": m.get("area") or "both", "severity": m.get("severity") or "medium", "source": "lost-runs check", "what": what})
    return out


def _services(opener=None) -> list[dict]:
    out = []
    for name, url, market in SERVICES:
        h = _get(url, opener)
        if h is None:
            out.append({"market": market, "severity": "high", "source": "services", "what": f"{name} is not answering"})
        elif market == "crypto" and isinstance(h.get("jobs_s_ago"), (int, float)) and h["jobs_s_ago"] > 45 * 60:
            out.append({"market": "crypto", "severity": "high", "source": "services",
                        "what": f"the crypto 15-minute jobs last ran {int(h['jobs_s_ago'] // 60)} minutes ago"})
    return out


def _answers() -> list[dict]:
    out = []
    try:
        r = json.loads((ROOT / "docs" / "repair_shop" / "replay" / "latest.json").read_text())
        s = r.get("summary") or {}
        bad = [f for f in r.get("failures") or [] if f.get("source") in ("today", "never_again")]
        if bad:
            ex = bad[0]
            why = ((ex.get("problems") or [{}])[0].get("why") or "")[:160]
            out.append({"market": "india", "severity": "low", "source": "nightly replay",            # told when asked, not as a nudge
                        "what": (f"last night's replay ({s.get('night')}) found {len(bad)} of my India answers wrong; for example "
                                 f"\"{str(ex.get('text'))[:60]}\": {why}")})
    except (OSError, ValueError):
        pass
    try:
        f = json.loads((ROOT / "docs" / "repair_shop" / "factmap" / "latest.json").read_text())
        if f.get("fails"):
            out.append({"market": "india", "severity": "medium", "source": "fact map",
                        "what": f"the fact map found {f['fails']} place(s) where a screen and my answers disagree ({f.get('at')})"})
    except (OSError, ValueError):
        pass
    return out


def _leftovers(db: Path = CRYPTO_DB) -> list[dict]:
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        rows = con.execute("SELECT id, summary FROM pending_actions WHERE status='PENDING' AND thread IN "
                           "(SELECT thread FROM ask_messages WHERE role='user' AND COALESCE(mode,'') LIKE 'eval:%')").fetchall()
        con.close()
    except sqlite3.Error:
        return []
    return [{"market": "crypto", "severity": "high", "source": "approvals",
             "what": f"a test card is waiting in your approvals though you never asked for it: {s[:100]}"} for _, s in rows]


def _restarts(now: float) -> list[dict]:
    out = []
    for f in sorted((HOME / "ananta_runs" / "stalls").glob("*_*.txt")) if (HOME / "ananta_runs" / "stalls").exists() else []:
        try:
            if f.stat().st_mtime < now - 86400:
                continue
        except OSError:
            continue
        which = "India" if f.name.startswith("india_") else "crypto (Jarvis)"
        out.append({"market": "india" if which == "India" else "crypto", "severity": "medium", "source": "watchdog",
                    "what": f"the {which} service froze and the watchdog restarted it at {_when(f.stat().st_mtime)}"})
    return out


def mac_stats() -> dict:
    """Free memory (%), swap in use (GB), load (5-minute) and cores, read from the Mac (read-only, about 0.1 s)."""
    import subprocess

    out: dict = {"cores": os.cpu_count() or 1}
    try:
        out["load1"], out["load5"], _ = (round(x, 1) for x in os.getloadavg())
    except OSError:
        pass
    try:
        txt = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"free percentage:\s*(\d+)%", txt)
        if m:
            out["free_pct"] = int(m.group(1))
    except Exception:  # noqa: BLE001
        pass
    try:
        txt = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"used\s*=\s*([\d.]+)([MG])", txt)
        if m:
            out["swap_gb"] = round(float(m.group(1)) / (1024 if m.group(2) == "M" else 1), 1)
    except Exception:  # noqa: BLE001
        pass
    return out


def _mac(stats: dict | None = None) -> list[dict]:
    """5 Nov 2026 evening (Madhav's yes to the audit's recommendations): the 19:34 false restart came from a starved Mac (swapping under the
    voice models and the jobs) and nothing watched that. Medium when memory is nearly gone or the load is twice the cores; low when it is
    getting tight. Words carry the numbers, so the voice can say them."""
    st = stats if stats is not None else mac_stats()
    free, swap, load5, cores = st.get("free_pct"), st.get("swap_gb"), st.get("load5"), st.get("cores") or 1
    medium = (free is not None and free < 10) or (load5 is not None and load5 >= 2 * cores)
    low = (free is not None and free < 20) or (swap is not None and swap >= 8) or (load5 is not None and load5 >= cores)
    if not (medium or low):
        return []
    bits = [f"{free}% of memory free" if free is not None else None, f"{swap} GB of swap in use" if swap is not None else None,
            f"load {load5} on {cores} cores" if load5 is not None else None]
    return [{"market": "both", "severity": "medium" if medium else "low", "source": "Mac load",
             "what": (f"the Mac is {'short of memory or overloaded' if medium else 'getting tight'} ({', '.join(b for b in bits if b)}): the voice "
                      "and the answers can be slow, and a service can be starved for a while, as the India service was at 19:34 on 5 Nov")}]


def _credit(post=None) -> list[dict]:
    """5 Nov 2026, 14:53 Toronto: the Anthropic credit ran out and nothing said so; India's answers fell back to its rules and crypto's to
    Gemini. A one-token call with the services' own key says whether Claude still answers (an empty balance is refused at once, free)."""
    return credit_probe(os.getenv("ANTHROPIC_API_KEY", ""), post)


def credit_probe(key: str, post=None) -> list[dict]:
    if not key:
        return []
    body = {"model": os.getenv("ASK_HAIKU_MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 1, "messages": [{"role": "user", "content": "ok"}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with (post or urllib.request.urlopen)(req, timeout=15) as r:
            r.read(200)
        return []
    except urllib.error.HTTPError as e:
        why = e.read(600).decode(errors="replace").lower()
    except Exception:  # noqa: BLE001  no network or a timeout: not a finding about the credit
        return []
    if "credit balance" in why:
        return [{"market": "both", "severity": "high", "source": "Claude credit",
                 "what": ("Claude's API credit has run out, so India answers from its rules only and crypto falls back to Gemini; "
                          "Madhav can top it up in the Anthropic Console under Plans & Billing")}]
    return []


def refresh(now: float | None = None, opener=None, write: bool = True, post=None) -> dict:
    now = now or time.time()
    items: list[dict] = []
    for name, fn in (("runs", lambda: _runs(now)), ("services", lambda: _services(opener)), ("answers", _answers),
                     ("leftovers", _leftovers), ("watchdog", lambda: _restarts(now)), ("credit", lambda: _credit(post)), ("mac", _mac)):
        try:
            items += fn()
        except Exception as exc:  # noqa: BLE001  one check failing is itself a finding, never a crash
            items.append({"market": "both", "severity": "low", "source": name, "what": f"the {name} check could not run ({type(exc).__name__})"})
    items.sort(key=lambda x: SEV.get(x.get("severity"), 3))
    out = {"at": int(now), "at_words": _when(now), "items": items}
    if write:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1))
        tmp.replace(FILE)
    return out


def check(market: str | None = None, now: float | None = None) -> dict:
    """The last self-check, for one market's Ask (its own items and the shared ones); says so when the check itself is stale."""
    now = now or time.time()
    try:
        c = json.loads(FILE.read_text())
    except (OSError, ValueError):
        return {"at": None, "items": [{"market": "both", "severity": "medium", "source": "self-check",
                                       "what": "the self-check has not run yet (it runs with the crypto service's 15-minute jobs)"}]}
    # 5 Nov evening audit (the blind grade): each side reported only its own market's items, so the crypto voice said "one item" and the India
    # voice "two things" about the same check. Ananta is one system: every item is told on both sides, this market's first, each named by side.
    own = [x for x in c.get("items") or [] if market is None or x.get("market") in (market, "both")]
    other = [x for x in c.get("items") or [] if x not in own]
    items = own + other
    if now - (c.get("at") or 0) > STALE_S:
        items.insert(0, {"market": "both", "severity": "medium", "source": "self-check",
                         "what": f"the self-check last ran at {c.get('at_words')}, so this may be out of date"})
    return {"at": c.get("at"), "at_words": c.get("at_words"), "items": items}


SIDE = {"india": "India side: ", "crypto": "crypto side: ", "both": ""}


def words(c: dict) -> list[str]:
    items = c.get("items") or []
    if not items:
        return [f"Nothing is wrong right now (checked {c.get('at_words')}): every scheduled part ran in the last 24 hours, the services "
                "answer, last night's replay passed and no test card is waiting."]
    return [f"{SIDE.get(x.get('market'), '')}{x['what']} ({x['severity']}, from the {x['source']})" for x in items]


CHECKS = (("runs", "every scheduled part of both markets ran in the last 24 hours"), ("services", "the four services answer (crypto, India, voice, voice print)"),
          ("answers", "last night's replay of real answers and the fact map"), ("leftovers", "no test card is waiting in approvals"),
          ("watchdog", "no watchdog restart"), ("credit", "Claude answers (the API credit is there)"),
          ("mac", "the Mac has memory and CPU to spare"))


SOURCE_CHECK = {"lost-runs check": "runs", "services": "services", "nightly replay": "answers", "fact map": "answers", "approvals": "leftovers",
                "watchdog": "watchdog", "Claude credit": "credit", "Mac load": "mac"}


def fine(c: dict) -> list[str]:
    """What the last self-check looked at and found in order (5 Nov evening audit: an answer said 'please check the credit was topped up'
    hours after it was, because only the problems were in front of the model)."""
    bad = {SOURCE_CHECK.get(str(x.get("source")), str(x.get("source"))) for x in c.get("items") or []}
    ok = [w for k, w in CHECKS if k not in bad]
    when = c.get("at_words") or "not run yet"
    n = len([x for x in c.get("items") or [] if x.get("source") != "self-check"])
    head = f"the same check ({when}) found {n} item{'s' if n != 1 else ''} not right (listed in not_right) and the rest in order: " if n else f"checked {when}, all in order: "
    return [head + "; ".join(ok)] if ok else [f"checked {when}"]


def headline(c: dict) -> str | None:
    """One sentence for the start of a conversation: only high or medium items, at most two."""
    top = [x for x in c.get("items") or [] if x.get("severity") in ("high", "medium") and x.get("source") != "self-check"][:2]
    if not top:
        return None
    return "Before we start: " + "; and ".join(x["what"] for x in top) + "."


def already_said(items: list[dict], answer: str) -> bool:
    """True when the answer itself already tells these items (5 Nov evening: with the book in short on every India turn, an answer that
    listed the self-check got the same item again as a nudge)."""
    words = set(re.findall(r"[a-z0-9]+", (answer or "").lower()))
    for x in items:
        mine = [w for w in re.findall(r"[a-z0-9]+", str(x.get("what") or "").lower()) if len(w) > 3]
        if mine and sum(1 for w in mine if w in words) >= 0.6 * len(mine):
            return True
    return False


def nudge(market: str, state: Path, thread: str, now: float | None = None, answer: str = "") -> str:
    """Once per conversation, and not again within 3 hours for the same findings, one line at the end of an answer to Madhav naming what
    is not right (high and medium only; the details come when he asks "is anything wrong"). Never when the answer already says it."""
    now = now or time.time()
    top = [x for x in check(market, now).get("items") or [] if x.get("severity") in ("high", "medium") and x.get("source") != "self-check"][:2]
    if not top or already_said(top, answer):
        return ""
    key = "|".join(x["what"] for x in top)
    try:
        d = json.loads(state.read_text())
    except (OSError, ValueError):
        d = {}
    th = {k: v for k, v in (d.get("threads") or {}).items() if now - float(v) < 86400}
    last = d.get("last") or {}
    if thread in th or (last.get("key") == key and now - float(last.get("t", 0)) < 3 * 3600):
        return ""
    th[thread] = now
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps({"threads": th, "last": {"key": key, "t": now}}))
    except OSError:
        return ""
    what = "; and ".join(x["what"] for x in top)
    return f"One thing that isn't right, sir: {what[:1].lower()}{what[1:]}. Ask me what's wrong for the details."
