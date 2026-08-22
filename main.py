"""Ananta Agent CLI.

If this file was truncated by a bad push, recover from a known-good commit once,
then keep local Stage 1 modules (lab_watch / market_truth / observation_log).
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parent
_MARKER = _ROOT / ".main_recovered"
_GOOD = "884d13fa4e25a010c3f83f92a8cc51c53fb66e76"


def _ensure_full_main() -> None:
    """One-time restore of interactive main from a known-good commit."""
    if _MARKER.exists():
        return
    text = pathlib.Path(__file__).read_text(encoding="utf-8", errors="replace")
    if "def interactive_mode" in text and "def run_once" in text:
        _MARKER.write_text(_GOOD)
        return
    print("Recovering main.py interactive body from known-good commit...")
    try:
        subprocess.check_call(
            ["git", "show", f"{_GOOD}:main.py"],
            cwd=str(_ROOT),
            stdout=open(__file__, "w", encoding="utf-8"),
        )
        _MARKER.write_text(_GOOD)
        print("Recovered. Re-run: python main.py")
        sys.exit(0)
    except Exception as e:
        print(f"Auto-recover failed ({e}). On your laptop run:")
        print(f"  cd ~/code/ananta-decision-agent")
        print(f"  git show {_GOOD}:main.py > main.py")
        print(f"  git checkout main -- src/lab_cli.py src/lab_watch.py src/tools/market_truth.py src/tools/observation_log.py")
        print(f"  python main.py")
        sys.exit(1)


_ensure_full_main()

# After recovery the file is replaced; imports below run only when full body is present.
from src.graph import agent_graph  # noqa: E402
from src.memory import get_last_user_profile  # noqa: E402

# Prefer importing interactive from recovered path — if still thin, exit above.
import runpy

if __name__ == "__main__":
    # Full interactive is restored into this file on first run when git history is available.
    # If still not present, recover instructions already printed.
    ns = runpy.run_path(str(pathlib.Path(__file__).resolve()), run_name="not_main")
    if "interactive_mode" in ns:
        ns["interactive_mode"]()
    else:
        print("main.py is incomplete. Run the recovery commands printed above.")
