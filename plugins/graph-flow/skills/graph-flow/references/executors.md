# Start the assigned session

Use `gf route <node>` as the source of truth for the current grade-to-model mapping, effort, account suggestion, executor, and isolation. Read its explanation and verify that the host actually supports the choice. Routing is a suggestion; it does not start a session or establish model availability. Read [leader.md](leader.md) for the dispatch sequence.

## Models and accounts

The defaults in [routing.json](../routing.json) are:

| Grade | Task | Claude model / effort | OpenAI model / effort |
| --- | --- | --- | --- |
| bulk | Repeated independent extraction or mechanical changes | claude-haiku-5-5 / medium | gpt-6-luna / medium |
| scoped | Bounded implementation with an established approach | claude-sonnet-5-5 / medium | gpt-6.1-sol / medium |
| daily | Debugging or an implementation that needs investigation | claude-opus-5-5 / medium | gpt-6.1-sol / high |
| large | Broad interface, architecture, or migration work | claude-fable-5-2 / high | gpt-6-astra / high |
| security | Defensive vulnerability discovery on owned systems | claude-fable-5-2 / high | gpt-6-astra / high |

Re-run routing before dispatch or retry. It prefers the eligible provider instance with the lowest measured usage, excludes stale or full accounts, and can recommend another family when default-family usage is high. Missing usage means unknown capacity, not a full quota. A null provider is not a usable account id: discover an available authenticated instance through the host, record what you actually use, and disclose missing usage evidence. Honor an explicit user model/account choice; report unavailability instead of silently substituting.

Review lane 2/3 work with a different family (`claude` versus `openai`), not just another model or account in the same family. Keep each reviewer to one lens. If no other family is available, leave the required review unverified.

## Record the actual executor

Before launch, run `gf assign <node> --executor <executor> --model <model> --effort <effort> --provider <provider> --family <family> --isolation <isolation>`, then `gf brief <node>`. All six assignment values are required. Use the real provider instance, model id, effort, and family; accepted families are `claude`, `openai`, and `other`. The assignment records a choice; it does not configure the host. Pass the same settings to the host launch.

| Host | Assignment executor | Isolation | How to deliver the brief |
| --- | --- | --- | --- |
| Leader itself | `inline` | `shared` | Execute the node's steps in the leader, retaining the leader role; effective lane 1 work only. |
| Native subagent | `subagent` | `shared`, or supported `worktree` | Give one generated brief to Claude Code's Agent tool or Codex's `spawn_agent`. |
| Claude Code Workflow | `workflow` | Match the actual checkout | Give each workflow agent one brief; each reports its own start/check/submission through `gf`. |
| T3 Code | `t3` | `worktree` for parallel work; `shared` for read-only review | Put one generated brief in `delegate_task`'s task. |
| Background session | `background` | Match the actual checkout | Start a supported persistent host session with one brief and its environment. |

For native agents, supply the routed model and effort through the host's supported fields or configuration; Claude Code uses Agent, Codex uses `spawn_agent`. If a setting cannot be selected, use a supported executor or report the limitation, and record the settings actually used. Do not pretend a prompt changes the model. Keep the new session's context limited to the brief and required inputs. Wait for its completion using the host's agent-completion facility.

For Workflow, the fan-out script is a separate integration unit. Do not invent a script path or arguments. When available, each agent receives exactly one brief and reports through `gf`; collect completions and run the leader's merge/gate procedure.

## T3 Code delegation

Call `orchestrator_capabilities` once before the first `delegate_task` to discover available provider instances and models. Use the selected provider instance and model in `target`; put effort and other provider settings in `target.options` according to that host's schema. Use title `<node> · <model>/<effort>`. Give the child the complete English `gf brief` output and require an English report to the leader.

For parallel work nodes, request `isolation: "worktree"` and `mode: "async"`. Let the host create the checkout, using the branch/base that contains the node's required inputs. Keep `GF_RUN` pointing to the leader's run. Tell the child to use its worktree for start/check/submit, commit its owned changes there, and use `gf submit <node> --cwd <worktree> --commit <sha> --notes "result"`. A worktree that lacks required uncommitted input is not ready: integrate that input or run the dependent work serially.

Follow the delegate result's `next` instructions and wait for completion events or the prescribed wait tool. Do not poll task status, create sleep/watch loops, or launch a new top-level thread to simulate a child. Cancel a superseded delegate through the host before replacing it. Start a fresh review delegate for a changed submission; do not reuse a reviewer's old opinion. For cross-family review, choose the other family's available provider instance, read-only shared isolation on the integrated target, and the review node's own brief.

For background sessions outside T3, use the host's supported background launch with the selected model and effort and the generated brief as input. Preserve its environment and run directory; collect completion through the host. In T3, use `delegate_task` for background work and record executor `t3`. Do not invent flags, assume a background process can resume itself, or fall back to a shell agent CLI when the requested host cannot launch it.

## Worktrees and checks

Uncommitted work in a shared tree is serial: `gf start` returns `shared_busy` while another shared work node is running or has a current uncommitted submission. Parallel work needs separate worktrees and commits even when owned paths do not overlap. Reviewers change no files and do not occupy that writer slot. Integrate committed submissions with `gf merge <node>` before gating them in the leader's tree; let the tool record conflicts and return the affected node.

A command whose process has an exit code is a `cmd` check: `swift test`, `xcodebuild`, or the project's build wrapper can qualify. Put the actual established invocation in the plan and let `gf check run <node> <check>` execute and capture it; comply with project build/cache instructions. An IDE's build, test, or preview tool without an exit code is a `host` check, even when it reports success. Record its observation with `gf check record <node> <check> --result passed --note "observed evidence"`; do not invent an exit code.

A lane 2 or 3 node with only host checks should receive an additional meaningful cmd check for its gate. Add it to the plan before work when possible; the gate has no option to inject a command. A later plan change invalidates the affected node and its dependents, so revalidate and resubmit. If the result has no machine-checkable behavior, retain the human check and raised lane and disclose the verification limit instead of adding a ceremonial command.
