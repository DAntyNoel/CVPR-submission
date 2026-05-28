# Seed Stability Job Manifest

Status: submitted on 2026-05-28.

## Submitted Jobs

| Seed | Model | Train job | Eval jobs |
| ---: | --- | ---: | --- |
| 13 | CEPO Answer-DPO | 64706 | 64707 COCO, 64708 GQA, 64709 Hard COCO, 64710 BEM, 64711 supported probe, 64712 wrong-evidence probe |
| 13 | CEPO-Dual-2k | 64720 | 64721 COCO, 64722 GQA, 64723 Hard COCO, 64724 BEM, 64725 supported probe, 64726 wrong-evidence probe |
| 97 | CEPO Answer-DPO | 64713 | 64714 COCO, 64715 GQA, 64716 Hard COCO, 64717 BEM, 64718 supported probe, 64719 wrong-evidence probe |
| 97 | CEPO-Dual-2k | 64699 | 64700 COCO, 64701 GQA, 64702 Hard COCO, 64703 BEM, 64704 supported probe, 64705 wrong-evidence probe |

All eval jobs were submitted with `afterok` dependencies on their corresponding
training job.

Initial jobs 64654, 64661, 64668, and 64675 failed before useful completion
because concurrent cache rebuilding triggered SIGBUS failures. Their dependent
eval jobs were canceled. The active retries set `preprocessing_num_workers: 1`
and `dataloader_num_workers: 0`; same-dataset retries are serialized to avoid
cache races.

## Planned Matrix

| Seed | Model | Training data | Adapter output | Eval output variant |
| ---: | --- | --- | --- | --- |
| 42 | CEPO Answer-DPO | existing V3 run | `outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2` | `cepo_dual` |
| 42 | CEPO-Dual-2k | existing V3 run | `outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2` | `cepo_dual` |
| 13 | CEPO Answer-DPO | same as V3 | `outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_seed13_zero2` | `cepo_seed_stability/seed13` |
| 13 | CEPO-Dual-2k | same as V3 | `outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_seed13_zero2` | `cepo_seed_stability/seed13` |
| 97 | CEPO Answer-DPO | same as V3 | `outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_seed97_zero2` | `cepo_seed_stability/seed97` |
| 97 | CEPO-Dual-2k | same as V3 | `outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_seed97_zero2` | `cepo_seed_stability/seed97` |

## Required Evaluations Per New Adapter

```text
data/eval/coco_heldout_object_existence.jsonl
data/eval/gqa_simple_heldout.jsonl
data/eval/coco_hard_object_existence.jsonl
data/eval/base_error_mined_object_existence.jsonl
data/eval/cepo_evidence_probe.jsonl
data/eval/cepo_wrong_evidence_probe.jsonl
```

External POPE/AMBER can be skipped for the first seed pass unless short-answer
metrics drift by more than 1 point.

## Implementation Note

The existing V3 training scripts are single-output scripts. This submission uses
seed-specific configs plus `experiments/slurm/train_cepo_seed_stability_dpo.slurm`
so reruns do not overwrite the locked V3 adapters. The submission helper now
serializes seed-13 and seed-97 training within each dataset family.

Do not set `ALLOW_OVERWRITE=1` for these runs.
