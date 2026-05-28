# Result Directory Contract

This directory is the canonical task-level result store for V3 convergence.

## Directory Meanings

| Directory | Meaning | Heavy compute required |
| --- | --- | --- |
| `paper_fixes/` | Build/page/citation evidence for no-compute paper fixes | No |
| `seed_stability/` | Extra-seed training and evaluation summaries | Yes, Slurm |
| `relation_stress/` | Locked relation-only probe construction and evaluation | Probe build no; inference yes |
| `backbone_transfer/` | Optional Qwen2.5-VL-32B transfer check | Yes, Slurm |
| `convergence_audit/` | Final requirement-by-requirement decision evidence | No |

## Required Final Files

Before marking this task complete, these files should exist and be current:

```text
results/convergence_audit/current_v3_snapshot.md
results/convergence_audit/current_v3_snapshot.json
results/convergence_audit/final_convergence_audit.md
results/seed_stability/metrics.csv
results/relation_stress/metrics.csv
```

Optional if E3 is run:

```text
results/backbone_transfer/metrics.csv
```
