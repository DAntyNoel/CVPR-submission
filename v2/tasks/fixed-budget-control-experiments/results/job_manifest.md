# Fixed-Budget Job Manifest

Status: complete. Submitted on 2026-05-28 15:49:39 +08:00; all expected
metric files are present.

Variants:

| Variant | Model key | Train output | Eval output variant |
| --- | --- | --- | --- |
| `answer4k` | `cepo_answer4k_dpo` | `outputs/llamafactory/qwen25vl7b_cepo_answer4k_dpo_zero2/` | `cepo_fixed_budget/answer4k` |
| `dual1k_fixed6k` | `cepo_fixed6k_dual1k_dpo` | `outputs/llamafactory/qwen25vl7b_cepo_fixed6k_dual1k_dpo_zero2/` | `cepo_fixed_budget/dual1k_fixed6k` |
| `dual2k_fixed6k` | `cepo_fixed6k_dual2k_dpo` | `outputs/llamafactory/qwen25vl7b_cepo_fixed6k_dual2k_dpo_zero2/` | `cepo_fixed_budget/dual2k_fixed6k` |

Prepared data:

| Variant | DPO JSONL | LLaMA-Factory JSON | Rows |
| --- | --- | --- | ---: |
| `answer4k` | `data/processed/cepo_fixed_budget/answer4k/cepo_dual_dpo_train.jsonl` | `experiments/llamafactory_data_cepo_fixed_budget/answer4k/cvpr_cepo_dual_dpo.json` | 4,000 |
| `dual1k_fixed6k` | `data/processed/cepo_fixed_budget/dual1k_fixed6k/cepo_dual_dpo_train.jsonl` | `experiments/llamafactory_data_cepo_fixed_budget/dual1k_fixed6k/cvpr_cepo_dual_dpo.json` | 6,000 |
| `dual2k_fixed6k` | `data/processed/cepo_fixed_budget/dual2k_fixed6k/cepo_dual_dpo_train.jsonl` | `experiments/llamafactory_data_cepo_fixed_budget/dual2k_fixed6k/cvpr_cepo_dual_dpo.json` | 6,000 |

Eval suite:

- `coco_heldout_object_existence`
- `gqa_simple_heldout`
- `coco_hard_object_existence`
- `base_error_mined_object_existence`
- `cepo_evidence_probe`
- `cepo_wrong_evidence_probe`
