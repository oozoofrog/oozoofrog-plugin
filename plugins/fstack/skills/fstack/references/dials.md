# Dials: pace, gates and spec tier

Choose two dials: Pace and Spec tier. Send them as the frame line in visible reply text right after the skill loads, before your next tool call and before any action that changes files. A line only in thinking, in a tool input or in the final report does not count. If this file changes a dial that you already sent, send a corrected frame line before the next file change. It is one literal line in the user's language, and it keeps the keys `Pace:` and `Spec:` in every language, for example `Pace: step · Spec: T1 — internal bug with a clear repro` or `Pace: step · Spec: T1 — 재현되는 내부 버그`. Do not wait for confirmation.

## Pace

| Pace | When | Behavior |
|---|---|---|
| `step` (default) | Always, unless the user granted drive | Finish the whole request without questions about reversible work. Keep changes in the working tree unless the request or a project rule says to commit. Then stop and propose one next step in one line. |
| `drive` | Only after an explicit grant, such as "run until done", "don't stop", "끝까지", "자율로" | Continue to the exit predicate across units (`playbooks/drive.md`). Fix blocking side issues. The grant alone permits no commit: commit only when the request or a project rule says to commit, otherwise leave the changes in the working tree and say so in the report. Push stays G1. |

A grant covers the task that it names. It does not carry over to the next request.

## Gates

Gates stop work in any pace. Details: `principles/stop-at-gates.md`.

| Gate | What | Step pace | Drive pace |
|---|---|---|---|
| G1 | Irreversible or externally visible action | Stop and ask | Park the unit, continue the others, list it in the report |
| G2 | A product or preference call that the user owns and no run can settle | Ask once, batched, with a recommendation | Park the unit, continue the others |
| G3 | A change to the meaning of an approved document or a project rule | Stop and ask | Park the unit, continue the others |

## Spec tier

Spec weight follows the lifetime of the contract and the cost of being wrong.

| Tier | Use when | Artifacts |
|---|---|---|
| T0 (always) | Every task | Goal, exit condition as a pass/fail sentence, verification method |
| T1 (default) | Internal change, no new contract | The failing check, the repro or the prototype is the spec |
| T2 | The change creates or alters a contract that others rely on (public API, CLI surface, persisted schema, protocol), the project already keeps such documents, or the user asks | Spec, ADR and plan with IDs (`references/doc-templates.md`), checked by `scripts/trace.py` |

Escalate from T1 to T2 when one of these signals appears:
- A contract appears during the work.
- The project already keeps spec, ADR or plan documents for this area.
- The same premise failed twice, so the shared understanding needs to be written down.

A fork that a run can settle goes to `playbooks/prototype.md`, not to a document or a question.

## Examples

| Request | Choice |
|---|---|
| Internal bug with a clear repro | `fix`, T1, step |
| New public CLI flag | `design-docs`, T2, step |
| New project | `kickoff`, then T2 |
| Overnight flaky-test hunt, "don't stop" | `fix` inside `drive`, T1, drive |
| Two UI layouts and no precedent | `prototype`, then `build` at T1 |
| "Which is better: read the whole file or line by line?" | `prototype`: measure both, then answer |
| "Make X work with Y", with no named target | `kickoff` |
| Purpose of the work is unclear | `kickoff` |
