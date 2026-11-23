# Report

Write the report in the user's language. Use these five headings in this order every time. Keep an empty heading and write "none".

| English | Korean |
|---|---|
| Goal | 목표 |
| Changes | 변경 |
| Verification | 검증 |
| Basis | 근거 |
| Remaining | 남은 일 |

## Contents

1. **Goal.** The goal as you understood it. Name the playbook and the skipped steps with reasons.
2. **Changes.** What the user sees first, then code and documents. Include deleted code. Add the items from the playbook's `**Report:**` line.
3. **Verification.** A table:

   | Item | Method | Verdict | Evidence |
   |---|---|---|---|
   | exit condition or ID | command, tool or path | Verified / Failed / Inconclusive | output excerpt, file, screenshot path |

   State the review mode: independent, two-lens, or single-agent fallback. Add any reduced coverage and its reason.

4. **Basis.** Each principle you read → the decision it changed. Label the claims that have no evidence row (`principles/label-the-claim.md`).
5. **Remaining.** The count of decisions that need confirmation and the top one, memos, rules not met, deferred items, and open findings, each with a closure state: Fixed, Rejected (with evidence) or Unresolved.

In step pace, the last line of the report is the next-step line, on its own line, with nothing after it. Use the template for the report's language. Do not start the candidate.

- English: `Next step: <candidate>`
- Korean: `다음 단계: <후보>`

## Rules

- There are three verdicts: Verified, Failed and Inconclusive. Inconclusive is not a pass.
- Evidence for Verified is real output. "It builds" is not evidence of behavior.
- Do not cite a principle that you did not read in this session.
- Do not hand the user a check that you can run yourself.
- When more than 5 decisions are unconfirmed, recommend `playbooks/checkpoint.md` as the next step.
- State facts only. Do not add praise or closing remarks.
