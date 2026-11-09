"""25 Oct audit: the firewall's allowlist names each India-app reference by file and pattern; anything else still fails, and order endpoints
built on a base constant are now seen by the sign-in scope check."""
from pathlib import Path

from india import firewall


def _agent(tmp_path: Path) -> Path:
    b = tmp_path / "ananta-agent-research"
    (b / "jarvis" / "india").mkdir(parents=True)
    (b / "src" / "india").mkdir(parents=True)
    return b


def test_allowlisted_reference_passes_and_a_new_one_fails(tmp_path, monkeypatch):
    b = _agent(tmp_path)
    (b / "jarvis/india/views.py").write_text('DATA = "~/ananta_data/india"\n')
    monkeypatch.setattr(firewall, "AGENT_DIRS", [b])
    ok, note, extra = firewall.check_static()
    assert ok and len(extra["allowed"]) == 1
    (b / "jarvis/india/views.py").write_text('DATA = "~/ananta_data/india"\nimport duckdb; duckdb.connect("india.duckdb")\n')   # a new pattern in an allowed file
    assert firewall.check_static()[0] is False
    (b / "jarvis/other.py").write_text('p = "~/ananta_data/india/silver"\n')                                                      # any other file
    (b / "jarvis/india/views.py").write_text('DATA = "~/ananta_data/india"\n')
    assert firewall.check_static()[0] is False


def test_order_endpoint_on_a_base_constant_is_caught(tmp_path, monkeypatch):
    b = _agent(tmp_path)
    ka = b / "src/india/kite_auth.py"
    ka.write_text('KITE_WEB = "https://kite.zerodha.com"\nu = f"{KITE_WEB}/api/login"\nv = f"{KITE_WEB}/api/twofa"\n')
    monkeypatch.setattr(firewall, "AGENT_DIRS", [b])
    assert firewall.check_kite_auth()[0]
    ka.write_text(ka.read_text() + 'w = f"{KITE_WEB}/oms/orders/regular"\n')
    ok, note, _ = firewall.check_kite_auth()
    assert not ok and "oms/orders" in note


def test_preopen_read_is_named_with_its_reason():
    """6 Nov morning review: jarvis/india/preopen.py (5 Nov) shipped without its allowlist line and the static scan failed on it."""
    reason = firewall.ALLOWED_REFS[("jarvis/india/preopen.py", r"ananta_data/india")]
    assert "paper/preopen" in reason
    assert ("jarvis/selfknow.py", r"ananta_data/india") not in firewall.ALLOWED_REFS   # outside the India app: Madhav's call, not allowed here


def test_askwords_is_named_and_selfcheck_is_not():
    """9 Nov morning review: jarvis/india/askwords.py (8 Nov) shipped without its allowlist line; selfcheck.py's India path moved into
    jarvis/india/selfparts.py instead of being allowed (a file outside the India app is Madhav's call)."""
    reason = firewall.ALLOWED_REFS[("jarvis/india/askwords.py", r"ananta_data/india")]
    assert "quotebook_names" in reason and "read-only" in reason
    assert ("jarvis/selfcheck.py", r"ananta_data/india") not in firewall.ALLOWED_REFS
