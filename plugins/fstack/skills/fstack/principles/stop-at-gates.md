# Stop at gates

Inside the request, do not ask about work that a run or an approved decision can settle. Stop at gates G1–G3. After the scope of the request is met, stop unless the user granted drive.

**Why:** The request boundary is the user's grant of authority. Inside it, questions about reversible work only slow the user down. Past it, AI decisions accumulate faster than the user can review them.

**How:**
- G1: an irreversible or externally visible action: push, deploy, release, data deletion, outgoing messages, secrets, rewriting pushed history, deleting files you did not create.
- G2: a product or preference call that the user owns and no run can settle. Ask it once, batched with the other user-owned questions.
- G3: a change to the meaning of an approved document or a project rule.
- In step pace, finish the whole request, then stop and propose one next step in one line.
- In drive pace, park the gated unit, continue with the other units, and list the parked gates in the report.
- Adding conclusions to an approved document is not G3. Mark each such edit "needs confirmation".

**Stop:** Never take a gated action without the user's answer. Never start the next plan unit in step pace.

**Evidence of use:** the frame line (`Pace: … · Spec: …`) in visible reply text before the first file change; parked gates and the next-step line in the report.
