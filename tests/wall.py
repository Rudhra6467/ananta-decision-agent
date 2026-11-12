"""The tests' wall. tests/conftest.py puts it up before any of Ananta's modules is imported.

12 Nov 2026, the keen outside audit (G-57: "test isolation is a list of nine past leaks, not a wall"). The first wall, that morning,
moved the tests' home folder and patched Python's socket class. The outside check that followed got through it four ways: a full path to
the live database and the .env file, the C-level socket, a UDP datagram, and a `curl` started from a test. This wall sits on Python's
audit hooks, which see each of those inside the interpreter whatever library or full path asks; a hook cannot be taken off once it is on.
The second outside check, the same morning, read four more ways through the second version (a name opened relative to an open folder, a
network tool started through a wrapper such as nice, a non-Python program writing under the home, a Python started without the wall) and
two small ones (a port list without 8210 and 8081, and a database name that only contained "mode=ro"). This third version closes them.
In a process with the wall:

  files     nothing under Madhav's private places is opened, listed, read or written, even by its full path or by a name relative to an
            open folder (DENIED below); no file named *.env under his home is read; and nothing under his home is written, renamed,
            removed or made, except Python's own __pycache__ files. The tests' own home and their temporary folders are not under his
            home, so they are untouched.
  network   no connection, datagram or name lookup leaves this machine, and none reaches the live services' ports on it.
  programs  no program that reaches the network or controls the services is started (curl, wget, ssh, git fetch, launchctl ...), also
            through a wrapper (nice, caffeinate, timeout, env, a shell's -c ...); the usual programs that write files (cp, mv, rm, touch,
            mkdir, ln, tee, sqlite3, sed -i, dd, tar, unzip ...) and a shell's > and >> are refused when what they would write is under
            his home; and every Python a test starts puts up the same wall first (SITECUSTOMIZE, written into the tests' home, first on
            PYTHONPATH), so a Python started with -I, -S or -E, or with an environment that leaves the wall out, is refused.

What it does not stop, and only an operating-system sandbox would: a program other than Python that reaches the network or writes files
by itself and is not on the lists here (a script file run by a shell, node, a compiled tool), since the wall sees how it is started and
not what it does; and native code that opens files or sockets itself, without Python's own calls (pyarrow, duckdb, SQLite's ATTACH,
ctypes). Those still find the tests' own home wherever they work a path out from the home folder, but a full path written into them is
not seen. None of today's tests does any of this (12 Nov: the one module that named a live file by its full path, jarvis/india/ask.py's
ENV_FILE, is pointed at the tests' home by conftest).

Each refusal is raised as the error the caller already handles (PermissionError for files and programs, ConnectionRefusedError and
socket.gaierror for the network), with "the tests' wall" in its words, and is noted in REFUSED; tests/conftest.py prints that list at
the end of the run, so a test whose code swallows the error still shows up. If the wall's own check fails on an event, the call goes on
(a fault in the wall never breaks a run) and the failure is noted in REFUSED too, so it is seen. A refused path is shown only to its first
folders.
"""
from __future__ import annotations

import os
import re
import shlex
import socket
import sys
import threading

DENIED = ("ananta_data", "ananta_runs", "ananta_private", "ananta_backups", ".ananta", ".appstore", "code/ananta-decision-agent",
          "Library")
# the services running on the Mac, and two that run only at times: 8210 (the Telugu voice) and 8081 (the app's development server)
LIVE_PORTS = frozenset({8001, 8081, 8100, 8110, 8199, 8200, 8210, 8215, 8300, 8301, 8302, 8399, 11434, 20241})
TOOLS = frozenset({"curl", "wget", "ssh", "scp", "sftp", "rsync", "nc", "ncat", "netcat", "socat", "telnet", "ftp", "nscurl", "ping", "ping6",
                   "dig", "nslookup", "host", "traceroute", "whois", "aria2c", "http", "https", "httpie", "ntfy", "networkQuality", "mail",
                   "sendmail", "ssh-keyscan", "launchctl", "osascript", "open", "security", "networksetup", "scutil"})
GIT_NET = frozenset({"clone", "fetch", "pull", "push", "ls-remote", "submodule", "send-email", "request-pull"})
WRAPPERS = frozenset({"env", "xargs", "nohup", "time", "exec", "command", "builtin", "nice", "caffeinate", "arch", "xcrun", "sudo", "doas",
                      "timeout", "gtimeout", "stdbuf", "script", "taskpolicy", "unbuffer", "chronic", "flock", "watch", "setsid", "ionice",
                      "chrt"})
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "fish", "csh", "tcsh"})
WRITE_ALL = frozenset({"rm", "rmdir", "unlink", "mv", "touch", "mkdir", "tee", "shred", "srm", "gzip", "gunzip", "bzip2", "bunzip2", "xz",
                       "unxz", "zstd"})
WRITE_LAST = frozenset({"cp", "ln", "ditto", "install"})              # the last name is written; the others are only read
WRITE_AFTER_FIRST = frozenset({"chmod", "chown", "chgrp", "chflags"})  # the first word is a mode or an owner, the rest are written
PYTHON = re.compile(r"^python(\d+(\.\d+)*)?w?$")
LOCAL = frozenset({"", "localhost", "127.0.0.1", "::1", "0.0.0.0", "::", "ip6-localhost"})
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

SITECUSTOMIZE = '''# Written by tests/conftest.py: every Python a test starts puts up the tests' wall first (tests/wall.py).
import importlib.util as _u
_s = _u.spec_from_file_location("ananta_tests_wall", {wall!r})
_m = _u.module_from_spec(_s)
_s.loader.exec_module(_m)
_m.install({home!r}, readable={readable!r}, never={never!r})
'''

WATCHED = frozenset({"open", "sqlite3.connect", "os.listdir", "os.scandir", "os.remove", "os.rmdir", "shutil.rmtree", "os.mkdir", "os.chmod",
                     "os.chown", "os.truncate", "os.rename", "os.link", "os.symlink", "socket.connect", "socket.sendto", "socket.sendmsg",
                     "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.gethostbyname_ex", "subprocess.Popen",
                     "os.system", "os.posix_spawn", "os.exec", "os.spawn"})

REFUSED: list[str] = []
_state: dict = {"on": False, "home": "", "denied": (), "readable": (), "never": (), "names": frozenset(), "site": ""}
_busy = threading.local()


def _fd_path(fd: int) -> str | None:
    """The folder an open file number stands for (shutil.rmtree and pytest's own clean-up name files relative to one)."""
    try:
        if sys.platform == "darwin":
            import fcntl
            return os.fsdecode(fcntl.fcntl(fd, getattr(fcntl, "F_GETPATH", 50), b"\0" * 1024)).split("\0", 1)[0] or None
        return os.readlink(f"/proc/self/fd/{fd}")
    except (OSError, ValueError, TypeError):
        return None


def _path(p, dir_fd=None, cwd=None) -> str | None:
    """A real, absolute path for what an event names, or None (a file number, an in-memory database, nothing, or a name relative to a
    folder number that cannot be read back). cwd: the folder a program was started in, for the names it is given."""
    if p is None or isinstance(p, int):
        return None
    try:
        s = os.fsdecode(os.fspath(p))
    except TypeError:
        return None
    if "\0" in s:
        return None
    if isinstance(dir_fd, int) and not os.path.isabs(s):
        base = _fd_path(dir_fd)
        if not base:
            return None
        s = os.path.join(base, s)
    if s.startswith("file:"):                                   # an SQLite URI
        s = s[5:].split("?", 1)[0]
        if s.startswith("//"):
            s = s[2:]
    if not s or s == ":memory:":
        return None
    if cwd is not None and not os.path.isabs(s):
        try:
            s = os.path.join(os.fsdecode(os.fspath(cwd)), s)
        except TypeError:
            pass
    return os.path.realpath(os.path.abspath(s))


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + os.sep)


def _shown(path: str, full: bool = False) -> str:
    """With full (a code checkout, which has no private names) the whole path; otherwise at most two folders under the home, then '...':
    a private file's own name (a guest's book was once named after an email) is never shown."""
    rel = os.path.relpath(path, _state["home"])
    if full:
        return "~/" + rel
    parts = rel.split(os.sep)
    return "~/" + "/".join(parts[:2]) + ("/..." if len(parts) > 2 else "")


def _file(path: str, write: bool):
    home = _state["home"]
    if not _under(path, home):
        return None
    if any(_under(path, r) for r in _state["never"]):
        return ("opening a sealed or private place", _shown(path), PermissionError)
    if any(_under(path, r) for r in _state["denied"]) and (write or not any(_under(path, r) for r in _state["readable"])):
        return ("reading or writing Madhav's private files", _shown(path), PermissionError)
    if write and "__pycache__" not in path.split(os.sep):
        code = _under(path, os.path.join(home, "code"))                 # the private checkout under code/ was refused above
        return ("writing under Madhav's home", _shown(path, full=code), PermissionError)
    if not write and os.path.basename(path).endswith(".env"):
        return ("reading a .env file", _shown(path), PermissionError)
    return None


def _sqlite_read_only(name) -> bool:
    """Only an SQLite URI whose own query says mode=ro (or immutable=1) opens a database read-only; a file name that merely contains the
    words does not (12 Nov, the second outside check)."""
    if not isinstance(name, str) or not name.startswith("file:") or "?" not in name:
        return False
    from urllib.parse import parse_qs
    q = parse_qs(name.split("?", 1)[1].split("#", 1)[0])
    return q.get("mode", [""])[-1] == "ro" or q.get("immutable", [""])[-1] == "1"


def _is_ip(host) -> bool:
    import ipaddress
    try:
        ipaddress.ip_address((host.decode() if isinstance(host, (bytes, bytearray)) else str(host)).strip("[]").split("%")[0])
        return True
    except ValueError:
        return False


def _host_ok(host) -> bool:
    h = (host.decode() if isinstance(host, (bytes, bytearray)) else str(host if host is not None else "")).lower().strip("[]")
    if h.startswith("::ffff:"):
        h = h[7:]
    return h in LOCAL or h.startswith("127.") or h in _state["names"]


def _address(address):
    if isinstance(address, (str, bytes)):                        # a Unix socket: a file on this machine
        p = _path(address)
        return _file(p, write=False) if p else None
    if isinstance(address, tuple) and len(address) >= 2:
        host, port = address[0], address[1]
        if not _host_ok(host) or (isinstance(port, int) and port in LIVE_PORTS):
            return ("reaching the network", f"{host}:{port}", ConnectionRefusedError)
    return None


# ---- programs a test starts ------------------------------------------------------------------------------------------------------------

def _words(argv) -> list[str]:
    if isinstance(argv, (str, bytes)):
        argv = [argv]
    return [os.fsdecode(a) if isinstance(a, (bytes, str)) else str(a) for a in (argv or [])]


def _getenv(env, key: str) -> str:
    if env is None:
        return os.environ.get(key, "")
    try:
        v = env.get(key) if key in env else env.get(key.encode())
    except (AttributeError, TypeError):
        return ""
    return os.fsdecode(v) if isinstance(v, (bytes, str)) else ""


def _segments(text: str, env) -> list[list[str]]:
    """The commands in a shell's -c string, split at ; & | ( ) ` and new lines, with ~ read as the shell would (the HOME it is given)."""
    home = _getenv(env, "HOME")
    out = []
    for part in re.split(r"[;&|()`\n]|\$\(", text):
        try:
            words = shlex.split(part, comments=True)
        except ValueError:
            words = part.split()
        if home:
            words = [home + w[1:] if w == "~" or w.startswith("~/") else w for w in words]
        if words:
            out.append(words)
    return out


def _writes(words: list[str], cwd):
    """For one program the wall knows writes files: the first name it would write under Madhav's home (or read from a private place)."""
    prog, args = os.path.basename(words[0]), words[1:]
    reads: list[str] = []
    writes: list[str] = []
    names = [a for a in args if not a.startswith("-")]
    if prog in WRITE_ALL:
        writes = names
    elif prog in WRITE_LAST and names:
        reads, writes = names[:-1], names[-1:]
    elif prog in WRITE_AFTER_FIRST:
        writes = names[1:]
    elif prog == "truncate":
        writes = [a for i, a in enumerate(args) if not a.startswith("-") and not (i and args[i - 1] == "-s")]
    elif prog == "sqlite3":
        db = names[:1]
        if db and not ("-readonly" in args or _sqlite_read_only(db[0])):
            writes = db
        else:
            reads = db
    elif prog in ("sed", "gsed") and any(a.startswith("-i") or a.startswith("--in-place") for a in args):
        scripts = {i + 1 for i, a in enumerate(args) if a in ("-e", "-f", "--expression", "--file")}
        suffix = {i + 1 for i, a in enumerate(args) if a == "-i" and prog == "sed"}     # macOS sed: -i takes the backup suffix next ('' too)
        files = [a for i, a in enumerate(args) if not a.startswith("-") and i not in scripts | suffix]
        writes = files if scripts else files[1:]
    elif prog == "dd":
        writes = [a[3:] for a in args if a.startswith("of=")]
        reads = [a[3:] for a in args if a.startswith("if=")]
    elif prog in ("tar", "bsdtar", "gtar") and args:
        bundled = args[0] if not args[0].startswith("-") else ""                     # "czf out.tgz" as well as "-c -z -f out.tgz"
        mode = bundled + "".join(a[1:] for a in args if re.fullmatch(r"-[A-Za-z]+", a) and a != "-C")
        target = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-C", "--directory")), None)
        archive = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-f", "--file") or (re.fullmatch(r"-?[A-Za-z]*f", a) and a != "-C")
                        or (i == 0 and bundled and "f" in bundled)), None)
        if "x" in mode:
            writes = [target or "."]
        elif any(c in mode for c in "cru") and archive:
            writes = [archive]
    elif prog == "unzip":
        writes = [next((args[i + 1] for i, a in enumerate(args[:-1]) if a == "-d"), ".")]
    elif prog == "zip":
        writes = names[:1]
    for name, write in [(n, False) for n in reads] + [(n, True) for n in writes]:
        if name == "-":
            continue
        p = _path(name, cwd=cwd)
        hit = _file(p, write) if p else None
        if hit:
            return hit
    return None


def _redirects(words: list[str], cwd):
    """A shell's > and >> write the file they name."""
    for i, w in enumerate(words):
        m = re.fullmatch(r"(\d*|&)>>?\|?(.*)", w)
        if not m:
            continue
        name = m.group(2) or (words[i + 1] if i + 1 < len(words) else "")
        if name and not name.startswith("&"):
            p = _path(name, cwd=cwd)
            hit = _file(p, write=True) if p else None
            if hit:
                return hit
    return None


def _python(words: list[str], env):
    """A Python started by a test must put up the wall: no -I, -S or -E, and an environment that keeps the wall's folder on PYTHONPATH."""
    for w in words[1:]:
        if w in ("-c", "-m") or not w.startswith("-"):
            break
        if not w.startswith("--") and any(c in w[1:] for c in "ISE"):
            return ("starting a Python that skips the wall (-I, -S or -E)", os.path.basename(words[0]) + " " + w, PermissionError)
    site = _state.get("site")
    if site and site not in _getenv(env, "PYTHONPATH").split(os.pathsep):
        return ("starting a Python without the wall (an environment that leaves it out)", os.path.basename(words[0]), PermissionError)
    return None


def _command(words: list[str], cwd, env, depth: int = 0):
    """One command a test starts: the program, and every later word when the program is a wrapper (nice, timeout, env, sudo ...)."""
    if not words or depth > 4:
        return None
    if depth:                                                         # inside a shell's -c: its > and >> write files
        hit = _redirects(words, cwd)
        if hit:
            return hit
        words = [w for w in words if not re.fullmatch(r"(\d*|&)[<>]{1,2}\|?.*", w)]
    first = 0
    while first < len(words) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", words[first]):     # FOO=bar before a program
        first += 1
    if first >= len(words):
        return None
    for w in words[first + 1:]:                                       # any program given a private place's name, a reader (cat) too
        if w.startswith("-") and "=" not in w:
            continue
        p = _path(w.split("=", 1)[1] if w.startswith("-") or re.fullmatch(r"[a-z]+=.*", w) else w, cwd=cwd)
        hit = _file(p, write=False) if p else None
        if hit:
            return hit
    lead = os.path.basename(words[first])
    starts = [first] + (list(range(first + 1, len(words))) if lead in WRAPPERS else [])
    for i in starts:
        prog = os.path.basename(words[i])
        if prog in TOOLS:
            return ("starting a program that reaches the network or the services", prog, PermissionError)
        if prog == "git":
            rest = words[i + 1:]
            sub = next((w for j, w in enumerate(rest) if not w.startswith("-") and not (j and rest[j - 1] in ("-C", "-c"))), "")
            if sub in GIT_NET or (sub == "remote" and any(w in ("update", "prune", "show", "set-head") for w in rest)):
                return ("starting a program that reaches the network or the services", f"git {sub}", PermissionError)
        if prog in SHELLS:
            rest = words[i + 1:]
            if "-c" in rest[:3]:
                k = rest.index("-c")
                for seg in _segments(rest[k + 1] if k + 1 < len(rest) else "", env):
                    hit = _command(seg, cwd, env, depth + 1)
                    if hit:
                        return hit
            continue
        if PYTHON.fullmatch(prog):
            hit = _python(words[i:], env)
            if hit:
                return hit
        if prog in WRITE_ALL | WRITE_LAST | WRITE_AFTER_FIRST or prog in ("truncate", "sqlite3", "sed", "gsed", "dd", "tar", "bsdtar", "gtar",
                                                                          "unzip", "zip"):
            hit = _writes(words[i:], cwd)
            if hit:
                return hit
    return None


def _program(argv, cwd=None, env=None):
    words = _words(argv)
    if not words:
        return None
    return _command(words, cwd, env)


def _check(event: str, args: tuple):
    if event == "open":
        p = _path(args[0])
        if not p:
            return None
        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else 0
        write = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (isinstance(flags, int) and bool(flags & WRITE_FLAGS))
        return _file(p, write)
    if event == "sqlite3.connect":
        p = _path(args[0])
        if not p:
            return None
        return _file(p, write=not _sqlite_read_only(args[0]))
    if event in ("os.listdir", "os.scandir"):
        p = _path(args[0]) if args else None
        return _file(p, write=False) if p else None
    if event in ("os.remove", "os.rmdir", "shutil.rmtree"):                  # (path, dir_fd)
        p = _path(args[0], args[1] if len(args) > 1 else None) if args else None
        return _file(p, write=True) if p else None
    if event in ("os.mkdir", "os.chmod"):                                     # (path, mode, dir_fd)
        p = _path(args[0], args[2] if len(args) > 2 else None) if args else None
        return _file(p, write=True) if p else None
    if event == "os.chown":                                                   # (path, uid, gid, dir_fd)
        p = _path(args[0], args[3] if len(args) > 3 else None) if args else None
        return _file(p, write=True) if p else None
    if event == "os.truncate":                                                # (path, length)
        p = _path(args[0]) if args else None
        return _file(p, write=True) if p else None
    if event in ("os.rename", "os.link"):                                     # (src, dst, src_dir_fd, dst_dir_fd)
        for a, fd in ((args[0], args[2] if len(args) > 2 else None), (args[1], args[3] if len(args) > 3 else None)):
            p = _path(a, fd)
            hit = _file(p, write=True) if p else None
            if hit:
                return hit
        return None
    if event == "os.symlink":                                                 # (src, dst, dir_fd): the new link is what is written
        p = _path(args[1], args[2] if len(args) > 2 else None) if len(args) > 1 else None
        return _file(p, write=True) if p else None
    if event in ("socket.connect", "socket.sendto", "socket.sendmsg"):
        return _address(args[1]) if len(args) > 1 and args[1] is not None else None
    if event in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.gethostbyname_ex"):
        host = args[0] if args else None
        if host is not None and not _host_ok(host) and not _is_ip(host):     # a number needs no lookup: its connection is checked instead
            return ("looking up a name on the network", str(host), socket.gaierror)
        return None
    if event == "subprocess.Popen":                                           # (executable, args, cwd, env)
        argv = args[1] if len(args) > 1 and args[1] else [args[0]]
        return _program(argv, args[2] if len(args) > 2 else None, args[3] if len(args) > 3 else None)
    if event == "os.system":
        return _program(["sh", "-c", args[0]])
    if event == "os.posix_spawn":                                             # (path, argv, env)
        return _program(args[1] if len(args) > 1 and args[1] else [args[0]], None, args[2] if len(args) > 2 else None)
    if event == "os.exec":                                                    # (path, args, env)
        return _program(args[1] if len(args) > 1 else None, None, args[2] if len(args) > 2 else None)
    if event == "os.spawn":                                                   # (mode, path, args, env)
        return _program(args[2] if len(args) > 2 else None, None, args[3] if len(args) > 3 else None)
    return None


def _refuse(hit) -> None:
    what, target, err = hit
    msg = f"the tests' wall: {what} refused ({target})"
    _note(msg)
    if err is socket.gaierror:
        raise socket.gaierror(socket.EAI_NONAME, msg)
    raise err(msg)


def _note(msg: str) -> None:
    if msg not in REFUSED and len(REFUSED) < 500:
        REFUSED.append(msg)


def _guarded(what: str, fn, *a):
    """Run one of the wall's own checks; a fault in it lets the call go on and is written down (never silent)."""
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001
        _note(f"the tests' wall: its own check failed on {what} ({type(e).__name__}); the call went on")
        return None


def _hook(event: str, args: tuple) -> None:
    if event not in WATCHED or not _state["on"] or getattr(_busy, "on", False):   # most events (import, compile, ...) leave at once
        return
    _busy.on = True
    try:
        hit = _guarded(event, _check, event, args)
    finally:
        _busy.on = False
    if hit:
        _refuse(hit)


_real_os_open = os.open


def _os_open(path, flags, mode=0o777, *, dir_fd=None):
    """os.open with a folder number: its audit event names the file but not the folder, so the hook would read the name against the
    current folder (12 Nov, the second outside check: a name relative to an open home folder got through). Checked here, then opened."""
    if dir_fd is None or not _state["on"] or getattr(_busy, "on", False):
        return _real_os_open(path, flags, mode, dir_fd=dir_fd)
    _busy.on = True
    try:
        p = _guarded("os.open", _path, path, dir_fd)
        hit = _guarded("os.open", _file, p, bool(flags & WRITE_FLAGS)) if p else None
        if p is None and not isinstance(path, int):
            _note("the tests' wall: a name opened relative to a folder it could not read back went on unchecked")
        if hit:
            _busy.on = False
            _refuse(hit)
        return _real_os_open(path, flags, mode, dir_fd=dir_fd)         # checked above; the hook would read the name against the wrong folder
    finally:
        _busy.on = False


def _own_names() -> frozenset:
    try:
        n = socket.gethostname().lower()
    except OSError:
        return frozenset()
    return frozenset({n, n.split(".")[0], n.split(".")[0] + ".local"})


def install(real_home: str, readable: tuple = (), never: tuple = ()) -> None:
    """Put the wall up in this process (once; it cannot be taken down). readable: places under DENIED that may be read, never written
    (the records tests read India's data folder); never: places refused even to them (the sealed data). Both are relative to the home."""
    if _state["on"]:
        return
    home = os.path.realpath(real_home)
    site = next((p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if os.path.basename(p.rstrip(os.sep)) == ".wall"), "")
    _state.update(home=home, denied=tuple(os.path.join(home, d) for d in DENIED), names=_own_names(), site=site,
                  readable=tuple(os.path.join(home, d) for d in readable), never=tuple(os.path.join(home, d) for d in never))
    os.open = _os_open
    sys.addaudithook(_hook)
    _state["on"] = True
