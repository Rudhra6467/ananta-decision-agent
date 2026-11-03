# Fact map 2026-11-03T13:35

Fact map 2026-11-03T13:35: 145 kinds of file written in 8 days; 46 read live, 15 after the nightly build, 4 feed another file, 0 copied into words by hand, 80 internal, 0 with no route. No FAIL.

| check | state | words |
|---|---|---|
| fresh: manifests/market_context.json | PASS | manifests/market_context.json is newer than all its inputs |
| fresh: manifests/quotebook.json | PASS | manifests/quotebook.json is newer than all its inputs |
| Today screen Nifty = what Ananta says | PASS | screen Nifty · Tue 3 Nov close 23,811; Ananta 23,810.85 (at the close of Tuesday 3 Nov, the last session (the next opens Wednesday 4 Nov 09:15 IST)) |
| options screen trades = the options ledger | PASS | screen [('BANKNIFTY', 'D1'), ('NIFTY', 'D3')]; ledger (2026-11-03) [('BANKNIFTY', 'D1'), ('NIFTY', 'D3')] |

| file | route | written | why |
|---|---|---|---|
| manifests/announce_api.jsonl | internal | 2026-11-02T19:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/big_falls.json | internal | 2026-11-03T12:26 | data audit step 6 workfile; its counts reach the Ask through data_audit.json (the desk's data_we_have) |
| manifests/board_meetings.jsonl | internal | 2026-11-03T12:53 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/cm_bhavcopy.jsonl | internal | 2026-11-03T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/corporate_actions.jsonl | internal | 2026-11-03T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/data_audit.json | live | 2026-11-03T12:59 |  |
| manifests/data_inventory.json | internal | 2026-11-03T11:29 | ops: the data inventory (read by lineage and the morning review) |
| manifests/datacheck.json | internal | 2026-10-29T21:55 | ops: freshness check (morning review) |
| manifests/dataset_versions.jsonl | internal | 2026-11-03T08:29 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/deals_build.json | internal | 2026-11-02T19:04 | a build receipt |
| manifests/deals_snapshot.jsonl | internal | 2026-11-02T19:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/delivery.jsonl | internal | 2026-11-03T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/desk.json | live | 2026-11-03T13:04 |  |
| manifests/evidence_log.jsonl | nightly | 2026-11-02T21:30 |  |
| manifests/exam_history.jsonl | internal | 2026-10-30T02:39 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/exam_latest.json | live | 2026-10-30T02:39 |  |
| manifests/fii_dii_build.json | internal | 2026-11-03T12:58 | a build receipt |
| manifests/fii_dii_cash.jsonl | internal | 2026-11-02T19:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/fii_dii_history.jsonl | internal | 2026-11-03T12:58 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/firewall.json | internal | 2026-11-03T12:59 | ops: sealed-data firewall |
| manifests/flows_participant_oi.jsonl | internal | 2026-11-03T12:53 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/fo_ban.json | live | 2026-11-02T22:00 |  |
| manifests/fo_bhavcopy.jsonl | internal | 2026-11-03T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/gaplab_gp1.json | internal | 2026-10-29T22:04 | research results: through the registry and the one map |
| manifests/gaplab_gp1_diag.json | internal | 2026-10-26T20:39 | research results: through the registry and the one map |
| manifests/gaplab_hg1.json | internal | 2026-10-26T20:37 | research results: through the registry and the one map |
| manifests/gaplab_ts1.json | internal | 2026-10-26T20:38 | research results: through the registry and the one map |
| manifests/hf_chronos_forward.json | internal | 2026-11-02T19:00 | the forecast record, spoken through the morning view |
| manifests/hfn1t.json | internal | 2026-11-03T12:59 | research results: through the registry and the one map (and data_audit.json step 2) |
| manifests/holdout_candidates.json | internal | 2026-11-02T19:02 | research workfile (sealed holdout list) |
| manifests/impact.json | internal | 2026-11-02T19:02 | ops: lineage impact |
| manifests/integrity.json | nightly | 2026-11-02T19:03 |  |
| manifests/kite_1m_fo.jsonl | internal | 2026-11-03T12:35 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_5minute.jsonl | internal | 2026-11-03T08:15 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_depth.jsonl | internal | 2026-11-03T05:01 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_fill.json | feeds | 2026-11-03T08:17 | input to the stock 5-minute candles (india.kite_fill) |
| manifests/kite_index.jsonl | internal | 2026-11-03T05:20 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_minute.jsonl | internal | 2026-11-03T08:17 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/lab3_bt1.json | internal | 2026-10-27T09:26 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab3_ca1.json | internal | 2026-10-27T09:26 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab3_cp1.json | internal | 2026-10-27T09:26 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab3_os1.json | internal | 2026-10-27T09:26 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab3_vl1.json | internal | 2026-10-27T09:26 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab4_gk1.json | internal | 2026-10-27T18:35 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab4_ib1.json | internal | 2026-10-27T18:37 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab4_ms1.json | internal | 2026-10-27T18:37 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab5_cl1.json | internal | 2026-10-29T22:41 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab5_dr1.json | internal | 2026-10-29T22:27 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab5_fp1.json | internal | 2026-10-29T22:33 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab5_rx1.json | internal | 2026-10-28T12:31 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab5_rx2.json | internal | 2026-10-29T08:39 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab5_rx3.json | internal | 2026-11-02T19:22 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/lab6_rs1.json | internal | 2026-11-02T19:09 | research results: reach the Ask through the registry and the one map (knowledgemap) |
| manifests/leakcheck.json | nightly | 2026-11-03T12:55 |  |
| manifests/lineage.json | nightly | 2026-11-03T08:29 |  |
| manifests/macro.jsonl | internal | 2026-11-03T13:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/market_context.json | live | 2026-11-03T13:04 |  |
| manifests/mf_history.jsonl | internal | 2026-11-02T19:05 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/mf_schemes.json | live | 2026-11-03T05:21 |  |
| manifests/missed_DATE.json | internal | 2026-11-02T21:30 | missed movers; reaches the Ask through the read model's learning section |
| manifests/notable_results.json | nightly | 2026-11-03T12:59 | read by india/readmodel.py (path built in code) |
| manifests/nse_holidays.json | live | 2026-11-02T21:00 |  |
| manifests/options_realism.json | internal | 2026-11-02T19:02 | research workfile behind the options line's realistic fills |
| manifests/others_DATE.json | internal | 2026-11-02T21:30 | the reference traders; reaches the Ask through the read model's learning section |
| manifests/pr_zip.jsonl | internal | 2026-11-03T02:32 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/premarket_chain.json | live | 2026-11-02T22:00 |  |
| manifests/premarket_inputs.json | internal | 2026-11-02T22:00 | input to the morning view's build |
| manifests/quotebook.json | live | 2026-11-03T13:04 |  |
| manifests/quotebook_names.json | live | 2026-11-03T13:04 |  |
| manifests/r2_verify.json | internal | 2026-11-03T13:03 | ops: backup check |
| manifests/results_html.jsonl | internal | 2026-11-03T13:35 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/results_index_integrated_v2.jsonl | internal | 2026-11-03T12:49 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/results_today.json | nightly | 2026-11-02T22:00 |  |
| manifests/sealed_access.jsonl | internal | 2026-11-03T13:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/sectormap.jsonl | internal | 2026-11-03T12:58 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/sectormap_build.json | internal | 2026-11-03T12:58 | a build receipt |
| manifests/sensitivity_compare.json | internal | 2026-10-29T22:12 | research workfile |
| manifests/sensitivity_jumps.json | internal | 2026-10-29T22:00 | research workfile |
| manifests/settle_vs_tradable.json | internal | 2026-11-02T19:02 | research workfile |
| manifests/sp1_nightly_replay.json | internal | 2026-11-03T07:53 | ops: the options line's replay check |
| manifests/sp1_nightly_replay.jsonl | internal | 2026-11-03T07:53 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/technicals.json | live | 2026-11-03T13:03 |  |
| manifests/test_ledger.jsonl | live | 2026-11-03T12:59 |  |
| manifests/trials.json | live | 2026-11-03T13:04 |  |
| manifests/us_close.jsonl | nightly | 2026-11-02T21:00 |  |
| manifests/v02t.json | internal | 2026-11-03T12:28 | research results: through the registry and the one map (and data_audit.json step 2) |
| manifests/valuation.jsonl | internal | 2026-11-03T12:58 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/valuation_build.json | internal | 2026-11-03T12:58 | a build receipt |
| manifests/voice_check_history.jsonl | live | 2026-11-03T13:00 |  |
| manifests/voice_check_latest.json | live | 2026-11-03T13:00 |  |
| manifests/w500.json | internal | 2026-11-03T12:06 | research results: reach the Ask through the registry and the one map (and data_audit.json step 4) |
| paper/account/benchmark.jsonl | feeds (daytime) | 2026-11-03T08:09 | input to paper/account/view.json (india.account run) |
| paper/account/frozen.json | live (daytime) | 2026-10-29T23:08 |  |
| paper/account/state.json | live (daytime) | 2026-11-03T08:09 |  |
| paper/account/view.json | live (daytime) | 2026-11-03T08:09 |  |
| paper/allocation_ledger.jsonl | internal | 2026-11-03T08:09 | the allocator's ledger (its view is what is read) |
| paper/allocation_view.json | live (daytime) | 2026-11-03T08:09 |  |
| paper/baseline.parquet | nightly | 2026-11-02T21:30 |  |
| paper/baseline_closed.parquet | internal | 2026-11-02T21:30 | research book workfile |
| paper/calls.jsonl | live | 2026-11-02T19:04 |  |
| paper/dayplans/DATE.json | live | 2026-11-02T19:00 | read by jarvis/india/views.py (path built in code) |
| paper/decisions/DATE.json | live | 2026-11-02T21:30 |  |
| paper/decisions/DATE.universe.json | nightly | 2026-11-02T21:30 |  |
| paper/events.jsonl | live | 2026-11-02T21:30 |  |
| paper/factorbook/marks.jsonl | nightly | 2026-11-02T19:04 |  |
| paper/factorbook/state.json | nightly | 2026-11-02T19:04 |  |
| paper/factorbook/view.json | nightly | 2026-11-02T19:04 |  |
| paper/filter_slices.csv | nightly | 2026-11-02T21:30 |  |
| paper/forecasts.jsonl | nightly | 2026-11-02T22:06 |  |
| paper/managed/ledger.jsonl | internal | 2026-11-02T19:06 | the managed book's hash-chained ledger (its state and view are what is read) |
| paper/managed/plans.jsonl | internal | 2026-11-02T19:06 | the plan history (the latest plan is read through the managed view) |
| paper/managed/score.json | live | 2026-11-02T19:06 |  |
| paper/managed/state.json | live | 2026-11-02T19:06 |  |
| paper/managed/view.json | live | 2026-11-02T19:06 |  |
| paper/marks.jsonl | live | 2026-11-02T21:30 |  |
| paper/morningview/DATE.json | live (daytime) | 2026-11-02T23:50 | read by jarvis/india/views.py (path built in code) |
| paper/morningview/latest.json | live (daytime) | 2026-11-02T23:50 |  |
| paper/news_read/DATE.json | internal | 2026-11-02T19:04 | the news model's daily read of movers: the record behind the news study |
| paper/news_read/log.jsonl | internal | 2026-11-02T19:04 | the news model's daily read of movers: the record behind the news study |
| paper/options_trades.jsonl | nightly | 2026-10-28T19:09 |  |
| paper/others_history.jsonl | feeds | 2026-11-02T21:30 | input to manifests/others_DATE.json (india.others) |
| paper/reconstruction/DATE.json | live | 2026-11-02T21:30 | read by jarvis/india/ask.py (path built in code) |
| paper/reconstruction/decisions.jsonl | live | 2026-10-31T15:39 |  |
| paper/reconstruction/forwarded.jsonl | live | 2026-10-31T22:50 |  |
| paper/reconstruction/latest.json | live | 2026-11-02T21:30 |  |
| paper/reconstruction/netnotes/DATE.jsonl | live | 2026-11-02T21:40 | read by jarvis/india/ask.py (path built in code) |
| paper/rs_trial.json | live | 2026-11-02T19:26 |  |
| paper/rx1_trial.json | live | 2026-11-02T19:06 |  |
| paper/shadow/DATE.json | live | 2026-11-02T22:06 | read by jarvis/india/views.py (path built in code) |
| paper/shadow/summary.json | live | 2026-11-03T13:04 |  |
| paper/sp1/book.json | live (daytime) | 2026-11-03T07:00 | read by jarvis/india/views.py (path built in code) |
| paper/sp1/decisions.jsonl | live (daytime) | 2026-11-02T23:45 |  |
| paper/sp1/outcomes.jsonl | feeds | 2026-11-03T07:00 | input to paper/sp1/book.json (india.sp1paper score) |
| paper/sp1/plans/DATE.json | internal | 2026-11-02T21:01 | the options line's plan files (the decisions ledger is read live) |
| paper/sp1/work/score_outcomes.parquet | internal | 2026-11-03T07:00 | research book workfile |
| paper/state.json | live | 2026-11-02T21:30 |  |
| paper/teachers/forward_options.jsonl | live | 2026-11-02T19:00 | read by jarvis/india/views.py (path built in code) |
| paper/teachers/forward_options_summary.json | live | 2026-11-02T19:00 |  |
| paper/teachers/live_signals.parquet | internal | 2026-11-02T19:01 | research book workfile |
| paper/teachers/live_summary.json | live | 2026-11-02T19:01 |  |
| readmodel/DATE.json | internal | 2026-11-03T13:04 | the read model itself |
| readmodel/latest.json | live | 2026-11-03T13:04 |  |
| reports/DATE.md | internal | 2026-11-02T21:30 | a written report for Madhav (the morning review page) |
| reports/ask_guard.jsonl | live | 2026-11-02T16:37 |  |
| reports/portfolio_DATE.md | internal | 2026-11-02T19:04 | a written report for Madhav (the morning review page) |
