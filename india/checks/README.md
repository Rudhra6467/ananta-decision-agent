# Independent cross-checks

Bar-by-bar re-derivations written separately from the study engines (own loops, own ATR, own Black-76). Run before any study result is read.

- oc1_crosscheck_baseline.py / oc1_crosscheck_filtered.py: OC v1 (19 Oct): 486 + 255 index trades and 1,671 stock decisions, 0 mismatches.
- sp1_crosscheck.py / sp1_crosscheck_by_exit.py: SP1 outcomes (19 Oct): 160 random + 180 stratified (30 per exit), option leg included, 0 mismatches.
