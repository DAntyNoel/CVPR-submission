#!/bin/bash
#SBATCH --job-name=cvpr_gqa_data
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/gqa_data.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/gqa_data.%j.err

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
SCENE_GRAPHS_URL="${GQA_SCENE_GRAPHS_URL:-https://downloads.cs.stanford.edu/nlp/data/gqa/sceneGraphs.zip}"
SCENE_GRAPHS_ZIP=data/raw/gqa/sceneGraphs.zip

mkdir -p logs data/raw/gqa/images data/processed "$HF_HOME"

"$PYTHON_BIN" -c "import datasets, huggingface_hub, PIL, pyarrow; print('deps-ok', datasets.__version__, huggingface_hub.__version__)"

if [ ! -s data/raw/gqa/train_sceneGraphs.json ]; then
  if [ ! -s "$SCENE_GRAPHS_ZIP" ]; then
    curl -L --fail --retry 8 --retry-delay 10 \
      -o "${SCENE_GRAPHS_ZIP}.tmp" \
      "$SCENE_GRAPHS_URL"
    mv "${SCENE_GRAPHS_ZIP}.tmp" "$SCENE_GRAPHS_ZIP"
  fi
  unzip -o "$SCENE_GRAPHS_ZIP" -d data/raw/gqa
  if [ ! -s data/raw/gqa/train_sceneGraphs.json ]; then
    FOUND_SCENE_GRAPH="$(find data/raw/gqa -type f -name train_sceneGraphs.json | head -n 1)"
    test -n "$FOUND_SCENE_GRAPH"
    ln -sf "$(readlink -f "$FOUND_SCENE_GRAPH")" data/raw/gqa/train_sceneGraphs.json
  fi
fi

test -s data/raw/gqa/train_sceneGraphs.json

"$PYTHON_BIN" scripts/data/02_build_gqa_simple_pairs.py \
  --scene-graphs data/raw/gqa/train_sceneGraphs.json \
  --image-root data/raw/gqa/images \
  --output data/processed/canonical_gqa_candidates.jsonl \
  --limit 5000 \
  --seed 42 \
  --allow-missing-images

"$PYTHON_BIN" scripts/data/10_download_gqa_vg_images.py \
  --input data/processed/canonical_gqa_candidates.jsonl \
  --image-root data/raw/gqa/images \
  --manifest data/raw/gqa/image_download_manifest.json \
  --limit-images 2500 \
  --min-success 1000

"$PYTHON_BIN" scripts/data/02_build_gqa_simple_pairs.py \
  --scene-graphs data/raw/gqa/train_sceneGraphs.json \
  --image-root data/raw/gqa/images \
  --output data/processed/canonical_gqa_main.jsonl \
  --limit 1500 \
  --seed 42

GQA_LINES="$(wc -l < data/processed/canonical_gqa_main.jsonl)"
test "$GQA_LINES" -ge 1500

"$PYTHON_BIN" scripts/data/03_merge_and_split_pairs.py \
  --version main \
  --coco data/processed/canonical_coco_main.jsonl \
  --gqa data/processed/canonical_gqa_main.jsonl \
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
  --eval-image-ids data/eval/heldout_object_existence_image_ids.txt \
  --report data/processed/check_report_main.json

wc -l \
  data/processed/canonical_gqa_candidates.jsonl \
  data/processed/canonical_gqa_main.jsonl \
  data/processed/canonical_pairs_main.jsonl \
  data/processed/answer_dpo_train.jsonl \
  data/processed/evidence_hint_dpo_train.jsonl \
  data/audit/audit_200.csv
