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
"""
from __future__ import annotations

import json
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
                     ("leftovers", _leftovers), ("watchdog", lambda: _restarts(now)), ("credit", lambda: _credit(post))):
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
    items = [x for x in c.get("items") or [] if market is None or x.get("market") in (market, "both")]
    if now - (c.get("at") or 0) > STALE_S:
        items.insert(0, {"market": "both", "severity": "medium", "source": "self-check",
                         "what": f"the self-check last ran at {c.get('at_words')}, so this may be out of date"})
    return {"at": c.get("at"), "at_words": c.get("at_words"), "items": items}


def words(c: dict) -> list[str]:
    items = c.get("items") or []
    if not items:
        return [f"Nothing is wrong right now (checked {c.get('at_words')}): every scheduled part ran in the last 24 hours, the services "
                "answer, last night's replay passed and no test card is waiting."]
    return [f"{x['what']} ({x['severity']}, from the {x['source']})" for x in items]


def headline(c: dict) -> str | None:
    """One sentence for the start of a conversation: only high or medium items, at most two."""
    top = [x for x in c.get("items") or [] if x.get("severity") in ("high", "medium") and x.get("source") != "self-check"][:2]
    if not top:
        return None
    return "Before we start: " + "; and ".join(x["what"] for x in top) + "."


def nudge(market: str, state: Path, thread: str, now: float | None = None) -> str:
    """Once per conversation, and not again within 3 hours for the same findings, one line at the end of an answer to Madhav naming what
    is not right (high and medium only; the details come when he asks "is anything wrong")."""
    now = now or time.time()
    top = [x for x in check(market, now).get("items") or [] if x.get("severity") in ("high", "medium") and x.get("source") != "self-check"][:2]
    if not top:
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
