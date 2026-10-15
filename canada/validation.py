"""The C2 gate's checks, frozen at C0 (doc section 'Validation, manifests and gap rules').

Thresholds live here once; tests hold them to the pre-registration. The cross-vendor test is written and
tested now but stays dormant while Norgate is the only vendor (decision 5).
"""
from __future__ import annotations

THRESHOLDS = {
    "V2_sanity_max_frac": 0.0001,          # price-sanity violations <= 0.01% of rows
    "V3_missing_member_days_max_frac": 0.005,  # index member-days with no price <= 0.5%
    "V4_outlier_move": 0.50,               # adjusted daily move above 50% is listed and KEPT as real...
    "V4_second_record_tol": 0.05,          # ...unless a second record shows the raw close off by > 5%
    "V6_reconcile_min": 0.95,              # index additions/deletions matched against published notices
    "V6_sample_years": 5,
    "V7_tsx60_range": (58, 62),
    "V8_sector_partition_min": 0.995,      # member-days in exactly one sector index existing that day
    "V8_real_estate_split": "2016-09-01",  # 10 GICS sectors before, 11 from this day
    "V9_spot_checks": 300,                 # stratified: 1/3 delisted, 1/3 before 2010, 1/3 the rest
    "V9_min_match": 297,
    "V9_tolerance": 0.005,
    "gap_short_max_days": 5,               # 1-5 day gaps kept, never filled
    "gap_exclusion_days": 60,              # after a longer gap the stock sits out 60 trading days
    "XV_agree_min": 0.995,                 # cross-vendor: share of stock-days that must agree
    "XV_tol_pct": 0.005,
    "XV_tol_abs_cad": 0.01,
    "XV_stock_min": 0.95,
}


def sector_count(day: str) -> int:
    """How many GICS sector indices existed on a day (ISO date)."""
    return 10 if day < THRESHOLDS["V8_real_estate_split"] else 11


def ohlc_ok(o: float, h: float, lo: float, c: float, v: float) -> bool:
    return min(o, h, lo, c) > 0 and lo <= o <= h and lo <= c <= h and v >= 0


def gap_rule(missing_days: int) -> str:
    if missing_days <= 0:
        return "none"
    return "keep_unfilled" if missing_days <= THRESHOLDS["gap_short_max_days"] else "no_new_signals_60_days"


def close_agrees(a: float, b: float) -> bool:
    """Two unadjusted closes agree within 0.5% or C$0.01, whichever is larger."""
    tol = max(THRESHOLDS["XV_tol_pct"] * abs(b), THRESHOLDS["XV_tol_abs_cad"])
    return abs(a - b) <= tol + 1e-12


def cross_vendor(pairs: list[tuple[str, float, float]]) -> dict:
    """pairs: (stock, close_vendor_a, close_vendor_b) for every overlapping stock-day."""
    if not pairs:
        return {"passed": False, "reason": "no overlapping stock-days", "agree": None}
    per: dict[str, list[int]] = {}
    for s, a, b in pairs:
        per.setdefault(s, []).append(int(close_agrees(a, b)))
    agree = sum(sum(v) for v in per.values()) / len(pairs)
    weak = sorted(s for s, v in per.items() if sum(v) / len(v) < THRESHOLDS["XV_stock_min"])
    return {"passed": agree >= THRESHOLDS["XV_agree_min"] and not weak, "agree": round(agree, 5),
            "stock_days": len(pairs), "stocks_below_95pct": weak}
