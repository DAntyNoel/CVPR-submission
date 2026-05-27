#!/bin/bash
set -euo pipefail

cd /home/fhshao/CVPR-submission
mkdir -p logs

submit_and_strip_cluster() {
  local raw
  raw="$(sbatch --parsable "$@")"
  echo "${raw%%;*}"
}

evidence_only_job=$(submit_and_strip_cluster experiments/slurm/train_phase2_evidence_only_dpo.slurm)
input_side_job=$(submit_and_strip_cluster experiments/slurm/train_phase2_input_side_evidence_dpo.slurm)
chosen_only_job=$(submit_and_strip_cluster experiments/slurm/train_phase2_chosen_only_evidence_dpo.slurm)

submit_eval() {
  local train_job="$1"
  local model_key="$2"
  local eval_jsonl="$3"
  local short_name="$4"

  submit_and_strip_cluster \
    --dependency=afterok:${train_job} \
    --job-name="${short_name}" \
    --export=ALL,MODEL_KEY="${model_key}",EVAL_JSONL="${eval_jsonl}",OUTPUT_VARIANT=phase2 \
    experiments/slurm/eval_vlm_object_hallucination.slurm
}

submit_eval_suite() {
  local train_job="$1"
  local model_key="$2"
  local prefix="$3"

  local coco_job
  local gqa_job
  local hard_job
  local mined_job
  coco_job=$(submit_eval "${train_job}" "${model_key}" data/eval/coco_heldout_object_existence.jsonl "eval_${prefix}_coco")
  gqa_job=$(submit_eval "${train_job}" "${model_key}" data/eval/gqa_simple_heldout.jsonl "eval_${prefix}_gqa")
  hard_job=$(submit_eval "${train_job}" "${model_key}" data/eval/coco_hard_object_existence.jsonl "eval_${prefix}_hard")
  mined_job=$(submit_eval "${train_job}" "${model_key}" data/eval/base_error_mined_object_existence.jsonl "eval_${prefix}_mine")

  echo "  ${prefix}: COCO=${coco_job} GQA=${gqa_job} Hard=${hard_job} BaseError=${mined_job}"
}

eval_summary=$(
  submit_eval_suite "${evidence_only_job}" phase2_evidence_only_dpo p2_eonly
  submit_eval_suite "${input_side_job}" phase2_input_side_evidence_dpo p2_input
  submit_eval_suite "${chosen_only_job}" phase2_chosen_only_evidence_dpo p2_chosen
)

cat <<EOF
Submitted Phase-2 method variant jobs:
  Evidence-Only DPO:          ${evidence_only_job}
  Input-Side Evidence DPO:    ${input_side_job}
  Chosen-Only Evidence DPO:   ${chosen_only_job}

Submitted afterok eval jobs under OUTPUT_VARIANT=phase2:
${eval_summary}
EOF
