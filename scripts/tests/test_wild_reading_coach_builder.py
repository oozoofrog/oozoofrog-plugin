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
