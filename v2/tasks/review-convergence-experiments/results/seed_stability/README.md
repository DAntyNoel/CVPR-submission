# Seed Stability Results

This directory stores completed extra-seed evidence for the central V3
conclusion.

Rows in `metrics.csv`:

- default seed 42, CEPO Answer-DPO;
- default seed 42, CEPO-Dual-2k;
- seed 13, CEPO Answer-DPO;
- seed 13, CEPO-Dual-2k;
- seed 97, CEPO Answer-DPO;
- seed 97, CEPO-Dual-2k.

Base Instruct is copied from the locked V3 evaluation and does not need a seed
row.

Completed result:

- CEPO-Dual-2k improves wrong-evidence rejection over CEPO Answer-DPO by
  +38.8, +36.0, and +35.2 points for seeds 13, 42, and 97.
- COCO/GQA/Hard accuracy stays within 0.3 points between the two trained
  groups for every seed.
- JSON-object parsing, scored-output rate, and parse failure remain
  100.0 / 100.0 / 0.0 on the evidence probes.

Heavy reruns must be submitted through Slurm. Do not run 7B training or full
VLM inference directly in the interactive environment.
