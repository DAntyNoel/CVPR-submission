# Experiment Outline

This outline converts the official review into a minimal experimental plan.
Heavy steps must be submitted through Slurm; local work is limited to scoring,
table generation, sampling, and paper editing.

## 1. Questions

Primary question:

```text
Does answer-level preference tuning improve claim-evidence consistency, or can
the two behaviors move independently?
```

Follow-up questions:

1. Are the CEPO-Probe differences stable enough to report with confidence
   intervals?
2. How many evidence-verifier rows are needed before wrong-evidence rejection
   improves?
3. Does evidence-verifier training alone preserve ordinary short-answer VQA?
4. Why do relation reversals remain hard even after CEPO-Dual?

## 2. Existing Baselines To Reuse

Do not rerun these unless files are missing or corrupted.

| Model | Training | Status |
| --- | --- | --- |
| Base Instruct | none | Existing. |
| CEPO Answer-DPO | 6k answer rows | Existing final adapter. |
| CEPO-Dual-2k | 6k answer rows + 2k verifier rows | Existing final adapter and selected main result. |

Existing headline results:

| Model | COCO Acc | GQA Acc | Hard Acc | Supported Acc | Wrong-Evidence Rej. | Relation Wrong Rej. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 96.0 | 76.2 | 94.4 | 86.5 | 44.3 | 17.6 |
| CEPO Answer-DPO | 97.0 | 76.8 | 95.0 | 90.7 | 34.3 | 10.4 |
| CEPO-Dual-2k | 97.0 | 77.1 | 94.9 | 95.2 | 70.2 | 25.6 |

## 3. Experiment A: Confidence Intervals on Existing Outputs

Purpose:

Address the review concern that the supported probe has only 600 rows, the
wrong-evidence probe has only 400 rows, and relation wrong-evidence has only
125 rows.

Input:

```text
results/eval/generations/cepo_evidence_probe/cepo_dual_evidence_probe/*.jsonl
results/eval/generations/cepo_wrong_evidence_probe/cepo_dual_evidence_probe/*.jsonl
```

Metrics:

- support accuracy;
- wrong-evidence rejection;
- object/attribute/relation wrong-evidence rejection;
- strict JSON valid rate;
- parse-failure rate;
- scored-output rate.

Planned implementation:

```text
scripts/eval/bootstrap_cepo_probe_ci.py
```

Recommended behavior:

- read raw generation JSONL or scored JSONL;
- reuse `score_cepo_evidence_probe.py` row-level scoring;
- bootstrap rows 10,000 times per metric;
- output mean, standard error, and 95% percentile CI;
- write both JSON and Markdown table artifacts.

Expected artifacts:

```text
results/eval/metrics/cepo_probe_ci/
  base.json
  cepo_answer_dpo.json
  cepo_dual_dpo.json
  table3_ci.md
  slice_breakdown_ci.md
```

Paper use:

- Table 3: add `N` and CI for supported accuracy and wrong-evidence rejection.
- Slice table: add object/attribute/relation N and CI.

## 4. Experiment B: Parser and BEM Audit

Purpose:

Fix two clarity problems without new inference:

- `Invalid JSON = 0.0` is misleading because the scorer falls back to labeled
  fields and support inference.
- `BEM` is unclear in the short-answer table.

Parser audit outputs:

| Metric | Meaning |
| --- | --- |
| strict_json_valid | Raw generation contains parseable JSON object. |
| parse_failure_rate | No useful answer/support/claim/evidence fields could be recovered. |
| scored_output_rate | Output could be scored after JSON parsing or fallback parsing. |

BEM definition to use in the paper:

```text
BEM is the Base-error-mined diagnostic set: a locked set of examples selected
from errors made by the base model under the standard yes/no prompt. The Base
row is therefore 0.0 by construction when reported as recovery accuracy, while
fine-tuned models receive credit only when they correct those previously
observed base errors.
```

Expected paper change:

- Rename the table column from `BEM` to `BEM Recovery`.
- Add one sentence in the caption or metric paragraph.
- Replace `Invalid JSON` with `Unscored/Parse Fail` or split strict and scored
  rates in appendix.

## 5. Experiment C: CEPO-Dual Verifier-Count Ablation

Purpose:

Show that CEPO-Dual's 2k verifier rows are not arbitrary and identify the
answer/evidence trade-off.

### C1. Settings

| Setting | Answer rows | Supported verifier rows | Wrong verifier rows | Total rows | New training? |
| --- | ---: | ---: | ---: | ---: | --- |
| CEPO Answer-DPO | 6,000 | 0 | 0 | 6,000 | No, reuse. |
| Evidence-DPO only | 0 | 1,000 | 1,000 | 2,000 | Yes. |
| CEPO-Dual-500 | 6,000 | 250 | 250 | 6,500 | Yes. |
| CEPO-Dual-1k | 6,000 | 500 | 500 | 7,000 | Yes. |
| CEPO-Dual-2k | 6,000 | 1,000 | 1,000 | 8,000 | No, reuse current. |

### C2. Data Export Pattern

Use the existing CEPO-Dual exporter arguments, but write each setting to a
separate output directory to avoid overwriting the selected current model.

Examples:

```bash
python scripts/data/14_export_cepo_dual_dpo.py \
  --output-dir data/processed/cepo_dual_ablation/evidence_only_2k \
  --answer-count 0 \
  --supported-verifier-count 1000 \
  --wrong-evidence-verifier-count 1000 \
  --seed 42

python scripts/data/14_export_cepo_dual_dpo.py \
  --output-dir data/processed/cepo_dual_ablation/dual500 \
  --answer-count 6000 \
  --supported-verifier-count 250 \
  --wrong-evidence-verifier-count 250 \
  --seed 42

python scripts/data/14_export_cepo_dual_dpo.py \
  --output-dir data/processed/cepo_dual_ablation/dual1k \
  --answer-count 6000 \
  --supported-verifier-count 500 \
  --wrong-evidence-verifier-count 500 \
  --seed 42
```

Prepare LLaMA-Factory files with variant-specific output directories:

```bash
python scripts/experiments/prepare_llamafactory_data_cepo_dual.py \
  --dual-input data/processed/cepo_dual_ablation/dual500/cepo_dual_dpo_train.jsonl \
  --output-dir experiments/llamafactory_data_cepo_dual_ablation/dual500
```

Implementation note:

- The existing train config points to the default CEPO-Dual dataset and output
  directory.
- Add variant-specific YAML files or a Slurm wrapper that renders temporary
  configs per setting.
- Never overwrite `outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2/`.

### C3. Training

Use the same recipe as the current CEPO-Dual model:

```text
Qwen2.5-VL-7B-Instruct
LoRA-DPO
ZeRO-2
1 epoch
pref_beta = 0.1
LoRA rank = 16
```

Proposed new files:

```text
experiments/llamafactory_configs/qwen25vl_cepo_evidence_only_dpo.yaml
experiments/llamafactory_configs/qwen25vl_cepo_dual500_dpo.yaml
experiments/llamafactory_configs/qwen25vl_cepo_dual1k_dpo.yaml
experiments/slurm/submit_cepo_ablation_pipeline.sh
experiments/slurm/train_cepo_ablation_dpo.slurm
```

### C4. Evaluation

For every ablation adapter:

Internal short-answer evals:

```text
data/eval/coco_heldout_object_existence.jsonl
data/eval/gqa_simple_heldout.jsonl
data/eval/coco_hard_object_existence.jsonl
```

Evidence probes:

```text
data/eval/cepo_evidence_probe.jsonl
data/eval/cepo_wrong_evidence_probe.jsonl
```

Optional only for the best ablation:

```text
data/eval/base_error_mined_object_existence.jsonl
data/eval/pope_coco_random.jsonl
data/eval/pope_coco_popular.jsonl
data/eval/pope_coco_adversarial.jsonl
data/eval/amber_discriminative.jsonl
```

Do not run all external benchmarks for every ablation unless the internal
results are surprising.

### C5. Ablation Table Shell

| Setting | COCO Acc | GQA Acc | Hard Acc | Supp. Acc | Wrong Rej. | Object Wrong | Attr. Wrong | Rel. Wrong | Parse Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CEPO Answer-DPO |  |  |  |  |  |  |  |  |  |
| Evidence-DPO only |  |  |  |  |  |  |  |  |  |
| CEPO-Dual-500 |  |  |  |  |  |  |  |  |  |
| CEPO-Dual-1k |  |  |  |  |  |  |  |  |  |
| CEPO-Dual-2k |  |  |  |  |  |  |  |  |  |

Success interpretation:

- If verifier rows improve wrong-evidence rejection while preserving COCO/GQA
  within about 0.5 points of Answer-DPO, the CEPO-Dual design is justified.
- If evidence-only improves evidence probes but hurts short-answer transfer,
  the paper gains evidence for separability.
- If relation wrong-evidence remains low across all settings, emphasize that
  relation verification requires stronger region-aware supervision.

## 6. Experiment D: Relation Failure Analysis

Purpose:

Turn the weakest metric into a useful analysis section.

Inputs:

```text
scored CEPO wrong-evidence relation rows for Base, CEPO Answer-DPO, CEPO-Dual
```

Sampling plan:

| Bucket | Count |
| --- | ---: |
| CEPO-Dual correctly rejects relation wrong-evidence | 4 |
| CEPO-Dual falsely accepts relation wrong-evidence | 6 |
| All models fail | 4 |
| Answer-DPO fails but CEPO-Dual succeeds | 4 |

Failure categories:

- subject/object swap;
- left/right ambiguity;
- both objects visible but relation unsupported;
- copied candidate evidence without verification;
- candidate relation text under-specified.

Expected paper use:

- one compact qualitative table in the main text;
- more examples in appendix;
- one paragraph explaining why object/attribute rejection is easier than
  relation rejection.

## 7. Optional Experiment E: Seed Check

Run only after Experiment C if compute budget is still available.

Minimal seed check:

| Model | Extra seeds | Reason |
| --- | ---: | --- |
| CEPO-Dual-2k | 2 | Tests selected method stability. |
| CEPO Answer-DPO | 1 | Gives an answer-only reference without doubling the whole matrix. |

Report mean/std in appendix, not the main table, unless variance is large.

## 8. What Not To Do Now

- Do not expand to many backbones before finishing CI, ablation, and relation
  analysis.
- Do not increase CEPO-Probe data size before explaining the existing 6k data
  better.
- Do not add another method name unless it directly answers a reviewer concern.
- Do not run GPU jobs outside Slurm.
