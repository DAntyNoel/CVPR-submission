#!/usr/bin/env bash
# Submit the CEPO paraphrased-probe evaluation matrix.

set -euo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python
SUPPORTED="${SUPPORTED:-${ROOT}/data/eval/cepo_evidence_probe_paraphrase.jsonl}"
WRONG="${WRONG:-${ROOT}/data/eval/cepo_wrong_evidence_probe_paraphrase.jsonl}"
OUTPUT_VARIANT="${OUTPUT_VARIANT:-cepo_paraphrase_probe}"

cd "${ROOT}"
mkdir -p logs

submit_and_strip_cluster() {
  local raw
  if ! raw="$(sbatch --parsable "$@")"; then
    return 1
  fi
  raw="${raw%%;*}"
  if [[ -z "${raw}" ]]; then
    echo "sbatch returned an empty job id for: $*" >&2
    return 1
  fi
  echo "${raw}"
}

if [[ ! -f "${SUPPORTED}" || ! -f "${WRONG}" ]]; then
  "${PY}" scripts/eval/prepare_cepo_paraphrase_probe.py \
    --supported-output "${SUPPORTED}" \
    --wrong-output "${WRONG}"
fi
test -f "${SUPPORTED}"
test -f "${WRONG}"
test -f outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2/adapter_model.safetensors
test -f outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2/adapter_model.safetensors

declare -a eval_jobs=()

submit_probe_pair() {
  local model_key="$1"
  local adapter_path="$2"
  local short_name="$3"
  local export_args

  export_args="ALL,MODEL_KEY=${model_key},OUTPUT_VARIANT=${OUTPUT_VARIANT}"
  if [[ -n "${adapter_path}" ]]; then
    export_args="ALL,MODEL_KEY=${model_key},ADAPTER_NAME_OR_PATH=${adapter_path},OUTPUT_VARIANT=${OUTPUT_VARIANT}"
  fi

  eval_jobs+=("$(submit_and_strip_cluster \
    --job-name="para_${short_name}_sup" \
    --export="${export_args},EVAL_JSONL=${SUPPORTED}" \
    experiments/slurm/eval_cepo_evidence_probe.slurm)")
  eval_jobs+=("$(submit_and_strip_cluster \
    --job-name="para_${short_name}_wrong" \
    --export="${export_args},EVAL_JSONL=${WRONG}" \
    experiments/slurm/eval_cepo_evidence_probe.slurm)")
}

submit_probe_pair "base" "" "base"
submit_probe_pair "cepo_answer_dpo" "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2" "ans"
submit_probe_pair "cepo_dual_dpo" "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2" "dual"

cat <<EOF
Submitted CEPO paraphrased-probe eval:
  eval_jobs=${eval_jobs[*]}

Outputs:
  supported probe: ${SUPPORTED}
  wrong probe: ${WRONG}
  evals: results/eval/generations/{cepo_evidence_probe_paraphrase,cepo_wrong_evidence_probe_paraphrase}/${OUTPUT_VARIANT}/<model_key>.jsonl
EOF
