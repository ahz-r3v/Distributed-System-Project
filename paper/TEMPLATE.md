# OSDI / USENIX template provenance

This repository is for a distributed systems course report and uses the official general-purpose USENIX paper style.
The official OSDI call for papers points authors to the USENIX template resources.

- [Official template page](https://www.usenix.org/conferences/author-resources/paper-templates)
- [Official LaTeX example](https://www.usenix.org/sites/default/files/usenix2019_v3.2.tex)
- [Official style file](https://www.usenix.org/sites/default/files/usenix2019_v3.sty)
- [Official sample PDF](https://www.usenix.org/sites/default/files/usenix2019_v3.2.pdf)
- [OSDI '27 formatting requirements](https://www.usenix.org/conference/osdi27/call-for-papers)

## Source record

- Retrieved on: 2026-11-08.
- Local file: `usenix2019_v3.sty`, downloaded from the official URL above without modification.
- Original file SHA-256: `4ed9aa9d0c5daec54ce3b4188a4bf6d3bef3462c79ff65551d567511d3c45ff6`.
- The `2019` in the filename is part of the official download's name; it does not mean this project follows OSDI 2019 submission rules.
- The upstream comments and provenance are preserved; this repository does not assign a separate license to that third-party file.

## Project adaptations

- Use US Letter paper, two columns, 10 pt body text, and the official style's 7 × 9 inch text area.
- Use XeLaTeX and TeX Gyre Termes, a Times-compatible font; the template also retains Fandol font support for Chinese text.
- Use `scrlfile` in the entry point to skip the dvips-only `breakurl` package and let `hyperref` handle URLs; disable the pdfTeX-only spacing / kerning features in `microtype` for XeLaTeX compatibility.
- Load fonts directly from files distributed with TeX, without requiring separate operating-system font registration.
- Use the official example's BibTeX `plain` bibliography style, with the shared bibliography in `references.bib`.
- Split the text into `sections/`, retaining author information fields, page numbers, and visible draft markers.
- Preserve the official style's margins, column widths, and title layout.

This is a starting point for the course report. Fill in the title, authors, and student IDs, and follow the course requirements for language and length.
For a future conference submission, check that edition's anonymity, page-limit, and other requirements again.
