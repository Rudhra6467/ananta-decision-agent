"""The morning records job (Madhav's yes of 10 Nov 2026, flag 75): only allowlisted record files are saved, each by name; never code, never a
pinned file, never a file that names the family; a checkout on the wrong branch or in a merge is left alone."""
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("commit_records", ROOT / "scripts" / "commit_records.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def _repo(tmp: Path, branch: str = "jarvis-4") -> Path:
    d = tmp / "repo"
    d.mkdir()
    g = lambda *a: subprocess.run(["git", *a], cwd=d, check=True, capture_output=True)   # noqa: E731
    g("init", "-q", "-b", branch)
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "t")
    (d / "docs/knowledge").mkdir(parents=True)
    (d / "docs/repair_shop/replay").mkdir(parents=True)
    (d / "docs/knowledge/lock.json").write_text(json.dumps({"pins": {"a": {"files": ["docs/repair_shop/replay/pinned.json"]}}}))
    (d / "docs/repair_shop/replay/latest.json").write_text("{}")
    (d / "docs/repair_shop/replay/pinned.json").write_text("{}")
    g("add", "-A")
    g("commit", "-q", "-m", "start")
    return d


def _c(d: Path, branch: str = "jarvis-4") -> dict:
    return {"name": "t", "dir": d, "branch": branch, "lock": "docs/knowledge/lock.json", "allow": ["docs/repair_shop/replay/*"]}


def test_only_allowlisted_records_are_saved_and_the_rest_is_named(tmp_path, monkeypatch):
    d = _repo(tmp_path)
    (d / "docs/repair_shop/replay/latest.json").write_text('{"night": 1}')
    (d / "docs/repair_shop/replay/2026-11-10.json").write_text('{"new": 1}')
    (d / "docs/repair_shop/replay/pinned.json").write_text('{"changed": 1}')
    (d / "docs/repair_shop/replay/family.json").write_text('{"q": "what do you know about my brother Vamsi Krishna"}')
    (d / "jarvis.py").write_text("print('code')")
    p = C.plan(_c(d))
    assert p["take"] == ["docs/repair_shop/replay/2026-11-10.json", "docs/repair_shop/replay/latest.json"]
    assert set(p["left"]) == {"docs/repair_shop/replay/pinned.json (pinned)", "docs/repair_shop/replay/family.json (names family; kept on the Mac)", "jarvis.py"}
    monkeypatch.setattr(C, "CHECKOUTS", [_c(d)])
    monkeypatch.setattr(C, "git", lambda dd, *a, timeout=120: subprocess.CompletedProcess(a, 1, "", "no remote") if a[:1] == ("push",)
                        else subprocess.run(["git", *a], cwd=dd, capture_output=True, text=True))
    r = C.run()[0]
    assert r["commit"] and r["pushed"] is False and "no remote" in r["push_error"]
    files = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"], cwd=d, capture_output=True, text=True).stdout.split()
    assert sorted(files) == ["docs/repair_shop/replay/2026-11-10.json", "docs/repair_shop/replay/latest.json"]
    assert "No-change-line: generated records only" in subprocess.run(["git", "log", "-1", "--format=%B"], cwd=d, capture_output=True, text=True).stdout
    assert C.plan(_c(d))["take"] == []                                          # once


def test_a_checkout_on_the_wrong_branch_or_in_a_merge_is_left_alone(tmp_path):
    d = _repo(tmp_path, branch="main")
    assert C.plan(_c(d))["skip"] == "on branch main, not jarvis-4"
    d2 = tmp_path / "x"
    d2.mkdir()
    assert C.plan(_c(d2 / "missing"))["skip"] == "the checkout is not there"
    (d / ".git" / "MERGE_HEAD").write_text("abc")
    assert C.plan(_c(d, branch="main"))["skip"] == "a merge or rebase is in progress"


def test_the_real_allowlists_hold_no_code_and_no_pinned_file():
    for c in C.CHECKOUTS:
        for p in c["allow"]:
            assert not p.endswith((".py", ".ts", ".tsx", ".sh", ".plist")) and not p.startswith(("jarvis/", "src/", "scripts/", "tests/")), p
        pins = C.pinned(c)
        assert c["lock"] in pins
