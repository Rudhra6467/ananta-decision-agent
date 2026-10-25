"""Crypto news shadow (Madhav, 25 Oct 2026: "We can add both, if they are helping Ananta in either crypto and Indian infrastructure").

A FORWARD, BLIND, RECORD-ONLY log, the way OD-SHADOW-LANE works: each night the headlines the daily news check already stored (news_log, one row
per coin and day, jarvis/service/news_watch.py) are read by a financial-news model from Hugging Face (ProsusAI/finbert, run on the Mac, zero-shot)
and appended to ~/ananta_lake/agent/hf_shadow/news_ratings.jsonl. Rule B holds: no book, brain, Ask, gate or screen reads this file (a test checks
that nothing under jarvis/ or src/ names it); it is scored only after the evidence window ends (14 Dec 2026, due-list PW-HF-NEWS), against the
STUDY_NEWS_CREDIT outcome (fwd20 minus the 10 coins' median). The database is opened read-only. Paper only; nothing trades on it.

  ~/ananta_venvs/hf/bin/python scripts/hf_news_shadow.py          rate every news_log row not yet in the log (append-only)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path

MODEL = "ProsusAI/finbert"
REVISION = "0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031"
DB = Path(os.getenv("JARVIS_AGENT_DIR", os.path.expanduser("~/code/ananta-decision-agent"))) / "jarvis.sqlite"
LOG = Path(os.path.expanduser("~/ananta_lake/agent/hf_shadow/news_ratings.jsonl"))


def headlines(js: str | None) -> list[str]:
    """Every 'headline' string anywhere in the news check's stored answer (damage, supply, catalysts ...), in order, without repeats."""
    out: list[str] = []

    def walk(x):
        if isinstance(x, dict):
            h = x.get("headline")
            if isinstance(h, str) and h.strip() and h.strip() not in out:
                out.append(h.strip())
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    try:
        walk(json.loads(js or "{}"))
    except ValueError:
        pass
    return out


def done_keys(log: Path = LOG) -> set[tuple[str, str]]:
    if not log.exists():
        return set()
    keys = set()
    for line in log.read_text().splitlines():
        try:
            r = json.loads(line)
            keys.add((r["day"], r["coin"]))
        except (ValueError, KeyError):
            continue
    return keys


def pending(db: Path = DB, log: Path = LOG) -> list[dict]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT day, coin, verdict, json FROM news_log ORDER BY day, coin").fetchall()
    finally:
        con.close()
    have = done_keys(log)
    return [{"day": d, "coin": c, "verdict": v, "headlines": headlines(js)} for d, c, v, js in rows if (d, c) not in have]


def rate(rows: list[dict], probs=None) -> list[dict]:
    """probs(texts) -> [[p_pos, p_neg, p_neu], ...]; the model is loaded only when there is something to rate."""
    texts = [h for r in rows for h in r["headlines"]]
    if texts and probs is None:
        probs = _finbert()
    P = probs(texts) if texts else []
    out, i = [], 0
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    for r in rows:
        hs = []
        for h in r["headlines"]:
            p = [float(x) for x in P[i]]
            i += 1
            hs.append({"headline": h[:240], "p_pos": round(p[0], 4), "p_neg": round(p[1], 4), "label": ("positive", "negative", "neutral")[p.index(max(p))]})
        tone = round(sum(x["p_pos"] - x["p_neg"] for x in hs) / len(hs), 4) if hs else None
        out.append({"day": r["day"], "coin": r["coin"], "check_verdict": r["verdict"], "headlines": hs, "tone": tone, "rated_at": now, "model": f"{MODEL}@{REVISION}",
                    "rule": "blind record: read by nothing until the window ends (PW-HF-NEWS, after 14 Dec 2026)"})
    return out


def append(recs: list[dict], log: Path = LOG) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    have = done_keys(log)
    n = 0
    with log.open("a") as fh:                       # append-only: a (day, coin) already in the log is never written again
        for r in recs:
            if (r["day"], r["coin"]) in have:
                continue
            fh.write(json.dumps(r) + "\n")
            have.add((r["day"], r["coin"]))
            n += 1
    return n


def _finbert():
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    m = AutoModelForSequenceClassification.from_pretrained(MODEL, revision=REVISION).to(dev).eval()
    lab = {v.lower(): int(k) for k, v in m.config.id2label.items()}
    ix = [lab["positive"], lab["negative"], lab["neutral"]]

    def probs(texts: list[str]):
        res = []
        for i in range(0, len(texts), 64):
            enc = tok(texts[i:i + 64], truncation=True, max_length=128, padding=True, return_tensors="pt").to(dev)
            with torch.no_grad():
                p = torch.softmax(m(**enc).logits.float(), dim=-1).cpu().numpy()
            res.extend(p[:, ix].tolist())
        return res
    return probs


RUN_LOG = Path.home() / "ananta_runs" / "shadow_hfnews" / "run.log"   # one dated line a run, for the lost-runs checker (counts only)


def _run_line(n: int, status: str) -> None:
    import datetime as _dt
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LOG.open("a") as fh:
        fh.write(f"[{_dt.datetime.now(_dt.timezone.utc):%Y-%m-%d %H:%M}] daily rows={n} status={status}\n")


if __name__ == "__main__":
    try:
        rows = pending()
        n = append(rate(rows)) if rows else 0
    except Exception as e:  # noqa: BLE001  recorded for the checker, then raised so launchd shows the exit
        _run_line(0, f"error {type(e).__name__}")
        raise
    _run_line(len(rows), "ok")             # the coin-days it found to rate: 0 means the news check stored nothing new (worth a look)
    print(json.dumps({"pending": len(rows), "appended": n, "log": str(LOG)}))
    sys.exit(0)
