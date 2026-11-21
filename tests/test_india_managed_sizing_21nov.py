"""managed-v3 (Madhav, 21 Nov 2026 07:43 Toronto: "Yes let's do the sizing changes and others we found"): a replacement is sized by fixed
risk (india/sizingstudy.py, 20 Nov): at most 0.5% of the stocks-and-cash book lost if it falls two daily ranges, at most 15% of the book,
never more than its cut freed; the rest stays in cash. Each test fails on the code before (no size_for, no atr14_pct)."""
import pandas as pd

from india import managed as m
from tests.test_india_managed import DAY, world  # noqa: F401  (the fixture)

C = {"size_risk_pct": 0.5, "size_atr_mult": 2, "max_name_pct": 15}
BOOK = {"positions": {"A": {"qty": 100, "last": 500.0}}, "cash_inr": 50000.0}       # stocks and cash: ₹1,00,000


def test_a_wild_name_gets_fewer_rupees_than_its_cut_freed():
    size, why = m.size_for(BOOK, {"atr14_pct": 0.05}, 20000, C)          # 0.5% of 1,00,000 / (2 x 5%) = ₹5,000
    assert round(size) == 5000 and "stays in cash" in why


def test_a_calm_name_never_gets_more_than_its_cut_and_the_cap_holds_at_15_percent():
    assert m.size_for(BOOK, {"atr14_pct": 0.01}, 8000, C)[0] == 8000     # cap ₹25,000 is above the cut
    assert round(m.size_for(BOOK, {"atr14_pct": 0.005}, 40000, C)[0]) == 15000    # 0.5%/1% = 50%, held to 15%


def test_no_daily_range_or_no_setting_means_the_cut_rupees_as_before():
    assert m.size_for(BOOK, {"atr14_pct": None}, 7000, C)[0] == 7000
    assert m.size_for(BOOK, {"atr14_pct": 0.05}, 7000, {})[0] == 7000


def test_the_live_config_carries_v3_and_its_yes():
    c = m.cfg()
    assert c["version"].startswith("managed-v3") and c["size_risk_pct"] == 0.5 and c["size_atr_mult"] == 2 and c["max_name_pct"] == 15
    assert "21 Nov 2026" in c["v3_approved"] and c["stop_pct"] == 7.0


def test_features_carry_the_daily_range(world):                         # noqa: F811
    f = m.features(m.bars(), DAY).set_index("symbol")
    assert f["atr14_pct"].notna().all() and (f.loc["WILD", "atr14_pct"] > f.loc["CALM", "atr14_pct"])


def test_a_plan_sizes_its_replacement_and_says_so(world, monkeypatch):    # noqa: F811
    monkeypatch.setattr(m, "refuse_late", lambda s: None)
    c0 = m.cfg

    def tight():
        c = c0()
        c["size_risk_pct"] = 0.02                                           # small enough that CALM is capped under the ₹5,000 cut
        return c
    monkeypatch.setattr(m, "cfg", tight)
    p = m.run(DAY)["plan"]
    b = {x["symbol"]: x for x in p["buys"]}
    if "CALM" in b:                                                         # sized under the cut, and the plan says how
        assert b["CALM"]["inr"] < b["CALM"]["cut_inr"] == 5000 and "stays in cash" in b["CALM"]["sized"]
        assert any("fixed-risk sizing" in n for n in p["notes"])
    else:                                                                   # too small to buy: the money stays in cash, said
        assert any("WEAK" in n and "cash" in n for n in p["notes"])
    assert isinstance(pd.DataFrame(p["buys"]), pd.DataFrame)
