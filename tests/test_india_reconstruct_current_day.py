"""4 Nov 2026: the paper job runs the card before it rebuilds the read model, so the card must not take its day from a read model
that still describes the session before."""
import json

from india import readmodel
from india import reconstruct as rx


def _rm_file(tmp_path, monkeypatch, through):
    data = tmp_path / "india"
    (data / "readmodel").mkdir(parents=True)
    (data / "readmodel" / "latest.json").write_text(json.dumps({"data_through": through}))
    monkeypatch.setattr(rx.paths, "data_dir", lambda: data)
    return data


def test_a_stale_read_model_is_rebuilt_for_the_newest_decision_day(tmp_path, monkeypatch):
    _rm_file(tmp_path, monkeypatch, "2026-11-02")
    monkeypatch.setattr(readmodel, "latest_day", lambda: "2026-11-03")
    built = []
    monkeypatch.setattr(readmodel, "build", lambda d=None: built.append(d) or {"data_through": d})
    assert rx._current_readmodel({"data_through": "2026-11-02"})["data_through"] == "2026-11-03"
    assert built == ["2026-11-03"]


def test_a_current_read_model_is_left_alone(tmp_path, monkeypatch):
    _rm_file(tmp_path, monkeypatch, "2026-11-03")
    monkeypatch.setattr(readmodel, "latest_day", lambda: "2026-11-03")
    monkeypatch.setattr(readmodel, "build", lambda d=None: (_ for _ in ()).throw(AssertionError("must not rebuild")))
    rm = {"data_through": "2026-11-03", "x": 1}
    assert rx._current_readmodel(rm) is rm


def test_a_failed_rebuild_keeps_the_old_read_model(tmp_path, monkeypatch):
    _rm_file(tmp_path, monkeypatch, "2026-11-02")
    monkeypatch.setattr(readmodel, "latest_day", lambda: "2026-11-03")
    monkeypatch.setattr(readmodel, "build", lambda d=None: (_ for _ in ()).throw(RuntimeError("boom")))
    rm = {"data_through": "2026-11-02"}
    assert rx._current_readmodel(rm) is rm


def test_a_named_day_never_rebuilds(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(rx, "_current_readmodel", lambda rm: calls.append(1) or rm)
    _rm_file(tmp_path, monkeypatch, "2026-11-02")
    try:
        rx.build("2026-11-02")
    except Exception:  # noqa: BLE001 - the empty lake cannot build a full card; only the call matters here
        pass
    assert calls == []
