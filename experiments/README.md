# Experiment Startup Notes

This folder contains project-specific wrappers around the cloned
`LLaMA-Factory` training code.

The intended main comparison has three groups:

```text
A. Base Instruct: no training
B. Answer-DPO: experiments/llamafactory_configs/qwen25vl_answer_dpo.yaml
C. Evidence-Hint DPO: experiments/llamafactory_configs/qwen25vl_evidence_hint_dpo.yaml
```

Use the 7B Qwen2.5-VL model for the main run. The scripts expect it at:

```text
models/Qwen2.5-VL-7B-Instruct
```

If it is not available in `/data1/public/hf`, download it on a CPU node:

```bash
sbatch experiments/slurm/download_qwen25vl7b.slurm
```

Then launch training jobs on a GPU partition:

```bash
sbatch experiments/slurm/smoke_dpo.slurm
sbatch experiments/slurm/train_answer_dpo.slurm
sbatch experiments/slurm/train_evidence_hint_dpo.slurm
```

The smoke job runs both DPO variants with `max_samples: 8`, `max_steps: 2`,
`template: qwen2_vl`, and ZeRO-3. The full jobs use the same fixed template and
the same LLaMA-Factory data registry.

Training and smoke scripts use the `verl0.6` conda environment. It is pinned to
torch 2.8.0 to avoid the LLaMA-Factory torch 2.9 + Conv3D guard for Qwen2.5-VL.

The current processed data is the 2026-05-27 mixed COCO+GQA split: 3,500 COCO
object-existence pairs plus 1,500 GQA simple attribute/relation pairs. Before
launching training, regenerate the LLaMA-Factory JSON export with:

```bash
python scripts/experiments/prepare_llamafactory_data.py \
  --answer-input data/processed/answer_dpo_train.jsonl \
  --evidence-input data/processed/evidence_hint_dpo_train.jsonl \
  --output-dir experiments/llamafactory_data
```

The mixed jobs write to:

```text
outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo/
```

The older `qwen25vl7b_answer_dpo/` and `qwen25vl7b_evidence_hint_dpo/`
directories correspond to COCO-only preliminary jobs 64167 and 64168. Keep
them out of the mixed-data main table.

## Evaluation Startup

The unified eval scripts live in `scripts/eval/`.

Build the lightweight held-out eval set:

```bash
python scripts/eval/prepare_coco_heldout_eval.py \
  --heldout-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --output data/eval/coco_heldout_object_existence.jsonl \
  --max-pairs 500 \
  --seed 42
```

Build the GQA simple held-out eval set:

```bash
python scripts/eval/prepare_gqa_simple_heldout_eval.py \
  --candidates data/processed/canonical_gqa_candidates.jsonl \
  --train data/processed/canonical_pairs_main.jsonl \
  --output data/eval/gqa_simple_heldout.jsonl \
  --max-rows 1000 \
  --seed 42
```

Normalize POPE annotations when the official POPE file is available:

```bash
python scripts/eval/prepare_pope_eval.py \
  --input path/to/pope.jsonl \
  --image-root data/raw/coco/val2014 \
  --output data/eval/pope_object_hallucination.jsonl
```

After the mixed adapter directories are written, check adapter wiring without
loading the model:

```bash
python scripts/eval/run_vlm_inference.py \
  --model-key answer_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --dry-run
```

The inference script refuses to run `answer_dpo` or `evidence_hint_dpo` unless
the LoRA adapter directory contains both `adapter_config.json` and
`adapter_model.safetensors`, preventing adapter rows from silently evaluating
the base model.

Submit GPU eval jobs with:

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

Raw generations and metadata are written to:

```text
results/eval/generations/<eval_name>/<model_key>.jsonl
results/eval/generations/<eval_name>/<model_key>.metadata.json
```

Score saved generations with:

```bash
python scripts/eval/score_object_eval.py \
  --input results/eval/generations/coco_heldout_object_existence/base.jsonl
```
