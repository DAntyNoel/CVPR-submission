#!/bin/bash
set -euo pipefail

cd /home/fhshao/CVPR-submission
mkdir -p logs

submit_and_strip_cluster() {
  local raw
  raw="$(sbatch --parsable "$@")"
  echo "${raw%%;*}"
}

submit_eval() {
  local train_job="$1"
  local eval_jsonl="$2"
  local short_name="$3"

  submit_and_strip_cluster \
    --dependency=afterok:${train_job} \
    --job-name="${short_name}" \
    --export=ALL,MODEL_KEY=answer_evidence_mix_dpo,EVAL_JSONL="${eval_jsonl}",OUTPUT_VARIANT=answer_evidence_mix \
    experiments/slurm/eval_vlm_object_hallucination.slurm
}

train_job=$(submit_and_strip_cluster experiments/slurm/train_answer_evidence_mix_dpo.slurm)

coco_job=$(submit_eval "${train_job}" data/eval/coco_heldout_object_existence.jsonl "eval_mix_coco")
gqa_job=$(submit_eval "${train_job}" data/eval/gqa_simple_heldout.jsonl "eval_mix_gqa")
hard_job=$(submit_eval "${train_job}" data/eval/coco_hard_object_existence.jsonl "eval_mix_hard")
mined_job=$(submit_eval "${train_job}" data/eval/base_error_mined_object_existence.jsonl "eval_mix_mine")

cat <<EOF
Submitted Answer-Evidence Mix DPO:
  train=${train_job}

Submitted afterok eval jobs under OUTPUT_VARIANT=answer_evidence_mix:
  COCO=${coco_job}
  GQA=${gqa_job}
  Hard=${hard_job}
  BaseError=${mined_job}
EOF
