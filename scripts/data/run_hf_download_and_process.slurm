#!/bin/bash
#SBATCH --job-name=cvpr_hf_data
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/hf_data.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/hf_data.%j.err

set -xeuo pipefail

cd /home/fhshao/CVPR-submission

unset http_proxy
unset https_proxy
unset all_proxy
echo "proxy-check: ${http_proxy-} ${https_proxy-} ${all_proxy-}"

export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/home/fhshao/CVPR-submission/.cache/hf
export HF_HUB_ENABLE_HF_TRANSFER=0
PYTHON_BIN=/home/fhshao/miniconda3/envs/perl/bin/python

mkdir -p logs data/raw data/processed data/audit "$HF_HOME"

"$PYTHON_BIN" -c "import datasets, huggingface_hub, PIL, pyarrow; print('deps-ok', datasets.__version__, huggingface_hub.__version__)"

"$PYTHON_BIN" scripts/data/00_download_hf_raw_subset.py \
  --coco-images 8000 \
  --gqa-images 4000 \
  --max-scan 60000 \
  --seed 42 \
  --allow-empty-gqa

"$PYTHON_BIN" scripts/data/01_build_coco_object_pairs.py \
  --instances data/raw/coco/annotations/instances_train2017.json \
  --image-root data/raw/coco/train2017 \
  --output data/processed/canonical_coco_main.jsonl \
  --limit 5000 \
  --seed 42

if [ -s data/raw/gqa/train_sceneGraphs.json ]; then
  "$PYTHON_BIN" scripts/data/02_build_gqa_simple_pairs.py \
    --scene-graphs data/raw/gqa/train_sceneGraphs.json \
    --image-root data/raw/gqa/images \
    --output data/processed/canonical_gqa_main.jsonl \
    --limit 1500 \
    --seed 42
else
  : > data/processed/canonical_gqa_main.jsonl
fi

"$PYTHON_BIN" scripts/data/03_merge_and_split_pairs.py \
  --version main \
  --coco data/processed/canonical_coco_main.jsonl \
  --gqa data/processed/canonical_gqa_main.jsonl \
  --fallback-coco-only \
  --write-default \
  --seed 42

"$PYTHON_BIN" scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-output data/processed/answer_dpo_train.jsonl \
  --evidence-output data/processed/evidence_hint_dpo_train.jsonl

"$PYTHON_BIN" scripts/data/05_make_audit_sheet.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --output data/audit/audit_200.csv \
  --sample-size 200 \
  --seed 42

"$PYTHON_BIN" scripts/data/06_check_data_leakage.py \
  --canonical data/processed/canonical_pairs_main.jsonl \
  --answer-dpo data/processed/answer_dpo_train.jsonl \
  --evidence-dpo data/processed/evidence_hint_dpo_train.jsonl \
  --report data/processed/check_report_main.json

wc -l \
  data/processed/canonical_pairs_main.jsonl \
  data/processed/answer_dpo_train.jsonl \
  data/processed/evidence_hint_dpo_train.jsonl \
  data/audit/audit_200.csv
