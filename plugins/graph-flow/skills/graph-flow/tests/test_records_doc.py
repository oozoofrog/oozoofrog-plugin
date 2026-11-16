import importlib
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
TEXT = (ROOT / "references" / "records.md").read_text(encoding="utf-8")


def section11_modules():
    part = TEXT.split("## 11. Modules", 1)[1]
    return re.findall(r"^\| `([a-z_]+\.py)` \|", part, re.M)


class RecordsDocTests(unittest.TestCase):
    def test_json_blocks_parse(self):
        blocks = re.findall(r"```json\n(.*?)```", TEXT, re.S)
        self.assertTrue(blocks)
        for i, b in enumerate(blocks):
            try:
                json.loads(b)
            except ValueError as e:
                self.fail("json block %d: %s" % (i, e))

    def test_modules_importable(self):
        mods = section11_modules()
        self.assertIn("core.py", mods)
        for m in mods:
            name = m[:-3]
            if (SCRIPTS / "graphflow" / m).exists():
                importlib.import_module("graphflow." + name)

    def test_validation_codes_and_gate_rules(self):
        for i in range(1, 9):
            self.assertRegex(TEXT, r"`V%d`" % i)
        for i in range(1, 8):
            self.assertRegex(TEXT, r"\| R%d \|" % i)


if __name__ == "__main__":
    unittest.main()
