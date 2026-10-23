"""G01 v2: the exit policy book by situation and its pre-declared verdict rule."""
from __future__ import annotations

import numpy as np
import pandas as pd

from india import exitbook


def _cell(sit, pol, per, mar, net, growth, trades=1000):
    return {"situation": sit, "policy": pol, "period": per, "trades": trades, "mean_net": net, "p5": -0.1, "worst": -0.3, "days": 20.0, "net_per_20d": net,
            "excess_vs_null": -0.001, "excess_t": -1.0, "book_growth_pa": growth, "book_max_dd": -0.3, "book_mar": mar, "book_trades": 100, "book_skip_share": 0.1}


def test_judge_marks_held_not_held_and_inconclusive():
    rows = []
    # dev ranking: A > B > C > D ; val ranking: C > A > E > F > G > B > D
    for pol, mar in (("A", 0.5), ("B", 0.4), ("C", 0.3), ("D", 0.2), ("E", 0.1), ("F", 0.05), ("G", 0.01), ("random_exit", 9.0)):
        rows.append(_cell("all", pol, "dev", mar, 0.01, 0.05))
    for pol, mar, net in (("C", 0.6, 0.02), ("A", 0.5, 0.01), ("E", 0.4, 0.01), ("F", 0.3, 0.01), ("G", 0.2, 0.01), ("B", 0.1, 0.01), ("D", 0.0, -0.01), ("random_exit", 9.0, 0.1)):
        rows.append(_cell("all", pol, "val", mar, net, 0.05 if net > 0 else -0.02))
    # a thin cell: dev leader with too few validation trades
    rows.append(_cell("below_both", "A", "dev", 0.5, 0.01, 0.05))
    rows.append(_cell("below_both", "A", "val", 0.5, 0.01, 0.05, trades=50))
    v = exitbook.judge(pd.DataFrame(rows)).set_index(["situation", "policy"])
    assert v.loc[("all", "A"), "verdict"] == "HELD"          # dev 1, val 2
    assert v.loc[("all", "C"), "verdict"] == "HELD"          # dev 3, val 1
    assert v.loc[("all", "B"), "verdict"] == "NOT_HELD"      # dev 2, val 6
    assert v.loc[("all", "D"), "verdict"] == ""              # not a dev leader
    assert ("all", "random_exit") not in v.index             # never ranked
    assert v.loc[("below_both", "A"), "verdict"] == "INCONCLUSIVE"
    assert int(v.loc[("all", "C"), "val_rank"]) == 1 and int(v.loc[("all", "A"), "dev_rank"]) == 1


def test_judge_requires_positive_val_net_and_growth():
    rows = [_cell("all", "A", "dev", 0.5, 0.01, 0.05), _cell("all", "B", "dev", 0.4, 0.01, 0.05),
            _cell("all", "A", "val", 0.5, -0.001, 0.05), _cell("all", "B", "val", 0.4, 0.01, -0.01)]
    v = exitbook.judge(pd.DataFrame(rows)).set_index("policy")["verdict"]
    assert v["A"] == "NOT_HELD" and v["B"] == "NOT_HELD"


def test_nifty_state_three_states(tmp_path, monkeypatch):
    days = pd.bdate_range("2010-01-01", periods=420)
    close = np.concatenate([np.linspace(100, 200, 260), np.linspace(200, 120, 160)])
    d = pd.DataFrame({"index_name": "NIFTY 50", "date": days.date, "close": close})
    d2 = d.assign(index_name="INDIA VIX", close=20.0)
    root = tmp_path / "silver" / "kite_index" / "day"
    root.mkdir(parents=True)
    pd.concat([d, d2]).to_parquet(root / "day.parquet")
    monkeypatch.setattr(exitbook.paths, "silver", lambda name: tmp_path / "silver" / name)
    st = exitbook.nifty_state()
    assert st.index.min() == days[199]                      # the first session with a 200-day average
    assert st.loc[days[259]] == "above_both"                # top of the rise
    assert st.loc[days[-1]] == "below_both"                 # end of the fall
    assert "mixed" in set(st.values)                        # the turn in between
