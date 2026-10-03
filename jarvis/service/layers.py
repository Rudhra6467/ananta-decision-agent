"""The layer map (docs/knowledge/layers.json): every part of Ananta with its layer, what it depends on, what it feeds,
its status and evidence, and whether it may act. Code asks `allowed(id)` before letting a component act; Ask Ananta and
the app use `board()` and `component(id)` to explain how the parts fit together.
"""
from __future__ import annotations

import json
from pathlib import Path

_CACHE: dict = {}


def load(base=None) -> dict:
    from jarvis.service.core import docs_dir

    p = docs_dir(base or Path(".")) / "knowledge" / "layers.json"
    key = (str(p), p.stat().st_mtime if p.exists() else 0)
    if _CACHE.get("key") != key:
        _CACHE.update(key=key, map=json.loads(p.read_text()) if p.exists() else {"components": [], "layers": []})
    return _CACHE["map"]


def _by_id(m: dict) -> dict:
    return {c["id"]: c for c in m["components"]}


def allowed(cid: str, base=None) -> bool:
    """The switch: a component may act only if the map says so (unknown components may not)."""
    c = _by_id(load(base)).get(cid)
    return bool(c and c.get("acts") and c.get("status") not in ("DROPPED", "PLANNED"))


def _walk(m: dict, start: str, key: str) -> list[str]:
    by, seen, todo = _by_id(m), [], [start]
    while todo:
        x = todo.pop()
        for y in by.get(x, {}).get(key, []):
            if y not in seen and y != start:
                seen.append(y)
                todo.append(y)
    return seen


def component(cid: str, base=None) -> dict | None:
    m = load(base)
    by = _by_id(m)
    c = by.get(cid.upper())
    if not c:
        q = cid.lower()
        c = next((x for x in m["components"] if q in x["name"].lower()), None)
    if not c:
        return None
    lname = {l["n"]: l["name"] for l in m["layers"]}
    users = [x["id"] for x in m["components"] if c["id"] in x.get("depends_on", [])]
    return {**c, "layer_name": lname.get(c["layer"]), "used_by": users,
            "everything_it_rests_on": _walk(m, c["id"], "depends_on"),
            "everything_that_would_feel_a_failure": _walk(m, c["id"], "feeds")}


def board(base=None) -> dict:
    m = load(base)
    rows = []
    for l in m["layers"]:
        cs = [c for c in m["components"] if c["layer"] == l["n"]]
        rows.append({**l, "components": [{k: c.get(k) for k in ("id", "name", "status", "acts", "regime", "evidence")} for c in cs],
                     "counts": {s: sum(1 for c in cs if c["status"] == s) for s in {c["status"] for c in cs}}})
    return {"layers": rows, "gaps": m.get("gaps", []), "meaning": m.get("meaning", {}), "updated": m.get("updated")}
