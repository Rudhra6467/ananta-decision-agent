"""Read-only ledger snapshot: holdings, positions, funds, today's orders and trades, one JSON per day.

  python -m india.ledger snapshot
Files go to bronze/ledger/YYYY-MM-DD.json (mode 600). bronze/ is not in the R2 sync, so the ledger never leaves the Mac;
the only thing written outside that folder is a heartbeat row with counts, never amounts. Nothing here can place an order.
"""
from __future__ import annotations

import datetime as dt
import json
import os

from india import catalog, kite, paths


def snapshot() -> dict:
    paths.ensure()
    k = kite.Kite()
    now = dt.datetime.now(dt.timezone.utc)
    rec = {"taken_at": now.isoformat(timespec="seconds"), "user_id": k.user_id,
           "holdings": k.holdings(), "positions": k.positions(), "margins": k.margins(), "orders": k.orders(), "trades": k.trades()}
    out = paths.bronze("ledger") / f"{now.astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, default=str))
    os.chmod(out, 0o600)
    counts = {"holdings": len(rec["holdings"]), "positions_net": len(rec["positions"].get("net", [])),
              "orders": len(rec["orders"]), "trades": len(rec["trades"]), "file": out.name}
    catalog.heartbeat("ledger.snapshot", True, json.dumps(counts))
    return counts


if __name__ == "__main__":
    print(snapshot())
