# The live path, design v1 (written Thu 26 Nov 2026, for Madhav's yes before anything is built)

Flag 239. Route: `golive_plan_v1.md`, Track A. Checklist: `pass_marks_v1.md`, "Going live", items 5-7. Decisions it follows: INDIA_LOCK.md, "Decisions of 25 Nov" (Rs 75,000 of options money, a Rs 37,500 cap on a 1-lot premium, at most one options position overnight, live in two steps).

**What this page is.** How Ananta India would place real orders, written before a line of it is built. Nothing here is switched on by this page. The paper line (SP1 v2) and every paper rule stay exactly as frozen; the live path follows the paper line's decisions, it never makes its own.

**What exists today (read on 26 Nov).** Zerodha is read-only: `india/kite.py` sends GET plus Kite's margin calculator, and the nightly leak check (`kite_calls`, the pinned `no_order_rule`) fails if any order or GTT word appears there. The survival rules (5% day, 22% pause) are written in `paper_config.json` and used by the research simulations, but no daily job computes them for the paper books yet, and India has no kill switch. So the live path must build three things that do not exist: the order module, the survival check in record mode, and the kill switch.

## Where it is built, and why the running system cannot see it

- Its own folder and branch: the git worktree `~/code/ananta-records-live`, branch `live-path`, pushed to origin and never merged until the live day.
- No running job imports it. The nightly leak check reads `india/kite.py` in the main checkout, which does not change, so G02's clean count is not touched.
- Every call that could place, change or cancel an order sits behind one master switch, `LIVE_ORDERS`, that is **off** in code (a constant, not a setting a job can flip), plus the kill switch.
- **Tested by:** a test that the master switch is off; a test that walks every code path (AST scan plus calling each public function with a fake Kite) and proves none reaches `/orders`, `/gtt` or any POST/PUT/DELETE other than the margin calculator while it is off; T15.

## Part 1. The order module (`india/orders.py`, used only from the live day)

- One small file is the only place that may talk to Kite's order and GTT endpoints. Everything else keeps using `kite.py` read-only.
- What it can do: place a LIMIT buy for the paper line's chosen contract, 1 lot, NRML; place the exit (a LIMIT sell); place, read and cancel one GTT per position (the broker-side stop); read orders, trades and positions (GET).
- What it cannot do: market orders on options (Zerodha restricts them and they fill badly at the open), more than 1 lot, a contract the paper line did not choose, a second position the rules forbid, any order while the kill switch is on.
- Every call writes one line first (what, why, which paper decision) and one line after (Kite's answer), in its own ledger `live/orders.jsonl`, apart from the paper records.
- Limit price: the paper line's decision price plus a fixed band (proposed: 2 ticks plus 0.5%, the same slippage the realistic-fill rule uses); unfilled after 60 seconds, it is cancelled and the decision is logged "not filled live". It never chases.
- **Tested by:** unit tests with a fake Kite (each refusal above is a test); a dry run on the live day's first session in which every order is built and logged but not sent; T15.

## Part 2. The options rules in code

- Rs 75,000 of options money; the 1-lot premium at the decision must be Rs 37,500 or less, or the trade is skipped and logged "over the cap".
- At most one options position held overnight: a second index's decision is skipped while one is held (pre-live T1: this skipped all 4 Nifty trades so far; the rule is Madhav's and stays).
- Before every entry, Kite's margin calculator must confirm the money covers it (T1: it asks for the premium and nothing more).
- The paper line runs beside it, unchanged, for at least 10 live sessions; each live fill is compared with the paper fill of the same decision (Part 6).
- **Tested by:** T1 re-run on the live day (and whenever a live rule changes); unit tests on the cap, the one-overnight rule and the margin check, using the 23 decisions of T1 as fixtures (18 of 22 scored trades must come out "trade", the rest "skip" with T1's reason).

## Part 3. The exits

The paper line's exits are: the next open (19 of 23 decisions), a stop on the index (ATRSTOP, ORSTOP: 4 of 23), and time exits at 11:30 or 15:15 IST (none chosen so far).

- **The next open.** After the close (from 15:45 IST, about 05:15 Toronto), the module places the exit as an after-market order (AMO, LIMIT) so Zerodha sends it at 09:15 IST the next session without the Mac. The 09:15 job checks it filled; if not filled by 09:20 IST it re-prices once, then alerts.
- **Index-level stops (flag 270).** A broker order triggers on the option's own price, not the index. Two layers: (1) the Mac watches the index each minute and exits when the index stop is hit, as on paper; (2) a GTT on the option as a backstop, set at entry at the option price that matches the index stop (from the option's delta at entry), placed a little wider so it fires only if the Mac has missed it. Live may exit a little differently from paper on these days; every such difference is logged and read in Part 6.
- **Time exits.** The Mac places a LIMIT sell at the time; the GTT backstop stays until it fills.
- **When the Mac or the sign-in is down.** The AMO and the GTT already sit at Zerodha, so the next-open exit and the backstop need no Mac and no new token. If neither can be placed (the Mac was down at entry time), no entry is made: the module never enters a trade whose exit it cannot place. If a position is open and the morning check cannot run, the phone gets a HIGH alert with the exact step for Madhav ("open Kite, Positions, exit BANKNIFTY 26DEC 63400 CE, 1 lot").
- **Tested by:** T13 (the missed exit: Mac asleep, sign-in failed, the 09:15 job crashed, each walked through with its fallback written down); unit tests for the AMO and GTT order shapes with a fake Kite. Two facts to confirm from Zerodha's own documentation before the build, not from memory: the AMO window for F&O, and GTT triggers on option contracts.

## Part 4. Stocks, the second step (one week after options)

- Which stock book goes live, and with how much, is named in Madhav's written yes on that day (the plan says "stocks one week later"; the book's 8 original holdings carry no stop, noted, not changed on paper).
- Every live stock position gets a Zerodha GTT stop at its paper stop the moment it is filled, so a stop does not wait for the next morning.
- The survival rules switch from record to enforce for the live money: a 5% loss in a day (realised plus open, from the session's start) closes every live position and blocks new entries that day; 22% below the high-water mark blocks new entries until Madhav resumes. Paper keeps recording both paths as now.
- **Tested by:** T15 (the rules in record mode over the paper record fire on exactly the expected days; the enforce switch exists and is off); unit tests for the GTT placed on each fill.

## Part 5. The survival check and the kill switch

- **Survival check, record mode, built first.** A daily job writes, for each paper book, the day's start equity, the high-water mark, the worst moment of the day, and whether the 5% or 22% line was crossed. It changes nothing. This is what T15 reads, and it is what enforce mode will act on.
- **Enforce switch.** Off in code. On the live day, for the live money only.
- **Kill switch.** One flag, read before every order call: when on, no new order of any kind is sent, and the phone is told. Madhav can turn it on from the app or by voice; the module turns it on by itself when reconciliation finds a mismatch, when the survival check cannot be read, or when an order call fails twice. Only Madhav turns it off. If the flag itself cannot be read, the answer is "on".
- **Tested by:** T15; unit tests (kill switch on blocks every call; unreadable flag counts as on; two failures turn it on); the monthly India risk rehearsal after go-live.

## Part 6. Reconciliation: live against paper against random (flag 241)

- Each night: read Zerodha's orders, trades and positions (GET) and compare with the module's own ledger. Any difference (a fill the ledger does not know, a position Zerodha holds that the ledger does not, a GTT missing) turns the kill switch on and is a HIGH self-check line.
- The yardstick gets a third line from the same scoring code: live fills, the paper line, and random, so the checks follow real money. The live-against-paper gap per trade (entry, exit, costs) is shown for the 10-session comparison.
- **Tested by:** unit tests with planted differences (each must turn the kill switch on); the first live week's read.

## Part 7. The join on the live day

In this order, each step only after the one before is confirmed, and none on a session night:
1. Madhav's written yes in chat, confirming the figures (Rs 75,000, Rs 37,500 cap, one overnight position) and that options go first.
2. The separate review of this code (Rule A: the order module reviewed) has no open finding at the top two severities.
3. Through the repair door, with his words in the pin history: the leak check's `no_order_rule` is changed to allow the order and GTT endpoints in `india/orders.py` only (still none in `kite.py`), and its test is updated to match.
4. The `live-path` branch is merged into records.
5. T1 re-run on the live rules; the kill switch tested on, then off by Madhav.
6. `LIVE_ORDERS` on for options only; the first session as a dry run (built and logged, not sent) if Madhav wants one.
7. One week later, the same steps for stocks, with the survival rules on enforce.

## What waits for Madhav

- His yes to this design before it is built (the open list item "live-path-design").
- On the live day: his written yes (step 1) and the leak check's change (step 3).
- To name in that yes: which stock book goes live a week later, and with how much.
