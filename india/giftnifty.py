"""GIFT Nifty before the open (9 Nov 2026; Madhav: "yes, lets complete" to the outsider readiness review, fix 1: see the open before it happens).

GIFT Nifty is the Nifty future traded at NSE IX in GIFT City nearly round the clock (06:30-15:40 and 16:35-02:45 IST), so it has already
moved on whatever happened overnight when India opens. Zerodha serves it under the existing sign-in as NSEIX:GIFT NIFTY (checked 10 Nov 2026,
05:02 IST: quotes and one-minute bars both answer). It is a futures price, a little above or below the Nifty itself, so it is never compared
with the Nifty's close: it is read against its own level at the last NSE close (its 15:29 minute on the last session), and that change is the
indicated gap. Read only; nothing trades on it and no rule reads it.

  read(k, last_session, nifty_close)   {"last", "last_at", "ref", "ref_at", "change_pct", "indicated_nifty", "bucket", "words", ...}
  bucket(change_pct)                    down / flat / up with the options line's own lines (its spec: down <= -0.25%, up >= +0.25%)

  python -m india.giftnifty             reads it now and prints the sentence
"""
from __future__ import annotations

import datetime as dt
import json
import sys

SYMBOL = "NSEIX:GIFT NIFTY"
TOKEN = 291849
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
GAP_LINE = 0.25            # per cent; the options line's gap levels (sp1_v2.json opening.gap)
STALE_MIN = 20             # a last print older than this is said as "not trading now"


def bucket(change_pct: float | None) -> str | None:
    if change_pct is None:
        return None
    return "down" if change_pct <= -GAP_LINE else ("up" if change_pct >= GAP_LINE else "flat")


def _ts(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(str(s)[:19]).replace(tzinfo=IST)


def _dw(d: dt.date) -> str:
    return f"{d:%a} {d.day} {d:%b}"


def read(k=None, last_session: str | dt.date | None = None, nifty_close: float | None = None, now: dt.datetime | None = None, candles: list | None = None) -> dict:
    """GIFT Nifty now against its own level at the last NSE close. candles (tests): one-minute rows [ts, o, h, l, c, ...] from the last
    session's 15:15 IST to now, as Kite's historical endpoint returns them."""
    now = now or dt.datetime.now(IST)
    out = {"symbol": SYMBOL, "taken_at": now.isoformat(timespec="seconds"), "last_session": str(last_session) if last_session else None, "paper": True}
    if not last_session:
        return {**out, "error": "the last session is not known"}
    d0 = dt.date.fromisoformat(str(last_session))
    try:
        if candles is None:
            r = k.get(f"/instruments/historical/{TOKEN}/minute", params={"from": f"{d0} 15:15:00", "to": f"{now:%Y-%m-%d %H:%M:%S}"})
            candles = (r or {}).get("candles") or []
    except Exception as e:  # noqa: BLE001 - said as missing, never raised into a view
        return {**out, "error": f"{type(e).__name__}: {str(e)[:100]}"}
    rows = [(_ts(c[0]), float(c[4])) for c in candles if c and c[4] is not None]
    cut = dt.datetime.combine(d0, dt.time(15, 30), IST)
    before = [x for x in rows if x[0] < cut]
    after = [x for x in rows if x[0] >= cut and x[0] <= now]
    if not before:
        return {**out, "error": f"no GIFT Nifty print before the {d0} 15:30 IST close"}
    if not after:
        return {**out, "error": "no GIFT Nifty print since the last NSE close"}
    (ref_at, ref), (last_at, last) = before[-1], after[-1]
    chg = round(100 * (last / ref - 1), 2)
    age = int((now - last_at).total_seconds() // 60)
    out.update({"ref": ref, "ref_at": ref_at.isoformat(timespec="minutes"), "last": last, "last_at": last_at.isoformat(timespec="minutes"), "age_min": age,
                "trading_now": age <= STALE_MIN, "change_pct": chg, "bucket": bucket(chg),
                "indicated_nifty": round(nifty_close * (1 + chg / 100)) if nifty_close else None, "nifty_close": nifty_close})
    out["words"] = words(out)
    return out


def words(d: dict | None) -> str | None:
    if not d or d.get("error") or d.get("change_pct") is None:
        return None
    last_at, ref_at = _ts(d["last_at"]), _ts(d["ref_at"])
    chg = d["change_pct"]
    move = "unchanged" if abs(chg) < 0.05 else f"{'up' if chg > 0 else 'down'} {abs(chg):.1f}%"
    b = {"up": "an open higher", "down": "an open lower", "flat": "a flat open"}[d["bucket"]]
    s = (f"GIFT Nifty, the Nifty future that trades overnight, is {move} from where it stood at the last NSE close "
         f"({d['last']:,.0f} at {last_at:%H:%M} IST {_dw(last_at.date())}, against {d['ref']:,.0f} at {_dw(ref_at.date())}'s 15:30 close)")
    if d.get("indicated_nifty"):
        s += f": it points to {b}, the Nifty near {d['indicated_nifty']:,.0f}"
    else:
        s += f": it points to {b}"
    if not d.get("trading_now"):
        s += f" (its last print is {d['age_min']} minutes old; it is not trading now)"
    return s + ". An indication only: the 09:15 open can differ, and nothing trades on it."


if __name__ == "__main__":
    from india import kite, paths
    rm = json.loads((paths.data_dir() / "readmodel" / "latest.json").read_text())
    r = read(kite.Kite(), rm.get("data_through"), (rm.get("market") or {}).get("nifty_close"))
    print(r.get("words") or r.get("error"))
    sys.exit(0)
