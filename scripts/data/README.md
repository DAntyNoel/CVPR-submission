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
  --evidence-output data/processed/evidence_hint_dpo_train.jsonl

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
