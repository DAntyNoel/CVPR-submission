#!/usr/bin/env bash
# Submit CEPO-Dual verifier-count ablations and their internal/probe evals.

set -euo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python

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

submit_eval() {
  local model_key="$1"
  local eval_jsonl="$2"
  local output_variant="$3"
  local short_name="$4"
  local dependency="$5"
  local adapter_path="$6"
  submit_and_strip_cluster \
    --job-name="${short_name}" \
    --dependency=afterok:${dependency} \
    --export=ALL,MODEL_KEY="${model_key}",ADAPTER_NAME_OR_PATH="${adapter_path}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${output_variant}" \
    experiments/slurm/eval_vlm_object_hallucination.slurm
}

submit_probe_eval() {
  local model_key="$1"
  local eval_jsonl="$2"
  local output_variant="$3"
  local short_name="$4"
  local dependency="$5"
  local adapter_path="$6"
  submit_and_strip_cluster \
    --job-name="${short_name}" \
    --dependency=afterok:${dependency} \
    --export=ALL,MODEL_KEY="${model_key}",ADAPTER_NAME_OR_PATH="${adapter_path}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${output_variant}" \
    experiments/slurm/eval_cepo_evidence_probe.slurm
}

"${PY}" scripts/data/13_check_cepo_data.py
test -f data/eval/cepo_evidence_probe.jsonl
test -f data/eval/cepo_wrong_evidence_probe.jsonl
test -f outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2/adapter_model.safetensors
test -f outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2/adapter_model.safetensors

variants=(evidence_only_2k dual500 dual1k)
model_keys=(cepo_evidence_only_dpo cepo_dual500_dpo cepo_dual1k_dpo)
adapter_paths=(
  "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_evidence_only_dpo_zero2"
  "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_dual500_dpo_zero2"
  "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_dual1k_dpo_zero2"
)

internal_evals=(
  data/eval/coco_heldout_object_existence.jsonl
  data/eval/gqa_simple_heldout.jsonl
  data/eval/coco_hard_object_existence.jsonl
)
probe_evals=(
  data/eval/cepo_evidence_probe.jsonl
  data/eval/cepo_wrong_evidence_probe.jsonl
)

declare -a train_jobs=()
declare -a eval_jobs=()

for i in "${!variants[@]}"; do
  variant="${variants[$i]}"
  model_key="${model_keys[$i]}"
  adapter_path="${adapter_paths[$i]}"
  output_variant="cepo_dual_ablation/${variant}"

  train_job="$(submit_and_strip_cluster \
    --job-name="cepo_${variant}" \
    --export=ALL,VARIANT="${variant}" \
    experiments/slurm/train_cepo_ablation_dpo.slurm)"
  train_jobs+=("${variant}=${train_job}")

  for eval_jsonl in "${internal_evals[@]}"; do
    eval_name="$(basename "${eval_jsonl}" .jsonl)"
    eval_jobs+=("$(submit_eval "${model_key}" "${eval_jsonl}" "${output_variant}" "abl_${variant:0:6}_${eval_name:0:8}" "${train_job}" "${adapter_path}")")
  done

  for eval_jsonl in "${probe_evals[@]}"; do
    eval_name="$(basename "${eval_jsonl}" .jsonl)"
    eval_jobs+=("$(submit_probe_eval "${model_key}" "${eval_jsonl}" "${output_variant}" "ablp_${variant:0:6}_${eval_name:0:8}" "${train_job}" "${adapter_path}")")
  done
done

cat <<EOF
Submitted CEPO verifier-count ablation pipeline:
  train_jobs=${train_jobs[*]}
  eval_jobs=${eval_jobs[*]}

Outputs:
  adapters: outputs/llamafactory/qwen25vl7b_cepo_{evidence_only,dual500,dual1k}_dpo_zero2/
  evals: results/eval/generations/<eval>/cepo_dual_ablation/<variant>/<model_key>.jsonl
EOF
