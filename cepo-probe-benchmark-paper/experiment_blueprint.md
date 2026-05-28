# Experiment Blueprint

## 1. Main Question

Does preference tuning that improves ordinary short-answer VQA also improve
claim-evidence consistency?

The main paper should report two linked evaluations:

1. Short-answer transfer: ordinary yes/no VQA behavior.
2. CEPO-Probe: explicit claim-evidence verification.

## 2. Main Model Groups

Keep the primary comparison to three groups.

| Group | Model | Role | Status |
| --- | --- | --- | --- |
| A | Base Instruct | Untuned reference model | Required |
| B | CEPO Answer-DPO | Answer-only preference baseline | Required |
| C | CEPO-Dual | Evidence-aware baseline | Selected |

Fallback for Group C:

```text
CEPO-Latent
```

CEPO-Latent remains a diagnostic fallback/appendix result because it did not
provide a sufficient positive short-answer result. CEPO-Dual is now selected
for the main paper.

## 3. What Counts As Success

For a positive CEPO-Dual baseline:

| Gate | Requirement |
| --- | --- |
| Short-answer accuracy | Within 0.5 percentage points of CEPO Answer-DPO on COCO, GQA, and Hard COCO. |
| FPR | Not worse than CEPO Answer-DPO on at least 3 of 4 internal short-answer evals. |
| Wrong-evidence rejection | At least 10 points above CEPO Answer-DPO. |
| Invalid JSON | Below 5% on probe evals. |

If these fail, the benchmark paper remains valid but should avoid method-win
language.

## 4. Primary Tables

### Table 1: Benchmark Composition

| Slice | Source | Train Rows | Probe Rows | Negative Type |
| --- | --- | ---: | ---: | --- |
| Object existence | COCO/GQA |  |  | absent object / wrong object |
| Attribute | GQA |  |  | attribute mismatch |
| Relation | GQA |  |  | left/right reversal |
| Wrong evidence | COCO/GQA |  |  | same answer, wrong evidence |

### Table 2: Short-Answer Transfer

| Model | COCO Acc | COCO FPR/FNR | GQA Acc | GQA FPR/FNR | Hard COCO Acc | Hard FPR/FNR | Other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 96.0 | 1.6 / 6.4 | 76.2 | 14.4 / 33.2 | 94.4 | 3.8 / 7.4 | Base-Err 0.0 |
| CEPO Answer-DPO | 97.0 | 1.8 / 4.2 | 76.8 | 23.6 / 22.8 | 95.0 | 5.0 / 5.0 | Base-Err 18.0 |
| CEPO-Dual | 97.0 | 1.8 / 4.2 | 77.1 | 24.4 / 21.4 | 94.9 | 5.2 / 5.0 | Base-Err 19.4 |

### Table 3: CEPO-Probe Evidence Consistency

| Model | Supported Support Acc | Wrong-Evidence Rejection | Evidence Label Acc | Relation Direction Acc | Invalid JSON |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 86.5 | 44.3 | 99.8 | relation wrong-rej. 17.6 | 0.0 |
| CEPO Answer-DPO | 90.7 | 34.3 | 99.8 | relation wrong-rej. 10.4 | 0.0 |
| CEPO-Dual | 95.2 | 70.2 | 100.0 | relation wrong-rej. 25.6 | 0.0 |

### Table 4: Slice Breakdown

| Model | Object Wrong-Evidence | Attribute Wrong-Evidence | Relation Wrong-Evidence | Main Failure |
| --- | ---: | ---: | ---: | --- |
| Base Instruct | 59.5 | 53.7 | 17.6 | relation evidence fragile |
| CEPO Answer-DPO | 45.2 | 45.0 | 10.4 | accepts plausible wrong evidence |
| CEPO-Dual | 96.0 | 85.9 | 25.6 | relation reversals still weak |

## 5. Secondary Tables

Appendix or compact diagnostics:

- Base-error-mined recovery.
- POPE random/popular/adversarial.
- AMBER discriminative.
- V1 Evidence-Hint and 10k scale-up as motivation.
- Qualitative examples of correct evidence matching and wrong-evidence failure.

## 6. Commands To Regenerate Final Numbers

Lightweight data checks:

```bash
python scripts/data/13_check_cepo_data.py
python scripts/eval/prepare_cepo_evidence_probe.py
```

Do not run heavy inference in the current shell. Use Slurm:

```bash
bash experiments/slurm/submit_cepo_pipeline.sh
```

If CEPO-Dual is selected:

```bash
python scripts/data/14_export_cepo_dual_dpo.py
python scripts/experiments/prepare_llamafactory_data_cepo_dual.py
bash experiments/slurm/submit_cepo_dual_pipeline.sh
```

Scoring example:

```bash
python scripts/eval/score_cepo_evidence_probe.py \
  --input results/eval/generations/cepo_wrong_evidence_probe/cepo_evidence_probe/cepo_answer_dpo.jsonl
```

## 7. Current Reading To Preserve

The paper should preserve this interpretation unless final numbers contradict
it:

- CEPO Answer-DPO can improve ordinary short-answer accuracy by increasing
  affirmative recall, but this may raise FPR and yes rate.
- CEPO-Latent has not shown reliable transfer from structured training
  responses to short-answer behavior.
- Wrong-evidence rejection is not automatically improved by answer-only DPO.
- Relation evidence is harder than object and attribute evidence.

## 8. Recommended Main Figure

Use one figure with three panels:

1. A normal answer-only preference row.
2. A claim-evidence row with supported evidence.
3. A wrong-evidence probe where the answer text is plausible but the candidate
   evidence is mismatched.

Caption message:

```text
CEPO-Probe isolates evidence consistency from answer correctness by asking the
model to judge candidate claim-evidence pairs, including same-answer examples
where only the evidence is wrong.
```
