# Submitted Seed-Stability Jobs

Submitted: 2026-05-28

Retry note: initial train jobs 64654, 64661, 64668, and 64675 hit SIGBUS
failures caused by concurrent cache rebuilding and shared-memory pressure. Their
dependent eval jobs were canceled. The active retry chains below use
`preprocessing_num_workers: 1`, `dataloader_num_workers: 0`, and serialized
same-dataset train dependencies.

| Seed | Model | Job type | Job ID | Output |
| ---: | --- | --- | ---: | --- |
| 13 | CEPO Answer-DPO | train | 64706 | `outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_seed13_zero2/` |
| 13 | CEPO Answer-DPO | eval COCO | 64707 | `results/eval/generations/coco_heldout_object_existence/cepo_seed_stability/seed13/cepo_answer_dpo.jsonl` |
| 13 | CEPO Answer-DPO | eval GQA | 64708 | `results/eval/generations/gqa_simple_heldout/cepo_seed_stability/seed13/cepo_answer_dpo.jsonl` |
| 13 | CEPO Answer-DPO | eval Hard COCO | 64709 | `results/eval/generations/coco_hard_object_existence/cepo_seed_stability/seed13/cepo_answer_dpo.jsonl` |
| 13 | CEPO Answer-DPO | eval BEM | 64710 | `results/eval/generations/base_error_mined_object_existence/cepo_seed_stability/seed13/cepo_answer_dpo.jsonl` |
| 13 | CEPO Answer-DPO | eval supported probe | 64711 | `results/eval/generations/cepo_evidence_probe/cepo_seed_stability/seed13/cepo_answer_dpo.jsonl` |
| 13 | CEPO Answer-DPO | eval wrong probe | 64712 | `results/eval/generations/cepo_wrong_evidence_probe/cepo_seed_stability/seed13/cepo_answer_dpo.jsonl` |
| 13 | CEPO-Dual-2k | train | 64720 | `outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_seed13_zero2/` |
| 13 | CEPO-Dual-2k | eval COCO | 64721 | `results/eval/generations/coco_heldout_object_existence/cepo_seed_stability/seed13/cepo_dual_dpo.jsonl` |
| 13 | CEPO-Dual-2k | eval GQA | 64722 | `results/eval/generations/gqa_simple_heldout/cepo_seed_stability/seed13/cepo_dual_dpo.jsonl` |
| 13 | CEPO-Dual-2k | eval Hard COCO | 64723 | `results/eval/generations/coco_hard_object_existence/cepo_seed_stability/seed13/cepo_dual_dpo.jsonl` |
| 13 | CEPO-Dual-2k | eval BEM | 64724 | `results/eval/generations/base_error_mined_object_existence/cepo_seed_stability/seed13/cepo_dual_dpo.jsonl` |
| 13 | CEPO-Dual-2k | eval supported probe | 64725 | `results/eval/generations/cepo_evidence_probe/cepo_seed_stability/seed13/cepo_dual_dpo.jsonl` |
| 13 | CEPO-Dual-2k | eval wrong probe | 64726 | `results/eval/generations/cepo_wrong_evidence_probe/cepo_seed_stability/seed13/cepo_dual_dpo.jsonl` |
| 97 | CEPO Answer-DPO | train | 64713 | `outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_seed97_zero2/` |
| 97 | CEPO Answer-DPO | eval COCO | 64714 | `results/eval/generations/coco_heldout_object_existence/cepo_seed_stability/seed97/cepo_answer_dpo.jsonl` |
| 97 | CEPO Answer-DPO | eval GQA | 64715 | `results/eval/generations/gqa_simple_heldout/cepo_seed_stability/seed97/cepo_answer_dpo.jsonl` |
| 97 | CEPO Answer-DPO | eval Hard COCO | 64716 | `results/eval/generations/coco_hard_object_existence/cepo_seed_stability/seed97/cepo_answer_dpo.jsonl` |
| 97 | CEPO Answer-DPO | eval BEM | 64717 | `results/eval/generations/base_error_mined_object_existence/cepo_seed_stability/seed97/cepo_answer_dpo.jsonl` |
| 97 | CEPO Answer-DPO | eval supported probe | 64718 | `results/eval/generations/cepo_evidence_probe/cepo_seed_stability/seed97/cepo_answer_dpo.jsonl` |
| 97 | CEPO Answer-DPO | eval wrong probe | 64719 | `results/eval/generations/cepo_wrong_evidence_probe/cepo_seed_stability/seed97/cepo_answer_dpo.jsonl` |
| 97 | CEPO-Dual-2k | train | 64699 | `outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_seed97_zero2/` |
| 97 | CEPO-Dual-2k | eval COCO | 64700 | `results/eval/generations/coco_heldout_object_existence/cepo_seed_stability/seed97/cepo_dual_dpo.jsonl` |
| 97 | CEPO-Dual-2k | eval GQA | 64701 | `results/eval/generations/gqa_simple_heldout/cepo_seed_stability/seed97/cepo_dual_dpo.jsonl` |
| 97 | CEPO-Dual-2k | eval Hard COCO | 64702 | `results/eval/generations/coco_hard_object_existence/cepo_seed_stability/seed97/cepo_dual_dpo.jsonl` |
| 97 | CEPO-Dual-2k | eval BEM | 64703 | `results/eval/generations/base_error_mined_object_existence/cepo_seed_stability/seed97/cepo_dual_dpo.jsonl` |
| 97 | CEPO-Dual-2k | eval supported probe | 64704 | `results/eval/generations/cepo_evidence_probe/cepo_seed_stability/seed97/cepo_dual_dpo.jsonl` |
| 97 | CEPO-Dual-2k | eval wrong probe | 64705 | `results/eval/generations/cepo_wrong_evidence_probe/cepo_seed_stability/seed97/cepo_dual_dpo.jsonl` |
