# Fixed-Budget Control Experiment Plan

## Design

Use the existing CEPO-Dual export pipeline with different row counts:

| Variant | Model key | Answer rows | Supported verifier | Wrong verifier | Total |
| --- | --- | ---: | ---: | ---: | ---: |
| `answer4k` | `cepo_answer4k_dpo` | 4,000 | 0 | 0 | 4,000 |
| `dual1k_fixed6k` | `cepo_fixed6k_dual1k_dpo` | 5,000 | 500 | 500 | 6,000 |
| `dual2k_fixed6k` | `cepo_fixed6k_dual2k_dpo` | 4,000 | 1,000 | 1,000 | 6,000 |

All runs use Qwen2.5-VL-7B-Instruct, LoRA-DPO, ZeRO-2, seed 42, one epoch,
and the same deterministic eval prompts as the main paper.

## Metrics

Report COCO, GQA, Hard COCO, BEM recovery, supported-evidence accuracy,
wrong-evidence rejection, object/attribute/relation wrong-evidence rejection,
JSON-object rate, scored-output rate, and parse failure.

## Paper Integration Rule

If `Dual-2k-fixed6k - CEPO Answer-DPO-6k` wrong-evidence rejection is at least
+20 points and COCO/GQA/Hard accuracy is no more than 1 point worse, write the
result as evidence that verifier rows help beyond simple total-row count.

If the fixed-budget gain shrinks substantially or short-answer accuracy drops,
write the result as evidence that verifier supervision and additional training
volume both contribute.

The fixed-budget controls stay in the appendix/control discussion. They do not
alter the five-group main comparison.

## Commands

Submit:

```bash
bash experiments/slurm/submit_cepo_fixed_budget_pipeline.sh
```

Summarize after completion:

```bash
python scripts/eval/summarize_cepo_fixed_budget_results.py
```
