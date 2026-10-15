"""The NDAX cost table lives in one file (research audit, Oct 15): ten copies became one, and none may grow back."""
import importlib
import re
from pathlib import Path

import pytest

from src.intelligence import ndax_costs as N

ROOT = Path(__file__).resolve().parents[1]

# The numbers as they stood in every copy before the merge (one NDAX snapshot, 2026-09-29). This is the independent reference:
# if someone edits the shared table, this test says so, and the edit has to be a dated decision, not a drive-by.
FROZEN = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
          "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}

# (module, the name that module used for the table before the merge)
OLD_NAMES = [("src.intelligence.explorer_engine", "HALF_SPREAD"), ("src.research.portfolio_trend", "HALF_SPREAD"),
             ("src.research.intraday_atlas", "HALF_SPREAD"), ("src.research.candidate_v3", "HALF_SPREAD"),
             ("src.research.green_runs", "HALF_SPREAD"), ("src.lake.agent_pack", "MEASURED_HALF_SPREAD"),
             ("src.intelligence.candidate_paper", "HALF_SPREAD"), ("src.intelligence.portfolio_layer", "HALF_SPREAD"),
             ("jarvis.service.manual", "HALF_SPREAD"), ("src.research.study_v3", "NDAX_HS_LAB")]


def test_the_shared_table_is_the_dated_snapshot():
    assert N.HALF_SPREAD == FROZEN
    assert N.NDAX_FEE == 0.0020 and N.DEFAULT_HS == 0.0040 and N.EXPENSIVE_HS == 0.0030
    assert N.SNAPSHOT["taken"] == "2026-09-29" and N.SNAPSHOT["samples"] == 1


def test_no_second_copy_of_the_table_exists():
    """A literal copy anywhere under src/ or jarvis/ (the BTC and ETH entries are the fingerprint) fails the test."""
    me = Path(N.__file__).resolve()
    fingerprint = re.compile(r'"BTC"\s*:\s*0\.00178|"ETH"\s*:\s*0\.00084')
    copies = [str(p.relative_to(ROOT)) for d in ("src", "jarvis") for p in (ROOT / d).rglob("*.py")
              if p.resolve() != me and fingerprint.search(p.read_text(errors="ignore"))]
    assert copies == [], f"a second copy of the NDAX half-spread table: {copies}; import src.intelligence.ndax_costs instead"


@pytest.mark.parametrize("module,name", OLD_NAMES)
def test_every_old_name_reads_the_shared_table(module, name):
    src = (ROOT / (module.replace(".", "/") + ".py")).read_text()
    assert "from src.intelligence.ndax_costs import" in src, f"{module} does not read the shared table"
    try:
        m = importlib.import_module(module)
    except ImportError as e:                       # an optional library (numpy, pandas) is missing in this environment
        pytest.skip(f"{module} not importable here: {e}")
    assert getattr(m, name) is N.HALF_SPREAD and getattr(m, name) == FROZEN


def test_explorer_engine_still_exports_the_cost_names():
    from src.intelligence import explorer_engine as xe

    assert (xe.NDAX_FEE, xe.DEFAULT_HS, xe.EXPENSIVE_HS) == (0.0020, 0.0040, 0.0030)
    assert xe.HALF_SPREAD["BTC"] == 0.00178
