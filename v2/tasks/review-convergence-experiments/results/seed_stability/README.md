# Seed Stability Results

This directory stores extra-seed evidence for the central V3 conclusion.

Required rows in `metrics.csv`:

- default seed 42, CEPO Answer-DPO;
- default seed 42, CEPO-Dual-2k;
- seed 13, CEPO Answer-DPO;
- seed 13, CEPO-Dual-2k;
- seed 97, CEPO Answer-DPO;
- seed 97, CEPO-Dual-2k.

Base Instruct is copied from the locked V3 evaluation and does not need a seed
row.

Heavy runs must be submitted through Slurm. Do not run 7B training or full VLM
inference directly in the interactive environment.
