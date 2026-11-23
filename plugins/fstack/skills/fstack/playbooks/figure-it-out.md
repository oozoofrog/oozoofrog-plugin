### Figure it out
**You own the workflow design before execution.**

1. Write the exit condition. If you cannot write it, ask the user.
2. Choose the nearest playbook. Note how this task differs from it.
3. Design the steps:
   - Capture a baseline before the change.
   - Verify on the same surface as the baseline.
   - End with wrap-up.
   - Scale rigor to reversibility.
4. Show the design once. If no step is irreversible, proceed without waiting.
5. Execute. Give each verdict as Verified, Failed or Inconclusive. If something passes too easily, suspect the measurement first.
6. If an artifact models real behavior, compare one verdict against a real run.
7. Run `playbooks/wrap-up.md`. Log "no playbook fit" and the request type.

**Report:** steps, nearest playbook and differences, verdict table, mocked parts.
