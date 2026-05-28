#!/usr/bin/env bash
# Submit the locked relation-stress CEPO-Probe evaluation matrix.

set -euo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python
PROBE="${PROBE:-${ROOT}/v2/tasks/review-convergence-experiments/results/relation_stress/relation_stress_probe.jsonl}"

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

if [[ ! -f "${PROBE}" ]]; then
  "${PY}" scripts/eval/prepare_relation_stress_probe.py --output "${PROBE}"
fi
test -f "${PROBE}"
test -f outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2/adapter_model.safetensors
test -f outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2/adapter_model.safetensors

declare -a eval_jobs=()
eval_jobs+=("$(submit_and_strip_cluster \
  --job-name="relstress_base" \
  --export=ALL,MODEL_KEY=base,EVAL_JSONL="${PROBE}",OUTPUT_VARIANT=relation_stress \
  experiments/slurm/eval_cepo_evidence_probe.slurm)")
eval_jobs+=("$(submit_and_strip_cluster \
  --job-name="relstress_ans" \
  --export=ALL,MODEL_KEY=cepo_answer_dpo,ADAPTER_NAME_OR_PATH="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2",EVAL_JSONL="${PROBE}",OUTPUT_VARIANT=relation_stress \
  experiments/slurm/eval_cepo_evidence_probe.slurm)")
eval_jobs+=("$(submit_and_strip_cluster \
  --job-name="relstress_dual" \
  --export=ALL,MODEL_KEY=cepo_dual_dpo,ADAPTER_NAME_OR_PATH="${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2",EVAL_JSONL="${PROBE}",OUTPUT_VARIANT=relation_stress \
  experiments/slurm/eval_cepo_evidence_probe.slurm)")

cat <<EOF
Submitted relation-stress eval:
  eval_jobs=${eval_jobs[*]}

Outputs:
  probe: ${PROBE}
  evals: results/eval/generations/relation_stress_probe/relation_stress/<model_key>.jsonl
EOF
