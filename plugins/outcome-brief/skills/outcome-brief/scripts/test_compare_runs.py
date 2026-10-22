"""Small synthetic invariants; these are not model A/B results."""
import copy
import unittest
from compare_runs import compare


class CompareTests(unittest.TestCase):
    def setUp(self):
        run = {"prompt": "synthetic", "elapsed_seconds": 1, "tool_calls": 0, "input_tokens": None,
               "output_tokens": None, "required_checks_passed": 2, "required_checks_total": 2,
               "quality_scores": {"action_identification": 2, "hierarchy": 1, "layout_integrity": 1}, "evidence": ["synthetic fixture"]}
        self.data = {"status": "measured", "environment": dict.fromkeys(("model", "product", "settings", "input_id", "criteria_id", "tool_access", "budget", "team_policy"), "synthetic"),
                     "A": copy.deepcopy(run), "B": copy.deepcopy(run)}

    def test_missing_telemetry_stays_unknown(self):
        result = compare(self.data)
        self.assertIsNone(result["metrics"]["input_tokens"]["B_minus_A"])
        self.assertEqual(result["metrics"]["tool_calls"]["B_minus_A"], 0)

    def test_planned_record_rejected(self):
        self.data["status"] = "planned"
        with self.assertRaises(ValueError):
            compare(self.data)

    def test_incomparable_criteria_rejected(self):
        self.data["B"]["required_checks_total"] = 3
        with self.assertRaises(ValueError):
            compare(self.data)

    def test_fabrication_prone_numeric_values_rejected(self):
        for value in (True, -1, float("nan"), float("inf"), "unknown", 0.5):
            with self.subTest(value=value):
                self.data["B"]["tool_calls"] = value
                with self.assertRaises(ValueError):
                    compare(self.data)

    def test_actual_delta_computed(self):
        self.data["B"]["elapsed_seconds"] = 3
        self.assertEqual(compare(self.data)["metrics"]["elapsed_seconds"]["B_minus_A"], 2)

    def test_empty_evidence_rejected(self):
        self.data["B"]["evidence"] = []
        with self.assertRaises(ValueError):
            compare(self.data)


if __name__ == "__main__":
    unittest.main()
