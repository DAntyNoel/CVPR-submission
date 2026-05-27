# CVPR Draft

This directory contains the CVPR 2026-format paper draft for the controlled
COCO/GQA evidence-hint DPO study. The current `main.tex` is a complete
review-ready manuscript written under the user-requested assumption that the
mixed Evidence-Hint DPO experiment completes normally and yields the reported
positive trend.

Current files:

- `main.tex`: paper body with assumed-normal main results and analysis.
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
- `appendix.tex`: optional appendix skeleton, currently disabled in `main.tex`.
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

The Evidence-Hint numbers in the paper should be treated as an assumed-normal
writing target until the final Slurm logs and evaluation summaries are
available. Before a real submission, replace or verify these values against the
completed mixed Evidence-Hint DPO adapter and held-out evaluation outputs.

Page budget:

- Main body target: 6 pages preferred, with 7 pages acceptable and 8 pages as
  the hard CVPR-style upper bound.
- References plus optional appendix: keep within 10 pages.
- Appendix is optional and should remain disabled unless extra templates,
  training details, or case studies are genuinely needed.

Build locally on the current machine with the user-level conda environment:

```bash
conda activate cvpr-latex
make pdf
```

This writes `build/main.pdf`. The environment currently uses Tectonic 0.16.9
because system-level TeX Live cannot be installed without sudo on this machine.
The PDF build was verified on 2026-05-27. The remaining non-fatal warning is
the upstream `lineno.sty` UTF-8 warning from the bundled review style; there
are no current overfull table warnings or Times/Helvetica font-substitution
warnings.

The draft currently uses review mode:

```tex
\usepackage[review]{cvpr}
```

Switch to `\usepackage{cvpr}` only for camera-ready formatting.
