#!/bin/bash
set -euo pipefail

cd /home/fhshao/CVPR-submission
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
  local train_job="$1"
  local eval_jsonl="$2"
  local short_name="$3"

  submit_and_strip_cluster \
    --dependency=afterok:${train_job} \
    --job-name="${short_name}" \
    --export=ALL,MODEL_KEY=input_side_main_balanced_hard_dpo,EVAL_JSONL="${eval_jsonl}",OUTPUT_VARIANT=input_side_main \
    experiments/slurm/eval_vlm_object_hallucination.slurm
}

train_job=$(submit_and_strip_cluster experiments/slurm/train_input_side_main_balanced_hard_dpo.slurm)

coco_job=$(submit_eval "${train_job}" data/eval/coco_heldout_object_existence.jsonl "eval_is_bh_coco")
gqa_job=$(submit_eval "${train_job}" data/eval/gqa_simple_heldout.jsonl "eval_is_bh_gqa")
hard_job=$(submit_eval "${train_job}" data/eval/coco_hard_object_existence.jsonl "eval_is_bh_hard")
mined_job=$(submit_eval "${train_job}" data/eval/base_error_mined_object_existence.jsonl "eval_is_bh_mine")

cat <<EOF
Submitted Balanced Hard Input-Side Evidence DPO:
  train=${train_job}

Submitted afterok eval jobs under OUTPUT_VARIANT=input_side_main:
  COCO=${coco_job}
  GQA=${gqa_job}
  Hard=${hard_job}
  BaseError=${mined_job}
EOF
