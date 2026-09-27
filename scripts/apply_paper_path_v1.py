"""Idempotent hook. Does not replace decision_store.py. Does not touch bar clock."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "intelligence" / "cycle_ingest.py"


def main() -> None:
    text = TARGET.read_text()
    if "paper_path_wire import correct" in text and "correct(run(obs))" in text:
        print("HOOK_ALREADY_PRESENT")
        return
    old = "from src.intelligence.di_loop import run\n"
    new = old + "from src.intelligence.paper_path_wire import correct\n"
    if text.count(old) != 1:
        raise SystemExit("IMPORT_ANCHOR_MISS")
    text = text.replace(old, new, 1)
    if text.count("        out = run(obs)\n") != 1:
        raise SystemExit("RUN_ANCHOR_MISS")
    text = text.replace("        out = run(obs)\n", "        out = correct(run(obs))\n", 1)
    text = text.replace('INGEST_VERSION = "cycle.ingest.v3"', 'INGEST_VERSION = "cycle.ingest.v4"', 1)
    text = text.replace(
        '    print("  paper_take=False keep=False exec=False m2=False G8=NOT_GRANTED")\n',
        '    print("  paper_path=ARMED grant_read=True exec=False m2=False live=False")\n'
        '    print("  fixture fill is not a market trade. family match is not a take.")\n',
        1,
    )
    text = text.replace('"g8": "NOT_GRANTED"', '"g8": "GRANT_READ", "paper_path": "ARMED_AFTER_FIXTURE_PROOF", "grant_read": True', 1)
    TARGET.write_text(text)
    print("HOOK_APPLIED")
    print("decision_store_untouched")


if __name__ == "__main__":
    main()
