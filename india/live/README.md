# The live path, built switched off (flag 239; design `india/registrations/live_path_design_v1.md`, Madhav's yes on flag 287)

Built Fri 27 Nov 2026 on the `live-path` branch in its own worktree (`~/code/ananta-records-live`). Never merged before the live day (design part 7). Nothing running imports it; `india/kite.py` and every pinned file are unchanged.

| Part of the design | File | Tests |
|---|---|---|
| 1. The order module | `india/orders.py` (the only file that builds order or GTT requests; one gate, `send`) | `tests/test_live_path_orders.py` |
| 2. The options rules | `india/live/rules.py` | `tests/test_live_path_rules.py` (T1's 23 decisions as fixtures) |
| 3. The exits | `india/orders.py` (AMO next open, GTT backstop, index-stop watch, the 09:20 re-price, the step for Madhav) | `tests/test_live_path_orders.py` |
| 5. Survival check (record mode), switches, kill switch | `india/live/survival.py`, `india/live/switches.py` | `tests/test_live_path_switches.py`, `tests/test_live_path_reconcile_survival.py` |
| 6. Reconciliation | `india/live/reconcile.py` | `tests/test_live_path_reconcile_survival.py` |
| Safety: off means off | all of the above | `tests/test_live_path_never_reaches_orders.py` |

**Off means off.** `LIVE_ORDERS = False` and `ENFORCE = False` are constants in code. The kill switch is a file in the live folder (`INDIA_LIVE_DIR`, default `~/ananta_live/india`, refused if it sits inside the India data folder); missing or unreadable counts as on, and only Madhav turns it off. The safety test scans the code (the one network call is `orders._http`, reached only from `orders.send` after `switches.require_send()`) and calls every public function with a fake Kite, proving nothing reaches an order or GTT endpoint, nor any POST, PUT or DELETE but the margin calculator.

## Zerodha facts the build relies on (read 27 Nov 2026 from Zerodha's own pages)

- **AMO for F&O: confirmed.** AMOs can be placed, changed or cancelled for F&O from 3:45 PM to 9:11 AM IST, and are sent to the exchange at 09:15 AM. No AMO can be placed, modified or cancelled between 1:00 AM and 5:30 AM IST (maintenance). Orders with the GTT box ticked are not accepted as AMOs, and auto-slicing is not available for AMOs. Source: [What is After Market Order (AMO) & its timings?](https://support.zerodha.com/category/trading-and-markets/charts-and-orders/order/articles/auto-amo). In code: `orders.amo_window_open`; the next-open exit is placed after 15:45 IST (about 05:15 Toronto), which is outside the 01:00-05:30 IST shut.
- **GTT on option contracts: confirmed.** GTTs are available for F&O contracts; they stay valid only until the contract expires; index F&O GTTs are cancelled when the contract's lot size changes. Source: [Are GTT orders available for F&O contracts?](https://support.zerodha.com/category/trading-and-markets/charts-and-orders/gtt/articles/gtt-fno). The API places a GTT with `POST /gtt/triggers` (`type`, `condition` with the instrument's own `tradingsymbol` and `trigger_values`, `orders` with LIMIT orders); it triggers on that instrument's own last price, which is why an index-level stop needs the Mac watching plus a wider option backstop. Source: [Kite Connect GTT orders](https://kite.trade/docs/connect/v3/gtt/).
- **Orders API.** `POST /orders/:variety` (regular, amo), `DELETE /orders/:variety/:order_id`; `validity` DAY, IOC or TTL with `validity_ttl` in minutes. The entry uses TTL 1 minute, so Zerodha itself cancels an unfilled entry even if the Mac is gone, and the module also cancels after 60 s. Source: [Kite Connect orders](https://kite.trade/docs/connect/v3/orders/).

## Not built here, by design or for later

- Part 4 (stocks, a week after options): the GTT stop on each stock fill and the survival rules on enforce reuse `orders.gtt_request` and `survival.actions`; the stock side's own entry is built after options go live and Madhav names the book.
- Part 7 (the join): the leak check's `no_order_rule` change through the repair door, the merge, the phone alert path for the kill switch and `alert_step`, and the daily survival job that writes its rows (today `survival.record` only reads a file). All need Madhav's written yes on the live day.
- To check by hand on the live day's dry run: that Zerodha takes a TTL of 1 minute on NFO LIMIT orders, and the tick of each contract (0.05 assumed, as T1 found on every decision).
