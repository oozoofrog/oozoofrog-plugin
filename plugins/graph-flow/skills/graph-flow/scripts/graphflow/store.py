"""Files, locking, transactions and plan revisions (records.md sections 1, 3, 5)."""
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import pathlib
import re
import secrets
import subprocess
import tempfile
import time

from .core import EXIT_IO, EXIT_STATE, EXIT_USAGE, GFError, gf_home, now

SCHEMA_VERSION = 2
LOCK_TIMEOUT_S = 30
GITIGNORE_LINES = ("runs/", ".lock")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_PATH_PART_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$")
_PLAN_FILE_RE = re.compile(r"^(\d+)\.json$")


# ---------------------------------------------------------------- files

def atomic_write(path, text):
    """Write text (str or bytes) to a temporary file in the same directory, fsync, os.replace."""
    path = pathlib.Path(path)
    data = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    _fsync_dir(path.parent)


def _fsync_dir(directory):
    try:
        fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


# ---------------------------------------------------------------- locks

@contextlib.contextmanager
def locked(lock_path, timeout_s=LOCK_TIMEOUT_S):
    """Exclusive fcntl.flock on lock_path; GFError lock_timeout (exit 5) after timeout_s."""
    lock_path = pathlib.Path(lock_path)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    except OSError as e:
        raise GFError("io_error", "cannot open lock %s: %s" % (lock_path, e), EXIT_IO)
    try:
        deadline = time.monotonic() + timeout_s
        delay = 0.002
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EACCES):
                    raise GFError("io_error", "cannot lock %s: %s" % (lock_path, e), EXIT_IO)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GFError("lock_timeout", "timed out after %ss waiting for %s" % (timeout_s, lock_path), EXIT_IO)
            time.sleep(min(delay, remaining))
            delay = min(delay * 2, 0.05)
        try:
            yield lock_path
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------- project and registry

def project_root(path=None):
    """Git top level of path (or the cwd); GFError if it is not inside a repository."""
    base = pathlib.Path(path) if path is not None else pathlib.Path.cwd()
    try:
        r = subprocess.run(["git", "-C", str(base), "rev-parse", "--show-toplevel"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    except OSError as e:
        raise GFError("not_a_repository", "cannot run git: %s" % e, EXIT_USAGE)
    top = r.stdout.strip()
    if r.returncode != 0 or not top:
        raise GFError("not_a_repository", "not inside a git repository: %s" % base, EXIT_USAGE)
    return pathlib.Path(top).resolve()


def project_of(run_dir):
    return pathlib.Path(run_dir).resolve().parent.parent.parent


def register_project(root):
    """Add root to $GF_HOME/registry.json under $GF_HOME/.lock; idempotent."""
    root = str(real_path(root))
    home = gf_home()
    reg_path = home / "registry.json"
    with locked(home / ".lock"):
        registry = {"projects": []}
        if reg_path.exists():
            try:
                registry = json.loads(reg_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise GFError("io_error", "cannot read %s: %s" % (reg_path, e), EXIT_IO)
            if not isinstance(registry, dict) or not isinstance(registry.get("projects"), list):
                raise GFError("io_error", "malformed %s" % reg_path, EXIT_IO)
        if not any(isinstance(p, dict) and p.get("root") == root for p in registry["projects"]):
            registry["projects"].append({"root": root, "added": now()})
            atomic_write(reg_path, json.dumps(registry, indent=2) + "\n")
    return registry


# ---------------------------------------------------------------- run layout

def _events_path(run_dir):
    return pathlib.Path(run_dir) / "events.jsonl"


def _plan_path(run_dir, revision):
    return pathlib.Path(run_dir) / "plans" / ("%04d.json" % revision)


def init_run(project_root, run_id, actor):
    if not isinstance(run_id, str) or not _ID_RE.match(run_id):
        raise GFError("bad_run_id", "run id must match %s: %r" % (_ID_RE.pattern, run_id), EXIT_USAGE)
    root = pathlib.Path(project_root).resolve()
    meta = root / ".graph-flow"
    try:
        (meta / "runs").mkdir(parents=True, exist_ok=True)
        _ensure_gitignore(meta / ".gitignore")
        run_dir = meta / "runs" / run_id
        try:
            run_dir.mkdir()
        except FileExistsError:
            raise GFError("run_exists", "run already exists: %s" % run_dir, EXIT_STATE)
        for sub in ("plans", "evidence", "brief"):
            (run_dir / sub).mkdir()
        _events_path(run_dir).touch()
        (run_dir / ".lock").touch()
    except OSError as e:
        raise GFError("io_error", "cannot create run: %s" % e, EXIT_IO)
    with transaction(run_dir) as tx:
        tx.append("run.init", {"run_id": run_id, "project_root": str(root),
                               "schema_version": SCHEMA_VERSION, "approval_required": True,
                               "run_nonce": secrets.token_hex(32)}, actor)
    register_project(root)
    return run_dir


def _ensure_gitignore(path):
    with locked(path.parent / ".lock"):
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        lines = existing.splitlines()
        missing = [l for l in GITIGNORE_LINES if l not in lines]
        if missing:
            text = existing
            if text and not text.endswith("\n"):
                text += "\n"
            atomic_write(path, text + "".join(l + "\n" for l in missing))


def evidence_path(run_dir, node, check, attempt):
    """Create evidence/<node>/<check>/a<attempt>-<8 hex>.log exclusively and return its Path."""
    for part in (node, check):
        if not isinstance(part, str) or not _PATH_PART_RE.match(part) or part in (".", ".."):
            raise GFError("bad_name", "invalid evidence path component: %r" % (part,), EXIT_USAGE)
    directory = pathlib.Path(run_dir) / "evidence" / node / check
    directory.mkdir(parents=True, exist_ok=True)
    while True:
        path = directory / ("a%d-%s.log" % (int(attempt), secrets.token_hex(4)))
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            continue
        os.close(fd)
        return path


# ---------------------------------------------------------------- log reading

def _read_log(run_dir):
    """(events, good_len, total_len). good_len is the byte offset after the last valid line."""
    path = _events_path(run_dir)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise GFError("no_run", "no event log at %s" % path, EXIT_STATE)
    except OSError as e:
        raise GFError("io_error", "cannot read %s: %s" % (path, e), EXIT_IO)
    out = []
    pos = 0
    good = 0
    n = len(data)
    while pos < n:
        nl = data.find(b"\n", pos)
        if nl < 0:
            break  # incomplete tail: no trailing newline
        line = data[pos:nl]
        try:
            ev = json.loads(line.decode("utf-8"))
            if not isinstance(ev, dict):
                raise ValueError("not an object")
        except ValueError:
            if nl + 1 == n:
                break  # last line does not parse: incomplete tail
            raise GFError("log_corrupt", "unparsable line at byte %d of %s" % (pos, path), EXIT_IO)
        expected = len(out) + 1
        if type(ev.get("seq")) is not int or ev["seq"] != expected:
            raise GFError("log_sequence", "invalid seq at line %d of %s; expected %d" %
                          (expected, path, expected), EXIT_STATE)
        out.append(ev)
        pos = nl + 1
        good = pos
    return out, good, n


class EventLog(list):
    """Trusted read context, never serialized into or taken from the event log."""
    def __init__(self, values, run_dir):
        super().__init__(values)
        self.run_dir = pathlib.Path(run_dir).resolve()


def real_path(path):
    """Resolve symlinks and the spelling stored by case-insensitive filesystems."""
    path = pathlib.Path(os.path.realpath(str(path)))
    result = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        candidate = result / part
        try:
            # Prefer exact names on case-sensitive filesystems; samefile also handles APFS aliases.
            names = os.listdir(result)
            if part not in names:
                part = next((name for name in names if name.casefold() == part.casefold()
                             and os.path.samefile(result / name, candidate)), part)
        except OSError:
            pass
        result /= part
    return result


def location(run_dir):
    path = real_path(run_dir)
    return {"project_root": str(path.parent.parent.parent), "run_directory": path.name}


def events(run_dir):
    return EventLog(_read_log(run_dir)[0], run_dir)


def _last_plan_set(evs):
    for ev in reversed(evs):
        if ev.get("type") == "plan.set":
            return ev
    return None


def _load_plan(run_dir, revision, recorded=None):
    from . import state, plan as planning
    path = _plan_path(run_dir, revision)
    if recorded is None:
        recorded = next((e["data"] for e in reversed(events(run_dir))
                         if e.get("type") == "plan.set" and e["data"].get("revision") == revision), {})
    try:
        raw = path.read_bytes()
        plan = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as e:
        raise GFError("plan_tampered", "Cannot verify plan revision %d: %s" % (revision, e), EXIT_STATE)
    problems = planning.validate(plan)
    if problems:
        raise GFError("plan_tampered", "Invalid plan revision %d: %s" % (revision, json.dumps(problems)), EXIT_STATE)
    if (hashlib.sha256(raw).hexdigest() != recorded.get("plan_sha256") or
            recorded.get("plan_identity") and state.plan_identity(plan) != recorded["plan_identity"]):
        raise GFError("plan_tampered", "Plan revision %d differs from its recorded hash or identity" % revision, EXIT_STATE)
    return plan


def read_plan(run_dir):
    ev = _last_plan_set(events(run_dir))
    if ev is None:
        return None
    return _load_plan(run_dir, int(ev["data"]["revision"]), ev["data"])


# ---------------------------------------------------------------- transactions

class Transaction(object):
    def __init__(self, run_dir, evs, good_len, total_len, replace_invalid=False):
        self.run_dir = pathlib.Path(run_dir)
        self.run_id = self.run_dir.name
        self.events = EventLog(evs, run_dir)
        self._good_len = good_len
        self._dropped = total_len - good_len
        self._pending = []
        self._written_plans = {}
        self.plan_error = False
        last = _last_plan_set(evs)
        if last is None:
            self.revision = 0
            self.plan = None
        else:
            self.revision = int(last["data"]["revision"])
            try:
                self.plan = _load_plan(run_dir, self.revision, last["data"])
            except GFError as exc:
                if not replace_invalid or exc.code != "plan_tampered":
                    raise
                self.plan, self.plan_error = None, True

    def _make(self, type_, data, actor):
        seq = (self.events[-1]["seq"] if self.events else 0) + 1
        ev = {"seq": seq, "ts": now(), "run": self.run_id, "plan_revision": self.revision,
              "actor": dict(actor) if actor is not None else None, "type": type_,
              "data": data if data is not None else {}}
        self.events.append(ev)
        self._pending.append(ev)
        return ev

    def append(self, type_, data, actor):
        if type_ == "decision.ask":
            from . import state
            data["location"] = location(self.run_dir)
            derived = state.derive(self.plan, self.events)
            sub = (derived["nodes"].get(data.get("node")) or {}).get("submission")
            data["submission_binding"] = state.submission_binding(sub) if sub else None
            data["artifact_hashes"] = state.artifact_hashes(self.run_dir, data.get("evidence"), sub)
        if self._dropped and not self._pending:
            self._make("log.recovered", {"dropped_bytes": self._dropped}, actor)
        if type_ == "plan.set":
            revision = int(data["revision"])
            if revision in self._written_plans:
                self.plan = self._written_plans[revision]
            else:
                self.plan = _load_plan(self.run_dir, revision, data)
            self.revision = revision
        return self._make(type_, data, actor)

    def write_plan(self, plan):
        plans = self.run_dir / "plans"
        highest = self.revision
        for p in plans.iterdir() if plans.is_dir() else ():
            m = _PLAN_FILE_RE.match(p.name)
            if m:
                highest = max(highest, int(m.group(1)))
        highest = max([highest] + list(self._written_plans))
        revision = highest + 1
        data = (json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        atomic_write(_plan_path(self.run_dir, revision), data)
        self._written_plans[revision] = json.loads(data.decode("utf-8"))
        return revision, hashlib.sha256(data).hexdigest()

    def _commit(self):
        if not self._pending:
            return
        payload = b"".join(
            (json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            for ev in self._pending)
        path = _events_path(self.run_dir)
        try:
            fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o644)
            try:
                if self._dropped:
                    os.ftruncate(fd, self._good_len)
                os.lseek(fd, 0, os.SEEK_END)
                view = memoryview(payload)
                while view:
                    view = view[os.write(fd, view):]
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError as e:
            raise GFError("io_error", "cannot append to %s: %s" % (path, e), EXIT_IO)
        self._pending = []
        self._dropped = 0


@contextlib.contextmanager
def transaction(run_dir, timeout_s=LOCK_TIMEOUT_S, replace_invalid=False):
    """Run lock + log read; pending appends are written (flush, fsync) only if the block succeeds."""
    run_dir = pathlib.Path(run_dir)
    if not _events_path(run_dir).exists():
        raise GFError("no_run", "not a run directory: %s" % run_dir, EXIT_STATE)
    with locked(run_dir / ".lock", timeout_s):
        tx = Transaction(run_dir, *_read_log(run_dir), replace_invalid=replace_invalid)
        # Observed invalidation is durable even if the requested action is refused.
        # It never changes the node, submission, or pending replacement question.
        if tx.plan and not tx.plan_error:
            from . import state
            derived = state.derive(tx.plan, tx.events)
            for decision in derived["decisions"].values():
                if decision["status"] != "superseded" and decision.get("stale_reason") in ("project_moved", "evidence_changed"):
                    tx.append("decision.superseded", {"id": decision["id"], "reason": decision["stale_reason"]},
                              {"role": "tool", "node": decision.get("node"), "session": None})
            tx._commit()
        yield tx
        tx._commit()
