# Backbone Transfer Job Manifest

Created: 2026-05-28

## Fixed Setting

- Training profile: `ada6000_qlora4_8`
- Training method: 4-bit bitsandbytes QLoRA, LoRA-DPO, ZeRO-2
- Full-train batch setting: `per_device_train_batch_size=2`,
  `gradient_accumulation_steps=4`
- Eval partitions: `A100,L40S,ADA6000`
- Eval GPUs per job: 4
- Final status: full T0/T1/T2 matrix completed on 2026-05-28 at `19:55 CST`

## Smoke Jobs

| Job | Target | Profile | State | Train runtime | Samples/sec | Decision |
| --- | --- | --- | --- | ---: | ---: | --- |
| `64768` | answer | `rtx4090_z2_4` | failed OOM | n/a | n/a | Escalate |
| `64769` | answer | `rtx4090_z2_8` | failed OOM | n/a | n/a | Escalate |
| `64770` | answer | `l40s_z2_8` | failed OOM | n/a | n/a | Escalate |
| `64772` | answer | `ada6000_z3_8` | completed | `234.47s` | `0.034` | Fits but too slow |
| `64775` | answer | `ada6000_qlora4_8` | completed | `18.10s` | `2.652` | Selected |
| `64777` | dual | `ada6000_qlora4_8` | completed | `18.76s` | `2.559` | Selected |

## Full Jobs

Submitted with:

```bash
PROFILE=ada6000_qlora4_8 \
EVAL_PARTITION=A100,L40S,ADA6000 \
EVAL_GPUS=4 \
EVAL_MEM=320G \
EVAL_TIME=12:00:00 \
bash experiments/slurm/submit_qwen25vl32b_backbone_transfer.sh full
```

| Job | Role | Dependency |
| --- | --- | --- |
| `64778` | T1 32B CEPO Answer-DPO train | none |
| `64779` | T2 32B CEPO-Dual-2k train | none |
| `64780` | T0 base eval: COCO heldout | none |
| `64783` | T0 base eval: GQA simple | none |
| `64786` | T0 base eval: hard COCO | none |
| `64789` | T0 base eval: base-error mined | none |
| `64792` | T0 base eval: CEPO supported | none |
| `64795` | T0 base eval: CEPO wrong evidence | none |
| `64798` | T0 base eval: relation stress | none |
| `64781`, `64784`, `64787`, `64790`, `64793`, `64796`, `64799` | T1 adapter evals | after `64778` |
| `64782`, `64785`, `64788`, `64791`, `64794`, `64797`, `64800` | T2 adapter evals | after `64779` |

## Completion Notes

- T1 training job `64778` completed in `00:42:39`.
- T2 training job `64779` completed in `00:54:38`.
- The original T1 CEPO-supported eval job `64793` on L40S was cancelled after
  `01:06:05` because it projected too slowly and had not flushed any output.
- Retry jobs `64803`/`64804`/`64805` were cancelled during evaluation-speed
  triage. `64806` was a 16-sample A100 speed check and completed in `00:02:20`.
- Final T1 CEPO-supported eval job `64807` completed on A100 in `01:08:43`,
  producing 600 generations and `support_accuracy=93.5%`.
- All planned metrics are present in `transfer_summary.md` and `metrics.csv`.

Final summary command:

```bash
python scripts/eval/summarize_qwen25vl32b_backbone_transfer.py
```
