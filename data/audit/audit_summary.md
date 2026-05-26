# Data Audit Summary

Updated: 2026-05-26

## Current Training Data

- Final canonical file: `data/processed/canonical_pairs_main.jsonl`
- Answer-DPO file: `data/processed/answer_dpo_train.jsonl`
- Evidence-Hint DPO file: `data/processed/evidence_hint_dpo_train.jsonl`
- Human audit sheet: `data/audit/audit_200.csv`

All three JSONL files contain 5,000 aligned records. The final data is
COCO-only object-existence data because the GQA HF source failed under the
cluster mirror path and the project fallback was applied.

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

The largest positive class is `person` with 650 examples after capping.

## Automatic QC

`scripts/data/06_check_data_leakage.py` reports:

- blocking errors: 0
- warnings: 1

Warnings:

- `object_existence ratio is 1.000; target is roughly 0.70`

The remaining warning is expected for the COCO-only fallback.

The leakage check now receives
`data/eval/heldout_object_existence_image_ids.txt`, which contains 1,000
held-out COCO object-existence image ids prepared from the unused candidate
pool. The reported train/eval image overlap is 0.

## Human Audit

`data/audit/audit_200.csv` has been completed with an annotation-grounded COCO
label consistency audit. This checks that each sampled row's chosen answer,
rejected answer, and evidence hint match the canonical COCO-derived labels; it
is not an independent pixel-level relabeling pass.

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
