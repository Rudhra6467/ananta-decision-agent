"""Decide each pre-2010 big fall from its price evidence (3 Nov 2026; Madhav's yes). Writes the proposed rows to ~/ananta_runs/ca_pre2010_rows.csv
for review before they are appended to india/registrations/ca_manual_v1.csv."""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.expanduser("~/code/ananta-records"))
from india.actions import parse_subject

COMMON = [1.5, 2, 2.5, 3, 4, 5, 6, 10, 20, 25, 50]
D = os.path.expanduser("~/ananta_data/india/")
ev = pd.read_csv(os.path.expanduser("~/ananta_runs/ca_review_pre2010.csv"))
rb = pd.read_parquet(D + "silver/corporate_actions/record_b.parquet")
rb["ex_date"] = pd.to_datetime(rb["ex_date"])
rows = []
for r in ev.itertuples():
    d = pd.Timestamp(r.date)
    if pd.isna(getattr(r, "close_before", float("nan"))) or pd.isna(r.open_day):
        rows.append((r.symbol, r.date, "flag", "UNCLEAR", "", "no raw prices on both sides of the fall")); continue
    go, gc, later, gapd = r.gap_open, r.gap_close, r.later_vs_before, r.days_gap
    b = rb[(rb["symbol"] == r.symbol) & ((rb["ex_date"] - d).abs() <= pd.Timedelta(days=3)) & rb["ratio"].notna()]
    rec = float(b["ratio"].iloc[0]) if len(b) else None
    base = f"raw close {r.close_before:g} -> open {r.open_day:g}, close {r.close_day:g} (open gap {go:.3f}, close gap {gc:.3f}); 20 sessions later {later:.3f} of the close before; shares traded x{r.vol_x}"
    if rec and abs(go / rec - 1) <= 0.20:
        rows.append((r.symbol, r.date, "apply", b["kind"].iloc[0], f"{rec:g}", f"NSE record '{b['subject'].iloc[0]}' (factor {rec:g}); {base}")); continue
    R = min(COMMON, key=lambda c: abs(go / c - 1))
    if r.open_day == r.close_before:
        rows.append((r.symbol, r.date, "flag", "UNCLEAR", "", f"the open equals the previous close (a stale open): {base}")); continue
    if go < 1.2 and gc < 1.2:
        rows.append((r.symbol, r.date, "flag", "UNCLEAR", "", f"no fall in the raw prices: the stock traded in the BE series (or under another symbol) before this day, so the EQ-only series spans the gap: {base}")); continue
    ok = abs(go / R - 1) <= 0.08 and abs(gc / R - 1) <= 0.15 and 0.6 <= later * R <= 1.5 and gapd <= 7
    if ok:
        kind = "SPLIT" if R in (5, 10, 20, 25, 50) else "BONUS" if R in (1.5, 2, 2.5, 3, 4) else "BONUS+SPLIT"
        rows.append((r.symbol, r.date, "apply", "SPLIT_OR_BONUS", f"{R:g}", f"price evidence, no NSE record (before 2005 the record is thin): the open gap is a clean {R:g} "
                     f"and the level holds; {base}"))
    else:
        why = "the open gap is not a clean ratio" if abs(go / R - 1) > 0.08 else "the day's close does not agree" if abs(gc / R - 1) > 0.15 else \
              "the level 20 sessions later does not fit the ratio" if not 0.6 <= later * R <= 1.5 else "trading not continuous"
        rows.append((r.symbol, r.date, "flag", "UNCLEAR", "", f"{why} (nearest {R:g}): {base}"))
out = pd.DataFrame(rows, columns=["symbol", "ex_date", "decision", "kind", "factor", "evidence"])
out.to_csv(os.path.expanduser("~/ananta_runs/ca_pre2010_rows.csv"), index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120); pd.set_option("display.max_rows", 400)
print(out["decision"].value_counts().to_dict())
print(out[["ex_date", "symbol", "decision", "factor", "evidence"]].to_string(index=False))
