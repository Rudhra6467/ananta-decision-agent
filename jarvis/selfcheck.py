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
  gates       the India firewall, leak check and integrity check, from their manifests (6 Nov: the firewall had failed unseen for a day)
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


def _plain_detail(detail) -> str:
    """The lost-runs detail in words Madhav reads (6 Nov replay and exam: '1x india_evening.err written during the run' and a job name
    with '(launchd sees only the last step's exit)' reached his answers). File names, paths and code names are dropped; the full detail
    stays in the lost-runs page."""
    det = str(detail or "").split(" (")[0][:120]
    if re.search(r"[_/\\]|\.(err|log|json|jsonl|py|plist|txt)\b|launchd|\bpid\b", det, re.I):
        return ""
    return det


PART_WORDS = {"hands_login": "Hands sign-in", "universe_feed": "the universe feed", "jobs": "the 15-minute jobs",
              "explorer": "the Explorer", "worker": "the worker Mac", "tunnel": "the public address", "hands": "Hands"}


def _runs(now: float) -> list[dict]:
    from jarvis.service import runcheck

    out = []
    r = runcheck.run(now=now)
    for m in (r.get("windows") or {}).get("24h", {}).get("misses") or []:
        raw = str(m.get("detail") or "")
        if m.get("kind") == "down":
            # 7 Nov review: 'hands_login: 64 min' and 'universe_feed: 63 min' lost the whole detail (the part's code name has an
            # underscore), so the line said only 'a part was down'. Name the part in words before the code-word filter.
            key, sep, rest = raw.partition(":")
            if sep and re.fullmatch(r"[a-z0-9_]+", key.strip()):
                raw = PART_WORDS.get(key.strip(), key.strip().replace("_", " ")) + sep + rest
        det = _plain_detail(raw)
        name = str(m.get("name") or "a scheduled job").split(" (")[0]
        if m.get("kind") == "down":
            what = f"a part was down at {_when(m.get('t') or now)}" + (f" ({det})" if det else "")
        else:
            what = f"{name} {KIND_WORDS.get(m.get('kind'), m.get('kind'))} at {_when(m.get('t') or now)}" + (f" ({det})" if det else "")
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


def _book500(db: Path = CRYPTO_DB) -> list[dict]:
    """10 Nov 2026 (Madhav: "Yes to all"): the $500 book's trades and its holdings agree. Every coin's buys less its sells must be what the
    book holds; on 28 Oct 0.008315 ETH left the holdings without a sale and nothing noticed for 13 days. Read-only."""
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        fills = con.execute("SELECT coin, side, qty FROM book500_fills").fetchall()
        row = con.execute("SELECT v FROM book500 WHERE k='state'").fetchone()
        con.close()
    except sqlite3.Error:
        return []
    try:
        held = {c: float(p.get("qty") or 0) for c, p in ((json.loads(row[0]) if row else {}).get("pos") or {}).items()}
    except (ValueError, TypeError, AttributeError):
        return []
    net: dict[str, float] = {}
    for coin, side, qty in fills:
        net[coin] = net.get(coin, 0.0) + (qty if side == "BUY" else -qty)
    out = []
    for coin in sorted(set(net) | set(held)):
        diff = net.get(coin, 0.0) - held.get(coin, 0.0)
        if abs(diff) > 1e-9:
            out.append({"market": "crypto", "severity": "high", "source": "book check",
                        "what": (f"the $500 book's trades and holdings disagree on {coin}: {abs(diff):.6g} {coin} "
                                 + ("was bought and never sold, yet is not held" if diff > 0 else "is held or sold with no buy on record")
                                 + ", so the book's value is wrong until it is put right")})
    return out


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
                    "what": f"the {which} service froze and was restarted automatically at {_when(f.stat().st_mtime)}"})
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


GATES = (("firewall", "the sealed-data firewall"), ("leakcheck", "the leak check"), ("integrity", "the data integrity check"))
INDIA_MANIFESTS = HOME / "ananta_data" / "india" / "manifests"


def _gates(manifests: Path = INDIA_MANIFESTS) -> list[dict]:
    """6 Nov 2026 (the reconstruction audit): the firewall's static scan had failed since the evening of 5 Nov (a new module read the India
    folder without its allowlist line) and nothing in front of the voice said so. The three India gates, from their own manifests."""
    out = []
    for name, words in GATES:
        d = _read_json(manifests / f"{name}.json") if (manifests / f"{name}.json").exists() else None
        if not isinstance(d, dict):
            continue
        failed = [k for k, v in d.items() if isinstance(v, dict) and v.get("ok") is False]
        if failed:
            out.append({"market": "india", "severity": "high" if name == "firewall" else "medium", "source": name,
                        "what": f"{words} fails on {', '.join(failed)} (as of {str(d.get('_at') or '')[:16]}); nothing trades, but the record is not clean until it passes"})
    return out


INDIA_PAPER = HOME / "ananta_data" / "india" / "paper"


def _rx_order(paper: Path = INDIA_PAPER, db: Path = CRYPTO_DB) -> list[dict]:
    """6 Nov 2026 (Madhav's yes to the reconstruction audit, E4): both bugs the audit found were ordering bugs (the India trials scored a night
    after the card; the crypto card made before the day's missed moves were reviewed), so the order is checked every 15 minutes:
    India: the newest card's session has a scored row in both trial files; crypto: the newest card is about the closed day and was made
    at or after 00:30 UTC. A reorder of a launchd chain or the job loop can no longer undo the fix silently."""
    out = []
    try:
        card = _read_json(paper / "reconstruction" / "latest.json") or {}
        day = str(card.get("day") or "")
        if day:
            late = []
            for name, label in (("rx1_trial.json", "RX1"), ("rs_trial.json", "RS")):
                tr = _read_json(paper / name) or {}
                scored_on = max((str(s.get("scored_on") or s.get("day") or "") for s in tr.get("sessions") or []), default="")
                if tr and not tr.get("complete") and tr.get("start", "0") < day and scored_on < day:     # a session's picks are scored on the next session, so the newest scored_on is the card's day
                    late.append(label)
            if late:
                out.append({"market": "india", "severity": "low", "source": "reconstruction order",
                            "what": f"the India card of {day} was built before the {' and '.join(late)} trial{'s' if len(late) > 1 else ''} scored that session "
                                    "(the trials run inside the 08:00 IST paper job, before the card); the trial is a night behind until the next run"})
    except Exception:  # noqa: BLE001
        pass
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        try:
            r = con.execute("SELECT day, t, card FROM rx_cards ORDER BY day DESC LIMIT 1").fetchone()
        finally:
            con.close()
        if r:
            day, t_, card = r[0], int(r[1] or 0), json.loads(r[2] or "{}")
            about = card.get("about_day")
            if about and t_ and (about >= day or t_ % 86400 < 1800):
                out.append({"market": "crypto", "severity": "low", "source": "reconstruction order",
                            "what": f"the crypto card of {day} was made at {time.strftime('%H:%M', time.gmtime(t_))} UTC about {about}; "
                                    "it should describe the closed day and come after the 00:30 UTC missed-move review"})
    except (sqlite3.Error, ValueError, TypeError):
        pass
    return out


def _read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _credit(post=None) -> list[dict]:
    """5 Nov 2026, 14:53 Toronto: the Anthropic credit ran out and nothing said so; India's answers fell back to its rules and crypto's to
    Gemini. A one-token call with the services' own key says whether Claude still answers (an empty balance is refused at once, free)."""
    return credit_probe(os.getenv("ANTHROPIC_API_KEY", ""), post) + model_fallbacks()


def model_fallbacks(now: float | None = None, hours: float = 6.0) -> list[dict]:
    """8 Nov 2026: a request Claude refused (a cache setting it would not take) made every India answer fall back to the read model for a
    morning, while the credit was fine and nothing said so. Any real India answer in the last hours that fell back is a finding."""
    import glob
    now = now or time.time()
    from jarvis.india.selfparts import ask_dir   # the India data path lives in the India app (the firewall allowlist), 9 Nov
    d = ask_dir()
    hits, why = 0, ""
    for f in glob.glob(str(d / "*.jsonl")):
        if f.endswith("threads.jsonl") or os.path.getmtime(f) < now - hours * 3600:
            continue
        try:
            for line in open(f):
                if 'read model only' not in line:
                    continue
                r = json.loads(line)
                note = str(r.get("note") or "")             # the note, not the answer: the self-check's own words quoted in an answer are not a fallback
                if r.get("role") == "assistant" and "read model only" in note and float(r.get("t") or 0) >= now - hours * 3600:
                    hits += 1
                    why = str(r.get("note") or "").split("read model only:", 1)[-1].strip(" :")[:80]
        except (OSError, ValueError):
            continue
    if not hits:
        return []
    return [{"market": "india", "severity": "high", "source": "Claude credit",
             "what": f"{hits} India answer{'s' if hits != 1 else ''} in the last {int(hours)} hours came from the read model only, not from Claude",
             "detail": why}]


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
                          "it is topped up in the Anthropic Console under Plans & Billing")}]
    return []


def _agree(now: float) -> list[dict]:
    """6 Nov 2026 (Madhav: Ananta scans itself the way it scans the market): do the parts agree with each other (jarvis/selfscan.py)."""
    from jarvis import selfscan

    return selfscan.scan(now=now)


TOLD = Path(os.getenv("ANANTA_SELFCHECK_TOLD", str(HOME / "ananta_data" / "selfcheck_told.json")))


def tell(items: list[dict], push, now: float, state: Path = TOLD, every: float = 86400) -> list[str]:
    """6 Nov 2026 (Madhav: "it should also be able to tell us ... there is something issue going on, you have to look at it"): a HIGH item
    reaches his phone once a day (web push through the crypto service); the rest wait for the morning review or his next question."""
    try:
        told = json.loads(state.read_text())
    except (OSError, ValueError):
        told = {}
    sent = []
    for x in items:
        if x.get("severity") != "high":
            continue
        key = re.sub(r"\d", "", str(x.get("what") or ""))[:120]
        if now - float(told.get(key) or 0) < every:
            continue
        try:
            push("Ananta: something is not right", f"{x['what']} (from the {x.get('source')}). Ask me what's wrong for the rest.")
            told[key] = now
            sent.append(key)
        except Exception:  # noqa: BLE001  a phone that cannot be reached never stops the check
            pass
    if sent:
        try:
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text(json.dumps({k: v for k, v in told.items() if now - float(v) < 7 * every}))
        except OSError:
            pass
    return sent


def refresh(now: float | None = None, opener=None, write: bool = True, post=None, push=None) -> dict:
    now = now or time.time()
    items: list[dict] = []
    for name, fn in (("runs", lambda: _runs(now)), ("services", lambda: _services(opener)), ("answers", _answers),
                     ("leftovers", _leftovers), ("watchdog", lambda: _restarts(now)), ("credit", lambda: _credit(post)), ("mac", _mac), ("gates", _gates), ("rx_order", _rx_order),
                     ("agree", lambda: _agree(now)), ("book500", _book500)):
        try:
            items += fn()
        except Exception as exc:  # noqa: BLE001  one check failing is itself a finding, never a crash
            items.append({"market": "both", "severity": "low", "source": name, "what": f"the {name} check could not run ({type(exc).__name__})"})
    try:                                                   # 7 Nov: a sleeping Mac is one line, planned or not, never nine faults
        items = fold_sleep(items, asleep_windows(now), downtime_notes(now), now)
    except Exception:  # noqa: BLE001
        pass
    items.sort(key=lambda x: SEV.get(x.get("severity"), 3))
    out = {"at": int(now), "at_words": _when(now), "items": items}
    if write:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, indent=1))
        tmp.replace(FILE)
    if push is not None:
        out["told"] = tell(items, push, now)
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
          ("mac", "the Mac has memory and CPU to spare"), ("gates", "the India firewall, leak check and integrity check pass"),
          ("rx_order", "the reconstruction cards come after the trials (India) and the missed-move review (crypto)"),
          ("agree", "the parts agree with each other: the right day, matching counts, no number stuck at zero, nothing waiting over a week"),
          ("book500", "the $500 book's trades and its holdings agree"))


SOURCE_CHECK = {"lost-runs check": "runs", "services": "services", "nightly replay": "answers", "fact map": "answers", "approvals": "leftovers",
                "watchdog": "watchdog", "Claude credit": "credit", "Mac load": "mac", "firewall": "gates", "leakcheck": "gates", "integrity": "gates",
                "reconstruction order": "rx_order", "self-scan": "agree", "Mac asleep": "runs", "book check": "book500"}


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
    what = spoken("; and ".join(x["what"] for x in top))
    return f"One thing that isn't right, sir: {what[:1].lower()}{what[1:]}. Ask me what's wrong for the details."


def spoken(s: str) -> str:
    """9 Nov 2026 (the outsider round): the self-check's items are written about Madhav; said to Madhav they are said to "you", and the
    parts are named in words ("Brain:" was read out as a label)."""
    s = re.sub(r"\bMadhav's\b", "your", s)
    s = re.sub(r"\b(?:for|to|from|by) Madhav\b", lambda m: m.group(0).split()[0] + " you", s)
    s = re.sub(r"\bMadhav (said|asked|planned|has|is)\b", lambda m: "you " + {"has": "have", "is": "are"}.get(m.group(1), m.group(1)), s)
    s = re.sub(r"\bMadhav\b", "you", s)
    s = re.sub(r"\bBrain:\s*", "the crypto brain: ", s)
    return s


# ------------------------------------------------------------------------------------------------- the Mac asleep, and planned downtime
# 7 Nov 2026 (Madhav's yes): the laptop slept from 12:10 to 15:10 and the self-check listed nine parts "down" or "did not run"; Ananta
# told him they needed a look. The Mac's own sleep log says when it slept; those items fold into one line, and a note Madhav gives
# ("I'm turning the laptop off for an hour") marks the window as planned.

DOWNTIME = Path(os.getenv("ANANTA_DOWNTIME", str(HOME / "ananta_data" / "downtime.json")))
_PM_LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) [-+]\d{4} (Sleep|Wake|DarkWake)\s{2,}")   # not "Wake Requests" / "WakeDetails"
_AT = re.compile(r"\bat (\d{1,2} [A-Z][a-z]{2} \d\d:\d\d) Toronto")


def pm_log() -> str:
    """The Mac's power log (read-only); empty when not on a Mac or when it cannot be read."""
    import subprocess

    try:
        return subprocess.run(["pmset", "-g", "log"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def asleep_windows(now: float, log_text: str | None = None, days: float = 1.5) -> list[tuple[float, float]]:
    """[(slept_at, woke_at)] from the Mac's sleep log, last 36 hours; a DarkWake (maintenance) does not end a sleep; gaps under 5 minutes merge."""
    text = pm_log() if log_text is None else log_text
    since = now - days * 86400
    wins: list[list[float]] = []
    open_at = None
    for line in text.splitlines():
        m = _PM_LINE.match(line.strip())
        if not m:
            continue
        try:
            t = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        if t < since:
            continue
        if m.group(2) == "Sleep" and open_at is None:
            open_at = t
        elif m.group(2) == "Wake" and open_at is not None:
            if wins and open_at - wins[-1][1] < 300:
                wins[-1][1] = t
            else:
                wins.append([open_at, t])
            open_at = None
    if open_at is not None:                       # asleep right now (the check runs only awake, so this is a log tail without its Wake)
        wins.append([open_at, now])
    return [(a, b) for a, b in wins if b - a >= 120]


def downtime_notes(now: float) -> list[dict]:
    try:
        rows = json.loads(DOWNTIME.read_text())
    except (OSError, ValueError):
        return []
    return [r for r in rows if isinstance(r, dict) and float(r.get("to") or 0) > now - 1.5 * 86400]


def note_downtime(hours: float, why: str, by: str, now: float | None = None) -> dict:
    """Madhav's word that the Mac will be off or asleep: the window is written so the self-check calls it planned, not a fault."""
    now = now or time.time()
    row = {"from": int(now - 300), "to": int(now + hours * 3600), "why": why[:160], "by": by, "noted_at": int(now)}
    rows = [r for r in downtime_notes(now) if float(r.get("to") or 0) > now - 1.5 * 86400]
    rows.append(row)
    DOWNTIME.parent.mkdir(parents=True, exist_ok=True)
    DOWNTIME.write_text(json.dumps(rows, indent=1))
    return row


def _item_time(x: dict, now: float) -> float | None:
    m = _AT.search(str(x.get("what") or ""))
    if not m:
        return None
    try:
        lt = time.localtime(now)
        t = time.mktime(time.strptime(f"{lt.tm_year} {m.group(1)}", "%Y %d %b %H:%M"))
        return t - 365 * 86400 if t > now + 86400 else t          # a December item read in January
    except ValueError:
        return None


def fold_sleep(items: list[dict], windows: list[tuple[float, float]], notes: list[dict], now: float) -> list[dict]:
    """Items from the lost-runs check and the watchdog whose time falls inside a sleep window (15 minutes either side) become one line per window."""
    if not windows:
        return items
    out, folded = [], {i: [] for i in range(len(windows))}
    for x in items:
        t = _item_time(x, now)
        hit = None
        if t is not None and x.get("source") in ("lost-runs check", "watchdog", "self-scan"):
            for i, (a, b) in enumerate(windows):
                if a - 900 <= t <= b + 900:
                    hit = i
                    break
        if hit is None:
            out.append(x)
        else:
            folded[hit].append(x)
    for i, (a, b) in enumerate(windows):
        xs = folded[i]
        if not xs:
            continue
        fits = [n for n in notes if float(n.get("from") or 0) - 900 <= a <= float(n.get("to") or 0) + 1800]
        planned = max(fits, key=lambda n: float(n.get("to") or 0)) if fits else None
        ran_long = bool(planned) and b > float(planned.get("to") or 0) + 1800
        names = set()
        for x in xs:
            w = str(x.get("what") or "")
            m = re.search(r"\(([^():]+):", w) if w.startswith("a part was down") else None
            names.add(m.group(1).strip() if m else re.sub(r"\s+(did not run|ran but did too little|ran with an error|was down).*$", "", w).split(":")[0].strip())
        names = sorted(n for n in names if n)
        what = (f"the Mac was asleep or off from {_when(a)} to {time.strftime('%H:%M', time.localtime(b))}, so {len(xs)} part{'s' if len(xs) != 1 else ''} missed runs or were down"
                + (f" ({', '.join(names[:5])}{', ...' if len(names) > 5 else ''})" if names else "")
                + ((f"; planned for about {max(1, round((float(planned['to']) - float(planned['from']) - 300) / 3600))} h ({planned.get('by', 'Madhav')}'s word)"
                    + (f", it lasted {int((b - a) // 3600)} h {int((b - a) % 3600 // 60)} min" if ran_long else "")) if planned else "; nobody said this was planned"))
        out.append({"market": "both", "severity": "low" if planned and not ran_long else "medium", "source": "Mac asleep", "what": what, "planned": bool(planned)})
    out.sort(key=lambda x: SEV.get(x.get("severity"), 3))
    return out


DOWNTIME_OBJ = re.compile(r"\b(laptop|mac(?:book)?(?: air| pro)?|computer|machine|lid|pc)\b", re.I)
DOWNTIME_VERB = re.compile(r"\b(?:turn(?:ing)?|switch(?:ing)?|shut(?:ting)?|power(?:ing)?)\b[^.?!]{0,20}\b(?:off|down)\b|\b(?:clos(?:e|ing)|sleep(?:ing)?|asleep|restart(?:ing)?|reboot(?:ing)?)\b"
                           r"|\bput(?:ting)?\b[^.?!]{0,20}\bto sleep\b", re.I)
_DUR = re.compile(r"\bfor\s+(?:about\s+|around\s+|roughly\s+)?(an?|one|two|three|four|five|six|half an?|a couple of|\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?)\b", re.I)
_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "half a": 0.5, "half an": 0.5, "a couple of": 2}


def downtime_words(text: str) -> float | None:
    """7 Nov 2026 (Madhav's yes): "I'm turning the laptop off for an hour" -> the hours (1 when no length is given); None when it is not that."""
    t = text or ""
    if not (DOWNTIME_OBJ.search(t) and DOWNTIME_VERB.search(t)) or re.search(r"\b(what if|what happens|do i need|why)\b", t, re.I):
        return None
    m = _DUR.search(t)
    if not m:
        return 1.0
    n = _NUM.get(m.group(1).lower(), None)
    if n is None:
        try:
            n = float(m.group(1))
        except ValueError:
            n = 1.0
    return round(n / 60, 2) if m.group(2).lower().startswith(("min", "m")) and not m.group(2).lower().startswith("h") else float(n)


def downtime_answer(hours: float, market: str, asked: bool = False) -> str:
    h = f"{int(hours)} hour{'s' if hours != 1 else ''}" if float(hours).is_integer() else f"{int(round(hours * 60))} minutes"
    return ((f"Yes, sir, go ahead. The next {h} counts as planned downtime, not a fault, and the self-check will say so. " if asked else
             f"Noted, sir: the next {h} counts as planned downtime, not a fault, and the self-check will say so. ")
            + ("While the Mac sleeps, the crypto paper books stop watching prices and the 15-minute checks pause; a stop hit in that time is handled late. "
               if market == "crypto" else
               "While the Mac sleeps, the India jobs due in that window are skipped and run again at their next time; the paper books lose nothing, since nothing trades off-session. ")
            + "Everything restarts by itself when you log back in.")
