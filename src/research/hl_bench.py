"""External benchmark: how other real traders/systems behave, versus Ananta.

Operator 2026-09-29: "Go with some random active accounts from multiple sources.
What we are doing is testing our system performance with other systems in order
to find what's working and what's not working in our system and modify it."

Laws kept
---------
* Reference, never teacher: nothing here produces a signal, a copy trade or a TAKE.
  Output is diagnostics for the operator (Law: external trades are reference only).
* Research-time only. The decision path never reads this.
* Set B discipline: every trade is stamped DESIGN (entry < 2026-08-01Z) or HOLDOUT.
  Design comparisons use DESIGN only; HOLDOUT is kept for the final exam.
* Survivorship: three sources, sampled at random within strata, fixed seed.
    A. leaderboard  - winners / middle / losers by all-time PnL, active last 30d
    B. live tape    - random wallets seen in recent trades on the 10 lab coins
    C. vaults       - public automated strategies (open, funded, >1y old)
* Market makers / HFT are excluded and counted (turnover filter), because their
  game is not ours.
* Public data only (Hyperliquid info API + stats-data). Wallets are pseudonymous;
  results are aggregated by behaviour, never published per person.

Run on a machine that can reach api.hyperliquid.xyz:
    python -m src.research.hl_bench collect --out ~/ananta_runs/hl_bench
    python -m src.research.hl_bench analyze --out ~/ananta_runs/hl_bench
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import statistics as st
import time
import urllib.request
from pathlib import Path
from typing import Any

VERSION = "hl.bench.v1"
INFO = "https://api.hyperliquid.xyz/info"
LEADERBOARD = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
VAULTS = "https://stats-data.hyperliquid.xyz/Mainnet/vaults"
LAB10 = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
DESIGN_END_MS = 1785542400 * 1000  # 2026-08-01T00:00Z, research-law discovery end
DAY_MS = 86_400_000
SEED = 20260929
MAX_FILLS_PER_ACCOUNT = 40_000
HFT_TURNOVER = 300.0  # monthly volume / account value above this = market maker / HFT


# ---------------------------------------------------------------------------
# HTTP (gentle: the public API is rate limited)
# ---------------------------------------------------------------------------
_last = [0.0]


def _pace(min_gap: float = 1.2) -> None:
    gap = time.time() - _last[0]
    if gap < min_gap:
        time.sleep(min_gap - gap)
    _last[0] = time.time()


def post(body: dict, retries: int = 4) -> Any:
    for i in range(retries):
        _pace()
        try:
            req = urllib.request.Request(INFO, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception:  # noqa: BLE001
            if i == retries - 1:
                raise
            time.sleep(10 * (i + 1))


def get(url: str) -> Any:
    _pace()
    return json.load(urllib.request.urlopen(url, timeout=120))


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------
def _window(row: dict, name: str) -> dict:
    for w, v in row.get("windowPerformances") or []:
        if w == name:
            return v
    return {}


def sample_leaderboard(rng: random.Random, per_bucket: int) -> tuple[list[dict], dict]:
    rows = get(LEADERBOARD)
    rows = rows.get("leaderboardRows") if isinstance(rows, dict) else rows
    active, hft = [], 0
    for r in rows:
        av = _f(r.get("accountValue"))
        mv = _f(_window(r, "month").get("vlm"))
        if mv <= 0 or av < 1_000:  # inactive or dust
            continue
        if av > 0 and mv / av > HFT_TURNOVER:
            hft += 1
            continue
        active.append({"address": r["ethAddress"], "account_value": av, "pnl_all": _f(_window(r, "allTime").get("pnl")),
                       "vlm_month": mv, "roi_all": _f(_window(r, "allTime").get("roi"))})
    active.sort(key=lambda x: x["pnl_all"])
    n = len(active)
    thirds = {"LB_LOSER": active[: n // 3], "LB_MIDDLE": active[n // 3: 2 * n // 3], "LB_WINNER": active[2 * n // 3:]}
    picks = []
    for label, pool in thirds.items():
        for x in rng.sample(pool, min(per_bucket, len(pool))):
            picks.append({**x, "source": label})
    return picks, {"leaderboard_rows": len(rows), "active_non_hft": n, "excluded_hft": hft}


def sample_tape(rng: random.Random, k: int) -> tuple[list[dict], dict]:
    seen: dict[str, str] = {}
    for coin in LAB10:
        try:
            for t in post({"type": "recentTrades", "coin": coin}) or []:
                for u in t.get("users") or []:
                    seen.setdefault(u.lower(), coin)
        except Exception:  # noqa: BLE001
            continue
    addrs = sorted(seen)
    rng.shuffle(addrs)
    return [{"address": a, "source": "TAPE", "seen_on": seen[a]} for a in addrs[: k * 3]], {"tape_unique_wallets": len(addrs)}


def sample_vaults(rng: random.Random, k: int) -> tuple[list[dict], dict]:
    vs = get(VAULTS)
    now = time.time() * 1000
    ok = []
    for v in vs:
        s = v.get("summary") or {}
        if s.get("isClosed") or _f(s.get("tvl")) < 10_000:
            continue
        if now - _f(s.get("createTimeMillis")) < 365 * DAY_MS:
            continue
        ok.append({"address": s["vaultAddress"], "source": "VAULT", "name": s.get("name"), "tvl": _f(s.get("tvl")), "apr": _f(v.get("apr"))})
    ok.sort(key=lambda x: x["apr"])
    n = len(ok)
    per = max(1, k // 3)
    picks = []
    for part in (ok[: n // 3], ok[n // 3: 2 * n // 3], ok[2 * n // 3:]):
        picks += rng.sample(part, min(per, len(part)))
    return picks, {"vaults_total": len(vs), "vaults_eligible": n}


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
def db(out: Path) -> sqlite3.Connection:
    out.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(out / "hl_bench.sqlite"))
    con.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (address TEXT PRIMARY KEY, source TEXT, meta_json TEXT, status TEXT);
    CREATE TABLE IF NOT EXISTS portfolio (address TEXT PRIMARY KEY, json TEXT);
    CREATE TABLE IF NOT EXISTS fills (address TEXT, tid INTEGER, time INTEGER, coin TEXT, side TEXT, px REAL, sz REAL,
        start_pos REAL, dir TEXT, closed_pnl REAL, fee REAL, PRIMARY KEY (address, tid));
    CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
    """)
    return con


def fetch_account(con: sqlite3.Connection, address: str, since_ms: int) -> dict:
    port = post({"type": "portfolio", "user": address})
    con.execute("INSERT OR REPLACE INTO portfolio VALUES (?,?)", (address, json.dumps(port)))
    start, total, now = since_ms, 0, int(time.time() * 1000)
    while start < now and total < MAX_FILLS_PER_ACCOUNT:
        batch = post({"type": "userFillsByTime", "user": address, "startTime": start, "endTime": now}) or []
        if not batch:
            break
        con.executemany("INSERT OR IGNORE INTO fills VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            (address, int(f["tid"]), int(f["time"]), f["coin"], f["side"], _f(f["px"]), _f(f["sz"]),
             _f(f.get("startPosition")), f.get("dir"), _f(f.get("closedPnl")), _f(f.get("fee"))) for f in batch])
        total += len(batch)
        last = max(int(f["time"]) for f in batch)
        if len(batch) < 2000 or last <= start:
            break
        start = last  # same-ms duplicates are dropped by the (address, tid) key
    con.commit()
    return {"fills": total, "truncated": total >= MAX_FILLS_PER_ACCOUNT}


def collect(out: Path, per_bucket: int = 10, tape_k: int = 20, vault_k: int = 15, years: float = 2.0) -> dict:
    rng = random.Random(SEED)
    con = db(out)
    if not con.execute("SELECT 1 FROM accounts LIMIT 1").fetchone():
        lb, lb_info = sample_leaderboard(rng, per_bucket)
        tape, tape_info = sample_tape(rng, tape_k)
        vaults, v_info = sample_vaults(rng, vault_k)
        chosen = {x["address"].lower(): x for x in lb + vaults}
        for x in tape:  # tape extras are trimmed after activity check below
            chosen.setdefault(x["address"].lower(), x)
        for a, x in chosen.items():
            con.execute("INSERT OR IGNORE INTO accounts VALUES (?,?,?,?)", (a, x["source"], json.dumps(x), "PENDING"))
        con.execute("INSERT OR REPLACE INTO meta VALUES ('sampling', ?)", (json.dumps({**lb_info, **tape_info, **v_info, "seed": SEED, "version": VERSION}),))
        con.commit()
    since = int(time.time() * 1000 - years * 365.25 * DAY_MS)
    tape_kept = con.execute("SELECT count(*) FROM accounts WHERE source='TAPE' AND status='DONE'").fetchone()[0]
    con.execute("UPDATE accounts SET status='PENDING' WHERE status LIKE 'ERROR:%'")  # retry rate-limited ones
    con.commit()
    for a, src in con.execute("SELECT address, source FROM accounts WHERE status='PENDING' ORDER BY source, address").fetchall():
        if src == "TAPE" and tape_kept >= tape_k:
            con.execute("UPDATE accounts SET status='SKIPPED_QUOTA' WHERE address=?", (a,))
            continue
        try:
            r = fetch_account(con, a, since)
            status = "DONE" if r["fills"] else "NO_FILLS"
            if src == "TAPE" and status == "DONE":
                tape_kept += 1
            if r["truncated"]:
                status = "DONE_TRUNCATED"
        except Exception as e:  # noqa: BLE001
            status = f"ERROR:{str(e)[:80]}"
        con.execute("UPDATE accounts SET status=? WHERE address=?", (status, a))
        con.commit()
        print(f"  {src:<10} {a[:10]}… {status}", flush=True)
    summary = dict(con.execute("SELECT status, count(*) FROM accounts GROUP BY status").fetchall())
    con.close()
    return summary


# ---------------------------------------------------------------------------
# Trade reconstruction + behaviour metrics
# ---------------------------------------------------------------------------
def round_trips(fills: list[tuple]) -> list[dict]:
    """fills: (time, coin, side, px, sz, start_pos, closed_pnl, fee) sorted by time.
    A trip = a coin position going from flat to flat. Flips close one trip and open the next."""
    trips: list[dict] = []
    open_: dict[str, dict] = {}
    for t, coin, side, px, sz, start_pos, cpnl, fee in fills:
        sgn = 1.0 if side == "B" else -1.0
        after = start_pos + sgn * sz
        cur = open_.get(coin)
        if cur is None and abs(start_pos) < 1e-12:
            cur = open_[coin] = {"coin": coin, "open_ms": t, "dir": "LONG" if sgn > 0 else "SHORT", "entry_px": px,
                                 "pnl": 0.0, "fees": 0.0, "max_notional": 0.0, "fills": 0}
        if cur is None:  # position opened before our window: cannot score it honestly
            continue
        cur["pnl"] += cpnl
        cur["fees"] += fee
        cur["fills"] += 1
        cur["max_notional"] = max(cur["max_notional"], abs(after) * px)
        crossed = (start_pos > 0 > after) or (start_pos < 0 < after)
        if abs(after) < 1e-12 or crossed:
            cur.update(close_ms=t, exit_px=px, net=cur["pnl"] - cur["fees"], hold_h=(t - cur["open_ms"]) / 3_600_000)
            trips.append(cur)
            open_.pop(coin, None)
            if crossed:
                open_[coin] = {"coin": coin, "open_ms": t, "dir": "LONG" if after > 0 else "SHORT", "entry_px": px,
                               "pnl": 0.0, "fees": 0.0, "max_notional": abs(after) * px, "fills": 1}
    return trips


def _pct(xs: list[float], q: float):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def behaviour(trips: list[dict]) -> dict[str, Any]:
    if not trips:
        return {"trips": 0}
    net = [t["net"] for t in trips]
    wins = [x for x in net if x > 0]
    losses = [-x for x in net if x <= 0]
    holds = [t["hold_h"] for t in trips]
    lab = [t for t in trips if t["coin"] in LAB10]
    span_w = max(1.0, (max(t["close_ms"] for t in trips) - min(t["open_ms"] for t in trips)) / (7 * DAY_MS))
    gross = sum(t["pnl"] for t in trips)
    fees = sum(t["fees"] for t in trips)
    return {
        "trips": len(trips),
        "trips_per_week": round(len(trips) / span_w, 2),
        "win_rate": round(len(wins) / len(trips), 3),
        "avg_win": round(st.mean(wins), 2) if wins else 0.0,
        "avg_loss": round(st.mean(losses), 2) if losses else 0.0,
        "payoff": round(st.mean(wins) / st.mean(losses), 2) if wins and losses and st.mean(losses) > 0 else None,
        "profit_factor": round(sum(wins) / sum(losses), 2) if losses and sum(losses) > 0 else None,
        "net": round(sum(net), 2),
        "fee_share_of_gross": round(fees / abs(gross), 3) if gross else None,
        "hold_h_median": round(_pct(holds, 0.5), 2),
        "hold_h_p90": round(_pct(holds, 0.9), 2),
        "hold_win_median": round(_pct([t["hold_h"] for t in trips if t["net"] > 0], 0.5) or 0, 2),
        "hold_loss_median": round(_pct([t["hold_h"] for t in trips if t["net"] <= 0], 0.5) or 0, 2),
        "long_share": round(sum(1 for t in trips if t["dir"] == "LONG") / len(trips), 3),
        "lab10_share": round(len(lab) / len(trips), 3),
        "coins": len({t["coin"] for t in trips}),
        "largest_loss_share": round(max(losses) / sum(losses), 3) if losses else None,
    }


def perf_windows(portfolio: list) -> dict[str, Any]:
    """PnL over the last 1y and 2y from the account's own allTime pnl history."""
    hist = {}
    for name, data in portfolio or []:
        if name == "allTime":
            hist = data
    pnl = [(int(t), _f(v)) for t, v in hist.get("pnlHistory") or []]
    av = [(int(t), _f(v)) for t, v in hist.get("accountValueHistory") or []]
    if not pnl:
        return {}
    now = pnl[-1][0]

    def at(series, ts):
        prev = None
        for t, v in series:
            if t > ts:
                break
            prev = v
        return prev

    out = {"pnl_all": round(pnl[-1][1], 2), "history_days": round((now - pnl[0][0]) / DAY_MS)}
    for label, days in (("1y", 365), ("2y", 730)):
        base = at(pnl, now - days * DAY_MS)
        out[f"pnl_{label}"] = round(pnl[-1][1] - base, 2) if base is not None else None
        eq = at(av, now - days * DAY_MS)
        out[f"equity_{label}_ago"] = round(eq, 2) if eq is not None else None
    out["equity_now"] = round(av[-1][1], 2) if av else None
    return out


def analyze(out: Path) -> dict[str, Any]:
    con = db(out)
    accts = con.execute("SELECT address, source, meta_json, status FROM accounts WHERE status LIKE 'DONE%'").fetchall()
    rows = []
    for a, src, meta, status in accts:
        fills = con.execute("SELECT time, coin, side, px, sz, start_pos, closed_pnl, fee FROM fills WHERE address=? ORDER BY time, tid", (a,)).fetchall()
        trips = round_trips(fills)
        design = [t for t in trips if t["open_ms"] < DESIGN_END_MS]
        holdout = [t for t in trips if t["open_ms"] >= DESIGN_END_MS]
        port = json.loads((con.execute("SELECT json FROM portfolio WHERE address=?", (a,)).fetchone() or ["[]"])[0])
        rows.append({"id": f"{src}:{a[:8]}", "source": src, "truncated": status == "DONE_TRUNCATED",
                     "perf": perf_windows(port), "design": behaviour(design), "holdout": behaviour(holdout)})
    con.close()
    # winners vs losers on DESIGN behaviour, by the account's own 1y result
    scored = [r for r in rows if r["design"].get("trips", 0) >= 10 and (r["perf"].get("pnl_1y") is not None)]
    good = [r for r in scored if r["perf"]["pnl_1y"] > 0]
    bad = [r for r in scored if r["perf"]["pnl_1y"] <= 0]
    keys = ["win_rate", "payoff", "profit_factor", "hold_h_median", "hold_win_median", "hold_loss_median", "trips_per_week", "fee_share_of_gross", "long_share", "largest_loss_share"]

    def med(group, k):
        xs = [g["design"].get(k) for g in group if isinstance(g["design"].get(k), (int, float))]
        return round(st.median(xs), 3) if xs else None

    contrast = {k: {"profitable_1y": med(good, k), "unprofitable_1y": med(bad, k)} for k in keys}
    report = {"version": VERSION, "accounts": len(rows), "scored": len(scored), "profitable_1y": len(good), "unprofitable_1y": len(bad),
              "contrast_design_period": contrast, "accounts_detail": rows}
    (out / "hl_bench_report.json").write_text(json.dumps(report, indent=2, default=str))
    return report


def ananta_behaviour(replay_dir: Path) -> dict[str, Any]:
    """Same metrics for Ananta's own replay trades (lab/mtf_replay output with per-trade rows)."""
    groups: dict[str, list[dict]] = {}
    for p in sorted(Path(replay_dir).glob("*_*.json")):
        if p.name == "config_snapshot.json":
            continue
        c = json.loads(p.read_text())
        for t in c.get("trades") or []:
            if t.get("partial"):
                continue
            groups.setdefault(f"ananta_{t['strategy']}_{c['tf']}", []).append(t)
    out = {}
    for k, ts in groups.items():
        net = [float(t["pnl"]) for t in ts]
        wins = [x for x in net if x > 0]
        losses = [-x for x in net if x <= 0]
        holds = [float(t["hold_hours"]) for t in ts]
        out[k] = {
            "trips": len(ts),
            "win_rate": round(len(wins) / len(ts), 3),
            "payoff": round(st.mean(wins) / st.mean(losses), 2) if wins and losses else None,
            "profit_factor": round(sum(wins) / sum(losses), 2) if losses and sum(losses) > 0 else None,
            "hold_h_median": round(_pct(holds, 0.5), 2),
            "hold_win_median": round(_pct([float(t["hold_hours"]) for t in ts if float(t["pnl"]) > 0], 0.5) or 0, 2),
            "hold_loss_median": round(_pct([float(t["hold_hours"]) for t in ts if float(t["pnl"]) <= 0], 0.5) or 0, 2),
            "avg_mfe_pct": round(st.mean(float(t["mfe_pct"] or 0) for t in ts), 2),
            "avg_mae_pct": round(st.mean(float(t["mae_pct"] or 0) for t in ts), 2),
            "exits": _count_list(t.get("exit_reason") for t in ts),
            "regimes": _count_list(t.get("regime_at_entry") for t in ts),
        }
    return out


def _count_list(xs) -> dict[str, int]:
    d: dict[str, int] = {}
    for x in xs:
        d[str(x)] = d.get(str(x), 0) + 1
    return dict(sorted(d.items(), key=lambda kv: -kv[1]))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "analyze"])
    ap.add_argument("--out", default=str(Path.home() / "ananta_runs" / "hl_bench"))
    ap.add_argument("--ananta", default=str(Path.home() / "ananta_runs" / "mtf_replay_v2"))
    a = ap.parse_args(argv)
    out = Path(a.out).expanduser()
    if a.cmd == "collect":
        print(json.dumps(collect(out), indent=2))
    else:
        r = analyze(out)
        if Path(a.ananta).expanduser().exists():
            r["ananta"] = ananta_behaviour(Path(a.ananta).expanduser())
            (out / "hl_bench_report.json").write_text(json.dumps(r, indent=2, default=str))
        print(json.dumps({k: v for k, v in r.items() if k != "accounts_detail"}, indent=2))


if __name__ == "__main__":
    main()
