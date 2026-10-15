"""The audit register closes every card of the research audit of 2026-10-14/15.

docs/knowledge/audit_register.json holds one row per card (and per reconstruction item) and one entry per follow-up doubt.
docs/research/AUDIT_V2.md is written from it. These tests keep the register honest: only final words, evidence on every row,
every pointer real, nothing left open, and the Markdown page lists every row.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REG = json.loads((ROOT / "docs/knowledge/audit_register.json").read_text(encoding="utf-8"))
DUE = {i["id"]: i for i in json.loads((ROOT / "docs/knowledge/due_list.json").read_text(encoding="utf-8"))["items"]}
ERRATA_TEXT = (ROOT / "docs/research/GROK_ERA_ERRATA.md").read_text(encoding="utf-8")
ERRATA = set(re.findall(r"^### (E-\d{3})\b", ERRATA_TEXT, re.M))
PAGE = (ROOT / "docs/research/AUDIT_V2.md").read_text(encoding="utf-8")

ROW_WORDS = {"DONE", "RECORDED", "ERRATA", "SCHEDULED", "PARKED_WINDOW", "OWNER_DECISION", "SUPERSEDED"}
DOUBT_WORDS = ROW_WORDS | {"ALREADY_FIXED"}
OPEN_WORDS = {"OPEN", "FIX_NOW", "NOT_DONE", "PARTLY", "TODO", "PENDING", ""}
SPECIAL_REFS = {"AUDIT_V2"}  # a document, not a due-list id
OWNED = {"SCHEDULED", "PARKED_WINDOW", "OWNER_DECISION"}


def _ref_ok(ref):
    if re.fullmatch(r"E-\d{3}", ref):
        return ref in ERRATA
    return ref in SPECIAL_REFS or ref in DUE


def test_rows_use_only_final_words():
    bad = [(r["key"], r["disposition"]) for r in REG["rows"] if r["disposition"] not in ROW_WORDS]
    assert not bad, bad
    bad = [(d["id"], d["disposition"]) for d in REG["doubts"] if d["disposition"] not in DOUBT_WORDS]
    assert not bad, bad


def test_nothing_is_left_open():
    for r in REG["rows"] + REG["doubts"]:
        assert r["disposition"] not in OPEN_WORDS, r


def test_row_keys_unique_and_complete():
    keys = [r["key"] for r in REG["rows"]]
    assert len(keys) == len(set(keys)), "duplicate keys"
    assert len(keys) >= 398
    groups = {k.split(":", 1)[0] for k in keys}
    assert groups == {"cards-%d" % i for i in range(1, 10)} | {"recon"}


def test_every_row_has_evidence():
    for r in REG["rows"]:
        assert len(r["evidence"].strip()) >= 20, r["key"]
        assert r["title"].strip(), r["key"]
    for d in REG["doubts"]:
        assert len(d["evidence"].strip()) >= 20, d["id"]
        assert d["topic"].strip(), d["id"]


def test_the_doubts_are_d128_to_d170():
    ids = [d["id"] for d in REG["doubts"]]
    assert ids == ["D%d" % n for n in range(128, 171)]


def test_every_pointer_exists():
    for r in REG["rows"]:
        if r["disposition"] == "SUPERSEDED":
            continue  # its refs name the replacing document in words
        for ref in r["refs"]:
            assert _ref_ok(ref), (r["key"], ref)
    for d in REG["doubts"]:
        for ref in d["refs"]:
            assert _ref_ok(ref), (d["id"], ref)


def test_errata_rows_cite_an_erratum():
    for r in REG["rows"] + REG["doubts"]:
        if r["disposition"] == "ERRATA":
            assert any(re.fullmatch(r"E-\d{3}", x) for x in r["refs"]), r.get("key") or r.get("id")


def test_owned_rows_point_at_the_due_list():
    for r in REG["rows"] + REG["doubts"]:
        if r["disposition"] in OWNED:
            assert any(x in DUE for x in r["refs"]), r.get("key") or r.get("id")


def test_owned_rows_match_the_kind_of_due_item():
    for r in REG["rows"]:
        for x in r["refs"]:
            if x not in DUE:
                continue
            if r["disposition"] == "OWNER_DECISION":
                assert x.startswith("OD-"), (r["key"], x)
            if r["disposition"] == "PARKED_WINDOW":
                assert x.startswith("PW-"), (r["key"], x)


def test_superseded_rows_name_their_replacement():
    for r in REG["rows"]:
        if r["disposition"] == "SUPERSEDED":
            assert r["refs"] and len(r["refs"][0]) > 10, r["key"]


def test_the_audit_born_due_items_are_cited():
    cited = {x for r in REG["rows"] + REG["doubts"] for x in r["refs"]}
    missing = [i for i in ("PW-LIBRARY", "PW-H1", "PW-HL-RX", "OD-READS-WAKES", "OD-C3-PRICE", "OD-CANDIDATE-BOOKS") if i not in cited]
    assert not missing, missing


def test_counts_match_the_rows():
    c = REG["counts"]
    assert c["rows"] == len(REG["rows"])
    assert c["doubts"] == len(REG["doubts"])
    from collections import Counter
    assert c["by_disposition"] == dict(sorted(Counter(r["disposition"] for r in REG["rows"]).items()))
    assert c["doubts_by_disposition"] == dict(sorted(Counter(d["disposition"] for d in REG["doubts"]).items()))


def test_the_page_lists_every_row_and_doubt():
    for r in REG["rows"]:
        assert "`%s`" % r["key"] in PAGE, r["key"]
    for d in REG["doubts"]:
        assert "`%s`" % d["id"] in PAGE, d["id"]
    assert "%d cards and reconstruction items" % len(REG["rows"]) in PAGE


def test_the_page_carries_the_v1_corrections():
    for needle in ("19 closed, 3 won, -$29.58", "3 live paper trades, all lost (-$2.93)", "The 27 rows that shared one reason",
                   "+0.07% in discovery and +0.17% in confirm", "KEEP 22, RE-TEST 5, CONTEXT 28, UNTESTED 3, DUMP 107"):
        assert needle in PAGE, needle
    v1 = json.loads((ROOT / "docs/research/audit_v1.json").read_text(encoding="utf-8"))
    assert len(v1["rows"]) == 165, "audit_v1.json is frozen at 165 rows"
    blanket = [r["id"] for r in v1["rows"] if "August legacy lab" in (r.get("reason") or "")]
    assert len(blanket) == 27
    for i in blanket:
        assert "`%s`" % i in PAGE, i


def test_fix_commit_is_a_real_commit():
    fc = REG["fix_commit"]
    assert re.fullmatch(r"[0-9a-f]{7,40}", fc), fc
    if shutil.which("git") and (ROOT / ".git").exists():
        r = subprocess.run(["git", "cat-file", "-e", fc + "^{commit}"], cwd=ROOT, capture_output=True)
        assert r.returncode == 0, "fix_commit %s is not in this repository" % fc
