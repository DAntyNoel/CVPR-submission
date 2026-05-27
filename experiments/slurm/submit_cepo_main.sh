#!/usr/bin/env bash
# Submit only the two CEPO main training jobs.

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

"${PY}" scripts/data/13_check_cepo_data.py
test -f experiments/llamafactory_data_cepo/dataset_info.json

answer_train_job=$(submit_and_strip_cluster experiments/slurm/train_cepo_answer_dpo.slurm)
latent_train_job=$(submit_and_strip_cluster experiments/slurm/train_cepo_latent_dpo.slurm)

cat <<EOF
Submitted CEPO main training jobs:
  train_cepo_answer_dpo=${answer_train_job}
  train_cepo_latent_dpo=${latent_train_job}
EOF
