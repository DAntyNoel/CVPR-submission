#!/bin/bash
#SBATCH --job-name=cvpr_is_bh_dpo
#SBATCH --partition=A100,RTX4090,ADA6000,L40S
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:4
#SBATCH --mem=160G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/train_input_side_main_balanced_hard_dpo.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/train_input_side_main_balanced_hard_dpo.%j.err

set -xeuo pipefail

cd /home/fhshao/CVPR-submission
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/home/fhshao/CVPR-submission/.cache/hf
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID:-cvpr_is_bh_dpo}
export PYTHONPATH=/home/fhshao/CVPR-submission/LLaMA-Factory/src
export PATH=/home/fhshao/miniconda3/envs/verl0.6/bin:$PATH
export FORCE_TORCHRUN=1
mkdir -p "$TRITON_CACHE_DIR"

/home/fhshao/miniconda3/envs/verl0.6/bin/python \
  /home/fhshao/CVPR-submission/tasks/input-side-evidence-main-method/build_input_side_main_balanced_hard_dpo.py

cd /home/fhshao/CVPR-submission/LLaMA-Factory
/home/fhshao/miniconda3/envs/verl0.6/bin/python -m llamafactory.cli train \
  /home/fhshao/CVPR-submission/experiments/llamafactory_configs/qwen25vl_input_side_main_balanced_hard_dpo.yaml
