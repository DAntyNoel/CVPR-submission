#!/bin/bash
#SBATCH --job-name=cvpr_mix10k_data
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/mixed10k_data.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/mixed10k_data.%j.err

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

mkdir -p logs data/processed data/audit experiments/llamafactory_data_10k "$HF_HOME"

"$PYTHON_BIN" scripts/data/01_build_coco_object_pairs.py \
  --instances data/raw/coco/annotations/instances_train2017.json \
  --image-root data/raw/coco/train2017 \
  --output data/processed/canonical_coco_mixed10k.jsonl \
  --limit 6000 \
  --seed 42 \
  --exclude-image-ids data/eval/heldout_object_existence_image_ids.txt

"$PYTHON_BIN" scripts/data/02_build_gqa_simple_pairs.py \
  --scene-graphs data/raw/gqa/train_sceneGraphs.json \
  --image-root data/raw/gqa/images \
  --output data/processed/canonical_gqa_candidates_mixed10k.jsonl \
  --limit 8000 \
  --seed 42 \
  --allow-missing-images \
  --exclude-image-ids data/eval/gqa_simple_heldout.jsonl

"$PYTHON_BIN" scripts/data/10_download_gqa_vg_images.py \
  --input data/processed/canonical_gqa_candidates_mixed10k.jsonl \
  --image-root data/raw/gqa/images \
  --manifest data/raw/gqa/image_download_manifest_mixed10k.json \
  --limit-images 4300 \
  --min-success 4200 \
  --sleep 0.1 \
  --workers 8

"$PYTHON_BIN" scripts/data/02_build_gqa_simple_pairs.py \
  --scene-graphs data/raw/gqa/train_sceneGraphs.json \
  --image-root data/raw/gqa/images \
  --output data/processed/canonical_gqa_mixed10k.jsonl \
  --limit 4000 \
  --seed 42 \
  --exclude-image-ids data/eval/gqa_simple_heldout.jsonl

"$PYTHON_BIN" scripts/data/03_merge_and_split_pairs.py \
  --version expanded \
  --coco data/processed/canonical_coco_mixed10k.jsonl \
  --gqa data/processed/canonical_gqa_mixed10k.jsonl \
  --output data/processed/canonical_pairs_mixed10k.jsonl \
  --stats-output data/processed/stats_mixed10k.json \
  --seed 42 \
  --eval-image-ids \
    data/eval/heldout_object_existence_image_ids.txt \
    data/eval/gqa_simple_heldout.jsonl

"$PYTHON_BIN" scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_mixed10k.jsonl \
  --answer-output data/processed/answer_dpo_train_mixed10k.jsonl \
  --evidence-output data/processed/evidence_hint_dpo_train_mixed10k.jsonl \
  --evidence-only-output data/processed/phase2_evidence_only_dpo_train_mixed10k.jsonl \
  --input-side-evidence-output data/processed/phase2_input_side_evidence_dpo_train_mixed10k.jsonl \
  --chosen-only-evidence-output data/processed/phase2_chosen_only_evidence_dpo_train_mixed10k.jsonl

"$PYTHON_BIN" scripts/data/05_make_audit_sheet.py \
  --input data/processed/canonical_pairs_mixed10k.jsonl \
  --output data/audit/audit_mixed10k_200.csv \
  --sample-size 200 \
  --seed 42

"$PYTHON_BIN" scripts/data/08_complete_audit_sheet.py \
  --canonical data/processed/canonical_pairs_mixed10k.jsonl \
  --audit data/audit/audit_mixed10k_200.csv \
  --summary data/audit/audit_mixed10k_200_summary.json

"$PYTHON_BIN" scripts/data/06_check_data_leakage.py \
  --canonical data/processed/canonical_pairs_mixed10k.jsonl \
  --answer-dpo data/processed/answer_dpo_train_mixed10k.jsonl \
  --evidence-dpo data/processed/evidence_hint_dpo_train_mixed10k.jsonl \
  --eval-image-ids \
    data/eval/heldout_object_existence_image_ids.txt \
    data/eval/gqa_simple_heldout.jsonl \
  --report data/processed/check_report_mixed10k.json

"$PYTHON_BIN" scripts/experiments/prepare_llamafactory_data.py \
  --answer-input data/processed/answer_dpo_train_mixed10k.jsonl \
  --evidence-input data/processed/evidence_hint_dpo_train_mixed10k.jsonl \
  --phase2-evidence-only-input data/processed/phase2_evidence_only_dpo_train_mixed10k.jsonl \
  --phase2-input-side-evidence-input data/processed/phase2_input_side_evidence_dpo_train_mixed10k.jsonl \
  --phase2-chosen-only-evidence-input data/processed/phase2_chosen_only_evidence_dpo_train_mixed10k.jsonl \
  --output-dir experiments/llamafactory_data_10k

wc -l \
  data/processed/canonical_coco_mixed10k.jsonl \
  data/processed/canonical_gqa_mixed10k.jsonl \
  data/processed/canonical_pairs_mixed10k.jsonl \
  data/processed/answer_dpo_train_mixed10k.jsonl \
  data/processed/evidence_hint_dpo_train_mixed10k.jsonl \
  data/processed/phase2_evidence_only_dpo_train_mixed10k.jsonl \
  data/processed/phase2_input_side_evidence_dpo_train_mixed10k.jsonl \
  data/processed/phase2_chosen_only_evidence_dpo_train_mixed10k.jsonl \
  data/audit/audit_mixed10k_200.csv
