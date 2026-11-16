"""What India's AI calls cost (16 Nov 2026, audit repair 7, G-67: "India cannot say what it costs"). Its background calls (the morning view's
writer and reviewer, the shadow trader, the net notes, the nightly replay and its grader, the mind) kept no cost record and had no budget, and
an India answer was priced as fresh tokens only, so every cached token counted as free.

One line per call in reports/ai_costs.jsonl of the India data folder: when, which job, which model, the tokens (fresh, cache write, cache read,
out) and the dollars, priced from the crypto Ask's own table (jarvis/service/ask.py MODELS: one owner for the prices). `month()` adds them up
by job; `price()` is what the India answer uses too. Writing a line never stops the call it records."""
from __future__ import annotations

import json
import time
from pathlib import Path

from jarvis.india.selfparts import INDIA   # the India data folder, from the module the firewall's allowlist names

LOG = INDIA / "reports" / "ai_costs.jsonl"


def _rates(model: str) -> tuple[float, float, float]:
    """(input $/M, output $/M, cache-read share of input) for a model id, from the crypto Ask's table; Sonnet's when it is not found."""
    try:
        from jarvis.service.ask import MODELS
    except Exception:  # noqa: BLE001
        MODELS = {}
    m = str(model or "").lower()
    key = "haiku" if "haiku" in m else "opus" if "opus" in m else "sonnet"
    row = MODELS.get(key) or {"price": (2.0, 10.0), "cache": 0.1}
    pin, pout = row["price"]
    return float(pin), float(pout), float(row.get("cache", 0.1))


def usage_of(r: dict) -> dict:
    """The token counts from an Anthropic reply (its 'usage'), or from India's own usage dict (in, out, cache_read, cache_write)."""
    u = (r or {}).get("usage") if isinstance(r, dict) and "usage" in r else r or {}
    return {"in": int(u.get("input_tokens", u.get("in", 0)) or 0), "out": int(u.get("output_tokens", u.get("out", 0)) or 0),
            "cache_read": int(u.get("cache_read_input_tokens", u.get("cache_read", 0)) or 0),
            "cache_write": int(u.get("cache_creation_input_tokens", u.get("cache_write", 0)) or 0)}


def price(model: str, usage: dict) -> float:
    """Dollars for one call: fresh input, cache writes at 1.25 x input, cache reads at the model's cache share, output."""
    pin, pout, cache = _rates(model)
    u = usage_of(usage)
    return round((u["in"] * pin + u["cache_write"] * pin * 1.25 + u["cache_read"] * pin * cache + u["out"] * pout) / 1e6, 6)


def record(job: str, model: str, reply_or_usage: dict, log: Path | None = None, now: float | None = None) -> float:
    """Write one call's line; returns its dollars. Never raises."""
    try:
        u = usage_of(reply_or_usage)
        usd = price(model, u)
        p = log or LOG
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as f:
            f.write(json.dumps({"t": int(now or time.time()), "job": job, "model": model, **u, "usd": usd}) + "\n")
        return usd
    except Exception:  # noqa: BLE001
        return 0.0


def month(log: Path | None = None, now: float | None = None) -> dict:
    """This calendar month's India AI spend, by job (UTC)."""
    now = now or time.time()
    start = time.strftime("%Y-%m", time.gmtime(now))
    out: dict = {"month": start, "usd": 0.0, "calls": 0, "by_job": {}}
    try:
        lines = (log or LOG).read_text().splitlines()
    except OSError:
        return out
    for x in lines:
        try:
            r = json.loads(x)
        except ValueError:
            continue
        if time.strftime("%Y-%m", time.gmtime(int(r.get("t") or 0))) != start:
            continue
        out["usd"] += float(r.get("usd") or 0)
        out["calls"] += 1
        j = out["by_job"].setdefault(r.get("job") or "?", {"usd": 0.0, "calls": 0})
        j["usd"] += float(r.get("usd") or 0)
        j["calls"] += 1
    out["usd"] = round(out["usd"], 4)
    for v in out["by_job"].values():
        v["usd"] = round(v["usd"], 4)
    return out
