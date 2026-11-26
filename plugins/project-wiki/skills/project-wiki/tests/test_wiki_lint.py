import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import wiki_lint  # noqa: E402

LESSON = """---
type: lesson
audience: both
kind: process
status: {status}
basis: success
first_seen: 2026-11-26
last_seen: 2026-11-26
applied: {applied}
worked: {worked}
encoded_in: "{encoded_in}"
episodes:
  - "[[2026-11-26 Episode]]"
aliases:
  - Short name
---

# Lesson

## 적용 기록
| 날짜 | 작업 기록 | 효과 | 내용 |
|---|---|---|---|
{rows}
"""

EPISODE = """---
type: episode
date: 2026-11-26
request: "do it"
outcome: {outcome}
mode: main-session
lessons:
  - "[[Measure first]]"
---

# Episode

See [[Measure first]] and `[[not a link]]`.

```
[[also not a link]]
```
"""

BASE = """filters:
  and:
    - 'type == "lesson"'
formulas:
  rate: 'worked / applied'
views:
  - type: table
    name: "All"
    sort:
      - property: applied
        direction: DESC
    order:
      - file.name
      - formula.rate
      - status
"""


class LintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for d in ("00 대시보드", "10 작업 기록", "20 교훈", "90 템플릿"):
            (self.root / d).mkdir()
        self.lesson()
        self.episode()
        (self.root / "00 대시보드" / "교훈.base").write_text(BASE, encoding="utf-8")
        (self.root / "90 템플릿" / "t.md").write_text("---\ntype: lesson\nfirst_seen: {{date}}\n---\n[[nowhere]]\n", encoding="utf-8")
        self.schema = wiki_lint.load_schema(self.root, None)[0]

    def tearDown(self):
        self.tmp.cleanup()

    def lesson(self, name="Measure first", status="candidate", applied=1, worked=1, encoded_in="",
               rows="| 2026-11-26 | [[2026-11-26 Episode]] | 있음 | 잘 됨 |"):
        (self.root / "20 교훈" / f"{name}.md").write_text(
            LESSON.format(status=status, applied=applied, worked=worked, encoded_in=encoded_in, rows=rows),
            encoding="utf-8")

    def episode(self, outcome="success", extra=""):
        (self.root / "10 작업 기록" / "2026-11-26 Episode.md").write_text(
            EPISODE.format(outcome=outcome) + extra, encoding="utf-8")

    def rules(self, level="error"):
        rep = wiki_lint.lint(self.root, self.schema)
        return sorted(i["rule"] for i in rep.items if i["level"] == level)

    def test_clean_vault_passes(self):
        self.assertEqual(self.rules(), [])
        self.assertEqual(self.rules("warning"), [])

    def test_enum_and_missing_field(self):
        self.episode(outcome="done")
        self.assertIn("field-enum", self.rules())

    def test_counter_drift(self):
        self.lesson(applied=0, worked=0)
        self.assertEqual(self.rules(), ["lesson-counts", "lesson-counts"])
        self.lesson(applied=1, worked=0)
        self.assertEqual(self.rules(), ["lesson-counts"])

    def test_effect_value_must_be_closed_set(self):
        self.lesson(rows="| 2026-11-26 | [[2026-11-26 Episode]] | 대체로 | 3건 모두 잡힘 |")
        self.assertIn("lesson-log-effect", self.rules())

    def test_unknown_effect_does_not_count(self):
        self.lesson(applied=2, worked=1, rows="| 2026-11-26 | [[2026-11-26 Episode]] | 있음 | a |\n| 2026-11-27 | [[2026-11-26 Episode]] | 모름 | b |")
        self.assertEqual(self.rules(), [])

    def test_old_table_without_effect_column_warns(self):
        (self.root / "20 교훈" / "Measure first.md").write_text(
            LESSON.replace("| 효과 | 내용 |", "| 결과 |").replace("|---|---|---|---|", "|---|---|---|").format(
                status="candidate", applied=1, worked=1, encoded_in="", rows="| 2026-11-26 | [[2026-11-26 Episode]] | 좋음 |"),
            encoding="utf-8")
        self.assertEqual(self.rules(), [])
        self.assertEqual(self.rules("warning"), ["lesson-log-effect"])

    def test_fix_counts(self):
        self.lesson(applied=0, worked=5)
        fixed = wiki_lint.fix_counts(self.root, self.schema)
        self.assertEqual(len(fixed), 1)
        self.assertEqual(self.rules(), [])
        self.assertEqual(wiki_lint.fix_counts(self.root, self.schema), [])

    def test_embedded_base_view_must_exist(self):
        self.episode(extra="\n![[교훈.base#All]]\n![[교훈.base#Missing]]\n")
        self.assertEqual(self.rules(), ["base-embed-view"])

    def test_evidence_path(self):
        self.episode(extra="")
        text = (self.root / "10 작업 기록" / "2026-11-26 Episode.md").read_text(encoding="utf-8")
        text = text.replace("lessons:", f"evidence:\n  - {self.root}/missing/report.md\n  - {self.root}/20 교훈\n  - https://example.com/x\nlessons:")
        (self.root / "10 작업 기록" / "2026-11-26 Episode.md").write_text(text, encoding="utf-8")
        self.assertEqual(self.rules(), [])
        self.assertEqual(self.rules("warning"), ["evidence-path"])

    def test_privacy(self):
        self.episode(extra="\nmail person@example.com and https://x.com/i/status/1?s=abcdefgh12\nPackage@swift-5.9.swift and `a@b.com`\n")
        self.assertEqual(self.rules("warning"), ["privacy", "privacy"])

    def test_encoded_memory_target(self):
        self.lesson(status="encoded", encoded_in="메모리: no-such-memory-file-xyz")
        self.assertEqual(self.rules(), [])

    def test_encoded_needs_target(self):
        self.lesson(status="encoded")
        self.assertIn("lesson-encoded", self.rules())

    def test_alias_only_link(self):
        self.episode(extra="\n[[Short name]]\n")
        self.assertEqual(self.rules(), ["link-alias-only"])

    def test_broken_link_ignores_code(self):
        self.episode(extra="\n[[Missing note|label]]\n")
        self.assertEqual(self.rules(), ["link-broken"])

    def test_slash_in_title_splits_folder(self):
        nested = self.root / "20 교훈" / "백그라운드 I"
        nested.mkdir()
        (nested / "O를 늘린다.md").write_text(
            LESSON.format(status="candidate", applied=0, worked=0, encoded_in="", rows=""), encoding="utf-8")
        self.assertIn("nested-note", self.rules())

    def test_forbidden_title_char(self):
        (self.root / "20 교훈" / "A#B.md").write_text(
            LESSON.format(status="candidate", applied=0, worked=0, encoded_in="", rows=""), encoding="utf-8")
        self.assertIn("title-chars", self.rules())

    def test_backlink_warning(self):
        self.lesson(name="Other")
        (self.root / "20 교훈" / "Measure first.md").unlink()
        self.episode()
        rules = self.rules()
        self.assertIn("link-broken", rules)
        self.assertIn("backlink", self.rules("warning"))

    def test_base_errors(self):
        bad = BASE.replace("formula.rate", "formula.missing").replace("type: table", "type: grid")
        (self.root / "00 대시보드" / "교훈.base").write_text(bad + "extra: 1\n", encoding="utf-8")
        self.assertEqual(self.rules(), ["base-key", "base-property", "base-views"])

    def test_base_yaml_error(self):
        (self.root / "00 대시보드" / "교훈.base").write_text("views:\n  - type: table\n     name: x\n", encoding="utf-8")
        self.assertEqual(self.rules(), ["base-yaml"])

    def test_outdated_lesson_template(self):
        (self.root / "90 템플릿" / "교훈 템플릿.md").write_text(
            "---\ntype: lesson\nfirst_seen: {{date}}\n---\n\n## 적용 기록\n| 날짜 | 작업 기록 | 결과 |\n|---|---|---|\n", encoding="utf-8")
        self.assertEqual(self.rules(), ["template-log"])

    def test_bundled_vault_is_clean(self):
        import shutil
        bundled = Path(__file__).resolve().parents[1] / "assets" / "vault" / "ko"
        target = self.root / "bundled"
        shutil.copytree(bundled, target)
        rep = wiki_lint.lint(target, self.schema)
        self.assertEqual([], [i for i in rep.items if i["level"] == "error"])

    def test_missed_rows(self):
        rows = ("| 2026-11-26 | [[2026-11-26 Episode]] | 있음 | a |\n"
                "| 2026-11-27 | [[2026-11-26 Episode]] | 미적용 | b |\n"
                "| 2026-11-28 | [[2026-11-26 Episode]] | 미적용 | c |")
        self.lesson(applied=3, worked=1, rows=rows)
        self.assertEqual(self.rules(), ["lesson-counts", "lesson-counts"])  # applied and missed
        fixed = wiki_lint.fix_counts(self.root, self.schema)
        self.assertIn("applied=1 worked=1 missed=2", fixed[0])
        self.assertEqual(self.rules(), [])
        s = wiki_lint.summary(self.root, self.schema)
        self.assertEqual(["Measure first"], [x["lesson"] for x in s["missed_often"]])

    def test_guides_generated_sections(self):
        import subprocess
        g = self.root / "40 대응 가이드"
        g.mkdir()
        (g / "에이전트 대응 원칙.md").write_text("---\ntype: guide\n---\n\n# 에이전트 대응 원칙\n\n머리말\n\n## 원칙\n소개 문단\n\n- 오래된 줄\n\n## 교훈 목록\n유지\n", encoding="utf-8")
        text = (self.root / "20 교훈" / "Measure first.md").read_text(encoding="utf-8")
        (self.root / "20 교훈" / "Measure first.md").write_text(
            text.replace("status: candidate", "status: adopted").replace("# Lesson\n", "# Lesson\n\n> [!abstract] 한 문장\n> 먼저 잰다.\n"), encoding="utf-8")
        script = Path(wiki_lint.__file__).with_name("wiki_guides.py")
        out = subprocess.run([sys.executable, "-I", "-B", str(script), str(self.root)], capture_output=True, text=True, check=True)
        self.assertIn('"adopted": 1', out.stdout)
        guide = (g / "에이전트 대응 원칙.md").read_text(encoding="utf-8")
        self.assertIn("- [[Measure first]] — 먼저 잰다.", guide)
        self.assertNotIn("오래된 줄", guide)
        self.assertIn("머리말", guide)
        self.assertIn("## 원칙\n소개 문단\n\n- [[Measure first]]", guide)
        self.assertIn("## 교훈 목록\n유지", guide)
        self.assertIn("## 이미 규칙으로 옮긴 것\n아직 없다.", guide)
        again = subprocess.run([sys.executable, "-I", "-B", str(script), str(self.root)], capture_output=True, text=True, check=True)
        self.assertIn('"changed": false', again.stdout)

    def test_encoded_memory_list(self):
        mem = self.root / "mem"
        mem.mkdir()
        (mem / "a.md").write_text("x", encoding="utf-8")
        rep = wiki_lint.Report(self.root)
        p = self.root / "20 교훈" / "Measure first.md"
        wiki_lint.check_encoded(rep, p, {"encoded_in": "메모리: a, b, CLAUDE.md; AGENTS.md, skill: x"}, self.schema, [mem])
        self.assertEqual(["encoded_in names memory 'b', but no agent memory file has that name"], [i["message"] for i in rep.items])

    def test_summary_skips_templates(self):
        (self.root / "90 템플릿" / "작업 기록 템플릿.md").write_text(
            "---\ntype: episode\ndate: {{date}}\noutcome: in-progress\n---\n", encoding="utf-8")
        (self.root / "10 작업 기록" / "2026-11-26 Episode.md").unlink()
        s = wiki_lint.summary(self.root, self.schema)
        self.assertEqual({}, s["episodes"])
        self.assertEqual({"candidate": 1}, s["lessons"])

    def test_duplicate_episode_warns(self):
        text = (self.root / "10 작업 기록" / "2026-11-26 Episode.md").read_text(encoding="utf-8")
        (self.root / "10 작업 기록" / "2026-11-26 Episode again.md").write_text(text, encoding="utf-8")
        self.assertEqual(1, self.rules("warning").count("episode-duplicate"))

    def test_bad_filter(self):
        (self.root / "00 대시보드" / "교훈.base").write_text(
            BASE.replace("  and:\n", "  and:\n").replace("filters:\n  and:", "filters:\n  both:"), encoding="utf-8")
        self.assertIn("base-filter", self.rules())


if __name__ == "__main__":
    unittest.main()
