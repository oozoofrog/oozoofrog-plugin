# V4 reused-case regression — bounded PASS

After V3 omitted a requested description and the explicit no-immediate-Wi-Fi-enable condition, two sentences were narrowed: omission of redundant descriptions is allowed only when no description was requested and no condition/negative/caution is needed; final editing checks requested components and confirmed negative conditions. The tested guide/examples/source bodies are byte-identical to the new [canonical skill](../../../../korean-product-writing/SKILL.md) and its references.

One new guide-provided call reused the exact [six V3 inputs](../paired-v3/cases.json), [pre-generation rubric](../paired-v3/rubric-frozen.json) and common task. These are reused regression cases, not unseen/held-out inputs. The preserved V3 baseline is only a reference; no simultaneous new paired baseline was run. No answers, prior outputs, diagnosis, rubric or other test documents were supplied to generation. The revised guide and references were explicitly supplied as usercontent. [Generated text](output.txt) is verbatim.

An independent AI reviewer assessed visible meaning, request completeness and naturalness before publication:

| Case | Result | Visible evidence |
|---|---|---|
| Actor | PASS | Natural reader-addressed omitted subject, operations format check, approval-before-download relation and unknown actors retained. |
| Network button | PASS | Requested description, official screen name, opening behavior and no-immediate-Wi-Fi-enable condition all retained; no destination capability invented. |
| Report | PASS | Date/version/9/7/2, expired-link inability versus unperformed test, guide-D offline-only alternative and no safety verification retained. |
| Marketing | PASS | Cost/answer time undecided; title/description/button complete without free/immediate-answer/resolution promises. |
| Error | PASS | E42 interruption/unknown cause and official record opening retained; resume/recovery only a separate confirmation item. |
| Direct action | PASS | Official term, immediate local-copy-only removal, retained original/other copies and already natural text preserved. |

This one six-case regression passed its fixed semantic/request-completeness criteria. It does not prove universal compliance, causal efficacy, superiority or automatic activation. Requested model was `gpt-6.1-sol` with `medium` reasoning; actual runtime model name was not exposed and remains unconfirmed. Exit code was 0, stderr empty and only `agent_message` items were returned, with no tool events. Normal on-request approvals, read-only sandbox and ephemeral/ignore-user-config/strict-config isolation were retained. Complete omission of injected global catalog/context cannot be proved from these receipts.

The [V3 failure](../paired-v3/results.md), original outputs/rubric and [earlier failures](../validation.md) remain unchanged. The original ten scope fixtures are manual review fixtures, not ten newly executed passes. No additional model call was made after this regression. Structural/distribution checks support packaging only. Actual installation, fresh loader discovery and implicit invocation were not tested; no global install is performed by this PR.
