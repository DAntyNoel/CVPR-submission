#!/bin/bash
set -euo pipefail

cd /home/fhshao/CVPR-submission

ANSWER_ADAPTER=/home/fhshao/CVPR-submission/outputs/llamafactory/qwen25vl7b_mixed10k_answer_dpo
EVIDENCE_ADAPTER=/home/fhshao/CVPR-submission/outputs/llamafactory/qwen25vl7b_mixed10k_evidence_hint_dpo_zero2
EVAL_SLURM=experiments/slurm/eval_vlm_object_hallucination.slurm
OUTPUT_VARIANT=mixed10k

submit_and_strip_cluster() {
  local raw
  raw="$(sbatch --parsable "$@")"
  echo "${raw%%;*}"
}

submit_eval() {
  local dependency="$1"
  local model_key="$2"
  local adapter_path="$3"
  local eval_jsonl="$4"

  submit_and_strip_cluster \
    --dependency="afterok:${dependency}" \
    --export="ALL,MODEL_KEY=${model_key},EVAL_JSONL=${eval_jsonl},ADAPTER_NAME_OR_PATH=${adapter_path},OUTPUT_VARIANT=${OUTPUT_VARIANT}" \
    "${EVAL_SLURM}"
}

DATA_JOB="$(submit_and_strip_cluster scripts/data/prepare_mixed_10k_scaleup.slurm)"
ANSWER_TRAIN_JOB="$(submit_and_strip_cluster --dependency="afterok:${DATA_JOB}" experiments/slurm/train_mixed10k_answer_dpo.slurm)"
EVIDENCE_TRAIN_JOB="$(submit_and_strip_cluster --dependency="afterok:${DATA_JOB}" experiments/slurm/train_mixed10k_evidence_hint_dpo.slurm)"

ANSWER_COCO_JOB="$(submit_eval "${ANSWER_TRAIN_JOB}" answer_dpo "${ANSWER_ADAPTER}" data/eval/coco_heldout_object_existence.jsonl)"
ANSWER_GQA_JOB="$(submit_eval "${ANSWER_TRAIN_JOB}" answer_dpo "${ANSWER_ADAPTER}" data/eval/gqa_simple_heldout.jsonl)"
ANSWER_HARD_JOB="$(submit_eval "${ANSWER_TRAIN_JOB}" answer_dpo "${ANSWER_ADAPTER}" data/eval/coco_hard_object_existence.jsonl)"

EVIDENCE_COCO_JOB="$(submit_eval "${EVIDENCE_TRAIN_JOB}" evidence_hint_dpo "${EVIDENCE_ADAPTER}" data/eval/coco_heldout_object_existence.jsonl)"
EVIDENCE_GQA_JOB="$(submit_eval "${EVIDENCE_TRAIN_JOB}" evidence_hint_dpo "${EVIDENCE_ADAPTER}" data/eval/gqa_simple_heldout.jsonl)"
EVIDENCE_HARD_JOB="$(submit_eval "${EVIDENCE_TRAIN_JOB}" evidence_hint_dpo "${EVIDENCE_ADAPTER}" data/eval/coco_hard_object_existence.jsonl)"

cat <<EOF
10k mixed scale-up submitted.
data_job=${DATA_JOB}
answer_train_job=${ANSWER_TRAIN_JOB}
evidence_train_job=${EVIDENCE_TRAIN_JOB}
answer_eval_jobs=${ANSWER_COCO_JOB},${ANSWER_GQA_JOB},${ANSWER_HARD_JOB}
evidence_eval_jobs=${EVIDENCE_COCO_JOB},${EVIDENCE_GQA_JOB},${EVIDENCE_HARD_JOB}
output_variant=${OUTPUT_VARIANT}
EOF
