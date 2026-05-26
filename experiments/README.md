# Experiment Startup Notes

This folder contains project-specific wrappers around the cloned
`LLaMA-Factory` training code.

The intended main comparison has three groups:

```text
A. Base Instruct: no training
B. Answer-DPO: experiments/llamafactory_configs/qwen25vl_answer_dpo.yaml
C. Evidence-Hint DPO: experiments/llamafactory_configs/qwen25vl_evidence_hint_dpo.yaml
```

Use the 7B Qwen2.5-VL model for the main run. The scripts expect it at:

```text
models/Qwen2.5-VL-7B-Instruct
```

If it is not available in `/data1/public/hf`, download it on a CPU node:

```bash
sbatch experiments/slurm/download_qwen25vl7b.slurm
```

Then launch training jobs on a GPU partition:

```bash
sbatch experiments/slurm/train_answer_dpo.slurm
sbatch experiments/slurm/train_evidence_hint_dpo.slurm
```

The current processed data is COCO-only because GQA download failed under the
cluster HF mirror path. This matches the fallback in the data plan and narrows
the first conclusion to simple object hallucination.

