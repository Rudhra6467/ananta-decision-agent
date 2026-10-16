"""The Trading Knowledge Library (Canada plan section 11; Madhav, Oct 16: "Trade With Trend is the most important one").

Every public Trade With Trend video with captions -> one structured note per video (Claude Sonnet 5.5, Message Batches API,
half price) -> one concept file per topic plus a register of testable hypotheses (Claude Opus 5.5, batch).

    python -m src.research.library prepare            # build the per-video requests from ~/ananta_runs/channels/tx
    python -m src.research.library submit             # send them as one batch (prints the batch id)
    python -m src.research.library collect            # wait for the batch, save one note per video
    python -m src.research.library merge-submit       # one request per topic from the saved notes
    python -m src.research.library merge-collect      # write docs/library/trade_with_trend/*.md
    python -m src.research.library status             # where it stands and what it cost

Rules (the research rules and the crypto lock):
 - Transcripts are the channel's work: they stay on the laptop (~/ananta_runs). Only paraphrased notes reach the repo.
 - Everything here is external teaching = a hypothesis to test, never proof and never an Ananta rule. Nothing in the agent,
   the brain, the books or the gate reads docs/library/ (tests/test_library.py checks that).
 - Market-specific (Indian stocks and indices); each item says whether the idea could transfer to Canada or the US.
Needs ANTHROPIC_API_KEY (run it with the service's environment: ~/ananta_runs/svc_env_run.py, or export it).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

SONNET = "claude-sonnet-5-5"
OPUS = "claude-opus-5-5"
TX = Path("~/ananta_runs/channels/tx").expanduser()
VIDEOS = Path("~/ananta_runs/channels/TradeWithTrend_videos.json").expanduser()
WORK = Path("~/ananta_runs/library/twt").expanduser()
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "library" / "trade_with_trend"
API = "https://api.anthropic.com/v1/messages/batches"
# batch prices, US$ per million tokens (half the standard price; platform.claude.com pricing, Oct 16 2026)
PRICE = {SONNET: (1.0, 5.0), OPUS: (2.0, 10.0)}

TOPICS = {
    "PROCESS": "how he works: philosophy, order of work, routine, checklists, mindset",
    "REGIME": "market regime: when to be aggressive, cautious or out (index vs averages, follow-through, distribution)",
    "BREADTH": "market breadth: advance/decline, % of stocks above averages, new highs/lows, participation",
    "STAGE": "stage analysis (Weinstein stages 1-4, the 30/50-week average)",
    "RS": "relative strength: RS line, leaders vs laggards, RS vs index and sector",
    "SECTOR": "sectors and groups: rotation, sector leadership, sister stocks, sector vs index",
    "INTERMARKET": "macro and other markets: yields, crude, the dollar, global indices, FII flows, rates, policy",
    "BASES": "bases and patterns: VCP, Wyckoff, cup and handle, flags, consolidation, contraction",
    "BREAKOUT": "breakouts: triggers, volume confirmation, false-breakout filters, retests",
    "PULLBACK": "pullbacks and moving averages: buying dips to averages, which averages, extension",
    "VOLUME": "volume and market profile: volume patterns, value area, POC, VWAP, volume profile",
    "FUNDAMENTALS": "fundamentals: earnings, growth, valuation, balance sheet, quality, how he combines them with charts",
    "DERIVATIVES": "options, futures and volatility: calls/puts, writing, spreads, straddles, open interest, PCR, VIX, hedging",
    "SHORT": "short selling and bear markets: stage 4, shorting rules, defence",
    "RISK": "risk, position sizing, pyramiding, progressive exposure, drawdown, capital",
    "EXIT": "selling and exits beyond the stop: targets, trailing, time, sell rules",
}
FILES = [  # concept file -> topics it gathers
    ("01_how_he_works", ["PROCESS"]), ("02_regime_and_breadth", ["REGIME", "BREADTH"]), ("03_stage_and_relative_strength", ["STAGE", "RS"]),
    ("04_sectors_and_intermarket", ["SECTOR", "INTERMARKET"]), ("05_bases_and_breakouts", ["BASES", "BREAKOUT"]),
    ("06_pullbacks_and_averages", ["PULLBACK"]), ("07_volume_and_market_profile", ["VOLUME"]), ("08_fundamentals", ["FUNDAMENTALS"]),
    ("09_derivatives_and_volatility", ["DERIVATIVES"]), ("10_short_selling_and_bear_markets", ["SHORT"]),
    ("11_risk_sizing_exposure", ["RISK"]), ("12_exits_and_selling", ["EXIT"]),
]

EXTRACT_SYSTEM = (
    "You build a trading knowledge library from the video transcripts of one teacher, for a research program that will test "
    "his ideas on Indian, Canadian and US markets. Paraphrase in plain English; never copy more than 10 consecutive words. "
    "Record only what this video actually says; automatic captions mishear words, so keep a term only when the context makes "
    "it clear. A teacher's idea is a hypothesis, never a fact: write it as what he teaches, not as truth. Answer only JSON.")

EXTRACT_TASK = """Teacher: Raunak A, Trade With Trend (Indian stocks and indices; positional and swing trading)
Video: "{title}" · {length} · published about {age} (before October 2026)
Description (first lines): {desc}
Transcript (automatic captions):
{text}

Return ONE JSON object:
{{"summary": "2-3 sentences: what this video teaches or says",
 "kind": "LESSON | MARKET_REVIEW | CASE_STUDY | QNA | OTHER",
 "market": "e.g. Indian stocks, Nifty and Bank Nifty, daily and weekly charts",
 "items": [
   {{"topic": "one of {topics}",
     "kind": "CONCEPT | RULE | SETUP | OBSERVATION | MARKET_CALL | CLAIM",
     "direction": "LONG | SHORT | BOTH | NA",
     "text": "the idea, precise and complete (conditions, order, numbers with units)",
     "parameters": {{"name": "value with units"}},
     "codable": "YES | PARTLY | NO (needs judgment)",
     "testable": "if it can be tested: the hypothesis as one precise statement a program could check, else empty",
     "data_needed": "what data a test would need (daily prices, volume, index membership, earnings, option chains...)",
     "transfer": "ANY_MARKET | INDIA_ONLY | NEEDS_ADAPTING (one short reason)",
     "clarity": "HIGH (he states it plainly) | MEDIUM | LOW (implied, or the captions are unclear)"}}
 ],
 "market_calls": [{{"what": "what he said about the market or a sector then, and on what basis", "horizon": "his time frame if given"}}],
 "quality": "HIGH | MEDIUM | LOW (how much concrete, reusable teaching the video has)"}}

Topics: {topic_help}
Up to 25 items; merge repeats; skip greetings, promotions and course sales. A MARKET_REVIEW's dated views go in market_calls."""

MERGE_SYSTEM = (
    "You write one chapter of a trading knowledge library from structured notes taken on many videos of one teacher "
    "(Raunak A, Trade With Trend, India). The reader is the trader who learned from him and the research program that will test "
    "the ideas. Paraphrase; no quotes over 10 words. Be concrete: conditions, order of operations, numbers with units. Tie every "
    "point to the video ids it came from, like [id1, id2]. Never invent: if the notes are thin on something, say so plainly. "
    "Everything is the teacher's claim or method, a hypothesis to test, never established fact. Where videos disagree or his "
    "teaching changed over time, say so.")

MERGE_TASK = """Chapter: {name} — {about}
Notes ({n} items from {v} videos; each line: [video id · published about ...] kind · direction · clarity · codable · transfer | text | parameters | testable):
{notes}

Write the chapter in Markdown:
# {title}
1. In one paragraph: what he teaches here and how it fits his overall method.
2. The ideas, merged and grouped (one subsection each): what it is; the exact conditions; numbers; when he says not to use it;
   how clearly and how often he teaches it (the video ids). Long and short sides apart where both exist.
3. How a program would test it: the 3-8 most testable statements, each precise, with the data needed.
4. Transfer: what could apply to Canadian (TSX) and US markets as it is, what needs adapting (index, sectors, costs,
   instruments), and what is India-only.
5. Gaps and doubts: what is thin, unclear in the captions, or contradicted; what he does not cover here.
Keep it to the substance; no padding."""

CALLS_TASK = """Chapter: Market calls over time — what he said about the market, sector by sector, in his reviews.
Notes ({n} calls; each line: [video id · published about ...] call | horizon):
{notes}

Write the chapter in Markdown:
# Market calls over time
1. How he reads the market week to week (the recurring signals he uses in reviews).
2. The calls in time order (oldest first), grouped by period: the call, its basis, the video id. Dates are approximate
   (from "N months/years ago" as of early October 2026): say so once at the top.
3. For a later point-in-time check: which calls are specific enough to score against what the market then did, and how.
No verdicts on whether he was right: the program will check that against data."""

HYP_TASK = """Chapter: the register of testable hypotheses, from all his teaching.
Candidates ({n}; each line: [video id] topic · direction · codable · transfer | hypothesis | data needed):
{notes}

Write the chapter in Markdown:
# Testable hypotheses (the register)
A short intro: these are the teacher's ideas restated as hypotheses; none is validated; the research rules (pre-registration,
counting looks, real costs, a sealed holdout) apply before any of them could become a rule anywhere.
Then a table with one row per distinct hypothesis (merge duplicates; keep the clearest wording), at most 60 rows, ordered by how
central and how codable it is: id (TWT-H01...), topic, the hypothesis (precise), direction, data needed, markets it could be
tested on (India / Canada / US), codable (YES/PARTLY), source videos.
Then: the 10 to test first, and why (central to his method, precise enough, data available).
Then: what is not testable as taught, and what it would need."""


def _key() -> str:
    k = os.environ.get("ANTHROPIC_API_KEY")
    if not k:
        sys.exit("ANTHROPIC_API_KEY is not set (run through ~/ananta_runs/svc_env_run.py or export it)")
    return k


def _http(method: str, url: str, body: dict | None = None, tries: int = 6) -> bytes:
    data = json.dumps(body).encode() if body is not None else None
    for k in range(tries):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "x-api-key": _key(), "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            return urllib.request.urlopen(req, timeout=600).read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and k < tries - 1:
                time.sleep(float(e.headers.get("retry-after") or 0) or min(60, 5 * 2 ** k))
                continue
            raise RuntimeError(f"Claude API {e.code}: {e.read()[:500]!r}") from None
        except urllib.error.URLError:
            if k < tries - 1:
                time.sleep(5 * 2 ** k)
                continue
            raise
    raise RuntimeError("unreachable")


def _state() -> dict:
    p = WORK / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _save_state(s: dict) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "state.json").write_text(json.dumps(s, indent=1))


def _params(model: str, system: str, user: str, max_tokens: int) -> dict:
    # the newer models take no temperature. Sonnet: no silent thinking, the whole budget goes to the written answer (as
    # teachers.py); Opus does not take that setting (checked Oct 16), so it gets its default and a larger budget.
    p = {"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]}
    if "sonnet" in model:
        p["thinking"] = {"type": "between_tools"}
    return p


def _cid(vid: str) -> str:
    return "v_" + re.sub(r"[^A-Za-z0-9_-]", "_", vid)[:60]


def prepare() -> dict:
    vids = {v["id"]: v for v in json.loads(VIDEOS.read_text())}
    reqs, skipped = [], []
    for f in sorted(TX.glob("*.json")):
        d = json.loads(f.read_text())
        vid = d.get("id") or f.stem
        if vid not in vids:
            continue                                            # the other channel
        words = (d.get("text") or "").split()
        if len(words) < 150:
            skipped.append(vid)
            continue
        user = EXTRACT_TASK.format(title=d.get("title", ""), length=d.get("length", ""), age=d.get("age", "unknown"),
                                   desc=" ".join((d.get("desc") or "").split()[:60]), text=" ".join(words[:26000]),
                                   topics=" | ".join(TOPICS), topic_help="; ".join(f"{k} = {v}" for k, v in TOPICS.items()))
        reqs.append({"custom_id": _cid(vid), "params": _params(SONNET, EXTRACT_SYSTEM, user, 9000)})
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "extract_requests.jsonl").write_text("\n".join(json.dumps(r) for r in reqs) + "\n")
    idmap = {_cid(json.loads(f.read_text()).get("id") or f.stem): json.loads(f.read_text()).get("id") or f.stem for f in TX.glob("*.json")}
    s = _state()
    s.update(prepared=len(reqs), skipped_short=skipped, idmap=idmap, channel_videos=len(vids))
    _save_state(s)
    return {"requests": len(reqs), "too_short": len(skipped), "channel_videos": len(vids),
            "words": sum(len(json.loads(f.read_text()).get("text", "").split()) for f in TX.glob("*.json")
                         if (json.loads(f.read_text()).get("id") or f.stem) in vids)}


def _submit(path: Path, tag: str) -> dict:
    reqs = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    r = json.loads(_http("POST", API, {"requests": reqs}))
    s = _state()
    s[f"{tag}_batch"] = r["id"]
    s[f"{tag}_submitted"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_state(s)
    return {"batch": r["id"], "requests": len(reqs), "status": r.get("processing_status")}


def _wait(bid: str, poll: int = 120, max_s: int = 0) -> dict:
    t0 = time.time()
    while True:
        b = json.loads(_http("GET", f"{API}/{bid}"))
        if b.get("processing_status") == "ended" or (max_s and time.time() - t0 > max_s):
            return b
        print(time.strftime("%H:%M:%S"), b.get("processing_status"), b.get("request_counts"), flush=True)
        time.sleep(poll)


def _results(b: dict):
    raw = _http("GET", b["results_url"]).decode()
    for line in raw.splitlines():
        if line.strip():
            yield json.loads(line)


def _text_usage(res: dict) -> tuple[str | None, dict, str]:
    r = res.get("result") or {}
    if r.get("type") != "succeeded":
        return None, {}, r.get("type") or "unknown"
    m = r["message"]
    return "".join(c.get("text", "") for c in m.get("content", []) if c.get("type") == "text"), m.get("usage", {}), m.get("model", "")


def _cost(usage: dict, model: str) -> float:
    pin, pout = PRICE.get(model, PRICE[OPUS if "opus" in model else SONNET])
    tin = (usage.get("input_tokens") or 0) + (usage.get("cache_creation_input_tokens") or 0) + (usage.get("cache_read_input_tokens") or 0)
    return tin / 1e6 * pin + (usage.get("output_tokens") or 0) / 1e6 * pout


def collect(max_s: int = 0) -> dict:
    s = _state()
    b = _wait(s["extract_batch"], max_s=max_s)
    if b.get("processing_status") != "ended":
        return {"status": b.get("processing_status"), "counts": b.get("request_counts")}
    notes = WORK / "notes"
    notes.mkdir(parents=True, exist_ok=True)
    tally, cost, failed = defaultdict(int), 0.0, []
    for res in _results(b):
        vid = s["idmap"].get(res["custom_id"], res["custom_id"])
        text, usage, model = _text_usage(res)
        if text is None:
            tally[model] += 1
            failed.append(res["custom_id"])
            continue
        cost += _cost(usage, SONNET)
        try:
            note = json.loads(text[text.index("{"):text.rindex("}") + 1])
            tally["ok"] += 1
        except Exception:  # noqa: BLE001
            note = {"unreadable": text[:3000]}
            tally["unreadable"] += 1
        (notes / f"{vid}.json").write_text(json.dumps({"id": vid, "usage": usage, "note": note}, indent=1))
    s.update(extract_collected=dict(tally), extract_failed=failed, extract_cost_usd=round(cost, 2))
    _save_state(s)
    return {"saved": dict(tally), "failed": failed[:20], "cost_usd": round(cost, 2)}


def _notes() -> tuple[dict, dict]:
    vids = {v["id"]: v for v in json.loads(VIDEOS.read_text())}
    out = {}
    for f in (WORK / "notes").glob("*.json"):
        d = json.loads(f.read_text())
        if "unreadable" not in d["note"]:
            out[d["id"]] = d["note"]
    return out, vids


def merge_submit() -> dict:
    notes, vids = _notes()
    reqs = []
    for name, tops in FILES:
        lines, used = [], set()
        for vid, n in notes.items():
            for it in n.get("items") or []:
                if str(it.get("topic", "")).upper() in tops:
                    used.add(vid)
                    lines.append(f"[{vid} · {vids.get(vid, {}).get('age', '?')}] {it.get('kind')} · {it.get('direction')} · {it.get('clarity')} · "
                                 f"{it.get('codable')} · {it.get('transfer')} | {it.get('text')} | {json.dumps(it.get('parameters') or {}, ensure_ascii=False)}"
                                 f" | {it.get('testable') or ''}")
        title = name.split("_", 1)[1].replace("_", " ").capitalize()
        about = "; ".join(TOPICS[t] for t in tops)
        body = "\n".join(lines) if lines else "(no notes on this topic in any video)"
        reqs.append({"custom_id": f"f_{name}", "params": _params(OPUS, MERGE_SYSTEM, MERGE_TASK.format(
            name=name, about=about, n=len(lines), v=len(used), notes=body, title=title), 12000)})
    calls = [f"[{vid} · {vids.get(vid, {}).get('age', '?')}] {c.get('what')} | {c.get('horizon') or ''}"
             for vid, n in notes.items() for c in (n.get("market_calls") or [])]
    reqs.append({"custom_id": "f_13_market_calls_over_time", "params": _params(OPUS, MERGE_SYSTEM, CALLS_TASK.format(
        n=len(calls), notes="\n".join(calls) or "(none)"), 12000)})
    hyps = [f"[{vid}] {it.get('topic')} · {it.get('direction')} · {it.get('codable')} · {it.get('transfer')} | {it.get('testable')} | {it.get('data_needed') or ''}"
            for vid, n in notes.items() for it in (n.get("items") or []) if (it.get("testable") or "").strip()]
    reqs.append({"custom_id": "f_14_testable_hypotheses", "params": _params(OPUS, MERGE_SYSTEM, HYP_TASK.format(
        n=len(hyps), notes="\n".join(hyps) or "(none)"), 16000)})
    (WORK / "merge_requests.jsonl").write_text("\n".join(json.dumps(r) for r in reqs) + "\n")
    r = _submit(WORK / "merge_requests.jsonl", "merge")
    r.update(videos_with_notes=len(notes), market_calls=len(calls), hypotheses=len(hyps))
    return r


HEADER = ("<!-- Trading Knowledge Library · Trade With Trend (Raunak A, India). Built {day} from {n} public videos with captions "
          "(of {total} on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this "
          "chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: "
          "external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->\n\n")


def merge_collect(max_s: int = 0) -> dict:
    s = _state()
    b = _wait(s["merge_batch"], max_s=max_s)
    if b.get("processing_status") != "ended":
        return {"status": b.get("processing_status"), "counts": b.get("request_counts")}
    notes, vids = _notes()
    OUT.mkdir(parents=True, exist_ok=True)
    written, cost, failed = [], 0.0, []
    hdr = HEADER.format(day=time.strftime("%Y-%m-%d"), n=len(notes), total=len(vids))
    for res in _results(b):
        text, usage, model = _text_usage(res)
        if text is None:
            failed.append(res["custom_id"])
            continue
        cost += _cost(usage, OPUS)
        name = res["custom_id"][2:]
        (OUT / f"{name}.md").write_text(hdr + text.strip() + "\n")
        written.append(name)
    _index(sorted(written), notes, vids)
    s.update(merge_written=sorted(written), merge_failed=failed, merge_cost_usd=round(cost, 2))
    _save_state(s)
    return {"written": sorted(written), "failed": failed, "cost_usd": round(cost, 2)}


def _index(names: list[str], notes: dict, vids: dict) -> None:
    kinds, quality, topics = defaultdict(int), defaultdict(int), defaultdict(int)
    for n in notes.values():
        kinds[n.get("kind", "?")] += 1
        quality[n.get("quality", "?")] += 1
        for it in n.get("items") or []:
            topics[str(it.get("topic", "?")).upper()] += 1
    lines = ["# Trading Knowledge Library · Trade With Trend", "",
             "Raunak A's public teaching, organised by topic, for Ananta's research across India, Canada and the US.",
             "Every chapter is the teacher's method restated as hypotheses; none of it is validated, and nothing in the crypto agent,",
             "its books or its gate reads this folder. The path to use: concept -> formal spec -> pre-registered test -> independent",
             "validation -> agent knowledge (Canada plan, section 11).", "",
             f"Built from {len(notes)} public videos with captions, of {len(vids)} on the channel (members-only videos were not used).", "",
             "| Chapter | Notes behind it |", "|---|---|"]
    for name in names:
        tops = dict(FILES).get(name, [])
        lines.append(f"| [{name.split('_', 1)[1].replace('_', ' ').capitalize()}]({name}.md) | {sum(topics[t] for t in tops) if tops else '-'} |")
    lines += ["", "Videos by kind: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())),
              "Videos by quality: " + ", ".join(f"{k} {v}" for k, v in sorted(quality.items())),
              "Items by topic: " + ", ".join(f"{k} {v}" for k, v in sorted(topics.items(), key=lambda x: -x[1]))]
    (OUT / "README.md").write_text("\n".join(lines) + "\n")


def status() -> dict:
    s = _state()
    out = {k: v for k, v in s.items() if k not in ("idmap", "skipped_short")}
    for tag in ("extract", "merge"):
        bid = s.get(f"{tag}_batch")
        if bid:
            b = json.loads(_http("GET", f"{API}/{bid}"))
            out[f"{tag}_now"] = {"status": b.get("processing_status"), "counts": b.get("request_counts")}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "submit", "collect", "merge-submit", "merge-collect", "status"])
    ap.add_argument("--max-wait", type=int, default=0, help="seconds to wait for a batch before returning (0 = until it ends)")
    a = ap.parse_args()
    if a.cmd == "prepare":
        r = prepare()
    elif a.cmd == "submit":
        r = _submit(WORK / "extract_requests.jsonl", "extract")
    elif a.cmd == "collect":
        r = collect(a.max_wait)
    elif a.cmd == "merge-submit":
        r = merge_submit()
    elif a.cmd == "merge-collect":
        r = merge_collect(a.max_wait)
    else:
        r = status()
    print(json.dumps(r, indent=1, default=str))


if __name__ == "__main__":
    main()
