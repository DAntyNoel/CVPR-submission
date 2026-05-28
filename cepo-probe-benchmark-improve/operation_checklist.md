# Operation Checklist

This checklist is ordered so the project improves even if no new GPU jobs can
be scheduled immediately.

## 0. Safety Rules

- Use `zsh` and the configured conda environment.
- Use `uv` for package management if new Python dependencies are needed.
- Do not run heavy data movement, 7B training, or full inference locally.
- Submit GPU training and full evaluation through Slurm.
- Prefer ZeRO-2 for GPU experiments.
- Do not `git commit` or `git push` without explicit permission.

## 1. Local-Safe First Pass

1. Confirm existing final artifacts:

```bash
test -f outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2/adapter_model.safetensors
test -f outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2/adapter_model.safetensors
test -f data/eval/cepo_evidence_probe.jsonl
test -f data/eval/cepo_wrong_evidence_probe.jsonl
```

2. Re-score existing evidence-probe outputs with scored row dumps:

```bash
python scripts/eval/score_cepo_evidence_probe.py \
  --input results/eval/generations/cepo_wrong_evidence_probe/cepo_dual_evidence_probe/cepo_dual_dpo.jsonl \
  --scored-output results/eval/metrics/cepo_probe_ci/cepo_dual_wrong_scored.jsonl
```

3. Add a CI utility or notebook-equivalent script:

```text
scripts/eval/bootstrap_cepo_probe_ci.py
```

4. Generate Markdown tables for:

```text
cepo-probe-benchmark-improve/artifacts/table3_ci.md
cepo-probe-benchmark-improve/artifacts/slice_ci.md
```

5. Sample relation failures:

```text
cepo-probe-benchmark-improve/artifacts/relation_failure_cases.md
```

## 2. Paper Edits Before New Training

Update `paper/main.tex` in this order:

1. Expand Related Work.
2. Add Figure 1 or a compact method diagram.
3. Add CEPO-Dual training row table and example.
4. Define BEM Recovery.
5. Split parser metrics.
6. Add CI/slice-N results.
7. Add relation-failure analysis.
8. Build the PDF and check page count.

Build command:

```bash
conda activate cvpr-latex
cd paper
make pdf
```

Expected target:

```text
build/main.pdf has at least 6 pages of main text before references.
```

## 3. Ablation Preparation

Create separate data directories for each ablation:

```text
data/processed/cepo_dual_ablation/evidence_only_2k/
data/processed/cepo_dual_ablation/dual500/
data/processed/cepo_dual_ablation/dual1k/
```

Create separate LLaMA-Factory dataset directories:

```text
experiments/llamafactory_data_cepo_dual_ablation/evidence_only_2k/
experiments/llamafactory_data_cepo_dual_ablation/dual500/
experiments/llamafactory_data_cepo_dual_ablation/dual1k/
```

Create separate output directories:

```text
outputs/llamafactory/qwen25vl7b_cepo_evidence_only_dpo_zero2/
outputs/llamafactory/qwen25vl7b_cepo_dual500_dpo_zero2/
outputs/llamafactory/qwen25vl7b_cepo_dual1k_dpo_zero2/
```

Before submitting, verify that no new job overwrites:

```text
outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2/
```

## 4. Slurm Submission

Recommended new launcher:

```text
experiments/slurm/submit_cepo_ablation_pipeline.sh
```

The launcher should:

1. run `scripts/data/13_check_cepo_data.py`;
2. export the three ablation datasets;
3. prepare the three LLaMA-Factory registries;
4. submit three ZeRO-2 LoRA-DPO training jobs;
5. submit after-ok internal short-answer evals;
6. submit after-ok supported/wrong-evidence probe evals;
7. skip external POPE/AMBER until the best ablation is selected.

Monitor jobs:

```bash
squeue -u "$USER"
sacct -j <jobid> --format=JobID,JobName,Partition,State,ExitCode,Elapsed
```

Stop conditions:

- cancel a job if it is using the wrong output directory;
- cancel a job if it falls back to ZeRO-3 unexpectedly and throughput becomes
  too slow;
- cancel dependent evals if training exits non-zero.

## 5. Post-Run Scoring

For each completed ablation:

1. Score short-answer evals with `score_object_eval.py`.
2. Score evidence probes with `score_cepo_evidence_probe.py`.
3. Run CI utility on supported and wrong-evidence probes.
4. Update:

```text
cepo-probe-benchmark-improve/artifacts/ablation_results.md
experiments/eval_summary.md
experiments/training_summary.md
```

5. Update `paper/main.tex` only after the table is internally consistent.

## 6. Final Handoff Criteria

The improvement cycle is ready to stop when:

- the paper is at least 6 pages main text;
- CI/slice counts are in the CEPO-Probe table;
- BEM Recovery and parser metrics are clearly defined;
- ablation table has at least Evidence-DPO only, CEPO-Dual-500, CEPO-Dual-1k,
  and the existing CEPO-Dual-2k;
- relation-failure cases are summarized;
- `README.md` and the relevant experiment summaries point to the new plan.
