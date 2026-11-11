# Review 42: the forward test on live paper (recording only)

Written 11 Nov 2026, after review 42 passed (`REVIEW_42_RESULTS.md`) and before any forward data exists. The first forward minute is
2026-11-12 00:00 UTC. Nothing here trades, sizes or reaches a book, and no screen, note, voice or phone note quotes its results before the read.

## The rule (review 42's passing cell, unchanged)
- **The coins:** NDAX30, frozen. That is the PIT30 list of 2026-09, the last month the lake had a list for, restricted to the coins NDAX listed on 11 Nov 2026. It is written once to `~/ananta_runs/review42_forward/universe.json`.
- **The trigger:** a coin's 15-minute return at or below its frozen worst 0.05% cut-off (`~/ananta_runs/review41/review41_cutoffs.json`), on Binance one-minute closes. At most one per coin per hour.
- **The order:**
  - a resting buy half that coin's cut-off below the price, resting 60 minutes;
  - filled only when the price trades through it by 0.1%;
  - sold 4 hours after the fill.

## Two records per sighting
1. **Binance**, from the lake's one-minute candles, exactly as review 42 measured it.
2. **NDAX, which decides:**
   - the order is placed at NDAX's mid at the close of the detection minute (the worker Mac's recorded quotes);
   - it fills when NDAX's ask trades through it by 0.1% within 60 minutes;
   - it is sold at NDAX's bid 4 hours after the fill;
   - the 0.20% fee is charged each way.

   A sighting whose NDAX quotes are missing is recorded as "no data" and never counted.

## How it runs
- **When:** weekly, after the Sunday lake update (`scripts/lake_weekly.sh`): `src/research/review42_forward.py`.
- **What it writes:** each finished sighting is appended once to `~/ananta_runs/review42_forward/sightings.jsonl`.
- **The count:** `status.json` holds counts only: sightings, fills, and independent days with an NDAX fill.
- **Its listings:** the open list (due list item EV-R42) and the watch R42_FWD in `docs/knowledge/watches.json`.

## The read (once)
- **When:** at 30 independent days with an NDAX fill (UTC days).
- **The marks:** review 42's frozen pass marks, with NDAX's own fills and the fee deciding:
  - at least 30 days;
  - the mean of the day means above zero;
  - the excess over random above z 2.5 (random times drawn from the same coins and hours of the forward period);
  - above zero at twice the fee plus NDAX's median spread;
  - no month above half of the gain.
- **No early looks:** until then the record is counted, never totalled.
- **A pass** is put to Madhav with the figures, after the 14 Dec review at the earliest. Only his yes moves it further.
- **A fail** is written up as a lesson.
