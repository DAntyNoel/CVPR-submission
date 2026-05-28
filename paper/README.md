# CVPR Draft

This directory contains the CVPR 2026-format paper draft for the CEPO-Probe
benchmark paper. The current `main.tex` is a complete diagnostic manuscript
using a five-group 7B main comparison: Base Instruct, CEPO Answer-DPO,
Evidence-DPO-only, CEPO-Dual-1k, and CEPO-Dual-2k, plus Qwen2.5-VL-32B
transfer rows for Base, CEPO Answer-DPO, and CEPO-Dual-2k. This keeps the main
ablation at or below five groups while adding a larger-backbone sanity check.

Current files:

- `main.tex`: paper body with final CEPO-Probe benchmark framing, first-use
  CEPO acronym expansion, vector Figure 1 claim-evidence overview,
  ClaimEvidence-6K data description, preference-format setup, five-group
  short-answer transfer results, evidence-probe results with carefully bounded
  32B transfer rows, confidence intervals, parser-audit note, seed stability
  summary, paraphrased-probe diagnostic, relation error analysis, external
  sanity checks, limitations, and conclusion.
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
- `references.bib`: bibliography entries used by the draft, including public
  hallucination/evaluation benchmarks, multimodal preference-tuning work, and
  grounding/rationale datasets relevant to CEPO-Probe.
- `appendix.tex`: supplementary material included by `main_full.tex`,
  organized into reproducibility setup, additional quantitative checks, and
  qualitative/scoring analysis. It keeps the auxiliary CEPO-Dual-500 run out of
  the main five-group body while documenting the full ablation, three-seed
  stability check, row-preserving paraphrased probe, fixed-budget row-count
  control, locked relation-stress probe, and 32B transfer training setup
  including the ZeRO-3 preflight.
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

The paper now follows the completed CEPO-Probe interpretation: CEPO Answer-DPO
improves ordinary yes/no accuracy but weakens wrong-evidence rejection, while
direct verifier supervision recovers evidence behavior. Evidence-DPO-only
reaches 53.0% wrong-evidence rejection, CEPO-Dual-1k reaches 48.5%, and
CEPO-Dual-2k reaches 70.3% while preserving the short-answer gains. The
three-seed stability check is now complete: CEPO-Dual-2k improves
wrong-evidence rejection over CEPO Answer-DPO by +35.2 to +38.8 points while
keeping COCO/GQA/Hard accuracy essentially flat. Relation-stress analysis
narrows the remaining relation bottleneck to subject/object role swaps:
CEPO-Dual-2k reaches 71.25% overall relation-stress rejection, with 42.50%
swap rejection and 100% left/right reversal rejection. POPE/AMBER are reported
only as external sanity checks: CEPO-Dual-2k stays close to CEPO Answer-DPO, so
the paper does not claim a general hallucination-benchmark win.

The Qwen2.5-VL-32B transfer check is integrated into the main result tables as
a limited larger-backbone sanity check. CEPO-Dual-2k recovers the small
wrong-evidence drop of 32B CEPO Answer-DPO, moving from 23.8% to 24.5%, while
matching the 32B base and preserving COCO/GQA/Hard short-answer accuracy. The
paper now explicitly avoids presenting this as a large scaling gain. The
appendix records the 32B training ladder: ZeRO-2 OOM on 4090/L40S preflights,
BF16 ZeRO-3 fitting on 8xADA6000 but projecting too slowly, and the final
4-bit QLoRA + ZeRO-2 setting used for the reported 32B rows.

The row-preserving paraphrased CEPO-Probe check is also complete for Base,
CEPO Answer-DPO, and CEPO-Dual-2k. It keeps the same 600 supported and 400
wrong-evidence rows and labels while rewriting the prompt/evidence wording.
CEPO-Dual-2k keeps a wrong-evidence rejection advantage over CEPO Answer-DPO
under this wording shift: 73.2% vs 61.8%, with both at 90.0% supported
accuracy and 0.0 parse failures. The main text now states that the absolute
paraphrased numbers are not directly comparable to the original prompt; only
the within-probe ordering is used as template-robustness evidence.

Constant parser-audit columns such as JSON-object rate and parse failure are
kept in released metrics but omitted from paper tables because all reported
paper rows are 100.0% parseable with 0.0% parse failure. The main text now
clarifies that decoding is unconstrained and the JSON reliability comes from
the prompt plus deterministic parser audit, not constrained decoding.

The fixed-budget row-count control requested after the 2026-05-30 review is
complete under `v2/tasks/fixed-budget-control-experiments/`. Dual-2k-fixed6k
reaches 62.7% wrong-evidence rejection, +28.5 points over CEPO Answer-DPO-6k,
while COCO/GQA/Hard accuracy changes by only -0.1/+0.1/+0.1 points. The result
is integrated as appendix/control evidence; the main 7B ablation remains the
five-group comparison.

Related-work references were expanded on 2026-05-28 for the latest outer
`paper/` draft. The current citation set now situates CEPO-Probe against
CHAIR, POPE, MME, MMHal-Bench/LLaVA-RLHF, AMBER, HallusionBench,
hallucination-aware multimodal preference optimization, RLHF-V, Silkie, Visual
Genome, Flickr30k Entities, ReferItGame, and VQA-X.

Page budget:

- Main body target: 6-8 pages under the review style.
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
The CEPO-Probe PDF builds were verified on 2026-05-28 after the AC-facing
polish, vector overview figure, seed-stability integration, paraphrased-probe
integration, fixed-budget control integration, appendix compaction, and
relation-stress update: `build/main.pdf` is 8 pages and `build/main_full.pdf`
is 10 pages. The
remaining non-fatal warning is the upstream `lineno.sty` UTF-8 warning from
the bundled review style; there are no current overfull table warnings,
missing-reference warnings, or missing-citation warnings.

The draft currently uses review mode:

```tex
\usepackage[review]{cvpr}
```

Switch to `\usepackage{cvpr}` only for camera-ready formatting.
