### Worktree cleanup

1. Inspect the actual target volume. Run the bundled scripts/worktree-audit.sh with an explicit base when the default branch differs. Its output is an inventory.
2. Use the active host's ownership and project-scoped activity records. For a complete, current check, supply a tab-separated snapshot with one absolute worktree path and one state per line using --activity FILE. Valid states are active, inactive and unknown. A pinned or recently used tree is active. Partial coverage and failed lookups are unknown. Recheck ownership immediately before removal.
3. Inspect changes, including untracked and ignored user files. Hold open PRs, unmerged work and active trees. Report missing ownership or PR evidence. Use the user's approved scope for any removal. Use git worktree remove on individually confirmed paths. A failed removal needs investigation.
4. Verify with git worktree list and disk usage on that volume. Simulator cleanup is a separate operation. Use the machine's device budget and ownership rules for a requested simulator cleanup.
