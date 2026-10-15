"""Review #29 (Oct 15): the registration is frozen, and its pre-decided effect on the measured-edge table is applied by code."""
import json
from pathlib import Path


def test_the_registration_is_the_one_madhav_approved():
    from src.research import review29

    assert review29.registration_ok()                     # REVIEW_29.md unchanged since approval (sha256 in the code)


def test_a_later_review_supersedes_its_cell(tmp_path):
    from jarvis.service import ev

    key, f = ("H07", "CLOSED", "A"), tmp_path / "r.json"
    cell = {"rule": "H07", "state": "CLOSED", "tier": "A", "verdict": "PASS", "expected_excess_pct": 6.34, "DISCOVERY": {}, "CONFIRM": {}}
    f.write_text(json.dumps({"cells": [cell]}))
    assert ev._later(f, key, "r")["passes"] is True
    f.write_text(json.dumps({"cells": [{**cell, "verdict": "FAIL"}]}))
    assert ev._later(f, key, "r")["passes"] is False      # FAIL: the cell's value goes to 0
    f.write_text(json.dumps({"cells": [{**cell, "verdict": "INSUFFICIENT"}]}))
    assert ev._later(f, key, "r") is None                 # INSUFFICIENT: nothing changes
    f.write_text(json.dumps({"stopped": "coverage short", "cells": []}))
    assert ev._later(f, key, "r") is None                 # a stopped run is no result


def test_the_live_value_is_review_29s():
    from jarvis.service import ev

    d = json.loads((Path(ev.__file__).resolve().parents[2] / "docs" / "research" / "review29.json").read_text())
    c = next(x for x in d["cells"] if x["state"] == "CLOSED")
    assert ev.value("H07", "CLOSED", "A") == (c["expected_excess_pct"] if c["verdict"] in ("PASS", "WEAKENED") else 0.0)
    assert ev.value("H07", "OPEN", "A") == 0.0           # the dial-open cell has no measured edge
    assert any(r["source"] == "review #29" for r in ev.table())
