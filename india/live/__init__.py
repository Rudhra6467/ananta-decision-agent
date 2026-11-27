"""The live path (flag 239; design: india/registrations/live_path_design_v1.md, Madhav's yes on flag 287, 26 Nov 2026).

Built switched off, on the `live-path` branch, never merged before the live day. Nothing running imports this package or india/orders.py.
What is here:
  switches.py    LIVE_ORDERS and ENFORCE (constants, False), the kill switch (a file; unreadable or missing counts as ON)
  rules.py       the live options rules: Rs 75,000 of options money, a Rs 37,500 cap on a 1-lot premium, one position overnight, the margin check
  survival.py    the survival check in record mode (5% day, 22% under the high-water mark); it only reads
  reconcile.py   the order ledger against Zerodha's own orders, positions and GTTs (GET); any difference turns the kill switch on
The only file that may build order or GTT requests is india/orders.py, and every send goes through its one gate (orders.send).
"""
