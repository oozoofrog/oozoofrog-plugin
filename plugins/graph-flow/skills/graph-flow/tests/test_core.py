import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from graphflow import core  # noqa: E402


class EnvCase(unittest.TestCase):
    KEYS = ("GF_ROLE", "GF_NODE", "GF_SESSION", "GF_HOME")

    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in self.KEYS}
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["GF_HOME"] = self._tmp.name

    def tearDown(self):
        for k, v in self._saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
        self._tmp.cleanup()


class CoreTests(EnvCase):
    def test_exit_codes(self):
        self.assertEqual(
            (core.EXIT_OK, core.EXIT_NEGATIVE, core.EXIT_USAGE,
             core.EXIT_FORBIDDEN, core.EXIT_STATE, core.EXIT_IO),
            (0, 1, 2, 3, 4, 5))

    def test_human_sig(self):
        self.assertIsNone(core.human_sig("r", "d1", "approved", "ok"))
        key = pathlib.Path(os.environ["GF_HOME"]) / "human.key"
        key.write_bytes(b"k" * 32)
        a = core.human_sig("r", "d1", "approved", "ok")
        self.assertEqual(64, len(a))
        self.assertEqual(a, core.human_sig("r", "d1", "approved", "ok"))
        self.assertNotEqual(a, core.human_sig("r", "d1", "rejected", "ok"))
        self.assertNotEqual(a, core.human_sig("r", "d2", "approved", "ok"))
        self.assertEqual(core.human_sig("r", "d1", "approved", None), core.human_sig("r", "d1", "approved", ""))

    def test_gferror(self):
        e = core.GFError("x", "msg", core.EXIT_STATE)
        self.assertIsInstance(e, Exception)
        self.assertEqual((e.code, e.message, e.exit_code), ("x", "msg", 4))

    def test_actor_defaults(self):
        self.assertEqual(core.actor_from_env(),
                         {"role": "leader", "node": None, "session": None})

    def test_actor_env_and_args(self):
        os.environ.update(GF_ROLE="worker", GF_NODE="n1", GF_SESSION="s")
        self.assertEqual(core.actor_from_env(),
                         {"role": "worker", "node": "n1", "session": "s"})
        self.assertEqual(core.actor_from_env("reviewer", "n2"),
                         {"role": "reviewer", "node": "n2", "session": "s"})

    def test_actor_bad_role(self):
        with self.assertRaises(core.GFError) as cm:
            core.actor_from_env("admin")
        self.assertEqual(cm.exception.exit_code, core.EXIT_USAGE)
        os.environ["GF_ROLE"] = "root"
        with self.assertRaises(core.GFError):
            core.actor_from_env()

    def test_actor_all_roles(self):
        for r in ("leader", "worker", "reviewer", "human"):
            self.assertEqual(core.actor_from_env(r)["role"], r)

    def test_now_format(self):
        self.assertRegex(core.now(), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_gf_home(self):
        self.assertEqual(core.gf_home(), pathlib.Path(self._tmp.name))
        del os.environ["GF_HOME"]
        self.assertEqual(core.gf_home(), pathlib.Path.home() / ".graph-flow")

    def test_gf_home_not_created(self):
        p = pathlib.Path(self._tmp.name) / "missing"
        os.environ["GF_HOME"] = str(p)
        self.assertEqual(core.gf_home(), p)
        self.assertFalse(p.exists())


class ScriptTests(EnvCase):
    def test_not_implemented(self):
        if (SCRIPTS / "graphflow" / "cli.py").exists():
            self.skipTest("cli.py exists")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, "-B", str(SCRIPTS / "gf"), "status"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout.strip())
        self.assertFalse(out["ok"])
        self.assertEqual(out["code"], "not_implemented")
        self.assertIn("message", out)

    def test_script_executable(self):
        self.assertTrue(os.access(SCRIPTS / "gf", os.X_OK))


if __name__ == "__main__":
    unittest.main()
