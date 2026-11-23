### Design docs
**You own the links between the documents. Do not implement.**

1. Reread the kickoff decisions. Before you rewrite a document, record its ID list and ID counts as a baseline.
2. Ask the ADR-level questions first. Ask only the questions that no prototype can settle.
3. Write the spec, then the domain doc (only for new terms or rules), then the ADR (in the project's format if it has one), then the plan. Use `references/doc-templates.md`.
4. Give each requirement an ID. Point each plan unit at IDs. List the units in landing order with a dependency graph, the files each unit touches and its verification, including one live-surface check.
5. Mark each decision Approved or Proposed.
6. Probe the documents with boundary inputs. Fix each gap you find.
7. From the project root, run `python3 -I -B "<skill-dir>/scripts/trace.py" --no-tests` (`principles/trace-by-id.md`). Compare the result with the baseline.
8. Run `playbooks/wrap-up.md`. Start execution only when the user says go.

**Report:** documents written, ID counts, user-decided and AI-proposed decisions (high impact first), check output, gaps, narrowed meanings.
