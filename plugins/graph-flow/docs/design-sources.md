# Design sources

Use these sources and the checklist when changing graph-flow. Keep full source
copies under the Git-ignored `_context/` directory. The paths below are relative
to the repository root. If a copy is missing, retrieve it from its source.

## Loops and Graphs: how to stop babysitting agents and only approve the last step

Hanako, 2026-08-23. [Original article](https://x.com/hanakoxbt/status/2091515787366306154).

- Local copy: `_context/sources/loops-and-graphs.hanako.2026-08-23.txt`.
- To retrieve the text, extract `tweet.article.content.blocks` from the
  [FxTwitter JSON](https://api.fxtwitter.com/hanakoxbt/status/2091515787366306154).
- The copy omits examples or tables shown as images after the introductions to
  program-evaluable checks, constraints derived from accepted results, the
  four parts of a return, and lanes ordered by undo cost. Leave those gaps open.

P1–P12 summarize the article. See [principles.md](../skills/graph-flow/references/principles.md).

### What principles.md leaves out

- The article describes a node as a bounded job with one input and one output.
- A loop can make each step correct while the overall workflow still does the
  wrong work, orders it poorly, or serializes independent steps. Improving
  individual loops cannot repair that workflow.
- Sending a whole batch back makes previously correct work uncertain again.
  Every rewritten unit has to be verified again, and repeated batch returns can
  keep the run from converging.
- Using a model for a deterministic transformation increases cost and latency
  and introduces variance into the result.
- The suggested first exercise is to pick one recurring task and draw its
  splitter, lanes, merge, one gate, and one return edge.

## Building agents: When to fold subagents into your main agent loop

Diane Sarkis (Anthropic), 2026-10-22.
[Original article](https://claude.com/resources/articles/building-agents-when-to-fold-subagents-into-your-main-agent-loop).

- Local copy: `_context/sources/fold-subagents.claude.2026-10-22.txt`.
- To retrieve it, open the article page and save the article body as plain text.
- No specific body-text omission is known. The tag-stripped copy includes page
  metadata and joins some paragraphs and list items.

Keep work in one loop when the same context helps across steps. Load relevant
procedures through skills and discover tools on demand. Each delegated call adds
a nested model loop and latency. Returning a summary can drop details that the
main agent needs for later decisions. Split where a unit needs little context
from the rest of the work. Specialists that share data, consume one another's
outputs, or are routinely called together are candidates for folding into the
main loop. A problem category alone gives little reason to split.

Keep a subagent when at least one of these conditions holds:

- A growing context measurably degrades performance in one loop.
- Work needs to run in parallel and each unit can use a fresh context window
  that can be discarded when the unit finishes.
- One agent struggles to choose the right tools, or its system instructions
  conflict.

Start with a small shared end-to-end task-completion eval. Cover important
chains and rules the agent must preserve. Change one boundary at a time and run
each task at least twice per variant. Inspect tasks whose outcomes flip, along
with inconsistent repeats, since averages can hide a regression. Compare
latency and cost alongside completion. Put mechanical steps such as payload
construction and stream parsing in code, and enforce hard limits in tools.

## How this applies to graph-flow

Hanako uses bounded nodes and separate worker contexts to keep work and review
focused. Sarkis keeps related work in one loop until there is evidence that a
separate context earns its cost. A plan node is a unit of work and can run in
the leader's existing context.

- **Node boundaries and independent review.** Named inputs and a scoped brief
  give delegates the context their unit needs. Independent review for effective
  lane 2 and 3 work gives the reviewer one lens and a different model family.
  See [brief generation](../skills/graph-flow/scripts/graphflow/assign.py) and
  [leader instructions](../skills/graph-flow/references/leader.md).
- **Same-context execution.** The leader can execute effective lane 1 work
  inline and can write the plan itself. The splitter agent is optional. See
  [executors](../skills/graph-flow/references/executors.md) and
  [principles](../skills/graph-flow/references/principles.md).
- **Mechanical steps.** Gate verdicts and readiness are computed by the CLI.
  See [gate evaluation](../skills/graph-flow/scripts/graphflow/gate.py) and
  [readiness](../skills/graph-flow/scripts/graphflow/graph.py).
- **Comparison design.** The ten-task eval compares inline with delegated lane
  1 work and leader planning with a separate splitter. It changes one factor
  per comparison, repeats tasks, inspects flipped outcomes, and records wall
  time and human waits. See the [evaluation guide](../dev/eval/README.md).

### Not implemented

- Routing uses host capabilities, task grade, and provider information.
  Measured context degradation, handoff loss, and task-level eval results are
  outside the executor selection rules. See
  [routing](../skills/graph-flow/scripts/graphflow/route.py).
- The eval guide defines the comparisons. It reports no measured winner, and
  graph-flow does not record token counts. See the
  [evaluation guide](../dev/eval/README.md).

## Change checklist

- Name the P1–P12 principle the change serves. Every added refusal or human stop must name its principle.
- Check whether the change increases human answers, wait time, or states that block progress. Count stops against the documented P10 baseline.
- For a new node, name its input, output, and failing check. For a new sub-session, name the context boundary. Justify either split with measured task outcomes and cost.
- When comparing execution designs, change one factor at a time. Run each end-to-end task at least twice per arm and inspect flips, inconsistent repeats, and wall time.
- Keep mechanical work in code and verify that failures return only the affected unit.
