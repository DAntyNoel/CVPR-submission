#!/bin/bash
#SBATCH --job-name=cvpr_ext_imgs
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fhshao/CVPR-submission/logs/external_eval_images.%j.out
#SBATCH --error=/home/fhshao/CVPR-submission/logs/external_eval_images.%j.err

set -xeuo pipefail

cd /home/fhshao/CVPR-submission
unset http_proxy
unset https_proxy
unset all_proxy

PYTHON_BIN=/home/fhshao/miniconda3/envs/perl/bin/python
export PYTHONUNBUFFERED=1
mkdir -p logs data/raw/coco data/raw/amber

"$PYTHON_BIN" -c "import requests; print('requests-ok', requests.__version__)"

"$PYTHON_BIN" scripts/data/11_prepare_external_eval_images.py \
  --benchmarks all \
  --manifest data/raw/external_eval_images_manifest.json \
  --amber-source "${AMBER_SOURCE:-auto}" \
  --amber-hf-endpoint "${AMBER_HF_ENDPOINT:-https://hf-mirror.com}" \
  --workers "${COCO_WORKERS:-16}"

"$PYTHON_BIN" scripts/eval/prepare_official_external_benchmarks.py \
  --skip-download \
  --require-images
