# Grok-era errata (written 2026-10-15)

The September 2026 research (H1-H6, SET1-SET16, MSM, MRD-1 to MRD-7, ME1-ME5, N3, N4, the fade, the exit maps, the PD cards and the packs) was done in a separate folder of
scripts, JSON files and documents that is not tracked in git. Those files are frozen: they are never edited, so a wrong number there stays wrong in the file.
This document is where the corrections go. `RESEARCH_RULES.md` (section 1, "Errata") points here.

How to use it: before quoting any Grok-era number, find its file name below. Each entry says what the file says, what is true, and how that was checked.
"Re-derived 2026-10-15" means the figure was recomputed read-only from the freeze copy of the data (`lab10_15m_merged.freeze_2026-09-12.sqlite`, sha256 `7921e98d66325cda263e6922ae58950f0297f4434759ec2305b14a7537e2f58b`).
Nothing here changes a verdict that was already NOT_ECONOMIC, REJECTED or DUMP; where an entry weakens a result, it says so.

The ratings of these files (KEEP, RETIRE, PARK and the reasons) are in `AUDIT_V2.md` and, row by row, in `../knowledge/audit_register.json`.

## Costs

### E-001 Fee tables charged 0-10 basis points for a round trip
Applies to: `phase3_cost_test_v1`, `set14_lag_birth_fee_v1`, `set16_move_lag_fee_v1` (all three use `FEES = (0, 4, 8, 10)`), and `oos_h1_h3_h4_sep2026` (`FEE_BP = 8`).
Fact: every SURVIVES_FEE, MARGINAL and KILLED_BY_FEE verdict in these four files charged 0-10 basis points for a whole round trip. Real paper costs on the lab coins are 0.57-1.20% round trip
(`src/intelligence/ndax_costs.py`; NDAX's fee alone is 0.40% for a round trip), and 0.8-2.4% on other coins. SET16 takes 0-10 bp off a gross move of 34, 10 and 22 bp; one long leg costs 56.8-120.0 bp.
None of these "survives fees" verdicts holds at real costs. `RESEARCH_RULES.md` section 5 now bans such tables for any decision.
Check: the constants are on the lines named above; the real costs are computed from `ndax_costs.py` (the median of 5 order-book snapshots on 2026-09-29, `CANDIDATE_V3.md` line 32).

### E-002 Master Blueprint v1 was never locked; its "8 bp kill" is a placeholder
Applies to: `Ananta_Agent_Master_Blueprint_v1.docx` ("Draft for operator lock. Not yet LOCKED." and "Fees 8 bp kill. n<30 = INSUFFICIENT.").
Fact: no operator lock was ever applied. The 8 bp figure is the same placeholder as E-001. The lock that applies to money is `LOCK.md`.

## Data

### E-003 No ETH 15-minute bars from 2026-04-01 to 2026-09-03
Applies to: `lab10_15m_merged` and its freeze copy, `binance_15m_canonical`, `inventory_lab10_gaps_v1.json`, every "OOS from 2026-08-01" figure, and the folder of Binance monthly files.
Fact: ETH-USD-SPOT has no 15-minute bars from 2026-04-01 00:00 to 2026-09-03 23:45 UTC in the merged tape, its freeze copy or the canonical file. March 2026 ends with 2,976 Kraken rows;
the next row is 2026-09-04 00:00 (Binance). ETH's 763 Binance bars start on 2026-09-04.
The April-August monthly files in the Binance download folder are `ETHFIUSDT` (a different token, first open 0.4781), not `ETHUSDT`; ETHFI was never ingested.
`inventory_lab10_gaps_v1.json` flags only 1000PEPE (`"missing_sep_2026"`) because it only checks September, so it hides this gap.
Consequence: Grok-era 15-minute results for April-August 2026, including every "OOS from 2026-08-01" figure, contain no ETH. September-only figures have ETH from Sep 4 only (763 of 1,051 bars).
The lake (`~/ananta_lake`) has ETHUSDT for every month, so any re-run should read the lake.

### E-004 The merged tape changes venue on 2026-04-01 (Kraken USD to Binance USDT) with no conversion
Applies to: `lab10_15m_merged` and freeze copy, every H1, SET, MSM and PD result that compares "OOS" with history.
Fact: lab coins in 2026-03 are `kraken.ohlcvt.15m` in USD (29,610 rows); in 2026-04 they are `binance.klines.15m` in USDT (25,920 rows, 9 coins). Bars keep the instrument name "-USD-SPOT" although the quote changed.
Volume is not comparable (mean 15-minute volume BTC 25.5 in March on Kraken against 164.3 in April on Binance; SOL 3,997.4 against 212,015.9).
The bars carry `source_code`, `quote` and `fill_rule`, but no H1, SET, MSM or PD script reads them.
Consequence: Kraken bars pass 3x their 20-bar volume average (vz >= 2) on 7.4-8.6% of bars per month (2025-01 to 2026-03); Binance bars do so on 2.9-4.1% in the same months, and on 2.9-3.5% from 2026-04.
The halving of the H1 gate rate in "OOS" comes from the venue change, so OOS gate rates are not comparable with history.

### E-012 DOGE's April-August 2026 15-minute bars are not Binance spot data
Applies to: `lab10_15m_merged` and freeze copy, any volume result on DOGE after 2026-03.
Fact: the bars come from `DOGEUSDT-15m-2026-04` to `-08` monthly files that have volume 0 in all 14,592 rows (trade count 894-900 per bar, 8-decimal prices). The lake's real spot bar for 2026-04-01 00:00 has volume 3,677,193.
The tape still labels them `binance.klines.15m`, and June has only 2,784 rows. DOGE therefore drops out of every volume result for those months. See also E-011 (the GAP state is DOGE).

### E-027 Freeze manifest hashes are placeholders, and the merged 15-minute tape is no longer the frozen file
Applies to: `freeze_5m_manifest_v1.json` (`sha256_5m` and `sha256_10m` read "OPERATOR_FILL"), `freeze_15m_manifest_v1.json`, `Ananta_Market_Regime_Dynamics_Lock_v1.docx`, and the "5M-SPINE" claim that the append extended the 5-minute file.
Fact (computed 2026-10-15): `lab5_5m.sqlite` (8,128,104 bars) has sha256 `707c4e7c899089b2313b74933e3eb62c5b5b0bc32e93d7828e91f5bb6718ba69`; `lab10m_derived.sqlite` (4,064,010 bars) has sha256 `f96bc9042add88052f4b1ebfb8e931312dfd278317b9ab389c18e7b874b564ef`. Both match the hashes in the Lock docx.
The 15-minute freeze copy `lab10_15m_merged.freeze_2026-09-12.sqlite` still has sha256 `7921e98d66325cda263e6922ae58950f0297f4434759ec2305b14a7537e2f58b`, the value in the docx.
The working file `lab10_15m_merged.sqlite` now has sha256 `574b6766f079f17f742d97ce849a2904e792b3e12470c198264f4657d3fce3b8`: it was modified on 2026-09-20 by the 09-17 append script and is no longer the frozen tape.
For any re-run of a Grok-era 15-minute study: read the freeze copy and record this hash; the 5-minute fingerprints above are owed to every study that reuses those files (13 files in `src/research`).

### E-028 The "5y" labels in the 15-minute ingest cover 4.55 years
Applies to: `ingest_lab10_15m.py` (`window_5y_count`, `gaps_in_5y`, `gaps_5y`). `phase3_lab10_15m_screen.py` has no year label.
Fact: the window comes from `bar_contract_15m_v1.py` (1631404800 to 1775001600), which is 2021-09-12 to 2026-04-01: 4.55 years, not 5.

### E-029 The "Fiverr" vendor history was never delivered
Applies to: `History_Expand_Sequence_Lock_v1.docx` ("Until the Fiverr files are on disk...", "1 Land Fiverr dump"), `Two_Layer_Research_Lock_v1.docx` ("B0 Land Fiverr/vendor 5m dump"), `Market_Regime_Dynamics_Lock_v1.docx` ("Fiverr extra 15m"), and `seq_candle_run_v0.json` (`"depends_on": "Fiverr pre-era stamp + existing lab10"`).
Fact: these are plans. No such files exist on disk. `lab5_5m.sqlite` holds Binance public klines (`"source_code": "binance.klines.5m"`). The dependency "Fiverr pre-era stamp" of `seq.candle_run.v0` was never met.

## Definitions and numbers

### E-005 "vz" is a volume ratio, not a z-score
Applies to: every SET and H1 script, the Research Catalog, `phase4_year_split_v1.py` (which calls the ratio "volume z"), the Tag V11 Lock docx ("volume-z"), `pd1_vz_card_v1.json` and `pd1_vz_dist_v0.py`.
Fact: in every SET and H1 script and in the Research Catalog, vz is volume divided by its 20-bar average (the average includes the current bar) minus 1, so vz >= 2 means 3x that average.
PD-1 measured a true z-score instead, with other era cuts (2021-07-01 and 2025-08-01) and including 1000PEPE. Its "stable ~7%" and its cuts 2.45 and 3.0 therefore do not describe the H1 gate.
For the real gate (the ratio), the share of bars with vz >= 2 is 6.93% (early), 7.82% (late) and 5.94% (OOS) in PD-1's eras, and it halves when the tape switches to Binance (E-004). PD-1's own z-score shares are 6.94% / 7.04% / 6.72%, which match its JSON.
Check: re-run of the PD-1 bins on the freeze copy (2026-10-15). `RESEARCH_RULES.md` section 3 has the naming rule.

### E-006 SET4's "hot" bit, the retracted 14-cell pass, and its continuation bar
Applies to: `set4_state_table_v1.py` / `.json`, `set4_read_v1.py`, the Frames docx, the frozen registry row for SET4, `agent_research_record_v1.json` (line 39 lists "set4 cells").
Fact: SET4's hot bit is volume at least 2x its 20-bar average (`VZ_HI = 1.0`), not the 3x (vz >= 2) the Frames docx states.
The 14-cell OOS_PASS list in `set4_state_table_v1.json` was retracted on 2026-09-12 (registry: "2 cells VALIDATING; 14-wide OOS_PASS retracted"); only `vz0_mo1_st0_rv0` (30 OOS events) and `vz1_mo1_st1_rv1` (32 events) stayed VALIDATING, and the registry still shows them as VALIDATING.
Its continuation bars (0.58 / 0.55) sit below the rate at which all events continue (0.626 early, 0.629 late, 0.703 OOS), so a CONTINUE tag does not mean better than average. The two cells continue at 0.653 / 0.681 / 0.733 and 0.735 / 0.715 / 0.750.

### E-007 H1, SET14, SET16 and HOT numbers that differ between files
Applies to: H1's bins and OOS files (`phase4_h1_bins_v1`, `oos_h1_h3_h4_sep2026`, `oos_set2_h1_dir_sep2026`), `set14_lag_birth_v1`, `set16_move_lag_v1`, `disc_pass1`, `disc_pass2`, the Discovery Map docx, the registry.
Re-derived 2026-10-15 on the freeze copy:
- Discovery hot bars: 199,253. The bins file's 199,275 adds 22 ETH bars from Sep 4-10 (ETH was read to Sep 10 there, the other nine coins to Aug 31).
- H1's lift of 2.63 compares the top bin with the quietest bin (0.0218 / 0.00829). Against all bars the history lift is 2.06 (4,344/199,275 against 28,988/2,735,900), 2.31 before 2022 and 1.88 after.
- The sealed OOS lift of 2.69 is 8 events in 298 gated bars against 102 in 10,212. The 8 events fall on 4 days (Sep 3, 6, 10, 11). The 95% range for 8/298 gives a lift of 1.4 to 5.2, so the result did not beat history. The frozen registry row still says "lift 2.69 HOLDS", and the promised weekly September rescore never ran.
- The 298 gated bars in OOS-1 against 293 in OOS-2: five ETH bars on Sep 4 have a 20-bar volume average that reaches back to Kraken's 2026-03-31 bars (vz 5.85, 3.47, 4.90, 3.20, 2.55). OOS-1 counts them, OOS-2 skips them. None of the 8 sealed events is among them.
- SET16 OOS is 76 events (`set16_move_lag_v1`, matching the catalog's `n_oos`). The 49 in `disc_pass2` and the Discovery Map ("Existing SET16 card") are SET14 lag births carrying the SET16 flag, a different object.
- SET14 lag births OOS: 194. The 192 in the frozen JSON, `set14_lag_birth_fee_v1.py` and the catalog came from an earlier, shorter tape (Sep 12 13:36, before the 19:19 freeze).
- HOT births OOS: 353. The 358 in `disc_pass1` came from the live tape after the freeze (n_events 37,546 against 37,551).
- The stamp's early HOT births of 53,070 against 52,848 is a definition difference: the stamp resets the state at gaps and counts the first bar after one; the transition script counts only consecutive valid bars.
- "Big move" has two definitions: against the prior swing (`set4_state_table_v1`, `set8_session_v1`, `phase4_h1_bins_v1`) and against a swing that includes the bar itself (`set9_h1_path_v1`, `set11_effort_v1`, `set12_breadth_v1`). One bar can be at most the square root of 19 = 4.359 standard deviations from its own 20-bar window, so event rates of SET9, SET11 and SET12 do not compare with SET4, SET8 or discovery.

### E-008 "OOS" means four different windows
Applies to: all Grok-era files that say "OOS", "sealed" or "discovery".
Fact: Sep 1-11 2026 (OOS-1 and OOS-2: `oos_h1_h3_h4_sep2026.py`, `oos_set2_h1_dir_sep2026.py`); from 2026-08-01 (the research law's `discovery_end`, SET4, MSM `DISC_END`, the Frames docx, the SET campaigns); from 2025-08-01 (PD-1); and "late" from 2022-01-01 (most early/late splits).
The discovery cut is written as 08-31 in the registry for H1 ("through 2026-08-31 discovery cut; Sep 2026 sealed"), as 2026-08-01 in the law and all 16 campaign rows (stamped 2026-09-12 13:02-15:24 UTC, after the Sep 11 runs), and as 2026-07-31 in the Frames docx.
The H1 sealed test (lift 2.69, 10,212 bars, 8 events) covers 2026-09-01 to 09-11 only, not August ("Aug/Sep" in the Frames docx is wrong). H1-H5 read bars to 2026-08-31, so August is discovery data for them.
ETH's Sep 4-10 bars were already in the discovery files (22 hot bars; `phase4_events_v1.jsonl` has 8 events dated on or after 2026-09-01, all ETH), so September is not sealed for ETH.

### E-009 H6, SET1, SET2 and the catalog: stale statuses
Applies to: the frozen registry rows for H6, SET1 and SET2; `research_catalog_v1.json`; `registry_add_h6_v1.py`.
Fact: H6 was tested on 2026-09-01 to 09-11 (`oos_set2_h1_dir_sep2026.json`, written in the same second as the registry row): INSUFFICIENT, 8 events, all in the direction of the hot bar (5 of 5 up, 3 of 3 down), which is too few to judge. The registry's `oos_result` "pending_sep" is hard-coded at `registry_add_h6_v1.py:34` and stale.
SET1 and SET2 are shown ACTIVE (2026-09-12T13:02:12Z) but closed with all set hunting (the catalog's phase is `SET_HUNTING_CLOSED`).
H2-H5 are rejected (H2 and H5 REJECTED_STATISTICAL, H3 and H4 REJECTED_ECONOMIC) and are missing from `research_catalog_v1.json`, whose items are h1, set14, set16, msm.lifecycle, watch.score, hot.birth.set15, msm4.exhaust and fade.n4. H1's sample there is empty (`n_early`, `n_late`, `n_oos` null; evidence quality 7); the real counts are 2,735,900 bars (early 1,144,111, late 1,591,789) plus September's 10,212 bars, 298 gated, 8 events.
"Direction rejected via hot.birth.set15" refers to the coin's path against BTC (SET15: first +50 bp against BTC or -50 bp in 48 bars), not to H6's question of whether the hot bar's own sign predicts the sign of the next 4x RV event.

### E-010 Grok-era 15-minute scripts step by row, not by clock
Applies to: `oos_h1_h3_h4`, `phase4_*`, `set*`, `msm*` (for example `oos_h1_h3_h4_sep2026.py` lines 85-110; `msm1_market_stamp_v1.py` lines 17-18 and 198-199; `msm_v1_hot_birth_path_v1.py` lines 156-162).
Fact: "1 hour" is 4 rows back and "12 hours" is 48 rows ahead. Where bars are missing these are longer: 55.3% of bars before 2016 and 3.7% of 2016-2021 are followed by a gap of more than 15 minutes (0.71% from 2022). ETH's first September windows reach back to 2026-03-31 (E-003).
`RESEARCH_RULES.md` section 3 has the clock-time rule for new work. The live fingerprint (`src/tools/market_truth.py`) is trailing and unaffected.

### E-011 Smaller script defects
- `set14_events_dedup_v1`: skips a fixed 48 bars after each event; the "release at residual > -0.3%" in its docstring (and the `RELEASE` constant at line 21) was never coded.
- `seq2_10m_characterize_v0.json`: `p_next10_pos` pools up and down births and is not a continuation rate. Continuation is in `seq_10m_starters_v0.json` (0.46-0.47), which matches the lock docx.
- `phase4_h1_bins_v1.py` printed per-era rates but never saved them. Next-bar 4x RV rate by vz bin (<0, 0-0.4, 0.4-1, 1-2, >=2): early 0.00843, 0.01213, 0.01358, 0.01803, 0.02552 (base 0.01105); late 0.00819, 0.01218, 0.01375, 0.01608, 0.01935 (base 0.01027). Re-derived 2026-10-15 from the freeze copy.
- The MSM stamp's GAP state (about 9% of OOS coin-bars) is DOGE alone: its April-August 2026 bars have zero volume (E-012). GAP is a data defect, not market behaviour.

## Packs, registries and records

### E-013 The "load_pack" and runtime guardrails were never built
Applies to: `runtime_guardrails_v1.json` ("load_pack"), `Ananta_Runtime_Guardrails_v1.docx` ("Load set"), `agent_research_record_v1.json`, `agent_progress_pack_v1.json`, the PD cards.
Fact: the "Load set" was a next step ("Next build order ... Copy the JSON pack into Agent Ananta") that was never built. No code in either agent repo reads the pack files, `research_catalog_v1.json` or `agent_progress_pack_v1.json`.
The copy of `runtime_guardrails_v1.json` put in the agent folder on 2026-10-04 is read by nothing (it is identical to the frozen copy and untracked). The agent's knowledge is the hand-written `src/intelligence/knowledge_catalog_v1.json` (2026-09-21).
Check: `git grep` for these names over tracked files finds only a test that strips the id `runtime.guardrails.v1`.

### E-014 `context_cites_deployed = False` gated nothing
Applies to: `agent_decisions.sqlite` (1,136 rows stored 2026-09-29 12:21 to 2026-10-11 07:02 UTC that cite `card.mrd.sync_after_vol.v0`), `src/intelligence/cite_allowlist.py`.
Fact: the flag was copied into each row's evidence filter and version stamp but never switched anything; the three context cards (H1, size after volume, sync after volume) were always citable because they are in `LIVE_5`. Read these cites as labels, not as checks of a live value.
All 1,136 rows carry `context_cites_deployed = 0`. All 93 TAKE rows of 2026-09-29 to 10-10 cite h1, mrd.size and mrd.sync. A citation shows what the model was shown, not that it changed the decision (see `LOCK.md`, known limits).

### E-015 The first seven `agent_decisions` rows predate the decision writer
Applies to: `agent_decisions.sqlite` rowids 1-7 (the five `observer_15m` rows of 2026-09-19 22:00 to 09-20 17:45 UTC, `eth_1h_cycle`, `test_synthetic`).
Fact: they were written before the only writer existed (`decision_store.persist_snapshot`, commit d4534eb, 2026-09-22; it writes camera "hands_cycle" only). No code that writes `observer_15m` or `high_sync_one_book` was found anywhere. Treat them as hand-entered notes.

### E-016 `relationship_registry.sqlite` stops on 2026-09-12 15:24 UTC
Applies to: `ananta-quant-research-db/relationship_registry.sqlite` (untracked).
Fact: it holds 6 relationships (H1-H6), 16 campaigns (SET1-SET16), 40 candidates, 11 research laws. MSM, MRD-1 to MRD-7, N3 and N4 have no row in it; their results exist only in their own JSON files and are rated in `AUDIT_V2.md`.

### E-017 The "+15m" means in the decision-quality report are meaningless
Applies to: `decision_quality_report.json` (gitignored); for example Hunter historical WAIT "+15m" +48.01%, Bollinger TAKE 59.77%, Squeeze 43.91%.
Fact: they come from a 1-hour-stride replay; the file marks each one `usable: false` / `UNUSABLE_CLOCK`. Use only +1h and +4h. `DECISION_QUALITY_V0.md` line 76 already warns about this.

### E-018 `universe_knowledge.json` and `setup_memory_index.json` were regenerated empty
Applies to: the copies in `ananta-agent-research` (gitignored).
Fact: `universe_knowledge.json` (2026-10-11) was rebuilt without its replay book (0 rows) and lost the 6 WASH grades; the record is the 2026-09-03 copy in `ananta-decision-agent` (11,089 replay rows, 6 WASH, 36 TESTED_UNKNOWN).
`setup_memory_index.json` (2026-10-09) has `n_obs` 0 because its book `observation_replay.jsonl` exists only in `ananta-decision-agent`; use that copy (2026-10-05: 11,089 observations, 1,973 setups). Only `lab tables` reads them.

### E-019 `experiments_ledger.jsonl` holds five test rows
Fact: the 5 rows were written within one millisecond on 2026-08-23 (12:36:21) by a test run; the only `human` field reads "test". They are not real approvals. The real locks are in `docs/S5_HYPOTHESES.md` (2026-08-25).

### E-020 `lab_exit_map_1h_raw.json` is not the pass-1 result
Fact: it was overwritten on 2026-09-19 21:26 by a Hunter-only rerun (status LOCAL_1H_HUNTER; 7 / 9 / 6 entries; best PF 0.94). The pass-1 result (Sep 13: BTC 49 trades PF 0.79 expectancy -0.51, ETH 46 PF 0.54, SOL 45 PF 0.45, all NOT_ECONOMIC) is kept in `lab_exit_map_1h_split_v0.json` and in the Official Research Record docx ("Fade to Best PF").

### E-021 The fade ledger is not valid evidence
Applies to: `fade_ledger.jsonl`, `fade_ledger_stamped.jsonl`, `fade_outcomes.jsonl`.
Fact: every tick was written twice (`patch_lab_watch_fade.py:15` calls `print_eval(attach_to_record(record))`, which writes at `fade_watch.py:156` and again at `:171`); 239 of 819 lines had no timestamp and `fade_stamp.py:58` invented them by proportional spacing; the watch read the unfinished hourly candle (`fade_watch.py:62`); and the join priced each entry 1-2 hours after its signal (`fade_outcome_join.py:153` takes the close of the first 1-hour bar that starts at or after the signal), so the 15-minute outcome (`:167`) can end before its entry price.
The 3,348 joined rows are 186 ticks x 9 coins x 2 copies. Do not quote its hit rates.

### E-022 N3 and N4: sign counting, and an execution wall that was never in the path
Applies to: `n4_score.py`, `n3_gate.py`, `n4_gate.py`.
Fact: `n4_score.py` (lines 54-61) counts a coin as agreeing when its sign repeats in both windows, positive or negative, and makes a CANDIDATE at n >= 6 whatever the mix, so a mixed row (`vol_regime_ratio` VOL_LOW: 4 positive, 2 negative) passes the script and had to be rejected by hand.
Under pure chance that bar passes 37.7% of rows (193/512); a one-direction bar would pass 3.9% (10,343/262,144, assuming independent coins).
The `N3_EXECUTION_AUTHORIZED = False` and `N4_EXECUTION_AUTHORIZED = False` flags were never imported by any campaign script; the campaigns ran as standalone scripts, so the flags do not mean the campaigns were blocked.

### E-023 The S2 split files are the 57-trade Squeeze log
Applies to: `s2_hunter_sync_split_v0.json`, `s2_hunter_size_split_v0.json`, `s2_squeeze_size_split_v0.json`, `s2_squeeze_trade_log_fullspan_v0.json`, `s2_join_sync_v0.py`, `s2_join_size_v0.py`.
Fact: all three split files hold the 57 Squeeze trades; the two size files are the same file (md5 7e94a7805c9a536ce9fed28694d94c2c); the "hunter" names and ids (`s2.hunter.*`) are wrong, and the squeeze trade log carries the id `s2.hunter.trade_log.fullspan.v0`. No split was ever computed for Hunter's 16 trades.
The sync file's window label ("1y_from_2025-09-19_not_three_era") is also wrong: it holds an "early" cell (2 trades). Both join scripts hard-code "hunter" file names and ids (line 9 of each) and a fixed window label.
"Tried 4, survivors 0" appears in no file: the size splits record `candidates_tried` 3, the trade logs 1, and the Sep 27 status document says "tried 2, survivors 0". The correct statement: S2 made 2 distinct splits (sync, size), both on the 57 Squeeze trades; survivors 0.

### E-024 The MRD rules file, two "Watch Score" formulas, EXHAUSTING and the Foundation Map
- `agent_context_rules_mrd_v0.json` rejects the "5m lag-1 transfer-entropy candidate" in a list written at 2026-09-12 22:47:35, before the test existed (`mrd7_te_hl_v0.py` 23:04:06, its JSON 23:04:20). Treat the line as a prediction; the test is `mrd7_te_hl_v0.json`.
- "Watch Score" names two formulas: the 6-term evidence board (`watch_score_v0.py`) and the 7-term observer "attention" score (Research Catalog section 7, `msm_v1_observer_v1*.py`). Their numbers are not comparable. Separately, SET14's OOS sign is recorded as 7 in Construction_Close and 6 in Tag_V11_Lock; the script gives 4.3 with 6 and 4.5 with 7.
- EXHAUSTING (`msm3_lifecycle_tagger_v1.py:92-93`) only means the bar after a hot-volume bar no longer has hot volume (coin within 1% of BTC); it tests no price. The 75-81% HOT-to-EXHAUSTING rate is mostly this definition, not a failed price extension.
- `Ananta_MRD_Foundation_Map_v1.docx` (22:33:30) lists block intervals ("Formal CIs / block bootstrap") and "Transfer of information BTC to alt" as unknown. Both were measured later the same night, together with lead-lag: lead-lag `mrd5_leadlag_hl_v0.json` (same-sign about 0.45-0.50, 22:38), block intervals `mrd6_block_ci_v0.json` (22:43), transfer entropy `mrd7_te_hl_v0.json` (23:04). There is only one version of the Map.

### E-025 MRR-3 and the Foundation Map: quiet became more common, not stickier
Fact: the share of bars in the Low state rose from 0.33 to 0.471 to 0.613 across the three eras. The stay-Low rate divided by that share is 1.22, 1.20 and 1.14, so Low did not become more persistent; it became more common. Read any "persistence" claim for the Low state as a change in the base rate.

### E-026 `research_catalog_v1.json`: copied scores, no registry rows, empty counts
Fact: the quality scores in `research_catalog_v1.json` were copied, and the registry has 0 rows for these items (see E-016). H1's counts are null in it; the "10,991-row counts" comparison holds only for set14 (`n_early` 10,991, `n_late` 11,281, `n_oos` 192, see E-007 for 194). The hand-written `knowledge_catalog_v1.json` in the live repo now records these splits in `n_split` fields.
