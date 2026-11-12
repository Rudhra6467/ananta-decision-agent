"""The tests' wall. tests/conftest.py puts it up before any of Ananta's modules is imported.

12 Nov 2026, the keen outside audit (G-57: "test isolation is a list of nine past leaks, not a wall"). The first wall, that morning,
moved the tests' home folder and patched Python's socket class. The outside check that followed got through it four ways: a full path to
the live database and the .env file, the C-level socket, a UDP datagram, and a `curl` started from a test. This wall sits on Python's
audit hooks, which see each of those inside the interpreter whatever library or full path asks; a hook cannot be taken off once it is on.
In a process with the wall:

  files     nothing under Madhav's private places is opened, listed, read or written, even by its full path (DENIED below); no file
            named *.env under his home is read; and nothing under his home is written, renamed, removed or made, except Python's own
            __pycache__ files. The tests' own home and their temporary folders are not under his home, so they are untouched.
  network   no connection, datagram or name lookup leaves this machine, and none reaches the live services' ports on it.
  programs  no program that reaches the network or controls the services is started (curl, wget, ssh, launchctl ...); and every
            Python a test starts puts up the same wall first (SITECUSTOMIZE, written into the tests' home, first on PYTHONPATH).

What it does not stop: a program other than Python, started by a test, that reaches the network itself (a shell script, node); a
Python started with -I or -S (which skips sitecustomize); and native code that opens files or sockets itself, without Python's own calls
(pyarrow, duckdb, ctypes): those still find the tests' own home wherever they work a path out from the home folder, but a full path
written into them is not seen. Only an operating-system sandbox would stop that; none of today's tests does it (12 Nov: the one module that
named a live file by its full path, jarvis/india/ask.py's ENV_FILE, is pointed at the tests' home by conftest).

Each refusal is raised as the error the caller already handles (PermissionError for files and programs, ConnectionRefusedError and
socket.gaierror for the network), with "the tests' wall" in its words, and is noted in REFUSED; tests/conftest.py prints that list at
the end of the run, so a test whose code swallows the error still shows up. A refused path is shown only to its first folders.
"""
from __future__ import annotations

import os
import re
import socket
import sys
import threading

DENIED = ("ananta_data", "ananta_runs", "ananta_private", "ananta_backups", ".ananta", ".appstore", "code/ananta-decision-agent",
          "Library")
LIVE_PORTS = frozenset({8001, 8100, 8110, 8199, 8200, 8215, 8300, 8302, 8399, 11434, 20241})   # the services running on the Mac
TOOLS = frozenset({"curl", "wget", "ssh", "scp", "sftp", "rsync", "nc", "ncat", "telnet", "ftp", "launchctl", "osascript", "open",
                   "security", "networksetup", "scutil"})
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "env", "xargs", "nohup", "time", "exec", "command"})
LOCAL = frozenset({"", "localhost", "127.0.0.1", "::1", "0.0.0.0", "::", "ip6-localhost"})
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC

SITECUSTOMIZE = '''# Written by tests/conftest.py: every Python a test starts puts up the tests' wall first (tests/wall.py).
import importlib.util as _u
_s = _u.spec_from_file_location("ananta_tests_wall", {wall!r})
_m = _u.module_from_spec(_s)
_s.loader.exec_module(_m)
_m.install({home!r})
'''

WATCHED = frozenset({"open", "sqlite3.connect", "os.listdir", "os.scandir", "os.remove", "os.rmdir", "shutil.rmtree", "os.mkdir", "os.chmod",
                     "os.chown", "os.truncate", "os.rename", "os.link", "os.symlink", "socket.connect", "socket.sendto", "socket.sendmsg",
                     "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.gethostbyname_ex", "subprocess.Popen",
                     "os.system", "os.posix_spawn", "os.exec", "os.spawn"})

REFUSED: list[str] = []
_state: dict = {"on": False, "home": "", "denied": (), "names": frozenset()}
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


def _path(p, dir_fd=None) -> str | None:
    """A real, absolute path for what an event names, or None (a file number, an in-memory database, nothing, or a name relative to a
    folder number that cannot be read back)."""
    if p is None or isinstance(p, int):
        return None
    try:
        s = os.fsdecode(os.fspath(p))
    except TypeError:
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
    if any(_under(path, r) for r in _state["denied"]):
        return ("reading or writing Madhav's private files", _shown(path), PermissionError)
    if write and "__pycache__" not in path.split(os.sep):
        code = _under(path, os.path.join(home, "code"))                 # the private checkout under code/ was refused above
        return ("writing under Madhav's home", _shown(path, full=code), PermissionError)
    if not write and os.path.basename(path).endswith(".env"):
        return ("reading a .env file", _shown(path), PermissionError)
    return None


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


def _program(argv):
    words = [os.fsdecode(a) if isinstance(a, (bytes, str)) else str(a) for a in (argv or [])]
    if not words:
        return None
    first = os.path.basename(words[0])
    found = first if first in TOOLS else None
    if found is None and (first in SHELLS or "-c" in words[1:2]):
        found = next((os.path.basename(t) for t in re.split(r"[\s;&|()`$<>'\"]+", " ".join(words[1:])) if os.path.basename(t) in TOOLS), None)
    return ("starting a program that reaches the network or the services", found, PermissionError) if found else None


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
        ro = isinstance(args[0], str) and "mode=ro" in args[0]
        return _file(p, write=not ro)
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
    if event == "subprocess.Popen":
        return _program(args[1] if len(args) > 1 and args[1] else [args[0]])
    if event == "os.system":
        return _program(["sh", "-c", args[0]])
    if event == "os.posix_spawn":
        return _program(args[1] if len(args) > 1 and args[1] else [args[0]])
    if event == "os.exec":
        return _program(args[1] if len(args) > 1 else None)
    if event == "os.spawn":
        return _program(args[2] if len(args) > 2 else None)
    return None


def _hook(event: str, args: tuple) -> None:
    if event not in WATCHED or not _state["on"] or getattr(_busy, "on", False):   # most events (import, compile, ...) leave at once
        return
    _busy.on = True
    try:
        try:
            hit = _check(event, args)
        except Exception:  # noqa: BLE001  a fault in the wall itself never breaks the run; the refusal below is the only raise
            hit = None
    finally:
        _busy.on = False
    if hit:
        what, target, err = hit
        msg = f"the tests' wall: {what} refused ({target})"
        if msg not in REFUSED and len(REFUSED) < 500:
            REFUSED.append(msg)
        if err is socket.gaierror:
            raise socket.gaierror(socket.EAI_NONAME, msg)
        raise err(msg)


def _own_names() -> frozenset:
    try:
        n = socket.gethostname().lower()
    except OSError:
        return frozenset()
    return frozenset({n, n.split(".")[0], n.split(".")[0] + ".local"})


def install(real_home: str) -> None:
    """Put the wall up in this process (once; it cannot be taken down)."""
    if _state["on"]:
        return
    home = os.path.realpath(real_home)
    _state.update(home=home, denied=tuple(os.path.join(home, d) for d in DENIED), names=_own_names())
    sys.addaudithook(_hook)
    _state["on"] = True
