### Drive
**You own the exit predicate. Drive to it without stopping on reversible work.**

1. If you have not sent the frame line (`Pace: drive · Spec: …`) as visible reply text, send it now, before the next tool call. "Without stopping" means no waiting for answers. It does not mean no text. Quote the user's grant. Write the predicate as a pass/fail check. Capture a baseline.
2. Split the work into verifiable units. Put the riskiest unknown first. Run the macro lens once on the split when `references/review.md` assigns one.
3. For each iteration: hypothesis → smallest change → check → keep or revert. The drive grant allows a local commit for each kept change. Push stays G1.
4. Fix side issues that block the predicate, each in its own local commit. Log the other side issues.
5. On a gate hit, park that unit and continue with the others. Never take the gated action.
6. Write one trail row per iteration (`references/records.md`). To wait for an external event, use the host's wait or monitor tool. Do not busy-poll.
7. Stop at the first of two events: the predicate passes, or you reach a genuine dead end. When the predicate passes, run the micro lens on the final diff and close each finding; park gate findings. On a plateau, change the approach. Never relax the predicate. If the session must end first, use handoff; the fallback is a resume note in the report.
8. Run `playbooks/wrap-up.md`.

**Report:** predicate, iterations, what landed, what was discarded, final state, parked gates, decision ledger.
