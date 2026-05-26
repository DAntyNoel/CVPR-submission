#!/bin/bash
#SBATCH --job-name=cvpr_ans_dpo
#SBATCH --partition=A100,RTX4090,ADA6000,L40S
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:4
#SBATCH --mem=160G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/train_answer_dpo.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/train_answer_dpo.%j.err

set -xeuo pipefail

cd /home/fhshao/CVPR-submission/LLaMA-Factory
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/home/fhshao/CVPR-submission/.cache/hf
export PYTHONPATH=/home/fhshao/CVPR-submission/LLaMA-Factory/src
export FORCE_TORCHRUN=1

/home/fhshao/miniconda3/envs/perl/bin/python -m llamafactory.cli train \
  /home/fhshao/CVPR-submission/experiments/llamafactory_configs/qwen25vl_answer_dpo.yaml

