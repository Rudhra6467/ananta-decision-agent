# Fact map 2026-11-02T19:33

Fact map 2026-11-02T19:33: 142 kinds of file written in 8 days; 43 read live, 16 after the nightly build, 5 feed another file, 5 copied into words by hand, 73 internal, 0 with no route. No FAIL.

| check | state | words |
|---|---|---|
| behind: manifests/evidence_log.jsonl | NOTE | manifests/evidence_log.jsonl is 6.2 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: manifests/integrity.json | NOTE | manifests/integrity.json is 6.2 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: manifests/leakcheck.json | NOTE | manifests/leakcheck.json is 6.6 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: manifests/lineage.json | NOTE | manifests/lineage.json is 6.2 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: manifests/notable_results.json | NOTE | manifests/notable_results.json is 6.2 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: manifests/us_close.jsonl | NOTE | manifests/us_close.jsonl is 6.1 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: paper/factorbook/marks.jsonl | NOTE | paper/factorbook/marks.jsonl is 6.2 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: paper/factorbook/state.json | NOTE | paper/factorbook/state.json is 6.2 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: paper/factorbook/view.json | NOTE | paper/factorbook/view.json is 6.2 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| behind: paper/forecasts.jsonl | NOTE | paper/forecasts.jsonl is 6.1 h newer on disk than the read model Ananta answers from; it is seen after the next build |
| fresh: manifests/market_context.json | PASS | manifests/market_context.json is newer than all its inputs |
| fresh: manifests/quotebook.json | PASS | manifests/quotebook.json is newer than all its inputs |
| Today screen Nifty = what Ananta says | PASS | screen Nifty · Mon 2 Nov close 23,441; Ananta 23,440.80 (at the close of Monday 2 Nov, the last session (the next opens Tuesday 3 Nov 09:15 IST)) |
| options screen trades = the options ledger | PASS | screen [('BANKNIFTY', 'D1'), ('NIFTY', 'D2')]; ledger (2026-11-02) [('BANKNIFTY', 'D1'), ('NIFTY', 'D2')] |

| file | route | written | why |
|---|---|---|---|
| manifests/announce_api.jsonl | internal | 2026-11-02T19:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/cm_bhavcopy.jsonl | internal | 2026-11-02T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/corporate_actions.jsonl | internal | 2026-11-02T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/data_inventory.json | internal | 2026-11-02T19:02 | ops: the data inventory (read by lineage and the morning review) |
| manifests/datacheck.json | internal | 2026-10-29T21:55 | ops: freshness check (morning review) |
| manifests/dataset_versions.jsonl | internal | 2026-11-02T19:03 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/deals_build.json | internal | 2026-11-02T19:04 | a build receipt |
| manifests/deals_snapshot.jsonl | internal | 2026-11-02T19:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/delivery.jsonl | internal | 2026-11-02T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/diistudy_dii1.json | copied | 2026-10-26T13:00 | its findings are written into jarvis/india/marketcontext.py by hand: a re-run must update those words |
| manifests/evidence_log.jsonl | nightly | 2026-11-02T19:04 |  |
| manifests/exam_history.jsonl | internal | 2026-10-30T02:39 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/exam_latest.json | live | 2026-10-30T02:39 |  |
| manifests/fii_dii_build.json | internal | 2026-11-02T19:05 | a build receipt |
| manifests/fii_dii_cash.jsonl | internal | 2026-11-02T19:04 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/fii_dii_coverage.json | feeds | 2026-10-26T13:02 | input to manifests/market_context.json (india.fiidii build) |
| manifests/fii_dii_history.jsonl | internal | 2026-11-02T12:50 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/firewall.json | internal | 2026-11-02T12:51 | ops: sealed-data firewall |
| manifests/flows_participant_oi.jsonl | internal | 2026-11-02T12:47 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/fo_ban.json | nightly | 2026-11-01T23:00 |  |
| manifests/fo_bhavcopy.jsonl | internal | 2026-11-02T12:45 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/gaplab_gp1.json | internal | 2026-10-29T22:04 | research results: through the registry and the one map |
| manifests/gaplab_gp1_diag.json | internal | 2026-10-26T20:39 | research results: through the registry and the one map |
| manifests/gaplab_hg1.json | internal | 2026-10-26T20:37 | research results: through the registry and the one map |
| manifests/gaplab_ts1.json | internal | 2026-10-26T20:38 | research results: through the registry and the one map |
| manifests/hf_chronos_forward.json | internal | 2026-11-02T19:00 | the forecast record, spoken through the morning view |
| manifests/holdout_candidates.json | internal | 2026-11-02T19:02 | research workfile (sealed holdout list) |
| manifests/impact.json | internal | 2026-11-02T19:02 | ops: lineage impact |
| manifests/integrity.json | nightly | 2026-11-02T19:03 |  |
| manifests/kite_1m_fo.jsonl | internal | 2026-11-02T12:36 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_depth.jsonl | internal | 2026-11-02T05:01 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_fill.json | feeds | 2026-10-26T06:51 | input to the stock 5-minute candles (india.kite_fill) |
| manifests/kite_index.jsonl | internal | 2026-11-02T12:37 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/kite_minute.jsonl | internal | 2026-10-26T06:51 | an ingest or run log; the data it records reaches Ananta through the built tables |
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
| manifests/leakcheck.json | nightly | 2026-11-02T19:27 |  |
| manifests/lineage.json | nightly | 2026-11-02T19:04 |  |
| manifests/macro.jsonl | internal | 2026-11-02T19:05 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/market_context.json | live | 2026-11-02T19:05 |  |
| manifests/mf_history.jsonl | internal | 2026-11-02T19:05 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/mf_schemes.json | live | 2026-11-02T19:05 |  |
| manifests/missed_DATE.json | internal | 2026-11-01T22:30 | missed movers; reaches the Ask through the read model's learning section |
| manifests/notable_results.json | nightly | 2026-11-02T19:06 | read by india/readmodel.py (path built in code) |
| manifests/nse_holidays.json | live | 2026-11-02T19:00 |  |
| manifests/options_realism.json | internal | 2026-11-02T19:02 | research workfile behind the options line's realistic fills |
| manifests/others_DATE.json | internal | 2026-11-01T22:30 | the reference traders; reaches the Ask through the read model's learning section |
| manifests/pr_zip.jsonl | internal | 2026-10-31T02:32 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/premarket_chain.json | nightly | 2026-11-01T23:00 |  |
| manifests/premarket_inputs.json | internal | 2026-11-01T23:00 | input to the morning view's build |
| manifests/quotebook.json | live | 2026-11-02T19:05 |  |
| manifests/quotebook_names.json | live | 2026-11-02T19:05 |  |
| manifests/r2_verify.json | internal | 2026-11-02T12:52 | ops: backup check |
| manifests/results_index_integrated_v2.jsonl | internal | 2026-11-02T12:46 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/results_today.json | nightly | 2026-11-01T23:00 |  |
| manifests/sealed_access.jsonl | internal | 2026-11-02T19:33 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/sectormap.jsonl | internal | 2026-11-02T12:50 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/sectormap_build.json | internal | 2026-11-02T12:50 | a build receipt |
| manifests/sensitivity_compare.json | internal | 2026-10-29T22:12 | research workfile |
| manifests/sensitivity_jumps.json | internal | 2026-10-29T22:00 | research workfile |
| manifests/settle_vs_tradable.json | internal | 2026-11-02T19:02 | research workfile |
| manifests/sp1_nightly_replay.json | internal | 2026-11-02T19:00 | ops: the options line's replay check |
| manifests/sp1_nightly_replay.jsonl | internal | 2026-11-02T19:00 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/technicals.json | live | 2026-11-02T12:53 |  |
| manifests/test_ledger.jsonl | live | 2026-11-02T19:22 |  |
| manifests/trials.json | live | 2026-11-02T19:29 |  |
| manifests/us_close.jsonl | nightly | 2026-11-02T19:00 |  |
| manifests/valuation.jsonl | internal | 2026-11-02T12:50 | an ingest or run log; the data it records reaches Ananta through the built tables |
| manifests/valuation_build.json | internal | 2026-11-02T12:50 | a build receipt |
| manifests/voice_check_history.jsonl | live | 2026-11-02T18:27 |  |
| manifests/voice_check_latest.json | live | 2026-11-02T18:27 |  |
| manifests/xstudies_fii1.json | copied | 2026-10-26T11:31 | its findings are written into jarvis/india/marketcontext.py by hand: a re-run must update those words |
| manifests/xstudies_fx1.json | copied | 2026-10-26T11:31 | its findings are written into jarvis/india/marketcontext.py by hand: a re-run must update those words |
| manifests/xstudies_sr1.json | copied | 2026-10-26T12:24 | its findings are written into jarvis/india/marketcontext.py by hand: a re-run must update those words |
| manifests/xstudies_xo1.json | copied | 2026-10-26T11:31 | its findings are written into jarvis/india/marketcontext.py by hand: a re-run must update those words |
| paper/account/benchmark.jsonl | feeds (daytime) | 2026-11-02T19:33 | input to paper/account/view.json (india.account run) |
| paper/account/frozen.json | live (daytime) | 2026-10-29T23:08 |  |
| paper/account/state.json | live (daytime) | 2026-11-02T19:33 |  |
| paper/account/view.json | live (daytime) | 2026-11-02T19:33 |  |
| paper/allocation_ledger.jsonl | internal | 2026-11-02T19:33 | the allocator's ledger (its view is what is read) |
| paper/allocation_view.json | live (daytime) | 2026-11-02T19:33 |  |
| paper/baseline.parquet | nightly | 2026-11-01T22:30 |  |
| paper/baseline_closed.parquet | internal | 2026-11-01T22:30 | research book workfile |
| paper/calls.jsonl | live | 2026-11-02T19:04 |  |
| paper/dayplans/DATE.json | live | 2026-11-02T19:00 | read by jarvis/india/views.py (path built in code) |
| paper/decisions/DATE.json | live | 2026-10-30T22:30 |  |
| paper/decisions/DATE.universe.json | nightly | 2026-10-30T22:30 |  |
| paper/events.jsonl | live | 2026-10-30T22:30 |  |
| paper/factorbook/marks.jsonl | nightly | 2026-11-02T19:04 |  |
| paper/factorbook/state.json | nightly | 2026-11-02T19:04 |  |
| paper/factorbook/view.json | nightly | 2026-11-02T19:04 |  |
| paper/filter_slices.csv | nightly | 2026-11-01T22:30 |  |
| paper/forecasts.jsonl | nightly | 2026-11-02T19:00 |  |
| paper/managed/ledger.jsonl | internal | 2026-11-02T19:06 | the managed book's hash-chained ledger (its state and view are what is read) |
| paper/managed/plans.jsonl | internal | 2026-11-02T19:06 | the plan history (the latest plan is read through the managed view) |
| paper/managed/score.json | live | 2026-11-02T19:06 |  |
| paper/managed/state.json | live | 2026-11-02T19:06 |  |
| paper/managed/view.json | live | 2026-11-02T19:06 |  |
| paper/marks.jsonl | live | 2026-11-01T22:30 |  |
| paper/morningview/DATE.json | live (daytime) | 2026-11-02T00:50 | read by jarvis/india/views.py (path built in code) |
| paper/morningview/latest.json | live (daytime) | 2026-11-02T00:50 |  |
| paper/news_read/DATE.json | internal | 2026-11-02T19:04 | the news model's daily read of movers: the record behind the news study |
| paper/news_read/log.jsonl | internal | 2026-11-02T19:04 | the news model's daily read of movers: the record behind the news study |
| paper/options_trades.jsonl | live (daytime) | 2026-10-28T19:09 |  |
| paper/others_history.jsonl | feeds | 2026-11-01T22:30 | input to manifests/others_DATE.json (india.others) |
| paper/reconstruction/DATE.json | live | 2026-11-01T22:30 | read by jarvis/india/ask.py (path built in code) |
| paper/reconstruction/decisions.jsonl | live | 2026-10-31T15:39 |  |
| paper/reconstruction/forwarded.jsonl | live | 2026-10-31T22:50 |  |
| paper/reconstruction/latest.json | live | 2026-11-01T22:30 |  |
| paper/reconstruction/netnotes/DATE.jsonl | live | 2026-10-30T22:40 | read by jarvis/india/ask.py (path built in code) |
| paper/rs_trial.json | live | 2026-11-02T19:26 |  |
| paper/rx1_trial.json | live | 2026-11-02T19:06 |  |
| paper/shadow/DATE.json | live | 2026-11-02T19:00 | read by jarvis/india/views.py (path built in code) |
| paper/shadow/summary.json | live | 2026-11-02T19:00 |  |
| paper/sp1/book.json | live (daytime) | 2026-11-02T12:37 | read by jarvis/india/views.py (path built in code) |
| paper/sp1/decisions.jsonl | live (daytime) | 2026-11-01T23:15 |  |
| paper/sp1/outcomes.jsonl | feeds | 2026-11-02T07:00 | input to paper/sp1/book.json (india.sp1paper score) |
| paper/sp1/plans/DATE.json | internal | 2026-11-01T22:01 | the options line's plan files (the decisions ledger is read live) |
| paper/sp1/work/score_outcomes.parquet | internal | 2026-11-02T12:37 | research book workfile |
| paper/state.json | live | 2026-11-01T22:30 |  |
| paper/teachers/forward_options.jsonl | live | 2026-11-02T19:00 | read by jarvis/india/views.py (path built in code) |
| paper/teachers/forward_options_summary.json | live | 2026-11-02T19:00 |  |
| paper/teachers/live_signals.parquet | internal | 2026-11-02T19:01 | research book workfile |
| paper/teachers/live_summary.json | live | 2026-11-02T19:01 |  |
| readmodel/DATE.json | internal | 2026-11-02T12:53 | the read model itself |
| readmodel/latest.json | live | 2026-11-02T12:53 |  |
| reports/DATE.md | internal | 2026-11-02T19:04 | a written report for Madhav (the morning review page) |
| reports/ask_guard.jsonl | live | 2026-11-02T16:37 |  |
| reports/portfolio_DATE.md | internal | 2026-11-02T19:04 | a written report for Madhav (the morning review page) |
