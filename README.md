# CVPR Submission Toy Project

This repository is now organized as a versioned set of small CVPR-style VLM
preference-tuning studies.

## Current Status

V1 has been archived under `v1/`. Its final conclusion is diagnostic: adding
template-level evidence hints to DPO responses slightly reduces some
false-positive rates, but does not consistently outperform plain Answer-DPO on
accuracy, F1, hard negatives, or base-error recovery.

The active paper path is V2 / CEPO-Probe:

```text
idea-evidence-grounded-preference-vlm/
```

V2 changes the research question from response-level evidence style to
claim-evidence preference:

> Can VLM preference tuning improve grounding when each visual claim is paired
> with verifiable object, attribute, or relation evidence?

V2 now has a completed CEPO-Probe benchmark-paper path: local data construction
and audits are lightweight, while 7B training and full evaluation are submitted
through Slurm. CEPO-Latent did not beat Answer-DPO on the primary short-answer
metrics, but the CEPO-Dual follow-up is complete and is now the selected third
main group for the benchmark paper.

The generated sidecar artifacts live under:

```text
data/processed/cepo/
experiments/llamafactory_data_cepo/
data/processed/cepo_dual/
experiments/llamafactory_data_cepo_dual/
data/eval/cepo_evidence_probe.jsonl
data/eval/cepo_wrong_evidence_probe.jsonl
```

## Project Layout

```text
v1/
  README.md
  idea-lightweighted-grounded-preference-vlm/
  idea-imporve-evidence/
  tasks/
```

Archived V1 plans, diagnostics, method variants, and rescue experiments.

```text
idea-evidence-grounded-preference-vlm/
  reusable_assets.md
  plan.md
  experiment_plan.md
  next_experiment_plan.md
```

Active V2 outline: what to reuse from V1, the new CEPO project framing, and the
planned experiment schedule. `next_experiment_plan.md` records the CEPO-Dual
follow-up after the CEPO-Latent result.

```text
cepo-probe-benchmark-paper/
  README.md
  conversion_plan.md
  benchmark_spec.md
  experiment_blueprint.md
  final_results.md
  paper_draft.tex
```

Benchmark/diagnostic-paper prototype for pivoting the project from a
method-centered CEPO story to CEPO-Probe: a claim-evidence consistency
benchmark. `final_results.md` records the selected three-group comparison and
the numbers now ported into `paper/main.tex`.

```text
cepo-probe-benchmark-improve/
  README.md
  project_plan.md
  experiment_outline.md
  operation_checklist.md
  artifacts/
```

Review-driven next-step plan based on `official-review/20260528.md`. It keeps
the main paper benchmark-first while planning confidence intervals, parser/BEM
clarification, CEPO-Dual verifier-count ablations, and relation-failure
analysis needed to strengthen the draft toward a 6-page CVPR-style submission.

```text
futurework-grounded-preference-vlm/
  experiment_plan.md
  index.html
```

Broader brainstorm for evidence-grounded preference optimization. V2 is the
smaller, executable version of that direction.

```text
scripts/data/
scripts/eval/
scripts/experiments/
experiments/
paper/
data/
outputs/
results/
```

Shared infrastructure and generated artifacts retained from V1. These remain
useful for V2, especially the data audit, leakage check, Slurm, LLaMA-Factory,
and evaluation pipelines.

```text
data/processed/cepo/
experiments/llamafactory_data_cepo/
```

V2 CEPO canonical data, Answer-DPO/CEPO-Latent/CEPO-Dual exports,
audit/check summaries, and LLaMA-Factory registry files.

## What Carries Forward From V1

Reusable:

- Canonical pair construction and DPO export pattern.
- Train/eval image leakage checks.
- Audit-sheet workflow.
- Qwen2.5-VL-7B + LoRA-DPO + ZeRO-2 training setup.
- Unified VLM inference and yes/no scoring scripts.
- COCO/GQA/Hard COCO/Base-error/POPE/AMBER eval files.
- CVPR LaTeX paper skeleton and 6-page writing discipline.

Not worth continuing as a main direction:

- More response-side `Evidence hint:` template variants.
- Evidence-ratio sweeps as the main experiment.
- More same-style 10k/20k scale-up.
- Claiming that template hints solve object hallucination.

## V2 Direction

The proposed V2 method is **CEPO: Claim-Evidence Preference Optimization**.

The original CEPO-Latent comparison used three groups:

| Group | Method |
| --- | --- |
| A | Base Instruct |
| B | Answer-DPO |
| C | CEPO-Latent |

CEPO-Latent trains with compact claim-evidence blocks, but the main evaluation
still asks for short answers. A separate evidence-probe evaluation checks
whether the model learned evidence consistency rather than merely changing
yes/no bias.

The completed benchmark-paper comparison keeps the same three-group discipline
and uses CEPO-Dual as the evidence-aware baseline:

| Group | Method |
| --- | --- |
| A | Base Instruct |
| B | CEPO Answer-DPO |
| C | CEPO-Dual |

The fixed V2 run uses 6,000 preference rows:

| Slice | Rows |
| --- | ---: |
| COCO object existence | 2,000 |
| GQA attribute | 1,500 |
| GQA left/right relation | 1,500 |
| Wrong-evidence negatives | 1,000 |

The completed CEPO-Dual result supports this paper-level reading:

```text
CEPO-Probe shows that short-answer preference tuning and claim-evidence
verification are separable. CEPO Answer-DPO improves ordinary yes/no accuracy
but weakens wrong-evidence rejection, while CEPO-Dual improves explicit
evidence consistency without resolving relation reversals.
```

The main launch point for rerunning the CEPO-Dual matrix is:

```bash
bash experiments/slurm/submit_cepo_pipeline.sh
```

It submits the two ZeRO-2 LoRA-DPO training jobs and after-ok eval jobs for
COCO/GQA/Hard COCO/Base-error, POPE/AMBER, and the CEPO evidence probes.

To rebuild the 8,000-row dual-task export and submit the single ZeRO-2 training
job plus fixed eval matrix:

```bash
python scripts/data/14_export_cepo_dual_dpo.py
python scripts/experiments/prepare_llamafactory_data_cepo_dual.py
bash experiments/slurm/submit_cepo_dual_pipeline.sh
```

See:

- `idea-evidence-grounded-preference-vlm/reusable_assets.md`
- `idea-evidence-grounded-preference-vlm/plan.md`
- `idea-evidence-grounded-preference-vlm/experiment_plan.md`
- `idea-evidence-grounded-preference-vlm/experiment_run_2026-05-27.md`
- `idea-evidence-grounded-preference-vlm/next_experiment_plan.md`

## Environment Rules

Default shell setup follows `~/.zshrc`. Python environments use conda, and
package management should prefer `uv`.

Do not run heavy jobs directly in the interactive environment. Large data
movement, 7B training, GPU inference, and full benchmark evaluation should be
submitted through Slurm. GPU experiments should prefer ZeRO-2 unless there is a
specific reason to change it.

Do not run `git commit` or `git push` without explicit permission.

## Paper Build

The existing CVPR paper skeleton is under `paper/`. The current LaTeX
environment uses:

```bash
conda activate cvpr-latex
cd paper
make pdf
```

The V1 diagnostic draft previously built as `paper/build/main.pdf` and the
full version with appendix as `paper/build/main_full.pdf`. V2 should reuse the
template but replace the story with claim-evidence preference once experiments
exist.
