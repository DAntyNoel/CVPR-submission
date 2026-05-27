# Evaluation Summary

Updated: 2026-05-27

This file records completed evaluation results and in-progress launches. The
mixed Evidence-Hint DPO default adapter is the completed ZeRO-2 run from job
64252. The old ZeRO-3 job 64201 and its dependency queue were cancelled.

## Overall Reading

The completed 5k mixed results support the Plan B / diagnostic interpretation.
Evidence-Hint DPO slightly reduces false-positive rates on COCO-style object
questions, but it does not consistently beat Answer-DPO on Acc/F1 or recovery:
COCO held-out is tied at 0.961, GQA simple is 0.766 vs. Answer-DPO 0.768, Hard
COCO is 0.946 vs. 0.950, and Base-error-mined recovery is 0.030 vs. 0.063.
Refusal and other/invalid rates are 0.0 throughout the normal yes/no runs.

10k mixed scale-up completed to test whether this trend changes with data
size. Data job 64369, Evidence-Hint train 64371, Answer-DPO replacement train
64397, Evidence-Hint evals 64375-64377, and Answer-DPO evals 64398-64400 all
completed with exit code 0. The slow Answer-DPO ZeRO-3 train 64370 and its eval
deps 64372-64374 were cancelled, then replaced by ZeRO-2 train 64397 on
`A100,L40S,ADA6000`.
The base-error-mined set is not included in this 10k chain because preserving a
6k COCO target uses images from that diagnostic pool.

10k normal-prompt results:

| Eval | 10k Answer-DPO Acc / F1 / FPR | 10k Evidence-Hint Acc / F1 / FPR | Delta EH - Answer |
| --- | --- | --- | --- |
| COCO held-out | 0.965 / 0.964 / 0.018 | 0.961 / 0.960 / 0.016 | Acc -0.004, F1 -0.004, FPR -0.002 |
| GQA simple | 0.769 / 0.752 / 0.164 | 0.766 / 0.743 / 0.146 | Acc -0.003, F1 -0.009, FPR -0.018 |
| Hard COCO | 0.948 / 0.948 / 0.048 | 0.944 / 0.943 / 0.038 | Acc -0.004, F1 -0.005, FPR -0.010 |

Conclusion: increasing the mixed preference set from 5k to 10k did not change
the Evidence-Hint trend. It still lowers false positives, but Acc/F1 remain at
or below Answer-DPO on all three normal-prompt evals.

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

## Base-Error-Mined Diagnostic Set

This set is conditioned on Base Instruct errors from a larger held-out COCO
candidate pool. It measures recovery from Base failures, not unbiased
benchmark accuracy. The audit sheet has been prepared but not manually filled,
so the table should be described as pre-audit diagnostic evidence.

Candidate pool job 64251 completed on 10,000 rows with Base Acc 0.9472 and 528
yes/no errors. The locked set contains 527 rows, 474 images, 404 Base false
negatives, and 123 Base false positives.

| Method | Job | Rows | Recovery Acc | FP Recovery | FN Recovery | Ref | Other | Confusion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Base Instruct | 64262 | 527 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | TP 0 / FP 123 / TN 0 / FN 404 |
| mixed Answer-DPO | 64264 | 527 | 0.063 | 0.008 | 0.079 | 0.000 | 0.000 | TP 32 / FP 122 / TN 1 / FN 372 |
| mixed Evidence-Hint DPO | 64267 | 527 | 0.030 | 0.016 | 0.035 | 0.000 | 0.000 | TP 14 / FP 121 / TN 2 / FN 390 |

The only favorable slice for Evidence-Hint DPO is false-positive recovery
(2/123 vs. 1/123), while overall recovery and false-negative recovery are lower
than Answer-DPO.
