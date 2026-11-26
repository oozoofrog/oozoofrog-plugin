"""Read or replace fstack role choices for one host profile."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROLES = (
    "feature, refactoring", "bug-fix", "perf-issue", "hillclimb",
    "judgment and prose", "arena runners", "arena cross-judge pool",
    "swarm workers", "interrogate reviewers",
)
PANELS = {"arena runners", "arena cross-judge pool", "interrogate reviewers"}


def settings_path(host):
    override = os.environ.get("FSTACK_MODELS")
    if override:
        return Path(override).expanduser()
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config / "fstack" / (host + ".json")


def validate(data):
    if not isinstance(data, dict) or set(data) != {"budget", "roles"}:
        raise ValueError("expected an object with budget and roles")
    if data["budget"] not in ("small", "medium", "large"):
        raise ValueError("budget must be small, medium or large")
    if not isinstance(data["roles"], dict):
        raise ValueError("roles must be an object")
    for role, choices in data["roles"].items():
        if role not in ROLES or not isinstance(choices, list) or not choices:
            raise ValueError(f"invalid role or empty choices: {role}")
        if role not in PANELS and len(choices) != 1:
            raise ValueError(f"{role} takes exactly one model")
        for choice in choices:
            if not isinstance(choice, str) or not choice.strip() or choice.strip() != choice or not choice.isprintable():
                raise ValueError(f"invalid model for {role}")
    return data


def read_settings(host, path):
    if path.exists():
        return validate(json.loads(path.read_text(encoding="utf-8")))
    data = {"budget": "large", "roles": {}}
    legacy = {"cursor": ".cursor/rules/pstack-models.mdc",
              "claude": ".claude/rules/pstack-models.md"}.get(host)
    if legacy:
        rule = Path.home() / legacy
        if rule.is_file():
            for line in rule.read_text(encoding="utf-8").splitlines():
                key, sep, value = line.partition(":")
                if key == "# budget" and value.strip():
                    data["budget"] = value.split()[0]
                    if data["budget"] == "unlimited":
                        data["budget"] = "large"
                if sep and key in ROLES:
                    data["roles"][key] = [part.strip() for part in value.split(",")]
    return validate(data)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("cursor", "claude", "codex", "t3", "other"), required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("show")
    commands.add_parser("save")
    commands.add_parser("role").add_argument("name", choices=ROLES)
    args = parser.parse_args()
    path = settings_path(args.host)
    if args.command == "save":
        save(path, validate(json.load(sys.stdin)))
        print(path)
        return
    data = read_settings(args.host, path)
    if args.command == "role":
        data = {"budget": data["budget"], "choices": data["roles"].get(args.name, ["inherit-parent"])}
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        sys.exit(str(error))
