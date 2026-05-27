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

To test a more aggressive 50/50 mix, change only the ratio:

```bash
python scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-evidence-mix-evidence-ratio 0.5
```

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
