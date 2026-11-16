"""Install the `graph-flow` and `gf` commands on the person's PATH (`gf setup`)."""
import os
import pathlib
import re
import stat

from . import core

MARKER = "# graph-flow launcher, written by `gf setup`"
# `gf` is short but often taken (oh-my-zsh aliases it to `git fetch`); `graph-flow` is the name to rely on.
NAMES = ("graph-flow", "gf")
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
    name = path[len(SIBLINGS.split("*")[0]):].split(os.sep)[0]
    return [int(part) for part in name.split(".")] if re.fullmatch(r"\\d+(\\.\\d+)*", name) else None


found = sorted((p for p in glob.glob(SIBLINGS) if version(p) is not None), key=version) if SIBLINGS else []
if not found and os.path.isfile(TARGET):
    found = [TARGET]
if not found:
    sys.stderr.write("graph-flow is no longer installed at %%s; run gf setup again from the skill\\n" %% TARGET)
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
    """Write the launchers; never replace a file this tool did not write."""
    directory = pathlib.Path(bin_dir).expanduser() if bin_dir else default_bin_dir()
    script = pathlib.Path(script) if script else SCRIPT
    taken = [name for name in NAMES if ((directory / name).exists() or (directory / name).is_symlink())
             and not _ours(directory / name)]
    if NAMES[0] in taken:
        raise core.GFError("exists", "%s exists and was not written by gf setup; "
                           "move it or choose --bin-dir" % (directory / NAMES[0]), core.EXIT_STATE)
    directory.mkdir(parents=True, exist_ok=True)
    text = TEMPLATE % {"marker": MARKER, "target": str(script), "siblings": _siblings(script)}
    commands = [name for name in NAMES if name not in taken]
    for name in commands:
        temporary = directory / (".%s.%d.tmp" % (name, os.getpid()))
        temporary.write_text(text, encoding="utf-8")
        temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(str(temporary), str(directory / name))
    on_path = _on_path(directory)
    message = "Installed %s in %s." % (" and ".join(commands), directory)
    if taken:
        message += " %s was left alone: it is another program." % (directory / taken[0])
    message += " Use `graph-flow` if your shell already gives `gf` another meaning."
    if not on_path:
        message += ' %s is not on PATH; add: export PATH="%s:$PATH"' % (directory, directory)
    return {"installed": str(directory / NAMES[0]), "commands": commands, "on_path": on_path, "message": message}


def remove(bin_dir=None):
    """Remove the launchers this tool wrote."""
    directory = pathlib.Path(bin_dir).expanduser() if bin_dir else default_bin_dir()
    removed = []
    for name in NAMES:
        path = directory / name
        if (path.exists() or path.is_symlink()) and _ours(path):
            path.unlink()
            removed.append(name)
    if removed:
        return {"removed": True, "commands": removed,
                "message": "Removed %s from %s." % (" and ".join(removed), directory)}
    return {"removed": False, "commands": [], "message": "No graph-flow command written by gf setup in %s." % directory}
