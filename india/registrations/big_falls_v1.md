# The big-falls check, first version (3 Nov 2026)

Data audit step 6. Every one-day fall of over 45% in a stock ranked in the 500 most traded, with no applied split or bonus within 3 days, from the start of the features table to 2023. 137 falls. Nothing in the prices is changed by this check.

| label | what it means | all years | since 2010 |
|---|---|---|---|
| known_action_not_applied | a split or bonus is on file but was left out of the adjustment | 118 | 6 |
| likely_missed_action | looks like a split or bonus that is not on file | 0 | 0 |
| likely_demerger | a demerger or scheme was filed shortly before | 1 | 1 |
| no_evidence_found | no split, bonus or scheme found nearby: a true fall, or an action filed under an older symbol or a payout; needs a look | 18 | 18 |

## The ones to fix (not a true fall)

| date | stock | label | ratio | on file |
|---|---|---|---|---|
| 1995-05-24 | TATAPOWER | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1995-11-22 | CHETNADCEM | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 1996-01-24 | INDIACEM | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1996-08-07 | CROSLANDS | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1997-03-26 | OUDHSUG | known_action_not_applied | 1:10 split | UNCLEAR MANUAL_FLAG |
| 1997-10-27 | CENTENKA | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1997-11-05 | RELIANCE | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 1997-12-03 | CENTURYTEX | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1998-02-11 | PIRAMHELTH | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 1998-06-10 | APTECH | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1998-06-10 | SMITHKLPHA | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 1998-06-17 | MAX | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1999-02-02 | INDNIPPON | known_action_not_applied | 3:2 bonus | UNCLEAR MANUAL_FLAG |
| 1999-03-08 | BABABUSERV | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1999-03-24 | SOFTSOLINT | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 1999-05-19 | ACC | known_action_not_applied | 1:10 split | UNCLEAR MANUAL_FLAG |
| 1999-08-04 | FINCABLES | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2000-01-27 | RAMCOIND | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2000-03-08 | AUROPHARMA | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2000-05-02 | EIDERTELE | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2000-05-15 | GPELECT | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2000-05-31 | PIDILITIND | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2000-06-21 | ITIL | known_action_not_applied | 3:2 bonus | UNCLEAR MANUAL_FLAG |
| 2000-08-02 | ELGIEQUIP | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2000-09-13 | HUGHESSOFT | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2000-09-20 | WIDIA | known_action_not_applied | 1:20 | UNCLEAR MANUAL_FLAG |
| 2000-11-01 | HINDINKS | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-03-07 | ONWARDTEC | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-05-10 | BABABUSERV | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | ARCHIES | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | ATCOIND | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | BFLSOFTWAR | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | BGFL | known_action_not_applied | 1:4 / 3:1 bonus | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | CITICORSEC | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | CYBERTECH | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | ELECTCAST | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | GLOBLTRUST | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | INDUSINDBK | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | KLGSYSTEL | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | KOTAKMAH | known_action_not_applied | 3:2 bonus | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | LUPINLAB | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | MAARSOFTW | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | MOREPENLAB | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | NAVNETPUBL | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | ORCHIDCHEM | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | PENTACOMMU | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | SRIADIKARI | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | SUNDRMCLAY | known_action_not_applied | 1:4 / 3:1 bonus | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | TATAUNISYS | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-02 | TORNTPHARM | known_action_not_applied | 1:3 / 2:1 bonus | UNCLEAR MANUAL_FLAG |
| 2001-07-03 | EXCELIND | known_action_not_applied | 1:3 / 2:1 bonus | UNCLEAR MANUAL_FLAG |
| 2001-07-03 | UNICHEMLAB | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-07-24 | ALBRMORARJ | known_action_not_applied | 3:4 bonus | UNCLEAR MANUAL_FLAG |
| 2001-08-09 | SAITELE | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-09-05 | IVP | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2001-09-25 | EMCOTRANS | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2002-01-09 | STERLINTEA | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2002-11-12 | VAMORGANIC | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2003-04-10 | MASTEK | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2003-07-24 | AMTEKAUTO | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2003-10-25 | GLENMARK | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-01-19 | KABRAEXTRU | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-03-17 | UNICHEMLAB | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-03-24 | BERGEPAINT | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-07-08 | PREMINSTR | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-07-21 | JAGSNPHARM | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-07-27 | SHANTIGEAR | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-08-02 | GEOMETRIC | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2004-08-23 | INDIANHUME | known_action_not_applied | 1:10 split | UNCLEAR MANUAL_FLAG |
| 2004-10-14 | SOFTSOLINT | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2004-10-25 | UCALFUEL | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2005-01-13 | KTKBANK | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2005-02-25 | VISHALEXPO | known_action_not_applied | 1:4 / 3:1 bonus | UNCLEAR MANUAL_FLAG |
| 2005-06-20 | GUJAMBCEM | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2005-08-25 | KOTAKBANK | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2005-09-21 | ITC | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2005-10-27 | HELIOSMATH | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2006-02-07 | KECINTL | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-02-17 | ARHAMFISCL | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | CAROLINFO | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | DUNCANSIND | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | KOPRAN | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | NAGPURENG | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | NRC | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | OILCOUNTUB | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | RANASUG | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | SB&TINTL | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-06-12 | SRIADIKARI | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-06-19 | UPERGANGES | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-09-08 | HOTELEELA | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2006-11-17 | LAKSHVILAS | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2007-01-02 | INDIABULLS | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2007-01-04 | KPIT | known_action_not_applied | 1:5 split | UNCLEAR MANUAL_FLAG |
| 2008-02-21 | GBN | known_action_not_applied | 1:5 split | UNCLEAR MANUAL_FLAG |
| 2008-02-29 | LLOYDSTEEL | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2008-02-29 | MOREPENLAB | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2008-04-04 | KNL | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2008-10-13 | COREPROTEC | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2008-10-24 | PURVA | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2008-10-24 | UNITECH | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | DHAMPURSUG | known_action_not_applied | 1:3 / 2:1 bonus | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | DWARKESH | known_action_not_applied | 1:3 / 2:1 bonus | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | HMT | known_action_not_applied | 1:3 / 2:1 bonus | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | ITI | known_action_not_applied | 3:2 bonus | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | KCPSUGIND | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | MCDHOLDING | known_action_not_applied | 1:4 / 3:1 bonus | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | SAKHTISUG | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | SELAN | known_action_not_applied | 1:2 split or 1:1 bonus | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | UTTAMSUGAR | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2008-12-01 | VISAKAIND | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2009-01-07 | SATYAMCOMP | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2009-03-26 | AKRUTI | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2010-04-15 | ZEENEWS | known_action_not_applied | 1:4 / 3:1 bonus | UNCLEAR MANUAL_FLAG |
| 2010-11-15 | TEXMACOLTD | known_action_not_applied | 3:2 bonus | UNCLEAR MANUAL_FLAG |
| 2011-05-03 | TRIVENI | known_action_not_applied | 3:2 bonus | UNCLEAR MANUAL_FLAG |
| 2012-04-23 | ZUARIAGRO | known_action_not_applied | 1:3 / 2:1 bonus | UNCLEAR MANUAL_FLAG |
| 2016-05-25 | FEL | likely_demerger |  |  |
| 2018-02-07 | EXCEL | known_action_not_applied |  | UNCLEAR MANUAL_FLAG |
| 2019-09-03 | HSIL | known_action_not_applied | 1:5 split | UNCLEAR MANUAL_FLAG |

The full list with the evidence for each fall is in big_falls_v1.csv.
