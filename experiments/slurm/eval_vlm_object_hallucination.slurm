#!/bin/bash
#SBATCH --job-name=cvpr_vlm_eval
#SBATCH --partition=A100,RTX4090,ADA6000,L40S
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=80G
#SBATCH --time=08:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/eval_vlm_object_hallucination.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/eval_vlm_object_hallucination.%j.err

set -xeuo pipefail

MODEL_KEY="${MODEL_KEY:-base}"
EVAL_JSONL="${EVAL_JSONL:-/home/fhshao/CVPR-submission/data/eval/coco_heldout_object_existence.jsonl}"
MAX_SAMPLES="${MAX_SAMPLES:-}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-32}"

cd /home/fhshao/CVPR-submission
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/home/fhshao/CVPR-submission/.cache/hf
export PYTHONPATH=/home/fhshao/CVPR-submission/LLaMA-Factory/src:/home/fhshao/CVPR-submission/scripts/eval
export PATH=/home/fhshao/miniconda3/envs/verl0.6/bin:$PATH

EVAL_NAME="$(basename "${EVAL_JSONL}" .jsonl)"
OUTPUT="/home/fhshao/CVPR-submission/results/eval/generations/${EVAL_NAME}/${MODEL_KEY}.jsonl"
mkdir -p "$(dirname "${OUTPUT}")"

ARGS=(
  /home/fhshao/CVPR-submission/scripts/eval/run_vlm_inference.py
  --model-key "${MODEL_KEY}"
  --eval "${EVAL_JSONL}"
  --output "${OUTPUT}"
  --max-new-tokens "${MAX_NEW_TOKENS}"
)

if [[ -n "${MAX_SAMPLES}" ]]; then
  ARGS+=(--max-samples "${MAX_SAMPLES}")
fi

/home/fhshao/miniconda3/envs/verl0.6/bin/python "${ARGS[@]}"
/home/fhshao/miniconda3/envs/verl0.6/bin/python \
  /home/fhshao/CVPR-submission/scripts/eval/score_object_eval.py \
  --input "${OUTPUT}"
