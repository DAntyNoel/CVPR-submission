# Base-Error Mining Results

This diagnostic set is conditioned on Base Instruct errors, so the table measures error recovery rather than unbiased benchmark accuracy.

## Run Snapshot

- Candidate pool: `data/eval/base_error_mining_candidates.jsonl`, 10,000 rows, yes/no balanced, 2,525 images, train/eval image overlap 0.
- Base mining job: `64251`, completed, candidate accuracy 0.9472 with 528 yes/no errors.
- Locked diagnostic set: `data/eval/base_error_mined_object_existence.jsonl`, 527 rows, 474 images, 404 Base false negatives and 123 Base false positives.
- Audit sheet: `data/audit/base_error_mined_audit.csv`, 150 rows prepared; manual audit pass rate is not filled yet.
- Evidence-Hint row below uses the completed mixed ZeRO-2 adapter from job `64252`; the canonical `mixed/evidence_hint_dpo.jsonl` eval was completed by job `64267`. This ZeRO-2 adapter is now the default mixed Evidence-Hint adapter. The old ZeRO-3 job `64201` and its dependent eval job `64263` were cancelled and produced no final result.

## Locked-Set Recovery

| Model | Rows | Recovery Acc | FP Recovery | FN Recovery | Refusal | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 527 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Answer-DPO | 527 | 0.063 | 0.008 | 0.079 | 0.000 | 0.000 |
| Evidence-Hint DPO ZeRO-2 | 527 | 0.030 | 0.016 | 0.035 | 0.000 | 0.000 |

## Evidence-Hint Delta

| Comparison | Overall | FP | FN |
| --- | ---: | ---: | ---: |
| Evidence-Hint DPO ZeRO-2 - Answer-DPO | -0.032 | 0.008 | -0.045 |

## Reading

On this pre-audit Base-conditioned set, both DPO variants recover only a small
fraction of Base errors, and the ZeRO-2 Evidence-Hint row is below Answer-DPO
overall. The only favorable slice for Evidence-Hint is FP recovery, but it is a
2/123 vs 1/123 difference and should not be over-interpreted. This result is
best written as a diagnostic finding that the mined errors are dominated by
hard Base false negatives and are not substantially repaired by the current DPO
adapters.

## Files

- Base Instruct: `/home/fhshao/CVPR-submission/results/eval/generations/base_error_mined_object_existence/mixed/base.jsonl`
- Answer-DPO: `/home/fhshao/CVPR-submission/results/eval/generations/base_error_mined_object_existence/mixed/answer_dpo.jsonl`
- Evidence-Hint DPO ZeRO-2: `/home/fhshao/CVPR-submission/results/eval/generations/base_error_mined_object_existence/mixed/evidence_hint_dpo.jsonl`
