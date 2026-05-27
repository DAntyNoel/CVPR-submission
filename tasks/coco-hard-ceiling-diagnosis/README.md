# COCO Hard Ceiling Diagnosis

## Background

The current COCO object-existence evaluation is close to saturated for the base
model. Existing records show:

| Eval | Method | Acc | F1 | Yes Bias | Confusion |
| --- | --- | ---: | ---: | ---: | --- |
| COCO held-out | Base Instruct | 0.959 | 0.958 | 0.477 | TP 468 / FP 9 / TN 491 / FN 32 |
| Hard COCO | Base Instruct | 0.944 | 0.943 | 0.482 | TP 463 / FP 19 / TN 481 / FN 37 |
| Hard COCO | mixed Answer-DPO | 0.950 | 0.949 | 0.490 | TP 470 / FP 20 / TN 480 / FN 30 |

The hard split is harder than the normal held-out split, but it only reduces
Base accuracy by 1.5 points. This suggests a ceiling effect: COCO
object-existence is useful as a sanity check, but may be too easy to provide a
strong main conclusion by itself.

## Core Question

Is the high COCO Base score expected behavior caused by task saturation, or does
it indicate that the current hard-negative construction is not stressful enough?

The working assumption is:

> The current COCO task is near-saturated for Qwen2.5-VL-7B-Instruct. Hard COCO
> improves the negative sampling protocol, but remains mostly a controlled
> sanity check rather than a decisive benchmark.

## Goals

1. Diagnose why COCO held-out and Hard COCO both produce high Base scores.
2. Decide whether the paper should treat COCO as a ceiling-limited sanity check.
3. Design one lightweight harder evaluation option that does not expand the
   project beyond the current CVPR toy-submission scope.
4. Keep the main paper comparison limited to three groups: Base Instruct,
   Answer-DPO, and Evidence-Hint DPO.

## Non-Goals

- Do not add a new training method.
- Do not expand the main experiments beyond three groups.
- Do not run heavy local inference, GPU jobs, or large data movement in the
  interactive environment; use Slurm for any full evaluation.
- Do not turn this into a broad benchmark paper.
- Do not rely on noisy COCO missing-label negatives as main evidence without
  manual or automated quality checks.

## Current Diagnosis

The high Base score is plausible for four reasons:

1. COCO object-existence yes/no questions are simple and use common object
   categories.
2. Qwen2.5-VL-7B-Instruct is already strong on common object recognition.
3. The current hard negatives are sampled from the same coarse category, but
   many pairs remain visually separable.
4. Low-confidence negative categories are excluded, which improves label
   reliability but removes many ambiguous or small-object cases.

The current Hard COCO result should therefore be interpreted as a mild stress
test, not as a fully adversarial evaluation.

## Proposed Work Plan

### Step 1: Lock Existing Evidence

- Record the final COCO held-out, Hard COCO, and GQA simple results in
  `experiments/eval_summary.md`.
- Add a short note that COCO is near ceiling and that small differences on COCO
  accuracy should be interpreted cautiously.
- Prefer false-positive rate and GQA simple gains when writing the main claim.

### Step 2: Error Analysis

- Inspect Base errors on normal COCO and Hard COCO.
- Group false positives by absent target object.
- Group false negatives by present target object.
- Check whether errors concentrate in small objects, occluded objects,
  co-occurring categories, or annotation-sensitive categories.

Expected output:

```text
tasks/coco-hard-ceiling-diagnosis/error_notes.md
```

### Step 3: Design a Stronger Lightweight Hard Set

Candidate option A: Base-error-mined hard set.

- Generate a larger pool of candidate yes/no object-existence questions.
- Run Base Instruct through Slurm.
- Keep only samples where Base is wrong and labels are reliable.
- Evaluate Answer-DPO and Evidence-Hint DPO on the locked mined set.

Candidate option B: Fine-grained confusable negatives.

- Prioritize visually or contextually confusable pairs, for example:
  bus/train, car/truck, couch/bed, bowl/cup, fork/spoon/knife,
  backpack/handbag/suitcase, dog/cat, sheep/cow/horse.
- Keep the same train/eval image-overlap check.
- Manually audit a small subset before using it in the paper.

Candidate option C: Small/occluded object subset.

- Use COCO area fraction bins to select harder present-object positives.
- Pair them with same-scene or same-coarse absent negatives.
- Treat this as an appendix diagnostic unless quality is clearly strong.

Recommended first choice: **Candidate A**, because it directly targets the
observed ceiling behavior and can be kept small.

### Step 4: Minimal Evaluation Protocol

If a stronger hard set is built, evaluate only:

| Group | Required |
| --- | --- |
| Base Instruct | yes |
| Answer-DPO | yes |
| Evidence-Hint DPO | yes |

Metrics:

- Accuracy
- F1
- False-positive rate on negative questions
- Yes bias
- Refusal rate
- Optional bootstrap confidence interval for COCO accuracy/FPR

### Step 5: Paper Decision Rules

Use the following decision rules when updating the paper:

| Outcome | Paper Treatment |
| --- | --- |
| COCO remains near saturated, GQA improves | State COCO ceiling; use GQA as stronger evidence. |
| Hard/mined COCO opens a clear FP gap | Report it as a targeted diagnostic or appendix table. |
| All COCO variants show tiny differences | Keep COCO as sanity check; avoid strong COCO-only claims. |
| Evidence-Hint helps only on COCO | Narrow the claim to object-existence hallucination. |
| Evidence-Hint does not help | Write a diagnostic or negative result with ceiling analysis. |

## Deliverables

- `README.md`: this task outline.
- `error_notes.md`: manual or scripted error-analysis notes.
- Optional script: `scripts/eval/prepare_coco_base_error_mined_eval.py`.
- Optional eval file: `data/eval/coco_base_error_mined_object_existence.jsonl`.
- Optional summary update: `experiments/eval_summary.md`.
- Optional paper update: a short ceiling-effect discussion in `paper/main.tex`.

## Status

- Created: 2026-05-27.
- Current status: outline prepared; no new evaluation jobs submitted.
- Next action: wait for final mixed Evidence-Hint DPO results, then decide
  whether a stronger hard set is necessary for the paper narrative.
