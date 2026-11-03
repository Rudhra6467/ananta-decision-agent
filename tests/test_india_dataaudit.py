"""3 Nov 2026 (flag 63): the data-set audit reads the research years only and says where the data is thin."""
from india import dataaudit

PR = '{"announcements": {"per_year": {"2021": 113496, "2022": 22367, "2023": 131213}}, "datasets": {}}'


def _base(monkeypatch, tmp_path, results, api):
    monkeypatch.setattr(dataaudit, "results_parse", lambda: {"by_year": results})
    monkeypatch.setattr(dataaudit, "universe", lambda: {2023: {"ranked_stocks": 1765, "ever_top250": 362, "ever_top500": 722}})
    monkeypatch.setattr(dataaudit, "xbrl_by_year", lambda: {})
    monkeypatch.setattr(dataaudit, "announcements_api", lambda: api)
    monkeypatch.setattr(dataaudit, "board_meetings", lambda: {})
    monkeypatch.setattr(dataaudit.paths, "manifest_dir", lambda: tmp_path)
    (tmp_path / "data_inventory.json").write_text(PR)
    a = dataaudit.build(write=False)
    return a, {f["area"]: f for f in a["findings"]}


def test_the_audit_finds_the_parse_gap_and_the_announcement_hole(monkeypatch, tmp_path):
    res = {2019: {"filings": 9000, "companies": 1600, "with_revenue": 10, "with_eps": 12, "companies_with_eps": 5},
           2022: {"filings": 11000, "companies": 1900, "with_revenue": 7400, "with_eps": 7451, "companies_with_eps": 1500}}
    api = {2021: {"rows": 104307, "with_dissemination_time": 1}, 2022: {"rows": 20000, "with_dissemination_time": 1}, 2023: {"rows": 142709, "with_dissemination_time": 1}}
    a, areas = _base(monkeypatch, tmp_path, res, api)
    assert "parsed for 2022" in areas["company results"]["finding"] and "2019: 12 of 9000" in areas["company results"]["finding"]
    assert "2022: 20,000" in areas["company announcements"]["finding"]          # a hole in the timestamped source: refetch
    assert "1,765 stocks" in areas["the research universe"]["finding"]
    assert a["widen_first"][0].startswith("1. Parse the downloaded results")
    assert a["widen_first"][1].startswith("2. Refetch")


def test_a_hole_only_in_the_old_pr_files_names_the_studies_that_read_them(monkeypatch, tmp_path):
    res = {y: {"filings": 9000, "companies": 1600, "with_revenue": 8900, "with_eps": 8900, "companies_with_eps": 1500} for y in range(2018, 2024)}
    api = {2021: {"rows": 104307, "with_dissemination_time": 1}, 2022: {"rows": 120937, "with_dissemination_time": 1}, 2023: {"rows": 142709, "with_dissemination_time": 1}}
    a, areas = _base(monkeypatch, tmp_path, res, api)
    assert "company announcements" not in areas
    old = areas["company announcements (old PR files)"]
    assert "2022: 22,367" in old["finding"] and "2022: 120,937" in old["finding"] and "V02 and HFN1" in old["finding"]
    assert "new registration" in old["so"]
    assert "earlier years hold the filing" not in areas["company results"]["finding"]
    assert a["widen_first"][0].startswith("1. Done") and a["widen_first"][1].startswith("2. Done")
