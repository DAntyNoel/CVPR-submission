# Answer-Evidence Mix DPO

## Goal

This task implements the low-cost rescue experiment proposed after the second
midterm report: keep the stability of plain Answer-DPO while injecting a
smaller amount of response-side evidence supervision.

The default mix is conservative:

```text
70% plain Answer-DPO rows
30% Evidence-Hint DPO rows
seed 42
```

The hypothesis is that the plain rows preserve Answer-DPO accuracy and recall,
while the evidence rows retain part of the false-positive reduction seen in
Evidence-Hint DPO.

The completed 30% run and the follow-up low-ratio analysis are summarized in
`LOW_RATIO_STUDY.md`. The short version: 30% slightly improves COCO/GQA but
hurts Hard COCO and base-error recovery, so the next ratio to test is 15%, not
50%.

## Implemented Files

```text
scripts/data/04_export_dpo_formats.py
  Exports data/processed/answer_evidence_mix_dpo_train.jsonl by default.

scripts/experiments/prepare_llamafactory_data.py
  Registers cvpr_answer_evidence_mix_dpo for LLaMA-Factory.

experiments/llamafactory_configs/qwen25vl_answer_evidence_mix_dpo.yaml
  ZeRO-2 LoRA-DPO training config.

experiments/slurm/train_answer_evidence_mix_dpo.slurm
  GPU Slurm wrapper for training.

experiments/slurm/submit_answer_evidence_mix_dpo.sh
  Submits training plus after-ok COCO/GQA/Hard COCO/Base-error evals.

scripts/eval/run_vlm_inference.py
  Adds model key answer_evidence_mix_dpo.
```

## Data Regeneration

Regenerate all 5k DPO sidecars, including the new mixed-format sidecar:

```bash
python scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-evidence-mix-evidence-ratio 0.3 \
  --answer-evidence-mix-seed 42

python scripts/experiments/prepare_llamafactory_data.py \
  --output-dir experiments/llamafactory_data
```

To test a lower 15% evidence mix without overwriting the completed 30% run,
write it to a separate sidecar and LLaMA-Factory data directory:

```bash
python scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-evidence-mix-output data/processed/answer_evidence_mix_r015_dpo_train.jsonl \
  --answer-evidence-mix-evidence-ratio 0.15 \
  --answer-evidence-mix-seed 42

python scripts/experiments/prepare_llamafactory_data.py \
  --answer-evidence-mix-input data/processed/answer_evidence_mix_r015_dpo_train.jsonl \
  --output-dir experiments/llamafactory_data_answer_evidence_r015
```

The existing LLaMA-Factory dataset key can stay `cvpr_answer_evidence_mix_dpo`
if the train config points `dataset_dir` to the r015 directory.

## Training And Evaluation

Do not run 7B training directly in the interactive shell. Submit the Slurm
chain:

```bash
bash experiments/slurm/submit_answer_evidence_mix_dpo.sh
```

This writes the adapter to:

```text
outputs/llamafactory/qwen25vl7b_answer_evidence_mix_dpo_zero2/
```

Evaluation generations use:

```text
results/eval/generations/<eval_name>/answer_evidence_mix/answer_evidence_mix_dpo.jsonl
```

## Success Criteria

Treat this as a rescue experiment only if it improves the trade-off against the
current Evidence-Hint run:

```text
Hard COCO: lower FPR than Answer-DPO, with Acc/F1 no worse by more than 0.2-0.3 pt
GQA simple: no clear degradation relative to Answer-DPO
Base-error-mined: recovery above current Evidence-Hint DPO, ideally near Answer-DPO
```

If the mix still trails Answer-DPO on Acc/F1, keep it as a diagnostic result
and do not expand the main paper beyond the original three-group comparison.

## Completed 30% Result

```text
train job: 64448
eval jobs: 64449 COCO, 64450 GQA, 64451 Hard COCO, 64452 Base-error
adapter: outputs/llamafactory/qwen25vl7b_answer_evidence_mix_dpo_zero2/
```

Summary:

```text
COCO held-out:    Acc 0.962, F1 0.961, FPR 0.016, FNR 0.060
GQA simple:       Acc 0.771, F1 0.750, FPR 0.146, FNR 0.312
Hard COCO:        Acc 0.942, F1 0.941, FPR 0.044, FNR 0.072
Base-error mined: Acc 0.042, F1 0.073, FPR 0.984, FNR 0.950
```

Interpretation: 30% Mix gives a small standard-split improvement, but it is not
strong enough to rescue the hard/base-error narrative. Use `LOW_RATIO_STUDY.md`
before launching any further ratio runs.
