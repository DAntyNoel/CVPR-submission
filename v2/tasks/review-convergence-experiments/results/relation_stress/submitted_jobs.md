# Completed Relation-Stress Jobs

Submitted: 2026-05-28
Completed: 2026-05-28

Probe:

```text
v2/tasks/review-convergence-experiments/results/relation_stress/relation_stress_probe.jsonl
```

Probe summary:

- rows: 240;
- subject/object swaps: 120;
- left/right reversals: 120;
- unique images: 169;
- missing images: 0.

| Model | Job ID | Output |
| --- | ---: | --- |
| Base Instruct | 64682 | `results/eval/generations/relation_stress_probe/relation_stress/base.jsonl` |
| CEPO Answer-DPO | 64683 | `results/eval/generations/relation_stress_probe/relation_stress/cepo_answer_dpo.jsonl` |
| CEPO-Dual-2k | 64684 | `results/eval/generations/relation_stress_probe/relation_stress/cepo_dual_dpo.jsonl` |

Metric summary:

| Model | Wrong rejection | Swap rejection | Left/right rejection | False accept |
| --- | ---: | ---: | ---: | ---: |
| Base Instruct | 60.83 | 21.67 | 100.00 | 39.17 |
| CEPO Answer-DPO | 55.42 | 10.83 | 100.00 | 44.58 |
| CEPO-Dual-2k | 71.25 | 42.50 | 100.00 | 28.75 |
