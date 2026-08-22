"""CLI interactive mode — body restored via base64 chunks."""
from pathlib import Path
import base64
_dir = Path(__file__).resolve().parent / "_cli_chunks"
_parts = [(_dir / f"c{i}.txt").read_text() for i in range(9)]
_code = base64.b64decode("".join(_parts)).decode()
exec(compile(_code, "cli_main_body", "exec"), globals())
