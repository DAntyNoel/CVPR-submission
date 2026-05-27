# CVPR Draft

This directory contains the CVPR 2026-format paper draft for the controlled
COCO/GQA evidence-hint DPO study.

Current files:

- `main.tex`: paper body with result placeholders.
- `cvpr.sty`: official CVPR 2026 style file from `cvpr-org/author-kit`
  (<https://github.com/cvpr-org/author-kit>).
- `ieeenat_fullname.bst`: official bibliography style from `cvpr-org/author-kit`.
- `references.bib`: minimal bibliography entries used by the draft.
- `appendix.tex`: optional appendix skeleton, currently disabled in `main.tex`.

The draft is intentionally conservative until the mixed Evidence-Hint DPO
adapter and full mixed evaluation results are available. Replace the result
placeholders in Section 4 and the case-study placeholder in Section 4.4 after
the Slurm evaluation jobs finish.

Page budget:

- Main body target: 6 pages preferred, with 7 pages acceptable and 8 pages as
  the hard CVPR-style upper bound.
- References plus optional appendix: keep within 10 pages.
- Appendix is optional and should remain disabled unless extra templates,
  training details, or case studies are genuinely needed.

Build locally with:

```bash
latexmk -pdf main.tex
```

The draft currently uses review mode:

```tex
\usepackage[review]{cvpr}
```

Switch to `\usepackage{cvpr}` only for camera-ready formatting.

Compilation was not verified in the current workspace because `latexmk`,
`pdflatex`, and `tectonic` are not installed in the active environment.
