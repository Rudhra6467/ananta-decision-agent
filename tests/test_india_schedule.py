"""The India jobs keep Indian time across Toronto's clock changes (2 Nov 2026: Monday's morning view came at 09:30 IST, after the open, because
Toronto left summer time on 1 Nov and the jobs stayed on the Toronto clock)."""
import datetime as dt

from jarvis.india import schedule as S


def test_winter_time_puts_the_morning_view_at_22_toronto():
    assert S.wanted("com.ananta.india.morningview", dt.date(2026, 11, 2)) == [{"Hour": 22, "Minute": 0}]
    assert S.wanted("com.ananta.india.openingview", dt.date(2026, 11, 2)) == [{"Hour": 23, "Minute": 50}]


def test_summer_time_puts_it_back_at_23():
    assert S.wanted("com.ananta.india.morningview", dt.date(2026, 10, 20)) == [{"Hour": 23, "Minute": 0}]
    assert S.wanted("com.ananta.india.morningview", dt.date(2027, 3, 16)) == [{"Hour": 23, "Minute": 0}]


def test_weekday_jobs_keep_indian_weekdays():
    post = S.wanted("com.ananta.india.postclose", dt.date(2026, 11, 2))
    assert [(e["Weekday"], e["Hour"], e["Minute"]) for e in post] == [(1, 5, 20), (2, 5, 20), (3, 5, 20), (4, 5, 20), (5, 5, 20)]
    spreads = S.wanted("com.ananta.india.spreads", dt.date(2026, 11, 2))         # 08:05 IST Mon-Fri = 21:35 Toronto Sun-Thu
    assert [(e["Weekday"], e["Hour"]) for e in spreads] == [(0, 21), (1, 21), (2, 21), (3, 21), (4, 21)]


def test_the_morning_chain_stays_in_order_and_before_the_open():
    for on in (dt.date(2026, 11, 2), dt.date(2026, 7, 1)):
        ist = [S.TARGETS[k][0][-1] for k in ("com.ananta.india.autologin", "com.ananta.india.sp1paper", "com.ananta.india.paper",
                                              "com.ananta.india.findings", "com.ananta.india.morningview", "com.ananta.india.shadowtrader")]
        assert ist == sorted(ist) and ist[-1] < "09:15"
