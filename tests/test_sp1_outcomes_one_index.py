"""sp1.outcomes with state rows for only one index (the live scorer, sp1paper.score, passes the traded index's rows only).

Found by the morning review of 26 Oct 2026: the first traded SP1 paper decision (BANKNIFTY D2 ATRSTOP, 26 Oct) made the 07:00 score job
crash with "IndexError: arrays used as indices must be of integer (or boolean) type", because outcomes() also looped over NIFTY, which had
no state rows. An index with no state rows is now skipped; the rows of the index that has them are unchanged.
"""
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india import ocstudy, sp1  # noqa: E402


def _minutes(days):
    rows = []
    rng = np.random.default_rng(7)
    for name, base in (("NIFTY 50", 22600.0), ("NIFTY BANK", 50000.0)):
        for d in days:
            px = base + np.cumsum(rng.normal(0, 3, ocstudy.NMIN))
            for m in range(ocstudy.NMIN):
                p = float(px[m])
                rows.append({"index_name": name, "date": d, "m": m, "open": p, "high": p + 2, "low": p - 2, "close": p + 0.5})
    return pd.DataFrame(rows)


def _src(states_for):
    days = [dt.date(2026, 10, 23), dt.date(2026, 10, 26), dt.date(2026, 10, 27)]
    index = ocstudy.index_arrays(_minutes(days))
    st = pd.DataFrame([{"date": d, "index": s, "atr14_prev": a} for s in states_for for d, a in ((days[0], np.nan), (days[1], 300.0))])
    lots = pd.DataFrame([{"date": d, "symbol": s, "lot": 30.0} for d in days[:2] for s in sp1.IDX])
    chains = pd.DataFrame(columns=["date", "symbol", "expiry", "strike", "opt_type", "fwd", "iv", "volume"])
    return {"days": days, "specials": set(), "states": st, "index": index, "lots": lots, "chains": chains}


def test_one_index_only(tmp_path):
    o = sp1.outcomes(lambda s: None, src=_src(["BANKNIFTY"]), out_file=tmp_path / "o.parquet")
    assert len(o) > 0
    assert set(o["index"]) == {"BANKNIFTY"}


def test_same_rows_as_with_both(tmp_path):
    one = sp1.outcomes(lambda s: None, src=_src(["BANKNIFTY"]), out_file=tmp_path / "a.parquet")
    both = sp1.outcomes(lambda s: None, src=_src(["NIFTY", "BANKNIFTY"]), out_file=tmp_path / "b.parquet")
    b = both[both["index"] == "BANKNIFTY"].reset_index(drop=True)
    pd.testing.assert_frame_equal(one.reset_index(drop=True), b, check_dtype=False)
