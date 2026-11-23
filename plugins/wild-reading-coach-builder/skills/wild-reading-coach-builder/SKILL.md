---
name: wild-reading-coach-builder
description: "새 책의 PDF, EPUB, Markdown, 텍스트 또는 제공된 발췌로 야생 학습 방식의 개인 독서 코치 환경을 만들거나 새 판본을 준비할 때 사용한다. 책마다 근거 자료, 읽기 지도, 독립된 독자 기록을 갖춘 스킬을 생성한다."
---

# Build a wild-learning reading coach

Create a working, local coach for the target book. The target book supplies the content. Wild learning supplies the method. The common coaching instructions are in [assets/coaching.md](assets/coaching.md). The generated coach is self-contained. It can operate without this builder or the book 《야생 학습》.

## Identify and reuse the book

1. Locate the supplied source, actual title, edition, language, and intended workspace. If the reader has a print book only, use their contents pages, notes, or supplied passages to create a partial kit. Mark exactly what is available. If they give only a title, ask for material before claiming passage-level coverage. Accept subsequent excerpts without discarding earlier work.
2. Choose a stable ASCII skill name specific to this book and a private local destination. Check for an existing coach for this edition before installing tools or extracting any text. With a single source file, run the probe below using Python 3.9+ and paths appropriate for this book. Run the script relative to the builder’s own directory. The probe reads the source fingerprint and writes nothing. When it finds the existing coach, use its index and preserve its PROFILE.md. Repair missing references specifically if necessary. For a changed edition, use a distinct destination. Map prior reading to the new edition only with evidence and the reader’s agreement.
3. For multiple supplied files, use an ordered text manifest of source names and SHA-256 hashes as the fingerprint input. For later additions to a partial kit, update the relevant sections and index in place, identify the new coverage and update the source fingerprint after verification. Preserve the profile and previous section links.

```sh
python3 scripts/make_coach.py --source "$source_file" --name "$skill_name" --title "$book_title" --parent "$destination"
```

## Prepare the reading material once

Inspect the actual contents and representative pages. Derive the section boundaries from this book. Keep front matter, chapters, appendices, notes, and bibliography where they belong. For a collection, play, manual, or book without chapters, use the author’s own meaningful divisions. Preserve the original language of the text. Use the reader’s language for summaries, descriptions, and coaching.

- **PDF or scans.** Establish the mapping from PDF leaves to printed pages, including restarts or unnumbered leaves. Use native text where accurate. Render affected pages and use OCR when a text layer is absent or unusable. Check OCR against the images, especially names, digits and tables. Preserve uncertain readings explicitly. Reconstruct reading order across columns. Rejoin unambiguous line and page wraps while retaining paragraph, verse, code, and list boundaries.
- **EPUB, HTML, Markdown, or text.** Follow the spine or the author’s heading hierarchy. Preserve linked notes, images, tables, verse, and code. Use stable section or paragraph identifiers when printed pagination is unavailable. Do not invent page numbers.
- **Figures and tables.** Capture the full figure, including vector labels and arrows, as a PNG. Add a relative Markdown image link and a factual explanation of labels, spatial relationships, direction, and meaning in context. For tables, keep each printed fragment as a PNG and transcribe the cells into one Markdown table with the original columns and rows. Join continued tables and remove repeated column headers. Describe meaningful shading and merged cells. Render editable source fragments when a paginated capture does not exist.
- **Provenance.** Put page or section locators in HTML comments at the source boundaries, including in a continued paragraph or table row when needed. Give each footnote a stable Markdown reference and definition. Preserve nested and continued notes. Keep explanation separate from source text.
- **Index.** Write references/INDEX.md with a relative link, original heading, verified range or locator, and three to five specific summary sentences for each substantive unit. For fiction, give a spoiler-light public index and reserve later plot details for the relevant section. For excerpts, state the limits of coverage, including which sections can support a question. Keep reader-specific data outside references.

## Publish and check

Review the source and prepared references before packaging. Compare section boundaries, first and last lines, figure labels, footnote associations, table dimensions, and a passage spanning a page break. Resolve every local index and asset link. Match the number of logical units to the target edition. Install missing extraction dependencies only for this initial preparation or a requested repair.

Run the same command with `--references "$reviewed_references"`. The script copies the reviewed corpus, writes the coaching instructions and UI metadata, and publishes the completed directory. Use a stable symlink in the personal Codex skills directory if the chosen destination is elsewhere. Check an existing link before creating one. Preserve unrelated entries.

To give an existing coach the current coaching instructions, run the same command with `--update-coaching` and the same source. The script replaces only the instructions in that coach’s SKILL.md, keeps the earlier file as SKILL.md.previous, and leaves the references and PROFILE.md unchanged.

Open the published index and follow an actual passage link. Walk through a reading recommendation, a five-problem sequence, a return visit, and the experiment page loop against this book. Verify that the proposed sequence uses each preceding answer and that only reported reading enters the private profile. For the page loop, verify that the page holds no book text, that the reported result appears beside the unchanged prediction, and that page use adds no confirmed reading. Use scratch state for trials. Deliver the new skill name and the index location. Regular reading uses the published coach directly.
