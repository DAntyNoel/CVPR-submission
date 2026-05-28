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
| C | CEPO-Dual | Preferred evidence-aware baseline if complete | Pending final decision |

Fallback for Group C:

```text
CEPO-Latent
```

Use CEPO-Latent if CEPO-Dual is incomplete or fails. In that case, write the
paper as a diagnostic showing that latent claim-evidence generation does not
transfer into robust evidence verification.

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
| Base Instruct |  |  |  |  |  |  |  |
| CEPO Answer-DPO |  |  |  |  |  |  |  |
| Evidence-aware baseline |  |  |  |  |  |  |  |

### Table 3: CEPO-Probe Evidence Consistency

| Model | Supported Support Acc | Wrong-Evidence Rejection | Evidence Label Acc | Relation Direction Acc | Invalid JSON |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base Instruct |  |  |  |  |  |
| CEPO Answer-DPO |  |  |  |  |  |
| Evidence-aware baseline |  |  |  |  |  |

### Table 4: Slice Breakdown

| Model | Object Wrong-Evidence | Attribute Wrong-Evidence | Relation Wrong-Evidence | Main Failure |
| --- | ---: | ---: | ---: | --- |
| Base Instruct |  |  |  |  |
| CEPO Answer-DPO |  |  |  |  |
| Evidence-aware baseline |  |  |  |  |

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

