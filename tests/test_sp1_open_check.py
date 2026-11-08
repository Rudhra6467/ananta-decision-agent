"""The SP1 open check (board #149, 8 Nov 2026): the live 09:15 open and the replay's open side by side, read-only."""
import datetime as dt

from india import sp1nightly


def _row(index, point, prev_close, open_, gap):
    return {"kind": "decision", "index": index, "point": point,
            "state": {"prev_close": prev_close, "open": open_, "gap": gap}}


def test_open_check_lists_both_opens_and_the_gap_between_them():
    led = [_row("BANKNIFTY", "D0", 57773.65, 57545.7, -0.003945570342188898),
           _row("NIFTY", "D0", 24536.6, 24600.0, 0.002583),
           _row("NIFTY", "D1", 24536.6, 24600.0, 0.002583),
           {"kind": "plan"}]
    rep = {"state_differences": [{"what": "BANKNIFTY D0", "diff": {"gap": [-0.003945570342188898, 0.0007]}},
                                 {"what": "NIFTY D1", "diff": {"or15_atr": [0.1, 0.2]}}]}
    rows = sp1nightly.open_check(dt.date(2026, 11, 6), led, rep)
    assert [r["index"] for r in rows] == ["BANKNIFTY", "NIFTY"]          # D0 rows only, one per index
    bn, nf = rows
    assert bn["agree"] is False and bn["replay_gap"] == 0.0007
    assert bn["replay_open"] == round(57773.65 * 1.0007, 2)
    assert bn["points_apart"] == round(bn["replay_open"] - 57545.7, 2) and bn["points_apart"] > 250
    assert nf["agree"] is True and nf["replay_gap"] == nf["live_gap"]  # an unlisted gap means the two agree


def test_open_check_survives_missing_numbers():
    rows = sp1nightly.open_check(dt.date(2026, 11, 9), [{"kind": "decision", "index": "NIFTY", "point": "D0", "state": {}}], {})
    assert rows[0]["replay_open"] is None and rows[0]["points_apart"] is None and rows[0]["agree"] is False
