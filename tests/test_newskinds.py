"""The news kinds dictionary (india/newskinds.py, NC1): a few plain cases each way, so a later edit that changes how news is read shows up."""
from india import newskinds as nk


def test_results_by_category_and_by_text():
    assert nk.kinds("Financial Result Updates", "XYZ Limited has informed the Exchange regarding the results") == ["results"]
    assert "results" in nk.kinds("Outcome of Board Meeting", "approved the Unaudited Financial Results for the quarter ended June 30, 2019")


def test_an_order_win_is_not_a_court_order():
    assert "order_win" in nk.kinds("Updates", "ABC Ltd has received an order worth Rs 450 crore from NHAI")
    assert "order_win" in nk.kinds("Press Release", "Company bags Letter of Award for a metro rail project")
    assert "order_win" not in nk.kinds("Updates", "copy of the order passed by the Hon'ble Court dated 3 March")


def test_usfda_adverse_and_approval_are_apart():
    assert nk.kinds("Updates", "The USFDA has issued a Warning Letter to the company's Halol facility") == ["usfda_adverse"]
    assert nk.kinds("Updates", "Company receives final approval from USFDA for its ANDA") == ["usfda_approval"]
    assert "usfda_approval" not in nk.kinds("Updates", "USFDA inspection concluded with 3 observations in Form 483")


def test_ratings_up_and_down():
    assert "rating_down" in nk.kinds("Credit Rating", "CRISIL has downgraded the rating of the company's bank facilities")
    assert "rating_up" in nk.kinds("Credit Rating", "ICRA has upgraded the long term rating to AA")
    assert "rating_up" not in nk.kinds("Credit Rating", "rating reaffirmed with outlook revised to Negative")


def test_management_exit_needs_a_senior_role():
    assert "management_exit" in nk.kinds("Resignation", "resignation of Mr X as Chief Financial Officer of the Company")
    assert "management_exit" not in nk.kinds("Resignation", "resignation of Mr X as Company Secretary")


def test_takeover_disclosures_are_holding_changes_not_mergers():
    k = nk.kinds("Disclosure under SEBI Takeover Regulations", "acquisition of shares by the promoter group")
    assert "holding_change" in k and "merger_acquisition" not in k


def test_routine_notices_carry_no_kind():
    assert nk.kinds("Loss of Share Certificates", "has informed the Exchange about loss of share certificates") == []
    assert nk.kinds("Trading Window", "closure of trading window") == []
    assert nk.kinds("Price movement", "The Exchange has sought clarification on the price movement") == []
    assert nk.routine("Copy of Newspaper Publication", "")


def test_every_kind_has_plain_words():
    assert all(nk.words(k) for k in nk.KINDS)
