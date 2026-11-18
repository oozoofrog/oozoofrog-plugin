# graph-flow evaluation set

Use these ten Python 3.9 standard-library tasks to measure how ways of working
change task completion and the path to it. This is a measurement guide, not a
report of measured results. The mix is four single fixes, three dependent chains,
two shared changes needing review, and one task with three independent parts.

## Runner commands

Run from the repository root. List task IDs and inspect command help:

```sh
python3 -I -S -B plugins/graph-flow/dev/eval/run_task.py --help
python3 -I -S -B plugins/graph-flow/dev/eval/run_task.py list
```

Prepare one fresh scratch candidate outside the fixture and task directories:

```sh
eval_scratch=$(mktemp -d /tmp/graph-flow-eval.XXXXXX)
python3 -I -S -B plugins/graph-flow/dev/eval/run_task.py setup 01-compatibility-slugs "$eval_scratch"
```

Read that task's `task.json` prompt and modify only the scratch candidate.
Keep `solution/`, `hidden_tests/`, and review `tempting/` states out of worker
and planner context. Score the completed candidate against external hidden tests:

```sh
python3 -I -S -B plugins/graph-flow/dev/eval/run_task.py score 01-compatibility-slugs "$eval_scratch"
python3 -I -S -B plugins/graph-flow/dev/eval/run_task.py selfcheck --expect 10 --mix single=4,chain=3,review=2,parallel=1
```

`setup` copies the fixture plus the task's starting overlay; its destination must
be absent or empty. `score` emits JSON (including `passed` and test counts) on
stdout, diagnostics on stderr, and exits 0 for pass or 1 for failure.
`selfcheck` checks that starts fail, solutions pass, and review temptations fail
hidden tests while passing visible tests. For multipart tasks it also checks
that each hidden file fails or errors alone against the start.

The runner requires importable `test*.py` modules executing at least one test,
ordinary unittest execution, and package markers for nested suites; it rejects
load_tests hooks and symlinks in candidates or hidden suites. Standard-library
imports take precedence. It is not a sandbox against deliberately hostile code:
harness monkeypatching, trusted-file/verdict tampering, filesystem races,
subprocess side effects, and resource exhaustion are outside its guarantees.
Selfcheck cannot infer semantic coverage of the named parts or whether hidden
tests are semantically sufficient.

## Tasks

IDs come from `list`; categories and descriptions come from each `task.json`.

| ID | Category | One-line description |
| --- | --- | --- |
| 01-compatibility-slugs | single | Fold compatibility characters into ASCII lowercase slugs. |
| 02-config-equals-values | single | Preserve all value text after the first equals sign. |
| 03-chunk-size-validation | single | Validate positive integer chunk sizes, including empty inputs. |
| 04-underscore-word-boundaries | single | Split words at underscores while retaining Unicode alphanumerics. |
| 05-slugged-config-export | chain | Fix compatibility folding, then export validated slugged config keys. |
| 06-vocabulary-batches | chain | Aggregate ordered document vocabulary, then batch its distinct words. |
| 07-layered-config-output | chain | Merge config layers with stable order, then format the merged mapping. |
| 08-projected-unique-review | review | Add equality-based projection to unique for both catalog callers. |
| 09-leading-bom-review | review | Add opt-in removal of exactly one leading BOM for shared consumers. |
| 10-independent-contract-fixes | parallel | Fix slug edges, duplicate-key precedence, and final partial chunks independently. |

## Controlled comparisons

The comparison method follows [Diane Sarkis’s end-to-end eval guidance](https://claude.com/resources/articles/building-agents-when-to-fold-subagents-into-your-main-agent-loop).
For each comparison below, run every task at least twice per arm, starting each
run with a fresh `setup` destination and separate graph-flow run records.
Alternate arm order. Hold prompt, starting files, model/settings, checks, review
requirements, and all other policies fixed; change only the named factor.

| Comparison | Arm A | Arm B |
| --- | --- | --- |
| Lane-1 execution | Leader performs lane-1 work inline. | Delegate the same lane-1 nodes to worker sessions. |
| Planning | Leader writes the plan. | The gf-splitter agent writes the plan from the same brief. |
| Plan approval | Obtain plan approval before dispatch on every task. | Obtain it only if a lane 2 or 3 node exists. |

The approval comparison is an experimental policy variation, not a claimed CLI
switch: current principles mandate plan approval before dispatch. Record how the
variant is enabled; do not silently bypass an enforced approval. Keep lane-2/3
independent review and lane-3 human approval in both arms.
In every arm, declare lanes, ownership, checks and real artifact dependencies;
use produce/check/correct loops within nodes, and gates between nodes. Parallel
workers need separate worktrees; only one uncommitted worker uses a shared tree.
Use the same scoring command with that run's task ID and scratch destination.

## Record and interpret

For each task, arm and repetition, retain the candidate, plan, settings, `score`
JSON/exit code, and graph-flow trace. With `GF_RUN` selecting that run, use:

```sh
python3 -I -S -B plugins/graph-flow/skills/graph-flow/scripts/gf trace --conformance
```

Record hidden-test pass from `score`, attempts and rejections, planned and
unplanned human answers and human wait time from `gf trace --conformance`, plus
wall time from planning start through final scoring (including waits). Its P10
baseline treats plan approval plus planned decisions as planned; other stops
are unplanned. Keep that baseline visible when comparing approval policies.
For review tasks, record whether the tempting mistake was caught, by whom and
with what evidence; do not infer reviewer detection merely from a final pass.
Token counts are not recorded by graph-flow today.

Compare which individual tasks flipped between arms, with both repetitions and
failure/review evidence alongside their costs, rather than comparing the mean.
Report inconsistent repetitions and unchanged tasks as well as improvements;
make no claims about outcomes until the runs have actually been measured.
