"""Publish a prepared reading kit as a self-contained personal Codex skill."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile


def quoted(value):
    return json.dumps(value, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--references", type=Path, help="Reviewed folder containing INDEX.md")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.name) or len(args.name) > 64:
        parser.error("Use a lowercase, hyphenated skill name of at most 64 characters.")
    title = args.title.strip()
    if not title or not title.isprintable():
        parser.error("Provide the book title on one line.")
    with args.source.open("rb") as source:
        digest = streaming_digest(source)
    marker = f"<!-- source-sha256: {digest} -->"
    target = args.parent / args.name
    if target.exists() or target.is_symlink():
        skill = target / "SKILL.md"
        if skill.is_file() and marker in skill.read_text().splitlines() and (target / "references/INDEX.md").is_file():
            print(f"Existing coach for this source: {target}")
            return
        parser.error(f"Destination belongs to another edition or is incomplete: {target}")
    if args.references is None:
        print(f"New source. Prepare references for {target}")
        return
    refs = args.references.resolve()
    index = refs / "INDEX.md"
    if not index.is_file() or not index.read_text().strip():
        parser.error("The reviewed references need a nonempty INDEX.md.")
    if target.resolve().is_relative_to(refs):
        parser.error("The destination must be outside the references directory.")
    body = (Path(__file__).resolve().parents[1] / "assets/coaching.md").read_text()
    description = f"Use for reading, discussing, or applying 《{title}》 with this book’s personal reading coach."
    args.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.parent, prefix=".prepare-coach-") as temporary:
        staged = Path(temporary) / args.name
        shutil.copytree(refs, staged / "references")
        (staged / "SKILL.md").write_text(
            f"---\nname: {args.name}\ndescription: {quoted(description)}\n---\n\n"
            f"# {title} 책 읽기 코치\n\n{marker}\n\n{body}"
        )
        ui = staged / "agents"
        ui.mkdir()
        (ui / "openai.yaml").write_text(
            f"interface:\n  display_name: {quoted(title + ' 책 읽기 코치')}\n"
            '  short_description: "관심사에 맞춰 책을 읽고 업무와 삶에서 작은 실험으로 이어갑니다."\n'
            f"  default_prompt: {quoted('$' + args.name + ' 지금 궁금한 것에서 읽기를 시작하고 싶어요.')}\n"
        )
        staged.rename(target)
    print(f"Created {target}")


def streaming_digest(source):
    digest = hashlib.sha256()
    for block in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
