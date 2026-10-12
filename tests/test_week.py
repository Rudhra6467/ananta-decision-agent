"""Request #34: wins and losses of the last 7 days across every book."""
import sqlite3

from jarvis.service import week

NOW = 1_800_000_000


class FakeJ:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE evidence_trades (id TEXT, watch TEXT, coin TEXT, status TEXT, exit_t INTEGER, net_usd REAL)")

    def now(self):
        return NOW

    def _explorer(self):
        raise RuntimeError("no explorer here")

    def prices(self):
        return {}


def test_week_groups_books_and_keeps_the_window():
    j = FakeJ()
    rows = [("a", "JARVIS", "BTC", "CLOSED", NOW - 86400, 4.0), ("b", "JARVIS", "ETH", "CLOSED", NOW - 2 * 86400, -6.0),
            ("c", "JARVIS", "SOL", "CLOSED", NOW - 9 * 86400, 50.0),            # outside the 7 days
            ("d", "ZONE_TOUCH-UC", "RVN", "CLOSED", NOW - 3600, -2.0), ("e", "ZONE_TOUCH", "ETH", "OPEN", None, None),
            ("f", "RANDOM_10D-UA", "X", "CLOSED", NOW - 3600, -1.0), ("g", "JARVIS_RANDOM", "Y", "CLOSED", NOW - 3600, 1.0)]
    j.db.executemany("INSERT INTO evidence_trades VALUES (?,?,?,?,?,?)", rows)
    w = week.week(j)
    b = {x["key"]: x for x in w["books"]}
    assert b["JARVIS"]["closed"] == 2 and b["JARVIS"]["wins"] == 1 and b["JARVIS"]["net_usd"] == -2.0
    assert b["JARVIS"]["best"] == {"coin": "BTC", "usd": 4.0} and b["JARVIS"]["worst"] == {"coin": "ETH", "usd": -6.0}
    assert b["ZONE_TOUCH"]["closed"] == 1 and b["RANDOM_"]["closed"] == 1 and b["JARVIS_RANDOM"]["closed"] == 1
    assert w["totals"] == {"closed": 3, "wins": 1, "losses": 2, "net_usd": -4.0}       # random baselines are not counted as ours
    assert "explorer" in w["errors"]                                                   # a missing part is named, not fatal


def test_family_matching():
    assert week._family("H07-T30") == "H07" and week._family("JARVIS_RANDOM") == "JARVIS_RANDOM"
    assert week._family("RANDOM_20D-UB") == "RANDOM_" and week._family("UNKNOWN") is None
