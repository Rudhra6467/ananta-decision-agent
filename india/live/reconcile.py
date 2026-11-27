"""Reconciliation (design part 6; flag 241): the order ledger against Zerodha's own orders, trades, positions and GTTs, read by GET only.

Any difference turns the kill switch on (and is a HIGH self-check line once joined on the live day):
  - a trade at Zerodha from an order the ledger did not send;
  - a position Zerodha holds in a contract the ledger never entered;
  - a GTT the ledger placed and did not delete, missing at Zerodha while its position is still open;
  - a GTT at Zerodha the ledger does not know.
If Zerodha cannot be read, the kill switch goes on too: what cannot be checked is not trusted.
The comparison is a pure function (differences); run() does the reads through india/kite.py's own GET client.
"""
from __future__ import annotations

from india.live import switches


def _sent(ledger: list[dict], what: tuple[str, ...]) -> list[dict]:
    return [r for r in ledger if r.get("step") == "after" and r.get("ok") and r.get("what") in what]


def differences(ledger: list[dict], trades: list[dict], positions: dict | list, gtts: list[dict]) -> list[str]:
    order_ids = {str((r.get("answer") or {}).get("order_id")) for r in _sent(ledger, ("entry", "exit", "exit_amo"))}
    entered = {(r.get("decision") or {}).get("tradingsymbol") for r in _sent(ledger, ("entry",))}
    placed = {int((r.get("answer") or {}).get("trigger_id")): (r.get("decision") or {}).get("tradingsymbol")
              for r in _sent(ledger, ("gtt",)) if (r.get("answer") or {}).get("trigger_id") is not None}
    deleted = set()
    for r in ledger:
        if r.get("step") == "before" and r.get("what") == "gtt_delete":
            deleted.add(int(str(r.get("path", "")).rsplit("/", 1)[-1]))
    live_gtts = {int(g["id"]): g for g in gtts if str(g.get("status", "active")) == "active"}
    net = positions.get("net", []) if isinstance(positions, dict) else positions
    open_syms = {p.get("tradingsymbol") for p in net if int(p.get("quantity") or 0) != 0}
    out = []
    for t in trades:
        if str(t.get("order_id")) not in order_ids:
            out.append(f"a trade at Zerodha the ledger did not send: order {t.get('order_id')} {t.get('tradingsymbol')}")
    for s in sorted(x for x in open_syms if x not in entered):
        out.append(f"a position at Zerodha the ledger never entered: {s}")
    for tid, sym in sorted(placed.items()):
        if tid in deleted:
            continue
        if sym in open_syms and tid not in live_gtts:
            out.append(f"the GTT backstop {tid} for {sym} is missing at Zerodha while the position is open")
    for tid in sorted(live_gtts):
        if tid not in placed:
            out.append(f"a GTT at Zerodha the ledger does not know: {tid} {live_gtts[tid].get('condition', {}).get('tradingsymbol', '')}")
    return out


def run(kite, ledger: list[dict]) -> dict:
    """Read Zerodha (GET) and compare. A difference, or a read that fails, turns the kill switch on."""
    try:
        trades, positions, gtts = kite.trades(), kite.positions(), kite.get("/gtt/triggers")
    except Exception as e:  # noqa: BLE001
        why = f"reconciliation could not read Zerodha ({type(e).__name__})"
        switches.turn_on(why)
        return {"ok": False, "differences": [why]}
    diffs = differences(ledger, trades or [], positions or {}, gtts or [])
    if diffs:
        switches.turn_on("reconciliation: " + "; ".join(diffs)[:500])
    return {"ok": not diffs, "differences": diffs}
