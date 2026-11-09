# Distributed System Project

A collaborative repository for a distributed systems course report, using the [official USENIX LaTeX template](https://www.usenix.org/conferences/author-resources/paper-templates) used by OSDI.
The report uses US Letter paper, two columns, and 10 pt text, with separate section files so teammates can write in parallel.
The CacheWise replication draft includes a historical six-policy experiment and a separate 60-run concurrency/held-out-cohort study, with workload plots, matched ablations, full eviction counts, and request-tail figures; recomputation and offloading analysis and secondary-storage methods remain future work, and author information still needs to be filled in.

## Getting started

1. Update the title, names, affiliations, and student IDs in `paper/main.tex`; add or remove author blocks as needed.
2. Record the topic, course requirements, section assignments, and deadlines in `notes/README.md`.
3. Edit your assigned sections in `paper/sections/`, replacing the `\draftnote{...}` placeholders as the draft develops.
4. Add verified sources to `paper/references.bib` and cite them with `\cite{citation-key}`.
5. Compile and inspect the PDF, then merge changes through branches and pull requests.

The shared bibliography includes the [CacheWise paper](https://arxiv.org/abs/2606.16824v1), with its citation details checked against the original paper.
The original paper already evaluates GPU–CPU DRAM offloading; this report plans to analyze recovery costs and methods for secondary storage, starting with local SSDs, without presenting existing DRAM offloading as a new contribution.
Add relevant literature and measured results as the report develops, and remove draft markers before submission.
Write the report in English and follow the instructor's length requirements.

## Report structure

1. **Introduction**: Motivation, three research questions, and expected contributions.
2. **Background and Related Work**: KV caching, CacheWise, the memory hierarchy, and existing offloading systems.
3. **CacheWise Replication: Experiments and Results**: Replication scope, experimental setup, results, ablations, and differences from the original paper.
4. **CacheWise Limitations: Recomputation versus Offloading**: Remaining recovery overhead, a cost model that includes writes and reads, break-even points, and conditions under which the comparison applies.
5. **Proposed Methods for Secondary-Storage KV Offloading**: Block storage and on-demand recovery, asynchronous transfer and prefetching, cost-based decisions, and implementation scope.
6. **Evaluation of the Proposed Offloading Methods**: End-to-end results, ablations, sensitivity, and resource costs.
7. **Discussion and Limitations**: Scope, failure cases, and threats to validity.
8. **Conclusion**: Summarize verified findings in the order of replication, cost analysis, methods, and evaluation.

Blue TODO notes in the report are writing prompts, not claims of completed implementations or experimental findings.
Any claim that offloading is cheaper must specify the comparison metric and the conditions under which it holds; do not assume it is universally true.
Verified replication results and separate uncached-request timings are stored in `notes/experiment-evidence/`; see its `manifest.json` for sources and checksums.
The coverage study includes cohort A at N=10/20/30 and two additional N=10 cohorts, totaling 60 runs and 6,384 requests; it is reported separately from the historical six-policy study.
One real preemption violated the original zero-preemption condition; the original rejection is preserved and a separate audit amendment is disclosed. Additional prefill work caused by that event remains unmeasured.
Full eviction counts do not measure actual KV bytes transferred, and no DRAM/SSD offloading comparison has been completed.

## Repository layout

```text
paper/
  main.tex             # Report entry point, title, authors, and shared packages
  usenix2019_v3.sty     # Unmodified official USENIX style
  TEMPLATE.md          # Official sources, checksum, and course adaptations
  sections/            # Abstract, introduction, background, replication, cost analysis,
                       # offloading methods, evaluation, discussion, and conclusion
  references.bib       # Shared BibTeX bibliography
  figures/             # Figures and their editable source files
  build/               # Build outputs (not committed)
notes/                 # Topic selection, assignments, reading notes, and experiment records
.github/workflows/     # Automated compilation and PDF artifacts
CONTRIBUTING.md         # Branching, review, and writing conventions
```

## Local compilation

Install [TeX Live](https://tug.org/texlive/) (a full installation is recommended) and make sure `xelatex`, `latexmk`, and `bibtex` are on PATH.
Run the following command from the repository root; it works in Windows PowerShell, macOS, and Linux:

```sh
latexmk -cd -xelatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build paper/main.tex
```

The PDF is written to `paper/build/main.pdf`. `latexmk` automatically runs BibTeX and resolves cross-references.
For a minimal TeX installation, install `xecjk`, `fandol`, `tex-gyre`, `koma-script` (including `scrlfile`), `amsmath`, `amsfonts`, `graphics`, `booktabs`, and `latexmk`,
along with the style and URL-handling packages `times`, `pslatex`, `microtype`, `sttools` (including `flushend`), `cite`, `url`, `xurl`, `xcolor`, `hyperref`, and their dependencies.

To clean build intermediates while keeping the final PDF:

```sh
latexmk -cd -c -outdir=build paper/main.tex
```

In VS Code, install the recommended LaTeX Workshop extension, open `paper/main.tex`, and select the `latexmk (XeLaTeX)` recipe.
The extension still requires a local TeX toolchain.

## Overleaf

1. On GitHub, select **Code → Download ZIP**.
2. In Overleaf, select **New Project → Upload Project** and upload the ZIP file.
3. Set Main document to `paper/main.tex` (if the import adds an outer directory, select the same file inside that directory).
4. Set Compiler to **XeLaTeX**, select a recent available TeX Live version, and click Recompile.

Use GitHub as the team's shared source of truth, and coordinate edits to avoid overwriting the same content between Overleaf and local copies.

## GitHub automated builds

Pushes, pull requests, and manual dispatches trigger [`Build paper`](https://github.com/ahz-r3v/Distributed-System-Project/actions/workflows/build-paper.yml).
After a successful run, download `paper-pdf` from that run's **Artifacts** and extract `main.pdf`; artifacts are retained for 14 days by default.
The same run also saves compilation logs as `paper-build-log` for troubleshooting failures.
GitHub Actions must be enabled for the repository.

Compilation uses the TeX Live 2026 environment provided by [latex-action](https://github.com/xu-cheng/latex-action).
Do not commit the compiled report PDF; PDF files used as figures may be committed.

## Collaboration

Create a task branch from `main`, such as `writing/introduction`, then open a PR and ask another teammate to review the source and PDF.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and [paper/TEMPLATE.md](paper/TEMPLATE.md) for template sources and adaptations.
