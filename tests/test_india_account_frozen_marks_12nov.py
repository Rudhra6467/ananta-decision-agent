"""12 Nov 2026, the keen outside audit (G-13; open-list flag 118): 'your holdings, as you have them' kept Indian Energy Exchange at its 30 Oct
price because the twin no longer held it and the Zerodha snapshot was current. A holding with no other mark now takes the session's close
from the nightly stock quote book; one with no close on file is named, never silently left at its old price. Made-up numbers only."""
import json

import pytest

from india import account, allocator, sealed


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper" / "account").mkdir(parents=True)
    (tmp_path / "manifests").mkdir(parents=True)
    (tmp_path / "paper" / "account" / "frozen.json").write_text(json.dumps({
        "day": "2026-10-30", "positions": {"IEX": {"qty": 100, "avg": 150.0, "last_at_open": 140.0},
                                           "TATAPOWER": {"qty": 10, "avg": 300.0, "last_at_open": 380.0}},
        "cash_inr": 1000.0, "options_inr": 0.0, "start_inr": 20000.0}))
    monkeypatch.setattr(allocator, "account", lambda: (_ for _ in ()).throw(RuntimeError("no snapshot in a test")))
    monkeypatch.setattr(sealed, "read_index", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no index in a test")))
    return tmp_path


BOOK = {"positions": {"TATAPOWER": {"qty": 10, "last": 390.0}}, "cash_inr": 500.0, "options_inr": 0.0}


def test_a_holding_the_twin_no_longer_holds_takes_the_sessions_close(lake):
    (lake / "manifests" / "quotebook.json").write_text(json.dumps({"as_of": "2026-11-11", "quotes": {"IEX": {"close": 114.05, "as_of": "2026-11-11"}}}))
    v = account.benchmark(dict(BOOK, positions=dict(BOOK["positions"])), {"last_session": "2026-11-11"})
    assert v["frozen_inr"] == round(100 * 114.05 + 10 * 390.0 + 1000.0)                 # before: 100 x 140 (the 30 Oct price)
    assert v["frozen_marked_from_quotebook"] == {"IEX": "2026-11-11"} and v["frozen_stale"] == []
    assert "opening price" not in v["words"]


def test_a_holding_with_no_close_on_file_is_named_not_hidden(lake):
    (lake / "manifests" / "quotebook.json").write_text(json.dumps({"as_of": "2026-11-11", "quotes": {}}))
    v = account.benchmark(dict(BOOK, positions=dict(BOOK["positions"])), {"last_session": "2026-11-11"})
    assert v["frozen_stale"] == ["IEX"] and "stay at their opening price in this line (IEX)" in v["words"]


def test_a_close_newer_than_the_session_is_never_used(lake):
    (lake / "manifests" / "quotebook.json").write_text(json.dumps({"as_of": "2026-11-12", "quotes": {"IEX": {"close": 120.0, "as_of": "2026-11-12"}}}))
    v = account.benchmark(dict(BOOK, positions=dict(BOOK["positions"])), {"last_session": "2026-11-11"})
    assert v["frozen_stale"] == ["IEX"] and v["frozen_marked_from_quotebook"] == {}
