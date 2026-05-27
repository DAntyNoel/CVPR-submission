# Evaluation Summary

Updated: 2026-05-27

This file records completed evaluation results and in-progress launches. The
mixed Evidence-Hint DPO default adapter is the completed ZeRO-2 run from job
64252. The old ZeRO-3 job 64201 and its dependency queue were cancelled.

## Normal Yes/No Prompt

Prompt suffix:

```text
Answer with a short yes/no sentence only.
```

| Eval | Method | Job | Acc | BAcc | F1 | FPR | FNR | Yes | Ref | Other | Confusion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| COCO held-out | Base Instruct | 64205 | 0.959 | 0.959 | 0.958 | 0.018 | 0.064 | 0.477 | 0.000 | 0.000 | TP 468 / FP 9 / TN 491 / FN 32 |
| COCO held-out | mixed Answer-DPO | 64214 | 0.961 | 0.961 | 0.960 | 0.018 | 0.060 | 0.479 | 0.000 | 0.000 | TP 470 / FP 9 / TN 491 / FN 30 |
| COCO held-out | mixed Evidence-Hint DPO | 64255 | 0.961 | 0.961 | 0.960 | 0.016 | 0.062 | 0.477 | 0.000 | 0.000 | TP 469 / FP 8 / TN 492 / FN 31 |
| GQA simple | Base Instruct | 64213 | 0.764 | 0.764 | 0.740 | 0.144 | 0.328 | 0.408 | 0.000 | 0.000 | TP 336 / FP 72 / TN 428 / FN 164 |
| GQA simple | mixed Answer-DPO | 64215 | 0.768 | 0.768 | 0.748 | 0.152 | 0.312 | 0.420 | 0.000 | 0.000 | TP 344 / FP 76 / TN 424 / FN 156 |
| GQA simple | mixed Evidence-Hint DPO | 64256 | 0.766 | 0.766 | 0.743 | 0.144 | 0.324 | 0.410 | 0.000 | 0.000 | TP 338 / FP 72 / TN 428 / FN 162 |

## Hard COCO

Eval file:

```text
data/eval/coco_hard_object_existence.jsonl
```

It contains 1,000 rows, yes/no balanced, 500 unique held-out images,
same-coarse-group absent-object negatives, and `train_eval_image_overlap = 0`.

| Method | Job | State | Acc | BAcc | F1 | FPR | FNR | Yes | Ref | Other | Confusion |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base Instruct | 64233 | COMPLETED | 0.944 | 0.944 | 0.943 | 0.038 | 0.074 | 0.482 | 0.000 | 0.000 | TP 463 / FP 19 / TN 481 / FN 37 |
| mixed Answer-DPO | 64234 | COMPLETED | 0.950 | 0.950 | 0.949 | 0.040 | 0.060 | 0.490 | 0.000 | 0.000 | TP 470 / FP 20 / TN 480 / FN 30 |
| mixed Evidence-Hint DPO | 64257 | COMPLETED | 0.946 | 0.946 | 0.945 | 0.038 | 0.070 | 0.484 | 0.000 | 0.000 | TP 465 / FP 19 / TN 481 / FN 35 |

## Evidence-Style Prompt

Prompt suffix:

```text
Answer yes or no, then briefly mention the visual evidence.
```

| Eval | Method | Job | Acc | BAcc | F1 | FPR | FNR | Yes | Ref | Other | Confusion |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| GQA simple | Base Instruct | 64216 | 0.768 | 0.768 | 0.727 | 0.082 | 0.382 | 0.350 | 0.000 | 0.000 | TP 309 / FP 41 / TN 459 / FN 191 |
| COCO held-out | Base Instruct | 64217 | 0.955 | 0.955 | 0.953 | 0.012 | 0.078 | 0.467 | 0.000 | 0.000 | TP 461 / FP 6 / TN 494 / FN 39 |
| GQA simple | mixed Answer-DPO | 64218 | 0.766 | 0.766 | 0.732 | 0.108 | 0.360 | 0.374 | 0.000 | 0.000 | TP 320 / FP 54 / TN 446 / FN 180 |
| COCO held-out | mixed Answer-DPO | 64219 | 0.956 | 0.956 | 0.955 | 0.014 | 0.074 | 0.470 | 0.000 | 0.000 | TP 463 / FP 7 / TN 493 / FN 37 |
| GQA simple | mixed Evidence-Hint DPO | 64259 | 0.767 | 0.767 | 0.728 | 0.090 | 0.376 | 0.357 | 0.000 | 0.000 | TP 312 / FP 45 / TN 455 / FN 188 |
| COCO held-out | mixed Evidence-Hint DPO | 64258 | 0.955 | 0.955 | 0.954 | 0.014 | 0.076 | 0.469 | 0.000 | 0.000 | TP 462 / FP 7 / TN 493 / FN 38 |

## GQA Task-Type Breakdown

The expanded scorer also writes subgroup metrics under `groups.task_type`.
Current GQA simple results show that relation questions are the harder half of
the set.

| Prompt | Method | Task | N | Acc | FPR | FNR | Yes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| normal | Base Instruct | attribute_color | 500 | 0.842 | 0.084 | 0.232 | 0.426 |
| normal | Base Instruct | relation_spatial | 500 | 0.686 | 0.204 | 0.424 | 0.390 |
| normal | mixed Answer-DPO | attribute_color | 500 | 0.844 | 0.084 | 0.228 | 0.428 |
| normal | mixed Answer-DPO | relation_spatial | 500 | 0.692 | 0.220 | 0.396 | 0.412 |
| normal | mixed Evidence-Hint DPO | attribute_color | 500 | 0.840 | 0.084 | 0.236 | 0.424 |
| normal | mixed Evidence-Hint DPO | relation_spatial | 500 | 0.692 | 0.204 | 0.412 | 0.396 |
| evidence-style | Base Instruct | attribute_color | 500 | 0.836 | 0.040 | 0.288 | 0.376 |
| evidence-style | Base Instruct | relation_spatial | 500 | 0.700 | 0.124 | 0.476 | 0.324 |
| evidence-style | mixed Answer-DPO | attribute_color | 500 | 0.836 | 0.064 | 0.264 | 0.400 |
| evidence-style | mixed Answer-DPO | relation_spatial | 500 | 0.696 | 0.152 | 0.456 | 0.348 |
| evidence-style | mixed Evidence-Hint DPO | attribute_color | 500 | 0.838 | 0.048 | 0.276 | 0.386 |
| evidence-style | mixed Evidence-Hint DPO | relation_spatial | 500 | 0.696 | 0.132 | 0.476 | 0.328 |

Old dependency jobs 64235 to 64239 and 64263 were cancelled after ZeRO-2 job
64252 replaced job 64201. Jobs 64255 to 64259 use the completed ZeRO-2 adapter
and are complete.
