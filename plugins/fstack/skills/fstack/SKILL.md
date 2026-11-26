---
name: fstack
description: "Use fstack for repository engineering tasks that need implementation, investigation, review or verification, and for explicit pstack-style workflows."
---
# fstack

For a named skill, open its SKILL.md from the sibling directory in this installation. For a review of a diff, keep the review read-only and report verified findings. For competing implementations, use the [Prototype playbook](../poteto-mode/playbooks/prototype.md) to measure them; use [arena](../arena/SKILL.md) when independent candidate artifacts are requested. For an engineering task, follow [poteto-mode](../poteto-mode/SKILL.md) and its matching playbook. For a question about the available workflows, use [poteto-help](../poteto-help/SKILL.md). Model and budget setup is optional.

Read [the host profile](references/host.md) before a host operation. Apply repository and user instructions throughout. External actions require the scope and authorization applicable to that host. Report the outcome, evidence, and any incomplete step.

If the repository uses a project wiki or journal, use [records](references/records.md) to write its episode before an authorized commit. For existing projects that verify numbered acceptance criteria, the retained checker runs from the project root with `python3 <this-skill>/scripts/trace.py`.
