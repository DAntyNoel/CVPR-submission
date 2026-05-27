# Simulated Review Package

This directory contains two simulated CVPR-style reviews for the current
`paper/build/main.pdf`.

Context:

- The reviewed PDF is the complete manuscript produced from `paper/main.tex`.
- The Evidence-Hint DPO row is evaluated under the user-requested assumption
  that the mixed Evidence-Hint experiment completes normally and yields the
  reported positive trend.
- Before a real submission, verify the reported Evidence-Hint numbers against
  final Slurm logs and `experiments/eval_summary.md`.

Files:

- `reviewer_1.md`: supportive reviewer focused on method clarity and controlled
  experimental design.
- `reviewer_2.md`: more skeptical reviewer focused on benchmark breadth,
  statistical robustness, and the assumed-result boundary.
