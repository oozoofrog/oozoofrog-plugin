# Real surface

Verify where the user meets the behavior. A green build or test run alone does not mean done. Inconclusive is not a pass.

**Why:** Tests run against the model of the system that their author had in mind. Wiring, configuration, startup order and real input formats fail outside that model.

**How:**
- Identify the surface: CLI output, an HTTP response, a rendered screen, a written file, a log line.
- Start the real program and drive it through that surface. Use the session's designated UI or browser tool for screens.
- Include at least one input that the tests do not cover.
- For a number, measure before and after under the same conditions. Name the limiting factor.
- If you cannot reach the surface, mark the item Inconclusive and say what blocked it.
- A result from before a later edit says nothing about the edited code. After each edit, rerun the checks that the edit could change. Keep the results that the edit could not change.

**Stop:** Do not say "done", "works" or "fixed" before a real-surface run on the final state. Do not hand the user a check that you can run yourself.

**Evidence of use:** a Verification row with the command or tool, the observed output and the verdict.
