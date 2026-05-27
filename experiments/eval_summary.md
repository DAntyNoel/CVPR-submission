# Evaluation Summary

Updated: 2026-05-27

This file records evaluation results that are already complete while mixed
Evidence-Hint DPO job 64201 is still running. Do not treat the main table as
complete until the Evidence-Hint DPO row is available.

## Normal Yes/No Prompt

Prompt suffix:

```text
Answer with a short yes/no sentence only.
```

| Eval | Method | Job | Acc | F1 | Yes Bias | Refusal | Confusion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| COCO held-out | Base Instruct | 64205 | 0.959 | 0.958 | 0.477 | 0.000 | TP 468 / FP 9 / TN 491 / FN 32 |
| COCO held-out | mixed Answer-DPO | 64214 | 0.961 | 0.960 | 0.479 | 0.000 | TP 470 / FP 9 / TN 491 / FN 30 |
| COCO held-out | mixed Evidence-Hint DPO | pending 64201 | TBD | TBD | TBD | TBD | TBD |
| GQA simple | Base Instruct | 64213 | 0.764 | 0.740 | 0.408 | 0.000 | TP 336 / FP 72 / TN 428 / FN 164 |
| GQA simple | mixed Answer-DPO | 64215 | 0.768 | 0.748 | 0.420 | 0.000 | TP 344 / FP 76 / TN 424 / FN 156 |
| GQA simple | mixed Evidence-Hint DPO | pending 64201 | TBD | TBD | TBD | TBD | TBD |

## Evidence-Style Prompt

Prompt suffix:

```text
Answer yes or no, then briefly mention the visual evidence.
```

| Eval | Method | Job | Acc | F1 | Yes Bias | Refusal | Confusion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| GQA simple | Base Instruct | 64216 | 0.768 | 0.727 | 0.350 | 0.000 | TP 309 / FP 41 / TN 459 / FN 191 |
| COCO held-out | Base Instruct | 64217 | 0.955 | 0.953 | 0.467 | 0.000 | TP 461 / FP 6 / TN 494 / FN 39 |
| GQA simple | mixed Answer-DPO | 64218 | 0.766 | 0.732 | 0.374 | 0.000 | TP 320 / FP 54 / TN 446 / FN 180 |
| COCO held-out | mixed Answer-DPO | 64219 | 0.956 | 0.955 | 0.470 | 0.000 | TP 463 / FP 7 / TN 493 / FN 37 |
| COCO/GQA | mixed Evidence-Hint DPO | pending 64201 | TBD | TBD | TBD | TBD | TBD |

Submit the mixed Evidence-Hint DPO evidence-style jobs after 64201 completes
and the adapter dry-run passes.
