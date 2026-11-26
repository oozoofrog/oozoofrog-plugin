#!/usr/bin/env python3
"""Rebuild the generated sections of the two guide notes from lesson frontmatter.

Usage: wiki_guides.py <vault> [--dry-run]

Each guide note has two generated sections; everything else in the note is kept:
  ## 원칙                 adopted lessons for this side: a link and the lesson's one-sentence summary
  ## 이미 규칙으로 옮긴 것  encoded lessons for this side: a link and where the rule lives (encoded_in)
The instruction guide takes audience user|both; the response guide takes agent|both.
A missing section is added at the end. Prints one JSON object.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from wiki_lint import FM, YamlError, load_schema, parse_yaml, vault_config, walk  # noqa: E402

GUIDES = {  # folder key -> (default file title, audiences)
    "instruction_guide": ("효과적인 지시 방법", {"user", "both"}),
    "response_guide": ("에이전트 대응 원칙", {"agent", "both"}),
}
ADOPTED, ENCODED = "원칙", "이미 규칙으로 옮긴 것"
ABSTRACT = re.compile(r"^>\s*\[!abstract\][^\n]*\n((?:>[^\n]*\n?)+)", re.M)


def one_sentence(body: str) -> str:
    m = ABSTRACT.search(body)
    if not m:
        return ""
    return " ".join(l.lstrip(">").strip() for l in m.group(1).splitlines()).strip()


def lessons(vault: Path, schema, tmpl: Path):
    out = []
    for p in walk(vault, schema):
        if p.suffix != ".md" or p.is_relative_to(tmpl):
            continue
        text = p.read_text(encoding="utf-8")
        m = FM.match(text)
        if not m:
            continue
        try:
            fm = parse_yaml(m.group(1))
        except YamlError:
            continue
        if isinstance(fm, dict) and fm.get("type") == "lesson":
            out.append((p.stem, fm, one_sentence(text[m.end():])))
    return sorted(out, key=lambda x: x[0])


def replace_section(text: str, heading: str, lines: list[str]) -> str:
    """Replace the list in a section. Text above the first list line (an intro) is kept."""
    pat = re.compile(rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", re.S | re.M)
    m = pat.search(text)
    intro = ""
    if m:
        old = m.group(1)
        first = re.search(r"^(- |아직 )", old, re.M)
        intro = old[: first.start()] if first else old
        intro = intro.rstrip("\n") + "\n\n" if intro.strip() else ""
    block = f"## {heading}\n{intro}" + ("\n".join(lines) if lines else "아직 없다.") + "\n"
    if m:
        return (text[: m.start()] + block + "\n" + text[m.end():]).rstrip("\n") + "\n"
    return text.rstrip("\n") + "\n\n" + block


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("vault")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    vault = Path(a.vault).expanduser().resolve()
    schema, _ = load_schema(vault, None)
    folders = vault_config(vault).get("folders", {})
    tmpl = vault / (folders.get("templates") or schema["template_folder"])
    all_lessons = lessons(vault, schema, tmpl)
    result = {"ok": True, "guides": []}
    for key, (title, audiences) in GUIDES.items():
        folder = folders.get(key)
        path = vault / folder / f"{title}.md" if folder else next(iter(vault.rglob(f"{title}.md")), None)
        if path is None or not path.is_file():
            result["guides"].append({"guide": title, "skipped": "note not found"})
            continue
        mine = [(n, fm, s) for n, fm, s in all_lessons if fm.get("audience") in audiences]
        adopted = [f"- [[{n}]] — {s or '(한 문장 요약 없음)'}" for n, fm, s in mine if fm.get("status") == "adopted"]
        encoded = [f"- [[{n}]] — 옮긴 곳: {fm.get('encoded_in') or '(없음)'}" for n, fm, s in mine if fm.get("status") == "encoded"]
        old = path.read_text(encoding="utf-8")
        new = replace_section(replace_section(old, ADOPTED, adopted), ENCODED, encoded)
        changed = new != old
        if changed and not a.dry_run:
            path.write_text(new, encoding="utf-8")
        result["guides"].append({"guide": str(path.relative_to(vault)), "adopted": len(adopted),
                                 "encoded": len(encoded), "changed": changed})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
