# CEPO-Probe Final Results

Updated: 2026-05-28

The benchmark paper has been ported into `paper/main.tex`. The selected three
main groups are:

| Group | Model |
| --- | --- |
| A | Base Instruct |
| B | CEPO Answer-DPO |
| C | CEPO-Dual |

CEPO-Dual is selected over CEPO-Latent because it keeps short-answer metrics
close to CEPO Answer-DPO while substantially improving wrong-evidence
rejection.

## Data Checks

| Check | Result |
| --- | ---: |
| ClaimEvidence-6K canonical rows | 6,000 |
| CEPO-Dual DPO rows | 8,000 |
| Supported probe rows | 600 |
| Wrong-evidence probe rows | 400 |
| Train/eval image overlap | 0 |
| Same-answer wrong-evidence rows | 1,000 |
| Identical Answer-DPO chosen/rejected rows | 0 |
| CEPO annotation-consistency audit | 200 / 200 pass |

The CEPO audit is an annotation-consistency audit, not an independent
pixel-level relabeling pass. Same-answer wrong-evidence rows mark
`rejected_answer_wrong` as not applicable.

## Short-Answer Transfer

Values are percentages after re-scoring with `scripts/eval/score_object_eval.py`.

| Model | COCO Acc | COCO FPR/FNR | GQA Acc | GQA FPR/FNR | Hard Acc | Hard FPR/FNR | Base-Err Acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 96.0 | 1.6 / 6.4 | 76.2 | 14.4 / 33.2 | 94.4 | 3.8 / 7.4 | 0.0 |
| CEPO Answer-DPO | 97.0 | 1.8 / 4.2 | 76.8 | 23.6 / 22.8 | 95.0 | 5.0 / 5.0 | 18.0 |
| CEPO-Dual | 97.0 | 1.8 / 4.2 | 77.1 | 24.4 / 21.4 | 94.9 | 5.2 / 5.0 | 19.4 |

## Evidence-Probe Results

Values are percentages after re-scoring with
`scripts/eval/score_cepo_evidence_probe.py`.

| Model | Supported Support Acc | Wrong-Evidence Rejection | Object Wrong | Attribute Wrong | Relation Wrong | Invalid JSON |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 86.5 | 44.3 | 59.5 | 53.7 | 17.6 | 0.0 |
| CEPO Answer-DPO | 90.7 | 34.3 | 45.2 | 45.0 | 10.4 | 0.0 |
| CEPO-Dual | 95.2 | 70.2 | 96.0 | 85.9 | 25.6 | 0.0 |

## External Sanity Checks

| Eval | Base | CEPO Answer-DPO | CEPO-Dual |
| --- | ---: | ---: | ---: |
| POPE random | 88.7 | 89.6 | 89.8 |
| POPE popular | 87.7 | 88.5 | 88.7 |
| POPE adversarial | 86.7 | 87.1 | 87.3 |
| AMBER discriminative | 87.6 | 88.2 | 88.2 |

## Paper Reading

The final benchmark conclusion is:

```text
CEPO-Probe shows that short-answer preference tuning and claim-evidence
verification are separable. CEPO Answer-DPO improves ordinary yes/no accuracy
but weakens wrong-evidence rejection, while CEPO-Dual improves explicit
evidence consistency without resolving relation reversals.
```
