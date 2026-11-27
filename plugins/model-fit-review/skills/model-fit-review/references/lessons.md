# Lessons from the first run of this procedure

Each lesson is a failure that happened once and the rule that prevents it.

1. **Only human messages count.** In a T3 Code DB, many `role='user'` rows are delegation results, notices and messages from other sessions. Keep rows with `createdBy='user'` and `creationSource` in (`web`, `mobile`). In Claude Code logs, skip tool results, `isMeta` and sidechain entries, and text that starts with `<` (system reminders, command output), but keep slash commands (`<command-name>` wrappers). `mfrlib.is_t3_human` and `mfrlib.log_human_text` encode this.

2. **Count distinct runs; separate reaction from steer.** A run can carry several human messages, so counting (run, message) pairs inflates the run count, and many "next messages" are sent before the run finished. The reaction to a result is the first human message after the run's `completed_at`. Messages sent while the run was going are steer, reported separately. If another run of the thread completed before that message, the user reacted to the later result: `pre_result`. `mfrlib.assign_reactions` encodes this.

3. **Session commands are not tasks.** `/compact`, `/clear`, `/reload-*`, `/mcp`, `/output-style` (and the same commands typed on a Korean keyboard layout) are excluded. A rule that dropped every slash message also dropped real tasks such as a slash-invoked skill with text and `/init`. `mfrlib.is_control` encodes the list.

4. **Calibrate classifiers before using their labels.** A follow-up classifier that met the 85 % gate against hand labels was used as data. A task-type classifier that missed the gate was used only for sampling, and no task-type rates were reported. Keep model names out of the items.

5. **A fix is not always the model's fault.** Fix reactions included the user's own mistaken facts, taste iteration on a design, results the user could not see yet, and process rules. Cards separate result fixes from method corrections.

6. **Pin everything a replay can read.** Replays that ran against today's machine read folders and a skill that the original episodes had created, so they saw the original answers. Only the replay whose inputs lived inside one pinned repository was valid. Use local clones with no remote, pinned to the commit before the episode, and check home config and sibling folders.

7. **The judge must check facts, and so must you.** A cross-vendor judge found that one candidate reported high-severity findings based on a feature that was disabled in the code. The main agent re-checked the decisive claims in the source. Without a different-vendor judge, report the missing independent verdict.

8. **Compare cost at equal context.** A replay in a fresh context used a small fraction of the tokens of the original step, which ran deep in a long thread and re-read its whole context on every call. The difference was context length, not the model.

9. **Practice design.** A pass mark the baseline already meets shows nothing; track over-picks instead. The guide between rounds cites only round-1 cards. When the misses fall on cards with `inferred` references while replay-backed cards are picked right, the data cannot tell whether the user over-picks or the references are too low. Record the evidence kind on every card and report the score per kind.

10. **Recurring corrections need mechanisms, not more text.** One rule ("ask questions as options") existed and kept being corrected; another ("answer in the user's language") existed and worked. A rule that applies to every reply stays in view; a rule that applies only at certain moments is missed. For the first kind, a dry-run check (Stop hook) on real turn endings measured catches and false alarms before install. A check must exempt lines that another standing instruction requires. Every change to global instructions, settings or hooks went through G2 with a backup.

11. **Move working files out of temporary storage first.** A session scratchpad can be cleared. Ask the user for the review directory before writing anything.

12. **Delete the DB snapshot at the end, with approval.** It can be several GB, and the scripts can rebuild everything from a fresh snapshot.
