"""Keep the procedure executable against the CLI it documents."""
import argparse
import json
from pathlib import Path
import re
import shlex
import sys
import unittest
from urllib.parse import unquote, urlsplit


SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from graphflow import cli


DOCUMENTS = [SKILL / "SKILL.md"] + [
    SKILL / "references" / (name + ".md")
    for name in ("leader", "worker", "executors")
]
PENDING_LINKS = {
    SKILL / "references" / "mcp.md",
    SKILL / "references" / "dashboard.md",
}
CODE = re.compile(
    r"^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n"
    r"(?P<block>.*?)^[ \t]*(?P=fence)[ \t]*$"
    r"|(?P<ticks>`+)(?P<span>.*?)(?P=ticks)",
    re.MULTILINE | re.DOTALL,
)


def command_examples(markdown):
    """Read code spans/fences, including shell prefixes and chained commands."""
    for match in CODE.finditer(markdown):
        code = match.group("block") if match.group("fence") else match.group("span")
        for line in code.replace("\\\n", " ").splitlines():
            lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|")
            lexer.whitespace_split = True
            tokens = list(lexer)
            for index, token in enumerate(tokens):
                if token != "gf" and not token.endswith("/gf"):
                    continue
                arguments = []
                for argument in tokens[index + 1:]:
                    if argument and all(char in ";&|" for char in argument):
                        break
                    arguments.append(argument)
                if arguments:
                    yield arguments


def command_options():
    """Discover command parsers and inherited options, without a copied registry."""
    result = {}

    def visit(parser, path=(), inherited=frozenset()):
        options = inherited | set(parser._option_string_actions)
        if path in cli.COMMANDS:
            result[path] = options
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    visit(child, path + (name,), options)

    visit(cli._parser())
    return result


def validate_command(arguments, options):
    identity, _ = cli._parser(authorize_only=True).parse_known_args(arguments)
    path = identity.command_path
    if path not in cli.COMMANDS:
        raise ValueError("Unknown command: " + " ".join(path))
    for argument in arguments:
        if re.match(r"^--[a-zA-Z][a-zA-Z0-9-]*(?:=|$)", argument):
            option = argument.split("=", 1)[0]
            if option not in options[path]:
                raise ValueError("Unknown option %s for %s" % (option, " ".join(path)))
    return path


class DocumentationCommandsTests(unittest.TestCase):
    def test_commands_options_and_registry_coverage(self):
        options = command_options()
        self.assertEqual(set(options), set(cli.COMMANDS))
        mentioned = set()
        for document in DOCUMENTS:
            examples = list(command_examples(document.read_text(encoding="utf-8")))
            self.assertTrue(examples, str(document))
            for arguments in examples:
                with self.subTest(document=document.name, command=arguments):
                    mentioned.add(validate_command(arguments, options))
        required = set(cli.COMMANDS) - {("mcp",), ("serve",)}
        self.assertFalse(required - mentioned, "Undocumented commands: %r" % (required - mentioned))

    def test_extraction_covers_spans_fences_and_shell_commands(self):
        sample = (
            "Prose gf ignored. `gf status` and ``gf brief --plan``.\n\n"
            "```sh\npython3 -B scripts/gf --json ready; gf trace\n```\n\n"
            "~~~sh\ngf assign node \\\n  --executor subagent\n~~~\n"
        )
        self.assertEqual(list(command_examples(sample)), [
            ["status"], ["brief", "--plan"], ["--json", "ready"], ["trace"],
            ["assign", "node", "--executor", "subagent"],
        ])

    def test_unknown_paths_and_options_fail(self):
        options = command_options()
        for arguments in (["nonexistent"], ["plan", "nonexistent"],
                          ["gate", "node", "--nonexistent"],
                          ["status", "--commit", "sha"]):
            with self.subTest(command=arguments), self.assertRaises((ValueError, cli.core.GFError)):
                validate_command(arguments, options)

    def test_relative_markdown_links_resolve(self):
        for document in DOCUMENTS:
            markdown = CODE.sub("", document.read_text(encoding="utf-8"))
            destinations = re.findall(r"\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)", markdown)
            # Include reference-style definitions as well as inline links.
            destinations += re.findall(r"^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)", markdown, re.MULTILINE)
            for destination in destinations:
                url = urlsplit(destination.strip("<>"))
                if url.scheme or url.netloc or not url.path:
                    continue
                with self.subTest(document=document.name, link=destination):
                    self.assertFalse(Path(url.path).is_absolute(), "Use relative documentation links")
                    target = (document.parent / unquote(url.path)).resolve()
                    if target in PENDING_LINKS and not target.exists():
                        continue
                    self.assertTrue(target.exists(), "Broken link: %s" % target)

    def test_skill_description_matches_plugin(self):
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        frontmatter, body = skill_text.split("---", 2)[1:]
        description = re.search(r"^description: (.+)$", frontmatter, re.MULTILINE)
        self.assertIsNotNone(description)
        manifest = json.loads((SKILL.parents[1] / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(description.group(1), manifest["description"])
        self.assertLessEqual(len(body.strip().splitlines()), 90)


if __name__ == "__main__":
    unittest.main()
