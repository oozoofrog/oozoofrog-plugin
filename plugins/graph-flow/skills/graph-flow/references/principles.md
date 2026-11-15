# Principles

graph-flow implements the article "Loops and Graphs: how to stop babysitting agents and only approve the last step" (Hanako, 2026-08-23). Every command, record field, and instruction in this skill cites one or more of the principles below by number. When a design question comes up, the principle decides it; when two readings are possible, pick the one the tool can enforce.

Two layers:

- A **loop** makes one unit of work correct without a person: produce, check, correct, repeat until green. It lives *inside* a node.
- A **graph** decides which units exist, what runs at the same time, what waits, and where results go back. It lives *between* nodes.

A graph without loops produces unverified work in parallel. A loop without a graph is one good step in a queue nobody designed.

## The twelve principles

| # | Principle | What the tool enforces |
| --- | --- | --- |
| P1 | **Check first.** A check is a condition a program can evaluate and that can fail. "Looks good", "the model is confident", and "no errors were raised" are not checks. | `gf plan validate` rejects a work node with no check. `gf red` runs a new check before the work and records whether it failed. `cmd` checks are executed by `gf` and judged by exit code. |
| P2 | **The loop lives inside the node.** Produce, check, correct, repeat until green, at most three attempts. If three corrections fail, the fault is in the plan, and the loop cannot see the plan. | Every `gf start` consumes one attempt. The fourth start is refused and the node becomes `replan`. |
| P3 | **An edge is a real dependency.** "And then" is not an edge. If you cannot name the artifact that crosses, there is no edge and the wait is waste. | Every `needs` entry must name the producing node and the artifact. `gf plan validate` rejects an unnamed edge and an artifact the producer does not own. |
| P4 | **Split by blast radius, not by folder.** The splitter decides more than any other node. | Every node declares `lane` and `owns`. Nodes that can run at the same time must not own overlapping paths. |
| P5 | **One unit, one lens, own context.** Workers that share a window converge on one opinion with echoes. | `gf brief` emits only that node's goal, inputs, scope, checks, and constraints. The worker and reviewer roles cannot read other nodes' results. |
| P6 | **Use code where there is exactly one correct answer.** Merging, ranking, deduplicating, comparing: if the transformation can be described without the words judge, decide, assess, or summarize, it is code. | Merge, scope comparison, verdict computation, readiness, and aggregation are `gf` commands, never model output. |
| P7 | **The gate reads evidence in order:** deterministic results, then the trajectory of this run, then how often this node's work was rolled back before, and the model's own assessment last. Confidence is the only input the model can influence. | Evidence carries a grade (1 deterministic, 2 observed, 3 history, 4 opinion). `gf gate` evaluates by grade order. Opinion alone never opens a gate and never overturns a grade 1 result. |
| P8 | **Return the unit, not the batch.** A rejection carries UNIT, VERDICT, REASON, EVIDENCE, SCOPE. Without the scope line a returned unit grows. | `gf gate` builds the rejection record from the failed check. Other nodes' passed status is never touched by a rejection. |
| P9 | **Open the gate on blast radius, not on confidence.** Lane 1: reversible and contained, opens first. Lane 2: reversible but wide, opens on deterministic checks plus a clean trajectory. Lane 3: hard to reverse, does not open regardless of score. A closed lane is not a high threshold; thresholds get adjusted and closed lanes do not. | A lane 3 node cannot become `passed` without a human `approved` decision event. A work node with no `cmd` check is raised one lane and gets a `human` check. Lane 2 and 3 work needs an independent review from a different model family before it can pass. |
| P10 | **Put the human on one step,** at the point of highest consequence and lowest reversibility. A human in the middle of a graph becomes its slowest node. | Only two things reach a person: decisions and approvals. A request for confirmation must be turned into a check. Agents can ask and wait; only a human surface can answer. |
| P11 | **Build the learning edge.** An accepted result goes back to the splitter as a constraint, not as output: ACCEPTED, DERIVED, LANDS IN the splitter's brief. A failure not turned into a permanent constraint will be met again. | A per-project constraint store. `gf plan set` injects matching constraints into the plan and records which were applied. `gf learn promote` turns a machine-checkable constraint into a fixed check on every run. |
| P12 | **Measure the path, not only the answer. A verdict that does not change what runs next is a report.** | The event log records every attempt, check, rejection, and duration; `gf trace` aggregates them. A gate verdict directly changes the output of `gf ready`. |

## Node kinds

The article names four kinds of node. graph-flow maps them as follows.

| Article | graph-flow |
| --- | --- |
| Splitter | The leader session following `leader.md`, optionally the `gf-splitter` agent. Output: `plan.json`. |
| Worker | A session with role `worker` (kind `work`) or `reviewer` (kind `review`, one `lens`). |
| Code node | A `gf` command (merge, scope comparison, verdict, readiness). It is recorded as an event, not as a plan node. |
| Gate | `gf gate`. Human judgment enters only as a `decision` node or a `human` check. |

## Two return paths

| Edge | Carries | Lands in | Fixes |
| --- | --- | --- | --- |
| Correction | The rejection record of one node | The same node's next brief | The run you are in |
| Learning | A constraint derived from an accepted result | The plan of every later run, and optionally a fixed check | Every run after |

## Questions to a person

The article removes *checking* by a person, not *deciding* by a person. A question that asks for verification ("is this OK?", "shall I proceed?") must become a check. A question whose answer is in the code or the records must be answered by reading them. A question only the person can answer (direction, missing information, a review of taste, authorization) is a decision: ask it before the split when possible, at the gate when it is an approval, and never block unrelated nodes while waiting.

## Build order

Gate first, then lanes, then the learning edge. Everything gets easier once something can fail loudly, and constraints cannot be derived from accepted results until something is accepting results.

## Limits stated plainly

- The article's numbers (three attempts, "the largest single speedup") are assertions, not measurements. `gf trace` exists so they can be replaced by measured values.
- A test written by the same model that wrote the code encodes that model's misunderstanding. Acceptance criteria are written at planning time, and lane 2 work is reviewed by a model from a different family.
- Some work has no machine check that can fail (visual design). Label it `human`; do not attach a ceremonial check.
- A check run through a host tool with no exit code (an IDE's build or test tool) is grade 2 evidence. It is useful and it is not a deterministic result.
