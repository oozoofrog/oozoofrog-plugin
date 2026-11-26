# fstack Korean entry validation

## Decision

Keep one user-facing entry point and the existing specialist resources. Ask for a result in Korean. Use the host-qualified fstack entry when predictable selection matters. Keep explicit specialist calls compatible. The remaining product preference is whether to type the entry name every time or let the host select a skill. Neither choice requires the user to learn the specialist names.

The owner first asked about combining the strengths of two packages. They then clarified that they wanted to keep only fstack and found the commands complicated. The earlier response about coexisting packages missed that preference. A question about simplifying usage should produce a usable example. It does not request a change to installed software.

## Inputs and controls

- The comparison case uses the owner's question from this conversation with its two specialist invocations removed. The simpler-usage case keeps the subsequent message verbatim, including its typo. Both cases get the same short package notes. They test the original request and the clarification independently. They do not replay a two-turn conversation.
- A separate performance fixture contains a single cold-cache 820 ms run and a single warm-cache 210 ms run. Its question and the state-diagram requests are authored probes. The runnable CSV case is an existing repository regression. None of these are owner quotes.
- The original upstream checkout is pstack 0.15.48. The baseline package is fstack 1.0.0 from repository revision `2b84dff`. Candidate runs used local snapshots. Each trial started in a new Claude Code 2.1.332 evaluation workspace with the Sonnet model selector. The session initialization records identify `claude-sonnet-5-5`, show 60 fstack skills and include neither a pstack plugin nor pstack-qualified skills. Built-in Claude tools remained available. No other user workflow plugin was needed.
- The 59 upstream skill names, 22 playbook filenames and two worker filenames all have counterparts in fstack. The index-link test covers every specialist SKILL.md except the index itself and the principle files. The latter are indexed by poteto-mode. Inventory checks establish reachability. They do not establish runtime parity for all 59 skills.
- Codex app-server `plugin/read` resolved the local marketplace ID `fstack@oozoofrog-plugin`, version 1.1.0 and 60 skills. Fresh-session behavior below was tested on Claude Code. Codex, Cursor and T3 automatic selection and external integrations were outside these runtime trials.

## Results

Each cell is the number of trials meeting the stated outcome. Each input had two trials per invocation style. The first four rows use the comparison snapshot. The fifth uses the final prompt-only route after a targeted correction. The cases are too small for a general success rate.

| Requested outcome | Korean request alone | Same request with /fstack:fstack | Evidence |
| --- | --- | --- | --- |
| Compare package strengths and give a combined example | 1/2 | 1/2 | One direct answer enumerated features, recommended replacing the install and asked for the upstream path. It omitted an example that combines the methods. |
| Explain simpler usage through fstack alone | 1/2 | 2/2 | A plain trial turned toward removing pstack and asked the user to choose what to change. Direct trials gave ordinary Korean examples, although some replies still added optional setup advice. |
| Judge the timing result already in the workspace | 2/2 | 2/2 | The responses identified unequal cache conditions and withheld the speedup claim. The 1.0.0 baseline had asked the user to paste the available result. |
| Compare the two implementations in report.py by running them | 2/2 | 2/2 | Python produced timings and memory measurements. Both direct trials failed only the legacy Skill-tool-call grader. Their session transcripts contain the direct slash command. All behavior graders passed. |
| Return only a ready-to-send statechart request with a model check and shortest counterexample | 0/2 | 1/2 automated | The two plain responses added guidance outside the prompt. Both direct answers contained the model check and shortest path and had no specialist invocation in the prompt. The judge rejected the longer, more prescriptive direct answer; the manual reading and raw score are kept separate. |

An additional direct trial used an order that could complete payment after cancellation. The agent returned only a Korean request, preserved that specific rule, and asked for a reachable-state check, a diagram and the shortest violating sequence. The grader passed it (1/1). This tested prompt composition on a new domain. No TLA+ model was run for a request that asked only for a prompt.

## Changes driven by failures

1. In the initial one-trial-per-case comparison, both the baseline and the first router answered the simpler-usage case. Only the new router opened the timing file and specialist checklist for the measurement case. Another candidate with a more generic trigger missed the file in one of two trials.
2. Before the implementation-comparison instruction explicitly required running both options, a plain CSV request produced source-reading advice or an unmeasured streaming recommendation. Adding “fstack으로 답해줘” to that version produced measured results in two of two trials. Keep explicit activation available and distinguish reading the source from measuring implementations.
3. Some package comparisons treated combining methods as installing two plugins. Keep upgrade and coexistence instructions in the installation guide, and show how a reusable method and project-specific verification work in one installation.
4. The specialist prompt probe exposed two separate failures. A generic reply could draw a diagram while omitting model checking. A technically correct reply could still give a specialist command and usage tips after “요청문만”. The revised entry identifies the next agent's task, reads its method, and gives an example of the requested output. The held-out order case tests whether that example can adapt to another rule.

## Reproduction

Run from the repository root. The tests are local and do not publish the report. The controller uses the existing authenticated Claude account. A normal test runner invocation chooses the output directory. On this Mac set TMPDIR and place --output-dir on /Volumes/eyedisk. For trace inspection, --keep-temp retains host-managed workspaces. This Claude version also creates its own /private/tmp/e-* sandbox roots on macOS.

```sh
claude plugin eval plugins/fstack --case 'entry-*' --runs 2 -j 2 --model sonnet --ablation none --scaffold --allow-tools Edit Write --trust-plugin --no-publish
claude plugin eval plugins/fstack --case under-prototype-ko --runs 2 -j 2 --model sonnet --ablation none --scaffold --allow-tools Bash Edit Write --trust-plugin --no-publish
python3 -I -S -B -m unittest discover -s scripts/tests
git diff --check
```

For the paired comparison, copy the entire plugin to scratch. Duplicate each selected case within that copy, use a distinct directory and case name, and prefix only the user message below its frontmatter with `/fstack:fstack `. Keep fixtures, model, tools, graders and trial count the same for both arms. Use `--json` to retain each report. Read the last response and tool outputs. For a direct invocation, check the command-name event in the session transcript. A host can expand a command without a model-issued Skill tool call.

The skill-creator validator accepts the public fstack entry. Its frontmatter allowlist rejects the existing Claude-specific disable-model-invocation key on poteto-help. Claude's own plugin validator accepts the package and reports a directory icon warning. The field preserves the existing explicit-only discovery policy for the specialist helper.
