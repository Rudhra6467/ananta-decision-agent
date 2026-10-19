"""The India/crypto firewall test: proves, with evidence, that the crypto agent, the app and their services cannot read India data, and says plainly
where isolation is not yet complete. Gate item: India data enters no shared agent workflow until every check here passes.

  python -m india.firewall          writes manifests/firewall.json and prints PASS/FAIL per check

Checks
  static_scan        every agent/app checkout (not ananta-records) has no reference to the India data folder, the India bucket, the India catalog,
                     the records worktree or the india package; the only India-named code allowed there is src/india/kite_auth.py (the sign-in page)
  kite_auth_scope    that sign-in module only calls Kite's login and session endpoints (no account, order, holdings or market-data call)
  git_branches       the India code lives only on branch `records`; `main` and the agent branches carry nothing India except kite_auth.py
  runtime_open_files no running agent or app process has any file open under the India data folder
  runtime_env        no running agent or app process has INDIA_DATA_DIR or the India bucket in its environment
  canary             a tripwire token is planted in the India data; it must not appear in any agent/app log, database or output file
  r2_credentials     the India backup must not share credentials with the crypto agent (a key that can read both buckets is a FAIL until a
                     bucket-scoped key exists)
Nothing here changes the agent; it only reads.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

from india import paths

HOME = Path.home()
AGENT_DIRS = [HOME / "code" / d for d in ("ananta-decision-agent", "ananta-agent-research", "ananta-a6", "ananta-guard", "Ananta", "Ananta-relabel", "Ananta-replay")]
TEXT_EXT = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".sh", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".md"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".expo", "dist", "build", ".next"}
PATTERNS = [r"ananta_data/india", r"INDIA_DATA_DIR", r"ananta-india-lake", r"india\.duckdb", r"ananta-records", r"from india\b", r"import india\b",
            r"bronze/ledger", r"sealed/silver"]
ALLOWED_FILES = {"src/india/kite_auth.py", "src/india/__init__.py"}
CANARY_FILE = paths.manifest_dir() / "firewall_canary.txt"


def _walk(base: Path):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield Path(root) / f


def check_static() -> tuple[bool, str, dict]:
    hits = []
    n = 0
    for base in AGENT_DIRS:
        if not base.exists():
            continue
        for p in _walk(base):
            if p.suffix not in TEXT_EXT or p.stat().st_size > 2_000_000:
                continue
            rel = str(p.relative_to(base))
            if rel in ALLOWED_FILES or rel.startswith("docs/"):
                continue  # docs describe the plan in words; code and config are what can read data
            n += 1
            try:
                txt = p.read_text(errors="ignore")
            except Exception:
                continue
            for pat in PATTERNS:
                for m in re.finditer(pat, txt):
                    line = txt.count("\n", 0, m.start()) + 1
                    hits.append(f"{base.name}/{rel}:{line} [{pat}]")
    return (not hits), f"{n} code/config files scanned in {sum(b.exists() for b in AGENT_DIRS)} checkouts: {len(hits)} references", {"hits": hits[:50]}


def check_kite_auth() -> tuple[bool, str, dict]:
    calls = {}
    for base in AGENT_DIRS:
        p = base / "src/india/kite_auth.py"
        if p.exists():
            txt = p.read_text()
            urls = sorted(set(re.findall(r"https?://[^\s\"']+", txt)) | set(re.findall(r"[\"'](/[a-z_/{}]+)[\"']", txt)))
            calls[base.name] = urls
    bad = {k: [u for u in v if not re.search(r"connect/login|session/token|kite\.zerodha\.com/connect|api\.kite\.trade/?$|127\.0\.0\.1|localhost", u) and u.startswith(("http", "/"))]
           for k, v in calls.items()}
    bad = {k: v for k, v in bad.items() if v}
    return (not bad), (f"kite_auth.py found in {len(calls)} checkouts; endpoints outside login/session: {bad or 'none'}"), {"endpoints": calls}


def check_git() -> tuple[bool, str, dict]:
    repo = HOME / "code" / "ananta-decision-agent"
    out = {}
    bad = []
    branches = subprocess.run(["git", "-C", str(repo), "for-each-ref", "--format=%(refname:short)", "refs/heads"], capture_output=True, text=True).stdout.split()
    for b in branches:
        files = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", "--name-only", b], capture_output=True, text=True).stdout.splitlines()
        india = [f for f in files if f.startswith("india/")]
        out[b] = len(india)
        if b != "records" and india:
            bad.append(f"{b}: {len(india)} files under india/")
    return (not bad), f"India package files per branch {out}; only `records` may carry them" + (f"; FAIL {bad}" if bad else ""), {"per_branch": out}


def _agent_pids() -> dict[int, str]:
    ps = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout.splitlines()
    out = {}
    for line in ps:
        pid, _, cmd = line.strip().partition(" ")
        if "india." in cmd or "ananta-records" in cmd or "desktop-commander" in cmd:
            continue  # the India jobs themselves
        if any(k in cmd for k in ("jarvis", "ananta-decision-agent", "ananta-agent-research", "explorer_live", "uvicorn", "Ananta/backend", "web_site.py", "telugu_server")):
            out[int(pid)] = cmd[:120]
    return out


def check_open_files() -> tuple[bool, str, dict]:
    pids = _agent_pids()
    india = str(paths.data_dir())
    hits = []
    for pid, cmd in pids.items():
        r = subprocess.run(["lsof", "-p", str(pid), "-Fn"], capture_output=True, text=True).stdout
        for line in r.splitlines():
            if line.startswith("n") and india in line:
                hits.append(f"{pid} {cmd[:60]}: {line[1:]}")
    return (not hits), f"{len(pids)} agent/app processes inspected; {len(hits)} open files under the India data folder", {"processes": pids, "hits": hits}


def check_env() -> tuple[bool, str, dict]:
    pids = _agent_pids()
    hits = []
    for pid, cmd in pids.items():
        r = subprocess.run(["ps", "eww", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout
        for key in ("INDIA_DATA_DIR", "ananta-india-lake", "ananta_data/india"):
            if key in r:
                hits.append(f"{pid}: {key}")
    return (not hits), f"{len(pids)} processes: {len(hits)} with India settings in their environment", {"hits": hits}


def plant_canary() -> str:
    if CANARY_FILE.exists():
        return CANARY_FILE.read_text().split()[0]
    tok = "ANANTA-INDIA-CANARY-" + secrets.token_hex(8)
    CANARY_FILE.write_text(tok + "\nplanted " + dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds") + "; this token must never appear outside the India data folder\n")
    # also inside the data the agent would most likely touch: the catalog and the paper folder
    (paths.data_dir() / "paper" / "firewall_canary.txt").write_text(tok + "\n")
    return tok


def check_canary(places: list | None = None) -> tuple[bool, str, dict]:
    tok = plant_canary().encode()
    places = places or [HOME / "ananta_runs"] + AGENT_DIRS + [HOME / d for d in ("ananta_lake", "ananta_private") if (HOME / d).exists()]
    hits, scanned = [], 0
    for base in places:
        if not base.exists():
            continue
        for p in _walk(base):
            name = p.name.lower()
            if base.name == "ananta_runs" and (name.startswith(("india", "firewall")) or p.suffix == ".py" or "replay" in name):
                continue  # the India jobs' own logs
            try:
                if p.stat().st_size > 200_000_000:
                    continue
                scanned += 1
                with open(p, "rb") as fh:
                    if tok in fh.read():
                        hits.append(str(p))
            except Exception:
                continue
    return (not hits), f"canary {tok.decode()[:28]}...: {scanned} agent/app files scanned, found in {len(hits)}", {"hits": hits}


def check_r2() -> tuple[bool, str, dict]:
    from india import r2sync
    shared = r2sync.ENV == HOME / "code/ananta-decision-agent/.env"
    agent_buckets = set()
    env = r2sync._env() if r2sync.ENV.exists() else {}
    for k, v in env.items():
        if "BUCKET" in k:
            agent_buckets.add(v)
    ok = not shared
    if not shared:  # own key present: prove it opens the India bucket and is refused on the crypto agent's bucket
        c = r2sync.client()
        try:
            c.head_bucket(Bucket=r2sync.BUCKET)
            own_ok = True
        except Exception:
            own_ok = False
        try:
            c.list_objects_v2(Bucket="ananta-lake", MaxKeys=1)
            other_refused = False
        except Exception:
            other_refused = True
        ok = own_ok and other_refused
        return ok, f"India key {r2sync.ENV}: opens {r2sync.BUCKET} {own_ok}; refused on ananta-lake {other_refused}", {"env_file": str(r2sync.ENV)}
    note = (("India backup reads its R2 key from the crypto agent's .env: the same account key can reach both buckets "
             f"(agent buckets named in that file: {sorted(agent_buckets)}; India bucket {r2sync.BUCKET}). Needs a key scoped to {r2sync.BUCKET} only, "
             "kept in ~/ananta_private, created by Madhav in the Cloudflare dashboard")
            if shared else f"India backup uses its own key file {r2sync.ENV}")
    return ok, note, {"env_file": str(r2sync.ENV)}


def check_token_surface() -> tuple[bool, str, dict]:
    """The one thing the agent side and India share on purpose: Jarvis's /kite/callback writes ~/ananta_private/kite_token.json, India's
    GET-only kite.py reads it. Agent code may touch the token file only through kite_auth.py, and nothing may hand the token out."""
    users, leaks = [], []
    for base in AGENT_DIRS:
        for sub in ("src", "jarvis", "backend", "app", "scripts"):
            d = base / sub
            if not d.exists():
                continue
            for p in _walk(d):
                if p.suffix != ".py":
                    continue
                txt = p.read_text(errors="ignore")
                rel = f"{base.name}/{p.relative_to(base)}"
                if re.search(r"kite_token|kite\.env|ananta_private[\"'/ ,)]*kite|kite_auth\.TOKEN_FILE", txt) and not rel.endswith("src/india/kite_auth.py"):
                    users.append(rel)
                if (re.search(r"kite", txt, re.I) and re.search(r"return[^\n]*access_token|\"access_token\"\s*:\s*t\[", txt)
                        and not rel.endswith("kite_auth.py")):  # the app's own login cookie is also called access_token; only Kite-touching code counts
                    leaks.append(rel)
    st = subprocess.run([sys.executable, "-c", "import inspect,re,sys;sys.path.insert(0,'%s');from src.india import kite_auth as k;"
                         "s=inspect.getsource(k.status);print('access_token' in s.split('return',1)[1])" % (HOME / "code/ananta-decision-agent")],
                        capture_output=True, text=True).stdout.strip()
    ok = not users and not leaks and st == "False"
    return ok, (f"token file touched outside kite_auth.py by {users or 'nothing'}; token returned by {leaks or 'nothing'}; status() hides the token: {st == 'False'}. "
                "Residual: Jarvis and India run as the same macOS user, so the boundary is code plus observation, not an OS permission"), {}


def selftest() -> tuple[bool, str, dict]:
    """Positive controls: each detector must fire on a planted violation, otherwise a 0 above proves nothing."""
    import tempfile
    global AGENT_DIRS
    saved = AGENT_DIRS
    tok = plant_canary()
    with tempfile.TemporaryDirectory() as td:
        b = Path(td) / "fake-agent"
        (b / "src").mkdir(parents=True)
        (b / "src/leak.py").write_text("import duckdb\ncon = duckdb.connect('~/ananta_data/india/india.duckdb')\n")
        (b / "logs.txt").write_text("echo " + tok + "\n")
        (b / "src/tok.py").write_text("TOKEN_FILE='kite_token.json'\n")
        AGENT_DIRS = [b]
        try:
            s = check_static()[0] is False
            c = check_canary([b])[0] is False
            t = check_token_surface()[0] is False
        finally:
            AGENT_DIRS = saved
    ok = s and c and t
    return ok, f"planted violations caught: static {s}, canary {c}, token {t}", {}


CHECKS = {"selftest": selftest, "token_surface": check_token_surface, "static_scan": check_static, "kite_auth_scope": check_kite_auth, "git_branches": check_git, "runtime_open_files": check_open_files,
          "runtime_env": check_env, "canary": check_canary, "r2_credentials": check_r2}


def run() -> dict:
    paths.ensure()
    out = {}
    for k, f in CHECKS.items():
        try:
            ok, note, extra = f()
        except Exception as e:
            ok, note, extra = False, f"error {type(e).__name__}: {e}", {}
        out[k] = {"ok": bool(ok), "note": note, **extra}
        print(("PASS " if ok else "FAIL ") + k + " — " + note, flush=True)
    out["_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "firewall.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    r = run()
    sys.exit(0 if all(v["ok"] for k, v in r.items() if not k.startswith("_")) else 1)
