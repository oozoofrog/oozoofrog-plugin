"""Run from the skill folder: python3 -I -B -m unittest discover -s tests -v

Set HANDOFF_TEST_TMP to choose where temporary git repositories are created."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import ctxlib  # noqa: E402

TMP_BASE = os.environ.get("HANDOFF_TEST_TMP")

HANDOFF = """---
status: active
branch: main
head: {head}
updated: 2026-11-11T10:00:00+09:00
session_id: sess-a
goal: 결제 모듈 재시도 로직 정리
---

# 인계: 결제 재시도

## 진행 중
BODY_ONLY_MARKER 재시도 간격 조정

## 다음 할 일
- RetryPolicy 테스트 추가
"""


def sh(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *args],
                          capture_output=True, text=True, check=True).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir=TMP_BASE)).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        sh(self.repo, "init", "-q", "-b", "main")
        (self.repo / "a.txt").write_text("x")
        sh(self.repo, "add", ".")
        sh(self.repo, "commit", "-qm", "init")
        self.head = sh(self.repo, "rev-parse", "--short", "HEAD")
        os.environ["HANDOFF_STATE_DIR"] = str(self.tmp / "state")
        os.environ.pop("HANDOFF_TOKENS", None)
        os.environ.pop("HANDOFF_TOKENS_STEP", None)

    def tearDown(self):
        subprocess.run(["rm", "-rf", str(self.tmp)])

    def write_handoff(self, text=None):
        ctxlib.ensure_context(self.repo)
        p = ctxlib.handoff_path(self.repo, "main")
        p.write_text(text if text is not None else HANDOFF.format(head=self.head), encoding="utf-8")
        return p

    def transcript(self, tokens, sidechain_after=None, filler=0):
        p = self.tmp / "t.jsonl"
        lines = [json.dumps({"type": "user", "message": {"content": "hi"}})]
        lines.append(json.dumps({"type": "assistant", "isSidechain": False, "message": {
            "usage": {"input_tokens": 2, "cache_creation_input_tokens": 1000,
                      "cache_read_input_tokens": tokens - 1002}}}))
        for _ in range(filler):
            lines.append(json.dumps({"type": "user", "message": {"content": "y" * 1000}}))
        if sidechain_after is not None:
            lines.append(json.dumps({"type": "assistant", "isSidechain": True, "message": {
                "usage": {"input_tokens": sidechain_after}}}))
        p.write_text("\n".join(lines) + "\n")
        return str(p)


class RootTests(Base):
    def test_git_subdir_resolves_toplevel(self):
        sub = self.repo / "src" / "x"
        sub.mkdir(parents=True)
        self.assertEqual(ctxlib.find_root(sub), self.repo)

    def test_non_git_needs_existing_context(self):
        d = self.tmp / "plain" / "deep"
        d.mkdir(parents=True)
        self.assertIsNone(ctxlib.find_root(d))
        (self.tmp / "plain" / "_context").mkdir()
        self.assertEqual(ctxlib.find_root(d), self.tmp / "plain")

    def test_home_is_refused(self):
        home = self.tmp / "home"
        home.mkdir()
        old = ctxlib.HOME
        ctxlib.HOME = home
        try:
            self.assertIsNone(ctxlib.find_root(home, allow_new_non_git=True))
            self.assertEqual(ctxlib.find_root(home / ".." / "home" / "..", allow_new_non_git=True), self.tmp)
        finally:
            ctxlib.HOME = old

    def test_branch_slug(self):
        self.assertEqual(ctxlib.slug("feature/로그인"), "feature__로그인")
        self.assertEqual(ctxlib.slug("a b:c"), "a-b-c")


class SessionStartTests(Base):
    def ss(self, source):
        return ctxlib.session_start({"cwd": str(self.repo), "source": source})

    def test_no_handoff(self):
        self.assertIsNone(self.ss("clear"))

    def test_clear_injects_full(self):
        self.write_handoff()
        msg = self.ss("clear")
        self.assertIn("BODY_ONLY_MARKER", msg)
        self.assertIn("RetryPolicy", msg)

    def test_startup_pointer_only(self):
        self.write_handoff()
        for src in ("startup", "resume"):
            msg = self.ss(src)
            self.assertIn("결제 모듈 재시도 로직 정리", msg)
            self.assertIn("RetryPolicy", msg)
            self.assertNotIn("BODY_ONLY_MARKER", msg)
            self.assertLessEqual(len(msg), ctxlib.STARTUP_LIMIT)

    def test_done_is_silent(self):
        self.write_handoff(HANDOFF.format(head=self.head).replace("status: active", "status: done"))
        self.assertIsNone(self.ss("clear"))

    def test_tracked_handoff_not_injected(self):
        p = self.write_handoff()
        sh(self.repo, "add", "-f", str(p))
        msg = self.ss("clear")
        self.assertNotIn("BODY_ONLY_MARKER", msg)
        self.assertIn("자동으로 읽지 않았습니다", msg)

    def test_clipped_to_limit(self):
        self.write_handoff(HANDOFF.format(head=self.head) + ("가" * 20000))
        msg = self.ss("compact")
        self.assertLessEqual(len(msg), ctxlib.INJECT_LIMIT)
        self.assertIn("잘림", msg)

    def test_missing_commit_is_stale_pointer(self):
        self.write_handoff(HANDOFF.format(head="0000000"))
        msg = self.ss("clear")
        self.assertIn("저장소에 없음", msg)
        self.assertNotIn("BODY_ONLY_MARKER", msg)

    def test_old_handoff_is_stale_pointer(self):
        p = self.write_handoff()
        old = time.time() - 20 * 86400
        os.utime(p, (old, old))
        for src in ("startup", "clear", "compact"):
            msg = self.ss(src)
            self.assertIn("20일 동안 갱신되지 않음", msg)
            self.assertNotIn("BODY_ONLY_MARKER", msg)

    def test_many_commits_is_stale(self):
        os.environ["HANDOFF_STALE_COMMITS"] = "2"
        self.addCleanup(os.environ.pop, "HANDOFF_STALE_COMMITS", None)
        self.write_handoff()
        for i in range(3):
            sh(self.repo, "commit", "-q", "--allow-empty", "-m", f"c{i}")
        self.assertIn("커밋 3개", self.ss("clear"))

    def test_diverged_history_is_stale(self):
        sh(self.repo, "checkout", "-q", "-b", "side")
        sh(self.repo, "commit", "-q", "--allow-empty", "-m", "side")
        side = sh(self.repo, "rev-parse", "HEAD")
        sh(self.repo, "checkout", "-q", "main")
        sh(self.repo, "commit", "-q", "--allow-empty", "-m", "main2")
        self.write_handoff(HANDOFF.format(head=side))
        self.assertIn("갈라짐", self.ss("clear"))

    def test_few_commits_still_fresh(self):
        self.write_handoff()
        sh(self.repo, "commit", "-q", "--allow-empty", "-m", "c1")
        self.assertIn("BODY_ONLY_MARKER", self.ss("clear"))

    def test_malformed_not_injected(self):
        self.write_handoff("그냥 메모 BODY_ONLY_MARKER")
        msg = self.ss("clear")
        self.assertIn("형식이 맞지 않는", msg)
        self.assertNotIn("BODY_ONLY_MARKER", msg)

    def test_compact_prefers_newer_summary(self):
        p = self.write_handoff()
        old = time.time() - 900
        os.utime(p, (old, old))
        msg = self.ss("compact")
        self.assertIn("압축 요약이 더 최신", msg)
        self.assertNotIn("BODY_ONLY_MARKER", msg)
        os.utime(p, None)
        self.assertIn("BODY_ONLY_MARKER", self.ss("compact"))


class StopTests(Base):
    def stop(self, tokens, active=False, sid="s1"):
        return ctxlib.stop({"cwd": str(self.repo), "session_id": sid, "stop_hook_active": active,
                            "transcript_path": self.transcript(tokens)})

    def test_below_threshold(self):
        self.assertIsNone(self.stop(399_999))

    def test_blocks_once_per_level(self):
        out = self.stop(410_000)
        self.assertEqual(out["decision"], "block")
        self.assertIn("handoff", out["reason"])
        self.assertIsNone(self.stop(420_000))
        self.assertEqual(self.stop(560_000)["decision"], "block")
        self.assertIsNone(self.stop(400_000, sid="s1"))

    def test_stop_hook_active_guard(self):
        self.assertIsNone(self.stop(900_000, active=True))

    def test_recent_handoff_suppresses(self):
        self.write_handoff()
        self.assertIsNone(self.stop(410_000))
        self.assertIsNone(self.stop(420_000))  # level already recorded

    def test_env_threshold(self):
        os.environ["HANDOFF_TOKENS"] = "100000"
        self.assertEqual(self.stop(120_000)["decision"], "block")


class TranscriptTests(Base):
    def test_ignores_sidechain_and_spans_chunks(self):
        path = self.transcript(123_456, sidechain_after=999_999, filler=600)  # ~600KB > chunk size
        self.assertGreater(Path(path).stat().st_size, 256 * 1024)
        self.assertEqual(ctxlib.context_tokens(path), 123_456)

    def test_missing(self):
        self.assertIsNone(ctxlib.context_tokens(str(self.tmp / "nope.jsonl")))
        self.assertIsNone(ctxlib.context_tokens(None))


class CompactTests(Base):
    def test_post_compact_saves_and_stays_ignored(self):
        out = ctxlib.post_compact({"cwd": str(self.repo), "session_id": "abcdef123456",
                                   "trigger": "auto", "compact_summary": "요약 본문"})
        self.assertTrue(out.is_file())
        self.assertIn("요약 본문", out.read_text())
        self.assertEqual(sh(self.repo, "status", "--porcelain"), "")

    def test_pre_compact_mentions_handoff(self):
        self.write_handoff()
        self.assertIn("_context/handoff/main.md", ctxlib.pre_compact({"cwd": str(self.repo)}))


class SkillHelperTests(Base):
    def test_prepare_archives_and_warns(self):
        p = self.write_handoff()
        r = ctxlib.prepare(str(self.repo), False, "sess-b")
        self.assertTrue(r["ok"])
        self.assertEqual(r["handoff_path"], str(p))
        self.assertTrue(Path(r["archived"]).is_file())
        self.assertIn("sess-a"[:8], r["warning"])
        self.assertIn("sess-a", Path(r["archived"]).name)
        self.assertIn("superseded", Path(r["archived"]).name)
        r2 = ctxlib.prepare(str(self.repo), False, "sess-a")
        self.assertIsNone(r2["warning"])
        self.assertIsNone(r2["archived"])  # own draft is not archived again

    def test_prepare_non_git_requires_flag(self):
        d = self.tmp / "plain"
        d.mkdir()
        self.assertFalse(ctxlib.prepare(str(d), False, "x")["ok"])
        self.assertTrue(ctxlib.prepare(str(d), True, "x")["ok"])

    def test_validate(self):
        p = self.write_handoff()
        self.assertTrue(ctxlib.validate(p)["ok"])
        p.write_text("no frontmatter")
        r = ctxlib.validate(p)
        self.assertFalse(r["ok"])
        self.assertTrue(any("frontmatter" in e for e in r["errors"]))

    def test_set_frontmatter_value(self):
        t = ctxlib.set_frontmatter_value(HANDOFF.format(head="x"), "status", "done")
        self.assertEqual(ctxlib.parse_frontmatter(t)[0]["status"], "done")


class LifecycleTests(Base):
    def put(self, name, branch, status="active", head=None):
        ctxlib.ensure_context(self.repo)
        p = self.repo / "_context/handoff" / f"{name}.md"
        p.write_text(HANDOFF.format(head=head or self.head).replace("branch: main", f"branch: {branch}")
                     .replace("status: active", f"status: {status}"))
        return p

    def test_prune_archives_finished_and_orphaned(self):
        keep = self.put("main", "main")
        done = self.put("old", "main", status="done")
        gone = self.put("feature__gone", "feature/gone")
        det = self.put("detached-abc1234", "detached-abc1234")
        sh(self.repo, "branch", "alive")
        alive = self.put("alive", "alive")
        r = ctxlib.prune(self.repo)
        self.assertTrue(keep.exists() and alive.exists())
        self.assertFalse(done.exists() or gone.exists() or det.exists())
        names = " ".join(r["archived"])
        for reason in ("-done-", "-branch-gone-", "-detached-"):
            self.assertIn(reason, names)

    def test_prune_keeps_freshly_archived_old_handoff(self):
        gone = self.put("gone", "gone")
        ancient = time.time() - 200 * 86400
        os.utime(gone, (ancient, ancient))
        r = ctxlib.prune(self.repo)
        self.assertEqual(1, len(r["archived"]))
        self.assertEqual([], r["deleted"])
        self.assertTrue((self.repo / r["archived"][0]).is_file())

    def test_prune_never_drops_current_file_for_frontmatter_typo(self):
        live = self.put("main", "mian")
        self.assertEqual([], ctxlib.prune(self.repo)["archived"])
        self.assertTrue(live.exists())

    def test_prune_expires_old_archives_only(self):
        s = ctxlib.ensure_context(self.repo) / "sessions"
        old_c, new_c, old_h, note = (s / "a-compact.md", s / "b-compact.md", s / "c-handoff.md", s / "my-note.md")
        for f in (old_c, new_c, old_h, note):
            f.write_text("x")
        ancient = time.time() - 120 * 86400
        for f in (old_c, old_h, note):
            os.utime(f, (ancient, ancient))
        r = ctxlib.prune(self.repo)
        self.assertFalse(old_c.exists() or old_h.exists())
        self.assertTrue(new_c.exists() and note.exists())
        self.assertEqual(2, len(r["deleted"]))

    def test_done_moves_out(self):
        p = self.write_handoff()
        r = ctxlib.done(self.repo)
        self.assertFalse(p.exists())
        self.assertTrue(Path(r["archived"]).is_file())
        self.assertIsNone(ctxlib.session_start({"cwd": str(self.repo), "source": "clear"}))

    def test_validate_against_current_state(self):
        p = self.write_handoff()
        self.assertTrue(ctxlib.validate(p, self.repo, "sess-a")["ok"])
        self.assertTrue(any("session_id" in e for e in ctxlib.validate(p, self.repo, "other")["errors"]))
        sh(self.repo, "commit", "-q", "--allow-empty", "-m", "moved")
        self.assertTrue(any("head" in e for e in ctxlib.validate(p, self.repo)["errors"]))
        cur = sh(self.repo, "rev-parse", "HEAD")
        p.write_text(HANDOFF.format(head=cur).replace("- RetryPolicy", "- [x] 끝난 것\n- RetryPolicy"))
        self.assertTrue(any("체크된" in e for e in ctxlib.validate(p, self.repo)["errors"]))
        many = "\n".join(f"- 항목 {i}" for i in range(9))
        p.write_text(HANDOFF.format(head=cur).replace("## 진행 중", f"## 끝낸 일\n{many}\n\n## 진행 중"))
        self.assertTrue(any("끝낸 일" in e for e in ctxlib.validate(p, self.repo)["errors"]))

    def test_stop_sweeps_old_state(self):
        sdir = Path(os.environ["HANDOFF_STATE_DIR"])
        sdir.mkdir(parents=True)
        stale = sdir / "old.json"
        stale.write_text("{}")
        ancient = time.time() - 30 * 86400
        os.utime(stale, (ancient, ancient))
        ctxlib.stop({"cwd": str(self.repo), "session_id": "s9", "transcript_path": self.transcript(410_000)})
        self.assertFalse(stale.exists())
        self.assertTrue((sdir / "s9.json").exists())


class HookEntryTests(Base):
    def run_hook(self, event, payload):
        return subprocess.run([sys.executable, "-I", "-B", str(SCRIPTS / "ctx_hook.py"), event],
                              input=payload, capture_output=True, text=True, cwd=str(self.repo))

    def test_bad_input_exits_zero(self):
        for ev in ("session-start", "stop", "pre-compact", "post-compact", "bogus"):
            r = self.run_hook(ev, "not json")
            self.assertEqual(r.returncode, 0)
            self.assertEqual(r.stdout, "")

    def test_session_start_json(self):
        self.write_handoff()
        r = self.run_hook("session-start", json.dumps({"cwd": str(self.repo), "source": "clear"}))
        self.assertEqual(r.returncode, 0)
        d = json.loads(r.stdout)
        self.assertEqual(d["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("BODY_ONLY_MARKER", d["hookSpecificOutput"]["additionalContext"])

    def test_ctx_cli_status_and_set_status(self):
        self.write_handoff()
        cli = [sys.executable, "-I", "-B", str(SCRIPTS / "ctx.py")]
        r = subprocess.run(cli + ["set-status", "done", "--cwd", str(self.repo)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run(cli + ["status", "--cwd", str(self.repo)], capture_output=True, text=True)
        self.assertFalse(json.loads(r.stdout)["exists"])  # done moves it out of handoff/
        archived = list((self.repo / "_context/sessions").glob("*-done-handoff.md"))
        self.assertEqual(1, len(archived))
        self.assertIn("status: done", archived[0].read_text())


if __name__ == "__main__":
    unittest.main()
