#!/usr/bin/env bash
# Submit V3 seed-stability CEPO training and dependent evaluation jobs.

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

submit_object_eval() {
  local dependency="$1"
  local model_key="$2"
  local adapter_path="$3"
  local seed="$4"
  local eval_jsonl="$5"
  local eval_name short_name output_variant

  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  output_variant="cepo_seed_stability/seed${seed}"
  short_name="seed${seed}_${model_key:5:4}_${eval_name:0:8}"
  submit_and_strip_cluster \
    --job-name="${short_name}" \
    --dependency=afterok:${dependency} \
    --export=ALL,MODEL_KEY="${model_key}",ADAPTER_NAME_OR_PATH="${adapter_path}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${output_variant}" \
    experiments/slurm/eval_vlm_object_hallucination.slurm
}

submit_probe_eval() {
  local dependency="$1"
  local model_key="$2"
  local adapter_path="$3"
  local seed="$4"
  local eval_jsonl="$5"
  local eval_name short_name output_variant

  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  output_variant="cepo_seed_stability/seed${seed}"
  short_name="seed${seed}_${model_key:5:4}_probe_${eval_name:0:8}"
  submit_and_strip_cluster \
    --job-name="${short_name}" \
    --dependency=afterok:${dependency} \
    --export=ALL,MODEL_KEY="${model_key}",ADAPTER_NAME_OR_PATH="${adapter_path}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${output_variant}" \
    experiments/slurm/eval_cepo_evidence_probe.slurm
}

"${PY}" scripts/data/13_check_cepo_data.py
test -f experiments/llamafactory_data_cepo/dataset_info.json
test -f experiments/llamafactory_data_cepo/cvpr_cepo_answer_dpo.json
test -f experiments/llamafactory_data_cepo_dual/dataset_info.json
test -f experiments/llamafactory_data_cepo_dual/cvpr_cepo_dual_dpo.json
test -f data/eval/cepo_evidence_probe.jsonl
test -f data/eval/cepo_wrong_evidence_probe.jsonl
test -f data/eval/base_error_mined_object_existence.jsonl

internal_evals=(
  data/eval/coco_heldout_object_existence.jsonl
  data/eval/gqa_simple_heldout.jsonl
  data/eval/coco_hard_object_existence.jsonl
  data/eval/base_error_mined_object_existence.jsonl
)
probe_evals=(
  data/eval/cepo_evidence_probe.jsonl
  data/eval/cepo_wrong_evidence_probe.jsonl
)

declare -a train_jobs=()
declare -a eval_jobs=()
answer_train_dependency=""
dual_train_dependency=""

for seed in 13 97; do
  answer_output="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_seed${seed}_zero2"
  answer_config="${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_answer_dpo_seed${seed}.yaml"
  answer_args=(--job-name="cepo_ans_s${seed}")
  if [[ -n "${answer_train_dependency}" ]]; then
    answer_args+=(--dependency=afterok:${answer_train_dependency})
  fi
  answer_job="$(submit_and_strip_cluster \
    "${answer_args[@]}" \
    --export=ALL,CONFIG_PATH="${answer_config}",OUTPUT_DIR="${answer_output}",DATASET_DIR="${ROOT}/experiments/llamafactory_data_cepo",DATASET_FILE="cvpr_cepo_answer_dpo.json" \
    experiments/slurm/train_cepo_seed_stability_dpo.slurm)"
  answer_train_dependency="${answer_job}"
  train_jobs+=("answer_seed${seed}=${answer_job}")

  for eval_jsonl in "${internal_evals[@]}"; do
    eval_jobs+=("$(submit_object_eval "${answer_job}" cepo_answer_dpo "${answer_output}" "${seed}" "${eval_jsonl}")")
  done
  for eval_jsonl in "${probe_evals[@]}"; do
    eval_jobs+=("$(submit_probe_eval "${answer_job}" cepo_answer_dpo "${answer_output}" "${seed}" "${eval_jsonl}")")
  done

  dual_output="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_seed${seed}_zero2"
  dual_config="${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_dual_dpo_seed${seed}.yaml"
  dual_args=(--job-name="cepo_dual_s${seed}")
  if [[ -n "${dual_train_dependency}" ]]; then
    dual_args+=(--dependency=afterok:${dual_train_dependency})
  fi
  dual_job="$(submit_and_strip_cluster \
    "${dual_args[@]}" \
    --export=ALL,CONFIG_PATH="${dual_config}",OUTPUT_DIR="${dual_output}",DATASET_DIR="${ROOT}/experiments/llamafactory_data_cepo_dual",DATASET_FILE="cvpr_cepo_dual_dpo.json" \
    experiments/slurm/train_cepo_seed_stability_dpo.slurm)"
  dual_train_dependency="${dual_job}"
  train_jobs+=("dual_seed${seed}=${dual_job}")

  for eval_jsonl in "${internal_evals[@]}"; do
    eval_jobs+=("$(submit_object_eval "${dual_job}" cepo_dual_dpo "${dual_output}" "${seed}" "${eval_jsonl}")")
  done
  for eval_jsonl in "${probe_evals[@]}"; do
    eval_jobs+=("$(submit_probe_eval "${dual_job}" cepo_dual_dpo "${dual_output}" "${seed}" "${eval_jsonl}")")
  done
done

cat <<EOF
Submitted CEPO seed-stability pipeline:
  train_jobs=${train_jobs[*]}
  eval_jobs=${eval_jobs[*]}

Outputs:
  adapters: outputs/llamafactory/qwen25vl7b_cepo_{answer,dual}_dpo_seed{13,97}_zero2/
  evals: results/eval/generations/<eval>/cepo_seed_stability/seed{13,97}/<model_key>.jsonl
EOF
