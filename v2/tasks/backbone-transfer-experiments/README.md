# Backbone Transfer Experiments

Created: 2026-05-28

## Purpose

This task plans the added-backbone evidence for the CEPO-Probe paper after the
second official review. The current paper already has a converged 7B result:
five main groups, three-seed stability for CEPO Answer-DPO and CEPO-Dual-2k,
and a locked relation-stress probe. The remaining external-validity concern is
whether the answer-vs-evidence separation also appears on a larger downloaded
backbone.

The currently available local backbones are:

| Backbone | Local path | Role |
| --- | --- | --- |
| Qwen2.5-VL-7B-Instruct | `models/Qwen2.5-VL-7B-Instruct` | Locked main-paper backbone |
| Qwen2.5-VL-32B-Instruct | `models/Qwen2.5-VL-32B-Instruct` | Transfer backbone for appendix evidence |

The 32B transfer should not replace the five-group 7B main table. It is an
appendix/diagnostic check for the single-backbone criticism.

## Available Assets

The 32B checkpoint and sidecar data exports are already present:

```text
models/Qwen2.5-VL-32B-Instruct/
data/processed/qwen25vl32b/
experiments/llamafactory_data_qwen25vl32b/
experiments/llamafactory_data_input_side_main_qwen25vl32b/
```

The CEPO-Probe evaluation files remain shared across backbones:

```text
data/eval/coco_heldout_object_existence.jsonl
data/eval/gqa_simple_heldout.jsonl
data/eval/coco_hard_object_existence.jsonl
data/eval/base_error_mined_object_existence.jsonl
data/eval/cepo_evidence_probe.jsonl
data/eval/cepo_wrong_evidence_probe.jsonl
v2/tasks/review-convergence-experiments/results/relation_stress/relation_stress_probe.jsonl
```

Heavy training and full VLM inference must be submitted through Slurm. Prefer
ZeRO-2 for GPU training; if 32B OOMs under ZeRO-2, record the failed preflight
and only then switch the follow-up plan to a stronger sharding setup.

Current run constraint: the first usable 32B transfer result must be available
within two days. Smoke tests therefore check both memory fit and step time. The
resource ladder is:

1. `rtx4090_z2_4`: 4x RTX4090 ZeRO-2, one-step smoke only.
2. `rtx4090_z2_8`: 8x RTX4090 ZeRO-2 if 4x4090 OOMs or projects beyond 48h.
3. `l40s_z2_8` or `ada6000_z2_8`: 8x L40S / RTX 6000 Ada when 4090 is too
   memory-constrained or too slow.
4. `l40s_z3_8` / `ada6000_z3_8`: ZeRO-3 strong sharding after ZeRO-2 load
   OOMs on 48GB-class GPUs.
5. `ada6000_qlora4_8`: 4-bit bitsandbytes QLoRA with ZeRO-2 if BF16 ZeRO-3
   fits but projects beyond the two-day deadline.
6. `a100_z3_4` / `a100_qlora4_4`: A100 fallbacks if L40S/ADA6000 queueing
   blocks the two-day deadline.

## Experiment Matrix

Keep the transfer matrix intentionally small:

| ID | Backbone | Training | Seed | Required? | Purpose |
| --- | --- | --- | ---: | --- | --- |
| T0 | Qwen2.5-VL-32B | Base Instruct | n/a | Yes | Check 32B base behavior on the same probes |
| T1 | Qwen2.5-VL-32B | CEPO Answer-DPO | 42 | Yes | Test answer-only tuning on 32B |
| T2 | Qwen2.5-VL-32B | CEPO-Dual-2k | 42 | Yes | Test whether verifier supervision recovers evidence rejection |
| T3 | Qwen2.5-VL-32B | CEPO-Dual-2k | 13 or 97 | Optional | Run only if T2 is unstable, failed, or reverses the claim |

Do not train Evidence-DPO-only, CEPO-Dual-500, or CEPO-Dual-1k on 32B unless
the first transfer result contradicts the 7B story and a diagnostic follow-up
is needed. The 32B transfer is a breadth check, not a new main ablation.

## Implementation Outline

1. Create 32B CEPO training configs by copying the locked 7B CEPO Answer-DPO
   and CEPO-Dual-2k YAMLs, changing only:
   - `model_name_or_path` to `models/Qwen2.5-VL-32B-Instruct`;
   - `dataset_dir` to the matching 32B export if needed;
   - `output_dir` to `outputs/llamafactory/qwen25vl32b_cepo_*_zero2`;
   - `seed` to 42;
   - worker/cache settings to the serialized values used by seed stability.
2. Add a 32B Slurm training wrapper that mirrors the seed-stability wrapper,
   uses ZeRO-2 first, and refuses to overwrite existing 32B adapters unless an
   explicit overwrite flag is set.
3. Add a 32B submit helper that launches T1 and T2 training, then dependent
   eval jobs for short-answer transfer, CEPO supported/wrong probes, and
   relation-stress.
4. Extend evaluation invocation to pass `--model-name-or-path
   models/Qwen2.5-VL-32B-Instruct` for the 32B base and trained adapters. Avoid
   changing the locked 7B `MODEL_KEY` behavior.
5. Summarize results into `results/backbone_transfer/metrics.csv` and a short
   Markdown report before touching the paper.

Implemented entrypoints:

```bash
# Memory/speed preflight. Escalate PROFILE if this OOMs or is too slow.
PROFILE=rtx4090_z2_4 bash experiments/slurm/submit_qwen25vl32b_backbone_transfer.sh smoke

# Fixed 2026-05-28 setting after ZeRO-2 OOMs and QLoRA smoke tests.
PROFILE=ada6000_qlora4_8 SMOKE_TARGET=answer bash experiments/slurm/submit_qwen25vl32b_backbone_transfer.sh smoke
PROFILE=ada6000_qlora4_8 SMOKE_TARGET=dual bash experiments/slurm/submit_qwen25vl32b_backbone_transfer.sh smoke

# Full T0/T1/T2 transfer after the fastest viable smoke profile is fixed.
PROFILE=ada6000_qlora4_8 \
EVAL_PARTITION=A100,L40S,ADA6000 \
EVAL_GPUS=4 \
EVAL_MEM=320G \
EVAL_TIME=12:00:00 \
bash experiments/slurm/submit_qwen25vl32b_backbone_transfer.sh full

# Summarize completed metrics.
python scripts/eval/summarize_qwen25vl32b_backbone_transfer.py
```

The submit helper supports `PROFILE=rtx4090_z2_4`, `rtx4090_z2_8`,
`l40s_z2_8`, `ada6000_z2_8`, `a100_z2_4`, `rtx4090_qlora4_8`,
`l40s_qlora4_8`, `ada6000_qlora4_8`, `a100_qlora4_4`, `l40s_z3_8`,
`ada6000_z3_8`, and `a100_z3_4`. Profiles containing `_z3_` automatically use
the ZeRO-3 YAMLs; profiles containing `_qlora4_` automatically use the 4-bit
QLoRA YAMLs. Full training defaults to a `1-20:00:00` Slurm time limit to keep
the wall-clock budget inside two days; override `TRAIN_TIME` only when
explicitly replanning the deadline.

The fixed 2026-05-28 smoke result selected `ada6000_qlora4_8`: answer smoke
job `64775` completed 48 samples in `18.10s`, and dual smoke job `64777`
completed 48 samples in `18.76s`. The full transfer jobs are tracked in
`results/job_manifest.md`.

Final 2026-05-28 outcome: the full T0/T1/T2 matrix completed by `19:55 CST`,
well inside the two-day deadline. Training used `ada6000_qlora4_8`; the final
straggler eval (`cepo_answer_dpo` on CEPO supported) was rerun on 4x A100 as
job `64807` after the L40S/ADA6000 attempts projected too slowly. The run
preserves short-answer accuracy but does not meet the +20 point 32B transfer
criterion:

| Model | COCO | GQA | Hard COCO | Supported acc. | Wrong-evidence rejection | Relation-stress rejection |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Base | 95.7 | 76.6 | 93.1 | 91.8 | 24.5 | 31.7 |
| CEPO Answer-DPO | 95.9 | 76.7 | 93.8 | 93.5 | 23.8 | 27.1 |
| CEPO-Dual-2k | 95.9 | 76.6 | 93.8 | 93.0 | 24.5 | 31.7 |

CEPO-Dual-2k is only `+0.8` points over CEPO Answer-DPO on wrong-evidence
rejection. Keep this as an appendix/limitation result: the 7B controlled study
still supports the main CEPO-Probe conclusion, while the 32B QLoRA transfer
does not independently reproduce the large answer-vs-evidence separation.

Result files:

```text
v2/tasks/backbone-transfer-experiments/results/
  job_manifest.md
  metrics.csv
  transfer_summary.md
  failure_notes.md
```

## Metrics

Report the same quantities used in the 7B paper:

- COCO / GQA / Hard COCO accuracy and FPR/FNR;
- BEM recovery;
- CEPO supported accuracy;
- CEPO wrong-evidence rejection;
- object / attribute / relation wrong-evidence rejection;
- relation-stress overall, subject/object-swap rejection, left/right-reversal
  rejection, and false-accept rate;
- JSON-object rate, scored-output rate, and parse-failure rate.

External POPE/AMBER evaluation is optional for the first 32B pass. Run it only
if T1/T2 preserves short-answer metrics and the paper needs an additional
sanity check.

## Acceptance Criteria

The transfer result supports the paper if:

- Qwen2.5-VL-32B CEPO-Dual-2k improves wrong-evidence rejection over 32B
  CEPO Answer-DPO by at least +20 points;
- 32B CEPO-Dual-2k does not reduce COCO, GQA, or Hard COCO accuracy by more
  than 1 point relative to 32B CEPO Answer-DPO;
- relation-stress still shows subject/object swaps as weaker than simple
  left/right reversals, or the paper updates the relation-bottleneck wording;
- parse failure remains too small to explain the evidence-probe difference.

If the 32B result weakens or reverses the 7B pattern, do not hide it. Keep the
main paper as a 7B controlled diagnostic study and report the 32B mismatch in
the appendix or limitations.

## Stop Rule

Stop after T0/T1/T2 if the direction matches the 7B conclusion. Do not launch a
larger model-size sweep unless a reviewer or instructor explicitly asks for
more breadth. The paper goal remains a simple, rigorous CVPR-style submission,
not a large benchmark paper.
