"""One live sentence for "what is Ananta watching" (plan Batch 1, G9): the Watchlists card, "Ananta now" and Ask all read it, so the
app and Ananta never describe an old system again (it said "10 coins" for two days after the universe went live)."""
from __future__ import annotations


def facts(j) -> dict:
    out: dict = {"lab_coins": 10}
    try:
        from jarvis.service import registry

        out["coins"] = {t: len(registry.members(j, t)) for t in ("A", "B", "C")}
        out["coins_total"] = sum(out["coins"].values())
    except Exception:  # noqa: BLE001
        out["coins_total"] = None
    try:
        from jarvis.service import exposure

        d = exposure.state(j).get("dial")
        out["dial"] = None if d is None else ("OPEN" if d > 0 else "CLOSED")
    except Exception:  # noqa: BLE001
        out["dial"] = None
    try:
        from jarvis.service import brain

        out["brain_open"], out["brain_max"] = brain._account_open(j), brain.MAX_OPEN
    except Exception:  # noqa: BLE001
        pass
    return out


def watching(j) -> str:
    f = facts(j)
    bits = []
    if f.get("coins_total"):
        c = f["coins"]
        bits.append(f"Watching {f['coins_total']} coins live ({c['A']} big, {c['B']} mid-size, {c['C']} small and watched only)")
    else:
        bits.append("Watching the whole crypto market")
    bits.append("the 10 lab coins also on 15-minute setups")
    if f.get("dial"):
        bits.append("market dial " + ("open: buying allowed" if f["dial"] == "OPEN" else "closed: no new buys except measured edges"))
    if f.get("brain_max"):
        bits.append(f"brain holds {f['brain_open']} of {f['brain_max']} trades")
    return "; ".join(bits)
