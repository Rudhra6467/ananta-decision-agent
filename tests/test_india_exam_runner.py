"""The India exam runner (scripts/run_india_exam.py): asks through the India Ask in its own thread folder, judges with the records
repo's india/exam.py, runs weekly from the evening job."""
import datetime as dt
import importlib.util
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_india_exam", ROOT / "scripts" / "run_india_exam.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

pytestmark = pytest.mark.skipif(not (R.RECORDS / "india" / "exam.py").exists(), reason="records checkout not on this machine")


def test_run_uses_its_own_thread_folder_and_saves(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    from jarvis.india import views
    monkeypatch.setattr(views, "readmodel", lambda: {"built_at": "x", "data_through": "2026-10-23"})
    asked = []
    fake = types.SimpleNamespace(DATA=tmp_path, ASK_DIR=tmp_path / "ask", MODEL="m",
                                 facts=lambda owner=True: {"market": {"nifty_close": 22600.0}},
                                 ask=lambda who, q, thread=None: asked.append((who, q, thread)) or {"answer": "I don't know, sir."})
    ex = R.judges()
    out = R.run(ex, ask_mod=fake)
    assert fake.ASK_DIR == tmp_path / "ask_exam" and len(asked) == 39 and all(w == "owner" for w, _, _ in asked)
    assert len({t for _, _, t in asked}) == 39                       # a fresh thread for every question
    assert (tmp_path / "manifests" / "exam_latest.json").exists() and out["unknown"] == 7 and not out["exam_pass"]
    assert not R.due(ex) and R.due(ex, now=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7))
