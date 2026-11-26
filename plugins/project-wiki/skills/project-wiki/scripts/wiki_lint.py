#!/usr/bin/env python3
"""Read-only checks for a project-wiki Obsidian vault.

Usage: python3 -I -B wiki_lint.py <vault> [--schema FILE] [--json]

Exit status: 0 = no errors, 1 = errors found, 2 = usage problem.
The vault MAY override the bundled schema with `<vault>/.wiki/schema.json`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- YAML subset
# Covers what frontmatter and .base files use: nested maps, block lists
# (including "- key: value" maps), flow lists ([] / [a, b]), quoted and plain
# scalars, comments. Anything else raises YamlError with a line number.


class YamlError(ValueError):
    pass


def _strip_comment(s: str) -> str:
    out, q = [], None
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).rstrip()


def _scalar(tok: str, ln: int):
    t = tok.strip()
    if t == "":
        return None
    if t[0] in "'\"":
        q = t[0]
        if len(t) < 2 or t[-1] != q:
            raise YamlError(f"line {ln}: unterminated quoted string")
        body = t[1:-1]
        return body.replace("''", "'") if q == "'" else body.replace('\\"', '"')
    if t.startswith("[") :
        if not t.endswith("]"):
            raise YamlError(f"line {ln}: unterminated flow list")
        inner = t[1:-1].strip()
        return [] if not inner else [_scalar(x, ln) for x in _split_flow(inner)]
    if t.startswith("{"):
        raise YamlError(f"line {ln}: flow maps are not supported")
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if t in ("true", "false"):
        return t == "true"
    if t in ("null", "~"):
        return None
    return t


def _split_flow(s: str):
    parts, cur, q = [], [], None
    for ch in s:
        if q:
            cur.append(ch)
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch
            cur.append(ch)
        elif ch == ",":
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


_KEY = re.compile(r"""^("[^"]*"|'[^']*'|[^:'"][^:]*?)\s*:(\s+(.*))?$""")


def parse_yaml(text: str, base_line: int = 1):
    lines = []
    for i, raw in enumerate(text.split("\n")):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlError(f"line {base_line + i}: tab in indentation")
        s = _strip_comment(raw)
        if s.strip():
            lines.append((len(s) - len(s.lstrip(" ")), s.strip(), base_line + i))
    if not lines:
        return {}
    val, pos = _block(lines, 0, lines[0][0])
    if pos != len(lines):
        raise YamlError(f"line {lines[pos][2]}: unexpected indentation")
    return val


def _block(lines, pos, ind):
    if lines[pos][1].startswith("- ") or lines[pos][1] == "-":
        return _list(lines, pos, ind)
    return _map(lines, pos, ind)


def _map(lines, pos, ind, first=None):
    out = {}
    while pos < len(lines) or first is not None:
        if first is not None:
            li, s, ln = first
            first = None
            pos -= 1  # the caller already consumed this line
        else:
            li, s, ln = lines[pos]
        if li < ind:
            break
        elif li > ind:
            raise YamlError(f"line {ln}: unexpected indentation")
        m = _KEY.match(s)
        if not m or s.startswith("- "):
            raise YamlError(f"line {ln}: expected 'key: value'")
        key = m.group(1).strip("'\"")
        if key in out:
            raise YamlError(f"line {ln}: duplicate key '{key}'")
        rest = m.group(3)
        pos += 1
        if rest not in (None, ""):
            if rest in ("|", ">", "|-", ">-"):
                raise YamlError(f"line {ln}: block scalars are not supported")
            out[key] = _scalar(rest, ln)
        elif pos < len(lines) and (lines[pos][0] > li or (lines[pos][0] == li and lines[pos][1].startswith("- "))):
            out[key], pos = _block(lines, pos, lines[pos][0])
        else:
            out[key] = None
    return out, pos


def _list(lines, pos, ind):
    out = []
    while pos < len(lines):
        li, s, ln = lines[pos]
        if li < ind or not (s.startswith("- ") or s == "-"):
            if li > ind:
                raise YamlError(f"line {ln}: unexpected indentation")
            break
        if li > ind:
            raise YamlError(f"line {ln}: unexpected indentation")
        item = s[2:].strip() if s != "-" else ""
        pos += 1
        if item == "":
            if pos < len(lines) and lines[pos][0] > li:
                v, pos = _block(lines, pos, lines[pos][0])
                out.append(v)
            else:
                out.append(None)
        elif _KEY.match(item) and not item[0] in "'\"[":
            sub_ind = li + 2
            v, pos = _map(lines, pos, sub_ind, first=(sub_ind, item, ln))
            out.append(v)
        else:
            out.append(_scalar(item, ln))
    return out, pos


# ---------------------------------------------------------------- vault model

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LINK = re.compile(r"(!?)\[\[([^\]\n]+?)\]\]")
FENCE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
INLINE = re.compile(r"`[^`\n]*`")


class Report:
    def __init__(self, root: Path):
        self.root = root
        self.items = []

    def add(self, level, rule, path, msg):
        rel = str(path.relative_to(self.root)) if isinstance(path, Path) else path
        self.items.append({"level": level, "rule": rule, "path": rel, "message": msg})

    def error(self, *a):
        self.add("error", *a)

    def warn(self, *a):
        self.add("warning", *a)


def load_schema(vault: Path, override: str | None):
    p = Path(override) if override else vault / ".wiki" / "schema.json"
    if not p.is_file():
        p = HERE / "schema_v1.json"
    return json.loads(p.read_text(encoding="utf-8")), p


def walk(vault: Path, schema):
    ignore = set(schema["ignore_folders"])
    for p in sorted(vault.rglob("*")):
        rel = p.relative_to(vault).parts
        if any(part in ignore or part.startswith(".") for part in rel):
            continue
        yield p


def body_without_code(text: str) -> str:
    text = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return INLINE.sub("", text)


def link_target(raw: str) -> str:
    t = raw.split("|", 1)[0]
    t = t.split("#", 1)[0].split("^", 1)[0]
    return t.strip()


def is_date(v) -> bool:
    if isinstance(v, date):
        return True
    if not isinstance(v, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return False
    try:
        date.fromisoformat(v)
        return True
    except ValueError:
        return False


def vault_config(vault: Path) -> dict:
    p = vault / ".wiki" / "config.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except ValueError:
        return {}


def memory_dirs_for(project: Path | None) -> list[Path]:
    if project is None:
        return []
    sys.path.insert(0, str(HERE))
    from wiki_sources import claude_project_dirs
    return [d / "memory" for d in claude_project_dirs(project) if (d / "memory").is_dir()]


def lint(vault: Path, schema, project: Path | None = None) -> Report:
    r = Report(vault)
    cfg = vault_config(vault)
    tmpl = vault / (cfg.get("folders", {}).get("templates") or schema["template_folder"])
    project = project or project_root_of(vault)
    memory_dirs = memory_dirs_for(project)
    forbidden = set(schema["forbidden_title_chars"])
    files = list(walk(vault, schema))
    notes = {}            # Path -> (frontmatter dict | None, body)
    by_name = {}          # lowercase basename (no .md) -> [Path]
    by_relpath = set()    # lowercase relative path without .md
    aliases = {}          # lowercase alias -> Path

    for p in files:
        if p.is_dir():
            continue
        rel_noext = str(p.relative_to(vault))
        if p.suffix == ".md":
            rel_noext = rel_noext[:-3]
        key = p.stem if p.suffix == ".md" else p.name
        by_name.setdefault(key.lower(), []).append(p)
        by_relpath.add(rel_noext.lower())
        if p.suffix != ".md":
            continue
        bad = sorted(set(p.stem) & forbidden)
        if bad:
            r.error("title-chars", p, f"title contains {''.join(bad)!r}; Obsidian links and some tools break on these")
        text = p.read_text(encoding="utf-8")
        m = FM.match(text)
        fm = None
        if m:
            src = m.group(1)
            if p.is_relative_to(tmpl):
                src = re.sub(r"\{\{[^}]*\}\}", "placeholder", src)
            try:
                fm = parse_yaml(src, base_line=2)
                if not isinstance(fm, dict):
                    raise YamlError("frontmatter is not a map")
            except YamlError as e:
                r.error("frontmatter-yaml", p, str(e))
                fm = None
        elif not p.is_relative_to(tmpl):
            r.error("frontmatter-missing", p, "no frontmatter block at the top of the note")
        notes[p] = (fm, text[m.end():] if m else text, m.group(1).count("\n") + 3 if m else 1)
        for a in (fm or {}).get("aliases") or []:
            if isinstance(a, str):
                aliases[a.lower()] = p

    # Folders under a typed-note folder usually come from a "/" in a title.
    typed_dirs = {}
    for p, (fm, _, _) in notes.items():
        if fm and fm.get("type") in ("episode", "lesson", "knowledge") and not p.is_relative_to(tmpl):
            typed_dirs.setdefault(fm["type"], set()).add(p.parent)
    for t, dirs in typed_dirs.items():
        for p, (fm, _, _) in notes.items():
            if not fm or fm.get("type") != t or p.is_relative_to(tmpl):
                continue
            outer = [d for d in dirs if d != p.parent and p.parent.is_relative_to(d)]
            if outer:
                top = min(outer, key=lambda d: len(d.parts))
                r.error("nested-note", p, f"{t} note is in a subfolder of '{top.relative_to(vault)}'; a '/' in the title probably split it")

    base_views = {}  # lowercase base file name -> set of view names (None if unparsable)
    for p in files:
        if p.suffix == ".base":
            try:
                d = parse_yaml(p.read_text(encoding="utf-8"))
                base_views[p.name.lower()] = {v.get("name") for v in d.get("views") or [] if isinstance(v, dict)}
            except (YamlError, AttributeError):
                base_views[p.name.lower()] = None

    def resolve(target: str):
        t = target.lower()
        if t.endswith(".md"):
            t = t[:-3]
        if "/" in t:
            return t in by_relpath or any(rp.endswith("/" + t) for rp in by_relpath)
        return t in by_name

    def check_link(p, raw, where):
        target = link_target(raw)
        if not target:
            return
        if resolve(target):
            name = target.split("/")[-1].lower()
            if name.endswith(".base") and "#" in raw:
                view = raw.split("|", 1)[0].split("#", 1)[1].strip()
                views = base_views.get(name)
                if views is not None and view not in views:
                    r.error("base-embed-view", p, f"{where}: [[{raw}]] names view '{view}', but {target} has only {sorted(x for x in views if x)}")
            return
        if target.lower() in aliases:
            owner = aliases[target.lower()].stem
            r.error("link-alias-only", p, f"{where}: [[{raw}]] matches only an alias of '{owner}'; Obsidian leaves it unresolved. Use [[{owner}|{target}]]")
        else:
            r.error("link-broken", p, f"{where}: [[{raw}]] has no target note")

    lessons, episodes = {}, {}
    for p, (fm, body, body_line) in notes.items():
        in_tmpl = p.is_relative_to(tmpl)
        if not in_tmpl:
            check_privacy(r, p, body)
            clean = body_without_code(body)
            for i, line in enumerate(clean.split("\n")):
                for m in LINK.finditer(line):
                    check_link(p, m.group(2), f"line {body_line + i}")
        if fm is not None and in_tmpl and fm.get("type") == "lesson":
            check_template_log(r, p, body, schema)
        if fm is None or in_tmpl:
            continue
        t = fm.get("type")
        if t is None:
            r.error("type-missing", p, "frontmatter has no 'type'")
            continue
        spec = schema["types"].get(t)
        if spec is None:
            r.error("type-unknown", p, f"type '{t}' is not in the schema ({', '.join(schema['types'])})")
            continue
        for k in spec.get("required", []):
            if fm.get(k) in (None, ""):
                r.error("field-missing", p, f"'{k}' is required for type '{t}'")
        for k, allowed in spec.get("enums", {}).items():
            v = fm.get(k)
            if v not in (None, "") and v not in allowed:
                r.error("field-enum", p, f"{k}: '{v}' is not one of {allowed}")
        for k in spec.get("integers", []):
            v = fm.get(k)
            if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 0):
                r.error("field-integer", p, f"{k}: '{v}' must be a non-negative integer")
        for k in spec.get("lists", []):
            v = fm.get(k)
            if v is not None and not isinstance(v, list):
                r.error("field-list", p, f"{k} must be a list")
        for k in schema["dates"]:
            v = fm.get(k)
            if v not in (None, "") and not is_date(v):
                r.error("field-date", p, f"{k}: '{v}' is not a YYYY-MM-DD date")
        for k in spec.get("links", []):
            for v in fm.get(k) or []:
                if isinstance(v, str):
                    m = LINK.fullmatch(v.strip())
                    if not m:
                        r.error("field-link", p, f"{k}: '{v}' must be a quoted [[wikilink]]")
                    else:
                        check_link(p, m.group(2), f"frontmatter {k}")
        check_paths(r, p, fm, schema.get("evidence_fields", {}).get(t, []), project)
        if t == "lesson":
            lessons[p] = fm
            check_lesson(r, p, fm, body, schema)
            check_encoded(r, p, fm, schema, memory_dirs)
        elif t == "episode":
            episodes[p] = fm

    # Back-references between episodes and lessons.
    def names(fm, key):
        out = set()
        for v in fm.get(key) or []:
            m = LINK.fullmatch(v.strip()) if isinstance(v, str) else None
            if m:
                out.add(link_target(m.group(2)).lower())
        return out

    ep_by = {p.stem.lower(): (p, fm) for p, fm in episodes.items()}
    le_by = {p.stem.lower(): (p, fm) for p, fm in lessons.items()}
    for lp, lfm in lessons.items():
        for e in names(lfm, "episodes"):
            if e in ep_by and lp.stem.lower() not in names(ep_by[e][1], "lessons"):
                r.warn("backlink", lp, f"lists episode '{ep_by[e][0].stem}', but that episode does not list this lesson")
    for ep, efm in episodes.items():
        for l in names(efm, "lessons"):
            if l in le_by and ep.stem.lower() not in names(le_by[l][1], "episodes"):
                r.warn("backlink", ep, f"lists lesson '{le_by[l][0].stem}', but that lesson does not list this episode")

    # One request, one episode: a second note for the same date and request is usually a rewrite under a new title.
    seen = {}
    for ep, efm in sorted(episodes.items(), key=lambda x: x[0].stem):
        req = " ".join(str(efm.get("request") or "").split())
        if not req:
            continue
        key = (str(efm.get("date", "")), req)
        if key in seen:
            r.warn("episode-duplicate", ep, f"same date and request as '{seen[key].stem}'; update one episode instead of writing two")
        else:
            seen[key] = ep

    for p in files:
        if p.suffix == ".base":
            check_base(r, p, notes)
    return r


TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")


def check_lesson(r, p, fm, body, schema):
    status = fm.get("status")
    applied, worked = fm.get("applied"), fm.get("worked")
    if status == "encoded" and not fm.get("encoded_in"):
        r.error("lesson-encoded", p, "status is 'encoded' but 'encoded_in' is empty")
    if isinstance(applied, int) and isinstance(worked, int) and worked > applied:
        r.error("lesson-counts", p, f"worked ({worked}) is greater than applied ({applied})")
    if status == "adopted" and isinstance(worked, int) and worked < schema["adopted_min_worked"]:
        r.warn("lesson-adopted", p, f"status is 'adopted' but worked is {worked} (rule: {schema['adopted_min_worked']}+)")
    fs, ls = fm.get("first_seen"), fm.get("last_seen")
    if is_date(fs) and is_date(ls) and str(ls) < str(fs):
        r.error("lesson-dates", p, "last_seen is before first_seen")

    log = schema["application_log"]
    rows, in_section, found = [], False, False
    # rows[0] is the header row once found
    for line in body.split("\n"):
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            in_section = h.group(2).strip() in log["headings"]
            found = found or in_section
            continue
        if in_section:
            m = TABLE_ROW.match(line)
            if m:
                cells = [c.strip() for c in m.group(1).split("|")]
                if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    continue
                rows.append(cells)
    if not found:
        r.warn("lesson-log", p, f"no '{log['headings'][0]}' section")
        return
    header, rows = (rows[0], rows[1:]) if rows else ([], [])
    col = next((i for i, h in enumerate(header) if h in log["effect_columns"]), None)
    if col is None:
        if isinstance(applied, int) and applied != len(rows):
            r.error("lesson-counts", p, f"applied is {applied} but the log has {len(rows)} row(s)")
        if rows or header:
            r.warn("lesson-log-effect", p, f"the log table has no '{log['effect_columns'][0]}' column; 'worked' cannot be checked")
        return
    values = log["effect_values"]
    for n, row in enumerate(rows, 1):
        cell = row[col] if col < len(row) else ""
        if cell not in values:
            r.error("lesson-log-effect", p, f"log row {n}: effect '{cell}' is not one of {sorted(k for k in values if not k.isascii())}")
    n_applied, yes, missed = tally(rows, col, values)
    if isinstance(applied, int) and applied != n_applied:
        r.error("lesson-counts", p, f"applied is {applied} but the log has {n_applied} applied row(s) (rows other than 'missed')")
    if isinstance(worked, int) and worked != yes:
        r.error("lesson-counts", p, f"worked is {worked} but the log has {yes} row(s) with effect 'yes'")
    m = fm.get("missed")
    if (m is not None or missed) and m != missed:
        r.error("lesson-counts", p, f"missed is {m} but the log has {missed} row(s) with effect 'missed'")


def tally(rows, col, values):
    """(applied, worked, missed): applied excludes rows where the lesson was not applied."""
    kinds = [values.get(row[col]) if col < len(row) else None for row in rows]
    missed = kinds.count("missed")
    return len(rows) - missed, kinds.count("yes"), missed


def check_template_log(r, p, body, schema):
    log = schema["application_log"]
    in_section = False
    for line in body.split("\n"):
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            in_section = h.group(2).strip() in log["headings"]
            continue
        m = TABLE_ROW.match(line) if in_section else None
        if m:
            header = [c.strip() for c in m.group(1).split("|")]
            if not any(c in log["effect_columns"] for c in header):
                r.error("template-log", p, f"the lesson template's log table has no '{log['effect_columns'][0]}' column; every lesson made from it will fail lint")
            return


def counts_from_log(body: str, schema) -> tuple[int, int] | None:
    """(applied, worked) from the application log, or None if the table has no effect column."""
    log = schema["application_log"]
    rows, in_section = [], False
    for line in body.split("\n"):
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            in_section = h.group(2).strip() in log["headings"]
            continue
        m = TABLE_ROW.match(line) if in_section else None
        if m:
            cells = [c.strip() for c in m.group(1).split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                rows.append(cells)
    if not rows:
        return None
    col = next((i for i, h in enumerate(rows[0]) if h in log["effect_columns"]), None)
    if col is None:
        return None
    return tally(rows[1:], col, log["effect_values"])


EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
TOKEN_QUERY = re.compile(r"https?://\S+?[?&](?:a|t|s|token|key|sig|signature|share|auth)=[A-Za-z0-9_\-]{6,}")


FILE_EXT = {"swift", "md", "png", "jpg", "jpeg", "svg", "gif", "json", "js", "ts", "py", "txt", "yml", "yaml",
            "plist", "kt", "java", "rb", "go", "rs", "c", "h", "m", "mm", "sh", "html", "css", "lock", "xcconfig"}


def check_privacy(r, p, text):
    for m in EMAIL.finditer(body_without_code(text)):
        if m.group(0).rsplit(".", 1)[-1].lower() in FILE_EXT:
            continue  # e.g. Package@swift-5.9.swift
        r.warn("privacy", p, f"looks like an e-mail address: {m.group(0)[:3]}…; the wiki keeps no personal data")
        break
    for m in TOKEN_QUERY.finditer(text):
        r.warn("privacy", p, f"URL carries a share or auth token: {m.group(0)[:40]}…; drop the query")
        break


def project_root_of(vault: Path) -> Path | None:
    import subprocess
    out = subprocess.run(["git", "-C", str(vault.parent), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    return Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None


def check_paths(r, p, fm, keys, project):
    for k in keys:
        for v in fm.get(k) or []:
            if not isinstance(v, str):
                continue
            s = v.strip().strip("`")
            if not s or re.match(r"^[a-z]+://", s) or s.startswith("[["):
                continue
            if s.startswith(("/", "~")):
                path = Path(s).expanduser()
            elif project and "/" in s and " " not in s.split("/")[0]:
                path = project / s
            else:
                continue
            if not path.exists():
                r.warn("evidence-path", p, f"{k}: '{s}' does not exist")


def check_encoded(r, p, fm, schema, memory_dirs):
    if not memory_dirs:
        return  # project or its memory folder unknown (e.g. a copied vault): nothing to check against
    v = fm.get("encoded_in")
    prefix = re.compile(rf"^\s*(?:{'|'.join(map(re.escape, schema['memory_prefixes']))})\s*:\s*(.*)$")
    other = re.compile(r"^\s*[^\s:]+\s*:")  # another target kind such as "skill: x"
    for part in (v if isinstance(v, list) else [v] if isinstance(v, str) else []):
        # "메모리: a, b; CLAUDE.md": after a memory prefix, comma items are memory names until ";"
        for group in (part or "").split(";"):
            items = group.split(",")
            m = prefix.match(items[0])
            if not m:
                continue
            names = [m.group(1)] + [x for x in items[1:] if not other.match(x)]
            for raw in names:
                name = raw.strip().removesuffix(".md")
                if not name or " " in name or "." in name or re.fullmatch(r"[A-Z][A-Z_]*", name):
                    continue  # a project file such as "CLAUDE.md" or "AGENTS.md", or prose
                if not any((d / f"{name}.md").is_file() for d in memory_dirs):
                    r.warn("encoded-target", p, f"encoded_in names memory '{name}', but no agent memory file has that name")


BASE_TOP = {"filters", "formulas", "properties", "summaries", "views"}
VIEW_KEYS = {"type", "name", "limit", "groupBy", "filters", "order", "summaries", "sort", "columnSize", "rowHeight", "image", "imageFit", "imageAspectRatio", "cardSize"}
VIEW_TYPES = {"table", "cards", "list", "map"}
FILE_PROPS = {"name", "basename", "path", "folder", "ext", "size", "ctime", "mtime", "tags", "links", "backlinks", "embeds", "properties", "file"}


def check_filter(r, p, f, where):
    if isinstance(f, str):
        if f.count("(") != f.count(")"):
            r.error("base-filter", p, f"{where}: unbalanced parentheses in {f!r}")
        if f.count('"') % 2:
            r.error("base-filter", p, f"{where}: unbalanced quotes in {f!r}")
        return
    if isinstance(f, dict) and len(f) == 1 and next(iter(f)) in ("and", "or", "not"):
        k, v = next(iter(f.items()))
        if not isinstance(v, list):
            r.error("base-filter", p, f"{where}.{k} must be a list")
            return
        for i, x in enumerate(v):
            check_filter(r, p, x, f"{where}.{k}[{i}]")
        return
    r.error("base-filter", p, f"{where}: a filter is a string or a map with exactly one of and/or/not")


def check_base(r, p, notes):
    try:
        doc = parse_yaml(p.read_text(encoding="utf-8"))
    except YamlError as e:
        r.error("base-yaml", p, str(e))
        return
    if not isinstance(doc, dict):
        r.error("base-yaml", p, "top level must be a map")
        return
    for k in doc:
        if k not in BASE_TOP:
            r.error("base-key", p, f"unknown top-level key '{k}'")
    formulas = doc.get("formulas") or {}
    if doc.get("filters") is not None:
        check_filter(r, p, doc["filters"], "filters")
    known = set()
    for fm, _, _ in notes.values():
        known.update((fm or {}).keys())

    def check_prop(prop, where):
        if not isinstance(prop, str):
            r.error("base-property", p, f"{where}: {prop!r} is not a property name")
        elif prop.startswith("formula."):
            if prop[8:] not in formulas:
                r.error("base-property", p, f"{where}: '{prop}' has no formula")
        elif prop.startswith("file."):
            if prop[5:] not in FILE_PROPS:
                r.warn("base-property", p, f"{where}: '{prop}' is not a known file property")
        elif prop.removeprefix("note.") not in known:
            r.warn("base-property", p, f"{where}: no note has property '{prop}'")

    for k in (doc.get("properties") or {}):
        check_prop(k, "properties")
    views = doc.get("views")
    if not isinstance(views, list) or not views:
        r.error("base-views", p, "'views' must be a non-empty list")
        return
    for i, v in enumerate(views):
        w = f"views[{i}]"
        if not isinstance(v, dict):
            r.error("base-views", p, f"{w} must be a map")
            continue
        w = f"view '{v.get('name', i)}'"
        for k in v:
            if k not in VIEW_KEYS:
                r.warn("base-view-key", p, f"{w}: unknown key '{k}'")
        if v.get("type") not in VIEW_TYPES:
            r.error("base-views", p, f"{w}: type '{v.get('type')}' is not one of {sorted(VIEW_TYPES)}")
        if not v.get("name"):
            r.error("base-views", p, f"{w}: 'name' is required")
        if v.get("filters") is not None:
            check_filter(r, p, v["filters"], f"{w}.filters")
        for prop in v.get("order") or []:
            check_prop(prop, f"{w}.order")
        g = v.get("groupBy")
        if g is not None:
            if not isinstance(g, dict) or "property" not in g:
                r.error("base-views", p, f"{w}.groupBy needs 'property'")
            else:
                check_prop(g["property"], f"{w}.groupBy")
        s = v.get("sort")
        if s is not None:
            if not isinstance(s, list):
                r.error("base-views", p, f"{w}.sort must be a list")
            else:
                for j, e in enumerate(s):
                    if not isinstance(e, dict) or "property" not in e:
                        r.error("base-views", p, f"{w}.sort[{j}] needs 'property'")
                        continue
                    check_prop(e["property"], f"{w}.sort")
                    if e.get("direction") not in (None, "ASC", "DESC"):
                        r.error("base-views", p, f"{w}.sort[{j}].direction must be ASC or DESC")


def fix_counts(vault: Path, schema) -> list[str]:
    fixed = []
    for p in walk(vault, schema):
        if p.suffix != ".md":
            continue
        text = p.read_text(encoding="utf-8")
        m = FM.match(text)
        if not m or not re.search(r"^type:\s*lesson\s*$", m.group(1), re.M):
            continue
        counts = counts_from_log(text[m.end():], schema)
        if counts is None:
            continue
        fm = m.group(1)
        new = fm
        for key, val in zip(("applied", "worked"), counts):
            new = re.sub(rf"^{key}:.*$", f"{key}: {val}", new, count=1, flags=re.M)
        if re.search(r"^missed:", new, re.M):
            new = re.sub(r"^missed:.*$", f"missed: {counts[2]}", new, count=1, flags=re.M)
        elif counts[2]:
            new = re.sub(r"^(worked:.*)$", rf"\1\nmissed: {counts[2]}", new, count=1, flags=re.M)
        if new != fm:
            p.write_text(text[: m.start(1)] + new + text[m.end(1):], encoding="utf-8")
            fixed.append(f"{p.relative_to(vault)}: applied={counts[0]} worked={counts[1]} missed={counts[2]}")
    return fixed


def summary(vault: Path, schema, since: str | None = None, stale_days: int = 30) -> dict:
    """Frontmatter-only numbers for a retro. Reads no note bodies except the inbox."""
    from datetime import timedelta
    today = date.today()
    out = {"episodes": {}, "lessons": {}, "eligible_for_adoption": [], "missed_often": [], "stale_candidates": [],
           "encoded_without_target": [], "inbox_lines": 0}
    tmpl = vault / (vault_config(vault).get("folders", {}).get("templates") or schema["template_folder"])
    for p in walk(vault, schema):
        if p.suffix != ".md" or p.is_relative_to(tmpl):
            continue
        text = p.read_text(encoding="utf-8")
        m = FM.match(text)
        try:
            fm = parse_yaml(m.group(1)) if m else {}
        except YamlError:
            continue
        t = fm.get("type")
        if t == "episode" and (not since or str(fm.get("date", "")) >= since):
            o = fm.get("outcome", "?")
            out["episodes"][o] = out["episodes"].get(o, 0) + 1
        elif t == "lesson":
            st = fm.get("status", "?")
            out["lessons"][st] = out["lessons"].get(st, 0) + 1
            w = fm.get("worked") if isinstance(fm.get("worked"), int) else 0
            if st == "candidate" and w >= schema["adopted_min_worked"]:
                out["eligible_for_adoption"].append({"lesson": p.stem, "applied": fm.get("applied"), "worked": w,
                                                     "audience": fm.get("audience")})
            ms = fm.get("missed") if isinstance(fm.get("missed"), int) else 0
            if st in ("candidate", "adopted") and ms >= schema["adopted_min_worked"]:
                out["missed_often"].append({"lesson": p.stem, "status": st, "missed": ms, "worked": w})
            ls = str(fm.get("last_seen", ""))
            if st == "candidate" and is_date(ls) and date.fromisoformat(ls) < today - timedelta(days=stale_days):
                out["stale_candidates"].append({"lesson": p.stem, "last_seen": ls})
            if st == "encoded" and not fm.get("encoded_in"):
                out["encoded_without_target"].append(p.stem)
        elif t == "inbox":
            out["inbox_lines"] += sum(1 for l in text.split("\n") if re.match(r"^- \d{4}-\d{2}-\d{2} ", l))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("vault")
    ap.add_argument("--schema")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--project", help="project root, when the vault is not inside it (e.g. a copy)")
    ap.add_argument("--summary", action="store_true", help="print retro numbers as JSON and exit")
    ap.add_argument("--since", help="with --summary: count episodes dated on or after YYYY-MM-DD")
    ap.add_argument("--fix-counts", action="store_true",
                    help="rewrite applied/worked in lesson frontmatter from the log table (the only write)")
    a = ap.parse_args(argv)
    vault = Path(a.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"not a directory: {vault}", file=sys.stderr)
        return 2
    schema, schema_path = load_schema(vault, a.schema)
    if a.summary:
        print(json.dumps(summary(vault, schema, a.since), ensure_ascii=False, indent=2))
        return 0
    if a.fix_counts:
        fixed = fix_counts(vault, schema)
        for f in fixed:
            print(f"fixed   {f}")
    rep = lint(vault, schema, Path(a.project).resolve() if a.project else None)
    errors = sum(1 for i in rep.items if i["level"] == "error")
    warnings = len(rep.items) - errors
    if a.json:
        print(json.dumps({"vault": str(vault), "schema": str(schema_path), "errors": errors,
                          "warnings": warnings, "findings": rep.items}, ensure_ascii=False, indent=2))
    else:
        for i in sorted(rep.items, key=lambda x: (x["level"] != "error", x["path"], x["rule"])):
            print(f"{i['level']:7} {i['rule']:18} {i['path']}: {i['message']}")
        print(f"\n{errors} error(s), {warnings} warning(s). schema: {schema_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
