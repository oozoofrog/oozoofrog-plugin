#!/usr/bin/env python3
"""Compare user-recorded A/B measurements; never collect or invent telemetry."""
import argparse
import json
import math
from pathlib import Path
import sys

FIELDS = ("elapsed_seconds", "tool_calls", "input_tokens", "output_tokens")
INTEGER_FIELDS = set(FIELDS[1:]) | {"required_checks_passed", "required_checks_total"}
ENV_FIELDS = ("model", "product", "settings", "input_id", "criteria_id", "tool_access", "budget", "team_policy")
QUALITY = ("action_identification", "hierarchy", "layout_integrity")


def number(value, key, maximum=None):
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{key}: use a finite nonnegative number or null")
    if key.split(".")[-1] in INTEGER_FIELDS and not isinstance(value, int):
        raise ValueError(f"{key}: use an integer or null")
    if maximum is not None and value > maximum:
        raise ValueError(f"{key}: maximum is {maximum}")


def compare(data):
    if not isinstance(data, dict) or data.get("status") != "measured":
        raise ValueError("Only status=measured records can be compared; planned tasks are not results")
    environment = data.get("environment", {})
    if not isinstance(environment, dict) or any(not isinstance(environment.get(k), str) or not environment[k].strip() for k in ENV_FIELDS):
        raise ValueError("Record model/product/settings/input/criteria/tool_access/budget/team_policy first")
    runs = []
    for label in ("A", "B"):
        run = data.get(label)
        if not isinstance(run, dict) or not isinstance(run.get("prompt"), str) or not run["prompt"].strip():
            raise ValueError(f"{label}: prompt is required")
        evidence = run.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(not isinstance(x, str) or not x.strip() for x in evidence):
            raise ValueError(f"{label}: actual evidence references are required")
        for key in FIELDS + ("required_checks_passed", "required_checks_total"):
            if key not in run:
                raise ValueError(f"{label}.{key}: missing; use null if unavailable")
            number(run[key], f"{label}.{key}")
        passed, total = run["required_checks_passed"], run["required_checks_total"]
        if (passed is None) != (total is None) or (total is not None and (total == 0 or passed > total)):
            raise ValueError(f"{label}: provide a valid checks numerator and positive denominator together")
        scores = run.get("quality_scores", {})
        if not isinstance(scores, dict) or any(k not in scores for k in QUALITY):
            raise ValueError(f"{label}: record all quality scores, using null when unavailable")
        for key in QUALITY:
            number(scores[key], f"{label}.{key}", 2)
        runs.append(run)
    a, b = runs
    if a["required_checks_total"] != b["required_checks_total"]:
        raise ValueError("A/B required check totals differ; use the same criteria")
    metrics = {}
    for key in FIELDS:
        av, bv = a[key], b[key]
        metrics[key] = {"A": av, "B": bv, "B_minus_A": bv-av if av is not None and bv is not None else None}
    total = a["required_checks_total"]
    accuracy = {label: run["required_checks_passed"]/total if total is not None else None for label, run in zip(("A", "B"), runs)}
    return {"environment": environment, "metrics": metrics, "accuracy": accuracy,
            "quality_scores": {"A": a["quality_scores"], "B": b["quality_scores"]},
            "limits": ["User-entered measurements; evidence and environment equivalence are not independently verified.",
                       "Null means unavailable; no token, cost, or speed improvement is inferred.",
                       "One pair is descriptive; it does not establish model or prompt superiority."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.record.read_text(encoding="utf-8"))
        result = compare(data)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Cannot compare: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
