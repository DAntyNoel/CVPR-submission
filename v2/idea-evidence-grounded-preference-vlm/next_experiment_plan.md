# Next Experiment Plan After CEPO-Latent

Date: 2026-05-27

## 0. Current Decision

Do not converge the paper yet.

CEPO-Latent is not a sufficient positive result on the primary short-answer
metrics. It mostly tracks Base rather than beating Answer-DPO:

| Eval | Base Acc / FPR | Answer-DPO Acc / FPR | CEPO-Latent Acc / FPR |
| --- | ---: | ---: | ---: |
| COCO held-out | 0.960 / 0.016 | **0.969 / 0.018** | 0.960 / 0.018 |
| GQA simple | 0.764 / 0.146 | **0.770 / 0.238** | 0.762 / 0.150 |
| Hard COCO | 0.942 / 0.040 | **0.950 / 0.050** | 0.944 / 0.040 |
| Base-error-mined | 0.028 / 0.959 | **0.178 / 1.000** | 0.032 / 0.984 |

Interpretation:

- Answer-DPO improves short-answer recall/accuracy but increases yes bias and
  FPR.
- CEPO-Latent does not transfer its structured response supervision into
  short-answer behavior.
- The claim-evidence block likely creates a format mismatch: training asks the
  model to generate claims, while main eval asks only for short answers and
  evidence-probe asks it to judge candidate evidence.

The evidence-probe jobs are still running for CEPO-Latent. Even if they improve,
the result is at best a narrow diagnostic Plan B unless short-answer behavior
also improves.

## 1. Next Hypothesis

The next experiment should remove the format mismatch:

> Claim-evidence preference should train the model to verify candidate evidence
> directly, while retaining ordinary short-answer DPO rows to preserve answer
> accuracy.

This changes CEPO from latent claim generation to a dual-task preference format.
The model sees two prompt families:

1. **Short-answer preference rows**
   ```text
   Image + Question
   Chosen: short correct answer
   Rejected: short incorrect answer
   ```

2. **Evidence-verifier preference rows**
   ```text
   Image + Question + Candidate claim + Candidate evidence
   Chosen: {"support": "supported"} or {"support": "wrong_evidence"}
   Rejected: the opposite support label
   ```

No model structure changes, no reward model, no closed-source judge.

## 2. Proposed Method

Name:

```text
CEPO-Dual: Answer + Evidence-Verifier Preference Optimization
```

Main comparison remains three groups:

| Group | Method | Training data |
| --- | --- | --- |
| A | Base Instruct | none |
| B | CEPO Answer-DPO | 6k answer-only rows |
| C | CEPO-Dual | 6k answer rows + 2k verifier rows |

The 2k verifier rows keep total data at 8k, matching the original project
upper bound.

## 3. Data Design

Reuse `data/processed/cepo/claim_evidence_canonical.jsonl`.

Export:

```text
data/processed/cepo_dual/
  cepo_dual_dpo_train.jsonl
  cepo_dual_summary.json

experiments/llamafactory_data_cepo_dual/
  cvpr_cepo_dual_dpo.json
  dataset_info.json
```

Composition:

| Slice | Rows | Source |
| --- | ---: | --- |
| Short-answer rows | 6,000 | Current CEPO Answer-DPO export |
| Supported verifier rows | 1,000 | chosen claims from object/attribute/relation rows |
| Wrong-evidence verifier rows | 1,000 | wrong_evidence rows, relation swaps and wrong object labels |

Verifier prompt:

```text
<image>
Question: Is there a bus in the image?
Candidate claim: bus visible
Candidate evidence: label=truck
Does the candidate evidence support the claim in the image?
Answer:
```

Verifier chosen/rejected:

```json
{"support": "wrong_evidence"}
{"support": "supported"}
```

For relation rows:

```json
{"support": "wrong_evidence", "relation": "left_of"}
{"support": "supported", "relation": "left_of"}
```

Keep verifier responses short and stable. Do not include boxes in the training
text; boxes remain metadata only.

## 4. Evaluation

Run the same fixed evals:

| Eval | Purpose |
| --- | --- |
| COCO held-out | preserve ordinary object-existence accuracy |
| GQA simple | relation/attribute transfer |
| Hard COCO | FPR under hard absent-object negatives |
| Base-error-mined | repair old failures |
| POPE/AMBER | external sanity |
| Evidence-probe | direct evidence verification |

Success gate:

```text
CEPO-Dual is useful only if:
1. short-answer Acc/F1 is within 0.5 pt of Answer-DPO on COCO/GQA/Hard COCO, and
2. FPR is not worse than Answer-DPO on at least 3/4 internal evals, and
3. wrong-evidence rejection improves by >= 10 points over Answer-DPO, and
4. invalid JSON remains below 5%.
```

If it only improves evidence-probe but loses short-answer accuracy, write a
diagnostic negative result and stop.

## 5. Minimal Implementation Plan

Add:

```text
scripts/data/14_export_cepo_dual_dpo.py
scripts/experiments/prepare_llamafactory_data_cepo_dual.py
experiments/llamafactory_configs/qwen25vl_cepo_dual_dpo.yaml
experiments/slurm/train_cepo_dual_dpo.slurm
experiments/slurm/submit_cepo_dual_pipeline.sh
```

Use the same training hyperparameters:

```text
Qwen2.5-VL-7B-Instruct
LoRA-DPO
ZeRO-2
1 epoch
pref_beta = 0.1
LoRA rank = 16
```

Do not run optional ablations until CEPO-Dual passes the evidence-probe gate.

## 6. Paper Path After This

If CEPO-Dual passes:

```text
Answer-only preference improves short answers but raises false positives.
Latent claim generation does not transfer.
Dual answer + evidence-verifier preference preserves short-answer behavior and
improves explicit evidence consistency.
```

If CEPO-Dual fails:

```text
Claim-evidence supervision is not enough when the evaluation interface does not
expose evidence verification. The honest paper is a controlled negative study:
response-level hints and latent claim blocks both fail to reliably improve
short-answer hallucination under small-data DPO.
```
