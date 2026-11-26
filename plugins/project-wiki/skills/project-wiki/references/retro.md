# Retro

A retro turns the period's records into decisions the owner makes. Run it after a batch of work or a release, or when the owner says "위키 회고".

## Steps

1. Numbers: `python3 -I -B "<skill-dir>/scripts/wiki_lint.py" --summary [--since YYYY-MM-DD] <vault>`. It reads frontmatter only and gives episodes by outcome, lessons by status, lessons eligible for adoption (`worked` ≥ 2), lessons missed twice or more (`missed_often`), stale candidates (not seen for 30 days), encoded lessons without a target, and the inbox line count.
2. Run `wiki_lint.py <vault>` and fix errors first, so the numbers are right.
3. Inbox: move each line into an episode, a lesson or a knowledge note, or drop it with a reason. Empty the inbox.
4. Proposals. Read the bodies of only the lessons you propose to change:
   - candidate → adopted: eligible lessons whose rows show a real effect.
   - adopted → encoded: lessons that a check, test, script, memory entry or project rule can enforce. Name the target. Prefer structure > script or test > prose. Lessons under `missed_often` (`missed` ≥ 2) come first: prose did not keep them.
   - → retired: lessons that were wrong, were contradicted, or no longer apply. Keep the note and write the reason.
   - candidate with no new rows for a long time: keep, merge with a similar lesson, or retire.
   - global: an adopted lesson that also applies in another project (see below).
   - A lesson in both the adoption list and the encoding list is proposed only for encoding. Encoding supersedes adoption.
5. Present the proposals to the owner, each item with one line of evidence. Wait. Zero accepted items is a valid result.
   - First send the full list as a visible message, grouped by proposal kind.
   - A question tool holds only a few options. For a long list, ask per group with batch answers: all, a threshold (for example `worked` ≥ 3), "I will pick in the retro note", or defer all. Keep per-item decisions possible: when the owner picks in the note, read the note before you apply anything.
6. Contradictions: after the owner's decisions are recorded, list the lessons (any status, also `encoded`) that a decision contradicts, and propose retiring or rewriting them. Apply only what the owner accepts.
7. Apply only accepted items: change `status`, set `encoded_in`, and change the rule where it lives (memory entry, project rule, test). When you rename or delete a memory entry, update every `encoded_in` and `evidence` that names it; lint reports the ones you miss. Then run `wiki_guides.py <vault>`: it rebuilds the 원칙 and 이미 규칙으로 옮긴 것 sections of [[효과적인 지시 방법]] (owner side) and [[에이전트 대응 원칙]] (agent side) from the lessons. Do not copy an encoded rule's text into a guide.
8. Write the retro note in `60 회고/` from the template: period, numbers, inbox results, the status table (lesson, before, after, reason), and what to try next period for each side.
9. Lint again.

## Global vault

The global vault (`global_vault` in `~/.config/project-wiki/config.json`) holds lessons that are true beyond one project.

- Propose promotion when an adopted lesson has worked in two or more projects, or when the owner asks.
- Promotion copies the lesson into the global lessons folder, with `projects` listing each project name and the source note as a path (wikilinks do not cross vaults). The project note keeps its status and gains `global: <title>` in its body.
- The global copy is the one to update after promotion. Project notes keep their own application logs.
