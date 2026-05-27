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

## Hard COCO Eval

Build the harder COCO object-existence eval JSONL directly from COCO
annotations and the held-out image ids:

```bash
python scripts/eval/prepare_coco_hard_eval.py \
  --heldout-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --output data/eval/coco_hard_object_existence.jsonl \
  --max-pairs 500 \
  --seed 42
```

Each selected image contributes one visible-object yes question and one
same-coarse-group absent-object no question, with low-confidence negatives
filtered by default. The current output has 1,000 rows, yes/no balanced, 500
unique images, and `train_eval_image_overlap = 0`; see
`data/eval/coco_hard_object_existence.summary.json`.

## Base-Error Mining Eval

Build a larger COCO object-existence candidate pool for Base-conditioned
diagnostic mining:

```bash
python scripts/data/09_prepare_eval_image_ids.py \
  --output data/eval/base_error_mining_image_ids.txt \
  --report data/eval/base_error_mining_image_ids.summary.json \
  --max-ids 3000 \
  --seed 42

python scripts/eval/prepare_base_error_mining_candidates.py \
  --heldout-image-ids data/eval/base_error_mining_image_ids.txt \
  --max-rows 10000 \
  --max-pairs-per-image 8 \
  --seed 42
```

Run Base candidate inference through Slurm:

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/base_error_mining_candidates.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

After Base generations and metrics are written, mine the locked diagnostic set:

```bash
python scripts/eval/mine_base_errors.py \
  --input results/eval/generations/base_error_mining_candidates/mixed/base.jsonl \
  --max-rows 600 \
  --audit-sample-size 150 \
  --seed 42
```

Then run the locked-set evals through the same Slurm entrypoint. Summarize the
completed generations with:

```bash
python scripts/eval/summarize_base_error_mining_results.py
```

The default Evidence-Hint registry now uses the completed ZeRO-2 adapter from
job 64252. If an older or alternate Evidence-Hint run uses an explicit
adapter/output variant, pass `--evidence-file` to point at that generation
file.

Current completed Base-error-mined results: candidate mining job 64251 produced
10,000 Base generations with Acc 0.9472; the locked diagnostic set has 527
rows. Locked-set jobs 64262/64264/64267 completed for Base/Answer-DPO/
Evidence-Hint DPO. Answer-DPO recovery is 0.063 and Evidence-Hint DPO recovery
is 0.030, so this diagnostic does not support a positive Evidence-Hint delta.

## GQA Simple Held-Out Eval

Build the small GQA simple eval set from unused GQA candidate pairs:

```bash
python scripts/eval/prepare_gqa_simple_heldout_eval.py \
  --candidates data/processed/canonical_gqa_candidates.jsonl \
  --train data/processed/canonical_pairs_main.jsonl \
  --output data/eval/gqa_simple_heldout.jsonl \
  --max-rows 1000 \
  --seed 42
```

The default output is yes/no balanced and uses only color attributes plus
left/right spatial relations. It excludes all GQA image ids used by the mixed
training set and writes a summary to:

```text
data/eval/gqa_simple_heldout.summary.json
```

## Official POPE/AMBER External Eval

Prepare the official POPE and AMBER query/annotation files and normalize them
into the shared yes/no eval schema:

```bash
python scripts/eval/prepare_official_external_benchmarks.py
```

This writes:

```text
data/eval/pope_coco_random.jsonl
data/eval/pope_coco_popular.jsonl
data/eval/pope_coco_adversarial.jsonl
data/eval/amber_discriminative.jsonl
```

The helper sparse-clones only lightweight official metadata from the POPE and
AMBER GitHub repos. It does not download image archives. POPE expects COCO
val2014 images under `data/raw/coco/val2014`; AMBER images should be unpacked
under `data/raw/amber/images`. Missing image counts are reported in each
summary JSON.

For a small wiring check of AMBER only, cap each dimension:

```bash
python scripts/eval/prepare_official_external_benchmarks.py \
  --amber-max-records-per-dimension 100
```

To normalize an already downloaded official POPE file manually:

```bash
python scripts/eval/prepare_pope_eval.py \
  --input data/raw/external/pope/output/coco/coco_pope_random.json \
  --image-root data/raw/coco/val2014 \
  --output data/eval/pope_coco_random.jsonl \
  --source-name pope_coco_random \
  --sampling-strategy random
```

To normalize official AMBER discriminative queries manually:

```bash
python scripts/eval/prepare_amber_eval.py \
  --annotation data/raw/external/amber/data/annotations.json \
  --query-root data/raw/external/amber/data/query \
  --image-root data/raw/amber/images \
  --output data/eval/amber_discriminative.jsonl
```

Both normalized schemas match the COCO held-out JSONL and add benchmark fields:

```text
id, source, source_id, benchmark, dimension, image, image_id, question, target, task_type
```

Submit the three fixed model groups on all prepared external evals through
Slurm:

```bash
DRY_RUN=1 scripts/eval/submit_external_benchmark_evals.sh
scripts/eval/submit_external_benchmark_evals.sh
```

## Unified Inference

Once the mixed adapter directories exist, dry-run setup checks are cheap and
verify adapter wiring:

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

The default adapter paths point to the mixed-data main adapters:

```text
outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2/
```

Phase-2 method keys are also registered for dependent eval jobs after training:

```text
phase2_evidence_only_dpo
phase2_input_side_evidence_dpo
phase2_chosen_only_evidence_dpo
```

GPU generation should be submitted with:

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

Hard COCO uses the same Slurm entrypoint:

```bash
MODEL_KEY=base EVAL_JSONL=data/eval/coco_hard_object_existence.jsonl OUTPUT_VARIANT=mixed \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

Raw generations are saved under:

```text
results/eval/generations/<eval_name>/<model_key>.jsonl
results/eval/generations/<eval_name>/<output_variant>/<model_key>.jsonl
```

Those files keep the image, question, target, prompt, raw generation, model key,
and method name so they can be reused for Table 1 and case study selection.
Use `OUTPUT_VARIANT` whenever a run should not overwrite an existing result,
for example `mixed` for the current COCO+GQA adapters or `evidence_prompt` for
an alternate prompting view.

Evidence-style prompt evaluation reuses the same inference and scoring scripts,
but changes the instruction suffix and writes to a separate variant directory:

```bash
MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/gqa_simple_heldout.jsonl \
OUTPUT_VARIANT=evidence_prompt \
INSTRUCTION_SUFFIX="Answer yes or no, then briefly mention the visual evidence." \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

## Metrics

Score any raw generation file with:

```bash
python scripts/eval/score_object_eval.py \
  --input results/eval/generations/coco_heldout_object_existence/base.jsonl
```

The metrics JSON includes:

- accuracy, balanced accuracy, precision, recall, specificity, F1, negative F1
- false positive rate and false negative rate
- yes/no bias, refusal rate, other/invalid prediction rate
- evidence-cue rate and generation length statistics
- binary confusion matrix and prediction/target counts
- subgroup metrics for `benchmark`, `source`, `dimension`, `task_type`,
  `target`, and `target_text` when at least 20 examples are available

Refusal rate is triggered by phrases such as `not sure`, `cannot determine`,
`unclear`, and related variants.

The same scorer can be used for COCO held-out, Hard COCO, POPE, AMBER
discriminative, and the yes/no GQA simple eval JSONL after model generations
are saved. For AMBER discriminative reporting, use `accuracy` and
`negative_f1`; AMBER's official precision/recall/F1 treat the negative/no class
as the hallucination-detection class. Default subgroup metrics now include
`benchmark` and `dimension`.
