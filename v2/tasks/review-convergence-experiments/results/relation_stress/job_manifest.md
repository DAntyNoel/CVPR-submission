# Relation-Stress Job Manifest

Status: completed on 2026-05-28.

Submitted jobs:

| Model key | Job ID |
| --- | ---: |
| `base` | 64682 |
| `cepo_answer_dpo` | 64683 |
| `cepo_dual_dpo` | 64684 |

Completion:

- all three jobs completed successfully;
- metrics copied to `metrics.csv`;
- CEPO-Dual-2k reaches 71.25% overall wrong-evidence rejection;
- the hard residual slice is subject/object swap rejection at 42.50%, while
  left/right reversal rejection is 100.00%.

## Probe Build

Target file:

```text
v2/tasks/review-convergence-experiments/results/relation_stress/relation_stress_probe.jsonl
```

Recommended size:

- 200-300 rows total;
- held-out GQA images only;
- balanced subject/object swaps and left/right reversals when possible;
- no overlap with training images.

Current probe:

- total rows: 240;
- subject/object swaps: 120;
- left/right reversals: 120;
- unique images: 169;
- missing images: 0.

## Planned Evaluation Matrix

| Model key | Adapter | Output variant |
| --- | --- | --- |
| `base` | none | `relation_stress` |
| `cepo_answer_dpo` | `outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2` | `relation_stress` |
| `cepo_dual_dpo` | `outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2` | `relation_stress` |

## Required Outputs

```text
results/eval/generations/relation_stress_probe/relation_stress/base.jsonl
results/eval/generations/relation_stress_probe/relation_stress/cepo_answer_dpo.jsonl
results/eval/generations/relation_stress_probe/relation_stress/cepo_dual_dpo.jsonl
results/eval/generations/relation_stress_probe/relation_stress/base.metrics.json
results/eval/generations/relation_stress_probe/relation_stress/cepo_answer_dpo.metrics.json
results/eval/generations/relation_stress_probe/relation_stress/cepo_dual_dpo.metrics.json
```

After scoring, copy the summary metrics into `metrics.csv` and sample
qualitative cases into `qualitative_cases.md`.
