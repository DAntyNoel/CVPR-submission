# Fixed-Budget Control Experiments

Created: 2026-05-28

## Goal

This task tests whether the CEPO-Dual-2k gain is only caused by using more
training rows than CEPO Answer-DPO. The control keeps the total training budget
fixed at 6,000 rows and replaces answer rows with verifier rows.

## Experiment Matrix

| Setting | Answer rows | Verifier rows | Total rows | Purpose |
| --- | ---: | ---: | ---: | --- |
| Answer-4k | 4,000 | 0 | 4,000 | Controls for fewer answer rows in Dual-2k-fixed6k. |
| Dual-1k-fixed6k | 5,000 | 1,000 | 6,000 | Tests a fixed-budget 1k verifier mix. |
| Dual-2k-fixed6k | 4,000 | 2,000 | 6,000 | Tests whether the 2k verifier effect survives without extra total rows. |

The existing CEPO Answer-DPO-6k and CEPO-Dual-2k runs are reused as references
and are not retrained here.

## Submission

Run all fixed-budget controls through Slurm:

```bash
bash experiments/slurm/submit_cepo_fixed_budget_pipeline.sh
```

Heavy training and full VLM inference must not be run directly in the
interactive environment.

## Results

Status: complete. All three fixed-budget Slurm trainings and dependent evals
finished, and `scripts/eval/summarize_cepo_fixed_budget_results.py` reports
`status=ready` for every fixed-budget row.

Canonical task-level outputs live under:

```text
results/
  metrics.csv
  summary.md
  job_manifest.md
  submitted_jobs.md
```

Raw eval generations are written under:

```text
results/eval/generations/<eval>/cepo_fixed_budget/<variant>/<model_key>.jsonl
```

After Slurm jobs complete, summarize with:

```bash
python scripts/eval/summarize_cepo_fixed_budget_results.py
```

## Stop Rule

If Dual-2k-fixed6k improves wrong-evidence rejection over CEPO Answer-DPO-6k
by at least 20 points while COCO/GQA/Hard accuracy drops by at most 1 point,
the paper can state that verifier replacement remains effective under a fixed
6k-row budget. Otherwise, the paper should state that the original CEPO-Dual-2k
gain is partly confounded by total training volume.

Observed result: Dual-2k-fixed6k reaches 62.7% wrong-evidence rejection versus
34.3% for CEPO Answer-DPO-6k, a +28.5 point gain. COCO/GQA/Hard accuracy is
96.9/76.9/95.1 versus 97.0/76.8/95.0, so the short-answer deltas are
-0.1/+0.1/+0.1 points. Probe parse failure is 0.0%. This satisfies the strong
control condition and is integrated only as appendix/control evidence.
