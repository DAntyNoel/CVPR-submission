#!/bin/bash
#SBATCH --job-name=cvpr_32b_cepo
#SBATCH --partition=RTX4090
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:4
#SBATCH --mem=320G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/train_qwen25vl32b_cepo_dpo.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/train_qwen25vl32b_cepo_dpo.%j.err

set -xeuo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python

CONFIG_PATH="${CONFIG_PATH:?CONFIG_PATH is required}"
OUTPUT_DIR="${OUTPUT_DIR:?OUTPUT_DIR is required}"
DATASET_DIR="${DATASET_DIR:?DATASET_DIR is required}"
DATASET_FILE="${DATASET_FILE:?DATASET_FILE is required}"
EXPECT_ADAPTER="${EXPECT_ADAPTER:-1}"

cd "${ROOT}"
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME="${ROOT}/.cache/hf"
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID:-cvpr_32b_cepo}
export PYTHONPATH="${ROOT}/LLaMA-Factory/src:${ROOT}/scripts/data"
export PATH=/home/fhshao/miniconda3/envs/verl0.6/bin:$PATH
export FORCE_TORCHRUN=1
mkdir -p "${TRITON_CACHE_DIR}" "${ROOT}/logs"

echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"
echo "SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-}"
echo "SLURM_GPUS=${SLURM_GPUS:-}"
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}"
echo "CONFIG_PATH=${CONFIG_PATH}"
echo "OUTPUT_DIR=${OUTPUT_DIR}"

if [[ -d "${OUTPUT_DIR}" && "${ALLOW_OVERWRITE:-0}" != "1" ]]; then
  echo "Refusing to overwrite ${OUTPUT_DIR}; set ALLOW_OVERWRITE=1 to rerun." >&2
  exit 2
fi

"${PY}" "${ROOT}/scripts/data/13_check_cepo_data.py"
test -f "${CONFIG_PATH}"
test -f "${DATASET_DIR}/dataset_info.json"
test -f "${DATASET_DIR}/${DATASET_FILE}"
test -d "${ROOT}/models/Qwen2.5-VL-32B-Instruct"
test -f "${ROOT}/models/Qwen2.5-VL-32B-Instruct/config.json"

cd "${ROOT}/LLaMA-Factory"
"${PY}" -m llamafactory.cli train "${CONFIG_PATH}"

if [[ "${EXPECT_ADAPTER}" == "1" ]]; then
  test -f "${OUTPUT_DIR}/adapter_config.json"
  test -f "${OUTPUT_DIR}/adapter_model.safetensors"
fi
