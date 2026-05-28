# Evaluation Summary

Updated: 2026-05-27

This file records completed evaluation results. The mixed Evidence-Hint DPO
default adapter is the completed ZeRO-2 run from job 64252. The old ZeRO-3 job
64201 and its dependency queue were cancelled.

## CEPO-Probe Benchmark Results

Updated: 2026-05-28

The CEPO-Probe paper now uses the completed CEPO-Dual three-group comparison:
Base Instruct, CEPO Answer-DPO, and CEPO-Dual. The selected metrics were
refreshed with the current `score_object_eval.py` and
`score_cepo_evidence_probe.py` scorers.

Short-answer transfer:

| Model | COCO Acc | COCO FPR/FNR | GQA Acc | GQA FPR/FNR | Hard Acc | Hard FPR/FNR | Base-Err Acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 0.960 | 0.016 / 0.064 | 0.762 | 0.144 / 0.332 | 0.944 | 0.038 / 0.074 | 0.000 |
| CEPO Answer-DPO | 0.970 | 0.018 / 0.042 | 0.768 | 0.236 / 0.228 | 0.950 | 0.050 / 0.050 | 0.180 |
| CEPO-Dual | 0.970 | 0.018 / 0.042 | 0.771 | 0.244 / 0.214 | 0.949 | 0.052 / 0.050 | 0.194 |

CEPO-Probe evidence consistency:

| Model | Supported Support Acc | Wrong-Evidence Rejection | Object Wrong | Attribute Wrong | Relation Wrong | Invalid JSON |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 0.865 | 0.443 | 0.595 | 0.537 | 0.176 | 0.000 |
| CEPO Answer-DPO | 0.907 | 0.343 | 0.452 | 0.450 | 0.104 | 0.000 |
| CEPO-Dual | 0.952 | 0.702 | 0.960 | 0.859 | 0.256 | 0.000 |

External sanity checks are close to CEPO Answer-DPO: CEPO-Dual reaches 0.898,
0.887, and 0.873 accuracy on POPE random/popular/adversarial, and 0.882 on
AMBER discriminative. The final paper reading is diagnostic: CEPO-Dual improves
explicit evidence verification, but relation wrong-evidence rejection remains
weak.

### Review-Driven CI and Ablation

Updated: 2026-05-28

The CEPO-Probe confidence intervals and parser audit were generated from the
existing locked generation files with `scripts/eval/bootstrap_cepo_probe_ci.py`.
Paper-facing tables are in:

```text
cepo-probe-benchmark-improve/artifacts/table3_ci.md
cepo-probe-benchmark-improve/artifacts/slice_ci.md
cepo-probe-benchmark-improve/artifacts/parser_audit.md
```

Headline 95% bootstrap CIs:

| Model | Supported N | Supported Acc | Wrong N | Wrong Rej |
| --- | ---: | ---: | ---: | ---: |
| Base Instruct | 600 | 86.5 [83.7, 89.2] | 400 | 44.3 [39.5, 49.0] |
| CEPO Answer-DPO | 600 | 90.7 [88.3, 93.0] | 400 | 34.3 [29.8, 39.0] |
| CEPO-Dual-2k | 600 | 95.2 [93.3, 96.8] | 400 | 70.3 [65.8, 74.8] |

All current probe generations are strict JSON valid and scored; parse-failure
rate is 0.0 for the three main groups.

The verifier-count ablation ran through Slurm jobs 64635-64652. Full table:

```text
cepo-probe-benchmark-improve/artifacts/ablation_results.md
```

| Setting | COCO Acc | GQA Acc | Hard Acc | Supp Acc | Wrong Rej | Object Wrong | Attr Wrong | Rel Wrong | Parse Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CEPO Answer-DPO | 97.0 | 76.8 | 95.0 | 90.7 | 34.3 | 45.2 | 45.0 | 10.4 | 0.0 |
| Evidence-DPO only | 95.9 | 76.7 | 94.4 | 87.8 | 53.0 | 77.0 | 63.8 | 16.0 | 0.0 |
| CEPO-Dual-500 | 96.9 | 76.8 | 95.0 | 91.3 | 39.5 | 56.3 | 50.3 | 9.6 | 0.0 |
| CEPO-Dual-1k | 97.0 | 77.2 | 94.9 | 93.2 | 48.5 | 74.6 | 59.1 | 9.6 | 0.0 |
| CEPO-Dual-2k | 97.0 | 77.1 | 94.9 | 95.2 | 70.3 | 96.0 | 85.9 | 25.6 | 0.0 |

Conclusion: short-answer transfer is stable across the compact ablation, while
supported accuracy and wrong-evidence rejection improve as verifier rows
increase. CEPO-Dual-2k is therefore the right selected evidence-aware baseline.
Relation wrong-evidence remains weak even in the selected model.

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

Phase-2 method variants also completed. They test whether changing evidence
placement fixes the weak Evidence-Hint result while keeping the same 5k split,
backbone, DPO objective, LoRA setup, and ZeRO-2 training. Input-Side Evidence is
the strongest of the three variants, but it remains close to the main runs and
does not change the diagnostic conclusion.

The follow-up Balanced Hard Input-Side Evidence DPO run completed as the
main-method rescue for this task. It improves COCO held-out Acc to 0.966 and
Base-error-mined recovery to 0.120, mainly by lowering false-negative rates.
However, Hard COCO FPR rises to 0.048 and external POPE/AMBER show the same
recall-for-FPR trade-off. It is therefore a useful rescue/diagnostic result,
not a clean solution to false-positive control.

Phase-2 normal-prompt results:

| Eval | Phase-2 Method | Job | Acc | F1 | FPR | FNR | Yes | Other |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| COCO held-out | Evidence-Only DPO | 64305 | 0.959 | 0.958 | 0.018 | 0.064 | 0.477 | 0.000 |
| COCO held-out | Input-Side Evidence DPO | 64309 | 0.961 | 0.960 | 0.016 | 0.062 | 0.477 | 0.000 |
| COCO held-out | Chosen-Only Evidence DPO | 64313 | 0.961 | 0.960 | 0.016 | 0.062 | 0.477 | 0.000 |
| GQA simple | Evidence-Only DPO | 64306 | 0.765 | 0.741 | 0.142 | 0.328 | 0.407 | 0.000 |
| GQA simple | Input-Side Evidence DPO | 64310 | 0.768 | 0.747 | 0.150 | 0.314 | 0.418 | 0.000 |
| GQA simple | Chosen-Only Evidence DPO | 64314 | 0.765 | 0.741 | 0.144 | 0.326 | 0.409 | 0.000 |
| Hard COCO | Evidence-Only DPO | 64307 | 0.942 | 0.941 | 0.040 | 0.076 | 0.482 | 0.000 |
| Hard COCO | Input-Side Evidence DPO | 64311 | 0.947 | 0.946 | 0.038 | 0.068 | 0.485 | 0.000 |
| Hard COCO | Chosen-Only Evidence DPO | 64315 | 0.946 | 0.945 | 0.038 | 0.070 | 0.484 | 0.000 |

Phase-2 Base-error-mined recovery:

| Method | Job | Rows | Recovery Acc | FP Recovery | FN Recovery | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Evidence-Only DPO | 64308 | 527 | 0.015 | 0.000 | 0.020 | 0.000 |
| Input-Side Evidence DPO | 64312 | 527 | 0.044 | 0.016 | 0.052 | 0.000 |
| Chosen-Only Evidence DPO | 64316 | 527 | 0.032 | 0.024 | 0.035 | 0.000 |

## Balanced Hard Input-Side Evidence DPO

This run uses `input_side_main_balanced_hard_dpo` and writes main eval outputs
under `OUTPUT_VARIANT=input_side_main`. The training and eval chain completed
with exit code 0:

```text
64443  COMPLETED  Balanced Hard Input-Side Evidence DPO train
64444  COMPLETED  COCO held-out eval
64445  COMPLETED  GQA simple eval
64446  COMPLETED  Hard COCO eval
64447  COMPLETED  Base-error-mined eval
```

Main eval results:

| Eval | Job | N | Acc | BAcc | F1 | Neg-F1 | FPR | FNR | Yes | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| COCO held-out | 64444 | 1000 | 0.966 | 0.966 | 0.965 | 0.967 | 0.018 | 0.050 | 0.484 | 0.000 |
| GQA simple | 64445 | 1000 | 0.766 | 0.766 | 0.748 | 0.782 | 0.162 | 0.306 | 0.428 | 0.000 |
| Hard COCO | 64446 | 1000 | 0.947 | 0.947 | 0.947 | 0.947 | 0.048 | 0.058 | 0.495 | 0.000 |
| Base-error-mined | 64447 | 527 | 0.120 | 0.078 | 0.214 | 0.000 | 1.000 | 0.844 | 0.353 | 0.000 |

Comparison to the fixed 5k mixed baselines:

| Eval | Method | Acc | F1 | FPR | FNR | Reading |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| COCO held-out | mixed Answer-DPO | 0.961 | 0.960 | 0.018 | 0.060 | baseline DPO |
| COCO held-out | Phase-2 Input-Side | 0.961 | 0.960 | 0.016 | 0.062 | lower FPR, same Acc |
| COCO held-out | Balanced Hard Input-Side | 0.966 | 0.965 | 0.018 | 0.050 | best COCO held-out |
| GQA simple | mixed Answer-DPO | 0.768 | 0.748 | 0.152 | 0.312 | baseline DPO |
| GQA simple | Phase-2 Input-Side | 0.768 | 0.747 | 0.150 | 0.314 | close to Answer-DPO |
| GQA simple | Balanced Hard Input-Side | 0.766 | 0.748 | 0.162 | 0.306 | recall gain, FPR up |
| Hard COCO | mixed Answer-DPO | 0.950 | 0.949 | 0.040 | 0.060 | best Hard COCO Acc |
| Hard COCO | Phase-2 Input-Side | 0.947 | 0.946 | 0.038 | 0.068 | best FPR among these rows |
| Hard COCO | Balanced Hard Input-Side | 0.947 | 0.947 | 0.048 | 0.058 | lower FNR, higher FPR |
| Base-error-mined | mixed Answer-DPO | 0.063 | 0.115 | 0.992 | 0.921 | modest recovery |
| Base-error-mined | Phase-2 Input-Side | 0.044 | 0.077 | 0.984 | 0.948 | weak recovery |
| Base-error-mined | Balanced Hard Input-Side | 0.120 | 0.214 | 1.000 | 0.844 | strongest recovery |

External sanity checks used `OUTPUT_VARIANT=input_side_main_external`:

```text
64457  COMPLETED  POPE random
64458  COMPLETED  POPE popular
64459  COMPLETED  POPE adversarial
64460  COMPLETED  AMBER discriminative
```

| Eval | Job | N | Acc | BAcc | F1 | Neg-F1 | FPR | FNR | Yes | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| POPE random | 64457 | 3000 | 0.894 | 0.894 | 0.883 | 0.903 | 0.011 | 0.201 | 0.405 | 0.000 |
| POPE popular | 64458 | 3000 | 0.883 | 0.883 | 0.872 | 0.892 | 0.033 | 0.201 | 0.416 | 0.000 |
| POPE adversarial | 64459 | 3000 | 0.871 | 0.871 | 0.861 | 0.880 | 0.057 | 0.201 | 0.428 | 0.000 |
| AMBER discr. | 64460 | 14216 | 0.881 | 0.860 | 0.818 | 0.912 | 0.076 | 0.204 | 0.318 | 0.000 |

External reading: Balanced Hard Input-Side improves recall and Acc/F1 slightly
over the fixed mixed Evidence-Hint row, but raises FPR versus mixed
Answer-DPO/Evidence-Hint on POPE popular/adversarial and AMBER. This mirrors
the main benchmark trade-off.

Metric refresh for the phase-1/main results: on 2026-05-27, the saved
generation JSONL files for COCO held-out, GQA simple, Hard COCO, evidence-style
prompting, the Base-error mining candidate pool, and the Base-error-mined
locked set were rescored with the current `score_object_eval.py`. The headline
numbers below are unchanged. Official POPE/AMBER evals were then run on the
same three phase-1 model groups with `OUTPUT_VARIANT=mixed_external`; POPE uses
the prepared COCO val2014 image root, and AMBER uses the prepared 1,004-image
root with `IMAGE_MAX_PIXELS=1003520` to keep high-resolution images tractable.
The external results reinforce the main reading: Answer-DPO has the small edge,
while Evidence-Hint DPO stays close to Base and does not produce a consistent
metric gain.

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

## External POPE/AMBER

Image roots are now resolved: POPE has 500 referenced COCO val2014 images under
`data/raw/coco/val2014`, and AMBER has 1,004 images under
`data/raw/amber/images`. The image-prep job 64378 completed with 0 missing eval
image references. POPE evals used the standard yes/no suffix. AMBER evals used
the same suffix plus `IMAGE_MAX_PIXELS=1003520` for Qwen visual preprocessing.

| Eval | Method | Job | N | Acc | BAcc | F1 | Neg-F1 | FPR | FNR | Yes | Other |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| POPE random | Base Instruct | 64379 | 3000 | 0.887 | 0.887 | 0.874 | 0.898 | 0.009 | 0.217 | 0.396 | 0.000 |
| POPE random | mixed Answer-DPO | 64380 | 3000 | 0.889 | 0.889 | 0.876 | 0.899 | 0.011 | 0.212 | 0.399 | 0.000 |
| POPE random | mixed Evidence-Hint DPO | 64381 | 3000 | 0.887 | 0.887 | 0.874 | 0.897 | 0.010 | 0.217 | 0.397 | 0.000 |
| POPE popular | Base Instruct | 64382 | 3000 | 0.877 | 0.877 | 0.865 | 0.888 | 0.029 | 0.217 | 0.406 | 0.000 |
| POPE popular | mixed Answer-DPO | 64383 | 3000 | 0.878 | 0.878 | 0.866 | 0.888 | 0.031 | 0.212 | 0.410 | 0.000 |
| POPE popular | mixed Evidence-Hint DPO | 64384 | 3000 | 0.877 | 0.877 | 0.865 | 0.888 | 0.029 | 0.217 | 0.406 | 0.000 |
| POPE adversarial | Base Instruct | 64385 | 3000 | 0.867 | 0.867 | 0.855 | 0.878 | 0.049 | 0.217 | 0.416 | 0.000 |
| POPE adversarial | mixed Answer-DPO | 64386 | 3000 | 0.869 | 0.869 | 0.857 | 0.879 | 0.050 | 0.212 | 0.419 | 0.000 |
| POPE adversarial | mixed Evidence-Hint DPO | 64387 | 3000 | 0.867 | 0.867 | 0.855 | 0.877 | 0.049 | 0.217 | 0.416 | 0.000 |
| AMBER discr. | Base Instruct | 64392 | 14216 | 0.879 | 0.852 | 0.810 | 0.911 | 0.066 | 0.230 | 0.303 | 0.000 |
| AMBER discr. | mixed Answer-DPO | 64393 | 14216 | 0.881 | 0.858 | 0.817 | 0.912 | 0.070 | 0.214 | 0.311 | 0.000 |
| AMBER discr. | mixed Evidence-Hint DPO | 64394 | 14216 | 0.879 | 0.852 | 0.811 | 0.911 | 0.068 | 0.227 | 0.305 | 0.000 |

AMBER dimension slices follow the same pattern. Answer-DPO is highest on the
relation subset (0.791 Acc vs. Base 0.774 and Evidence-Hint 0.775) and slightly
higher on attribute (0.861 vs. 0.857/0.857), while Base is marginally higher on
existence (0.948 vs. 0.944/0.946). No external run produced refusals or other
invalid answers.

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
