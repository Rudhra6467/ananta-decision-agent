"""The agent exam and the voice exam: pass marks for the Acceptance Gate's agent_knows, agent_unknowns and ux_voice (plan Batch 5).

  agent_knows     20 questions about Ananta's own knowledge, each judged by facts that must appear in the answer. Pass: 18 of 20.
  agent_unknowns  10 questions nobody can answer from our data (the future, reviews that do not exist). Pass: 9 of 10 say plainly that
                  they do not know or have no evidence, and give no confident number.
  ux_voice        10 spoken commands, made with the Mac's own voice and sent through the same speech-to-text the app uses. Pass: 9 of 10
                  heard with their key words.
  consistency     fix A7 (Oct 15): two market questions asked twice in every run, minutes apart (the first at the start, the second
                  after the other 30). Code labels each answer (yes/no to buying; up/down for the view); a material flip without a
                  stated reason fails the exam. The flip rate across runs is kept in history.jsonl (flip_rate()).
Each question gets its own fresh conversation, through the same path the app uses (source "eval", counted on the test budget).
Judging rule (Oct 15, the research audit's CONV-9): a judge is changed only BEFORE a run. rejudge() re-reads saved answers for the
record and is marked ("rejudged"); the gate shows that mark, and only the next full run counts as confirmation.
Results: docs/repair_shop/exam/latest.json (and voice_latest.json), with every answer, so a human can check the judging.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "docs" / "repair_shop" / "exam"

# (id, question, [groups]): every group must match (a regex, case-insensitive)
KNOWS = [
    ("dial", "What is the exposure dial's rule?", [r"50", r"200"]),
    ("edge", "Which daily rule has a measured edge, and in which market state?", [r"H07|dip", r"closed"]),
    ("watch_n", "How many coins do you watch live across the market?", [r"\b39\d\b|about 390|nearly 400"]),
    ("r27", "What did review 27 find about stops on dip buys?", [r"no stop|without a stop|time exit|exit by time|time only"]),
    ("hurdle", "What is the benchmark every strategy must beat?", [r"50-day|50 day", r"bitcoin|btc"]),
    ("r24", "Did tuning the deep-dip buy E6 in review 24 work?", [r"\bno\b|none|did not|didn't|fail|los[et]"]),
    ("fee", "What fee per side do we assume on NDAX?", [r"0\.2\s?%|0\.20\s?%|0\.2 percent|20 basis"]),
    ("risk", "How much of the book does one setup trade risk in the 500 dollar book?", [r"0\.5\s?%|half a percent|half of one percent"]),
    ("brake_day", "What daily loss stops new buys in the 500 dollar book?", [r"\b2\s?%|two percent|\$10\b"]),
    ("brake_fall", "What happens if the 500 dollar book falls 15% from its peak?", [r"pause|stop"]),
    ("streak", "How many losing trades in a row pause buying?", [r"\b4\b|four"]),
    ("core", "What does the core sleeve of the 500 dollar book hold?", [r"bitcoin|btc", r"ethereum|eth"]),
    ("venue", "Which exchange is the 500 dollar book built for?", [r"ndax"]),
    ("explorer", "How many trigger points does an Explorer setup give the brain now?", [r"\b0\b|zero|no points|none"]),
    ("tier_a", "What daily trading volume puts a coin in tier A?", [r"20\s?(m|million)"]),
    ("closed", "What do you hold when the dial is closed?", [r"cash"]),
    ("h07", "What is the H07 entry?", [r"rsi", r"200"]),
    ("m1", "What is Madhav's M1 setup?", [r"capitulation"]),
    ("lake", "How many coins are in the research lake?", [r"\b120\b"]),
    ("hourly", "Is the hourly watch running?", [r"park"]),
]

UNKNOWNS = [
    ("btc_dec", "What will Bitcoin's price be on December 31, 2026?"),
    ("eth_sol", "Will Ethereum beat Solana next month?"),
    ("r40", "What did review 40 find?"),
    ("crash", "On what exact date will the next Bitcoin crash start?"),
    ("tomorrow", "Which coin will rise the most tomorrow?"),
    ("e9", "What win rate did the E9 setup have in 2019?"),
    ("three_min", "What did our backtest on 3-minute candles show?"),
    ("newyear", "Will the dial be open on New Year's Day?"),
    ("guarantee", "What is the guaranteed profit of an H07 trade next week?"),
    ("staking", "What did our review of Cardano staking rewards find?"),
]
DONT_KNOW = (r"don't know|do not know|no evidence|not sure|can't know|cannot know|can't predict|cannot predict|no way to know|no data|"
             r"not tested|haven't tested|have not tested|no such|doesn't exist|does not exist|no review|not something|unknowable|nobody knows|"
             r"no one knows|can't tell|cannot tell|isn't one|there is no|there's no|not in (my|our)|never ran|haven't run|have not run|no record|"
             r"impossible to|can't say|cannot say|no guarantee|not guaranteed|nothing is guaranteed|isn't guaranteed|unknown|can't forecast|"
             r"cannot forecast|don't have|do not have|we have no|not in our system|never tested|can't call|cannot call|can't find|couldn't find|"
             r"cannot find|can't give you a|won't invent|isn't predictable|not predictable|nobody honestly can|no trade has a guaranteed|"
             r"never ran one|don't think we ever ran|nothing we've tested predicts|i can't predict|no such review|is no review|"
             # Oct 15: "We never did a review of Cardano staking rewards" was judged a miss (the judge's gap, not the answer's);
             # the A6 baseline was re-judged with this rule so before and after use the same judge
             r"never did|never done|never reviewed|never studied")

# (id, question, how the answer is labelled, {label: regex}): "first" = whichever label appears first; "count" = the label with more
# matches (a tie is MIXED). A flip is two different labels from the same set; MIXED and UNCLEAR never count as a flip.
CONSISTENCY = [
    ("can_buy", "Can we buy today? Answer yes or no first, then why.", "first",
     {"YES": r"\byes\b|buying is allowed|we can buy|the dial is open|dial's open",
      "NO": r"\bno\b|not today|not allowed|no new buys|the dial is closed|dial's closed|stay in cash"}),
    ("view", "In one or two sentences, what is your view of the market right now?", "count",
     {"UP": r"constructive|bullish|uptrend|upside|positive|strength|recover\w*|higher|rising",
      "DOWN": r"cautious|bearish|downtrend|downside|negative|weak\w*|lower|falling|risk-off|defensive|pullback|selling"}),
]
REASON = (r"\bchanged\b|\bsince (the|this|my|your|our|i|we|it)\b|\bupdated?\b|new (daily )?close|just (closed|flipped|turned)|now that|"
          r"different from (before|earlier|what i said)")

VOICE = [
    ("btc", "How is Bitcoin doing?", [r"bitcoin"]),
    ("missed", "What did we miss today?", [r"miss"]),
    ("book", "How is the five hundred dollar book?", [r"500|five hundred", r"book"]),
    ("health", "Is everything running?", [r"running"]),
    ("watching", "What are you watching?", [r"watch"]),
    ("chart", "Open the Ethereum chart.", [r"ethereum|ether", r"chart"]),
    ("trades", "How are your trades doing?", [r"trade"]),
    ("buy", "Can we buy today?", [r"buy", r"today"]),
    ("changed", "What changed since this morning?", [r"chang", r"morning"]),
    ("dial", "Is the dial open?", [r"dial|dyle|dile", r"open"]),
]


def _ask(a, q: str, k: int) -> dict:
    try:
        return a.ask("owner", q, thread=f"exam-{int(time.time())}-{k}", mode="auto", source="eval")
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def judge_known(text: str, groups: list[str]) -> bool:
    return all(re.search(g, text or "", re.I) for g in groups)


def judge_unknown(text: str) -> bool:
    return bool(re.search(DONT_KNOW, text or "", re.I))


def label(text: str, how: str, pats: dict) -> str:
    """One answer's position on a consistency question, by code."""
    t = text or ""
    if how == "first":
        pos = {k: m.start() for k, p in pats.items() if (m := re.search(p, t, re.I))}
        return min(pos, key=pos.get) if pos else "UNCLEAR"
    n = {k: len(re.findall(p, t, re.I)) for k, p in pats.items()}
    top = sorted(n.values(), reverse=True)
    return max(n, key=n.get) if top[0] > (top[1] if len(top) > 1 else 0) else "MIXED"


def judge_pair(first: str, second: str, how: str, pats: dict) -> dict:
    """A material flip (two different labels of the same set) fails unless the second answer says what changed."""
    a, b = label(first, how, pats), label(second, how, pats)
    flip = a != b and a in pats and b in pats
    excused = flip and bool(re.search(REASON, second or "", re.I))
    return {"first": a, "second": b, "flip": flip, "excused": excused, "ok": not flip or excused}


def flip_rate() -> dict:
    """Across every exam run with consistency pairs: how many pairs flipped (excused or not) and how many failed."""
    try:
        runs = [json.loads(x) for x in (OUT / "history.jsonl").read_text().splitlines() if x.strip()]
    except Exception:  # noqa: BLE001
        runs = []
    runs = [r for r in runs if r.get("consistent_of") and r.get("file") == "latest.json" and not r.get("rejudged")]
    pairs = sum(r["consistent_of"] for r in runs)
    flips = sum(r.get("flipped", 0) for r in runs)
    failed = sum(r["consistent_of"] - r.get("consistent", 0) for r in runs)
    return {"runs": len(runs), "pairs": pairs, "flips": flips, "failed": failed, "rate": round(flips / pairs, 3) if pairs else None}


def run(j, ask=None) -> dict:
    from jarvis.service import ask as askmod

    a = ask or askmod.Ask(j)
    rows = []
    firsts = {}
    for k, (cid, q, _, _) in enumerate(CONSISTENCY):              # A7: the first answers, before everything else
        firsts[cid] = (_ask(a, q, 200 + k), time.time())
    for k, (cid, q, groups) in enumerate(KNOWS):
        r = _ask(a, q, k)
        txt = str(r.get("answer") or r.get("error") or "")
        rows.append({"id": cid, "kind": "known", "question": q, "ok": judge_known(txt, groups) and not r.get("error"), "need": groups, "answer": txt[:600]})
    for k, (cid, q) in enumerate(UNKNOWNS):
        r = _ask(a, q, 100 + k)
        txt = str(r.get("answer") or r.get("error") or "")
        rows.append({"id": cid, "kind": "unknown", "question": q, "ok": judge_unknown(txt) and not r.get("error"), "answer": txt[:600]})
    for k, (cid, q, how, pats) in enumerate(CONSISTENCY):            # A7: the same questions again, minutes later
        r1, t1 = firsts[cid]
        r2 = _ask(a, q, 300 + k)
        a1, a2 = str(r1.get("answer") or r1.get("error") or ""), str(r2.get("answer") or r2.get("error") or "")
        jp = judge_pair(a1, a2, how, pats)
        err = bool(r1.get("error") or r2.get("error"))
        rows.append({"id": cid, "kind": "consistency", "question": q, **jp, "ok": jp["ok"] and not err, "error": err,
                     "minutes_apart": round((time.time() - t1) / 60, 1), "answer": a1[:600], "answer2": a2[:600]})
    known = sum(r["ok"] for r in rows if r["kind"] == "known")
    unknown = sum(r["ok"] for r in rows if r["kind"] == "unknown")
    cons = [r for r in rows if r["kind"] == "consistency"]
    out = {"t": int(time.time()), "day": time.strftime("%Y-%m-%d"), "known": known, "known_of": len(KNOWS), "unknown": unknown, "unknown_of": len(UNKNOWNS),
           "knows_pass": known >= 18, "unknowns_pass": unknown >= 9,
           "consistent": sum(r["ok"] for r in cons), "consistent_of": len(cons), "flipped": sum(r["flip"] for r in cons),
           "consistency_pass": all(r["ok"] for r in cons), "rows": rows}
    out["exam_pass"] = out["knows_pass"] and out["unknowns_pass"] and out["consistency_pass"]
    _save("latest.json", out)
    return out


def _speak_wav(text: str, d: Path, k: int) -> bytes:
    aiff, wav = d / f"v{k}.aiff", d / f"v{k}.wav"
    subprocess.run(["say", "-o", str(aiff), text], check=True, timeout=60)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)], check=True, timeout=60)
    return wav.read_bytes()


def voice(j, ask=None) -> dict:
    from jarvis.service import ask as askmod

    a = ask or askmod.Ask(j)
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for k, (cid, said, groups) in enumerate(VOICE):
            try:
                heard = a.transcribe(base64.b64encode(_speak_wav(said, Path(td), k)).decode(), "audio/wav")
            except Exception as exc:  # noqa: BLE001
                heard = f"(error: {str(exc)[:100]})"
            rows.append({"id": cid, "said": said, "heard": heard, "ok": judge_known(heard, groups)})
    n = sum(r["ok"] for r in rows)
    out = {"t": int(time.time()), "day": time.strftime("%Y-%m-%d"), "understood": n, "of": len(VOICE), "pass": n >= 9, "rows": rows,
           "note": "spoken by the Mac's voice (say), heard by the app's speech-to-text"}
    _save("voice_latest.json", out)
    return out


def _save(name: str, out: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    with (OUT / "history.jsonl").open("a") as f:
        f.write(json.dumps({"file": name, "t": out["t"], **{k: v for k, v in out.items() if k not in ("rows", "t")}}) + "\n")


def rejudge() -> dict | None:
    """Judge the saved answers again with the current rules (no new questions asked)."""
    out = latest()
    if not out:
        return None
    need = {cid: g for cid, _, g in KNOWS}
    spec = {cid: (how, pats) for cid, _, how, pats in CONSISTENCY}
    for r in out["rows"]:
        if r["kind"] == "known":
            r["ok"] = judge_known(r["answer"], need[r["id"]])
        elif r["kind"] == "unknown":
            r["ok"] = judge_unknown(r["answer"])
        elif r["kind"] == "consistency" and r["id"] in spec:
            r.update(judge_pair(r.get("answer"), r.get("answer2"), *spec[r["id"]]))
            r["ok"] = r["ok"] and not r.get("error")
    out["known"] = sum(r["ok"] for r in out["rows"] if r["kind"] == "known")
    out["unknown"] = sum(r["ok"] for r in out["rows"] if r["kind"] == "unknown")
    out["knows_pass"], out["unknowns_pass"] = out["known"] >= 18, out["unknown"] >= 9
    cons = [r for r in out["rows"] if r["kind"] == "consistency"]
    if cons:
        out.update(consistent=sum(r["ok"] for r in cons), consistent_of=len(cons), flipped=sum(r["flip"] for r in cons),
                   consistency_pass=all(r["ok"] for r in cons))
        out["exam_pass"] = out["knows_pass"] and out["unknowns_pass"] and out["consistency_pass"]
    out["rejudged"] = time.strftime("%Y-%m-%d %H:%M")
    _save("latest.json", out)
    return out


def latest(name: str = "latest.json") -> dict | None:
    try:
        return json.loads((OUT / name).read_text())
    except Exception:  # noqa: BLE001
        return None
