# The big-falls check, first version (3 Nov 2026)

Data audit step 6. Every one-day fall of over 45% in a stock ranked in the 500 most traded, with no applied split or bonus within 3 days, from the start of the features table to 2023. 369 falls. Nothing in the prices is changed by this check.

| label | what it means | all years | since 2010 |
|---|---|---|---|
| known_action_not_applied | a split or bonus is on file but was left out of the adjustment | 2 | 1 |
| likely_missed_action | looks like a split or bonus that is not on file | 104 | 28 |
| likely_demerger | a demerger or scheme was filed shortly before | 20 | 20 |
| no_evidence_found | no split, bonus or scheme found nearby: a true fall, or an action filed under an older symbol or a payout; needs a look | 243 | 27 |

## The ones to fix (not a true fall)

| date | stock | label | ratio | on file |
|---|---|---|---|---|
| 1995-11-08 | UNITEDPHOS | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1995-11-15 | ASIANPAINT | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1996-07-10 | JINDALPOLY | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1996-10-09 | PIDILITIND | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1996-11-20 | SWARAJENG | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1996-12-11 | WHEELS | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1997-03-26 | OUDHSUG | likely_missed_action | 1:10 split |  |
| 1997-09-24 | KERALACHEM | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1997-10-15 | LAXMIMACH | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1998-06-10 | SMITHKLPHA | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1998-08-12 | HEROHONDA | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1998-08-19 | BOOTSPHARM | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1998-08-19 | JAYSREETEA | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1999-02-02 | INDNIPPON | likely_missed_action | 3:2 bonus |  |
| 1999-05-12 | CASTROL | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 1999-05-19 | ACC | likely_missed_action | 1:10 split |  |
| 1999-12-15 | GUJAMBCEM | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2000-03-08 | SUNPHARMA | likely_missed_action | 1:3 / 2:1 bonus |  |
| 2000-08-23 | SHREEKRPET | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2000-09-13 | HUGHESSOFT | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2000-09-20 | WIDIA | likely_missed_action | 1:20 |  |
| 2000-10-11 | COLORCHEM | likely_missed_action | 1:10 split |  |
| 2000-11-01 | VSNL | likely_missed_action | 1:3 / 2:1 bonus |  |
| 2000-11-15 | COCHINREFN | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2000-11-22 | KIRLOSKCUM | likely_missed_action | 1:5 split |  |
| 2001-01-24 | VIKASWSP | likely_missed_action | 1:10 split |  |
| 2001-10-08 | SKFBEARING | likely_missed_action | 1:10 split |  |
| 2001-10-15 | DRREDDY | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2001-11-22 | ONWARDTEC | likely_missed_action | 3:4 bonus |  |
| 2002-05-15 | FDC | likely_missed_action | 1:10 split |  |
| 2002-09-25 | BALAJITELE | likely_missed_action | 1:5 split |  |
| 2002-10-09 | ASAHIINDIA | likely_missed_action | 1:10 split |  |
| 2003-07-03 | CHLORIDIND | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2003-11-07 | MADRASCEM | likely_missed_action | 1:10 split |  |
| 2003-12-15 | MIRCELECTR | likely_missed_action | 1:10 split |  |
| 2004-04-29 | BAJAJHIND | likely_missed_action | 1:10 split |  |
| 2004-05-12 | CIPLA | likely_missed_action | 1:5 split |  |
| 2004-06-25 | WIPRO | likely_missed_action | 1:3 / 2:1 bonus |  |
| 2004-06-29 | ASHOKLEY | likely_missed_action | 1:10 split |  |
| 2004-07-09 | MICO | likely_missed_action | 1:10 split |  |
| 2004-08-02 | GEOMETRIC | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2004-08-23 | INDIANHUME | likely_missed_action | 1:10 split |  |
| 2004-08-31 | TUBEINVEST | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2005-01-13 | MATRIXLABS | likely_missed_action | 1:10 split |  |
| 2005-02-09 | GUJNRECOKE | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2005-02-21 | VYSYABANK | likely_missed_action | 1:3 / 2:1 bonus |  |
| 2005-02-25 | VISHALEXPO | likely_missed_action | 1:4 / 3:1 bonus |  |
| 2005-03-03 | KPIT | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2005-07-25 | RANBAXY | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2005-08-10 | KIRLOSOIL | likely_missed_action | 1:5 split |  |
| 2005-08-30 | HINDALC0 | likely_missed_action | 1:10 split |  |
| 2005-09-01 | ASAHIINDIA | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2005-10-14 | HIMATSEIDE | likely_missed_action | 1:4 / 3:1 bonus |  |
| 2005-10-19 | KAJARIACER | likely_missed_action | 1:5 split |  |
| 2005-11-02 | CRANESSOFT | likely_missed_action | 1:10 split |  |
| 2005-11-08 | HINDCONS | likely_missed_action | 1:10 split |  |
| 2005-12-30 | HINDSANIT | likely_missed_action | 3:2 bonus |  |
| 2006-01-02 | COROMNFERT | likely_missed_action | 1:5 split |  |
| 2006-01-06 | RADICO | likely_missed_action | 1:5 split |  |
| 2006-03-17 | JUBILANT | likely_missed_action | 1:5 split |  |
| 2006-05-05 | STER | likely_missed_action | 1:5 split |  |
| 2006-09-20 | NAGARCONST | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2006-11-17 | LAKSHVILAS | known_action_not_applied | 1:2 split or 1:1 bonus | BONUS DISAGREE |
| 2006-12-12 | PANTALOONR | likely_missed_action | 1:5 split |  |
| 2007-01-04 | KPIT | likely_missed_action | 1:5 split |  |
| 2007-06-06 | BOSCHCHASY | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2007-07-23 | SUNTV | likely_missed_action | 1:4 / 3:1 bonus |  |
| 2007-09-19 | AMARAJABAT | likely_missed_action | 1:5 split |  |
| 2007-09-28 | GMRINFRA | likely_missed_action | 1:5 split |  |
| 2008-02-21 | GBN | likely_missed_action | 1:5 split |  |
| 2008-08-08 | INDIAINFO | likely_missed_action | 1:5 split |  |
| 2008-09-08 | JMFINANCIL | likely_missed_action | 1:20 |  |
| 2008-10-24 | UNITECH | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2009-01-01 | TEXMACOLTD | likely_missed_action | 1:10 split |  |
| 2009-07-30 | DIVISLAB | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2009-10-01 | GMRINFRA | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2009-11-19 | ALLCARGO | likely_missed_action | 1:5 split |  |
| 2010-02-10 | KRBL | likely_missed_action |  |  |
| 2010-04-15 | ZEENEWS | likely_missed_action | 1:4 / 3:1 bonus |  |
| 2010-05-06 | ENGINERSIN | likely_missed_action | 1:5 split |  |
| 2010-08-13 | MAGMA | likely_missed_action |  |  |
| 2010-09-21 | BHUSANSTL | likely_missed_action | 1:5 split |  |
| 2010-11-08 | ATLANTA | likely_missed_action | 1:5 split |  |
| 2010-11-15 | TEXMACOLTD | likely_demerger | 3:2 bonus |  |
| 2011-03-07 | HINDZINC | known_action_not_applied | 1:10 split | SPLIT DISAGREE |
| 2011-04-28 | ALEMBICLTD | likely_missed_action | 1:3 / 2:1 bonus |  |
| 2011-05-03 | TRIVENI | likely_demerger | 3:2 bonus |  |
| 2011-06-09 | MANAPPURAM | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2011-06-15 | RAINCOM | likely_missed_action |  |  |
| 2012-03-13 | KPIT | likely_missed_action |  |  |
| 2012-04-12 | VAKRANSOFT | likely_missed_action |  |  |
| 2012-04-23 | ZUARIAGRO | likely_demerger | 1:3 / 2:1 bonus |  |
| 2012-05-22 | DHFL | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2012-05-22 | INVENTURE | likely_missed_action |  |  |
| 2012-09-25 | AMARAJABAT | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2014-06-09 | GRUH | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2015-04-23 | TWL | likely_missed_action | 1:5 split |  |
| 2015-06-03 | ADANIENT | likely_demerger |  |  |
| 2015-06-26 | MASTEK | likely_demerger |  |  |
| 2015-09-16 | AEGISCHEM | likely_missed_action | 1:10 split |  |
| 2015-10-01 | IDFC | likely_demerger |  |  |
| 2015-12-04 | JSL | likely_demerger |  |  |
| 2016-01-20 | ABIRLANUVO | likely_missed_action |  |  |
| 2016-03-15 | CROMPGREAV | likely_demerger |  |  |
| 2016-03-16 | TIDEWATER | likely_missed_action | 1:4 / 3:1 bonus |  |
| 2016-05-25 | FEL | likely_demerger |  |  |
| 2016-09-01 | NBVENTURES | likely_missed_action |  |  |
| 2016-09-12 | TCI | likely_demerger | 1:2 split or 1:1 bonus |  |
| 2017-05-25 | SINTEX | likely_missed_action | 1:4 / 3:1 bonus |  |
| 2017-06-27 | OMKARCHEM | likely_missed_action | 3:2 bonus |  |
| 2018-01-25 | ORIENTPPR | likely_demerger |  |  |
| 2018-02-07 | EXCEL | likely_missed_action |  |  |
| 2018-04-12 | TALWALKARS | likely_demerger |  |  |
| 2018-04-19 | PHILIPCARB | likely_missed_action |  |  |
| 2018-11-28 | ARVIND | likely_demerger |  |  |
| 2019-06-14 | IIFL | likely_demerger | 3:2 bonus |  |
| 2019-08-22 | GFLLIMITED | likely_demerger |  |  |
| 2019-09-03 | HSIL | likely_missed_action | 1:5 split |  |
| 2019-12-19 | THOMASCOOK | likely_demerger |  |  |
| 2020-02-03 | SUVEN | likely_demerger |  |  |
| 2020-03-04 | TATACHEM | likely_demerger |  |  |
| 2020-08-20 | COFORGE | likely_missed_action | 1:5 split |  |
| 2021-03-18 | INFIBEAM | likely_missed_action |  |  |
| 2022-03-14 | INFIBEAM | likely_missed_action | 1:2 split or 1:1 bonus |  |
| 2023-04-18 | MIRZAINT | likely_demerger |  |  |
| 2023-06-22 | NIITLTD | likely_demerger |  |  |

The full list with the evidence for each fall is in big_falls_v1.csv.
