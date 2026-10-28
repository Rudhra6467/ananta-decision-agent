"""Mutual fund schemes and their latest NAVs from AMFI (Madhav, 27 Oct 2026: asked about SBI Gold Fund, Ananta "had no data"; the outside review
ranked fund data first: "most Indian retail money is in mutual funds").

  python -m india.mfdata amfi       AMFI's daily NAV file (public) -> bronze/mf/NAVAll_<date>.txt (last 10 kept) and manifests/mf_schemes.json

manifests/mf_schemes.json holds every open scheme once per plan and option: code, name, fund house, category, plan (Direct/Regular), option
(Growth/IDCW), latest NAV and its date. The Ask finds a fund by name here, then fetches that scheme's NAV history on demand (mfapi.in, a free
public mirror of AMFI's history; jarvis/india/lookup.py) to compute returns, SIP returns and the comparison with an index fund.
Expense ratios (TER) are not in this file and AMFI publishes them only through an interactive page, so they are reported as not available; the
gap between a scheme's Direct and Regular plan returns shows the extra yearly cost of the Regular plan (the distributor's commission).
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

from india import paths

URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
KEEP = 10


def _bronze() -> Path:
    d = paths.data_dir() / "bronze" / "mf"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _out() -> Path:
    return paths.manifest_dir() / "mf_schemes.json"


def _plan(s: str) -> str:
    s = s.lower()
    return "Direct" if "direct" in s else "Regular" if "regular" in s else ""


def _option(s: str) -> str:
    s = s.lower()
    if "growth" in s:
        return "Growth"
    if any(k in s for k in ("idcw", "dividend", "payout", "reinvest", "bonus")):
        return "IDCW"
    return ""


def parse(text: str) -> list[dict]:
    """AMFI NAVAll.txt -> one row per scheme code. Section lines carry the type and category ("Open Ended Schemes(Equity Scheme - Large Cap
    Fund)"); a line with no ';' between sections is the fund house; data lines are code;isin;isin;name;plan;option;nav;date (8 fields, the
    2026 layout) or code;isin;isin;name;nav;date (6 fields, the older layout, plan and option inside the name)."""
    rows, typ, cat, amc = [], "", "", ""
    for raw in text.splitlines():
        line = raw.strip().replace("’", "'")
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            m = re.match(r"^(.*?Schemes?)\s*\((.*)\)\s*$", line)
            if m:
                typ, cat = m.group(1).strip(), m.group(2).strip()
            else:
                amc = line
            continue
        f = [x.strip() for x in line.split(";")]
        if len(f) >= 8:
            code, isin1, isin2, name, plan, opt, nav, date = f[:8]
        elif len(f) >= 6:
            code, isin1, isin2, name, nav, date = f[:6]
            plan, opt = name, name
        else:
            continue
        if not code.isdigit():
            continue
        try:
            navf = float(nav)
        except ValueError:
            navf = None
        try:
            d = dt.datetime.strptime(date, "%d-%b-%Y").date().isoformat()
        except ValueError:
            d = None
        rows.append({"code": int(code), "name": name, "amc": amc, "type": typ, "category": cat, "plan": _plan(plan) or _plan(name),
                     "option": _option(opt) or _option(name), "nav": navf, "date": d,
                     "isin": isin1 if isin1 not in ("-", "") else (isin2 if isin2 not in ("-", "") else None)})
    return rows


def amfi(force: bool = False) -> dict:
    import requests

    from india import nse
    today = dt.date.today().strftime("%Y%m%d")
    p = _bronze() / f"NAVAll_{today}.txt"
    note = "kept today's copy"
    if force or not p.exists():
        try:
            r = requests.get(URL, headers=nse.HEADERS, timeout=90, allow_redirects=True)
            if r.status_code != 200 or b";" not in r.content[:300]:
                raise RuntimeError(f"status {r.status_code}")
            p.write_bytes(r.content)
            note = f"fetched {len(r.content)} bytes"
        except Exception as e:  # noqa: BLE001  the last good file stays in use
            old = sorted(_bronze().glob("NAVAll_*.txt"))
            if not old:
                return {"status": "failed", "why": f"{type(e).__name__}: {str(e)[:120]}"}
            p, note = old[-1], f"fetch failed ({type(e).__name__}); using {old[-1].name}"
    for old in sorted(_bronze().glob("NAVAll_*.txt"))[:-KEEP]:
        old.unlink()
    rows = parse(p.read_text(encoding="utf-8", errors="replace"))
    dates = sorted({r["date"] for r in rows if r["date"]})
    out = {"source": URL, "file": p.name, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "latest_nav_date": dates[-1] if dates else None, "schemes": len(rows),
           "note": "every open scheme, one row per plan and option; NAV history and returns are fetched per scheme when asked (mfapi.in)",
           "rows": rows}
    _out().write_text(json.dumps(out, ensure_ascii=False))
    return {"status": "ok", "note": note, "schemes": len(rows), "latest_nav_date": out["latest_nav_date"],
            "direct_growth": sum(1 for r in rows if r["plan"] == "Direct" and r["option"] == "Growth")}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "amfi"
    print(json.dumps(amfi(force="--force" in sys.argv), indent=1))
