#!/bin/bash
# MTF_SLURM_HEADER_BEGIN
#SBATCH --job-name=gpt2_124M-openwebtext_85.3m-mtf-debug-slurm
#SBATCH --mem-per-cpu=8gb
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --gres=gpu:8
#SBATCH --output=/home/fhshao/CVPR-submission/logs/slurm.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/slurm.%j.err
#SBATCH --partition=A100,ADA6000,L40S,RTX4090
#SBATCH --time=7-00:00:00
# MTF_SLURM_HEADER_END

set -xeuo pipefail

echo "Do some job"
# ...