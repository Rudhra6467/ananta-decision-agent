# Ananta Canada (research only)

A separate evidence lab for TSX stocks, started Oct 14, 2026. It shares no data, findings, parameters or
files with the crypto lab, and nothing here may wake the agent, trigger a trade or influence a decision.

- Plan: https://claude.ai/code/artifact/d038af31-baff-49d5-922b-ad9a565f7b8f
- C0 pre-registration (awaiting Madhav's approval): https://claude.ai/code/artifact/5c0cfa72-d128-46d4-b053-f9c4e564c1b4

## Where things live

| What | Where |
| --- | --- |
| Code | `canada/` (this folder; never under `docs/`, which the agent reads) |
| Registry (namespace CA) | `canada/registry/canada_status.json` |
| Frozen registrations | `canada/registrations/CA1.md` ... `CA5.md`, written only at approval, each with its SHA-256 in the registry |
| Data lake (2000-2023) | `~/ananta_data/canada/canada_lake.sqlite` (outside every crypto folder; `CANADA_DATA_DIR` overrides) |
| Sealed holdout (2024+) | `~/ananta_data/canada/sealed/canada_holdout.sqlite` |
| Raw pulls and manifests | `~/ananta_data/canada/raw/`, `~/ananta_data/canada/manifests/` |
| Tests | `tests/test_canada_isolation.py` |

## Rules the code enforces

1. `jarvis/` and `src/` never import `canada`; `canada` never imports them.
2. Research code calls `registry.assert_research_dates()` first; 2024+ is refused while the holdout is sealed.
3. `registry.freeze()` refuses without an approval note and refuses to re-freeze; a change is a new registration.
4. Costs are labelled ESTIMATE until measured spreads replace them.
5. Validation thresholds live once in `validation.py`; the cross-vendor test is dormant with a single vendor.

## Phases

C0 decide and pre-register -> C1 acquire -> C2 validate -> C3 baselines, costs, group atlas -> C4 run CA#1-5
-> C5 integration plan (only if a finding is ENOUGH and the crypto Rule A gate has passed). Each phase passes
its gate on persisted data, not on code that exists. Crypto reviews and fixes always come first.
