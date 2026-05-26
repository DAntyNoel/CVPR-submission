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
- warnings: 2

Warnings:

- `object_existence ratio is 1.000; target is roughly 0.70`
- `no eval image-id files provided; skipped leakage overlap check`

The first warning is expected for the COCO-only fallback. The second should be
resolved once POPE/AMBER/GQA eval image ids are prepared.

## Human Audit

`data/audit/audit_200.csv` is ready for manual annotation with:

```text
chosen_correct, rejected_wrong, hint_correct, note
```

Pass thresholds from the plan:

- chosen_correct >= 85%
- rejected_wrong >= 90%
- hint_correct >= 90%

