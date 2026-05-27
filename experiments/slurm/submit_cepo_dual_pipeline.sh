#!/usr/bin/env bash
# Submit CEPO-Dual training plus the fixed main/evidence evaluation matrix.

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

submit_probe_eval() {
  local model_key="$1"
  local eval_jsonl="$2"
  local short_name="$3"
  local dependency="${4:-}"
  local args=(--job-name="${short_name}")
  if [[ -n "${dependency}" ]]; then
    args+=(--dependency=afterok:${dependency})
  fi
  submit_and_strip_cluster \
    "${args[@]}" \
    --export=ALL,MODEL_KEY="${model_key}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT=cepo_dual_evidence_probe \
    experiments/slurm/eval_cepo_evidence_probe.slurm
}

"${PY}" scripts/data/13_check_cepo_data.py
"${PY}" scripts/data/14_export_cepo_dual_dpo.py
"${PY}" scripts/experiments/prepare_llamafactory_data_cepo_dual.py
test -f experiments/llamafactory_data_cepo_dual/dataset_info.json
test -f data/eval/cepo_evidence_probe.jsonl
test -f data/eval/cepo_wrong_evidence_probe.jsonl

dual_train_job=$(submit_and_strip_cluster experiments/slurm/train_cepo_dual_dpo.slurm)

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
probe_evals=(
  data/eval/cepo_evidence_probe.jsonl
  data/eval/cepo_wrong_evidence_probe.jsonl
)

declare -a eval_jobs=()
for eval_jsonl in "${internal_evals[@]}"; do
  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  eval_jobs+=("$(submit_eval base "${eval_jsonl}" cepo_dual "dual_base_${eval_name:0:8}")")
  eval_jobs+=("$(submit_eval cepo_answer_dpo "${eval_jsonl}" cepo_dual "dual_ans_${eval_name:0:8}")")
  eval_jobs+=("$(submit_eval cepo_dual_dpo "${eval_jsonl}" cepo_dual "dual_dual_${eval_name:0:8}" "${dual_train_job}")")
done

for eval_jsonl in "${external_evals[@]}"; do
  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  eval_jobs+=("$(submit_eval base "${eval_jsonl}" cepo_dual_external "dual_base_${eval_name:0:8}")")
  eval_jobs+=("$(submit_eval cepo_answer_dpo "${eval_jsonl}" cepo_dual_external "dual_ans_${eval_name:0:8}")")
  eval_jobs+=("$(submit_eval cepo_dual_dpo "${eval_jsonl}" cepo_dual_external "dual_dual_${eval_name:0:8}" "${dual_train_job}")")
done

for eval_jsonl in "${probe_evals[@]}"; do
  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  eval_jobs+=("$(submit_probe_eval base "${eval_jsonl}" "dual_probe_base_${eval_name:0:8}")")
  eval_jobs+=("$(submit_probe_eval cepo_answer_dpo "${eval_jsonl}" "dual_probe_ans_${eval_name:0:8}")")
  eval_jobs+=("$(submit_probe_eval cepo_dual_dpo "${eval_jsonl}" "dual_probe_dual_${eval_name:0:8}" "${dual_train_job}")")
done

cat <<EOF
Submitted CEPO-Dual pipeline:
  train_cepo_dual_dpo=${dual_train_job}
  eval_jobs=${eval_jobs[*]}

Outputs:
  internal evals: results/eval/generations/<eval>/cepo_dual/<model>.jsonl
  external evals: results/eval/generations/<eval>/cepo_dual_external/<model>.jsonl
  evidence probes: results/eval/generations/<eval>/cepo_dual_evidence_probe/<model>.jsonl
EOF
