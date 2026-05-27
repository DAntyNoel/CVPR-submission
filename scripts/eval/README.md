# Evaluation Pipeline

This directory contains the lightweight evaluation chain for the three main
groups:

```text
base
answer_dpo
evidence_hint_dpo
```

The scripts are intentionally split into cheap data/metric steps and GPU
inference. Run the model generation through Slurm; do not launch the 7B model
directly on the login/current shell.

## COCO Held-Out Eval

Build the quick COCO object-existence eval JSONL from the held-out image ids:

```bash
python scripts/eval/prepare_coco_heldout_eval.py \
  --heldout-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --output data/eval/coco_heldout_object_existence.jsonl \
  --max-pairs 500 \
  --seed 42
```

Each selected pool pair contributes one yes question for the annotated object
and one no question for the unannotated negative object.

## POPE Eval

Normalize an official POPE object-hallucination annotation file:

```bash
python scripts/eval/prepare_pope_eval.py \
  --input path/to/pope.jsonl \
  --image-root data/raw/coco/val2014 \
  --output data/eval/pope_object_hallucination.jsonl
```

The normalized schema matches the COCO held-out JSONL:

```text
id, image, image_id, question, target, task_type
```

## Unified Inference

Dry-run setup checks are cheap and verify adapter wiring:

```bash
python scripts/eval/run_vlm_inference.py \
  --model-key answer_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --dry-run
```

For `answer_dpo` and `evidence_hint_dpo`, the script refuses to run unless the
LoRA directory contains both `adapter_config.json` and
`adapter_model.safetensors`. This prevents accidentally evaluating the base
model for an adapter row.

GPU generation should be submitted with:

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

Raw generations are saved under:

```text
results/eval/generations/<eval_name>/<model_key>.jsonl
```

Those files keep the image, question, target, prompt, raw generation, model key,
and method name so they can be reused for Table 1 and case study selection.

## Metrics

Score any raw generation file with:

```bash
python scripts/eval/score_object_eval.py \
  --input results/eval/generations/coco_heldout_object_existence/base.jsonl
```

The metrics JSON includes accuracy, F1, yes bias, refusal rate, and a binary
confusion matrix. Refusal rate is triggered by phrases such as `not sure`,
`cannot determine`, `unclear`, and related variants.

