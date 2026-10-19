"""Turns the 19 Oct 2026 calendar research (RBI decisions, Union Budgets, election counting days) into event-registry batches.
Times: only 2014-04-01, 2015-06-02 (11:00) and 2016-10-04 (14:30) are source-confirmed; RBI and Budget announcements in this era all fall
inside market hours, so the rest carry public_period 'during' with the time left blank. Dates marked U came from memory (the RBI annual
report gives the month only): those rows are leads until a source confirms the day. Elections are sourced to Wikipedia only: leads."""
import json
from pathlib import Path

H = Path(__file__).parent
RBIAR = "https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx?Id="
# date|time_confirmed|scheduled|before|after|change_bp|crr_bp|stance|source|U
RBI = """2014-01-28||1|7.75|8.0|25|0|disinflationary path|1121|
2014-04-01|11:00|1|8.0|8.0|0|0|disinflationary glide path|1121|
2014-06-03||1|8.0|8.0|0|0|maintained (SLR cut to 22.5%)|1121|
2014-08-05||1|8.0|8.0|0|0|vigilant (SLR cut to 22%)|1158|
2014-09-30||1|8.0|8.0|0|0|guided by inflation projections|1149|
2014-12-02||1|8.0|8.0|0|0|status quo; easing could begin early 2015|1149|
2015-01-15||0|8.0|7.75|-25|0|shift to easing (inter-meeting)|1158|
2015-02-03||1|7.75|7.75|0|0|maintained (SLR cut to 21.5%)|1158|
2015-03-04||0|7.75|7.5|-25|0|easing (inter-meeting)|1158|
2015-04-07||1|7.5|7.5|0|0|accommodative|1149|
2015-06-02|11:00|1|7.5|7.25|-25|0|accommodative|1158|
2015-08-04||1|7.25|7.25|0|0|accommodative|1176|U
2015-09-29||1|7.25|6.75|-50|0|accommodative (front-loaded)|1185|
2015-12-01||1|6.75|6.75|0|0|accommodative|1176|
2016-02-02||1|6.75|6.75|0|0|accommodative|1176|U
2016-04-05||1|6.75|6.5|-25|0|accommodative (corridor +/-50 bp)|1185|
2016-06-07||1|6.5|6.5|0|0|accommodative|1176|U
2016-08-09||1|6.5|6.5|0|0|accommodative|1203|U
2016-10-04|14:30|1|6.5|6.25|-25|0|accommodative (first MPC)|1212|
2016-12-07||1|6.25|6.25|0|0|accommodative|1203|
2017-02-08||1|6.25|6.25|0|0|neutral (from accommodative)|1212|
2017-04-06||1|6.25|6.25|0|0|neutral (reverse repo to 6.00%)|1212|
2017-06-07||1|6.25|6.25|0|0|neutral|1212|
2017-08-02||1|6.25|6.0|-25|0|neutral|1240|
2017-10-04||1|6.0|6.0|0|0|neutral|1240|
2017-12-06||1|6.0|6.0|0|0|neutral|1230|
2018-02-07||1|6.0|6.0|0|0|neutral|1230|
2018-04-05||1|6.0|6.0|0|0|neutral|1230|
2018-06-06||1|6.0|6.25|25|0|neutral|1240|
2018-08-01||1|6.25|6.5|25|0|neutral|1268|
2018-10-05||1|6.5|6.5|0|0|calibrated tightening (from neutral)|1268|
2018-12-05||1|6.5|6.5|0|0|calibrated tightening|1258|U
2019-02-07||1|6.5|6.25|-25|0|neutral (from calibrated tightening)|1268|
2019-04-04||1|6.25|6.0|-25|0|neutral|1268|
2019-06-06||1|6.0|5.75|-25|0|accommodative (from neutral)|1268|
2019-08-07||1|5.75|5.4|-35|0|accommodative|1297|
2019-10-04||1|5.4|5.15|-25|0|accommodative|1297|
2019-12-05||1|5.15|5.15|0|0|accommodative|1287|U
2020-02-06||1|5.15|5.15|0|0|accommodative|1297|
2020-03-27||0|5.15|4.4|-75|-100|accommodative as long as necessary (off-cycle)|1297|
2020-04-17||0|4.4|4.4|0|0|Governor's inter-meeting measures (reverse repo to 3.75%)|1297|
2020-05-22||0|4.4|4.0|-40|0|accommodative (off-cycle)|1297|
2020-08-06||1|4.0|4.0|0|0|accommodative|1326|
2020-10-09||1|4.0|4.0|0|0|accommodative (time-based guidance)|1326|
2020-12-04||1|4.0|4.0|0|0|accommodative|1316|U
2021-02-05||1|4.0|4.0|0|100|accommodative (CRR restored in two phases)|1326|
2021-04-07||1|4.0|4.0|0|0|accommodative|1355|
2021-06-04||1|4.0|4.0|0|0|accommodative|1345|U
2021-08-06||1|4.0|4.0|0|0|accommodative|1345|U
2021-10-08||1|4.0|4.0|0|0|accommodative|1345|U
2021-12-08||1|4.0|4.0|0|0|accommodative|1345|U
2022-02-10||1|4.0|4.0|0|0|accommodative|1345|
2022-04-08||1|4.0|4.0|0|0|withdrawal of accommodation focus (SDF 3.75%)|1384|
2022-05-04||0|4.0|4.4|40|50|withdrawal of accommodation (off-cycle)|1384|
2022-06-08||1|4.4|4.9|50|0|withdrawal of accommodation|1384|
2022-08-05||1|4.9|5.4|50|0|withdrawal of accommodation|1384|
2022-09-30||1|5.4|5.9|50|0|withdrawal of accommodation|1384|
2022-12-07||1|5.9|6.25|35|0|withdrawal of accommodation|1384|
2023-02-08||1|6.25|6.5|25|0|withdrawal of accommodation|1384|
2023-04-06||1|6.5|6.5|0|0|withdrawal of accommodation|1413|
2023-06-08||1|6.5|6.5|0|0|withdrawal of accommodation|1403|
2023-08-10||1|6.5|6.5|0|0|withdrawal of accommodation (temporary incremental CRR)|1413|
2023-10-06||1|6.5|6.5|0|0|withdrawal of accommodation|1403|
2023-12-08||1|6.5|6.5|0|0|withdrawal of accommodation|1403|
2024-02-08||1|6.5|6.5|0|0|withdrawal of accommodation|1403|
2024-04-05||1|6.5|6.5|0|0|withdrawal of accommodation|1443|
2024-06-07||1|6.5|6.5|0|0|withdrawal of accommodation|1433|
2024-08-08||1|6.5|6.5|0|0|withdrawal of accommodation|1433|U
2024-10-09||1|6.5|6.5|0|0|neutral (from withdrawal of accommodation)|1443|
2024-12-06||1|6.5|6.5|0|-50|neutral (CRR to 4.0%)|1443|
2025-02-07||1|6.5|6.25|-25|0|neutral|1443|
2025-04-09||1|6.25|6.0|-25|0|accommodative (from neutral)|1473|
2025-06-06||1|6.0|5.5|-50|-100|neutral (from accommodative; CRR to 3.0%)|1473|
2025-08-06||1|5.5|5.5|0|0|neutral|1463|U
2025-10-01||1|5.5|5.5|0|0|neutral|1463|U
2025-12-05||1|5.5|5.25|-25|0|neutral|1473|
2026-02-06||1|5.25|5.25|0|0|neutral|1463|U
2026-04-08||1|5.25|5.25|0|0|neutral|PR62514|
2026-06-05||1|5.25|5.25|0|0|neutral|PR62863|
2026-08-05||1|5.25|5.25|0|0|neutral|PR63287|
2026-10-07||1|5.25|5.5|25|0|calibrated tightening (from neutral; 4-2 on stance)|PR63742|"""

BUDGETS = [("2014-02-17", "interim", "P. Chidambaram", "budget2014-2015(I)/ub2014-15/bs/bs.pdf", "Excise cuts on capital goods, durables and vehicles; FY15 deficit target 4.1%"),
           ("2014-07-10", "full", "Arun Jaitley", "budget2014-2015/ub2014-15/bs/bs.pdf", "Insurance FDI to 49%; REIT/InvIT pass-through; debt-fund LTCG to 20%"),
           ("2015-02-28", "full", "Arun Jaitley", "budget2015-2016/ub2015-16/bs/bs.pdf", "Corporate tax to fall from 30% to 25% over four years; GAAR deferred two years"),
           ("2016-02-29", "full", "Arun Jaitley", "budget2016-2017/ub2016-17/bs/bs.pdf", "Extra 10% tax on dividends above Rs 10 lakh; STT on options raised; deficit 3.5%"),
           ("2017-02-01", "full", "Arun Jaitley", "budget2017-2018/ub2017-18/bs/bs.pdf", "Rail budget merged; Rs 2.5-5 lakh slab to 5%; FIPB abolished; deficit 3.2%"),
           ("2018-02-01", "full", "Arun Jaitley", "budget2018-2019/ub2018-19/bs/bs.pdf", "10% LTCG on equities above Rs 1 lakh (grandfathered); dividend tax on equity funds"),
           ("2019-02-01", "interim", "Piyush Goyal", "budget2019-20(I)/ub2019-20/bs/bs.pdf", "PM-KISAN Rs 6,000 a year; tax rebate to Rs 5 lakh; deficit 3.4%"),
           ("2019-07-05", "full", "Nirmala Sitharaman", "budget2019-20/doc/Budget_Speech.pdf", "Surcharge on high earners raised; 20% tax on listed buybacks; Rs 70,000 crore PSB recap"),
           ("2020-02-01", "full", "Nirmala Sitharaman", "budget2020-21/doc/Budget_Speech.pdf", "Dividend distribution tax abolished; optional new tax regime; LIC IPO"),
           ("2021-02-01", "full", "Nirmala Sitharaman", "budget2021-22/doc/Budget_Speech.pdf", "Two PSB and one insurer privatisation; insurance FDI to 74%; bad bank; deficit 6.8%"),
           ("2022-02-01", "full", "Nirmala Sitharaman", "budget2022-23/doc/Budget_Speech.pdf", "30% tax on virtual digital assets; LTCG surcharge capped at 15%; capex Rs 7.5 lakh crore"),
           ("2023-02-01", "full", "Nirmala Sitharaman", "budget2023-24/doc/Budget_Speech.pdf", "New tax regime default (no tax to Rs 7 lakh); capex Rs 10 lakh crore; deficit 5.9%"),
           ("2024-02-01", "interim", "Nirmala Sitharaman", "budget2024-25(I)/doc/Budget_Speech.pdf", "Deficit 5.1%; capex Rs 11.11 lakh crore; no tax-rate changes"),
           ("2024-07-23", "full", "Nirmala Sitharaman", "budget2024-25/doc/Budget_Speech.pdf", "STT on F&O raised; STCG to 20%, LTCG to 12.5%; buybacks taxed as dividend"),
           ("2025-02-01", "full", "Nirmala Sitharaman", "budget2025-26/doc/Budget_Speech.pdf", "No tax up to Rs 12 lakh (new regime); insurance FDI to 100%; deficit 4.4%"),
           ("2026-02-01", "full", "Nirmala Sitharaman", "doc/Budget_Speech.pdf", "STT on futures to 0.05% and options to 0.15%; buybacks taxed as capital gains; deficit 4.3%")]

ELECTIONS = [("Lok Sabha 2014", "2014-05-16", "2014-05-12", "BJP 282 of 543 (majority); NDA 336", "2014_Indian_general_election"),
             ("Maharashtra and Haryana 2014", "2014-10-19", None, "Haryana BJP majority 47/90; Maharashtra BJP largest 122/288", "2014_Maharashtra_Legislative_Assembly_election"),
             ("Delhi 2015", "2015-02-10", None, "AAP 67/70", "2015_Delhi_Legislative_Assembly_election"),
             ("Bihar 2015", "2015-11-08", None, "Mahagathbandhan 178/243; NDA 58", "2015_Bihar_Legislative_Assembly_election"),
             ("Assam, West Bengal, Tamil Nadu, Kerala, Puducherry 2016", "2016-05-19", None, "BJP-led NDA won Assam; TMC, AIADMK, LDF retained or won", "2016_Assam_Legislative_Assembly_election"),
             ("Uttar Pradesh and four states 2017", "2017-03-11", "2017-03-09", "UP: BJP 312/403; BJP won Uttarakhand; INC won Punjab", "2017_Uttar_Pradesh_Legislative_Assembly_election"),
             ("Gujarat and Himachal 2017", "2017-12-18", "2017-12-14", "BJP retained Gujarat 99/182; BJP won Himachal", "2017_Gujarat_Legislative_Assembly_election"),
             ("Karnataka 2018", "2018-05-15", "2018-05-12", "Hung: BJP 104/224; INC-JD(S) formed govt", "2018_Karnataka_Legislative_Assembly_election"),
             ("Five states Dec 2018", "2018-12-11", "2018-12-07", "INC won Rajasthan, Chhattisgarh, formed MP govt; TRS Telangana", "2018_Madhya_Pradesh_Legislative_Assembly_election"),
             ("Lok Sabha 2019", "2019-05-23", "2019-05-19", "BJP 303 of 543; NDA 353", "2019_Indian_general_election"),
             ("Maharashtra and Haryana 2019", "2019-10-24", "2019-10-21", "Maharashtra BJP-Sena 161/288 (alliance later split); Haryana hung, BJP+JJP", "2019_Maharashtra_Legislative_Assembly_election"),
             ("Bihar 2020", "2020-11-10", None, "NDA 125/243", "2020_Bihar_Legislative_Assembly_election"),
             ("West Bengal and four states 2021", "2021-05-02", "2021-04-29", "TMC retained West Bengal 215/294; DMK won Tamil Nadu; LDF Kerala; NDA Assam", "2021_West_Bengal_Legislative_Assembly_election"),
             ("Uttar Pradesh and four states 2022", "2022-03-10", "2022-03-07", "BJP retained UP 255/403; AAP won Punjab", "2022_Uttar_Pradesh_Legislative_Assembly_election"),
             ("Gujarat and Himachal 2022", "2022-12-08", "2022-12-05", "BJP 156/182 in Gujarat; INC won Himachal", "2022_Gujarat_Legislative_Assembly_election"),
             ("Karnataka 2023", "2023-05-13", "2023-05-10", "INC 135/224", "2023_Karnataka_Legislative_Assembly_election"),
             ("Four states Dec 2023", "2023-12-03", "2023-11-30", "BJP won MP, Rajasthan, Chhattisgarh; INC won Telangana", "2023_Madhya_Pradesh_Legislative_Assembly_election"),
             ("Lok Sabha 2024", "2024-06-04", "2024-06-01", "BJP 240 of 543 (short of 272); NDA 293 formed govt", "2024_Indian_general_election"),
             ("Haryana and Jammu & Kashmir 2024", "2024-10-08", "2024-10-05", "BJP 48/90 in Haryana (exit polls had INC); NC-INC won J&K", "2024_Haryana_Legislative_Assembly_election"),
             ("Maharashtra and Jharkhand 2024", "2024-11-23", "2024-11-20", "Mahayuti 235/288; JMM alliance retained Jharkhand", "2024_Maharashtra_Legislative_Assembly_election"),
             ("Delhi 2025", "2025-02-08", "2025-02-05", "BJP 48/70", "2025_Delhi_Legislative_Assembly_election"),
             ("Bihar 2025", "2025-11-14", "2025-11-11", "NDA 202/243", "2025_Bihar_Legislative_Assembly_election"),
             ("West Bengal and four states 2026", "2026-05-04", "2026-04-29", "BJP won West Bengal 208/294; TVK largest in Tamil Nadu; UDF Kerala; NDA Assam", "2026_West_Bengal_Legislative_Assembly_election")]

rbi = []
for line in RBI.strip().splitlines():
    d, t, sch, b, a, bp, crr, stance, src, u = line.split("|")
    url = ("https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=" + src[2:]) if src.startswith("PR") else RBIAR + src
    kind = "hike" if int(bp) > 0 else ("cut" if int(bp) < 0 else "hold")
    rbi.append({"title": f"RBI policy {d}: repo {kind} {b}% to {a}%" + ("" if sch == "1" else " (unscheduled)"), "category": "rbi_policy",
                "subcategory": "mpc_decision" if sch == "1" else "off_cycle", "event_date": d, "public_time_ist": t or None,
                "public_period": "during", "timing_note": "time source-confirmed" if t else "time not source-confirmed; RBI announcements in this era fall inside market hours",
                "first_tradable_session": d, "scope": "india", "known_beforehand": "scheduled" if sch == "1" else "surprise",
                "expectation": None, "expectation_source": None,
                "what_happened": f"Repo {b}% to {a}% ({int(bp):+d} bp), CRR change {int(crr):+d} bp; stance: {stance}.",
                "reported_affected": [], "confounders": [], "change_bp": int(bp), "crr_change_bp": int(crr), "stance": stance,
                "sources": [{"url": url, "publisher": "Reserve Bank of India", "published": None, "kind": "official"}],
                "date_unverified": u == "U", "notes": "date from memory; month confirmed by the RBI annual report" if u == "U" else None})
bud = [{"title": f"Union Budget {d} ({typ})", "category": "union_budget", "subcategory": typ, "event_date": d, "public_time_ist": None,
        "public_period": "during", "timing_note": "presented from about 11:00 IST by convention (not confirmed per budget)", "first_tradable_session": d,
        "scope": "india", "known_beforehand": "scheduled", "expectation": None, "expectation_source": None, "what_happened": f"{fm}: {m}.",
        "reported_affected": [], "confounders": [], "sources": [{"url": "https://www.indiabudget.gov.in/" + p, "publisher": "Ministry of Finance", "published": d,
        "kind": "official"}], "notes": None} for d, typ, fm, p, m in BUDGETS]
ele = [{"title": f"Election results: {n}", "category": "election", "subcategory": "counting_day", "event_date": d, "public_time_ist": None,
        "public_period": "during", "timing_note": "counting from about 08:00 IST; trends during the session (non-trading days roll to the next session)",
        "first_tradable_session": None, "scope": "india", "known_beforehand": "scheduled", "expectation": f"exit polls released {x}" if x else None,
        "expectation_source": None, "what_happened": o + ".", "reported_affected": [], "confounders": [],
        "sources": [{"url": "https://en.wikipedia.org/wiki/" + w, "publisher": "Wikipedia (secondary)", "published": None, "kind": "news"}],
        "notes": "Wikipedia only: a lead until an official (ECI) or two news sources confirm it"} for n, d, x, o, w in ELECTIONS]
for name, rows in (("calendar_rbi", rbi), ("calendar_budgets", bud), ("calendar_elections", ele)):
    (H / f"{name}.json").write_text(json.dumps(rows, indent=0))
    print(name, len(rows))
