# CVPR Draft

This directory contains the CVPR 2026-format paper draft for the controlled
COCO/GQA evidence-hint DPO study. The current `main.tex` is a complete
diagnostic manuscript using the completed mixed Answer-DPO and mixed
Evidence-Hint DPO ZeRO-2 results.

Current files:

- `main.tex`: paper body with real mixed results, Hard COCO diagnostics,
  evidence-style prompt analysis, and Base-error-mined diagnostics.
- `main_full.tex`: standalone entry point that enables the appendix and writes
  `build/main_full.pdf`.
- `preamble.tex`: CVPR author-kit preamble helper, kept aligned with the
  official template structure.
- `local_xetex_fonts.tex`: local Tectonic/XeTeX font shim that forces T1 font
  encoding so the official PSNFSS Times/Helvetica families render with proper
  bold shapes.
- `rebuttal.tex`: official CVPR author-response template from
  `cvpr-org/author-kit`.
- `cvpr.sty`: official CVPR 2026 style file from `cvpr-org/author-kit`
  (<https://github.com/cvpr-org/author-kit>).
- `ieeenat_fullname.bst`: official bibliography style from `cvpr-org/author-kit`.
- `references.bib`: minimal bibliography entries used by the draft.
- `appendix.tex`: supplementary material included by `main_full.tex`.
- `Makefile`: Tectonic-based local build entry point.
- `rebuttal/`: simulated reviewer reports for the current PDF.

Author-kit alignment:

- Checked against `cvpr-org/author-kit` main commit
  `217fe7698116978ab2d972e2369a3d1567152f34` on 2026-05-27.
- `cvpr.sty`, `ieeenat_fullname.bst`, `preamble.tex`, and `rebuttal.tex` were
  copied directly from the official files at that commit.
- `main.tex` keeps the project manuscript body, but its documentclass,
  `cvpr` package selection, `preamble.tex` loading point, `hyperref` setup,
  paper-id block, title block, and author block follow the official template
  structure.
- The temporary author-kit clone used for replacement has been removed; the
  project does not vendor the author-kit repository.

The paper now follows the completed-result interpretation: template evidence
hints slightly reduce some false-positive object claims but do not consistently
outperform Answer-DPO across COCO/GQA/Hard COCO, evidence-style prompting, or
Base-error-mined diagnostics.

Page budget:

- Main body target: 6 pages preferred, with 7 pages acceptable and 8 pages as
  the hard CVPR-style upper bound.
- References plus optional appendix: keep within 10 pages.
- The normal review PDF excludes the appendix; the independent full-paper build
  includes it for internal review and supplementary inspection.

Build locally on the current machine with the user-level conda environment:

```bash
conda activate cvpr-latex
make pdf
```

This writes `build/main.pdf`. To compile the independent full paper with
appendix:

```bash
conda activate cvpr-latex
make full
```

This writes `build/main_full.pdf`. The environment currently uses Tectonic 0.16.9
because system-level TeX Live cannot be installed without sudo on this machine.
The diagnostic PDF builds were verified on 2026-05-27: `build/main.pdf` is 4
pages and `build/main_full.pdf` is 5 pages. The remaining non-fatal warning is
the upstream `lineno.sty` UTF-8 warning from the bundled review style; there
are no current overfull/underfull table warnings or Times/Helvetica
font-substitution warnings.

The draft currently uses review mode:

```tex
\usepackage[review]{cvpr}
```

Switch to `\usepackage{cvpr}` only for camera-ready formatting.
