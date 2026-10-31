"""india.shadow must import without india.sealed (the India web service seals plans in a venv without duckdb: 30 Oct 2026 the
POST /v3/morning/shadow failed with ModuleNotFoundError), and its stock closes must come through the sealed module's own reader (the
module-level name `sealed` is the plan check, which used to shadow the module so read_shadow was never reached)."""
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_import_does_not_load_sealed_or_duckdb():
    code = "import sys; from india import shadow; print('india.sealed' in sys.modules, 'duckdb' in sys.modules, callable(shadow.sealed))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert out == ["False", "False", "True"]


def test_closes_reaches_the_sealed_reader(monkeypatch, tmp_path):
    from india import paths, sealed, shadow
    seen = {}

    def fake(purpose, since):
        seen["args"] = (purpose, since)
        return pd.DataFrame({"symbol": ["ABC"], "date": ["2026-10-30"], "close": [100.0]})

    monkeypatch.setattr(sealed, "read_shadow", fake)
    monkeypatch.setattr(paths, "manifest_dir", lambda: tmp_path)
    df = shadow._closes()
    assert seen["args"] == ("shadow_score", shadow.SHADOW_START)
    assert list(df["symbol"]) == ["ABC"]
