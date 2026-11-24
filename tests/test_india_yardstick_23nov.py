"""23 Nov 2026 (Madhav: "Yes, let's do it"): the nightly yardstick, one line, with the options line in it."""
import json

from india import yardstick


def _setup(tmp_path):
    m = tmp_path / "manifests"
    m.mkdir()
    (m / "others_2026-11-20.json").write_text(json.dumps({"date": "2026-11-20", "status": "ok", "league": {
        "1": {"sessions": 20, "ANANTA": 0.0001, "RANDOM": 0.0003, "ananta_pct_vs_random": 0.48},
        "5": {"sessions": 19, "ANANTA": 0.02, "RANDOM": 0.01, "ananta_pct_vs_random": 0.8}}}))
    (m / "others_2026-11-22.json").write_text(json.dumps({"date": "2026-11-22", "status": "no session (weekend)"}))
    s = tmp_path / "paper" / "sp1"
    s.mkdir(parents=True)
    rows = [{"dir": 1, "index_proxy": {"gross_bps": 100, "cost_bps": 6, "net_bps": 94}, "legs": {"option": {"net_rs_realistic": 5000}}},
            {"dir": -1, "index_proxy": {"gross_bps": -50, "cost_bps": 6, "net_bps": -56}, "legs": {"option": {"net_rs_realistic": -2000}}}]
    (s / "outcomes.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    return tmp_path


def test_weekend_reads_the_last_session_and_the_options_line(tmp_path):
    D = _setup(tmp_path)
    w = yardstick.line("2026-11-22", D)
    assert "Stocks (through 2026-11-20)" in w and "1 day +0.01% vs random +0.03% (worse" in w and "5 days +2.00% vs random +1.00% (better" in w
    o = yardstick.options(D)
    assert o["trades"] == 2 and o["right_side"] == 1
    assert round(o["ananta_bps"]) == 19 and round(o["always_long_bps"]) == 69 and round(o["coin_bps"]) == -6
    assert "Rs 3,000" in w and "Rs -2,000 without its best trade" in w


def test_nothing_yet(tmp_path):
    assert yardstick.line("2026-11-20", tmp_path) == "no yardstick yet for this session"
