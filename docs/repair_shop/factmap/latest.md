# Fact map 2026-11-11T05:40

Fact map 2026-11-11T05:40: 124 kinds of file written in 8 days; 52 read live, 15 after the nightly build, 2 feed another file, 0 copied into words by hand, 55 internal, 0 with no route. No FAIL.

| check | state | words |
|---|---|---|
| fresh: manifests/market_context.json | PASS | manifests/market_context.json is newer than all its inputs |
| fresh: manifests/quotebook.json | PASS | manifests/quotebook.json is newer than all its inputs |
| Today screen Nifty = what Ananta says | PASS | screen Nifty · Wed 11 Nov close 25,255; Ananta 25,255.05 (at today's close (Kite's closing price; the official NSE file lands later the same day)) |
| Today screen Bank Nifty = what Ananta says | PASS | screen 60,792 (Wed 11 Nov close); Ananta 60,792.40 (at today's close (Kite's closing price; the official NSE file lands later the same day)) |
| options screen trades = the options ledger | PASS | screen [('BANKNIFTY', 'D0'), ('NIFTY', 'D2')]; ledger (2026-11-11) [('BANKNIFTY', 'D0'), ('NIFTY', 'D2')] |

| file | route | written | why |
|---|---|---|---|
| manifests/announce_api.jsonl | internal | 2026-11-11T05:21 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/big_falls.json | internal | 2026-11-03T13:57 | data audit step 6 workfile; its counts reach the Ask through data_audit.json (the desk's data_we_have) |
| manifests/board_meetings.jsonl | internal | 2026-11-11T02:32 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/calendar.json | live | 2026-11-11T05:21 |  |
| manifests/cm_bhavcopy.jsonl | internal | 2026-11-11T02:30 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/corporate_actions.jsonl | internal | 2026-11-11T02:30 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/data_audit.json | live | 2026-11-10T20:35 |  |
| manifests/data_inventory.json | internal | 2026-11-10T20:22 | ops: the data inventory (read by lineage and the morning review) |
| manifests/dataset_versions.jsonl | internal | 2026-11-10T20:22 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/deals_build.json | internal | 2026-11-10T20:23 | a build receipt |
| manifests/deals_snapshot.jsonl | internal | 2026-11-10T20:23 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/delivery.jsonl | internal | 2026-11-10T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/desk.json | live | 2026-11-11T05:21 |  |
| manifests/evidence_log.jsonl | nightly | 2026-11-10T21:30 |  |
| manifests/exam_history.jsonl | internal | 2026-11-05T23:46 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/exam_latest.json | live | 2026-11-05T23:46 |  |
| manifests/fii_dii_build.json | internal | 2026-11-11T02:41 | a build receipt |
| manifests/fii_dii_cash.jsonl | internal | 2026-11-10T20:23 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/fii_dii_history.jsonl | internal | 2026-11-11T02:41 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/firewall.json | internal | 2026-11-11T02:42 | ops: sealed-data firewall |
| manifests/flows_participant_oi.jsonl | internal | 2026-11-11T02:38 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/fo_ban.json | live | 2026-11-10T22:00 |  |
| manifests/fo_bhavcopy.jsonl | internal | 2026-11-11T02:30 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/hfn1t.json | internal | 2026-11-03T12:59 | research results: through the registry and the one map (and data_audit.json step 2) |
| manifests/holdout_candidates.json | internal | 2026-11-10T20:22 | research workfile (sealed holdout list) |
| manifests/impact.json | internal | 2026-11-10T20:22 | ops: lineage impact |
| manifests/integrity.json | nightly | 2026-11-10T20:22 |  |
| manifests/kite_1m_fo.jsonl | internal | 2026-11-10T20:05 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_5minute.jsonl | internal | 2026-11-07T10:12 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_depth.jsonl | internal | 2026-11-11T05:01 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_fill.json | feeds | 2026-11-07T10:13 | input to the stock 5-minute candles (india.kite_fill) |
| manifests/kite_index.jsonl | internal | 2026-11-11T05:20 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_minute.jsonl | internal | 2026-11-07T10:13 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/lab7.json | live | 2026-11-05T11:11 |  |
| manifests/leakcheck.json | nightly | 2026-11-10T20:22 |  |
| manifests/lineage.json | nightly | 2026-11-10T20:22 |  |
| manifests/macro.jsonl | internal | 2026-11-11T02:57 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/market_context.json | live | 2026-11-11T02:57 |  |
| manifests/mf_history.jsonl | internal | 2026-11-10T20:23 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/mf_schemes.json | live | 2026-11-10T20:23 |  |
| manifests/missed_DATE.json | internal | 2026-11-10T21:30 | missed movers; reaches the Ask through the read model's learning section |
| manifests/notable_results.json | nightly | 2026-11-10T20:35 | read by india/readmodel.py (path built in code) |
| manifests/nse_holidays.json | live | 2026-11-10T22:00 |  |
| manifests/options_realism.json | internal | 2026-11-10T20:22 | research workfile behind the options line's realistic fills |
| manifests/others_DATE.json | internal | 2026-11-10T21:30 | the reference traders; reaches the Ask through the read model's learning section |
| manifests/pr_zip.jsonl | internal | 2026-11-11T02:38 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/premarket_chain.json | live | 2026-11-10T22:00 |  |
| manifests/premarket_gift.json | nightly | 2026-11-10T22:00 |  |
| manifests/premarket_inputs.json | internal | 2026-11-10T22:00 | input to the morning view's build |
| manifests/quotebook.json | live | 2026-11-11T02:57 |  |
| manifests/quotebook_names.json | live | 2026-11-11T02:57 |  |
| manifests/r2_verify.json | internal | 2026-11-11T02:44 | ops: backup check |
| manifests/results_html.jsonl | internal | 2026-11-11T02:36 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/results_index_integrated_v2.jsonl | internal | 2026-11-11T02:31 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/results_today.json | nightly | 2026-11-10T22:00 |  |
| manifests/sealed_access.jsonl | internal | 2026-11-11T05:21 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/sectormap.jsonl | internal | 2026-11-11T02:41 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/sectormap_build.json | internal | 2026-11-11T02:41 | a build receipt |
| manifests/settle_vs_tradable.json | internal | 2026-11-10T20:22 | research workfile |
| manifests/sp1_nightly_replay.json | internal | 2026-11-10T20:05 | ops: the options line's replay check |
| manifests/sp1_nightly_replay.jsonl | internal | 2026-11-10T20:05 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/sp1_open_check.jsonl | internal | 2026-11-09T20:05 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/technicals.json | live | 2026-11-11T05:21 |  |
| manifests/test_ledger.jsonl | live | 2026-11-05T11:11 |  |
| manifests/trials.json | live | 2026-11-11T02:57 |  |
| manifests/us_close.jsonl | nightly | 2026-11-10T21:00 |  |
| manifests/v02t.json | internal | 2026-11-03T12:28 | research results: through the registry and the one map (and data_audit.json step 2) |
| manifests/valuation.jsonl | internal | 2026-11-11T02:41 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/valuation_build.json | internal | 2026-11-11T02:41 | a build receipt |
| manifests/voice_check_history.jsonl | live | 2026-11-10T22:44 |  |
| manifests/voice_check_latest.json | live | 2026-11-10T22:44 |  |
| manifests/w500.json | internal | 2026-11-03T12:06 | research results: reach the Ask through the registry and the one map (and data_audit.json step 4) |
| paper/account/benchmark.jsonl | live (daytime) | 2026-11-10T20:24 |  |
| paper/account/state.json | live (daytime) | 2026-11-10T20:24 |  |
| paper/account/view.json | live (daytime) | 2026-11-10T20:24 |  |
| paper/allocation_ledger.jsonl | internal | 2026-11-10T20:24 | the allocator's ledger (its view is what is read) |
| paper/allocation_view.json | live (daytime) | 2026-11-10T20:24 |  |
| paper/baseline.parquet | nightly | 2026-11-10T21:30 |  |
| paper/baseline_closed.parquet | internal | 2026-11-10T21:30 | research book workfile |
| paper/calls.jsonl | live | 2026-11-09T20:22 |  |
| paper/dayplans/DATE.json | live | 2026-11-10T20:20 | read by jarvis/india/views.py (path built in code) |
| paper/decisions/DATE.json | live | 2026-11-09T21:30 |  |
| paper/decisions/DATE.universe.json | nightly | 2026-11-09T21:30 |  |
| paper/events.jsonl | live | 2026-11-09T21:30 |  |
| paper/factorbook/marks.jsonl | nightly | 2026-11-10T20:35 |  |
| paper/factorbook/state.json | nightly | 2026-11-10T20:35 |  |
| paper/factorbook/view.json | nightly | 2026-11-10T20:35 |  |
| paper/filter_slices.csv | nightly | 2026-11-10T21:30 |  |
| paper/forecasts.jsonl | nightly | 2026-11-10T22:00 |  |
| paper/managed/ledger.jsonl | live | 2026-11-10T20:24 |  |
| paper/managed/plans.jsonl | live | 2026-11-09T20:24 |  |
| paper/managed/score.json | live | 2026-11-10T20:24 |  |
| paper/managed/state.json | live | 2026-11-10T20:24 |  |
| paper/managed/view.json | live | 2026-11-10T20:24 |  |
| paper/marks.jsonl | live | 2026-11-10T21:30 |  |
| paper/morningview/DATE.json | live (daytime) | 2026-11-10T23:50 | read by jarvis/india/views.py (path built in code) |
| paper/morningview/latest.json | live (daytime) | 2026-11-10T23:50 |  |
| paper/news_read/DATE.json | internal | 2026-11-10T20:23 | the news model's daily read of movers: the record behind the news study |
| paper/news_read/log.jsonl | internal | 2026-11-10T20:23 | the news model's daily read of movers: the record behind the news study |
| paper/others_history.jsonl | feeds | 2026-11-10T21:30 | input to manifests/others_DATE.json (india.others) |
| paper/preopen/DATE.json | live | 2026-11-10T23:50 | read by jarvis/india/preopen.py (path built in code) |
| paper/reconstruction/DATE.json | live | 2026-11-10T21:30 | read by jarvis/india/ask.py (path built in code) |
| paper/reconstruction/decisions.jsonl | live | 2026-11-08T11:48 |  |
| paper/reconstruction/latest.json | live | 2026-11-10T21:30 |  |
| paper/rs_trial.json | live | 2026-11-10T21:30 |  |
| paper/rx1_trial.json | live | 2026-11-10T21:30 |  |
| paper/shadow/DATE.json | live | 2026-11-10T22:06 | read by jarvis/india/views.py (path built in code) |
| paper/shadow/summary.json | live | 2026-11-11T02:57 |  |
| paper/sp1/book.json | live (daytime) | 2026-11-10T07:00 |  |
| paper/sp1/decisions.jsonl | live (daytime) | 2026-11-10T23:15 |  |
| paper/sp1/outcomes.jsonl | live | 2026-11-09T07:00 |  |
| paper/sp1/plans/DATE.json | live | 2026-11-10T21:01 |  |
| paper/sp1/work/score_outcomes.parquet | internal | 2026-11-09T07:00 | research book workfile |
| paper/state.json | live | 2026-11-10T21:30 |  |
| paper/teachers/forward_options.jsonl | live | 2026-11-09T20:20 | read by jarvis/india/views.py (path built in code) |
| paper/teachers/forward_options_summary.json | live | 2026-11-10T20:20 |  |
| paper/teachers/live_signals.parquet | internal | 2026-11-10T20:20 | research book workfile |
| paper/teachers/live_summary.json | live | 2026-11-10T20:20 |  |
| readmodel/DATE.json | internal | 2026-11-11T02:57 | the read model itself |
| readmodel/latest.json | live | 2026-11-11T02:57 |  |
| reports/DATE.md | internal | 2026-11-10T21:30 | a written report for Madhav (the morning review page) |
| reports/ask_clarify.jsonl | live | 2026-11-07T18:51 |  |
| reports/ask_timing.jsonl | live | 2026-11-10T21:40 |  |
| reports/portfolio_DATE.md | internal | 2026-11-10T20:23 | a written report for Madhav (the morning review page) |
