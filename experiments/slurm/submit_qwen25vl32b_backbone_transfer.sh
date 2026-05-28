#!/usr/bin/env bash
# Submit the Qwen2.5-VL-32B backbone-transfer smoke/full pipeline.

set -euo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python
MODE="${1:-${MODE:-smoke}}"
PROFILE="${PROFILE:-rtx4090_z2_4}"
SMOKE_TARGET="${SMOKE_TARGET:-answer}"
if [[ -z "${SHARDING:-}" ]]; then
  if [[ "${PROFILE}" == *_z3_* ]]; then
    SHARDING=zero3
  elif [[ "${PROFILE}" == *_qlora4_* ]]; then
    SHARDING=qlora4
  else
    SHARDING=zero2
  fi
fi
OUTPUT_VARIANT="${OUTPUT_VARIANT:-backbone_transfer/qwen25vl32b}"
MODEL_PATH="${MODEL_PATH:-${ROOT}/models/Qwen2.5-VL-32B-Instruct}"
SMOKE_TIME="${SMOKE_TIME:-02:00:00}"
TRAIN_TIME="${TRAIN_TIME:-1-20:00:00}"

cd "${ROOT}"
mkdir -p logs v2/tasks/backbone-transfer-experiments/results

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

profile_args() {
  local time_limit
  if [[ "${MODE}" == "smoke" ]]; then
    time_limit="${SMOKE_TIME}"
  else
    time_limit="${TRAIN_TIME}"
  fi
  case "${PROFILE}" in
    rtx4090_z2_4)
      echo "--partition=RTX4090 --gres=gpu:4 --mem=320G --time=${time_limit}"
      ;;
    rtx4090_z2_8)
      echo "--partition=RTX4090 --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    a100_z2_4)
      echo "--partition=A100 --gres=gpu:4 --mem=320G --time=${time_limit}"
      ;;
    l40s_z2_8)
      echo "--partition=L40S --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    ada6000_z2_8)
      echo "--partition=ADA6000 --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    rtx4090_qlora4_8)
      echo "--partition=RTX4090 --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    l40s_qlora4_8)
      echo "--partition=L40S --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    ada6000_qlora4_8)
      echo "--partition=ADA6000 --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    a100_qlora4_4)
      echo "--partition=A100 --gres=gpu:4 --mem=320G --time=${time_limit}"
      ;;
    l40s_z3_8)
      echo "--partition=L40S --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    ada6000_z3_8)
      echo "--partition=ADA6000 --gres=gpu:8 --mem=640G --time=${time_limit}"
      ;;
    a100_z3_4)
      echo "--partition=A100 --gres=gpu:4 --mem=320G --time=${time_limit}"
      ;;
    *)
      echo "Unknown PROFILE=${PROFILE}" >&2
      return 2
      ;;
  esac
}

eval_resource_args() {
  echo "--partition=${EVAL_PARTITION:-L40S,ADA6000,A100,RTX4090} --gres=gpu:${EVAL_GPUS:-4} --mem=${EVAL_MEM:-320G} --time=${EVAL_TIME:-12:00:00}"
}

shell_words_to_array() {
  local -n out_ref="$1"
  shift
  read -r -a out_ref <<< "$*"
}

submit_train() {
  local job_name="$1"
  local config="$2"
  local output="$3"
  local dataset_dir="$4"
  local dataset_file="$5"
  local expect_adapter="$6"
  local extra_export="$7"
  local resource_string
  local -a resources

  resource_string="$(profile_args)"
  shell_words_to_array resources "${resource_string}"
  submit_and_strip_cluster \
    --job-name="${job_name}" \
    "${resources[@]}" \
    --export=ALL,CONFIG_PATH="${config}",OUTPUT_DIR="${output}",DATASET_DIR="${dataset_dir}",DATASET_FILE="${dataset_file}",EXPECT_ADAPTER="${expect_adapter}",${extra_export} \
    experiments/slurm/train_qwen25vl32b_cepo_dpo.slurm
}

submit_object_eval() {
  local dependency="$1"
  local model_key="$2"
  local adapter_path="$3"
  local eval_jsonl="$4"
  local short_name eval_name
  local resource_string
  local -a resources dep_arg adapter_arg

  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  short_name="32b_${model_key:0:4}_${eval_name:0:8}"
  resource_string="$(eval_resource_args)"
  shell_words_to_array resources "${resource_string}"
  dep_arg=()
  if [[ -n "${dependency}" ]]; then
    dep_arg=(--dependency=afterok:${dependency})
  fi
  adapter_arg=()
  if [[ -n "${adapter_path}" ]]; then
    adapter_arg=(ADAPTER_NAME_OR_PATH="${adapter_path}")
  else
    adapter_arg=(ADAPTER_NAME_OR_PATH=none)
  fi
  submit_and_strip_cluster \
    --job-name="${short_name}" \
    "${resources[@]}" \
    "${dep_arg[@]}" \
    --export=ALL,MODEL_KEY="${model_key}",MODEL_NAME_OR_PATH="${MODEL_PATH}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${OUTPUT_VARIANT}","${adapter_arg[@]}" \
    experiments/slurm/eval_vlm_object_hallucination.slurm
}

submit_probe_eval() {
  local dependency="$1"
  local model_key="$2"
  local adapter_path="$3"
  local eval_jsonl="$4"
  local short_name eval_name
  local resource_string
  local -a resources dep_arg adapter_arg

  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  short_name="32b_${model_key:0:4}_probe_${eval_name:0:8}"
  resource_string="$(eval_resource_args)"
  shell_words_to_array resources "${resource_string}"
  dep_arg=()
  if [[ -n "${dependency}" ]]; then
    dep_arg=(--dependency=afterok:${dependency})
  fi
  adapter_arg=()
  if [[ -n "${adapter_path}" ]]; then
    adapter_arg=(ADAPTER_NAME_OR_PATH="${adapter_path}")
  else
    adapter_arg=(ADAPTER_NAME_OR_PATH=none)
  fi
  submit_and_strip_cluster \
    --job-name="${short_name}" \
    "${resources[@]}" \
    "${dep_arg[@]}" \
    --export=ALL,MODEL_KEY="${model_key}",MODEL_NAME_OR_PATH="${MODEL_PATH}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${OUTPUT_VARIANT}","${adapter_arg[@]}" \
    experiments/slurm/eval_cepo_evidence_probe.slurm
}

"${PY}" scripts/data/13_check_cepo_data.py
test -d "${MODEL_PATH}"
test -f experiments/llamafactory_data_cepo/dataset_info.json
test -f experiments/llamafactory_data_cepo/cvpr_cepo_answer_dpo.json
test -f experiments/llamafactory_data_cepo_dual/dataset_info.json
test -f experiments/llamafactory_data_cepo_dual/cvpr_cepo_dual_dpo.json
test -f data/eval/cepo_evidence_probe.jsonl
test -f data/eval/cepo_wrong_evidence_probe.jsonl
test -f v2/tasks/review-convergence-experiments/results/relation_stress/relation_stress_probe.jsonl

if [[ "${MODE}" == "smoke" ]]; then
  case "${SMOKE_TARGET}" in
    answer)
      smoke_config="${ROOT}/experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_answer_dpo_seed42_${SHARDING}.yaml"
      smoke_output="${ROOT}/outputs/llamafactory_smoke/qwen25vl32b_cepo_answer_dpo_seed42_${SHARDING}"
      smoke_dataset_dir="${ROOT}/experiments/llamafactory_data_cepo"
      smoke_dataset_file="cvpr_cepo_answer_dpo.json"
      ;;
    dual)
      smoke_config="${ROOT}/experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_dual_dpo_seed42_${SHARDING}.yaml"
      smoke_output="${ROOT}/outputs/llamafactory_smoke/qwen25vl32b_cepo_dual_dpo_seed42_${SHARDING}"
      smoke_dataset_dir="${ROOT}/experiments/llamafactory_data_cepo_dual"
      smoke_dataset_file="cvpr_cepo_dual_dpo.json"
      ;;
    *)
      echo "Unknown SMOKE_TARGET=${SMOKE_TARGET}; expected answer or dual" >&2
      exit 2
      ;;
  esac
  smoke_job="$(submit_train \
    "32b_${SMOKE_TARGET}_smoke_${PROFILE}" \
    "${smoke_config}" \
    "${smoke_output}" \
    "${smoke_dataset_dir}" \
    "${smoke_dataset_file}" \
    "0" \
    "ALLOW_OVERWRITE=1")"
  cat <<EOF
Submitted Qwen2.5-VL-32B smoke:
  profile=${PROFILE}
  sharding=${SHARDING}
  smoke_target=${SMOKE_TARGET}
  smoke_job=${smoke_job}
  output=${smoke_output}
EOF
  exit 0
fi

if [[ "${MODE}" != "full" ]]; then
  echo "Usage: PROFILE=<profile> $0 smoke|full" >&2
  exit 2
fi

internal_evals=(
  data/eval/coco_heldout_object_existence.jsonl
  data/eval/gqa_simple_heldout.jsonl
  data/eval/coco_hard_object_existence.jsonl
  data/eval/base_error_mined_object_existence.jsonl
)
probe_evals=(
  data/eval/cepo_evidence_probe.jsonl
  data/eval/cepo_wrong_evidence_probe.jsonl
  v2/tasks/review-convergence-experiments/results/relation_stress/relation_stress_probe.jsonl
)

declare -a train_jobs=()
declare -a eval_jobs=()

answer_output="${ROOT}/outputs/llamafactory/qwen25vl32b_cepo_answer_dpo_seed42_${SHARDING}"
dual_output="${ROOT}/outputs/llamafactory/qwen25vl32b_cepo_dual_dpo_seed42_${SHARDING}"

answer_job="$(submit_train \
  "32b_ans_s42" \
  "${ROOT}/experiments/llamafactory_configs/qwen25vl32b_cepo_answer_dpo_seed42_${SHARDING}.yaml" \
  "${answer_output}" \
  "${ROOT}/experiments/llamafactory_data_cepo" \
  "cvpr_cepo_answer_dpo.json" \
  "1" \
  "ALLOW_OVERWRITE=${ALLOW_OVERWRITE:-0}")"
train_jobs+=("answer_seed42=${answer_job}")

dual_job="$(submit_train \
  "32b_dual_s42" \
  "${ROOT}/experiments/llamafactory_configs/qwen25vl32b_cepo_dual_dpo_seed42_${SHARDING}.yaml" \
  "${dual_output}" \
  "${ROOT}/experiments/llamafactory_data_cepo_dual" \
  "cvpr_cepo_dual_dpo.json" \
  "1" \
  "ALLOW_OVERWRITE=${ALLOW_OVERWRITE:-0}")"
train_jobs+=("dual_seed42=${dual_job}")

for eval_jsonl in "${internal_evals[@]}"; do
  eval_jobs+=("$(submit_object_eval "" base "" "${eval_jsonl}")")
  eval_jobs+=("$(submit_object_eval "${answer_job}" cepo_answer_dpo "${answer_output}" "${eval_jsonl}")")
  eval_jobs+=("$(submit_object_eval "${dual_job}" cepo_dual_dpo "${dual_output}" "${eval_jsonl}")")
done

for eval_jsonl in "${probe_evals[@]}"; do
  eval_jobs+=("$(submit_probe_eval "" base "" "${eval_jsonl}")")
  eval_jobs+=("$(submit_probe_eval "${answer_job}" cepo_answer_dpo "${answer_output}" "${eval_jsonl}")")
  eval_jobs+=("$(submit_probe_eval "${dual_job}" cepo_dual_dpo "${dual_output}" "${eval_jsonl}")")
done

cat <<EOF
Submitted Qwen2.5-VL-32B backbone transfer:
  profile=${PROFILE}
  sharding=${SHARDING}
  train_jobs=${train_jobs[*]}
  eval_jobs=${eval_jobs[*]}

Outputs:
  adapters: outputs/llamafactory/qwen25vl32b_cepo_{answer,dual}_dpo_seed42_${SHARDING}/
  evals: results/eval/generations/<eval>/${OUTPUT_VARIANT}/<model_key>.jsonl
  summarize: python scripts/eval/summarize_qwen25vl32b_backbone_transfer.py
EOF
