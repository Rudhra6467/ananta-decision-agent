"""The owner's manual paper book, the decision journal, and research jobs.

Manual book: paper orders the owner asks Ananta to prepare ("buy $300 of ETH"). They live in their own book, separate from the
Explorer and the T3 portfolio, so the agent's evidence is never mixed with the owner's calls (and the two can be compared).
Fills at the current price with NDAX market costs (0.20% fee + the coin's half-spread). Optional stop / target are checked
every 15 minutes. Paper only: nothing here can reach an exchange.

Decision journal: the owner's reasons for manual orders and portfolio decisions, kept for later evaluation.
Research jobs: longer checks Ananta can start when asked (now: the reconstruction), with a phone note when done.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Callable

START_CASH = 1000.0
FEE = 0.0020
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
MAX_ORDER_USD = 1000.0


class Manual:
    def __init__(self, db, now: Callable[[], float] = time.time):
        self.db, self.now = db, now
        db.executescript("""
            CREATE TABLE IF NOT EXISTS manual_fills (id TEXT PRIMARY KEY, t INTEGER, coin TEXT, side TEXT, usd REAL, units REAL, px REAL,
                cost REAL, reason TEXT, by TEXT, trigger TEXT);
            CREATE TABLE IF NOT EXISTS manual_orders (coin TEXT PRIMARY KEY, stop REAL, target REAL, t INTEGER);
            CREATE TABLE IF NOT EXISTS journal (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, ref TEXT, text TEXT, by TEXT);
            CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, status TEXT, result TEXT, done_t INTEGER, by TEXT);
        """)
        db.commit()

    # ---- book ----
    def state(self, px: dict[str, float] | None = None) -> dict:
        px = px or {}
        cash, units, cost_basis, costs, realized = START_CASH, {}, {}, 0.0, 0.0
        for coin, side, usd, u, p, c in self.db.execute("SELECT coin, side, usd, units, px, cost FROM manual_fills ORDER BY t, rowid"):
            costs += c
            if side == "BUY":
                cash -= usd + c
                units[coin] = units.get(coin, 0.0) + u
                cost_basis[coin] = cost_basis.get(coin, 0.0) + usd + c
            else:
                held = units.get(coin, 0.0)
                frac = min(1.0, u / held) if held else 0.0
                basis = cost_basis.get(coin, 0.0) * frac
                cash += usd - c
                realized += usd - c - basis
                units[coin] = held - u
                cost_basis[coin] = cost_basis.get(coin, 0.0) - basis
                if units[coin] * p < 0.01:
                    units.pop(coin)
                    cost_basis.pop(coin, None)
        stops = {c: (s, t) for c, s, t in self.db.execute("SELECT coin, stop, target FROM manual_orders")}
        pos = []
        for c, u in units.items():
            val = u * px.get(c, 0.0) if c in px else None
            pos.append({"coin": c, "units": u, "value": round(val, 2) if val is not None else None, "cost": round(cost_basis.get(c, 0.0), 2),
                        "pnl": round(val - cost_basis.get(c, 0.0), 2) if val is not None else None,
                        "stop": (stops.get(c) or (None, None))[0], "target": (stops.get(c) or (None, None))[1]})
        eq = cash + sum(p["value"] or 0 for p in pos)
        return {"start": START_CASH, "cash": round(cash, 2), "equity": round(eq, 2), "return_pct": round(100 * (eq / START_CASH - 1), 2),
                "realized": round(realized, 2), "costs": round(costs, 2), "positions": pos}

    def validate(self, p: dict, px: dict[str, float]) -> dict:
        side = str(p.get("side", "")).lower()
        coin = str(p.get("coin") or "").upper().replace("/USD", "")
        if side not in ("buy", "sell"):
            raise ValueError("side is buy or sell")
        if coin not in px:
            raise ValueError(f"{coin or 'coin'} is not watched; Ananta trades {', '.join(sorted(px))}")
        st = self.state(px)
        held = next((x for x in st["positions"] if x["coin"] == coin), None)
        usd = p.get("usd")
        if side == "sell" and usd in (None, "", "all", 0):
            if not held:
                raise ValueError(f"no {coin} in the manual book to sell")
            usd = held["value"]
        try:
            usd = round(float(usd), 2)
        except (TypeError, ValueError) as exc:
            raise ValueError("an amount in dollars is required") from exc
        if usd <= 0 or usd > MAX_ORDER_USD:
            raise ValueError(f"amount must be between $1 and ${MAX_ORDER_USD:.0f} (paper)")
        if side == "buy" and usd * (1 + FEE + HALF_SPREAD.get(coin, 0.004)) > st["cash"] + 0.01:
            raise ValueError(f"not enough paper cash: ${st['cash']:.2f} available")
        if side == "sell" and (not held or usd > (held["value"] or 0) + 0.01):
            raise ValueError(f"the manual book holds only ${(held or {}).get('value') or 0:.2f} of {coin}")
        stop, target = p.get("stop"), p.get("target")
        stop = float(stop) if stop not in (None, "") else None
        target = float(target) if target not in (None, "") else None
        if side == "buy" and stop is not None and stop >= px[coin]:
            raise ValueError("the stop must be below the current price")
        if side == "buy" and target is not None and target <= px[coin]:
            raise ValueError("the target must be above the current price")
        return {"side": side, "coin": coin, "usd": usd, "stop": stop, "target": target, "reason": str(p.get("reason") or "")[:300]}

    def preview(self, p: dict, px: dict[str, float]) -> dict:
        v = self.validate(p, px)
        price = px[v["coin"]]
        cost = v["usd"] * (FEE + HALF_SPREAD.get(v["coin"], 0.004))
        st = self.state(px)
        cash_after = st["cash"] - v["usd"] - cost if v["side"] == "buy" else st["cash"] + v["usd"] - cost
        held = next((x for x in st["positions"] if x["coin"] == v["coin"]), None)
        exposure = ((held or {}).get("value") or 0) + (v["usd"] if v["side"] == "buy" else -v["usd"])
        words = (f"Paper {v['side'].upper()} ${v['usd']:,.2f} of {v['coin']} at about ${price:,.6g} (cost ~${cost:.2f}). "
                 f"After: {v['coin']} ${max(0, exposure):,.2f}, cash ${cash_after:,.2f}.")
        if v["stop"]:
            words += f" Stop ${v['stop']:,.6g} ({100 * (v['stop'] / price - 1):+.1f}%)."
        if v["target"]:
            words += f" Target ${v['target']:,.6g} ({100 * (v['target'] / price - 1):+.1f}%)."
        return {"order": v, "price": price, "cost": round(cost, 2), "cash_after": round(cash_after, 2), "summary": words}

    def execute(self, who: str, p: dict, px: dict[str, float], trigger: str = "owner") -> dict:
        v = self.validate(p, px)
        price = px[v["coin"]]
        cost = v["usd"] * (FEE + HALF_SPREAD.get(v["coin"], 0.004))
        fid = "M" + uuid.uuid4().hex[:9]
        self.db.execute("INSERT INTO manual_fills VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (fid, int(self.now()), v["coin"], v["side"].upper(), v["usd"], v["usd"] / price, price, cost, v["reason"], who, trigger))
        if v["side"] == "buy" and (v["stop"] or v["target"]):
            self.db.execute("INSERT OR REPLACE INTO manual_orders VALUES (?,?,?,?)", (v["coin"], v["stop"], v["target"], int(self.now())))
        if v["side"] == "sell" and not any(x["coin"] == v["coin"] for x in self.state(px)["positions"]):
            self.db.execute("DELETE FROM manual_orders WHERE coin=?", (v["coin"],))
        self.db.commit()
        if v["reason"]:
            self.note(who, "manual_order", fid, v["reason"])
        return {"fill": fid, "side": v["side"], "coin": v["coin"], "usd": v["usd"], "price": price, "cost": round(cost, 2)}

    def set_levels(self, who: str, coin: str, stop: float | None, target: float | None, px: dict[str, float]) -> dict:
        """Set, move or remove (0) the stop / target of a position in this book. None leaves that level as it is."""
        coin = (coin or "").upper()
        if not any(x["coin"] == coin for x in self.state(px)["positions"]):
            raise ValueError(f"no {coin} in the manual book")
        row = self.db.execute("SELECT stop, target FROM manual_orders WHERE coin=?", (coin,)).fetchone() or (None, None)
        new_stop = row[0] if stop is None else (float(stop) or None)
        new_target = row[1] if target is None else (float(target) or None)
        p = px.get(coin)
        if p and new_stop and new_stop >= p:
            raise ValueError("the stop must be below the current price")
        if p and new_target and new_target <= p:
            raise ValueError("the target must be above the current price")
        if new_stop is None and new_target is None:
            self.db.execute("DELETE FROM manual_orders WHERE coin=?", (coin,))
        else:
            self.db.execute("INSERT OR REPLACE INTO manual_orders VALUES (?,?,?,?)", (coin, new_stop, new_target, int(self.now())))
        self.db.commit()
        self.note(who, "levels", coin, f"stop {new_stop}, target {new_target}")
        return {"coin": coin, "stop": new_stop, "target": new_target}

    def check_stops(self, px: dict[str, float], push: Callable[[str, str], Any] | None = None) -> list[dict]:
        out = []
        for coin, stop, target in list(self.db.execute("SELECT coin, stop, target FROM manual_orders")):
            if coin not in px:
                continue
            p = px[coin]
            hit = "stop" if (stop and p <= stop) else "target" if (target and p >= target) else None
            if not hit:
                continue
            held = next((x for x in self.state(px)["positions"] if x["coin"] == coin), None)
            if not held:
                self.db.execute("DELETE FROM manual_orders WHERE coin=?", (coin,))
                continue
            r = self.execute("ananta (paper stop/target)", {"side": "sell", "coin": coin, "usd": held["value"], "reason": f"{hit} reached"}, px, trigger=hit)
            out.append(r)
            if push:
                try:
                    push(f"Paper {hit}: {coin}", f"Your manual paper {coin} position was sold at ${p:,.6g} ({hit} reached).")
                except Exception:  # noqa: BLE001
                    pass
        self.db.commit()
        return out

    def fills(self, n: int = 30) -> list[dict]:
        return [dict(zip(("id", "t", "coin", "side", "usd", "px", "cost", "reason", "trigger"), r)) for r in self.db.execute(
            "SELECT id, t, coin, side, usd, px, cost, reason, trigger FROM manual_fills ORDER BY t DESC LIMIT ?", (n,))]

    # ---- journal ----
    def note(self, who: str, kind: str, ref: str, text: str) -> dict:
        jid = "J" + uuid.uuid4().hex[:9]
        self.db.execute("INSERT INTO journal VALUES (?,?,?,?,?,?)", (jid, int(self.now()), kind, ref, text[:500], who))
        self.db.commit()
        return {"id": jid}

    def journal(self, n: int = 50) -> list[dict]:
        return [dict(zip(("id", "t", "kind", "ref", "text"), r)) for r in self.db.execute(
            "SELECT id, t, kind, ref, text FROM journal ORDER BY t DESC LIMIT ?", (n,))]

    # ---- research jobs ----
    def start_job(self, who: str, kind: str, fn: Callable[[], Any], push: Callable[[str, str], Any] | None = None,
                  background: bool = True) -> dict:
        jid = "R" + uuid.uuid4().hex[:9]
        self.db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?)", (jid, int(self.now()), kind, "RUNNING", None, None, who))
        self.db.commit()

        def run():
            try:
                res, status = fn(), "DONE"
            except Exception as exc:  # noqa: BLE001
                res, status = {"error": str(exc)[:300]}, "FAILED"
            self.db.execute("UPDATE jobs SET status=?, result=?, done_t=? WHERE id=?", (status, json.dumps(res, default=str)[:4000], int(self.now()), jid))
            self.db.commit()
            if push:
                try:
                    push(f"Ananta research: {kind} {status.lower()}", _job_line(kind, status, res))
                except Exception:  # noqa: BLE001
                    pass

        if background:
            threading.Thread(target=run, daemon=True).start()
        else:
            run()
        return {"job": jid, "kind": kind, "status": "RUNNING" if background else self.job(jid)["status"]}

    def job(self, jid: str) -> dict | None:
        r = self.db.execute("SELECT id, t, kind, status, result, done_t FROM jobs WHERE id=?", (jid,)).fetchone()
        return None if not r else {"id": r[0], "t": r[1], "kind": r[2], "status": r[3], "result": json.loads(r[4]) if r[4] else None, "done_t": r[5]}

    def jobs(self, n: int = 10) -> list[dict]:
        return [self.job(i) for (i,) in self.db.execute("SELECT id FROM jobs ORDER BY t DESC LIMIT ?", (n,))]


def _job_line(kind: str, status: str, res: Any) -> str:
    if kind == "reconstruction" and isinstance(res, dict) and "match" in res:
        return (f"Rebuilt {res.get('rebuilt_real_events')} decisions from raw candles vs {res.get('logged_real_events')} logged: "
                + ("they match." if res["match"] else "they DIFFER; check the Evidence page."))
    return f"{kind}: {status.lower()}"
