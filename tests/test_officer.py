"""The officer's note labels the account's Canadian-dollar figures by code (audit OFFICER, Oct 15)."""


def test_account_figures_become_cad_and_market_prices_do_not():
    from jarvis.service.officer import cad_labels

    f = {"account": {"value_cad": 497.75, "cash_cad": 300.1, "positions": {"BTC": {"paid_cad": 120.0, "last_price_cad": 118000.0}}},
         "background": {"signals_today_by_rule": {"H07-UA": 2}}}
    note = "The book is at $498 with $300 in cash; Bitcoin trades near $118,000 here and US$83,000 abroad, and C$120 sits in BTC."
    assert cad_labels(note, f) == ("The book is at C$498 with C$300 in cash; Bitcoin trades near C$118,000 here and US$83,000 abroad, "
                                   "and C$120 sits in BTC.")
    assert cad_labels("Bitcoin is $80,900 today.", f) == "Bitcoin is $80,900 today."           # not an account figure


def test_a_figure_that_also_matches_a_market_number_is_left_alone():
    from jarvis.service.officer import cad_labels

    f = {"account": {"value_cad": 491.0}, "market": {"BCH": 490.0}}
    assert cad_labels("BCH closed at $490 and the book is at $491.", f) == "BCH closed at $490 and the book is at $491."
