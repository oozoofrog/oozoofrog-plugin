import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


NAME = "wild-reading-coach-builder"
BUILDER = Path(__file__).resolve().parents[2] / "plugins" / NAME / "skills" / NAME


class ReadingCoachBuilderTests(unittest.TestCase):
    def test_publish_and_revisit_an_edition(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "book.md"
            source.write_text("# Observation\nRecord the time of each sighting.\n", encoding="utf-8")
            refs = workspace / "reviewed"
            refs.mkdir()
            index = "[Observation](observation.md)\n"
            (refs / "INDEX.md").write_text(index, encoding="utf-8")
            (refs / "observation.md").write_bytes(source.read_bytes())

            parent = workspace / "coaches"
            target = parent / "observation-coach"
            probe = [
                sys.executable, "-X", "utf8", str(BUILDER / "scripts/make_coach.py"),
                "--source", str(source), "--title", "Observation", "--name", target.name,
                "--parent", str(parent),
            ]
            subprocess.run(probe, cwd=workspace, check=True, capture_output=True)
            self.assertFalse(parent.exists())
            publish = [*probe, "--references", str(refs)]
            subprocess.run(publish, cwd=workspace, check=True, capture_output=True)
            self.assertEqual(index, (target / "references/INDEX.md").read_text(encoding="utf-8"))
            self.assertEqual(source.read_bytes(), (target / "references/observation.md").read_bytes())
            self.assertIn((BUILDER / "assets/coaching.md").read_text(encoding="utf-8"),
                          (target / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("$observation-coach", (target / "agents/openai.yaml").read_text(encoding="utf-8"))

            profile = target / "PROFILE.md"
            profile.write_bytes(b"Read section one.\n")
            subprocess.run(publish, cwd=workspace, check=True, capture_output=True)
            source.write_bytes(b"A revised edition.\n")
            result = subprocess.run(publish, cwd=workspace, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"another edition", result.stderr)
            self.assertEqual(b"Read section one.\n", profile.read_bytes())


class CoachingTextContractTests(unittest.TestCase):
    """Each test proves that an instruction is present. It does not prove coach behavior."""

    def assertCoaching(self, *phrases):
        text = " ".join((BUILDER / "assets/coaching.md").read_text(encoding="utf-8").lower().split())
        for phrase in phrases:
            self.assertIn(phrase, text)

    def test_ac1_1_one_page_file_in_the_coach_directory(self):
        self.assertCoaching("one file named experiment.html in the real directory that contains this skill.md",
                            "never in references", "overwrite the earlier file", "tell the reader the full path")

    def test_ac1_2_page_is_self_contained_and_stores_nothing(self):
        self.assertCoaching("single self-contained file", "no network requests",
                            "no localstorage, sessionstorage, indexeddb, or cookies")

    def test_ac1_3_page_shows_no_book_text_or_metrics(self):
        self.assertCoaching("must not contain book text, figures, links to passage files, "
                            "a completion percentage, time spent, a streak, or a count of items read")

    def test_ac1_4_new_experiment_view(self):
        self.assertCoaching("two or three verified entry points", "let the reader select one",
                            "the action, the predicted result, and the date to check, which may stay empty")

    def test_ac1_5_handoff_block_is_copied_by_hand(self):
        self.assertCoaching("plain-text block from the selected locator and the three fields",
                            "select and copy it by hand")

    def test_ac1_6_page_states_that_it_saves_nothing(self):
        self.assertCoaching("the page saves nothing and that a reload erases text that was not copied",
                            "write it in the reader’s language")

    def test_ac1_7_comparison_view(self):
        self.assertCoaching("the prediction and the result side by side with their dates",
                            "not in input fields", "escape the reader’s text")

    def test_ac1_8_page_only_on_request(self):
        self.assertCoaching("create the page only when the reader asks for it", "all coaching works without it",
                            "accept it from a message or from a block pasted from the experiment page")

    def test_ac1_9_page_is_never_published(self):
        self.assertCoaching("never publish, host, or upload the page or its content")

    def test_ac2_1_experiment_entry_format(self):
        self.assertCoaching("### e<n> · <date recorded>", "- prediction: <reader’s exact words>",
                            "one more than the last key")

    def test_ac2_2_result_joins_its_entry(self):
        self.assertCoaching("- result (<date reported>): <reader’s exact words>",
                            "if more than one entry has no result and the reader does not say which, ask")

    def test_ac2_3_recorded_wording_is_never_changed(self):
        self.assertCoaching("never change the recorded wording of a prediction or a result",
                            "add a dated correction line and keep the original")

    def test_ac2_4_page_use_is_never_confirmed_reading(self):
        self.assertCoaching("anything done on the page is never confirmed reading")

    def test_ac2_5_page_is_rebuilt_from_the_profile(self):
        self.assertCoaching("rebuild it from profile.md alone")

    def test_ac2_6_result_without_prediction(self):
        self.assertCoaching("record the result alone", "never write a prediction for the reader")

    def test_ac2_7_next_question_quotes_both(self):
        self.assertCoaching("quote the prediction and the result in the conversation",
                            "do this with or without the page")

    def test_ac3_1_page_is_optional(self):
        self.assertCoaching("routine coaching needs only these local markdown files and their linked images",
                            "the experiment page is optional")

    def test_ac3_6_published_coach_has_the_page_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = workspace / "book.md"
            source.write_text("# Observation\n", encoding="utf-8")
            refs = workspace / "reviewed"
            refs.mkdir()
            (refs / "INDEX.md").write_text("[Observation](observation.md)\n", encoding="utf-8")
            subprocess.run([
                sys.executable, "-X", "utf8", str(BUILDER / "scripts/make_coach.py"),
                "--source", str(source), "--title", "Observation", "--name", "observation-coach",
                "--parent", str(workspace / "coaches"), "--references", str(refs),
            ], cwd=workspace, check=True, capture_output=True)
            published = (workspace / "coaches/observation-coach/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("experiment.html", published)


class BuilderInstructionTests(unittest.TestCase):
    def assertBuilder(self, *phrases):
        text = " ".join((BUILDER / "SKILL.md").read_text(encoding="utf-8").lower().split())
        for phrase in phrases:
            self.assertIn(phrase, text)

    def test_ac3_2_check_includes_the_page_loop(self):
        self.assertBuilder("a return visit, and the experiment page loop against this book",
                           "the page holds no book text", "page use adds no confirmed reading")

    def test_ac3_10_update_command_for_an_existing_coach(self):
        self.assertBuilder("run the same command with `--update-coaching`", "skill.md.previous",
                           "leaves the references and profile.md unchanged")


class UpdateCoachingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.workspace = Path(directory.name)
        self.source = self.workspace / "book.md"
        self.source.write_text("# Observation\n", encoding="utf-8")
        refs = self.workspace / "reviewed"
        refs.mkdir()
        (refs / "INDEX.md").write_text("[Observation](observation.md)\n", encoding="utf-8")
        self.parent = self.workspace / "coaches"
        self.target = self.parent / "observation-coach"
        self.run_script("--references", str(refs))
        self.skill = self.target / "SKILL.md"
        self.current = self.skill.read_text(encoding="utf-8")
        body = (BUILDER / "assets/coaching.md").read_text(encoding="utf-8")
        self.earlier = self.current[: -len(body)] + "Earlier instructions.\n"
        self.skill.write_text(self.earlier, encoding="utf-8")
        (self.target / "PROFILE.md").write_text("### E1 · 2026-11-24\n", encoding="utf-8")
        (self.target / "experiment.html").write_text("<!doctype html>", encoding="utf-8")

    def run_script(self, *extra, source=None, name="observation-coach"):
        return subprocess.run([
            sys.executable, "-X", "utf8", str(BUILDER / "scripts/make_coach.py"),
            "--source", str(source or self.source), "--title", "Observation", "--name", name,
            "--parent", str(self.parent), *extra,
        ], cwd=self.workspace, capture_output=True, text=True)

    def files(self, *excluded):
        return {str(path.relative_to(self.target)): path.read_bytes()
                for path in self.target.rglob("*") if path.is_file() and path.name not in excluded}

    def test_ac3_7_update_replaces_only_the_instructions(self):
        before = self.files("SKILL.md")
        result = self.run_script("--update-coaching")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(self.current, self.skill.read_text(encoding="utf-8"))
        self.assertEqual(before, self.files("SKILL.md", "SKILL.md.previous"))

    def test_ac3_8_update_keeps_the_earlier_file_and_is_idempotent(self):
        self.assertEqual(0, self.run_script("--update-coaching").returncode)
        previous = self.target / "SKILL.md.previous"
        self.assertEqual(self.earlier, previous.read_text(encoding="utf-8"))
        before = self.files()
        result = self.run_script("--update-coaching")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("already current", result.stdout)
        self.assertEqual(before, self.files())

    def test_ac3_9_update_refuses_a_missing_or_foreign_destination(self):
        before = self.files()
        self.assertEqual(0, self.run_script().returncode)
        self.assertEqual(before, self.files())
        missing = self.run_script("--update-coaching", name="absent-coach")
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("No coach to update", missing.stderr)
        self.assertFalse((self.parent / "absent-coach").exists())
        other = self.workspace / "other.md"
        other.write_text("# Another book\n", encoding="utf-8")
        foreign = self.run_script("--update-coaching", source=other)
        self.assertNotEqual(0, foreign.returncode)
        self.assertIn("another edition", foreign.stderr)
        self.assertEqual(before, self.files())


class DistributionTests(unittest.TestCase):
    def test_ac3_3_release_describes_the_experiment_page(self):
        root = BUILDER.parents[3]
        for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            self.assertIn('"version": "0.2.0"', (BUILDER.parents[1] / manifest).read_text(encoding="utf-8"))
        self.assertIn("`wild-reading-coach-builder` 0.2.0", (root / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn("experiment page", (root / "README.md").read_text(encoding="utf-8"))
        self.assertIn("실험 페이지", (root / "README.ko.md").read_text(encoding="utf-8"))
