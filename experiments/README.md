# Experiment Startup Notes

This folder contains project-specific wrappers around the cloned
`LLaMA-Factory` training code.

The intended main comparison has three groups:

```text
A. Base Instruct: no training
B. Answer-DPO: experiments/llamafactory_configs/qwen25vl_answer_dpo.yaml
C. Evidence-Hint DPO: experiments/llamafactory_configs/qwen25vl_evidence_hint_dpo.yaml
```

The active V2/CEPO comparison keeps the same three-group discipline but changes
the trained methods:

```text
A. Base Instruct: no training
B. CEPO Answer-DPO: experiments/llamafactory_configs/qwen25vl_cepo_answer_dpo.yaml
C. CEPO-Latent: experiments/llamafactory_configs/qwen25vl_cepo_latent_dpo.yaml
```

Use the 7B Qwen2.5-VL model for the main run. The scripts expect it at:

```text
models/Qwen2.5-VL-7B-Instruct
```

If it is not available in `/data1/public/hf`, download it on a CPU node:

```bash
sbatch experiments/slurm/download_qwen25vl7b.slurm
```

For a model-size diagnostic, use Qwen2.5-VL-32B rather than replacing the main
7B table. First look for a shared copy under `/data1/public/hf`; if it is not
present, download on a CPU node through the Hugging Face mirror and prepare the
isolated 32B data exports with:

```bash
sbatch experiments/slurm/download_qwen25vl32b_and_prepare_data.slurm
```

The script clears `http_proxy`, `https_proxy`, and `all_proxy`, sets
`HF_ENDPOINT=https://hf-mirror.com`, verifies the downloaded model files, and
writes model-size diagnostic data to:

```text
data/processed/qwen25vl32b/
experiments/llamafactory_data_qwen25vl32b/
experiments/llamafactory_data_input_side_main_qwen25vl32b/
```

## CEPO V2 Main Pipeline

CEPO data is generated as an isolated sidecar so it does not overwrite the V1
mixed-data artifacts:

```bash
python scripts/data/12_build_cepo_claim_evidence.py
python scripts/data/13_check_cepo_data.py
python scripts/experiments/prepare_llamafactory_data_cepo.py
python scripts/eval/prepare_cepo_evidence_probe.py
```

The generated files are:

```text
data/processed/cepo/claim_evidence_canonical.jsonl
data/processed/cepo/answer_dpo_train.jsonl
data/processed/cepo/cepo_latent_dpo_train.jsonl
experiments/llamafactory_data_cepo/dataset_info.json
data/eval/cepo_evidence_probe.jsonl
data/eval/cepo_wrong_evidence_probe.jsonl
```

Launch the two ZeRO-2 training jobs plus dependent eval jobs with:

```bash
bash experiments/slurm/submit_cepo_pipeline.sh
```

For training only, use:

```bash
bash experiments/slurm/submit_cepo_main.sh
```

Adapters and generations are written to:

```text
outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2/
outputs/llamafactory/qwen25vl7b_cepo_latent_dpo_zero2/
results/eval/generations/<eval_name>/cepo/<model_key>.jsonl
results/eval/generations/<eval_name>/cepo_external/<model_key>.jsonl
results/eval/generations/<eval_name>/cepo_evidence_probe/<model_key>.jsonl
```

For the archived V1 Evidence-Hint startup, launch training jobs on a GPU
partition:

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

## Answer-Evidence Mix DPO

The Answer-Evidence Mix DPO rescue run follows
`tasks/answer-evidence-mix-dpo/README.md`. It keeps the same 5k mixed
COCO/GQA split, backbone, LoRA-DPO hyperparameters, and ZeRO-2 setup. The only
change is the training data format: by default, 70% of rows use plain
Answer-DPO responses and 30% use Evidence-Hint responses.

The completed 30% run is useful but not sufficient as a main-method rescue:
COCO/GQA improve slightly, while Hard COCO and Base-error-mined weaken. The
follow-up ratio memo is `tasks/answer-evidence-mix-dpo/LOW_RATIO_STUDY.md`; if
one more response-side evidence run is launched, use 15% evidence as the next
point.

Regenerate the LLaMA-Factory data with:

```bash
python scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-evidence-mix-evidence-ratio 0.3 \
  --answer-evidence-mix-seed 42

python scripts/experiments/prepare_llamafactory_data.py \
  --output-dir experiments/llamafactory_data
```

The dataset is registered as:

```text
cvpr_answer_evidence_mix_dpo
```

Launch training plus COCO/GQA/Hard COCO/Base-error after-ok evals with:

```bash
bash experiments/slurm/submit_answer_evidence_mix_dpo.sh
```

The adapter and eval outputs will be written to:

```text
outputs/llamafactory/qwen25vl7b_answer_evidence_mix_dpo_zero2/
results/eval/generations/<eval_name>/answer_evidence_mix/answer_evidence_mix_dpo.jsonl
```

## Phase 2 Method Variants

The first Phase-2 method round follows
`idea-imporve-evidence/phase2_method_ideas.md` and keeps the same 5k
COCO/GQA mixed split, backbone, LoRA-DPO hyperparameters, and ZeRO-2 setup.
Only the preference format changes:

```text
Evidence-Only DPO        chosen/rejected share the same answer; evidence consistency differs
Input-Side Evidence DPO  supported evidence moves into the user prompt; responses stay plain
Chosen-Only Evidence DPO supported evidence is appended only to the chosen response
```

Regenerate all Answer/Evidence-Hint/Mix/Phase-2 LLaMA-Factory data with:

```bash
python scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl

python scripts/experiments/prepare_llamafactory_data.py \
  --output-dir experiments/llamafactory_data
```

The Phase-2 datasets are registered as:

```text
cvpr_phase2_evidence_only_dpo
cvpr_phase2_input_side_evidence_dpo
cvpr_phase2_chosen_only_evidence_dpo
```

Launch the three method jobs with:

```bash
bash experiments/slurm/submit_phase2_method_variants.sh
```

This submission script also attaches after-ok eval jobs for COCO held-out, GQA
simple, Hard COCO, and the Base-error-mined diagnostic set. The eval outputs
use `OUTPUT_VARIANT=phase2`.

The configs are:

```text
experiments/llamafactory_configs/qwen25vl_phase2_evidence_only_dpo.yaml
experiments/llamafactory_configs/qwen25vl_phase2_input_side_evidence_dpo.yaml
experiments/llamafactory_configs/qwen25vl_phase2_chosen_only_evidence_dpo.yaml
```

Adapters will be written to:

```text
outputs/llamafactory/qwen25vl7b_phase2_evidence_only_dpo_zero2/
outputs/llamafactory/qwen25vl7b_phase2_input_side_evidence_dpo_zero2/
outputs/llamafactory/qwen25vl7b_phase2_chosen_only_evidence_dpo_zero2/
```

Phase-2 eval generations will be written to:

```text
results/eval/generations/<eval_name>/phase2/phase2_evidence_only_dpo.jsonl
results/eval/generations/<eval_name>/phase2/phase2_input_side_evidence_dpo.jsonl
results/eval/generations/<eval_name>/phase2/phase2_chosen_only_evidence_dpo.jsonl
```

2026-05-27 completed status:

```text
64302  COMPLETED  Phase-2 Evidence-Only DPO train
64303  COMPLETED  Phase-2 Input-Side Evidence DPO train
64304  COMPLETED  Phase-2 Chosen-Only Evidence DPO train
64305-64308  COMPLETED  Evidence-Only COCO/GQA/Hard COCO/Base-error evals
64309-64312  COMPLETED  Input-Side COCO/GQA/Hard COCO/Base-error evals
64313-64316  COMPLETED  Chosen-Only COCO/GQA/Hard COCO/Base-error evals
```

Phase-2 result:

```text
COCO held-out:
  Evidence-Only Acc 0.959/F1 0.958/FPR 0.018
  Input-Side   Acc 0.961/F1 0.960/FPR 0.016
  Chosen-Only  Acc 0.961/F1 0.960/FPR 0.016
GQA simple:
  Evidence-Only Acc 0.765/F1 0.741/FPR 0.142
  Input-Side   Acc 0.768/F1 0.747/FPR 0.150
  Chosen-Only  Acc 0.765/F1 0.741/FPR 0.144
Hard COCO:
  Evidence-Only Acc 0.942/F1 0.941/FPR 0.040
  Input-Side   Acc 0.947/F1 0.946/FPR 0.038
  Chosen-Only  Acc 0.946/F1 0.945/FPR 0.038
Base-error-mined recovery:
  Evidence-Only 0.015, Input-Side 0.044, Chosen-Only 0.032
```

Input-Side Evidence is the best Phase-2 variant, but it remains a diagnostic
side result rather than a replacement for the three-group main paper table.

## Balanced Hard Input-Side Evidence DPO

The Input-Side main-method rescue follows
`tasks/input-side-evidence-main-method/README.md`. It keeps responses as plain
short answers and moves all lightweight evidence into the user prompt as
`Visual cue: ...`. The balanced-hard version uses 5,500 rows:

```text
1,000 Hard COCO-style pairs
1,000 Base-error-mined pairs
2,500 canonical COCO paired rows
1,000 GQA anchors
```

Regenerate the data and launch training plus four after-ok evals with:

```bash
bash experiments/slurm/submit_input_side_main_balanced_hard_dpo.sh
```

The config, adapter, and eval outputs are:

```text
experiments/llamafactory_configs/qwen25vl_input_side_main_balanced_hard_dpo.yaml
outputs/llamafactory/qwen25vl7b_input_side_main_balanced_hard_dpo_zero2/
results/eval/generations/<eval_name>/input_side_main/input_side_main_balanced_hard_dpo.jsonl
```

2026-05-27 completed status:

```text
64443  COMPLETED  Balanced Hard Input-Side Evidence DPO train
64444  COMPLETED  COCO held-out eval
64445  COMPLETED  GQA simple eval
64446  COMPLETED  Hard COCO eval
64447  COMPLETED  Base-error-mined eval
```

Main result:

```text
COCO held-out:     Acc 0.966/F1 0.965/FPR 0.018/FNR 0.050
GQA simple:        Acc 0.766/F1 0.748/FPR 0.162/FNR 0.306
Hard COCO:         Acc 0.947/F1 0.947/FPR 0.048/FNR 0.058
Base-error-mined:  Acc 0.120/F1 0.214/FPR 1.000/FNR 0.844
```

External sanity checks completed with `OUTPUT_VARIANT=input_side_main_external`
for POPE random/popular/adversarial and AMBER discriminative. The pattern is
consistent with the main evals: better recall and slightly higher Acc/F1 on
POPE, but higher FPR/yes-bias than the fixed mixed Answer-DPO baseline. Treat
this as a rescue/diagnostic result, not as a solved false-positive-control
method.

## 10k Mixed Scale-Up

Use the scale-up only as a diagnostic for whether data size changes the
Evidence-Hint trend. It keeps the same three method groups and writes separate
data, adapter, and eval output variants:

```bash
bash experiments/slurm/submit_mixed10k_scaleup.sh
```

The submission chain runs CPU data prep first, then the two 10k DPO trainings,
then COCO held-out, GQA simple, and Hard COCO evals with
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

2026-05-27 launch status:

```text
64272-64282  CANCELLED  first attempt; excluding the base-error-mining image pool left only 4,586 COCO pairs
64283-64291  CANCELLED  second attempt; replaced to avoid overwriting Phase-2 default DPO sidecar files
64293-64301  CANCELLED  third attempt; replaced with concurrent GQA/VG downloading
64321-64329  CANCELLED  fourth attempt; replaced to cap GQA/VG target downloads at 4,300 with a 4,200 success threshold
64369        COMPLETED  wrote 6k COCO + 4k GQA, 10k DPO exports, audit summary, leakage report, and LLaMA-Factory registry
64370        CANCELLED  old 10k Answer-DPO ZeRO-3 train; reached the train loop but was too slow on RTX4090
64371        COMPLETED  10k Evidence-Hint DPO ZeRO-2 train, afterok:64369, runtime 33:51
64372-64374  CANCELLED  old Answer-DPO eval deps, tied to 64370
64375-64377  COMPLETED  10k Evidence-Hint COCO/GQA/Hard COCO evals, afterok:64371
64397        COMPLETED  10k Answer-DPO ZeRO-2 train on A100,L40S,ADA6000, replacing 64370, runtime 30:50
64398-64400  COMPLETED  10k Answer-DPO COCO/GQA/Hard COCO evals, afterok:64397
```

10k result:

```text
COCO held-out:  Answer-DPO Acc 0.965/F1 0.964/FPR 0.018; Evidence-Hint Acc 0.961/F1 0.960/FPR 0.016
GQA simple:     Answer-DPO Acc 0.769/F1 0.752/FPR 0.164; Evidence-Hint Acc 0.766/F1 0.743/FPR 0.146
Hard COCO:      Answer-DPO Acc 0.948/F1 0.948/FPR 0.048; Evidence-Hint Acc 0.944/F1 0.943/FPR 0.038
```

The 10k scale-up preserves the 5k pattern: Evidence-Hint reduces false
positives, especially on GQA and Hard COCO, but still does not beat Answer-DPO
on Acc/F1.

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
and AMBER images at `data/raw/amber/images`; the CPU Slurm helper fills those
roots and falls back to the `visual-preference/AMBER` HF parquet mirror if
Google Drive is blocked:

```bash
sbatch scripts/data/prepare_external_eval_images.slurm
```

Submit the fixed Base/Answer-DPO/Evidence-Hint DPO comparison with:

```bash
DRY_RUN=1 scripts/eval/submit_external_benchmark_evals.sh
scripts/eval/submit_external_benchmark_evals.sh
```

For the full AMBER split, set `IMAGE_MAX_PIXELS=1003520` to avoid very large
visual-token counts on high-resolution AMBER images.

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
