#!/usr/bin/env bash
# Submit the archived V1 mixed-data main training/evaluation matrix.

set -euo pipefail

ROOT=/home/fhshao/CVPR-submission

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
  local dependency="${5:-}"
  local args=(--job-name="${short_name}")
  if [[ -n "${dependency}" ]]; then
    args+=(--dependency=afterok:${dependency})
  fi
  submit_and_strip_cluster \
    "${args[@]}" \
    --export=ALL,MODEL_KEY="${model_key}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${output_variant}" \
    experiments/slurm/eval_vlm_object_hallucination.slurm
}

test -f experiments/llamafactory_data/dataset_info.json
test -f experiments/llamafactory_data/cvpr_answer_dpo.json
test -f experiments/llamafactory_data/cvpr_evidence_hint_dpo.json

answer_train_job=$(submit_and_strip_cluster experiments/slurm/train_answer_dpo.slurm)
evidence_train_job=$(submit_and_strip_cluster experiments/slurm/train_evidence_hint_dpo.slurm)

internal_evals=(
  data/eval/coco_heldout_object_existence.jsonl
  data/eval/gqa_simple_heldout.jsonl
  data/eval/coco_hard_object_existence.jsonl
  data/eval/base_error_mined_object_existence.jsonl
)
external_evals=(
  data/eval/pope_coco_random.jsonl
  data/eval/pope_coco_popular.jsonl
  data/eval/pope_coco_adversarial.jsonl
  data/eval/amber_discriminative.jsonl
)

declare -a eval_jobs=()
for eval_jsonl in "${internal_evals[@]}"; do
  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  eval_jobs+=("$(submit_eval base "${eval_jsonl}" mixed "v1_base_${eval_name:0:8}")")
  eval_jobs+=("$(submit_eval answer_dpo "${eval_jsonl}" mixed "v1_ans_${eval_name:0:8}" "${answer_train_job}")")
  eval_jobs+=("$(submit_eval evidence_hint_dpo "${eval_jsonl}" mixed "v1_eh_${eval_name:0:8}" "${evidence_train_job}")")
done

for eval_jsonl in "${external_evals[@]}"; do
  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  eval_jobs+=("$(submit_eval base "${eval_jsonl}" mixed_external "v1_base_${eval_name:0:8}")")
  eval_jobs+=("$(submit_eval answer_dpo "${eval_jsonl}" mixed_external "v1_ans_${eval_name:0:8}" "${answer_train_job}")")
  eval_jobs+=("$(submit_eval evidence_hint_dpo "${eval_jsonl}" mixed_external "v1_eh_${eval_name:0:8}" "${evidence_train_job}")")
done

cat <<EOF
Submitted V1 mixed main pipeline:
  train_answer_dpo=${answer_train_job}
  train_evidence_hint_dpo=${evidence_train_job}
  eval_jobs=${eval_jobs[*]}

Outputs:
  internal evals: results/eval/generations/<eval>/mixed/<model>.jsonl
  external evals: results/eval/generations/<eval>/mixed_external/<model>.jsonl
EOF
