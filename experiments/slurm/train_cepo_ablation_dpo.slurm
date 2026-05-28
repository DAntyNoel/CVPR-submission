#!/bin/bash
#SBATCH --job-name=cvpr_cepo_ablate
#SBATCH --partition=A100,RTX4090,ADA6000,L40S
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:4
#SBATCH --mem=160G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/train_cepo_ablation_dpo.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/train_cepo_ablation_dpo.%j.err

set -xeuo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python
VARIANT="${VARIANT:-evidence_only_2k}"
SEED="${SEED:-42}"

case "${VARIANT}" in
  evidence_only_2k)
    ANSWER_COUNT="${ANSWER_COUNT:-0}"
    SUPPORTED_COUNT="${SUPPORTED_COUNT:-1000}"
    WRONG_COUNT="${WRONG_COUNT:-1000}"
    CONFIG="${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_evidence_only_dpo.yaml"
    DATA_DIR="${ROOT}/data/processed/cepo_dual_ablation/evidence_only_2k"
    LF_DIR="${ROOT}/experiments/llamafactory_data_cepo_dual_ablation/evidence_only_2k"
    OUTPUT_DIR="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_evidence_only_dpo_zero2"
    ;;
  dual500)
    ANSWER_COUNT="${ANSWER_COUNT:-6000}"
    SUPPORTED_COUNT="${SUPPORTED_COUNT:-250}"
    WRONG_COUNT="${WRONG_COUNT:-250}"
    CONFIG="${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_dual500_dpo.yaml"
    DATA_DIR="${ROOT}/data/processed/cepo_dual_ablation/dual500"
    LF_DIR="${ROOT}/experiments/llamafactory_data_cepo_dual_ablation/dual500"
    OUTPUT_DIR="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_dual500_dpo_zero2"
    ;;
  dual1k)
    ANSWER_COUNT="${ANSWER_COUNT:-6000}"
    SUPPORTED_COUNT="${SUPPORTED_COUNT:-500}"
    WRONG_COUNT="${WRONG_COUNT:-500}"
    CONFIG="${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_dual1k_dpo.yaml"
    DATA_DIR="${ROOT}/data/processed/cepo_dual_ablation/dual1k"
    LF_DIR="${ROOT}/experiments/llamafactory_data_cepo_dual_ablation/dual1k"
    OUTPUT_DIR="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_dual1k_dpo_zero2"
    ;;
  *)
    echo "Unknown CEPO ablation variant: ${VARIANT}" >&2
    exit 2
    ;;
esac

cd "${ROOT}"
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME="${ROOT}/.cache/hf"
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID:-cvpr_cepo_ablation}
export PYTHONPATH="${ROOT}/LLaMA-Factory/src:${ROOT}/scripts/data"
export PATH=/home/fhshao/miniconda3/envs/verl0.6/bin:$PATH
export FORCE_TORCHRUN=1
mkdir -p "${TRITON_CACHE_DIR}" "${ROOT}/logs"

if [[ -d "${OUTPUT_DIR}" && "${ALLOW_OVERWRITE:-0}" != "1" ]]; then
  echo "Refusing to overwrite ${OUTPUT_DIR}; set ALLOW_OVERWRITE=1 to rerun." >&2
  exit 2
fi

"${PY}" "${ROOT}/scripts/data/13_check_cepo_data.py"
"${PY}" "${ROOT}/scripts/data/14_export_cepo_dual_dpo.py" \
  --output-dir "${DATA_DIR}" \
  --answer-count "${ANSWER_COUNT}" \
  --supported-verifier-count "${SUPPORTED_COUNT}" \
  --wrong-evidence-verifier-count "${WRONG_COUNT}" \
  --seed "${SEED}"
"${PY}" "${ROOT}/scripts/experiments/prepare_llamafactory_data_cepo_dual.py" \
  --dual-input "${DATA_DIR}/cepo_dual_dpo_train.jsonl" \
  --output-dir "${LF_DIR}"
test -f "${LF_DIR}/dataset_info.json"
test -f "${LF_DIR}/cvpr_cepo_dual_dpo.json"

cd "${ROOT}/LLaMA-Factory"
"${PY}" -m llamafactory.cli train "${CONFIG}"

test -f "${OUTPUT_DIR}/adapter_config.json"
test -f "${OUTPUT_DIR}/adapter_model.safetensors"
