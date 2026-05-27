# Lightweight Evidence-Hint Data Pipeline

This directory implements the data-processing plan in
`idea-lightweighted-grounded-preference-vlm/data_processing_plan.md`.

The scripts only use the Python standard library. They do not download data,
copy large datasets, run GPU jobs, or call model APIs.

## Expected raw data

Link or place the raw annotations/images at:

```text
data/raw/coco/annotations/instances_train2017.json
data/raw/coco/train2017/
data/raw/gqa/train_sceneGraphs.json
data/raw/gqa/images/
```

Large files should be symlinked instead of copied.

Official external benchmark images are prepared separately:

```bash
sbatch scripts/data/prepare_external_eval_images.slurm
```

This CPU Slurm job creates `data/raw/coco/val2014` for POPE and
`data/raw/amber/images` for AMBER, then verifies the normalized external eval
files with `--require-images`. AMBER image prep first tries the official Google
Drive archive and falls back to the `visual-preference/AMBER` HF parquet mirror
when Google Drive is unreachable from the cluster.

If raw COCO/GQA files are not already available, submit the CPU-only HF
download-and-process job:

```bash
sbatch scripts/data/run_hf_download_and_process.slurm
```

The job clears proxy variables, sets `HF_ENDPOINT=https://hf-mirror.com`, uses
the existing `perl` conda environment, downloads a small HF-backed COCO subset,
tries GQA, and falls back to COCO-only 5k pairs if GQA is unavailable.

## Main 5k pipeline

```bash
python scripts/data/01_build_coco_object_pairs.py \
  --instances data/raw/coco/annotations/instances_train2017.json \
  --image-root data/raw/coco/train2017 \
  --output data/processed/canonical_coco_main.jsonl \
  --limit 3500 \
  --seed 42

python scripts/data/02_build_gqa_simple_pairs.py \
  --scene-graphs data/raw/gqa/train_sceneGraphs.json \
  --image-root data/raw/gqa/images \
  --output data/processed/canonical_gqa_main.jsonl \
  --limit 1500 \
  --seed 42

python scripts/data/03_merge_and_split_pairs.py \
  --version main \
  --coco data/processed/canonical_coco_main.jsonl \
  --gqa data/processed/canonical_gqa_main.jsonl \
  --write-default \
  --seed 42

python scripts/data/07_clean_and_balance_pairs.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --output data/processed/canonical_pairs_main_clean.jsonl \
  --stats-output data/processed/stats_main_clean.json \
  --limit 5000 \
  --seed 42

cp data/processed/canonical_pairs_main_clean.jsonl data/processed/canonical_pairs_main.jsonl
cp data/processed/canonical_pairs_main_clean.jsonl data/processed/canonical_pairs.jsonl

python scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-output data/processed/answer_dpo_train.jsonl \
  --evidence-output data/processed/evidence_hint_dpo_train.jsonl \
  --answer-evidence-mix-output data/processed/answer_evidence_mix_dpo_train.jsonl

python scripts/data/05_make_audit_sheet.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --output data/audit/audit_200.csv \
  --sample-size 200 \
  --seed 42

python scripts/data/08_complete_audit_sheet.py \
  --canonical data/processed/canonical_pairs_main.jsonl \
  --audit data/audit/audit_200.csv \
  --summary data/audit/audit_200_summary.json

python scripts/data/09_prepare_eval_image_ids.py \
  --train data/processed/canonical_pairs_main.jsonl \
  --pool data/processed/canonical_coco_pool.jsonl \
  --output data/eval/heldout_object_existence_image_ids.txt \
  --max-ids 1000 \
  --seed 42

python scripts/data/06_check_data_leakage.py \
  --canonical data/processed/canonical_pairs_main.jsonl \
  --answer-dpo data/processed/answer_dpo_train.jsonl \
  --evidence-dpo data/processed/evidence_hint_dpo_train.jsonl \
  --eval-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --report data/processed/check_report_main.json
```

Pass `--eval-image-ids path/to/eval_ids.txt` to the build/check scripts when
POPE, AMBER, or GQA eval image ids are available.

`04_export_dpo_formats.py` also writes the Answer-Evidence Mix DPO sidecar and
the Phase-2 method-variant sidecars by default:

```text
data/processed/answer_evidence_mix_dpo_train.jsonl
data/processed/phase2_evidence_only_dpo_train.jsonl
data/processed/phase2_input_side_evidence_dpo_train.jsonl
data/processed/phase2_chosen_only_evidence_dpo_train.jsonl
```

Answer-Evidence Mix DPO keeps one row per canonical pair and deterministically
exports 70% as plain Answer-DPO rows plus 30% as Evidence-Hint DPO rows by
default. Override this with `--answer-evidence-mix-evidence-ratio` and
`--answer-evidence-mix-seed`.

Evidence-Only keeps answer text fixed and changes only evidence consistency,
Input-Side moves the supported cue into the prompt, and Chosen-Only appends
supported evidence only to the chosen response.

`08_complete_audit_sheet.py` summarizes both COCO object-existence rows and
GQA simple attribute/relation rows. Its checks are label/scene-graph
consistency checks for the sampled audit sheet, not independent pixel-level
relabeling.

## 10k mixed scale-up

The 10k diagnostic keeps the same task families but writes separate artifacts
so the 5k main run remains untouched. Submit it through Slurm because it may
download additional GQA/VG images:

```bash
sbatch scripts/data/prepare_mixed_10k_scaleup.slurm
```

The target split is 6,000 COCO object-existence pairs plus 4,000 GQA simple
attribute/relation pairs. It excludes the current COCO held-out and GQA simple
eval image ids, then exports:

```text
data/processed/canonical_pairs_mixed10k.jsonl
data/processed/answer_dpo_train_mixed10k.jsonl
data/processed/evidence_hint_dpo_train_mixed10k.jsonl
data/processed/answer_evidence_mix_dpo_train_mixed10k.jsonl
experiments/llamafactory_data_10k/
```

When Phase-2 exporters are present, their sidecar DPO files use the same
`mixed10k` suffix so they do not overwrite the default 5k/phase-2 artifacts.
The GQA/VG image downloader requests 4,300 target images with a 4,200-image
success threshold and `--workers 8` in this Slurm path; the script default
remains sequential for smaller/manual uses.

## Smoke and fallback options

For the 2k smoke version, change the COCO/GQA limits to `1500` and `500`, and
use `--version smoke`.

If GQA processing is not ready, generate enough COCO pairs and merge with:

```bash
python scripts/data/03_merge_and_split_pairs.py \
  --version main \
  --coco data/processed/canonical_coco_main.jsonl \
  --gqa data/processed/canonical_gqa_main.jsonl \
  --fallback-coco-only \
  --write-default \
  --seed 42
```
