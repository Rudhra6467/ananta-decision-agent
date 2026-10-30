"""Phase 2.1 of the reverse-engineering pass (29 Oct 2026): the data layer, checked as one read-only report.

  python -m india.datacheck            manifests/datacheck.json and a plain summary

What it checks (each with a verdict and the numbers):
  1. freshness: when each live input Ananta decides on was last updated (the read model, the universe file, the index closes, the market
     context readings, flows, AMFI NAVs, the IPO list, announcements, deals, the sealed stock candles) against what it should be;
  2. bars: the research bars (gold/bars adj_daily) for one-day jumps above 40% among the 250 most traded names (a missed adjustment looks
     like a jump), duplicate stock-days, non-positive prices, and sessions in the calendar with no bars at all;
  3. the firewall, leak check and integrity results as they stand (not re-run here), with the hits named;
  4. coverage: rows per dataset and the research cut (nothing after 2023-12-29 in the research tables).
Nothing here changes anything.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path

import pandas as pd

from india import paths, sealed

MAN = paths.manifest_dir()
D = paths.data_dir()
TODAY = dt.date.today()


def _mtime(p: Path) -> str | None:
    try:
        return dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return None


def _json(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return default


def freshness() -> list[dict]:
    rows = []

    def add(name, as_of, expect, note=""):
        try:
            age = (TODAY - dt.date.fromisoformat(str(as_of)[:10])).days if as_of else None
        except ValueError:
            age = None
        rows.append({"input": name, "as_of": as_of, "age_days": age, "expected": expect, "ok": (age is not None and age <= expect) if isinstance(expect, int) else None, "note": note})

    rm = _json(D / "readmodel" / "latest.json", {}) or {}
    add("read model (data_through)", rm.get("data_through"), 1, "built nightly; data_through = the last session with a close")
    uni = sorted(glob.glob(str(D / "paper/decisions/????-??-??.universe.json")))
    add("universe file (paper engine)", Path(uni[-1]).name[:10] if uni else None, 1)
    mc = _json(MAN / "market_context.json", {}) or {}
    for k, v in (mc.get("macro") or {}).items():
        add(f"market context: {k}", v.get("as_of"), 7 if k in ("DTWEXBGS", "DEXINUS") else 3, "FRED publishes the dollar index and the rupee with a lag of several days")
    for k in ("india_vix", "rupee_same_day", "flows"):
        add(f"market context: {k}", (mc.get(k) or {}).get("as_of"), 1)
    add("GIFT Nifty", (mc.get("gift_nifty") or {}).get("as_of"), 1, (mc.get("gift_nifty") or {}).get("status") or "no free source")
    ki = sorted(glob.glob(str(D / "sealed" / "kite_index" / "day" / "*.parquet")) + glob.glob(str(D / "silver" / "kite_index" / "day" / "*.parquet")))
    add("index closes (kite_index day files)", _mtime(Path(max(ki, key=os.path.getmtime))) if ki else None, 1, "the newest file's time; the Ask's latest_closes reads these")
    mf = _json(MAN / "mf_schemes.json", {}) or {}
    add("AMFI NAVs", mf.get("as_of") or mf.get("date") or _mtime(MAN / "mf_schemes.json"), 2)
    add("quotebook (every stock, ETF, sector, gold)", _mtime(MAN / "quotebook.json"), 1)
    add("lookup data (TRI benchmarks, IPO list)", _mtime(MAN / "lookupdata.json") if (MAN / "lookupdata.json").exists() else _mtime(MAN / "quotebook_names.json"), 1)
    for name, pat in (("announcements", "silver/announce/*"), ("deals (bulk/block)", "silver/deals/*"), ("FII/DII flows", "silver/flows/*"), ("option recorder", "silver/option_spreads/*")):
        fs = sorted(glob.glob(str(D / pat)))
        add(name, _mtime(Path(fs[-1])) if fs else None, 2)
    try:
        m5 = sealed.metadata("kite_5m", "year=*/part.parquet", "date")
        add("stock 5-minute candles (sealed part)", (m5 or {}).get("last") or (m5 or {}).get("sealed_last"), 1, "filled by india.kite_fill (one-off plan); no nightly top-up job")
    except Exception as e:  # noqa: BLE001
        add("stock 5-minute candles (sealed part)", None, 1, f"metadata unavailable: {type(e).__name__}")
    inv = _json(MAN / "data_inventory.json", {}) or {}
    add("data inventory manifest", (inv.get("at") or "")[:10], 1, "india.inventory run; lineage reads it, so a stale inventory reads as stale data")
    return rows


def bars() -> dict:
    p = paths.gold() / "bars" / "adj_daily.parquet"
    df = pd.read_parquet(p, columns=["sid", "date", "o", "h", "l", "c", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    out = {"rows": int(len(df)), "first": str(df["date"].min())[:10], "last": str(df["date"].max())[:10], "sids": int(df["sid"].nunique())}
    out["after_cut"] = int((df["date"] >= "2024-01-01").sum())
    out["dupes"] = int(df.duplicated(["sid", "date"]).sum())
    out["nonpositive"] = int(((df[["o", "h", "l", "c"]] <= 0).any(axis=1)).sum())
    out["high_below_low"] = int((df["h"] < df["l"]).sum())
    u = pd.read_parquet(paths.gold() / "universe" / "u_liq_in.parquet", columns=["sid", "date", "rank"])
    u["date"] = pd.to_datetime(u["date"])
    liq = u[u["rank"] <= 250][["sid", "date"]]
    d = df.merge(liq, on=["sid", "date"], how="inner").sort_values(["sid", "date"])
    d["r"] = d.groupby("sid")["c"].pct_change()
    big = d[d["r"].abs() > 0.40]
    out["jumps_over_40pct_liquid"] = int(len(big))
    out["jumps_by_year"] = {int(k): int(v) for k, v in big.groupby(big["date"].dt.year).size().items()}
    ratio = 1 + big["r"]
    out["jumps_split_like"] = int(sum(any(abs(x - n) < 0.08 * n or abs(x - 1 / n) < 0.08 / n for n in (2, 3, 4, 5, 8, 10, 13, 20)) for x in ratio))
    try:
        fl = pd.read_parquet(paths.gold() / "ca_flags" / "ca_flags.parquet", columns=["sid", "date"])
        fl["date"] = pd.to_datetime(fl["date"])
        out["jumps_with_a_ca_flag_same_day"] = int(len(big.merge(fl, on=["sid", "date"])))
    except Exception:  # noqa: BLE001
        out["jumps_with_a_ca_flag_same_day"] = None
    out["jumps_sample"] = [{"sid": r.sid, "date": str(r.date)[:10], "move": round(float(r.r), 3)} for r in big.sort_values("r", key=abs, ascending=False).head(12).itertuples()]
    cal = pd.read_parquet(D / "silver" / "calendar" / "calendar.parquet") if (D / "silver" / "calendar" / "calendar.parquet").exists() else None
    if cal is not None:
        dc = [c for c in cal.columns if "date" in c.lower()]
        if dc:
            if "is_trading_day" in cal.columns:
                cal = cal[cal["is_trading_day"].astype(bool)]
            sess = pd.to_datetime(cal[dc[0]])
            sess = sess[(sess >= "2000-01-01") & (sess <= "2023-12-29")]
            have = set(df["date"].dt.date)
            missing = [str(x.date()) for x in sess if x.date() not in have]
            out["sessions_without_bars"] = len(missing)
            out["sessions_without_bars_sample"] = missing[:10]
    return out


def checks_as_they_stand() -> dict:
    fw = _json(MAN / "firewall.json", {}) or {}
    lk = _json(MAN / "leakcheck.json", {}) or {}
    ig = _json(MAN / "integrity.json", {}) or {}
    ln = _json(MAN / "lineage.json", {}) or {}
    return {"firewall": {k: v.get("ok") for k, v in fw.items() if isinstance(v, dict)}, "firewall_hits": (fw.get("static_scan") or {}).get("hits"),
            "leakcheck": {k: v.get("ok") for k, v in lk.items() if isinstance(v, dict)}, "leakcheck_at": lk.get("_at"),
            "integrity": {k: (v.get("ok") if isinstance(v, dict) else v) for k, v in ig.items()}, "lineage_mismatches": ln.get("mismatches"), "lineage_built": ln.get("built_at")}


def coverage() -> dict:
    inv = _json(MAN / "data_inventory.json", {}) or {}
    ds = inv.get("datasets") or {}
    return {k: {x: v.get(x) for x in ("rows", "first", "last", "sealed_last")} for k, v in ds.items()}


def run() -> dict:
    out = {"at": dt.datetime.now().isoformat(timespec="seconds"), "freshness": freshness(), "bars": bars(), "checks": checks_as_they_stand(), "coverage": coverage()}
    stale = [r for r in out["freshness"] if r["ok"] is False]
    b = out["bars"]
    out["summary"] = {"stale_inputs": [f"{r['input']} ({r['as_of']}, {r['age_days']} days)" for r in stale],
                      "bars_issues": {k: b.get(k) for k in ("after_cut", "dupes", "nonpositive", "high_below_low", "jumps_over_40pct_liquid", "sessions_without_bars")},
                      "firewall_ok": all(v for v in out["checks"]["firewall"].values()), "leakcheck_ok": all(v for v in out["checks"]["leakcheck"].values()),
                      "lineage_mismatches": out["checks"]["lineage_mismatches"]}
    (MAN / "datacheck.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    o = run()
    print(json.dumps(o["summary"], indent=1, default=str))
    for r in o["freshness"]:
        print(f"  {r['input']:<48} {str(r['as_of'])[:16]:<17} age {r['age_days']}  {'ok' if r['ok'] else ('STALE' if r['ok'] is False else '?')}  {r['note']}")
    print("bars:", {k: v for k, v in o["bars"].items() if k != "jumps_sample"})
    print("jumps:", o["bars"].get("jumps_sample"))
