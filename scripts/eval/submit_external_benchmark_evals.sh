#!/usr/bin/env bash
# Submit the three fixed model groups on normalized external POPE/AMBER evals.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_VARIANT="${OUTPUT_VARIANT:-mixed_external}"
MODELS=(${MODELS:-base answer_dpo evidence_hint_dpo})
EVALS=(${EVALS:- \
  data/eval/pope_coco_random.jsonl \
  data/eval/pope_coco_popular.jsonl \
  data/eval/pope_coco_adversarial.jsonl \
  data/eval/amber_discriminative.jsonl \
})
DRY_RUN="${DRY_RUN:-0}"
DEPENDENCY="${DEPENDENCY:-}"
SBATCH_ARGS=(${SBATCH_ARGS:-})

cd "${ROOT_DIR}"

for eval_jsonl in "${EVALS[@]}"; do
  if [[ ! -s "${eval_jsonl}" ]]; then
    echo "skip missing eval file: ${eval_jsonl}" >&2
    continue
  fi
  for model_key in "${MODELS[@]}"; do
    cmd=(
      sbatch
      "${SBATCH_ARGS[@]}"
      --export="ALL,MODEL_KEY=${model_key},EVAL_JSONL=${ROOT_DIR}/${eval_jsonl},OUTPUT_VARIANT=${OUTPUT_VARIANT}"
      experiments/slurm/eval_vlm_object_hallucination.slurm
    )
    if [[ -n "${DEPENDENCY}" ]]; then
      cmd=(
        sbatch
        "${SBATCH_ARGS[@]}"
        --dependency="${DEPENDENCY}"
        --export="ALL,MODEL_KEY=${model_key},EVAL_JSONL=${ROOT_DIR}/${eval_jsonl},OUTPUT_VARIANT=${OUTPUT_VARIANT}"
        experiments/slurm/eval_vlm_object_hallucination.slurm
      )
    fi
    if [[ "${DRY_RUN}" == "1" ]]; then
      printf '+'
      printf ' %q' "${cmd[@]}"
      printf '\n'
    else
      "${cmd[@]}"
    fi
  done
done
