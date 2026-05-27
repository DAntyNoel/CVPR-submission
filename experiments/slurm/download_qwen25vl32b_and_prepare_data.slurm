#!/bin/bash
#SBATCH --job-name=qwen25vl32b_prep
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/qwen25vl32b_prep.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/qwen25vl32b_prep.%j.err

set -xeuo pipefail

cd /home/fhshao/CVPR-submission
unset http_proxy
unset https_proxy
unset all_proxy
test -z "${http_proxy-}${https_proxy-}${all_proxy-}"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/home/fhshao/CVPR-submission/.cache/hf

DOWNLOAD_PYTHON=/home/fhshao/miniconda3/envs/perl/bin/python
VERIFY_PYTHON=/home/fhshao/miniconda3/envs/verl0.6/bin/python
MODEL_ID=Qwen/Qwen2.5-VL-32B-Instruct
MODEL_DIR=/home/fhshao/CVPR-submission/models/Qwen2.5-VL-32B-Instruct
PUBLIC_DIRECT=/data1/public/hf/Qwen/Qwen2.5-VL-32B-Instruct
PUBLIC_CACHE=/data1/public/hf/models--Qwen--Qwen2.5-VL-32B-Instruct

mkdir -p models logs "$HF_HOME" data/processed/qwen25vl32b

if [ -d "$PUBLIC_DIRECT" ]; then
  ln -sfn "$PUBLIC_DIRECT" "$MODEL_DIR"
elif [ -d "$PUBLIC_CACHE/snapshots" ]; then
  PUBLIC_SNAPSHOT="$(find "$PUBLIC_CACHE/snapshots" -mindepth 1 -maxdepth 1 -type d | sort | tail -n 1)"
  test -n "$PUBLIC_SNAPSHOT"
  ln -sfn "$PUBLIC_SNAPSHOT" "$MODEL_DIR"
else
  "$DOWNLOAD_PYTHON" -m huggingface_hub.commands.huggingface_cli download \
    "$MODEL_ID" \
    --local-dir "$MODEL_DIR" \
    --local-dir-use-symlinks False
fi

"$VERIFY_PYTHON" - "$MODEL_DIR" <<'PY'
import json
import sys
from pathlib import Path

from transformers import AutoConfig, AutoProcessor

model_dir = Path(sys.argv[1])
required_files = [
    "config.json",
    "preprocessor_config.json",
    "tokenizer_config.json",
]
missing = [name for name in required_files if not (model_dir / name).exists()]
if missing:
    raise SystemExit(f"missing required model files: {missing}")

config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
architectures = config.get("architectures", [])
if "Qwen2_5_VLForConditionalGeneration" not in architectures:
    raise SystemExit(f"unexpected architectures: {architectures}")

index_path = model_dir / "model.safetensors.index.json"
single_weight = model_dir / "model.safetensors"
if index_path.exists():
    index = json.loads(index_path.read_text(encoding="utf-8"))
    weight_files = sorted(set(index.get("weight_map", {}).values()))
    missing_weights = [name for name in weight_files if not (model_dir / name).exists()]
    if missing_weights:
        raise SystemExit(f"missing sharded weight files: {missing_weights[:5]}")
elif not single_weight.exists():
    raise SystemExit("missing model.safetensors or model.safetensors.index.json")

safetensors = list(model_dir.glob("*.safetensors"))
total_gb = sum(path.stat().st_size for path in safetensors) / 1e9
if total_gb < 40:
    raise SystemExit(f"safetensors payload looks too small: {total_gb:.2f} GB")

AutoConfig.from_pretrained(model_dir, trust_remote_code=True)
AutoProcessor.from_pretrained(model_dir, trust_remote_code=True)
print(f"Verified {model_dir}: {len(safetensors)} safetensors files, {total_gb:.2f} GB")
PY

"$DOWNLOAD_PYTHON" scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-output data/processed/qwen25vl32b/answer_dpo_train.jsonl \
  --evidence-output data/processed/qwen25vl32b/evidence_hint_dpo_train.jsonl \
  --answer-evidence-mix-output data/processed/qwen25vl32b/answer_evidence_mix_dpo_train.jsonl \
  --evidence-only-output data/processed/qwen25vl32b/phase2_evidence_only_dpo_train.jsonl \
  --input-side-evidence-output data/processed/qwen25vl32b/phase2_input_side_evidence_dpo_train.jsonl \
  --chosen-only-evidence-output data/processed/qwen25vl32b/phase2_chosen_only_evidence_dpo_train.jsonl

"$DOWNLOAD_PYTHON" scripts/experiments/prepare_llamafactory_data.py \
  --answer-input data/processed/qwen25vl32b/answer_dpo_train.jsonl \
  --evidence-input data/processed/qwen25vl32b/evidence_hint_dpo_train.jsonl \
  --answer-evidence-mix-input data/processed/qwen25vl32b/answer_evidence_mix_dpo_train.jsonl \
  --phase2-evidence-only-input data/processed/qwen25vl32b/phase2_evidence_only_dpo_train.jsonl \
  --phase2-input-side-evidence-input data/processed/qwen25vl32b/phase2_input_side_evidence_dpo_train.jsonl \
  --phase2-chosen-only-evidence-input data/processed/qwen25vl32b/phase2_chosen_only_evidence_dpo_train.jsonl \
  --output-dir experiments/llamafactory_data_qwen25vl32b

"$DOWNLOAD_PYTHON" v1/tasks/input-side-evidence-main-method/build_input_side_main_balanced_hard_dpo.py \
  --canonical /home/fhshao/CVPR-submission/data/processed/canonical_pairs_main.jsonl \
  --hard-eval /home/fhshao/CVPR-submission/data/eval/coco_hard_object_existence.jsonl \
  --base-error-mined /home/fhshao/CVPR-submission/data/eval/base_error_mined_object_existence.jsonl \
  --output /home/fhshao/CVPR-submission/data/processed/qwen25vl32b/input_side_main_balanced_hard_dpo_train.jsonl \
  --summary-output /home/fhshao/CVPR-submission/data/processed/qwen25vl32b/input_side_main_balanced_hard_dpo_summary.json \
  --llamafactory-dir /home/fhshao/CVPR-submission/experiments/llamafactory_data_input_side_main_qwen25vl32b \
  --dataset-key cvpr_input_side_main_balanced_hard_dpo_qwen25vl32b

test -f experiments/llamafactory_data_qwen25vl32b/dataset_info.json
test -f experiments/llamafactory_data_input_side_main_qwen25vl32b/dataset_info.json
