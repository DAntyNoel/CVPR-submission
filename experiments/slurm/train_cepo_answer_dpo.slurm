#!/bin/bash
#SBATCH --job-name=cvpr_cepo_ans
#SBATCH --partition=A100,RTX4090,ADA6000,L40S
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:4
#SBATCH --mem=160G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/train_cepo_answer_dpo.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/train_cepo_answer_dpo.%j.err

set -xeuo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python
OUTPUT_DIR="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2"

cd "${ROOT}"
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME="${ROOT}/.cache/hf"
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID:-cvpr_cepo_ans}
export PYTHONPATH="${ROOT}/LLaMA-Factory/src:${ROOT}/scripts/data"
export PATH=/home/fhshao/miniconda3/envs/verl0.6/bin:$PATH
export FORCE_TORCHRUN=1
mkdir -p "${TRITON_CACHE_DIR}" "${ROOT}/logs"

if [[ -d "${OUTPUT_DIR}" && "${ALLOW_OVERWRITE:-0}" != "1" ]]; then
  echo "Refusing to overwrite ${OUTPUT_DIR}; set ALLOW_OVERWRITE=1 to rerun." >&2
  exit 2
fi

"${PY}" "${ROOT}/scripts/data/13_check_cepo_data.py"
test -f "${ROOT}/experiments/llamafactory_data_cepo/dataset_info.json"
test -f "${ROOT}/experiments/llamafactory_data_cepo/cvpr_cepo_answer_dpo.json"

cd "${ROOT}/LLaMA-Factory"
"${PY}" -m llamafactory.cli train \
  "${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_answer_dpo.yaml"

test -f "${OUTPUT_DIR}/adapter_config.json"
test -f "${OUTPUT_DIR}/adapter_model.safetensors"
