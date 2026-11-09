# Collaborative writing conventions

## Branches and review

1. Update your local copy from the GitHub default branch, then create a task branch such as `writing/introduction`, `figures/architecture`, or `codex/update-related-work`.
2. Use an issue or `notes/` to identify the target section, owner, and related figures, reducing simultaneous edits to the same paragraphs.
3. Keep each commit focused on one content change, for example `docs: clarify the failure model`.
4. Push the task branch and open a PR describing the rationale, evidence sources, and compilation results.
5. Review the text and generated PDF, and merge after the automated build passes; review by at least one other author is recommended.

These are team conventions; branch protection rules must be configured separately in the repository settings.

## Text and formatting

- Put each sentence on its own line where practical, and avoid unrelated diffs caused by reflowing entire paragraphs.
- Use UTF-8 and LF line endings; `.editorconfig` and `.gitattributes` provide shared settings.
- Write content in `paper/sections/` and keep shared packages and commands in `paper/main.tex`.
- Use the prefixes `sec:`, `fig:`, `tab:`, and `eq:` for labels, and refer to them with `\ref{...}` rather than hard-coded numbers.
- Mark unfinished content with `\draftnote{...}`. Find and remove all placeholders before submission.
- Commit template changes separately from changes to the report text.
- The report uses the OSDI / USENIX format; do not edit the official `paper/usenix2019_v3.sty` directly.
- Use BibTeX with the `plain` style; do not also load `biblatex`, which conflicts with the official style's `cite` package.

## References and evidence

- Maintain references in `paper/references.bib` and check for duplicates before adding entries.
- Prefer citation keys in the form `FirstAuthorYearKeyword`; verify authors, title, year, and DOI/URL against the publisher or original paper.
- Do not add placeholder papers, unverified citations, or fabricated experimental conclusions.
- Clearly distinguish research hypotheses from verified findings; link experimental results to data, script versions, parameters, and the execution environment.
- Include source links and relevant page numbers in reading notes so collaborators can verify them.

## Figures and experiment records

- Store figures in `paper/figures/`, retain editable sources or generation scripts, and document how to regenerate them.
- Use short English filenames, such as `system-architecture.pdf`.
- Use accessible external links for large raw datasets and full texts of third-party papers, recording versions or checksums.
- Do not commit build caches; use Actions PDF artifacts to share drafts.

## Before committing

- Compile using the README command and inspect equations, figures, tables, page breaks, and citations in the PDF.
- Fix undefined citations and cross-references, and inspect layout warnings about overflowing content.
- Run `git diff --check` to check whitespace and confirm that the staging area contains only the intended changes.
- If you do not have a local TeX environment, note this in the PR and wait for the GitHub build result.
