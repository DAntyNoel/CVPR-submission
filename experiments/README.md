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

Mixed Evidence-Hint DPO uses ZeRO-2 by default. The default wrapper is:

```bash
sbatch experiments/slurm/train_evidence_hint_dpo.slurm
```

The smoke job runs both DPO variants with `max_samples: 8`, `max_steps: 2`,
`template: qwen2_vl`, and ZeRO-3. The full jobs use the same fixed template and
the same LLaMA-Factory data registry. Evidence-Hint now keeps the same data,
LoRA, and global-batch settings, but uses ZeRO-2 and writes to a `_zero2`
output directory. `train_evidence_hint_dpo_zero2.slurm` is retained as an
explicit compatibility wrapper.

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
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2/
```

2026-05-27 ZeRO-2 status: job 64252 completed on RTX4090 from
`experiments/slurm/train_evidence_hint_dpo_zero2.slurm` and replaces the old
ZeRO-3 job 64201. The run used about 15.6GB allocated memory at optimizer
initialization and finished in 00:17:13 wall time (`train_runtime` 950.96s,
train loss 0.1347). The zero2 adapter dry-run passed, and the eval registry now
uses this adapter by default.

The older `qwen25vl7b_answer_dpo/` and `qwen25vl7b_evidence_hint_dpo/`
directories correspond to COCO-only preliminary jobs 64167 and 64168. Keep
them out of the mixed-data main table.

## 10k Mixed Scale-Up

Use the scale-up only as a diagnostic for whether data size changes the
Evidence-Hint trend. It keeps the same three method groups and writes separate
data, adapter, and eval output variants:

```bash
bash experiments/slurm/submit_mixed10k_scaleup.sh
```

The submission chain runs CPU data prep first, then the two 10k DPO trainings,
then COCO held-out, GQA simple, Hard COCO, and base-error-mined evals with
`OUTPUT_VARIANT=mixed10k`. The 10k configs are:

```text
experiments/llamafactory_configs/qwen25vl_answer_dpo_10k.yaml
experiments/llamafactory_configs/qwen25vl_evidence_hint_dpo_10k.yaml
```

Adapters will be written to:

```text
outputs/llamafactory/qwen25vl7b_mixed10k_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed10k_evidence_hint_dpo_zero2/
```

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

Build the Hard COCO held-out eval set:

```bash
python scripts/eval/prepare_coco_hard_eval.py \
  --heldout-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --output data/eval/coco_hard_object_existence.jsonl \
  --max-pairs 500 \
  --seed 42
```

The current Hard COCO file has 1,000 rows, yes/no balanced, 500 unique images,
and zero train/eval image overlap.

Prepare official POPE/AMBER external benchmark metadata and normalized eval
JSONL files:

```bash
python scripts/eval/prepare_official_external_benchmarks.py
```

This produces POPE random/popular/adversarial and AMBER discriminative eval
files under `data/eval/`. It only downloads official annotations/query files.
Before GPU evaluation, place COCO val2014 images at `data/raw/coco/val2014`
and AMBER official images at `data/raw/amber/images`. Submit the fixed
Base/Answer-DPO/Evidence-Hint DPO comparison with:

```bash
DRY_RUN=1 scripts/eval/submit_external_benchmark_evals.sh
scripts/eval/submit_external_benchmark_evals.sh
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

For the COCO-only controlled validation in
`idea-lightweighted-grounded-preference-vlm/main_experiment_core_claims/`, pin
the already-finished 5k COCO adapters with `ADAPTER_NAME_OR_PATH`:

```bash
MODEL_KEY=answer_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
ADAPTER_NAME_OR_PATH=outputs/llamafactory/qwen25vl7b_answer_dpo \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm

MODEL_KEY=evidence_hint_dpo EVAL_JSONL=data/eval/coco_heldout_object_existence.jsonl \
ADAPTER_NAME_OR_PATH=outputs/llamafactory/qwen25vl7b_evidence_hint_dpo \
  sbatch experiments/slurm/eval_vlm_object_hallucination.slurm
```

2026-05-27 COCO-only validation launch:

```text
64205  Base Instruct
64206  Answer-DPO        outputs/llamafactory/qwen25vl7b_answer_dpo
64207  Evidence-Hint DPO outputs/llamafactory/qwen25vl7b_evidence_hint_dpo
```

2026-05-27 Hard COCO mixed validation while waiting for 64201:

```text
64233  COMPLETED  Base Instruct      Acc 0.944, F1 0.943
64234  COMPLETED  mixed Answer-DPO   Acc 0.950, F1 0.949
```

Current Evidence-Hint eval status:

```text
64201  CANCELLED            old ZeRO-3 training, replaced by 64252
64235  CANCELLED            old afterok:64201 COCO held-out
64236  CANCELLED            old afterok:64201 GQA simple
64237  CANCELLED            old afterok:64201 Hard COCO
64238  CANCELLED            old afterok:64201 GQA evidence-style
64239  CANCELLED            old afterok:64201 COCO evidence-style
64255  COMPLETED            Evidence-Hint DPO COCO held-out, mixed_zero2, Acc 0.961
64256  COMPLETED            Evidence-Hint DPO GQA simple, mixed_zero2, Acc 0.766
64257  COMPLETED            Evidence-Hint DPO Hard COCO, mixed_zero2, Acc 0.946
64258  COMPLETED            Evidence-Hint DPO COCO held-out, evidence_prompt_zero2, Acc 0.955
64259  COMPLETED            Evidence-Hint DPO GQA simple, evidence_prompt_zero2, Acc 0.767
64263  CANCELLED            old afterok:64201 base-error-mined eval
64251  COMPLETED            Base candidate mining, Acc 0.9472 on 10,000 rows
64262  COMPLETED            Base-error-mined locked set, Base recovery 0.000
64264  COMPLETED            Base-error-mined locked set, Answer-DPO recovery 0.063
64267  COMPLETED            Base-error-mined locked set, Evidence-Hint DPO recovery 0.030
```

Completed mixed results support the diagnostic Plan B reading: Evidence-Hint
DPO slightly lowers some false-positive rates but does not consistently beat
Answer-DPO on overall Acc/F1 or Base-error recovery. Do not re-submit the same
COCO/GQA/Hard COCO/evidence-style/base-error-mined jobs unless their output
files are explicitly missing.

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
