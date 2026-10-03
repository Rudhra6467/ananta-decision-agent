"""Teachers: turn the trading-education videos Madhav learned from into a rulebook Ananta can test.

    python -m src.research.teachers extract --pick ~/ananta_runs/yt/pick.tsv --subs ~/ananta_runs/yt/subs --out ~/ananta_runs/yt/rules
    python -m src.research.teachers merge --rules ~/ananta_runs/yt/rules --channel TWT --out ~/ananta_runs/yt/rulebook_TWT.md

1. captions come from yt-dlp (English, manual or automatic) into --subs as <id>.en.vtt (fetched separately)
2. extract: one small AI call per video (Claude Haiku) -> the video's setups, entry / stop / exit rules, market-regime,
   selection and risk rules, any performance claims, and whether each setup can be coded precisely
3. merge: one call per channel (Claude Sonnet) -> a single rulebook, every rule tagged with the videos it came from
Transcripts stay on the laptop (they are the channels' work); only paraphrased rules are kept in the repo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5-5"
CHANNELS = {"TWT": "Trade With Trend (Indian markets, positional and swing trading)", "RAYNER": "TradingwithRayner (Rayner Teo, price action and systematic strategies)"}


def vtt_text(path: Path) -> str:
    """Plain text from a YouTube .vtt: no timestamps or tags, rolling duplicate lines removed."""
    out: list[str] = []
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")) or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line).replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<").strip()
        if line and (not out or line != out[-1]):
            out.append(line)
    # automatic captions repeat each line once more as the next cue starts
    dedup: list[str] = []
    for line in out:
        if dedup and (line == dedup[-1] or dedup[-1].endswith(line)):
            continue
        dedup.append(line)
    return " ".join(dedup)


def claude(model: str, system: str, user: str, max_tokens: int = 4000, tries: int = 8) -> tuple[str, dict]:
    body = {"model": model, "max_tokens": max_tokens, "temperature": 0, "system": system, "messages": [{"role": "user", "content": user}]}
    for k in range(tries):
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                              "anthropic-version": "2023-06-01"})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=600).read())
            return "".join(c.get("text", "") for c in r.get("content", [])), r.get("usage", {})
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and k < tries - 1:
                wait = float(e.headers.get("retry-after") or 0) or min(60, 5 * 2 ** k)
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def json_from(text: str) -> dict:
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


EXTRACT_SYSTEM = ("You turn trading-education video transcripts into precise rule notes for a trading research program. "
                  "Paraphrase in plain English; never copy more than 10 consecutive words from the transcript. "
                  "Only include what this video actually teaches. Answer only JSON.")

EXTRACT_TASK = """Channel: {channel}
Video: "{title}" ({minutes} min)
Transcript (automatic captions; expect wrong words):
{text}

Return this JSON (empty lists are fine):
{{"topic": "one line",
 "market_and_timeframe": "e.g. Indian stocks, daily and weekly charts; or general",
 "concepts": [{{"name": "...", "meaning": "plain one-liner"}}],
 "setups": [{{"name": "...",
   "context": ["what must be true first: trend, stage, market breadth, relative strength, the base, sector..."],
   "entry": "the exact trigger",
   "stop": "stop-loss rule",
   "exits": "targets, trailing, time or sell rules",
   "sizing": "position size, pyramiding or exposure rule if any",
   "avoid": ["when not to take it"],
   "parameters": {{"name": "value with units"}},
   "codable": "YES (every part precise) | PARTLY | NO (needs judgment)",
   "how_to_code": "one line on how a program would detect it"}}],
 "market_regime_rules": ["when to be aggressive or defensive, breadth, index vs moving averages, follow-through day..."],
 "selection_rules": ["how to choose what to trade: relative strength, sector, leaders, liquidity, fundamentals..."],
 "risk_rules": ["risk per trade, position sizing, pyramiding, exposure, drawdown rules"],
 "sell_rules": ["when to take profit or get out, separate from the stop"],
 "claims": ["performance claims with their numbers, as stated"],
 "examples": ["instrument, date and what happened, if given"],
 "quality": "HIGH | MEDIUM | LOW (how much concrete, rule-like teaching the video has)"}}"""


def extract_one(meta: dict, subs: Path, out: Path) -> dict:
    dest = out / f"{meta['id']}.json"
    if dest.exists():
        return {"id": meta["id"], "status": "cached"}
    vtts = sorted(subs.glob(f"{meta['id']}.en*.vtt"))
    if not vtts:
        return {"id": meta["id"], "status": "no_captions"}
    text = vtt_text(vtts[0])
    words = text.split()
    if len(words) < 150:
        return {"id": meta["id"], "status": "too_short"}
    text = " ".join(words[:24000])
    raw, usage = claude(HAIKU, EXTRACT_SYSTEM, EXTRACT_TASK.format(channel=CHANNELS[meta["channel"]], title=meta["title"],
                                                                    minutes=meta["minutes"], text=text), max_tokens=6000)
    try:
        rules = json_from(raw)
    except Exception:  # noqa: BLE001
        rules = {"unreadable": raw[:2000]}
    rec = {**meta, "words": len(words), "usage": usage, "rules": rules}
    dest.write_text(json.dumps(rec, indent=1))
    return {"id": meta["id"], "status": "ok", "in": usage.get("input_tokens"), "out": usage.get("output_tokens")}


def extract(pick: str, subs: str, out: str, workers: int = 3) -> dict:
    o = Path(os.path.expanduser(out))
    o.mkdir(parents=True, exist_ok=True)
    metas = []
    for line in Path(os.path.expanduser(pick)).read_text().splitlines():
        vid, ch, title, dur, views = (line.split("\t") + ["", "", "", "", ""])[:5]
        metas.append({"id": vid, "channel": ch, "title": title, "minutes": int(float(dur or 0) // 60), "views": views})
    sp = Path(os.path.expanduser(subs))
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda m: _safe(extract_one, m, sp, o), metas))
    tally: dict[str, int] = {}
    for r in res:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    tin = sum(r.get("in") or 0 for r in res)
    tout = sum(r.get("out") or 0 for r in res)
    return {"videos": len(res), "status": tally, "input_tokens": tin, "output_tokens": tout,
            "cost_usd_est": round(tin / 1e6 * 1.0 + tout / 1e6 * 5.0, 2), "failed": [r for r in res if r["status"] == "error"][:10]}


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as exc:  # noqa: BLE001
        return {"id": a[0]["id"], "status": "error", "error": str(exc)[:200]}


MERGE_SYSTEM = ("You are writing the rulebook of a trading teacher from notes extracted from many of his videos, for a trader who "
                "learned from him and for the research program that will test the rules. Paraphrase; no long quotes. Be concrete: "
                "numbers, conditions and order of operations. Keep every rule tied to the video ids it came from, like [id1, id2]. "
                "Do not invent rules that are not in the notes. Where videos disagree or the teaching changed over time, say so.")

MERGE_TASK = """Teacher: {channel}
Notes from {n} videos (newest first), one JSON per video:
{notes}

Write the rulebook in Markdown with these sections:
1. How he thinks (6-10 bullets: the core philosophy and the order he works in)
2. Market regime (when to be aggressive, cautious or out: breadth, index structure, moving averages, follow-through day, VIX...)
3. What to trade (top-down: sectors, leaders, relative strength, fundamentals, liquidity)
4. Setups (one subsection each: what it is; context that must be true; entry; stop; exits and selling; sizing; when to avoid;
   codable YES/PARTLY/NO with the parameters a program would need) - merge duplicates across videos
5. Risk, position sizing, pyramiding and exposure
6. Selling and exits (beyond the stop)
7. Mindset and process (short)
8. Claims made (numbers as stated; flag that they are his claims, not verified)
9. For a testing program: the 8-12 rules most worth testing first, each as a precise, codable definition, and which parts need human judgment
Then a final line: how much of the teaching is codable (rough share)."""


def merge(rules: str, channel: str, out: str, max_notes_chars: int = 420000) -> dict:
    recs = []
    order = {}
    for i, line in enumerate(Path(os.path.expanduser("~/ananta_runs/yt/pick.tsv")).read_text().splitlines()):
        order[line.split("\t")[0]] = i
    for p in Path(os.path.expanduser(rules)).glob("*.json"):
        r = json.loads(p.read_text())
        if r.get("channel") != channel:
            continue
        x = r.get("rules") or {}
        for k in ("examples", "concepts"):                 # keep the merge input inside one call
            x.pop(k, None)
        for st in x.get("setups") or []:
            if isinstance(st, dict):
                st.pop("how_to_code", None)
        recs.append((order.get(r["id"], 9999), {"id": r["id"], "title": r["title"], "minutes": r["minutes"], **x}))
    recs.sort(key=lambda t: t[0])
    notes = "\n".join(json.dumps(r, separators=(",", ":")) for _, r in recs)[:max_notes_chars]
    text, usage = claude(SONNET, MERGE_SYSTEM, MERGE_TASK.format(channel=CHANNELS[channel], n=len(recs), notes=notes), max_tokens=20000)
    Path(os.path.expanduser(out)).write_text(text)
    return {"channel": channel, "videos": len(recs), "usage": usage, "out": out}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--pick", required=True)
    e.add_argument("--subs", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--workers", type=int, default=3)
    m = sub.add_parser("merge")
    m.add_argument("--rules", required=True)
    m.add_argument("--channel", required=True, choices=list(CHANNELS))
    m.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "extract":
        print(json.dumps(extract(a.pick, a.subs, a.out, a.workers), indent=1))
    else:
        print(json.dumps(merge(a.rules, a.channel, a.out), indent=1))


if __name__ == "__main__":
    main()
