from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "plugins/openai-decisions/skills/openai-decisions/scripts/openai-decisions"
FAKE_KEY = "sk-test-not-a-real-key-123"

FAKE_OPENAI = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    if sys.argv[1:] == ["--version"]:
        print(os.environ.get("FAKE_OPENAI_VERSION", "openai version 1.51.2"))
        sys.exit(0)
    capture = {
        "argv": sys.argv[1:],
        "stdin": json.loads(sys.stdin.read()),
        "env": {k: os.environ.get(k) for k in (
            "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_UNTRUSTED_STDIN",
            "OPENAI_CLI_NO_UPDATE_CHECK", "OPENAI_CLI_NO_AUTO_UPDATE")},
    }
    with open(os.environ["FAKE_CAPTURE"], "w") as handle:
        json.dump(capture, handle)
    if os.environ.get("FAKE_ECHO_KEY"):
        key = os.environ.get("OPENAI_API_KEY", "")
        print(json.dumps({"error": {"message": "Incorrect API key provided: " + key}}))
        print("401 Unauthorized: " + key, file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"object": "decision", "answers": [{"name": "refund", "probability": 0.9}]}))
    sys.exit(int(os.environ.get("FAKE_OPENAI_EXIT", "0")))
    """
)

FAKE_SECURITY = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os, sys
    args = sys.argv[1:]
    service = args[args.index("-s") + 1]
    if service != os.environ.get("FAKE_KEYCHAIN_SERVICE"):
        sys.exit(44)
    if "-w" in args:
        with open(os.environ["FAKE_SECRET_READS"], "a") as log:
            print(service, file=log)
        print(os.environ["FAKE_KEYCHAIN_VALUE"])
    sys.exit(0)
    """
)


class OpenAIDecisionsCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.capture = root / "capture.json"
        self.secret_reads = root / "secret-reads.log"
        self.openai = root / "openai"
        self.security = root / "security"
        for path, body in ((self.openai, FAKE_OPENAI), (self.security, FAKE_SECURITY)):
            path.write_text(body)
            path.chmod(0o755)
        self.root = root

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, args, stdin="", **env_overrides):
        env = {k: v for k, v in os.environ.items()
               if k not in ("OPENAI_API_KEY", "OPENAI_BASE_URL")}
        env.update({
            "OPENAI_DECISIONS_OPENAI_BIN": str(self.openai),
            "OPENAI_DECISIONS_SECURITY_BIN": str(self.security),
            "FAKE_CAPTURE": str(self.capture),
            "FAKE_SECRET_READS": str(self.secret_reads),
            "FAKE_KEYCHAIN_SERVICE": "none",
        })
        env.update(env_overrides)
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin,
                              capture_output=True, text=True, env=env, timeout=60)

    def captured(self) -> dict:
        return json.loads(self.capture.read_text())

    def test_script_is_executable_in_git_index(self) -> None:
        mode = subprocess.run(["git", "ls-files", "-s", str(SCRIPT.relative_to(REPO_ROOT))],
                              cwd=REPO_ROOT, capture_output=True, text=True).stdout.split(" ")[0]
        if mode:
            self.assertEqual("100755", mode)
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_wrapper_text_request_converts_to_native_and_keeps_key_out_of_argv(self) -> None:
        request = {"state": "결제가 두 번 됐습니다. 환불해주세요.",
                   "questions": [{"type": "predicate", "name": "refund", "instructions": "환불 요청인가?"}]}
        result = self.run_cli(["create"], json.dumps(request), OPENAI_API_KEY=FAKE_KEY)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("decision", json.loads(result.stdout)["object"])
        capture = self.captured()
        self.assertEqual(["decisions", "create", "--format", "json"], capture["argv"])
        self.assertEqual({"model": "gpt-6-luna", "input": request["state"],
                          "questions": request["questions"]}, capture["stdin"])
        self.assertEqual(FAKE_KEY, capture["env"]["OPENAI_API_KEY"])
        for name in ("OPENAI_UNTRUSTED_STDIN", "OPENAI_CLI_NO_UPDATE_CHECK", "OPENAI_CLI_NO_AUTO_UPDATE"):
            self.assertEqual("1", capture["env"][name])
        self.assertNotIn(FAKE_KEY, " ".join(capture["argv"]))
        self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)

    def test_json_state_array_and_image_file(self) -> None:
        image = self.root / "pixel.png"
        image.write_bytes(b"\x89PNG\r\n")
        request = {"state": [1, True], "image_urls": ["https://example.com/a.png"],
                   "questions": [{"type": "score", "name": "q", "instructions": "rate",
                                  "levels": [{"label": "low"}, {"label": "high"}]}]}
        result = self.run_cli(["create", "--image", str(image)], json.dumps(request), OPENAI_API_KEY=FAKE_KEY)
        self.assertEqual(0, result.returncode, result.stderr)
        content = self.captured()["stdin"]["input"][0]["content"]
        self.assertEqual({"type": "input_json", "data": {"items": [1, True]}}, content[0])
        self.assertEqual("https://example.com/a.png", content[1]["image_url"])
        self.assertTrue(content[2]["image_url"].startswith("data:image/png;base64,"))
        self.assertNotIn("image_urls", self.captured()["stdin"])

    def test_wrapper_request_keeps_optional_cli_fields(self) -> None:
        request = {"state": "hello", "timeout_seconds": 30,
                   "prompt_cache_key": "tickets", "prompt_cache_options": {"mode": "explicit"},
                   "safety_identifier": "user-hash",
                   "questions": [{"type": "predicate", "name": "p", "instructions": "x"}]}
        result = self.run_cli(["create"], json.dumps(request), OPENAI_API_KEY=FAKE_KEY)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"model": "gpt-6-luna", "input": "hello", "questions": request["questions"],
                          "prompt_cache_key": "tickets", "prompt_cache_options": {"mode": "explicit"},
                          "safety_identifier": "user-hash"}, self.captured()["stdin"])

    def test_native_request_passes_through_from_input_file(self) -> None:
        request = {"model": "gpt-6-luna", "input": "hello",
                   "questions": [{"type": "choice", "name": "lang", "instructions": "language?",
                                  "choices": [{"value": "en"}, {"value": "ko"}]}]}
        path = self.root / "request.json"
        path.write_text(json.dumps(request))
        result = self.run_cli(["create", "--input", str(path)], OPENAI_API_KEY=FAKE_KEY)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(request, self.captured()["stdin"])

    def test_invalid_questions_fail_without_calling_cli(self) -> None:
        cases = [
            [],
            [{"type": "predicate", "name": "a", "instructions": "x"},
             {"type": "predicate", "name": "a", "instructions": "y"}],
            [{"type": "choice", "name": "c", "instructions": "x", "choices": [{"value": "only"}]}],
            [{"type": "score", "name": "s", "instructions": "x", "levels": [{"label": str(i)} for i in range(11)]}],
            [{"type": "freeform", "name": "f", "instructions": "x"}],
        ]
        for questions in cases:
            with self.subTest(questions=questions):
                result = self.run_cli(["create"], json.dumps({"state": "x", "questions": questions}),
                                      OPENAI_API_KEY=FAKE_KEY)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("openai-decisions:", result.stderr)
                self.assertEqual("", result.stdout)
                self.assertFalse(self.capture.exists())

    def test_keychain_credential_forces_official_base_url(self) -> None:
        request = json.dumps({"state": "x", "questions": [{"type": "predicate", "name": "p", "instructions": "x"}]})
        keychain = {"FAKE_KEYCHAIN_SERVICE": "com.kakao.mac-cu.decisions", "FAKE_KEYCHAIN_VALUE": FAKE_KEY}
        refused = self.run_cli(["create"], request, OPENAI_BASE_URL="https://proxy.example/v1", **keychain)
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("custom OPENAI_BASE_URL", refused.stderr)
        self.assertFalse(self.capture.exists())
        self.assertFalse(self.secret_reads.exists(), "refused request must not read the Keychain secret")
        accepted = self.run_cli(["create"], request, **keychain)
        self.assertEqual(0, accepted.returncode, accepted.stderr)
        self.assertEqual("https://api.openai.com/v1", self.captured()["env"]["OPENAI_BASE_URL"])
        self.assertEqual(FAKE_KEY, self.captured()["env"]["OPENAI_API_KEY"])
        self.assertNotIn(FAKE_KEY, accepted.stdout + accepted.stderr)

    def test_env_key_may_use_custom_base_url(self) -> None:
        request = json.dumps({"state": "x", "questions": [{"type": "predicate", "name": "p", "instructions": "x"}]})
        result = self.run_cli(["create"], request, OPENAI_API_KEY=FAKE_KEY, OPENAI_BASE_URL="https://proxy.example/v1")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("https://proxy.example/v1", self.captured()["env"]["OPENAI_BASE_URL"])

    def test_missing_credentials_and_old_cli_fail_clearly(self) -> None:
        request = json.dumps({"state": "x", "questions": [{"type": "predicate", "name": "p", "instructions": "x"}]})
        missing = self.run_cli(["create"], request)
        self.assertNotEqual(0, missing.returncode)
        self.assertIn("no OpenAI API key", missing.stderr)
        old = self.run_cli(["create"], request, OPENAI_API_KEY=FAKE_KEY, FAKE_OPENAI_VERSION="openai version 1.40.0")
        self.assertNotEqual(0, old.returncode)
        self.assertIn("1.51.2", old.stderr)

    def test_cli_failure_is_reported_not_fabricated(self) -> None:
        request = json.dumps({"state": "x", "questions": [{"type": "predicate", "name": "p", "instructions": "x"}]})
        result = self.run_cli(["create"], request, OPENAI_API_KEY=FAKE_KEY, FAKE_OPENAI_EXIT="3")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("exit code 3", result.stderr)

    def test_echoed_key_is_redacted_from_cli_output(self) -> None:
        request = json.dumps({"state": "x", "questions": [{"type": "predicate", "name": "p", "instructions": "x"}]})
        for env in ({"OPENAI_API_KEY": FAKE_KEY},
                    {"FAKE_KEYCHAIN_SERVICE": "local.openai-decisions", "FAKE_KEYCHAIN_VALUE": FAKE_KEY}):
            result = self.run_cli(["create"], request, FAKE_ECHO_KEY="1", **env)
            self.assertNotEqual(0, result.returncode)
            self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)
            self.assertIn("[REDACTED]", result.stdout)
            self.assertIn("[REDACTED]", result.stderr)

    def test_status_reports_source_names_only(self) -> None:
        result = self.run_cli(["status"], FAKE_KEYCHAIN_SERVICE="local.openai-decisions", FAKE_KEYCHAIN_VALUE=FAKE_KEY)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("1.51.2", report["openai_cli_version"])
        self.assertEqual("keychain:local.openai-decisions/openai", report["credential_source"])
        self.assertFalse(report["api_checked"])
        self.assertNotIn(FAKE_KEY, result.stdout + result.stderr)
        self.assertFalse(self.capture.exists())


if __name__ == "__main__":
    unittest.main()
