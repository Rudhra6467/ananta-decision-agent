"""3 Nov 2026 (flag 63): the data-set audit reads the research years only and says where the data is thin."""
from india import dataaudit


def test_the_audit_finds_the_parse_gap_and_the_announcement_hole(monkeypatch, tmp_path):
    monkeypatch.setattr(dataaudit, "results_parse", lambda: {"by_year": {2019: {"filings": 9000, "companies": 1600, "with_revenue": 10, "with_eps": 12, "companies_with_eps": 5},
                                                                         2022: {"filings": 11000, "companies": 1900, "with_revenue": 7400, "with_eps": 7451, "companies_with_eps": 1500}}})
    monkeypatch.setattr(dataaudit, "universe", lambda: {2023: {"ranked_stocks": 1765, "ever_top250": 362, "ever_top500": 722}})
    monkeypatch.setattr(dataaudit, "xbrl_by_year", lambda: {})
    monkeypatch.setattr(dataaudit.paths, "manifest_dir", lambda: tmp_path)
    (tmp_path / "data_inventory.json").write_text('{"announcements": {"per_year": {"2021": 113496, "2022": 22367, "2023": 131213}}, "datasets": {}}')
    a = dataaudit.build(write=False)
    areas = {f["area"]: f for f in a["findings"]}
    assert "parsed for 2022 only" in areas["company results"]["finding"] and "2019: 12 of 9000" in areas["company results"]["finding"]
    assert "2022: 22,367" in areas["company announcements"]["finding"]
    assert "1,765 stocks" in areas["the research universe"]["finding"]
    assert a["widen_first"][0].startswith("1. Parse the downloaded results")
