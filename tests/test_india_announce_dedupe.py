"""3 Nov 2026: announcements without a seq_id (most of 2010-2012) must not collapse into one row."""
import pandas as pd

from india import announce


def test_rows_without_seq_id_are_kept_and_true_repeats_dropped():
    d = pd.Timestamp("2010-01-04")
    df = pd.DataFrame([
        {"symbol": "A", "an_dt": d, "category": "Outcome", "text": "x", "attchmntFile": "-", "seq_id": None, "file_date": d},
        {"symbol": "B", "an_dt": d, "category": "Outcome", "text": "y", "attchmntFile": "-", "seq_id": None, "file_date": d},
        {"symbol": "B", "an_dt": d, "category": "Outcome", "text": "y", "attchmntFile": "-", "seq_id": None, "file_date": d},   # a repeat
        {"symbol": "C", "an_dt": d, "category": "Outcome", "text": "z", "attchmntFile": "-", "seq_id": "7", "file_date": d},
        {"symbol": "C", "an_dt": d, "category": "Outcome", "text": "z2", "attchmntFile": "-", "seq_id": "7", "file_date": d},  # same seq_id
    ])
    out = announce.dedupe(df)
    assert sorted(out["symbol"]) == ["A", "B", "C"]
