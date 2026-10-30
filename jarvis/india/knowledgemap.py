"""The one map (Phase 1 of the reverse-engineering pass, 29 Oct 2026; Madhav: "Something is planned, not done. Something is done, but not
noted. Noted but not in paper. In paper, but not embedded... I want deep analysis, mappings and a simple way for agent and voice to use it").

One table, built by code from every record Ananta keeps, so that each idea has a single row that says where it stands in every layer:

  registered -> tested (verdict, at full scale or not) -> written up -> in the paper rules -> in the facts the voice reads -> has a plain-words
  name -> in the read model the screens show -> in the exam -> pinned in the lock -> tracker state -> hypothesis state

and a list of the mismatches between layers, each with a class and a lane (SAFE: fix now; DECISION: needs Madhav's yes because it touches a
pinned rule). Nothing here changes anything; it reads and reports.

  python -m jarvis.india.knowledgemap build      docs/knowledge/india_map.json and docs/repair_shop/map/latest.md (+ <date>.md)
  python -m jarvis.india.knowledgemap gaps       the gap counts only (what the nightly check reads)

Sources: the test ledger (registrations and results), the registration folder (specs, results pages, locks, the exam, the tracker, the exit
book), the hypothesis map, the paper config, the read model, the Ask's own facts block, askwords' names, and the reconstruction decisions.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))
DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
REG = RECORDS / "india" / "registrations"
OUT_JSON = ROOT / "docs" / "knowledge" / "india_map.json"
OUT_DIR = ROOT / "docs" / "repair_shop" / "map"
MIN_DATES = 16                      # the registry's rule: fewer blocks than this in a period is INCONCLUSIVE for want of data
RANK = {"VALIDATED": 5, "CONDITIONAL": 4, "OPPOSITE": 3, "REJECTED": 2, "SUPPORTED_SEEN": 2, "NOT_SUPPORTED_SEEN": 1, "NOT_CONFIRMED": 1, "INCONCLUSIVE": 0}
# the paper rules and what backs them (the paper config does not name its studies; these links are from the tracker's own notes)
PAPER_LINKS = {"E02": "the BRK and PULL entry sets and their exits", "E03": "the BRK and PULL exits", "G01": "the exit book (hold_20d reference exit)",
               "P01": "the REV family (RSI under 30), rules v1.2", "SP1": "the index options line", "SP1P": "the options line on paper", "SZ2": "the options line's sizing",
               "SP3": "the positional playbook (registered, not in a book)", "HG1": "the allocation rule's cash by regime (informs it)", "RX1": "the RX1 paper trial"}
GLOSS = {"A": "planned, not done", "B": "done, not noted", "C": "proved, not in the paper rules", "D": "in the paper rules, not in the voice's facts",
         "E": "tested, but not at full scale", "F": "the voice has it, but no plain-words name", "G": "a result the screens do not show"}


def _jsonl(p: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _source(sid: str) -> str:
    if sid.startswith("T-"):
        return "teacher card"
    if sid.startswith("RX"):
        return "reconstruction draft (Madhav's yes)"
    if sid.startswith(("SP", "SZ", "OC")):
        return "the playbook work (Madhav, 19-21 Oct)"
    if sid.startswith("HF"):
        return "Hugging Face model"
    return "the lab"


def _full_scale(results: list[dict]) -> str:
    """'full' when any variant had enough blocks in both periods; 'thin' when every variant was short of data; 'none' with no results."""
    if not results:
        return "none"
    for r in results:
        d, v = r.get("dev") or [None, None, 0], r.get("val") or [None, None, 0]
        if (d[2] or 0) >= MIN_DATES and (v[2] or 0) >= MIN_DATES:
            return "full"
    return "thin"


def _top(res: list[dict], n: int = 4) -> list[dict]:
    """The strongest variants (by verdict rank, then validation t), with their numbers, so the voice can say size and direction."""
    last = {}
    for r in res:                                           # the newest result per variant
        last[r.get("variant")] = r
    rs = sorted(last.values(), key=lambda r: (-RANK.get(r.get("verdict"), -1), -abs((r.get("val") or [0, 0, 0])[1] or 0)))
    out = []
    for r in rs[:n]:
        d, v = r.get("dev") or [None, None, 0], r.get("val") or [None, None, 0]
        out.append({"variant": r.get("variant"), "verdict": r.get("verdict"), "dev_mean": d[0], "dev_t": d[1], "dev_blocks": d[2], "val_mean": v[0], "val_t": v[1], "val_blocks": v[2]})
    return out


def _tokens(text: str, ids: list[str]) -> set[str]:
    """Which study ids appear in a text as whole tokens (T-TWT-H10 also matches as TWT-H10)."""
    found = set()
    for sid in ids:
        alts = {sid, sid.replace("T-", "", 1)} if sid.startswith("T-") else {sid}
        if any(re.search(rf"(?<![\w-]){re.escape(a)}(?![\w-])", text) for a in alts):
            found.add(sid)
    return found


def _tracker_rows() -> dict[str, dict]:
    rows = {}
    p = REG / "research_tracker.md"
    try:
        for line in p.read_text().splitlines():
            if not line.startswith("| ") or line.startswith("| id") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 6 and re.match(r"^[A-Z]{1,3}\d{1,2}[A-Z]?$|^[A-Z]{2,4}$", cells[0]):
                rows[cells[0]] = {"state": cells[5] if len(cells) > 6 else cells[2], "title": cells[3] if len(cells) > 6 else cells[1], "note": cells[-1][:200]}
    except OSError:
        pass
    return rows


def _hypotheses() -> list[dict]:
    p = DATA / "gold" / "hypothesis_map" / "hypothesis_map.csv"
    try:
        with p.open() as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def _facts_text() -> str:
    """The Ask's own facts block, as the voice sees it (owner view); '' when the read model is not there."""
    try:
        from jarvis.india import ask
        return json.dumps(ask.facts(owner=True), default=str)
    except Exception as e:  # noqa: BLE001
        return f"__facts_unavailable__ {type(e).__name__}"


def _plain_names() -> dict:
    try:
        from jarvis.india import askwords
        return {**askwords.STUDIES, **{k: v for k, v in askwords.titles().items()}}
    except Exception:  # noqa: BLE001
        return {}


def _paper_refs() -> dict[str, str]:
    """Study ids named by the paper rule files, plus the known links."""
    refs = dict(PAPER_LINKS)
    files = [RECORDS / "india" / "paper_config.json", REG / "sp1_v2.json", REG / "allocation_rule_v1.json", REG / "exit_policy_book.md", REG / "sz2_v1.json"]
    text = "\n".join(p.read_text() for p in files if p.exists())
    return refs, text


def _lock_text() -> str:
    lock = _json(REG / "india_lock.json", {}) or {}
    parts = [json.dumps(lock)]
    for pin in (lock.get("pins") or {}).values():
        for f in pin.get("files") or []:
            p = RECORDS / f
            if p.exists() and p.suffix in (".json", ".md", ".csv"):
                try:
                    parts.append(p.read_text())
                except OSError:
                    pass
    return "\n".join(parts)


def build() -> dict:
    t0 = time.time()
    ledger = _jsonl(DATA / "manifests" / "test_ledger.jsonl")
    regs = defaultdict(list)
    for r in ledger:
        if r.get("kind") == "registration":
            regs[r["study"]].append(r)
    results = defaultdict(list)
    for r in ledger:
        if r.get("kind") == "result":
            results[r["study"]].append(r)
    ids = sorted(set(regs) | set(results))
    facts = _facts_text()
    names = _plain_names()
    paper_refs, paper_text = _paper_refs()
    paper_ids = _tokens(paper_text, ids) | {i for i in ids if i in paper_refs}
    rm_text = json.dumps(_json(DATA / "readmodel" / "latest.json", {}), default=str)
    exam_text = json.dumps(_json(REG / "india_exam_v1.json", {}), default=str)
    lock_text = _lock_text()
    facts_ids, rm_ids, exam_ids, lock_ids = _tokens(facts, ids), _tokens(rm_text, ids), _tokens(exam_text, ids), _tokens(lock_text, ids)
    tracker = _tracker_rows()
    hyps = _hypotheses()
    hyp_by_study = defaultdict(list)
    for h in hyps:
        if h.get("study") and h["study"] != "-":
            hyp_by_study[h["study"].split("-")[0]].append(h["id"])
    decisions = _jsonl(DATA / "paper" / "reconstruction" / "decisions.jsonl")
    answered = _json(REG / "answered_situations.json", {}) or {}
    ans_prefixes = [a["prefix"] for a in answered.get("answered") or []]
    specs = {p.stem.split("_v")[0].upper() for p in REG.glob("*_v*.json")}
    # "written up" = named in any write-up Ananta can read (results pages, the exit book, the playbook results, the teachers' results ...)
    md_text = "\n".join(p.read_text() for p in REG.glob("*.md") if p.name not in ("research_tracker.md", "hypothesis_review.md"))
    pages = _tokens(md_text, ids)

    rows = []
    for sid in ids:
        reg = regs.get(sid) or []
        res = results.get(sid) or []
        vc = Counter(r.get("verdict") for r in res)
        best = max((v for v in vc if v), key=lambda v: RANK.get(v, -1), default=None)
        base = sid.split("-")[0]
        row = {"id": sid, "family": (reg[-1].get("family") if reg else (res[-1].get("family") if res else None)), "source": _source(sid),
               "title": ((reg[-1].get("title") if reg else "") or "")[:160], "registered": bool(reg), "registered_at": (reg[0].get("at") if reg else None)[:10] if reg else None,
               "versions": len(reg), "variants": len({r.get("variant") for r in res}), "verdicts": dict(vc), "best_verdict": best, "scale": _full_scale(res),
               "last_result": max((r.get("at") or "" for r in res), default=None), "spec_file": base in specs or sid in specs, "results_page": sid in pages,
               "tracker_state": (tracker.get(sid) or tracker.get(base) or {}).get("state"), "hypotheses": hyp_by_study.get(base, [])[:6],
               "in_paper": sid in paper_ids or sid in paper_refs or base in paper_refs, "paper_role": paper_refs.get(sid) or paper_refs.get(base),
               "in_facts": sid in facts_ids, "plain_name": names.get(sid) or names.get(base) or names.get(sid.replace("T-", "", 1)),
               "in_readmodel": sid in rm_ids, "in_exam": sid in exam_ids, "in_lock": sid in lock_ids or base in lock_ids,
               "top_variants": _top(res)}
        rows.append(row)

    # ----------------------------------------------------------------------------------------------- the gaps
    gaps = []

    def gap(cls, sid, what, lane="SAFE", fix=""):
        gaps.append({"class": cls, "meaning": GLOSS[cls], "id": sid, "what": what, "lane": lane, "fix": fix})

    for row in rows:
        sid, best = row["id"], row["best_verdict"]
        if row["registered"] and not row["variants"]:
            gap("A", sid, "registered, no result recorded", "SAFE", "run it or withdraw the registration with a note")
        if row["variants"] and not (row["results_page"] or row["in_facts"] or row["plain_name"]):
            gap("B", sid, f"{row['variants']} variants recorded ({best}), no results page, not in the facts, no plain name", "SAFE", "write the results page and a plain-words name")
        if best in ("VALIDATED", "CONDITIONAL") and not row["in_paper"]:
            gap("C", sid, f"{best}: {row['title'][:90]}", "DECISION", "decide: a filter in the paper rules, a 20-session trial, or 'noted, not used' with the reason")
        if row["scale"] == "thin" and row["variants"]:
            gap("E", sid, "every variant short of the registry's block count in a period (INCONCLUSIVE for want of data)", "SAFE", "say so in the facts; re-run when the data allows")
        if row["in_facts"] and not row["plain_name"] and row["source"] != "teacher card":
            gap("F", sid, "in the voice's facts with no plain-words name (the voice may say the code)", "SAFE", "add a name to askwords.STUDIES")
        if row["variants"] and best in ("VALIDATED", "CONDITIONAL", "OPPOSITE") and not row["in_readmodel"] and not row["in_facts"]:
            gap("G", sid, f"{best} result that neither the read model nor the facts carry", "SAFE", "surface it in indicator_knowledge or the teacher cards")
    # planned, not done: tracker rows not READY; hypotheses with no study; approved drafts no study covers
    for tid, t in tracker.items():
        if t.get("state") and t["state"] not in ("READY", "DONE", "") and tid not in {r["id"] for r in rows}:
            gap("A", tid, f"tracker: {t['state']}: {t.get('title', '')[:100]}", "SAFE", t.get("note", "")[:120] or "build it, or mark it dropped with a reason")
    for h in hyps:
        if h.get("status") in ("NEEDS_BUILD", "NEEDS_DATA", "WAITS_RECORDER") and (not h.get("study") or h["study"] == "-"):
            gap("A", h["id"], f"hypothesis {h['status']}, no study: {str(h.get('text', ''))[:100]}", "SAFE", "a study id or a 'dropped' mark")
    seen_keys = set()
    for d in decisions:
        k = d.get("key")
        if d.get("decision") == "APPROVED" and k and k not in seen_keys:
            seen_keys.add(k)
            if not any(k.startswith(p.replace("*", "")) or re.match("^" + re.escape(p).replace(r"\*", ".*"), k) for p in ans_prefixes):
                gap("A", k, "an approved draft with no study answering it", "SAFE", "register and run it, or record why not")
    # in the paper rules, not in the voice's facts: the rule elements the facts should describe
    cfg = _json(RECORDS / "india" / "paper_config.json", {}) or {}
    st = cfg.get("stock") or {}
    checks = [("the Rs 50,000 research scale unit per trade", "50,000"), ("the Rs 60,000 book", "60,000"), ("the 250 most traded stocks (liq_top)", "250"),
              ("the 14-session re-entry rule", "re-entry" if "re-entry" in facts else "reentry"), ("the 2-ATR initial stop", "2 ATR" if "2 ATR" in facts else "2-ATR"),
              ("the hold_20d reference exit", "20 sessions" if "20 sessions" in facts else "hold_20d"), ("the random control's 40-name draw", "random control"),
              ("the per-family caps (10/10/10/5)", "cap")]
    for what, token in checks:
        if token.lower() not in facts.lower():
            gap("D", "paper_rules", f"{what} is not described in the facts the voice reads", "SAFE", "add it to guardrail_facts / the paper rules part of the facts")
    if "__facts_unavailable__" in facts:
        gap("D", "facts", "the facts block could not be built here, so in_facts is unknown for every row", "SAFE", "run on the Mac with the read model present")

    counts = Counter(g["class"] for g in gaps)
    summary = {"built_at": dt.datetime.now().isoformat(timespec="seconds"), "studies": len(rows), "variants": sum(r["variants"] for r in rows),
               "gap_counts": {f"{k} {GLOSS[k]}": counts.get(k, 0) for k in GLOSS}, "gaps_total": len(gaps),
               "needs_yes": sum(1 for g in gaps if g["lane"] == "DECISION"), "seconds": round(time.time() - t0, 1)}
    summary["words"] = (f"The map holds {len(rows)} studies and {summary['variants']} variants. {len(gaps)} mismatches between layers: "
                        + ", ".join(f"{counts.get(k, 0)} {GLOSS[k]}" for k in GLOSS if counts.get(k)) + f"; {summary['needs_yes']} need Madhav's yes.")
    return {"summary": summary, "rows": rows, "gaps": gaps}


def write(m: dict) -> Path:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(m, indent=1, ensure_ascii=False, default=str))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s = m["summary"]
    lines = [f"# The one map ({s['built_at'][:16]})", "", s["words"], "", "## Mismatches", "", "| class | id | what | lane | fix |", "|---|---|---|---|---|"]
    for g in sorted(m["gaps"], key=lambda g: (g["class"], g["id"])):
        lines.append(f"| {g['class']} {g['meaning']} | {g['id']} | {g['what'].replace('|', '/')} | {g['lane']} | {g['fix'].replace('|', '/')} |")
    lines += ["", "## Every study", "", "| id | source | best verdict | variants | scale | page | paper | facts | plain name | screens | exam | lock | tracker |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    y = lambda b: "yes" if b else "-"
    for r in m["rows"]:
        lines.append(f"| {r['id']} | {r['source']} | {r['best_verdict'] or '-'} | {r['variants']} | {r['scale']} | {y(r['results_page'])} | {y(r['in_paper'])} | {y(r['in_facts'])} | "
                     f"{y(r['plain_name'])} | {y(r['in_readmodel'])} | {y(r['in_exam'])} | {y(r['in_lock'])} | {r['tracker_state'] or '-'} |")
    text = "\n".join(lines) + "\n"
    (OUT_DIR / "latest.md").write_text(text)
    (OUT_DIR / f"{s['built_at'][:10]}.md").write_text(text)
    return OUT_DIR / "latest.md"


def gaps() -> dict:
    m = _json(OUT_JSON, {}) or {}
    return (m.get("summary") or {}).get("gap_counts") or {}


def lookup(question: str, limit: int = 6) -> list[dict]:
    """The map rows a question is about (ids named, or two shared content words with a title), for the Ask's facts: compact, plain."""
    m = _json(OUT_JSON, {}) or {}
    rows = m.get("rows") or []
    q = (question or "").lower()
    stop = {"the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "is", "it", "does", "do", "what", "about", "did", "you", "ananta", "test", "tested", "study", "with", "by", "from", "that", "this"}
    qw = {w for w in re.findall(r"[a-z][a-z0-9-]{2,}", q) if w not in stop}
    out = []
    for r in rows:
        named = r["id"].lower() in q or r["id"].replace("T-", "", 1).lower() in q
        tw = {w for w in re.findall(r"[a-z][a-z0-9-]{2,}", (r.get("title") or "").lower()) if w not in stop}
        score = 3 if named else len(qw & tw)
        if score >= 2:
            out.append((score, r))
    out.sort(key=lambda t: (-t[0], t[1]["id"]))
    return [{"id": r["id"], "name": r.get("plain_name") or r["id"], "title": r.get("title"), "verdict": r.get("best_verdict"), "scale": r.get("scale"),
             "in_paper_rules": r.get("in_paper"), "paper_role": r.get("paper_role"), "results_page": r.get("results_page"),
             "numbers": [{"variant": t["variant"], "verdict": t["verdict"], "mean_2000_2017": t["dev_mean"], "mean_2018_2023": t["val_mean"], "t": [t["dev_t"], t["val_t"]]}
                         for t in (r.get("top_variants") or [])[:3]],
             "numbers_meaning": "means are per event in return units (0.01 = 1%) unless the variant says otherwise; t beyond about 3.6 clears the bar"} for _, r in out[:limit]]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "gaps":
        print(json.dumps(gaps(), indent=1))
    else:
        m = build()
        p = write(m)
        print(m["summary"]["words"], "\n->", p)
