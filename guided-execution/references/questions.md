# Bounded, useful human questions

## Start from evidence

Before asking, inspect relevant project material and conversation decisions. Maintain a private uncertainty table with: missing fact/decision; evidence checked; affected tasks; consequence of a wrong assumption; recommended default; whether the user must decide. Do not present the entire table as homework.

Classify each gap:

| Gap | Action |
| --- | --- |
| Discoverable fact | Read or measure it; do not ask the user to repeat it. |
| Reversible routine choice | Use a project-consistent default and briefly state the assumption. |
| Consequential preference/tradeoff | Consider a question against the remaining budget. |
| Essential unavailable fact | Block affected work; ask the smallest question that unblocks it. |
| Missing permission | Apply host policy and actual user authorization; do not infer permission. |

## Select the few questions that change the work

Rank candidates by how much downstream work the answer changes, how costly a wrong assumption is to reverse, and how much effort answering requires. Prefer a question that resolves a common underlying decision over a list of dependent implementation settings. These are qualitative judgments, not a claim of mathematically optimal information gain.

Ask independent questions together when that reduces turns. If an answer determines whether another question is relevant, defer the dependent question. Do not ask for tools, frameworks, file names, colors, or internal architecture the existing project already decides.

**Default budget:** 3 independent discretionary decision questions, at most 2 rounds for the entire request. For example, 2 in the first round and 1 follow-up, or 3 once. Zero is preferred when the request is executable. Track used questions/rounds across stages and resumed sessions. Each unrelated decision in a compound sentence counts separately. A clarification already answered is not a new question to repeat.

The user's smaller budget or instruction to use judgment takes precedence. Do not expand the budget silently. After it is used, proceed with explicit reversible defaults; unresolved essentials remain blocked. Required permission under host policy is not waived by this budget. Bundle related permission requests around a concrete reviewed action, never treat elapsed time as consent, and do not repeatedly ask the same unanswered permission question.

## Shape of a decision request

Provide, in this order:

1. The concrete decision and why it changes the result.
2. A recommended choice with one reason; at most two meaningful alternatives if useful.
3. The result/preview/evidence the user can inspect, when available.
4. One focused question; accept free-form feedback.

Use an available structured input tool only when it materially helps, and honor its question and permission restrictions. Ordinary conversation is sufficient. Do not expose internal graphs, schemas, or configuration fields unless the user needs them for a decision.

Example: A local note exporter has UTF-8 JSON storage, no attachments, and the user only needs a portable copy. Reuse JSON, preserve the original, and choose a distinct output name such as notes-export.json without overwriting an existing file. Do not ask the user to choose serialization libraries, indentation, filenames, compression, and encryption. If the export must be opened by a particular other app and that fact is absent, ask which destination app; that one answer may determine format and encoding together.

## End requirements discovery

Discovery ends when the outcome, must-keep constraints, meaningful acceptance criteria, and authorized scope permit execution. The user need not say a special phrase such as 'requirements finished'. A partial answer resolves what it actually says; use defaults for nonessential omissions. A final brief summarizes decisions and assumptions, then execution starts if requested. Do not append 'shall I proceed?' to an already authorized task.

If no project is identifiable, ask for its location before creating a workspace. Do not invent a repository or act on an unrelated project. If the user requested only advice/design, deliver that scope instead of implementing.

## Questions during execution

Reopen a question only for new evidence that materially changes an agreed decision. Reserve remaining budget for genuinely new ambiguity. Direction questions belong before expensive dependent work; subjective review belongs at a representative artifact; execution permission belongs immediately before the consequential action after preparation.

Record a decision's kind, user wording, affected task IDs, scope, and reviewed artifact version. 'Looks good' on a design resolves design review only. 'Continue' resumes the established scope; it does not grant unrelated new access. User preferences remain local to the request unless the user assigns a wider scope.

Do not notify repeatedly while the same decision is pending. At a blocked handoff, give completed work and one clear unresolved decision. On response, reconcile and continue from the checkpoint.
