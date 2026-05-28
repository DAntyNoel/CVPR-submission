#!/usr/bin/env bash
# Submit fixed-budget CEPO controls and dependent internal/probe evals.

set -euo pipefail

ROOT=/home/fhshao/CVPR-submission
PY=/home/fhshao/miniconda3/envs/verl0.6/bin/python

cd "${ROOT}"
mkdir -p logs v2/tasks/fixed-budget-control-experiments/results

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

prepare_variant() {
  local variant="$1"
  local answer_count="$2"
  local supported_count="$3"
  local wrong_count="$4"
  local data_dir="$5"
  local lf_dir="$6"
  local expected_total="$7"

  "${PY}" scripts/data/14_export_cepo_dual_dpo.py \
    --output-dir "${data_dir}" \
    --answer-count "${answer_count}" \
    --supported-verifier-count "${supported_count}" \
    --wrong-evidence-verifier-count "${wrong_count}" \
    --seed 42
  "${PY}" scripts/experiments/prepare_llamafactory_data_cepo_dual.py \
    --dual-input "${data_dir}/cepo_dual_dpo_train.jsonl" \
    --output-dir "${lf_dir}"
  "${PY}" - "${ROOT}/${data_dir}" "${ROOT}/${lf_dir}" "${expected_total}" "${variant}" <<'PY'
import json
import sys
from pathlib import Path

data_dir = Path(sys.argv[1])
lf_dir = Path(sys.argv[2])
expected_total = int(sys.argv[3])
variant = sys.argv[4]

jsonl_path = data_dir / "cepo_dual_dpo_train.jsonl"
lf_path = lf_dir / "cvpr_cepo_dual_dpo.json"
info_path = lf_dir / "dataset_info.json"

jsonl_count = sum(1 for line in jsonl_path.open(encoding="utf-8") if line.strip())
lf_count = len(json.loads(lf_path.read_text(encoding="utf-8")))
if jsonl_count != expected_total or lf_count != expected_total:
    raise SystemExit(
        f"{variant}: expected {expected_total} rows, got jsonl={jsonl_count}, lf={lf_count}"
    )
if not info_path.exists():
    raise SystemExit(f"{variant}: missing {info_path}")
print(f"{variant}: prepared {expected_total} rows")
PY
}

submit_object_eval() {
  local dependency="$1"
  local model_key="$2"
  local adapter_path="$3"
  local variant="$4"
  local eval_jsonl="$5"
  local eval_name short_name output_variant

  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  output_variant="cepo_fixed_budget/${variant}"
  short_name="fb_${variant:0:8}_${eval_name:0:8}"
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
  local variant="$4"
  local eval_jsonl="$5"
  local eval_name short_name output_variant

  eval_name="$(basename "${eval_jsonl}" .jsonl)"
  output_variant="cepo_fixed_budget/${variant}"
  short_name="fbp_${variant:0:7}_${eval_name:0:8}"
  submit_and_strip_cluster \
    --job-name="${short_name}" \
    --dependency=afterok:${dependency} \
    --export=ALL,MODEL_KEY="${model_key}",ADAPTER_NAME_OR_PATH="${adapter_path}",EVAL_JSONL="${ROOT}/${eval_jsonl}",OUTPUT_VARIANT="${output_variant}" \
    experiments/slurm/eval_cepo_evidence_probe.slurm
}

"${PY}" scripts/data/13_check_cepo_data.py
test -f data/eval/cepo_evidence_probe.jsonl
test -f data/eval/cepo_wrong_evidence_probe.jsonl
test -f data/eval/base_error_mined_object_existence.jsonl

prepare_variant \
  answer4k \
  4000 0 0 \
  data/processed/cepo_fixed_budget/answer4k \
  experiments/llamafactory_data_cepo_fixed_budget/answer4k \
  4000
prepare_variant \
  dual1k_fixed6k \
  5000 500 500 \
  data/processed/cepo_fixed_budget/dual1k_fixed6k \
  experiments/llamafactory_data_cepo_fixed_budget/dual1k_fixed6k \
  6000
prepare_variant \
  dual2k_fixed6k \
  4000 1000 1000 \
  data/processed/cepo_fixed_budget/dual2k_fixed6k \
  experiments/llamafactory_data_cepo_fixed_budget/dual2k_fixed6k \
  6000

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

variants=(answer4k dual1k_fixed6k dual2k_fixed6k)
model_keys=(cepo_answer4k_dpo cepo_fixed6k_dual1k_dpo cepo_fixed6k_dual2k_dpo)
configs=(
  "${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_answer4k_dpo.yaml"
  "${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_fixed6k_dual1k_dpo.yaml"
  "${ROOT}/experiments/llamafactory_configs/qwen25vl_cepo_fixed6k_dual2k_dpo.yaml"
)
lf_dirs=(
  "${ROOT}/experiments/llamafactory_data_cepo_fixed_budget/answer4k"
  "${ROOT}/experiments/llamafactory_data_cepo_fixed_budget/dual1k_fixed6k"
  "${ROOT}/experiments/llamafactory_data_cepo_fixed_budget/dual2k_fixed6k"
)
outputs=(
  "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_answer4k_dpo_zero2"
  "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_fixed6k_dual1k_dpo_zero2"
  "${ROOT}/outputs/llamafactory/qwen25vl7b_cepo_fixed6k_dual2k_dpo_zero2"
)

declare -a train_jobs=()
declare -a eval_jobs=()

for i in "${!variants[@]}"; do
  variant="${variants[$i]}"
  model_key="${model_keys[$i]}"
  config="${configs[$i]}"
  lf_dir="${lf_dirs[$i]}"
  output_dir="${outputs[$i]}"

  test -f "${config}"
  test -f "${lf_dir}/dataset_info.json"
  test -f "${lf_dir}/cvpr_cepo_dual_dpo.json"

  if [[ -d "${output_dir}" && "${ALLOW_OVERWRITE:-0}" != "1" ]]; then
    echo "Refusing to overwrite ${output_dir}; set ALLOW_OVERWRITE=1 to rerun." >&2
    exit 2
  fi

  train_job="$(submit_and_strip_cluster \
    --job-name="cepo_fb_${variant:0:8}" \
    --export=ALL,CONFIG_PATH="${config}",OUTPUT_DIR="${output_dir}",DATASET_DIR="${lf_dir}",DATASET_FILE="cvpr_cepo_dual_dpo.json" \
    experiments/slurm/train_cepo_seed_stability_dpo.slurm)"
  train_jobs+=("${variant}=${train_job}")

  for eval_jsonl in "${internal_evals[@]}"; do
    eval_jobs+=("$(submit_object_eval "${train_job}" "${model_key}" "${output_dir}" "${variant}" "${eval_jsonl}")")
  done
  for eval_jsonl in "${probe_evals[@]}"; do
    eval_jobs+=("$(submit_probe_eval "${train_job}" "${model_key}" "${output_dir}" "${variant}" "${eval_jsonl}")")
  done
done

cat <<EOF
Submitted CEPO fixed-budget pipeline:
  submitted_at=$(date -Iseconds)
  train_jobs=${train_jobs[*]}
  eval_jobs=${eval_jobs[*]}

Outputs:
  adapters: outputs/llamafactory/qwen25vl7b_cepo_{answer4k,fixed6k_dual1k,fixed6k_dual2k}_dpo_zero2/
  evals: results/eval/generations/<eval>/cepo_fixed_budget/<variant>/<model_key>.jsonl
EOF
