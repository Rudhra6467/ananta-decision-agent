# HL-RX camera: result (written 2026-10-15 from the surviving records)

HL-RX asked a different question from "find a good trader". Other traders are event generators, never teachers or copy signals (decision D8). The benchmark is the market at time T and the path after T.
The question: when something objectively interesting happened, was Ananta looking, did it recognise it, did its knowledge cover it, and why did it act or not.

Source: the status document of 2026-09-27 (section "Job B"). The camera code and its raw results were not found anywhere on the owner's machines, so this file is the whole record. Nothing here can be re-run.

## What was measured

Window: 72 hours, 2026-09-22 to 2026-09-25. One public wallet hit the 2,000-fill API cap, so the window is truncated.

| Step | Result |
|---|---|
| Raw fills | 2,079 |
| Episodes after normalising | 1,593 |
| Hold class | 981 tactical, 40 directional-read, 572 incompatible |
| Outside the 10-coin universe | 1,506 unsupported-asset rows, never replayed |
| Eligible once a 1-hour spine existed | 62 |
| Ananta snapshot on the same 1-hour bar | 0 of 62 (and 0 of 1,593) |
| Matched comparison cases | 0 |
| Diagnosis rows | 0 |
| Writes into trusted memory, rank or paper | 0 |

The 62 eligible events by coin: LTC 18, BCH 9, XRP 8, DOGE 7, ADA 6, ETH 6, SOL 6, BTC 1, LINK 1. Of the 62, 8 look like the external trade worked, 4 look like it failed, 50 are unresolved.
All 62 are classified NO_SNAPSHOT_AT_T: the Agent had not saved a decision row for that bar, and a live decision is never invented for a bar it did not persist. That is a legal result; it is not "Ananta missed a trade".

Version 1.0 of the camera could not even mark eligibility because the lab spine was not mounted. Version 1.1 built a 730-bar 1-hour spine from Hyperliquid candles and checked that BTC and ETH closed bars end at or before the entry time (no future bar in the features).
The join key was re-run afterwards and still matched 0. The 62 events are historically unmatchable; scoring them again cannot create a snapshot that was not written.

## From the owner's notes only (no file holds these)

- One participant, holding about 9 minutes, on the 2026-09-25 13:00Z bar. The same notes mention a 54 short / 8 long split; what it counts is not recorded.
- A later sandbox replay of published defaults gave 57 insufficient data and 5 detected (one a DOGE 10-minute continuation). It was never compared with the live Hands engine, and parity with Hands is unproven.

## CASE-0001

Two meanings exist and they are different. In the status document, CASE-0001 is the first Hyperliquid event whose coin and hour overlap an Ananta decision row; none has happened yet, and until then every result is NO_SNAPSHOT, which the document calls fine.
In the owner's notes the same label was used for a Hands-versus-L2 regime disagreement on SOL (n = 1). That is a separate item and is not a result of this camera.

## Verdict

DUMP (`audit_v1.json`, row `STUDY:HL_RX`). It produced no matched case, wrote nothing into memory or paper, and cannot count toward any behaviour gate. The teacher stays closed until a future external event lands on a bar where an Ananta decision row already exists.
Rule B: no new study of this kind during the evidence window. Whether to collect Hyperliquid fills continuously so the question can be asked again is an owner decision (`OD-HL-FILLS` in `../knowledge/due_list.json`); the quarterly other-traders study (`Q-R2-HL`) pulls fresh fills by hand.
After the window, the question is listed as `PW-HL-RX` in the same file.
