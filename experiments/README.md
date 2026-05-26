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
sbatch experiments/slurm/smoke_dpo.slurm
sbatch experiments/slurm/train_answer_dpo.slurm
sbatch experiments/slurm/train_evidence_hint_dpo.slurm
```

The smoke job runs both DPO variants with `max_samples: 8`, `max_steps: 2`,
`template: qwen2_vl`, and ZeRO-3. The full jobs use the same fixed template and
the same LLaMA-Factory data registry.

Training and smoke scripts use the `verl0.6` conda environment. It is pinned to
torch 2.8.0 to avoid the LLaMA-Factory torch 2.9 + Conv3D guard for Qwen2.5-VL.

The current processed data is COCO-only because GQA download failed under the
cluster HF mirror path. This matches the fallback in the data plan and narrows
the first conclusion to simple object hallucination.
