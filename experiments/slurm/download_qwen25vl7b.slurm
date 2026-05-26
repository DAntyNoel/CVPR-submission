#!/bin/bash
#SBATCH --job-name=qwen25vl7b_dl
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/qwen25vl7b_dl.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/qwen25vl7b_dl.%j.err

set -xeuo pipefail

cd /home/fhshao/CVPR-submission
unset http_proxy
unset https_proxy
unset all_proxy
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/home/fhshao/CVPR-submission/.cache/hf

PYTHON_BIN=/home/fhshao/miniconda3/envs/perl/bin/python
mkdir -p models logs "$HF_HOME"

if [ -d /data1/public/hf/Qwen/Qwen2.5-VL-7B-Instruct ]; then
  ln -sfn /data1/public/hf/Qwen/Qwen2.5-VL-7B-Instruct models/Qwen2.5-VL-7B-Instruct
else
  "$PYTHON_BIN" -m huggingface_hub.commands.huggingface_cli download \
    Qwen/Qwen2.5-VL-7B-Instruct \
    --local-dir models/Qwen2.5-VL-7B-Instruct \
    --local-dir-use-symlinks False
fi

test -f models/Qwen2.5-VL-7B-Instruct/config.json
test -f models/Qwen2.5-VL-7B-Instruct/preprocessor_config.json

