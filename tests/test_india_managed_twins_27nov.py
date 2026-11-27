"""27 Nov 2026 (flag 290, Madhav 26 Nov 22:22: "Yes, let's set it up"): the managed book's two twins, the start held unchanged and the start
stocks all in NIFTYBEES, marked each session, and what Ananta's own decisions added or cost in rupees (stocks and cash only)."""
import json

import pandas as pd

from india import managedtwins as T
from india import paths

BOOK = {"start_day": "2026-10-30", "start_inr": 150000.0, "options_inr": 50000.0, "cash_inr": 1000.0,
        "sleeve_moves": [{"day": "2026-11-03", "from": "cash", "to": "options", "inr": 16000.0}],
        "positions": {"AAA": {"qty": 10, "last": 120.0, "source": "twin"}, "NEW": {"qty": 5, "last": 210.0, "source": "replacement"}},
        "trades": [{"side": "SELL", "symbol": "AAA", "qty": 10, "filled": True}, {"side": "SELL", "symbol": "BBB", "qty": 20, "filled": True},
                   {"side": "BUY", "symbol": "NEW", "qty": 5, "filled": True}, {"side": "SELL", "symbol": "NEW", "qty": 1, "filled": False}]}


def _closes():
    idx = pd.to_datetime(["2026-10-29", "2026-10-30", "2026-11-02", "2026-11-03"])
    return pd.DataFrame({"AAA": [99, 100, 110, 120], "BBB": [49, 50, 45, None], "NIFTYBEES": [99, 100, 105, 110], "NEW": [0, 200, 205, 210]}, index=idx)


def test_start_holdings_put_back_what_was_sold_of_the_account():
    assert T.start_holdings(BOOK) == {"AAA": 20, "BBB": 20}          # NEW was bought by the book, so it is not a start holding


def test_marks_and_the_decisions_line():
    m = T.marks(BOOK, _closes())
    # stocks and cash at the start: 150,000 - (50,000 - 16,000) = 116,000; stocks 20*100 + 20*50 = 3,000, so cash 113,000
    assert m["status"] == "ok" and m["stocks_start_inr"] == 3000 and m["cash_start_inr"] == 113000
    assert [r["day"] for r in m["marks"]] == ["2026-10-30", "2026-11-02", "2026-11-03"]
    last = m["marks"][-1]
    assert last["held_inr"] == 113000 + 20 * 120 + 20 * 45                # BBB had no close on 3 Nov, so it stays at its last close
    assert last["index_inr"] == round(113000 + 3000 * 1.10)
    w = T.words(BOOK, m, "2026-11-03")
    now = 10 * 120 + 5 * 210 + 1000 + 16000
    assert w["managed_stocks_cash_inr"] == now and w["decisions_vs_held_inr"] == now - last["held_inr"]
    assert w["words"].startswith("Ananta's own decisions since Fri 30 Oct cost ₹")
    assert "options lot apart" in w["words"] and "−" not in w["words"].split("cost")[1][:3]


def test_no_first_day_close_says_so():
    c = _closes().drop(pd.Timestamp("2026-10-30"))
    assert T.marks(BOOK, c)["status"] == "missing"


def test_build_writes_the_file_and_changes_nothing_else(tmp_path, monkeypatch):
    d = tmp_path / "paper" / "managed"
    d.mkdir(parents=True)
    (d / "state.json").write_text(json.dumps(BOOK))
    (d / "view.json").write_text(json.dumps({"day": "2026-11-03"}))
    monkeypatch.setattr(paths, "data_dir", lambda: tmp_path)
    from india import managed
    df = _closes().stack().rename("close").reset_index()
    df.columns = ["date", "symbol", "close"]
    monkeypatch.setattr(managed, "bars", lambda: df)
    out = T.build()
    assert out["status"] == "ok" and json.loads((d / "twins.json").read_text())["day"] == "2026-11-03"
    assert json.loads((d / "state.json").read_text()) == BOOK
    assert T.line() == out["words"]
