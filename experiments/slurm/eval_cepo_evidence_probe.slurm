#!/bin/bash
#SBATCH --job-name=cvpr_cepo_probe
#SBATCH --partition=A100,RTX4090,ADA6000,L40S
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --mem=80G
#SBATCH --time=08:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/eval_cepo_evidence_probe.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/eval_cepo_evidence_probe.%j.err

set -xeuo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python

MODEL_KEY="${MODEL_KEY:-base}"
MODEL_NAME_OR_PATH="${MODEL_NAME_OR_PATH:-models/Qwen2.5-VL-7B-Instruct}"
EVAL_JSONL="${EVAL_JSONL:-${ROOT}/data/eval/cepo_evidence_probe.jsonl}"
ADAPTER_NAME_OR_PATH="${ADAPTER_NAME_OR_PATH:-}"
MAX_SAMPLES="${MAX_SAMPLES:-}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-96}"
IMAGE_MIN_PIXELS="${IMAGE_MIN_PIXELS:-}"
IMAGE_MAX_PIXELS="${IMAGE_MAX_PIXELS:-}"
OUTPUT_VARIANT="${OUTPUT_VARIANT:-cepo_evidence_probe}"
INSTRUCTION_SUFFIX="${INSTRUCTION_SUFFIX:-Return JSON with answer, claim, evidence_label, support. Use support as supported, contradicted, or wrong_evidence.}"

cd "${ROOT}"
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME="${ROOT}/.cache/hf"
export PYTHONPATH="${ROOT}/LLaMA-Factory/src:${ROOT}/scripts/eval"
export PATH=/home/fhshao/miniconda3/envs/verl0.6/bin:$PATH
mkdir -p "${ROOT}/logs"

EVAL_NAME="$(basename "${EVAL_JSONL}" .jsonl)"
OUTPUT_DIR="${ROOT}/results/eval/generations/${EVAL_NAME}/${OUTPUT_VARIANT}"
OUTPUT="${OUTPUT_DIR}/${MODEL_KEY}.jsonl"
mkdir -p "${OUTPUT_DIR}"

ARGS=(
  "${ROOT}/scripts/eval/run_vlm_inference.py"
  --model-key "${MODEL_KEY}"
  --model-name-or-path "${MODEL_NAME_OR_PATH}"
  --eval "${EVAL_JSONL}"
  --output "${OUTPUT}"
  --max-new-tokens "${MAX_NEW_TOKENS}"
  --instruction-suffix "${INSTRUCTION_SUFFIX}"
)

if [[ -n "${MAX_SAMPLES}" ]]; then
  ARGS+=(--max-samples "${MAX_SAMPLES}")
fi

if [[ -n "${IMAGE_MIN_PIXELS}" ]]; then
  ARGS+=(--image-min-pixels "${IMAGE_MIN_PIXELS}")
fi

if [[ -n "${IMAGE_MAX_PIXELS}" ]]; then
  ARGS+=(--image-max-pixels "${IMAGE_MAX_PIXELS}")
fi

if [[ -n "${ADAPTER_NAME_OR_PATH}" ]]; then
  ARGS+=(--adapter-name-or-path "${ADAPTER_NAME_OR_PATH}")
fi

"${PY}" "${ARGS[@]}"
"${PY}" "${ROOT}/scripts/eval/score_cepo_evidence_probe.py" --input "${OUTPUT}"
