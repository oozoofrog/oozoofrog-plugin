"""Install a `gf` command on the person's PATH (`gf setup`)."""
import os
import pathlib
import re
import stat

from . import core

MARKER = "# graph-flow launcher, written by `gf setup`"
SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "gf"
TEMPLATE = '''#!/usr/bin/env python3
%(marker)s
import glob
import os
import re
import sys

TARGET = %(target)r
SIBLINGS = %(siblings)r


def version(path):
    return [int(part) for part in re.findall(r"\\d+", path[len(SIBLINGS.split("*")[0]):].split(os.sep)[0])]


found = sorted(glob.glob(SIBLINGS), key=version) if SIBLINGS else []
if not found and os.path.isfile(TARGET):
    found = [TARGET]
if not found:
    sys.stderr.write("gf: graph-flow is no longer installed at %%s; run gf setup again from the skill\\n" %% TARGET)
    sys.exit(5)
os.execv(sys.executable, [sys.executable, "-B", found[-1]] + sys.argv[1:])
'''


def default_bin_dir():
    return pathlib.Path.home() / ".local" / "bin"


def _siblings(script):
    """Glob matching every installed version beside this one, or "" outside a versioned install."""
    version_dir = script.parents[3]
    if not re.fullmatch(r"\d+(\.\d+)*", version_dir.name):
        return ""
    return str(version_dir.parent / "*" / script.relative_to(version_dir))


def _ours(path):
    try:
        return MARKER in path.read_text(encoding="utf-8").splitlines()[:3]
    except (OSError, UnicodeDecodeError):
        return False


def _on_path(directory):
    resolved = directory.resolve()
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if entry and pathlib.Path(entry).expanduser().resolve() == resolved:
            return True
    return False


def install(bin_dir=None, script=None):
    """Write the launcher; refuse to replace a file this tool did not write."""
    directory = pathlib.Path(bin_dir).expanduser() if bin_dir else default_bin_dir()
    script = pathlib.Path(script) if script else SCRIPT
    path = directory / "gf"
    if (path.exists() or path.is_symlink()) and not _ours(path):
        raise core.GFError("exists", "%s exists and was not written by gf setup; "
                           "move it or choose --bin-dir" % path, core.EXIT_STATE)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / (".gf.%d.tmp" % os.getpid())
    temporary.write_text(TEMPLATE % {"marker": MARKER, "target": str(script),
                                     "siblings": _siblings(script)}, encoding="utf-8")
    temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    os.replace(str(temporary), str(path))
    on_path = _on_path(directory)
    message = "Installed %s." % path
    if not on_path:
        message += ' %s is not on PATH; add: export PATH="%s:$PATH"' % (directory, directory)
    return {"installed": str(path), "on_path": on_path, "message": message}


def remove(bin_dir=None):
    """Remove the launcher when this tool wrote it."""
    directory = pathlib.Path(bin_dir).expanduser() if bin_dir else default_bin_dir()
    path = directory / "gf"
    if not (path.exists() or path.is_symlink()):
        return {"removed": False, "message": "No gf command at %s." % path}
    if not _ours(path):
        raise core.GFError("exists", "%s was not written by gf setup; left in place" % path, core.EXIT_STATE)
    path.unlink()
    return {"removed": True, "message": "Removed %s." % path}
