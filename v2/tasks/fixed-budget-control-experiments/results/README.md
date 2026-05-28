# Fixed-Budget Results

This folder is the canonical landing area for the 2026-05-30 row-count
confound control.

Files:

- `metrics.csv`: three complete fixed-budget rows written by
  `scripts/eval/summarize_cepo_fixed_budget_results.py`.
- `summary.md`: paper-facing read, including the locked CEPO Answer-DPO-6k
  reference and the stop-rule recommendation.
- `job_manifest.md`: intended training/eval outputs and Slurm job layout.
- `submitted_jobs.md`: concrete Slurm IDs after submission.

Final read: Dual-2k-fixed6k improves wrong-evidence rejection over CEPO
Answer-DPO-6k by +28.5 points while keeping COCO/GQA/Hard accuracy within
0.1 points. Probe parse failure remains 0.0%. The fixed-budget rows do not
change the five-group main table; they are appendix/control evidence for the
row-count confound.
