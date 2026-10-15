"""Give the worker Mac its outside alert (Madhav's yes, Oct 15): the ntfy server and topic the main Mac already uses for phone
notes, written to ~/ananta_worker/alert.json on the worker (mode 600) over SSH. The topic is never printed or logged here.

    python3 ~/ananta_runs/svc_env_run.py 'exec(open("scripts/worker_alert_setup.py").read())'            write it
    ... with ANANTA_WORKER_ALERT_TEST=1 in the environment                                              also send one test note
Run from the service's environment (svc_env_run.py), so ANANTA_NTFY_TOPIC comes from the .env without anyone typing it.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
from src.intelligence.paper_watch import NTFY_SERVER, _ntfy_topic  # noqa: E402

HOST = os.getenv("ANANTA_WORKER_HOST", "ananta-worker")
topic = _ntfy_topic()
if not topic:
    raise SystemExit("no ANANTA_NTFY_TOPIC in this environment: nothing written")
cfg = json.dumps({"server": os.getenv("ANANTA_NTFY_SERVER", NTFY_SERVER), "topic": topic})
w = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST, "umask 077; cat > ~/ananta_worker/alert.json"],
                   input=cfg, text=True, capture_output=True, timeout=30)
print("alert.json written on the worker" if w.returncode == 0 else f"failed to write: {w.stderr.strip()[:120]}")
if w.returncode == 0 and os.getenv("ANANTA_WORKER_ALERT_TEST") == "1":
    code = ("import sys; sys.path.insert(0, '/Users/' + __import__('getpass').getuser() + '/ananta_worker'); import collector as c; "
            "print(c.alert('Ananta: worker alert test', 'The worker Mac can now tell you when the main Mac or the site has been down for "
            "10 minutes. Nothing to do.'))")
    py = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, "cat ~/ananta_worker/status"], capture_output=True, text=True, timeout=20).stdout
    exe = py.split("exec ", 1)[1].split(" ", 1)[0] if "exec " in py else "python3"
    t = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, f"{exe} -c {json.dumps(code)}"], capture_output=True, text=True, timeout=60)
    print("test note:", (t.stdout or t.stderr).strip()[-60:])
