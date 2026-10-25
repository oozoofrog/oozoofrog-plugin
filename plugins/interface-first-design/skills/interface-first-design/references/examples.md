# Visible paths and preserved meaning

These are synthetic design examples, not tested product outcomes.

## Collection screen

An introduction says, “This workspace helps you organize records. Use the plus icon to get started.” Replace its instructional burden with a **Records** heading, a visible **Create record** button, and records grouped by their actual names and statuses. First use shows the same creation action in the empty list. A filter with no matches shows **No matching records** and **Clear filters**; it does not imply that the collection is empty. Loading keeps the heading and controls stable and shows **Loading records…**. Failure exposes **Records couldn’t load** and **Retry**.

Known data: **Maple · 7 records · 1 needs review** and **Elm · 0 records**. Keep those facts. Elm’s review count is unknown; leave it unspecified or identify it as unavailable when the layout requires a value. Do not fill in zero to complete a tidy table.

Checks: open a record, create/cancel, filter/clear, load/fail/retry, use keyboard focus and a narrow touch layout. Each proposed check remains unverified until exercised.

## Review and upload

A review banner explains comparison and commenting. Replace it with persistent **Before**, **After**, comparison-mode selection, and **Add comment** controls. Retain filenames, the measured difference, and the user’s comment exactly. A failed save keeps the draft beside **Not saved** and **Retry save**. Show **Saving…** during retry and **Saved** only after confirmation. Keep editing and cancellation usable; verify retry does not duplicate comments. A screenshot cannot establish that saving works.

For **Upload pending · 3 of 8**, preserve that wording until the count’s meaning is established. Do not rewrite it as “3 uploaded, 5 pending.” Color-only status needs a label based on the actual status model, not an assumed meaning of red or green. A visible **Edit photo** action can replace a long-press tutorial; long press remains optional. Destructive controls name their target and consequence. Keep the actual upload error, local work, recovery control, and location-consent disclosure at the relevant decision.

## Essential text counterexample

“Remove all labels so the UI speaks for itself” fails the task. Labels, data, user notes, accessible names, errors, and consent are how the interface communicates. Shorten redundant instructions after making their function visible. Technical review prose may explain the issue and evidence; this skill does not impose product-copy limits on the agent’s report.
