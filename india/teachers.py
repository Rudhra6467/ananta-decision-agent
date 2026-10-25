"""Teacher libraries -> India strategy cards -> backtests on 2000-2023 -> forward evidence.

Madhav, 25 Oct 2026: "youtube teachers plan, I want you to extract all the information that will be useful for Indian market and we will test all
the needed strategies and keep their results, have backtest if possible. Keep a track of them for forward evidence."

Every row of the two registers (Trade With Trend TWT-H01..H60, Optionables OPT-H01..H60) becomes one card here, written before any result was seen:
what it claims for India, the exact rule, every variant with its expected sign, and the test. Cards that cannot be backtested say why and what would
unlock them; the intraday option systems are tracked forward on the live recorder (india/teacher_forward.py).

  python -m india.teachers cards          writes india/registrations/teachers_v1.md (the pre-registration: every card, rule and variant)
  python -m india.teachers run [ids]      registers each testable card, runs it, records every variant in the test ledger (default: all)
  python -m india.teachers report         gold/teachers/results.{parquet,csv} and india/registrations/teachers_results_v1.md

Bars: one family per teacher (teacher_twt, teacher_opt). Each registration freezes union_k = every variant of that teacher's cards, so the first card
faces the same strict bar as the last (two-sided Bonferroni over the whole teacher, both periods). Development 2000-2017, validation 2018-2023;
2024 onward stays sealed. Costs: delivery round trip plus the spread estimate for stocks; Zerodha charges plus a 0.4% half-spread for options.
Descriptive checks (base rates he quotes) are measured and kept, but are not hypothesis tests and do not enter the ledger.
"""
from __future__ import annotations

import json
import sys
from functools import cached_property

import numpy as np
import pandas as pd

from india import paths, registry
from india import teachers_stock as ts

FAM = {"TWT": "teacher_twt", "OPT": "teacher_opt"}
TEACHER = {"TWT": "Trade With Trend (Raunak A)", "OPT": "Optionables"}
CARDS: dict[str, dict] = {}
TESTS: dict = {}


def card(cid: str, title: str, status: str, rule: str, variants: dict | None = None, india: str = "yes", note: str = "", forward: str = ""):
    """status: TEST (backtested here), DESCRIPTIVE (base rates measured, not a hypothesis), FORWARD (needs live intraday option prices: the recorder),
    LINKED (an earlier registered study ran this exact rule), NEEDS_DATA, NEEDS_BUILD, TOO_FEW (too few episodes for a test), DEFERRED (sizing,
    deferred by Madhav), NOT_INDIA, AMBIGUOUS (the rule as taught cannot be pinned down without guessing his numbers)."""
    CARDS[cid] = {"id": cid, "teacher": cid.split("-")[0], "title": title, "status": status, "rule": rule, "variants": dict(variants or {}),
                  "india": india, "note": note, "forward": forward}


def test(cid):
    def deco(f):
        TESTS[cid] = f
        return f
    return deco


class Ctx:
    """Lazy data for the tests: the stock panel, the market frame, sectors."""

    @cached_property
    def s(self) -> pd.DataFrame:
        df = ts.stock_panel()
        for k in (5, 20):
            df[f"p3net{k}"] = df[f"p3fwd{k}"] - df["cost"]
        return df

    @cached_property
    def s5(self) -> pd.Series:
        return ts.sample5(self.s)

    @cached_property
    def brk(self) -> pd.Series:
        """60-session breakout: a close above the highest high of the prior 60 sessions; one per stock per 10 sessions."""
        s = self.s
        return ts._cooldown(s, s["c"] > s["hi60_prev"], 10)

    @cached_property
    def fail5(self) -> pd.Series:
        """A breakout that closes back below its breakout level within 5 sessions."""
        s = self.s
        return ((1 + s["fwd_minc5"]) * s["c"] < s["hi60_prev"]).astype(float).where(s["fwd_minc5"].notna())

    @cached_property
    def m(self) -> pd.DataFrame:
        mk = self.s.groupby("date")[["breadth200", "breadth50", "hhhl"]].first()
        M = ts.market_context().join(mk, how="left")
        M["date"] = M.index
        M["b50_chg10"] = M["breadth50"] - M["breadth50"].shift(10)
        M["b200_chg10"] = M["breadth200"] - M["breadth200"].shift(10)
        M["b200_fwd21"] = M["breadth200"].shift(-21) - M["breadth200"]
        M["sess"] = np.arange(len(M))
        return M

    @cached_property
    def sec(self) -> pd.DataFrame:
        S = ts.sector_panel().merge(self.m[["date", "nifty_dd252", "sess"]], on="date", how="left")
        S["rs_rank"] = S.groupby("date")["rs63"].rank(ascending=False, method="first")
        S["dd_rank"] = S.groupby("date")["dd_from_hi"].rank(ascending=False, method="first")     # 1 = fell least
        S["n_sec"] = S.groupby("date")["sector"].transform("count")
        return S


def _ev(df: pd.DataFrame, mask: pd.Series, days: int = 10) -> pd.Series:
    return ts._cooldown(df, mask.fillna(False).astype(bool), days)


# =================================================================================================================== Trade With Trend (stocks)
# Breakout = a close above the prior 60-session high (one per stock per 10 sessions). Stock outcomes netK = buy at the next open, sell at the close
# K sessions later, net of costs. Market outcomes nfwdK = Nifty from the next close to K sessions later. Breadth = share of the liquid 500 above
# their 200 (or 50) DMA, built from our own universe (not point-in-time Nifty 500 membership; labelled).

card("TWT-H01", "Low breadth hurts breakouts", "TEST",
     "Breakouts taken while under X% of the liquid 500 are above their 200 DMA (X = 25, 30, 35, 40) earn less over 20 and 60 sessions than breakouts "
     "taken while breadth is 50% or more; they also fail (close back under the breakout level within 5 sessions) more often.",
     {**{f"lt{x}|net{h}": -1 for x in (25, 30, 35, 40) for h in (20, 60)}, "lt35|fail5": 1})


@test("TWT-H01")
def _(P):
    s, out = P.s, {}
    for x in (25, 30, 35, 40):
        on = s["breadth200"] < x / 100
        base = P.brk & (on | (s["breadth200"] >= 0.5))
        for h in (20, 60):
            out[f"lt{x}|net{h}"] = ts.split(s, on, f"net{h}", base=base)
    on = s["breadth200"] < 0.35
    out["lt35|fail5"] = ts.split(s.assign(fail5=P.fail5), on, "fail5", base=P.brk & (on | (s["breadth200"] >= 0.5)))
    return out


card("TWT-H02", "Index below both averages hurts breakouts", "TEST",
     "Breakouts taken while the Nifty closes below both its 50 and 200 DMA earn less over 20 and 60 sessions, and fail within 5 sessions more often, "
     "than breakouts taken while it is above both. His figure checked alongside: about 75% of longs lose over 3 months when the index is below a falling 200 DMA.",
     {"net20": -1, "net60": -1, "fail5": 1})


@test("TWT-H02")
def _(P):
    s = P.s
    below = (s["nifty_vs50"] < 0) & (s["nifty_vs200"] < 0)
    above = (s["nifty_vs50"] > 0) & (s["nifty_vs200"] > 0)
    base = P.brk & (below | above)
    out = {f"net{h}": ts.split(s, below, f"net{h}", base=base) for h in (20, 60)}
    out["fail5"] = ts.split(s.assign(fail5=P.fail5), below, "fail5", base=base)
    falling = P.brk & (s["nifty_vs200"] < 0) & ~s["nifty_200up"].fillna(False).astype(bool)
    x = s.loc[falling, "net60"].dropna()
    out["net60"]["extra"]["his_75pct_claim_share_losing"] = float((x < 0).mean()) if len(x) else None
    out["net60"]["extra"]["his_75pct_claim_n"] = int(len(x))
    return out


card("TWT-H03", "Cut risk to 0.25-0.5% in bad regimes", "DEFERRED", "Sizing rule on the H02 trade list.", india="yes",
     note="Sizing and capital rules were deferred by Madhav on 17 Oct ('not about sizing'). Cheap to run on the H02 trade list when he wants it.")

card("TWT-H04", "Top-RS sectors lead", "TEST",
     "Sector version (we hold sector indices, not a stock-to-sector map): every 5th session, rank the sector indices by their 63-session change against "
     "the Nifty 500; the top 3 beat the rest over 21, 63 and 126 sessions (excess return over the Nifty 500).",
     {"top3|xs21": 1, "top3|xs63": 1, "top3|xs126": 1},
     note="The stock-level claim (stocks from the top sectors) needs a point-in-time stock-to-sector map: not in the lake yet.")


@test("TWT-H04")
def _(P):
    S = P.sec
    S = S[(S["sess"] % 5 == 0) & (S["n_sec"] >= 8)]
    return {f"top3|xs{h}": ts.split(S, S["rs_rank"] <= 3, f"xs{h}") for h in (21, 63, 126)}


card("TWT-H05", "Strong-structure sectors outperform, weak ones lag", "TEST",
     "A sector index with higher highs and higher lows (20-session swings), above a rising 50 DMA, and a rising RS line against the Nifty 500 beats "
     "the Nifty 500 over 21/63/126 sessions; a sector below a falling 50 DMA with falling RS lags.",
     {"strong|xs21": 1, "strong|xs63": 1, "strong|xs126": 1, "weak|xs21": -1, "weak|xs63": -1, "weak|xs126": -1})


@test("TWT-H05")
def _(P):
    S = P.sec
    S = S[S["sess"] % 5 == 0]
    out = {}
    for name in ("strong", "weak"):
        for h in (21, 63, 126):
            out[f"{name}|xs{h}"] = ts.split(S, S[name].astype(bool), f"xs{h}")
    return out


card("TWT-H06", "Sector breadth ranks", "NEEDS_DATA", "Rank sectors by the share of members above their 200/50 DMA.",
     note="Needs sector membership over time (stock-to-sector map).")
card("TWT-H07", "Index, sector and stock all in uptrends", "NEEDS_DATA", "Long only when the index, the stock's sector index and the stock are above their 200 DMA.",
     note="Needs the stock-to-sector map. The index-plus-stock part is TWT-H02.")
card("TWT-H08", "Beating both sector and index", "NEEDS_DATA", "Stocks beating both their sector and the broad index over 3-6 months.",
     note="Needs the stock-to-sector map.")

card("TWT-H09", "50 DMA pullback in leaders", "TEST",
     "Stock above a rising 50 DMA and above its 200 DMA, within 15% of its all-time high, RS line rising, low touched the 50 DMA in the last 3 sessions. "
     "Entries on a strong bullish candle (close in the top 30% of the bar, up on the day) after a pullback on volume below the 50-day average beat the "
     "same pullbacks bought without the volume and candle conditions, over 20 and 60 sessions.",
     {"net20": 1, "net60": 1}, note="His first condition (a leading sector) needs the sector map and is left out.")


@test("TWT-H09")
def _(P):
    s = P.s
    setup = (s["sma50_up"].astype(bool) & (s["dist_sma50"] > -0.02) & (s["dist_sma200"] > 0) & (s["dist_ath"] >= -0.15) & s["rs_up20"].astype(bool)
             & s["touch50_3"].astype(bool))
    trig = setup & (s["vol50_5"] < 1) & (s["c"] > s["o"]) & (s["close_pos"] >= 0.7) & (s["ret_1"] > 0)
    on_ev = _ev(s, trig)
    off_ev = _ev(s, setup & ~trig)
    base = on_ev | off_ev
    return {f"net{h}": ts.split(s, on_ev, f"net{h}", base=base) for h in (20, 60)}


card("TWT-H10", "Don't chase: extension above the 50 DMA", "TEST",
     "In uptrend stocks (above the 50 and 200 DMA, every 5th session), entries more than X% above the 50 DMA (X = 8, 10, 15, 25) earn less over 20 and 60 "
     "sessions than entries within 5% of it; at 15% the next-60-session drawdown is also deeper.",
     {**{f"gt{x}|net{h}": -1 for x in (8, 10, 15, 25) for h in (20, 60)}, "gt15|minfwd60": -1})


@test("TWT-H10")
def _(P):
    s, out = P.s, {}
    up = P.s5 & (s["dist_sma50"] > 0) & (s["dist_sma200"] > 0)
    near = s["dist_sma50"] <= 0.05
    for x in (8, 10, 15, 25):
        on = s["dist_sma50"] > x / 100
        for h in (20, 60):
            out[f"gt{x}|net{h}"] = ts.split(s, on, f"net{h}", base=up & (on | near))
    on = s["dist_sma50"] > 0.15
    out["gt15|minfwd60"] = ts.split(s, on, "minfwd60", base=up & (on | near))
    return out


card("TWT-H11", "Breakouts on volume", "TEST",
     "Breakouts on volume above X times the 50-day average (X = 1.0, 1.5, 2.0) earn more over 20 sessions than breakouts below it; at 1.5x they fail within 5 sessions less often.",
     {"vol1.0|net20": 1, "vol1.5|net20": 1, "vol2.0|net20": 1, "vol1.5|fail5": -1})


@test("TWT-H11")
def _(P):
    s = P.s
    out = {f"vol{x}|net20": ts.split(s, s["vol50"] > x, "net20", base=P.brk) for x in (1.0, 1.5, 2.0)}
    out["vol1.5|fail5"] = ts.split(s.assign(fail5=P.fail5), s["vol50"] > 1.5, "fail5", base=P.brk)
    return out


card("TWT-H12", "The breakout bar's shape", "TEST",
     "Breakout bars that are the widest of the last 20 sessions, close in the top 25% of the bar and have an upper wick under 15% of the range earn more over "
     "5/10/20 sessions and fail less often. Wide, high-volume (1.5x) bars with an upper wick of 40% or more earn less.",
     {"good|net5": 1, "good|net10": 1, "good|net20": 1, "good|fail5": -1, "wicky|net20": -1})


@test("TWT-H12")
def _(P):
    s = P.s
    good = (s["range_vs_max20"] >= 1) & (s["close_pos"] >= 0.75) & (s["upper_wick"] <= 0.15)
    out = {f"good|net{h}": ts.split(s, good, f"net{h}", base=P.brk) for h in (5, 10, 20)}
    out["good|fail5"] = ts.split(s.assign(fail5=P.fail5), good, "fail5", base=P.brk)
    wicky = (s["range_vs_max20"] >= 1) & (s["vol50"] > 1.5) & (s["upper_wick"] >= 0.4)
    out["wicky|net20"] = ts.split(s, wicky, "net20", base=P.brk)
    return out


card("TWT-H13", "RS line at a high confirms the breakout", "TEST",
     "Breakouts where the stock / Nifty 500 ratio is at (within 0.5% of) its 126-session high earn more over 20 and 60 sessions than breakouts where it is not.",
     {"net20": 1, "net60": 1})


@test("TWT-H13")
def _(P):
    s = P.s
    return {f"net{h}": ts.split(s, s["rs_hi126"].astype(bool), f"net{h}", base=P.brk) for h in (20, 60)}


card("TWT-H14", "RS new high before price", "TEST",
     "Stocks whose RS line is at a 126-session high while the price is still more than 5% below its 52-week high beat the market's drift over 60 and 120 sessions.",
     {"net60": 1, "net120": 1}, note="Second claim (RS breakouts lead price breakouts by a measurable time) is descriptive and not tested.")


@test("TWT-H14")
def _(P):
    s = P.s
    ev = _ev(s, s["rs_hi126"].astype(bool) & (s["dist_hi252"] < -0.05), 20)
    d = s[P.s5 | ev]
    return {f"net{h}": ts.level(d, ev.reindex(d.index), f"net{h}") for h in (60, 120)}


card("TWT-H15", "Near highs beats far below", "TEST",
     "Stocks within 5% of their 52-week high beat stocks 40%+ below it over 20, 60 and 120 sessions (every 5th session). Stocks 40%+ down and below the "
     "200 DMA more often fall another 40% within 120 sessions.",
     {"near|net20": 1, "near|net60": 1, "near|net120": 1, "deep|fall40": 1})


@test("TWT-H15")
def _(P):
    s = P.s
    near, far = s["dist_hi252"] >= -0.05, s["dist_hi252"] <= -0.40
    out = {f"near|net{h}": ts.split(s, near, f"net{h}", base=P.s5 & (near | far)) for h in (20, 60, 120)}
    fall = (s["minfwd120"] <= -0.40).astype(float).where(s["minfwd120"].notna())
    out["deep|fall40"] = ts.split(s.assign(fall40=fall), far & (s["dist_sma200"] < 0), "fall40", base=P.s5)
    return out


card("TWT-H16", "Group breakouts", "NEEDS_DATA", "Several breakouts in one industry within weeks.", note="Needs an industry map.")

card("TWT-H17", "Breakout follow-through", "TEST",
     "Breakouts that close above the breakout close on each of days 1-3 and have above-average volume on at least 3 of the first 5 days earn more over the "
     "next 20 and 60 sessions, counted from day 5 (when the follow-through is known), than breakouts without it.",
     {"p5net20": 1, "p5net60": 1}, note="His 5:1 bullish-to-bearish candle filter is not added.")


@test("TWT-H17")
def _(P):
    s = P.s
    return {f"p5net{h}": ts.split(s, s["ft"].astype(bool), f"p5net{h}", base=P.brk) for h in (20, 60)}


card("TWT-H18", "Quiet pullbacks after a breakout", "TEST",
     "After a breakout, the first pullback of 3% from the post-breakout high (days 3-15): pullbacks on lower volume than the up-leg that hold the breakout "
     "level make a new high within 15 sessions more often than other pullbacks; pullbacks that retrace under 38.2% of the run do too.",
     {"quiet_hold|newhigh15": 1, "shallow|newhigh15": 1})


@test("TWT-H18")
def _(P):
    s = P.s
    base = s["pb3"].astype(bool)
    return {"quiet_hold|newhigh15": ts.split(s, s["pb3_good"].astype(bool), "pb3_newhigh15", base=base),
            "shallow|newhigh15": ts.split(s, s["pb3_shallow"].astype(bool), "pb3_newhigh15", base=base)}


card("TWT-H19", "How often breakouts retest", "DESCRIPTIVE",
     "Share of breakouts whose close returns to the breakout level within 10 sessions, and whose low touches it within 20; also among the breakouts that "
     "went on to gain 10%+ in 60 sessions. His figures: about 40% of eventual winners, more than 65% of breakouts.",
     note="The retest-entry versus breakout-entry comparison needs the exit engine (batch 3).")

DESCS: dict = {}


def desc(cid):
    def deco(f):
        DESCS[cid] = f
        return f
    return deco


@desc("TWT-H19")
def _(P):
    s = P.s
    b = s[P.brk].dropna(subset=["fwd_minc10", "fwd_minl20", "net60"])
    lvl = b["hi60_prev"] / b["c"] - 1
    close_back = b["fwd_minc10"] <= lvl
    low_touch = b["fwd_minl20"] <= lvl
    win = b["net60"] >= 0.10
    return {"breakouts": int(len(b)), "close_back_within_10": float(close_back.mean()), "low_touch_within_20": float(low_touch.mean()),
            "winners_10pct_in_60": int(win.sum()), "winners_low_touch_within_20": float(low_touch[win].mean()),
            "his_figures": "about 40% of eventual winners revisit; more than 65% of breakouts revisit"}


card("TWT-H20", "25% at the breakout, 75% after the pullback", "LINKED", "Staged entry versus one entry, same stop.",
     note="Run on 18 Oct as E09 'stage_25_75_pullback' (his exact split) on BRK, PULL and ANY entries.", forward="")
card("TWT-H21", "Weekly instalments in weak markets", "LINKED", "Equal weekly instalments versus one breakout-day entry.",
     note="Run on 18 Oct as E09 'stage_weekly4' (4 weekly instalments). His 8-16 week version was not run; it would add looks for a sizing-type rule.")

card("TWT-H22", "Staged stop -3/-5/-7 versus one -7% stop", "TEST",
     "On breakout entries (next open), selling a third at -3%, a third at -5% and the rest at -7% beats a single -7% stop when every position is closed "
     "at the close of day 20 or 60 at the latest; also checked when breadth is under 40%. Baseline: a single -7% stop beats no stop (60 sessions).",
     {"staged_vs_single|hold20": 1, "staged_vs_single|hold60": 1, "staged_vs_single|hold60|weak_breadth": 1, "single7_vs_none|hold60": 1},
     note="Re-entry after recovery is not simulated.")
card("TWT-H23", "Structure exits", "TEST",
     "On breakout entries, an initial stop at the last confirmed swing low and an exit on the first close below the latest swing low (max 120 sessions) beats "
     "(a) a +15% target with a -7% stop and (b) a tight -3% stop held otherwise to 60 sessions.",
     {"vs_target15_stop7": 1, "vs_tight3": 1})
card("TWT-H24", "Three-step exit for big winners", "TEST",
     "For breakouts that reach +30% within a year: selling 30% at +40%, 35% on the first close below the 50 DMA and the rest below the latest swing low beats "
     "holding to day 250, and beats a full exit on the first close below the 50 DMA.",
     {"vs_hold250": 1, "vs_full_50dma": 1})
card("TWT-H25", "Portfolio drawdown rule", "LINKED", "Review or exit all positions at a 7-8% open drawdown.",
     note="Run on 18 Oct as E10 (dd7/dd8 pause rules on 10-slot books).")

card("TWT-H26", "During index pullbacks, sell weak losers", "TEST",
     "While the Nifty is 3-10% below its 52-week high (every 5th session), stocks that are down over 60 sessions and lagging the Nifty 500 over 63 sessions earn "
     "less over the next 20 and 60 sessions than stocks that are up and leading, so selling the first group and keeping the second helps.",
     {"net20": -1, "net60": -1})


@test("TWT-H26")
def _(P):
    s = P.s
    pull = (s["nifty_dd252"] <= -0.03) & (s["nifty_dd252"] >= -0.10)
    weak = (s["ret_60"] < 0) & (s["rs_ret63"] < 0)
    lead = (s["ret_60"] > 0) & (s["rs_ret63"] > 0)
    return {f"net{h}": ts.split(s, weak, f"net{h}", base=P.s5 & pull & (weak | lead)) for h in (20, 60)}


card("TWT-H27", "Stage 2 stocks", "TEST",
     "Stage 2 (above a rising 150-day average, the daily stand-in for his 30-week MA, with higher highs and lows and a rising RS line) beats every other "
     "stock over 60 and 120 sessions (every 5th session). Breakouts from a 120-session range while in stage 2 beat other 120-session breakouts.",
     {"stage2|net60": 1, "stage2|net120": 1, "range_brk_in_stage2|net60": 1, "range_brk_in_stage2|net120": 1})


@test("TWT-H27")
def _(P):
    s = P.s
    st2 = s["above150"].astype(bool) & s["sma150_up"].astype(bool) & s["hh_hl"].astype(bool) & s["rs_up20"].astype(bool)
    out = {f"stage2|net{h}": ts.split(s, st2, f"net{h}", base=P.s5) for h in (60, 120)}
    b120 = _ev(s, s["c"] > s["hi120_prev"])
    up = s["above150"].astype(bool) & s["sma150_up"].astype(bool)
    for h in (60, 120):
        out[f"range_brk_in_stage2|net{h}"] = ts.split(s, up, f"net{h}", base=b120)
    return out


card("TWT-H28", "Correction leaders", "TEST",
     "While the Nifty is 10%+ below its 52-week high (every 5th session), the top fifth of stocks by 63-session relative strength beat the bottom fifth over 60 and 120 sessions.",
     {"net60": 1, "net120": 1})


@test("TWT-H28")
def _(P):
    s = P.s
    d = s[P.s5 & (s["nifty_dd252"] <= -0.10)].copy()
    q = d.groupby("date")["rs_ret63"].rank(pct=True)
    top, bot = q >= 0.8, q <= 0.2
    return {f"net{h}": ts.split(d, top, f"net{h}", base=top | bot) for h in (60, 120)}


card("TWT-H29", "Sectors that fall least lead the rebound", "TEST",
     "While the Nifty is 10%+ below its 52-week high (every 5th session), the 3 sector indices closest to their own 52-week high beat the 3 furthest, "
     "against the Nifty 500, over 63 and 126 sessions.",
     {"xs63": 1, "xs126": 1})


@test("TWT-H29")
def _(P):
    S = P.sec
    S = S[(S["sess"] % 5 == 0) & (S["nifty_dd252"] <= -0.10) & (S["n_sec"] >= 8)]
    top, bot = S["dd_rank"] <= 3, S["dd_rank"] > S["n_sec"] - 3
    return {f"xs{h}": ts.split(S, top, f"xs{h}", base=top | bot) for h in (63, 126)}


card("TWT-H30", "Swing-structure breadth", "TEST",
     "When under 35% of the liquid 500 show higher highs and higher lows (20-session swings), the Nifty's next-21-session return is lower and its volatility "
     "higher than when over 60% do. Under 20% with the Nifty within 3% of its high flags deeper drawdowns over 63 sessions.",
     {"lt35|nfwd21": -1, "lt35|nrv_fwd21": 1, "lt20_near_high|n_mdd63": -1})


@test("TWT-H30")
def _(P):
    M = P.m
    on = M["hhhl"] < 0.35
    base = on | (M["hhhl"] > 0.60)
    out = {"lt35|nfwd21": ts.split(M, on, "nfwd21", base=base), "lt35|nrv_fwd21": ts.split(M, on, "nrv_fwd21", base=base)}
    out["lt20_near_high|n_mdd63"] = ts.split(M, (M["hhhl"] <= 0.20) & (M["nifty_dd252"] >= -0.03), "n_mdd63")
    return out


card("TWT-H31", "New highs on thin breadth", "TEST",
     "With the Nifty within 2% of its 52-week high, a 4%+ drawdown within 21 and 63 sessions is more likely when 50% or fewer stocks are above their 200 DMA "
     "than when 70% or more are.",
     {"dd4|21": 1, "dd4|63": 1})


@test("TWT-H31")
def _(P):
    M = P.m.copy()
    near = M["nifty_dd252"] >= -0.02
    thin, wide = M["breadth200"] <= 0.5, M["breadth200"] >= 0.7
    M["dd4_21"] = (M["n_mdd21"] <= -0.04).astype(float).where(M["n_mdd21"].notna())
    M["dd4_63"] = (M["n_mdd63"] <= -0.04).astype(float).where(M["n_mdd63"].notna())
    return {"dd4|21": ts.split(M, thin, "dd4_21", base=near & (thin | wide)), "dd4|63": ts.split(M, thin, "dd4_63", base=near & (thin | wide))}


card("TWT-H32", "Short-term breadth damage, long-term intact", "TEST",
     "Three versions, each against all other sessions, Nifty over 21 and 63 sessions: (v1) 50-DMA breadth down 20+ points in 10 sessions while 200-DMA breadth "
     "is down 10 or less; (v2) 50-DMA breadth 45% or less with 200-DMA breadth 65%+; (v3) the Nifty 4-6% off its high with 50-DMA breadth 55%+.",
     {f"{v}|nfwd{h}": 1 for v in ("v1", "v2", "v3") for h in (21, 63)},
     note="One of his videos (8QeR8FmYYg4) says a fast drop is bearish: the test is two-sided, so that reading would show as OPPOSITE.")


@test("TWT-H32")
def _(P):
    M = P.m
    v = {"v1": (M["b50_chg10"] <= -0.20) & (M["b200_chg10"] >= -0.10),
         "v2": (M["breadth50"] <= 0.45) & (M["breadth200"] >= 0.65),
         "v3": (M["nifty_dd252"] <= -0.04) & (M["nifty_dd252"] >= -0.06) & (M["breadth50"] >= 0.55)}
    return {f"{k}|nfwd{h}": ts.split(M, on, f"nfwd{h}") for k, on in v.items() for h in (21, 63)}


card("TWT-H33", "Breadth washouts", "TEST",
     "When 20% or fewer stocks are above their 200 DMA, or 11% or fewer above their 50 DMA, the Nifty's next 63/126/252 sessions beat all other sessions.",
     {f"{v}|nfwd{h}": 1 for v in ("b200le20", "b50le11") for h in (63, 126, 252)},
     note="Washouts cluster in a few quarters (2008, 2011, 2020): expect INCONCLUSIVE on the 16-quarter minimum.")


@test("TWT-H33")
def _(P):
    M = P.m
    v = {"b200le20": M["breadth200"] <= 0.20, "b50le11": M["breadth50"] <= 0.11}
    return {f"{k}|nfwd{h}": ts.split(M, on, f"nfwd{h}") for k, on in v.items() for h in (63, 126, 252)}


card("TWT-H34", "Bottoming signals", "TOO_FEW", "Strong up days after lows, holding the first rally day's low, ranges above the 50/200 DMA.",
     note="About 8-10 corrections in 2003-2023: below the 16-quarter minimum for a test. A descriptive table can be added.")

card("TWT-H35", "Bear-market rallies fail near the 50 DMA", "TEST",
     "With the Nifty below a falling 50 DMA and below its 200 DMA, the session it rallies to within 3% of the 50 DMA (from further below) is followed by lower "
     "10 and 21 session returns than the market's drift.",
     {"nfwd10": -1, "nfwd21": -1})


@test("TWT-H35")
def _(P):
    M = P.m
    down = (M["nifty_vs50"] < 0) & ~M["nifty_50up"].astype(bool) & (M["nifty_vs200"] < 0)
    ev = down & (M["nifty_vs50"] >= -0.03) & (M["nifty_vs50"].shift(1) < -0.03)
    return {f"nfwd{h}": ts.split(M, ev, f"nfwd{h}") for h in (10, 21)}


card("TWT-H36", "Deep below the 200 DMA", "TEST",
     "Nifty closes 8-14% below its 200 DMA are followed by higher 21 and 63 session returns than other sessions; the 9-10% band by higher 63 and 126 session returns.",
     {"b8_14|nfwd21": 1, "b8_14|nfwd63": 1, "b9_10|nfwd63": 1, "b9_10|nfwd126": 1}, note="Few episodes: likely INCONCLUSIVE.")


@test("TWT-H36")
def _(P):
    M = P.m
    a = (M["nifty_vs200"] <= -0.08) & (M["nifty_vs200"] >= -0.14)
    b = (M["nifty_vs200"] <= -0.09) & (M["nifty_vs200"] >= -0.10)
    return {"b8_14|nfwd21": ts.split(M, a, "nfwd21"), "b8_14|nfwd63": ts.split(M, a, "nfwd63"),
            "b9_10|nfwd63": ts.split(M, b, "nfwd63"), "b9_10|nfwd126": ts.split(M, b, "nfwd126")}


card("TWT-H37", "India VIX spikes above 28", "TEST",
     "Sessions with India VIX at 28 or more, and sessions within 10% of a VIX peak of 28+ in the last 5 sessions after it turned down 10%, are followed by higher "
     "Nifty returns than other sessions (21, 63, 252 and 21, 63 sessions).",
     {"ge28|nfwd21": 1, "ge28|nfwd63": 1, "ge28|nfwd252": 1, "peak_turn|nfwd21": 1, "peak_turn|nfwd63": 1},
     note="India VIX from 2009 (dev 2009-2017). High-VIX sessions cluster: likely INCONCLUSIVE.")


@test("TWT-H37")
def _(P):
    M = P.m
    ge = M["vix"] >= 28
    mx = M["vix"].rolling(5, min_periods=1).max()
    pk = (mx >= 28) & (M["vix"] <= 0.9 * mx)
    out = {f"ge28|nfwd{h}": ts.split(M, ge, f"nfwd{h}", base=M["vix"].notna()) for h in (21, 63, 252)}
    out.update({f"peak_turn|nfwd{h}": ts.split(M, pk, f"nfwd{h}", base=M["vix"].notna()) for h in (21, 63)})
    return out


card("TWT-H38", "VIX waking up from low levels", "TEST",
     "The Nifty's drawdown over the next 21 sessions is deeper (a) when VIX reaches 14+ after 15 sessions at 13 or less, (b) after a 30%+ weekly VIX jump, and "
     "(c) when VIX is above 17 rather than below 14.",
     {"wake14|n_mdd21": -1, "jump30|n_mdd21": -1, "gt17_vs_lt14|n_mdd21": -1})


@test("TWT-H38")
def _(P):
    M = P.m
    ok = M["vix"].notna()
    wake = (M["vix"] >= 14) & (M["vix"].shift(1).rolling(15).max() <= 13)
    jump = M["vix_wk"] >= 0.30
    hi, lo = M["vix"] > 17, M["vix"] < 14
    return {"wake14|n_mdd21": ts.split(M, wake, "n_mdd21", base=ok), "jump30|n_mdd21": ts.split(M, jump, "n_mdd21", base=ok),
            "gt17_vs_lt14|n_mdd21": ts.split(M, hi, "n_mdd21", base=hi | lo)}


card("TWT-H39", "Small caps' turn", "TEST",
     "When the Nifty Smallcap 100 / Nifty 100 ratio has risen over 40 sessions, or closes above its 50 DMA, the ratio keeps rising over the next 63 and 126 sessions.",
     {"ret40|slfwd63": 1, "ret40|slfwd126": 1, "above50|slfwd63": 1, "above50|slfwd126": 1})


@test("TWT-H39")
def _(P):
    M = P.m
    v = {"ret40": M["sl_ret40"] > 0, "above50": M["sl_vs50"] > 0}
    return {f"{k}|slfwd{h}": ts.split(M, on, f"slfwd{h}", base=M["sl_ratio"].notna()) for k, on in v.items() for h in (63, 126)}


card("TWT-H40", "Index contraction on a rising 50 DMA", "TEST",
     "In an uptrend (Nifty above a rising 50 DMA), sessions with the 10-day average range under 70% of the 50-day average and the Nifty within 3% above its 50 DMA "
     "are followed by higher 10 and 21 session returns than other uptrend sessions.",
     {"nfwd10": 1, "nfwd21": 1})


@test("TWT-H40")
def _(P):
    M = P.m
    up = M["nifty_50up"].astype(bool) & (M["nifty_vs50"] > 0)
    on = (M["n_rng10_vs50"] < 0.7) & (M["nifty_vs50"] <= 0.03)
    return {f"nfwd{h}": ts.split(M, on, f"nfwd{h}", base=up) for h in (10, 21)}


card("TWT-H41", "Leadership turns over after a bear phase", "TOO_FEW", "Prior-cycle leaders lag for 1-3 years.",
     note="About 4 bear phases since 2000: too few for a test. The correction-leaders cross-section is TWT-H28.")

card("TWT-H42", "A strong dollar hurts the Nifty", "TEST",
     "When the broad dollar index (the Fed's, from 2006; stand-in for DXY) is up 5%+ over 126 sessions, or breaks above its 3-year high, the Nifty's next 21 and 63 "
     "sessions are weaker than other sessions.",
     {"up5|nfwd21": -1, "up5|nfwd63": -1, "break3y|nfwd21": -1, "break3y|nfwd63": -1},
     note="His threshold is +10% on DXY; the broad index moves less than DXY, so +5% is used and labelled. A US close counts from the next Indian session.")


@test("TWT-H42")
def _(P):
    M = P.m
    ok = M["dxy_chg126"].notna()
    v = {"up5": M["dxy_chg126"] >= 0.05, "break3y": M["dxy_break"].fillna(False).astype(bool)}
    return {f"{k}|nfwd{h}": ts.split(M, on, f"nfwd{h}", base=ok) for k, on in v.items() for h in (21, 63)}


card("TWT-H43", "Strong crude hurts the Nifty", "TEST",
     "Brent above its 50 DMA, or at $100+, is followed by weaker Nifty returns over 21 and 63 sessions.",
     {"above50|nfwd21": -1, "above50|nfwd63": -1, "ge100|nfwd21": -1, "ge100|nfwd63": -1},
     note="Another of his videos says Brent at 80-100 is not meaningfully worse: two-sided test.")


@test("TWT-H43")
def _(P):
    M = P.m
    ok = M["brent"].notna()
    v = {"above50": M["brent_vs50"] > 0, "ge100": M["brent"] >= 100}
    return {f"{k}|nfwd{h}": ts.split(M, on, f"nfwd{h}", base=ok) for k, on in v.items() for h in (21, 63)}


card("TWT-H44", "US weakness leads the Nifty lower", "TEST",
     "With the Nasdaq (stand-in: the lake's S&P 500 starts 2016) below its 50 DMA, or 10%+ below its 60-session high, the Nifty's next 21 and 63 sessions are weaker; "
     "in the 5 sessions after the Nasdaq reclaims its 50 DMA the Nifty's next 21 and 42 sessions are stronger.",
     {"below50|nfwd21": -1, "below50|nfwd63": -1, "dd10|nfwd21": -1, "dd10|nfwd63": -1, "reclaim|nfwd21": 1, "reclaim|nfwd42": 1})


@test("TWT-H44")
def _(P):
    M = P.m
    ok = M["nq_vs50"].notna()
    rec = M["nq_reclaim50"].fillna(False).astype(int).rolling(5, min_periods=1).max().astype(bool)
    out = {f"below50|nfwd{h}": ts.split(M, M["nq_vs50"] < 0, f"nfwd{h}", base=ok) for h in (21, 63)}
    out.update({f"dd10|nfwd{h}": ts.split(M, M["nq_dd60"] <= -0.10, f"nfwd{h}", base=ok) for h in (21, 63)})
    out.update({f"reclaim|nfwd{h}": ts.split(M, rec, f"nfwd{h}", base=ok) for h in (21, 42)})
    return out


card("TWT-H45", "India vs US relative legs", "TOO_FEW", "Nifty 500 / S&P 500 legs of 4-12 months.",
     note="The lake's S&P 500 starts 2016, and legs of 4-12 months give only a handful of observations.")

card("TWT-H46", "Bank Nifty leads", "TEST",
     "After a 3.5%+ weekly Bank Nifty gain the Nifty's next 21 sessions and the 200-DMA breadth over 21 sessions rise more than otherwise; with Bank Nifty above "
     "its 200 DMA the Nifty's next 21 and 63 sessions beat sessions when it is below.",
     {"wk35|nfwd21": 1, "wk35|breadth_fwd21": 1, "above200|nfwd21": 1, "above200|nfwd63": 1})


@test("TWT-H46")
def _(P):
    M = P.m
    wk = M["bank_ret5"] >= 0.035
    ab = M["bank_vs200"] > 0
    return {"wk35|nfwd21": ts.split(M, wk, "nfwd21"), "wk35|breadth_fwd21": ts.split(M, wk, "b200_fwd21"),
            "above200|nfwd21": ts.split(M, ab, "nfwd21", base=M["bank_vs200"].notna()), "above200|nfwd63": ts.split(M, ab, "nfwd63", base=M["bank_vs200"].notna())}


card("TWT-H47", "Rate-cut lags", "TOO_FEW", "First cut of a cycle to the index's major low: 4-8 months.", note="About 5 RBI cutting cycles since 2000.")
card("TWT-H48", "FII flow beta", "NEEDS_DATA", "FII flow sensitivity before and after the SIP era.", note="The FII/DII cash-flow table in the lake is empty.")

card("TWT-H49", "Stochastic pullback with filters", "TEST",
     "Among Stochastic(15,3,3) dips with %K and %D both under 30, those with the close above the 100-day average and at most one wide-range down candle "
     "(range over 1.5 ATR, red) in the last 5 sessions earn more over 10 and 20 sessions.",
     {"net10": 1, "net20": 1}, note="His narrow Heikin Ashi condition has no numeric definition and is left out.")


@test("TWT-H49")
def _(P):
    s = P.s
    base = _ev(s, (s["stoch_k"] < 30) & (s["stoch_d"] < 30))
    on = s["above100"].astype(bool) & (s["wrd5"] <= 1)
    return {f"net{h}": ts.split(s, on, f"net{h}", base=base) for h in (10, 20)}


card("TWT-H50", "Confirmed Heikin Ashi entries", "TEST",
     "Entries on the second green Heikin Ashi candle after 3+ red ones (initiation plus confirmation) earn more over 10 and 20 sessions than entries on every red-to-green change.",
     {"net10": 1, "net20": 1})


@test("TWT-H50")
def _(P):
    s = P.s
    conf = _ev(s, s["ha_conf"].astype(bool))
    flip = _ev(s, s["ha_flip"].astype(bool) & ~s["ha_conf"].astype(bool))
    return {f"net{h}": ts.split(s, conf, f"net{h}", base=conf | flip) for h in (10, 20)}


card("TWT-H51", "Hidden bullish divergence", "TEST",
     "In stocks above their 200 DMA, a confirmed higher swing low in price with a lower RSI(14) low at 35 or under beats the market drift of uptrend pullbacks "
     "(below the 20 DMA, every 5th session) over 5, 10 and 20 sessions.",
     {"net5": 1, "net10": 1, "net20": 1})


@test("TWT-H51")
def _(P):
    s = P.s
    ev = _ev(s, s["hidden_div"].astype(bool) & (s["dist_sma200"] > 0))
    pull = P.s5 & (s["dist_sma200"] > 0) & (s["dist_sma20"] < 0)
    return {f"net{h}": ts.split(s, ev, f"net{h}", base=ev | pull) for h in (5, 10, 20)}


card("TWT-H52", "Ichimoku: all elements aligned", "TEST",
     "Among closes above the cloud (first close above), those with Senkou A and B rising, Chikou above price and Tenkan and Kijun rising earn more over 10 and 20 sessions.",
     {"net10": 1, "net20": 1}, note="The bearish mirror (shorts) is not tested: the India paper book is long only.")


@test("TWT-H52")
def _(P):
    s = P.s
    base = _ev(s, s["cloud_cross"].astype(bool))
    return {f"net{h}": ts.split(s, s["ichi_aligned"].astype(bool), f"net{h}", base=base) for h in (10, 20)}


card("TWT-H53", "Weekly outside reversal bars", "TEST",
     "A bullish weekly outside bar (high above and low below the prior week, close above the prior week's high) after a 10%+ fall over 8 weeks beats the market "
     "drift over 10 and 20 sessions; with the week's volume the highest in 52 weeks over 20 sessions; a bearish one after a 10%+ rise lags over 20.",
     {"bull|net10": 1, "bull|net20": 1, "bull_vol52|net20": 1, "bear|net20": -1})


@test("TWT-H53")
def _(P):
    s = P.s
    out = {}
    for name, col, hs, in (("bull", "wk_out_bull", (10, 20)), ("bull_vol52", "wk_out_bull_v", (20,)), ("bear", "wk_out_bear", (20,))):
        ev = s[col].astype(bool)
        d = s[P.s5 | ev]
        for h in hs:
            out[f"{name}|net{h}"] = ts.level(d, ev.reindex(d.index), f"net{h}")
    return out


card("TWT-H54", "ADX trend pullback to the 20 EMA", "TEST",
     "Buying the break of the high of a candle that touched the 20 EMA (entry next open) earns more over 10 and 20 sessions when ADX(14) was above 30 and rising "
     "with +DI above -DI than for any 20-EMA touch.",
     {"net10": 1, "net20": 1}, note="He buys the break intraday; this enters at the next open (one session later).")


@test("TWT-H54")
def _(P):
    s = P.s
    base = _ev(s, s["ema_break"].astype(bool))
    return {f"net{h}": ts.split(s, s["ema_break_adx"].astype(bool), f"net{h}", base=base) for h in (10, 20)}


card("TWT-H55", "Daily beats intraday", "NEEDS_DATA", "Same rules on daily versus 5-30 minute bars.", note="Needs stock minute history before 2024.")
card("TWT-H56", "Intraday entries aligned with the daily trend", "NEEDS_DATA", "30/60-minute entries only with the daily trend up.",
     note="Needs stock minute history before 2024.")
card("TWT-H57", "Index ETF tranches", "DEFERRED", "Buying an index ETF in drawdown tranches.", note="Sizing rule: deferred by Madhav.")
card("TWT-H58", "Quality screen", "NEEDS_BUILD", "Sales growth, margins, ROE, D/E screen.",
     note="Fundamentals exist but a point-in-time screen (as reported, with filing dates) must be built first.")

card("TWT-H59", "Opening outside yesterday's range", "TEST",
     "Days the Nifty (and Bank Nifty) opens outside the prior day's high-low range have a bigger range (vs the 20-day average) and more often close further in the "
     "direction of the gap than days opening inside.",
     {"NIFTY|range": 1, "NIFTY|continuation": 1, "BANKNIFTY|range": 1, "BANKNIFTY|continuation": 1},
     note="His value-area version needs minute profiles (index minutes exist from 2015; a later build).")


@test("TWT-H59")
def _(P):
    ts.index_panel()
    ohl = ts._P["index_ohl"]
    piv = ts._P["index"]
    out = {}
    for sym, name in (("NIFTY", "NIFTY 50"), ("BANKNIFTY", "NIFTY BANK")):
        o, h, l, c = ohl["open"][name], ohl["high"][name], ohl["low"][name], piv[name]
        d = pd.DataFrame({"date": c.index})
        d.index = c.index
        outside = (o > h.shift(1)) | (o < l.shift(1))
        rng = h - l
        d["range"] = rng / rng.rolling(20).mean().shift(1)
        d["continuation"] = (np.sign(c - o) == np.sign(o - c.shift(1))).astype(float).where(o.notna() & (o != c.shift(1)))
        ok = o.notna() & (o > 0) & (h > l)
        out[f"{sym}|range"] = ts.split(d, outside, "range", base=ok)
        out[f"{sym}|continuation"] = ts.split(d, outside, "continuation", base=ok)
    return out


card("TWT-H60", "Value-area sequences", "NEEDS_BUILD", "Higher non-overlapping value areas predict continuation.", note="Needs TPO profiles built from minute bars.")


# =================================================================================================================== Optionables (index options)
REC = ("Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full "
       "charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.")

for _cid, _title, _rule in (
        ("OPT-H01", "Intraday ATM straddle at fixed times", "Sell the ATM Bank Nifty/Nifty straddle at 9:20, 9:30, 9:45, 10:00, 12:30, 13:00 or 14:00 with a premium stop on each leg; same-day exit."),
        ("OPT-H02", "The 1 pm Bank Nifty straddle", "ATM Bank Nifty straddle at 13:00, 30% stop per leg, exit 14:55. His figures: ~70% winning days, win/loss ~1:1, max drawdown ~11% at 2.5 lakh per lot."),
        ("OPT-H03", "The 9:30 Bank Nifty straddle", "ATM Bank Nifty straddle at 9:30, 50% stop per leg, exit 15:00. His figure: ~70% winning days."),
        ("OPT-H04", "The 9:30 Nifty straddle, split by VIX", "ATM Nifty straddle at 9:30, 70-point stop per leg, exit 15:20; better below VIX 14, more double stops above 20."),
        ("OPT-H05", "Entry time", "Afternoon entries (12:30-14:00) beat 9:30-10:00 entries (conflicting videos: all slots registered together)."),
        ("OPT-H06", "Per-leg stop width", "Stops of 25/30/35/40/50/75/100% of premium on identical entries."),
        ("OPT-H07", "Stop to cost", "After the first leg stops, move the other leg's stop to its entry price."),
        ("OPT-H08", "Staggered entries", "Split the same size over 2-3 entry times: lower drawdown, daily P&L correlation below 1."),
        ("OPT-H09", "Where straddle losses come from", "Losses concentrate on V-shaped or whipsaw days; trend and range days pay."),
        ("OPT-H10", "Late-session exit", "Close intraday short premium at 14:55-15:20 rather than the final minutes."),
        ("OPT-H11", "Expiry last-hour decay", "ATM straddle sold after 15:00 on expiry day profitable on ~80% of days."),
        ("OPT-H12", "Expiry afternoon straddle", "ATM straddle sold 12:30-14:00 on expiry day, held to close; better after a contracted morning range."),
        ("OPT-H13", "Daily loss cap", "Flatten the book at a 0.5-3% daily loss: smaller worst day without losing expectancy."),
        ("OPT-H22", "Budget day straddles", "ATM straddles every 30 minutes 9:30-12:00 on Budget day, 40-50% stops, stop to cost, exit 15:23-15:29."),
        ("OPT-H23", "After RBI announcements", "Straddles sold ~30 minutes after a policy announcement beat those held into it."),
        ("OPT-H34", "Premium-imbalance shift", "Shift the cheap leg toward the money only beyond an imbalance threshold (~20% of premium)."),
        ("OPT-H35", "Counter trade after a stop", "After one leg stops, sell a fresh option at 40-60% of the surviving leg's premium."),
        ("OPT-H36", "Adjust versus don't", "The shift-plus-counter adjusted straddle beats the unadjusted one over a large sample."),
        ("OPT-H37", "Strangle to straddle", "Convert a short strangle into a straddle when spot nears the threatened strike."),
        ("OPT-H38", "Weekly Bank Nifty condor", "Iron condor Friday 9:20, shorts 500 points out, longs 800; convert to an iron fly once at an 800-point move."),
        ("OPT-H39", "Cap on adjustments", "Cap adjustments at 1-4, then exit."),
        ("OPT-H40", "Adjust only on breach", "No action inside the breakevens; adjust only on a breach."),
):
    card(_cid, _title, "FORWARD", _rule, india="yes", forward=REC,
         note="Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.")

card("OPT-H14", "Capital per lot", "DEFERRED", "One lot per 2-2.5 lakh.", note="Sizing rule: deferred by Madhav.")
card("OPT-H15", "Gap-stress sizing", "DEFERRED", "Size so a stress gap costs a fixed small share.", note="Sizing rule: deferred by Madhav.")
card("OPT-H33", "FII/DII flows", "NEEDS_DATA", "FII selling versus DII buying predicts returns.", note="The FII/DII cash-flow table in the lake is empty.")
card("OPT-H44", "Bitcoin daily condor", "NOT_INDIA", "BTC daily-expiry condor.", india="no", note="Crypto, not India. Crypto has its own locked research.")
card("OPT-H53", "Pair ratio at 2 SD", "NEEDS_DATA", "Same-sub-sector pairs revert from 2 SD.", note="Needs a sub-sector map to pick the pairs.")
card("OPT-H54", "Expectancy screen", "NEEDS_BUILD", "High in-sample expectancy keeps working out of sample.",
     note="Testable on our own ledger once enough systems have both dev and validation trade logs; a later check.")
card("OPT-H56", "Stop-limit versus stop-market", "NEEDS_DATA", "Stop-limit buffers in fast spikes.", note="Needs tick and order-book data.")
card("OPT-H60", "Nifty P/E zones", "NEEDS_DATA", "Buy at P/E 18-19 or lower.", note="No Nifty P/E history in the lake (NSE publishes it; a fetch is needed).")
card("OPT-H43", "Call ratio spread 1:3", "AMBIGUOUS", "Long a call ~20% OTM, short 3 calls ~30% OTM, 30 days, net credit.",
     note="Index calls 20-30% out of the money do not trade on monthly Nifty/Bank Nifty; the numbers fit stocks or crypto. Needs his exact strikes before a test.")

card("OPT-H18", "Two thirds of days are range days", "DESCRIPTIVE",
     "Share of Nifty and Bank Nifty days with open-to-close within 1%, close-to-close within 1%, and moves over 2%, by period. His figures: Bank Nifty o-c within "
     "1% ~66% (2012-20); Nifty within 1% 62%+ and over 2% 10% or less (2006-21); Nifty c-c within 1% ~68% (since 2000).")


@desc("OPT-H18")
def _(P):
    ts.index_panel()
    ohl, piv = ts._P["index_ohl"], ts._P["index"]
    out = {}
    for sym, name in (("NIFTY", "NIFTY 50"), ("BANKNIFTY", "NIFTY BANK")):
        o, c = ohl["open"][name], piv[name]
        oc, cc = (c / o - 1).abs(), c.pct_change().abs()
        ok = o.notna() & (o > 0) & (o != c.shift(1))
        for per, lo, hi in (("2003-2011", "2003", "2011"), ("2012-2020", "2012", "2020"), ("2018-2023", "2018", "2023"), ("all to 2023", "2003", "2023")):
            sel = (c.index >= f"{lo}-01-01") & (c.index <= f"{hi}-12-31")
            out[f"{sym} {per}"] = {"oc_within_1pct": round(float((oc[sel & ok] <= 0.01).mean()), 3), "cc_within_1pct": round(float((cc[sel] <= 0.01).mean()), 3),
                                   "cc_over_2pct": round(float((cc[sel] > 0.02).mean()), 3), "days_with_real_open": int((sel & ok).sum())}
    return out


card("OPT-H19", "VIX buckets and realised range", "DESCRIPTIVE",
     "Nifty mean (high-low)/open, mean |open-to-close| and mean |overnight gap| for VIX under 14, 14-20 and over 20. His figures: 0.78/1.0/1.78% range, 0.4/0.56/1.0% "
     "open-to-close, gaps ~3x larger above 20 than below 14.")


@desc("OPT-H19")
def _(P):
    ts.index_panel()
    ohl, piv = ts._P["index_ohl"], ts._P["index"]
    o, h, l, c, v = ohl["open"]["NIFTY 50"], ohl["high"]["NIFTY 50"], ohl["low"]["NIFTY 50"], piv["NIFTY 50"], piv["INDIA VIX"].shift(1)
    ok = o.notna() & (o > 0) & (o != c.shift(1)) & v.notna()
    d = pd.DataFrame({"rng": (h - l) / o, "oc": (c / o - 1).abs(), "gap": (o / c.shift(1) - 1).abs(), "b": pd.cut(v, [0, 14, 20, 999], labels=["<14", "14-20", ">20"])})[ok]
    g = d.groupby("b", observed=True).agg(range_pct=("rng", "mean"), oc_pct=("oc", "mean"), gap_pct=("gap", "mean"), days=("rng", "size"))
    return {k: {kk: (round(float(vv) * 100, 3) if kk != "days" else int(vv)) for kk, vv in r.items()} for k, r in g.to_dict("index").items()}


card("OPT-H48", "Range breakouts", "TEST",
     "Stocks closing above a 20-session range no wider than 10% beat the market drift over 5 and 10 sessions; 60-session ranges (15% or tighter) beat the 20-session "
     "ones over 10. Nifty: a close above a 20-session range no wider than 4% is followed by higher 5 and 10 session returns than other sessions.",
     {"stk20|net5": 1, "stk20|net10": 1, "stk60_vs_20|net10": 1, "nifty20|nfwd5": 1, "nifty20|nfwd10": 1})


@test("OPT-H48")
def _(P):
    s = P.s
    e20 = _ev(s, (s["rng20"] <= 0.10) & (s["c"] > s["hi20_prev"]))
    e60 = _ev(s, (s["rng60"] <= 0.15) & (s["c"] > s["hi60_prev"]))
    d = s[P.s5 | e20]
    out = {f"stk20|net{h}": ts.level(d, e20.reindex(d.index), f"net{h}") for h in (5, 10)}
    out["stk60_vs_20|net10"] = ts.split(s, e60, "net10", base=e20 | e60)
    ts.index_panel()
    hh, ll, c = ts._P["index_ohl"]["high"]["NIFTY 50"], ts._P["index_ohl"]["low"]["NIFTY 50"], ts._P["index"]["NIFTY 50"]
    M = P.m
    hi20, lo20 = hh.rolling(20).max().shift(1), ll.rolling(20).min().shift(1)
    ev = ((hi20 / lo20 - 1) <= 0.04) & (c > hi20)
    out.update({f"nifty20|nfwd{h}": ts.split(M, ev.reindex(M.index).fillna(False), f"nfwd{h}") for h in (5, 10)})
    return out


card("OPT-H49", "Big red day without follow-through", "TEST",
     "After a 1.5%+ down day in an uptrend stock (above its 200 DMA, rising 50 DMA), if the next 3 closes stay above that day's low, the next 5 and 20 sessions "
     "(counted from day 3) beat red days that did get follow-through.",
     {"p3net5": 1, "p3net20": 1})


@test("OPT-H49")
def _(P):
    s = P.s
    up = (s["dist_sma200"] > 0) & s["sma50_up"].astype(bool)
    nf, ff = _ev(s, s["nf3"].astype(bool) & up), _ev(s, s["ff3"].astype(bool) & up)
    return {f"p3net{h}": ts.split(s, nf, f"p3net{h}", base=nf | ff) for h in (5, 20)}


card("OPT-H50", "Swing-low invalidation", "TEST",
     "Stocks closing below their last confirmed swing low earn less over 5, 10 and 20 sessions than stocks still above it (every 5th session).",
     {"net5": -1, "net10": -1, "net20": -1}, note="The short-side half is not tested: the India paper book is long only.")


@test("OPT-H50")
def _(P):
    s = P.s
    ok = P.s5 & s["last_pivot_low"].notna()
    return {f"net{h}": ts.split(s, s["below_swing"].astype(bool), f"net{h}", base=ok) for h in (5, 10, 20)}


card("OPT-H51", "New all-time highs", "TEST",
     "A stock's first close above every earlier high (one per 10 sessions) beats the market drift over 5, 10 and 20 sessions; Nifty all-time-high closes are "
     "followed by higher 5 and 21 session returns than other sessions.",
     {"stk|net5": 1, "stk|net10": 1, "stk|net20": 1, "nifty|nfwd5": 1, "nifty|nfwd21": 1})


@test("OPT-H51")
def _(P):
    s = P.s
    ev = _ev(s, s["ath"].astype(bool) & (s["n"] >= 250))
    d = s[P.s5 | ev]
    out = {f"stk|net{h}": ts.level(d, ev.reindex(d.index), f"net{h}") for h in (5, 10, 20)}
    M = P.m
    out.update({f"nifty|nfwd{h}": ts.split(M, M["nifty_ath"].fillna(False).astype(bool), f"nfwd{h}") for h in (5, 21)})
    return out


card("OPT-H52", "Broken resistance holds on the first retest", "TEST",
     "The first retest of a broken 60-session high (low within 1% of the level, close no more than 2% under it, 5-20 sessions after the breakout) beats the market drift over 10 sessions.",
     {"first_retest|net10": 1}, note="His conflicting claims about later retests are not tested (no objective count of 'tests' before the break).")


@test("OPT-H52")
def _(P):
    s = P.s
    ev = s["retest1"].astype(bool)
    d = s[P.s5 | ev]
    return {"first_retest|net10": ts.level(d, ev.reindex(d.index), "net10")}


card("OPT-H55", "Charges eat option sellers' profits", "DESCRIPTIVE",
     "For a typical index-option round trip, the share of total cost that is statutory (STT, exchange, GST, stamp, SEBI) versus brokerage, from the cost model; "
     "and the cost as a share of the gross on the F01 short straddles. His figures: statutory ~88% of cost; costs 10-20% of gross profit.")


@desc("OPT-H55")
def _(P):
    from india import costs
    out = {}
    for prem in (5_000, 15_000, 40_000):
        tot = costs.cost("options", "sell", prem, 2023) + costs.cost("options", "buy", prem * 0.5, 2023)
        brk = 40.0
        out[f"premium Rs {prem:,} sold, bought back at half"] = {"total_rs": round(tot, 2), "statutory_share": round(1 - brk / tot, 3)}
    f01 = paths.gold() / "studies" / "F01_straddles.parquet"
    if f01.exists():
        x = pd.read_parquet(f01)
        gross = (x["credit"] - x["payoff"]) * x["lot"]
        fees = gross - x["pnl_inr"]
        win = gross > 0
        out["F01 short straddles"] = {"trades": int(len(x)), "fees_over_gross_profit_on_winners": round(float(fees[win].sum() / gross[win].sum()), 3),
                                      "fees_plus_spread_over_net": round(float((fees.sum() + x["spread_inr"].sum()) / max(1.0, abs(x["pnl_inr"].sum()))), 3)}
    return out


# ---- Optionables on end-of-day F&O files (india/teachers_fo.py). Settlement/close prices, not quotes: every leg pays a 0.4% half-spread (min Rs 0.05)
# plus Zerodha charges; one lot; P&L as a share of a Rs 50,000 book. Weekly Bank Nifty expiries from mid-2016, weekly Nifty from 2019, monthly before.
card("OPT-H16", "Weekly straddle: naked versus winged", "TEST",
     "Sell the ATM weekly straddle at the first session's open of the expiry week (Friday, or the session after the previous expiry), hold to expiry "
     "settlement. Naked earns more than zero; naked minus the version with wings bought at the breakevens (strikes nearest K +/- the credit) is positive.",
     {"BANKNIFTY|naked": 1, "BANKNIFTY|naked_minus_winged": 1, "NIFTY|naked": 1, "NIFTY|naked_minus_winged": 1},
     note="Weekly expiries only: Bank Nifty from 2016 and Nifty from 2019 leave too few development quarters, so INCONCLUSIVE is likely by design.")
card("OPT-H17", "Overnight expiry-eve strangle", "TEST",
     "Sell the call and put about 200 points out (Bank Nifty), or 0.7% of spot, at the close the session before expiry; buy back at the expiry-day open. "
     "A winged version buys the strikes 550 points out. Earns more than zero; his figures: 75%+ wins, 20-25% a year, max drawdown ~11%.",
     {"BANKNIFTY|200pt": 1, "BANKNIFTY|0.7pct": 1, "BANKNIFTY|200pt_wings550": 1, "NIFTY|0.7pct": 1},
     note="His 9:20 exit is approximated by the expiry-day open price in the bhavcopy; his 75% stop at 9:16 is then the same moment.")
card("OPT-H20", "VIX level and premium selling", "TEST",
     "The short ATM straddle sold 5 sessions before each expiry and held to expiry earns more when VIX is under 14 than at 14+ (claim a), and more when VIX is "
     "over 20 than at 20 or less (claim d). His videos conflict, so both are registered; claim (b) 'worse in low VIX' shows as OPPOSITE on the first.",
     {"BANKNIFTY|vix_lt14": 1, "NIFTY|vix_lt14": 1, "BANKNIFTY|vix_gt20": 1, "NIFTY|vix_gt20": 1})
card("OPT-H21", "Rising VIX hurts premium sellers", "TEST",
     "The same straddle earns less when VIX rose over the prior 5 sessions, and when it rose 10%+ from under 14.",
     {"BANKNIFTY|vix_rising": -1, "NIFTY|vix_rising": -1, "BANKNIFTY|vix_rising_from_low": -1, "NIFTY|vix_rising_from_low": -1})
card("OPT-H24", "Flat through binary events", "TEST",
     "A short ATM straddle sold at the close and bought back at the next open earns less on nights before scheduled binary events (elections, RBI, Budget, "
     "Fed, from the event table) than on other nights.",
     {"BANKNIFTY|event_nights": -1, "NIFTY|event_nights": -1})
card("OPT-H25", "OI band contains the expiry", "TEST",
     "k sessions before expiry (k = 5, 1), the settlement lands between the biggest put-OI strike below spot and the biggest call-OI strike above spot more "
     "often than inside a band of the same width centred on spot.",
     {"NIFTY|k5": 1, "NIFTY|k1": 1, "BANKNIFTY|k5": 1, "BANKNIFTY|k1": 1})
card("OPT-H26", "OI band contains tomorrow", "TEST",
     "The next session's high and low stay inside the prior close's biggest call-OI and put-OI strikes (nearest expiry) more often than inside an equal-width band centred on the close.",
     {"NIFTY": 1, "BANKNIFTY": 1})
card("OPT-H27", "OI levels fail when VIX is high", "TEST",
     "The H26 band holds less often when VIX is 20 or more.", {"NIFTY|vix_ge20": -1, "BANKNIFTY|vix_ge20": -1})
card("OPT-H28", "PCR and direction", "TEST",
     "Nearest-expiry put/call OI ratio at the close against the index from the next open to the close 1 or 5 sessions later: (a) PCR over 1.2 bullish; "
     "(b) PCR under 0.5 contrarian bullish; (c) PCR under 0.7 bearish. All three registered (his videos contradict each other).",
     {"NIFTY|a_gt1.2|d1": 1, "NIFTY|a_gt1.2|d5": 1, "NIFTY|b_lt0.5|d1": 1, "NIFTY|b_lt0.5|d5": 1, "NIFTY|c_lt0.7|d1": -1, "NIFTY|c_lt0.7|d5": -1,
      "BANKNIFTY|a_gt1.2|d5": 1, "BANKNIFTY|b_lt0.5|d5": 1, "BANKNIFTY|c_lt0.7|d5": -1})
card("OPT-H29", "PCR near 1 means a quiet day", "TEST",
     "With PCR 0.85-1.15 and the biggest single strike holding more than the median share of OI, the next session's range (and the next 5 sessions') is narrower.",
     {"NIFTY|d1": -1, "BANKNIFTY|d1": -1, "NIFTY|d5": -1})
card("OPT-H30", "OI change near the money", "TEST",
     "Within 2% of spot (nearest expiry): call OI falling while put OI rises predicts a higher index over 1 and 5 sessions; call OI added at 2x the put OI added "
     "while put OI falls predicts a lower one.",
     {"NIFTY|bull|d1": 1, "NIFTY|bull|d5": 1, "NIFTY|bear|d1": -1, "NIFTY|bear|d5": -1, "BANKNIFTY|bull|d5": 1, "BANKNIFTY|bear|d5": -1})
card("OPT-H31", "Max-OI pinning", "TEST",
     "Expiry settles closer to the strike with the biggest call+put OI (k = 1, 3 sessions before) than to the at-the-money strike at the same time.",
     {"NIFTY|k1": -1, "NIFTY|k3": -1, "BANKNIFTY|k1": -1, "BANKNIFTY|k3": -1})
card("OPT-H32", "OI the day after expiry", "TEST",
     "The OI band (H25) taken from the next contract on the first session after an expiry contains that contract's settlement more often than the band taken on the expiry day itself.",
     {"NIFTY": 1, "BANKNIFTY": 1})
card("OPT-H41", "Early profit-taking", "TEST",
     "Short weekly ATM straddle (H16 entries, naked): closing at the first daily close where it has kept 65%, 75% or 90% of the credit beats holding to expiry.",
     {"BANKNIFTY|take65": 1, "BANKNIFTY|take75": 1, "BANKNIFTY|take90": 1, "NIFTY|take65": 1, "NIFTY|take75": 1, "NIFTY|take90": 1},
     note="Re-entry after the early close is not simulated.")
card("OPT-H42", "Monthly put ratio spread 1:2", "TEST",
     "About 20 sessions before monthly expiry: buy the ATM put, sell 2 puts ~1.3% lower, hold to expiry. Earns more than zero (Nifty, Bank Nifty); net-credit "
     "entries beat net-debit ones; entries with VIX over 20 beat the rest. His figure: profitable 60-70% of months.",
     {"NIFTY|all": 1, "BANKNIFTY|all": 1, "NIFTY|credit_vs_debit": 1, "NIFTY|vix_gt20": 1}, note="His 3-4% capital stop and margins are not modelled.")
card("OPT-H45", "Implied probabilities are well calibrated", "TEST",
     "5 sessions before expiry, the probability of settling above each near strike from adjacent call prices scores better (lower Brier score) than a lognormal "
     "built from the last 20 sessions' realised volatility.",
     {"NIFTY": 1, "BANKNIFTY": 1})
card("OPT-H46", "Most OTM call buyers lose", "DESCRIPTIVE",
     "Share of 1-3% out-of-the-money calls bought 5 sessions before expiry and held to expiry that end above their cost; same for debit call spreads. His figure: one third or fewer.")
card("OPT-H47", "Buying after an IV spike loses", "TEST",
     "After a 25%+ weekly VIX jump (and with VIX over 30), an ATM Nifty call bought at the close and sold 3 sessions later loses on average.",
     {"NIFTY|vix_jump25_gt30": -1, "NIFTY|vix_jump25": -1})
card("OPT-H57", "Cheap OTM options spike on expiry day", "DESCRIPTIVE",
     "On expiry days, share of options opening at Rs 5 or less whose day high reaches 8x the open, and how many close back under 2x.")
card("OPT-H58", "Holiday weeks decay faster", "TEST",
     "The ATM straddle's decay per session from the start of the expiry week to the expiry eve is faster in weeks shortened by a holiday.",
     {"NIFTY": 1, "BANKNIFTY": 1})
card("OPT-H59", "Next week's straddle sold on expiry day", "TEST",
     "On each weekly expiry day, sell the next expiry's ATM straddle at the close; buy back at the next open, or at the next close. Earns more than zero.",
     {"NIFTY|next_open": 1, "NIFTY|next_close": 1, "BANKNIFTY|next_open": 1, "BANKNIFTY|next_close": 1},
     note="He sells around 15:00; the close is the nearest end-of-day price.")


# =================================================================================================================== running and reporting
OUT = paths.gold() / "teachers"


def _repo() -> "Path":
    from pathlib import Path
    return Path(__file__).resolve().parent


def union_k(teacher: str) -> int:
    return sum(len(c["variants"]) for c in CARDS.values() if c["teacher"] == teacher and c["status"] == "TEST")


def _load_more():
    from india import teachers_exits, teachers_fo  # noqa: F401  (their @test functions register here)


def write_cards() -> str:
    _load_more()
    lines = ["# Teacher cards v1 (pre-registration, written 25 Oct 2026 before any result was seen)", "",
             "Madhav's request: extract everything useful for the Indian market from the two YouTube teachers, test every strategy that can be tested, keep "
             "every result, and track the survivors forward. Source registers: Trade With Trend TWT-H01..H60 and Optionables OPT-H01..H60 (paraphrased "
             "from public videos; members-only videos not used).", "",
             f"Bars: family teacher_twt k = {union_k('TWT')}, teacher_opt k = {union_k('OPT')} (frozen in every registration); two-sided Bonferroni z at "
             f"{registry.threshold(union_k('TWT')):.2f} and {registry.threshold(union_k('OPT')):.2f}. VALIDATED needs |t| at z in both development "
             "(2000-2017) and validation (2018-2023) with the same sign; CONDITIONAL needs z in one and 1.65 in the other. t is across calendar-quarter "
             "means; at least 16 quarters per period. 2024 onward stays sealed.", ""]
    counts = pd.Series([c["status"] for c in CARDS.values()]).value_counts().to_dict()
    lines += ["Status counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), ""]
    for t in ("TWT", "OPT"):
        lines += [f"## {TEACHER[t]}", ""]
        for cid in sorted((c for c in CARDS if c.startswith(t)), key=lambda x: int(x.split("H")[1])):
            c = CARDS[cid]
            lines.append(f"### {cid} · {c['title']} · {c['status']}")
            lines.append(c["rule"])
            if c["variants"]:
                lines.append("Variants (expected sign): " + "; ".join(f"`{k}` {'+' if v > 0 else '-'}" for k, v in c["variants"].items()))
            if c["note"]:
                lines.append(f"Note: {c['note']}")
            if c["forward"]:
                lines.append(f"Forward: {c['forward']}")
            lines.append("")
    p = _repo() / "registrations" / "teachers_v1.md"
    p.write_text("\n".join(lines))
    return str(p)


def run(ids: list[str] | None = None) -> list[dict]:
    _load_more()
    P = Ctx()
    todo = [cid for cid, c in CARDS.items() if c["status"] == "TEST" and (not ids or cid in ids or c["teacher"] in ids)]
    rows = []
    for cid in todo:
        c = CARDS[cid]
        if cid not in TESTS:
            print(f"{cid}: no test function yet", flush=True)
            continue
        reg = registry.register(f"T-{cid}", family=FAM[c["teacher"]], title=f"{TEACHER[c['teacher']]} · {cid} {c['title']}", hypothesis=c["rule"],
                                variants=list(c["variants"]), note=c["note"], union_k=union_k(c["teacher"]))
        try:
            res = TESTS[cid](P)
        except Exception as e:  # noqa: BLE001  a crash is recorded as such, never silently skipped
            print(f"{cid}: test failed: {type(e).__name__}: {e}", flush=True)
            res = {}
            err = f"{type(e).__name__}: {e}"
        else:
            err = None
        for var, expect in c["variants"].items():
            r = res.get(var)
            if r is None:
                line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True, "error": err}, expect=expect)
            else:
                line = registry.record(reg, var, r["dev"], r["val"], extra=_clean(r.get("extra", {})), expect=expect)
            rows.append({"card": cid, "teacher": c["teacher"], "variant": var, "expect": expect, "verdict": line["verdict"], "dev": line["dev"], "val": line["val"],
                         "z": line["z"], "extra": line["extra"]})
            d, v = line["dev"], line["val"]
            print(f"{cid:8s} {var:32s} {line['verdict']:12s} dev {_f(d[0])} t {_f(d[1], 1)} q{d[2]} | val {_f(v[0])} t {_f(v[1], 1)} q{v[2]}", flush=True)
    registry.mirror_to_catalog()
    return rows


def _f(x, nd=4):
    return "  nan " if x is None or x != x else (f"{x:+.{nd}f}" if nd != 1 else f"{x:+.1f}")


def _clean(d: dict) -> dict:
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, (np.floating, np.integer)):
            v = v.item()
        if isinstance(v, float) and v != v:
            v = None
        if isinstance(v, list):
            v = [None if (isinstance(x, float) and x != x) else (x.item() if isinstance(x, (np.floating, np.integer)) else x) for x in v]
        out[k] = v
    return out


def descriptives() -> dict:
    _load_more()
    P = Ctx()
    out = {}
    for cid, f in DESCS.items():
        try:
            out[cid] = f(P)
        except Exception as e:  # noqa: BLE001
            out[cid] = {"error": f"{type(e).__name__}: {e}"}
        print(cid, json.dumps(out[cid], default=str)[:600], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "descriptive.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def latest_results() -> pd.DataFrame:
    rows = [json.loads(x) for x in open(paths.manifest_dir() / "test_ledger.jsonl")]
    res = [r for r in rows if r["kind"] == "result" and str(r["study"]).startswith("T-")]
    df = pd.DataFrame(res)
    if df.empty:
        return df
    df = df.sort_values("at").groupby(["study", "variant"], as_index=False).last()
    df["card"] = df["study"].str[2:]
    return df


def report() -> str:
    _load_more()
    df = latest_results()
    OUT.mkdir(parents=True, exist_ok=True)
    cards = pd.DataFrame(CARDS.values())
    if not df.empty:
        flat = df.assign(dev_mean=df["dev"].str[0], dev_t=df["dev"].str[1], dev_q=df["dev"].str[2], val_mean=df["val"].str[0], val_t=df["val"].str[1],
                         val_q=df["val"].str[2], extra=df["extra"].map(lambda e: json.dumps(e, default=str)))
        flat = flat[["card", "variant", "verdict", "z", "dev_mean", "dev_t", "dev_q", "val_mean", "val_t", "val_q", "k_in_family", "extra", "at"]]
        flat.to_parquet(OUT / "results.parquet", index=False)
        flat.to_csv(OUT / "results.csv", index=False)
    cards.to_csv(OUT / "cards.csv", index=False)
    desc = json.loads((OUT / "descriptive.json").read_text()) if (OUT / "descriptive.json").exists() else {}
    lines = ["# Teacher cards v1 · results", "", f"Generated {pd.Timestamp.now(tz='America/Toronto'):%d %b %Y %H:%M} Toronto. Rules and variants: teachers_v1.md.", ""]
    for t in ("TWT", "OPT"):
        cs = [c for c in CARDS.values() if c["teacher"] == t]
        st = pd.Series([c["status"] for c in cs]).value_counts().to_dict()
        lines += [f"## {TEACHER[t]}", "", "Cards: " + ", ".join(f"{k} {v}" for k, v in sorted(st.items())), ""]
        if not df.empty:
            sub = df[df["card"].str.startswith(t)]
            vc = sub["verdict"].value_counts().to_dict()
            lines += ["Variant verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(vc.items())), "",
                      "| card | variant | verdict | dev mean | dev t | val mean | val t | val quarters |", "|---|---|---|---|---|---|---|---|"]
            sub = sub.assign(_n=sub["card"].str.split("H").str[1].astype(int)).sort_values(["_n", "variant"])
            for _, r in sub.iterrows():
                lines.append(f"| {r['card']} | {r['variant']} | {r['verdict']} | {_f(r['dev'][0])} | {_f(r['dev'][1], 1)} | {_f(r['val'][0])} | {_f(r['val'][1], 1)} | {r['val'][2]} |")
            lines.append("")
    if desc:
        lines += ["## Descriptive checks (his base rates, measured)", ""]
        for cid, d in desc.items():
            lines.append(f"**{cid} {CARDS.get(cid, {}).get('title', '')}**: `{json.dumps(d, default=str)}`")
            lines.append("")
    p = _repo() / "registrations" / "teachers_results_v1.md"
    p.write_text("\n".join(lines))
    return str(p)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cards"
    if cmd == "cards":
        print(write_cards())
        print({t: union_k(t) for t in ("TWT", "OPT")})
    elif cmd == "run":
        run(sys.argv[2:] or None)
    elif cmd == "desc":
        descriptives()
    elif cmd == "report":
        print(report())
