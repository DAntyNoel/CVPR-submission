# Data Audit Summary

Updated: 2026-05-27

## Current Training Data

- Final canonical file: `data/processed/canonical_pairs_main.jsonl`
- Answer-DPO file: `data/processed/answer_dpo_train.jsonl`
- Evidence-Hint DPO file: `data/processed/evidence_hint_dpo_train.jsonl`
- Human audit sheet: `data/audit/audit_200.csv`

All three JSONL files contain 5,000 aligned records. The final data is
mixed COCO+GQA data:

- 3,500 COCO object-existence pairs.
- 1,500 GQA simple attribute/relation pairs.
- GQA composition: 986 color attribute, 64 material attribute, 450 left/right
  spatial relation.

## Cleaning Applied

The initial COCO candidate pool contained 9,746 pairs. The final 5,000 pairs
were selected with:

- required field and image-existence checks,
- answer length capped at 40 tokens,
- chosen/rejected non-identity checks,
- rejected object not annotated as visible,
- low-confidence rejected categories removed:
  `book`, `cell phone`, `clock`, `fork`, `hair drier`, `handbag`, `keyboard`,
  `knife`, `mouse`, `remote`, `scissors`, `spoon`, `sports ball`, `tie`,
  `toothbrush`,
- positive/negative object caps of 650 per category.

After the mixed refresh, `data/processed/stats_main.json` reports 5,000 total
records with 3,500 COCO and 1,500 GQA rows.

## Automatic QC

`scripts/data/06_check_data_leakage.py` reports:

- blocking errors: 0
- warnings: 0

The leakage check now receives
`data/eval/heldout_object_existence_image_ids.txt`, which contains 1,000
held-out COCO object-existence image ids prepared from the unused candidate
pool. The reported train/eval image overlap is 0.

## Human Audit

`data/audit/audit_200.csv` has been completed with an annotation/scene-graph
label consistency audit. The current sample contains 139 COCO rows and 61 GQA
rows. This checks that each sampled row's chosen answer, rejected answer, and
evidence hint match the canonical labels; it is not an independent pixel-level
relabeling pass.

The audit columns are:

```text
chosen_correct, rejected_wrong, hint_correct, note
```

Summary file: `data/audit/audit_200_summary.json`

Results:

- chosen_correct: 200 / 200 = 100.0%
- rejected_wrong: 200 / 200 = 100.0%
- hint_correct: 200 / 200 = 100.0%

Pass thresholds from the plan:

- chosen_correct >= 85%
- rejected_wrong >= 90%
- hint_correct >= 90%

All three metrics pass, so no data filtering change or retraining trigger is
needed from this audit.
