# Training Summary

Updated: 2026-05-27

## Slurm Jobs

### Mixed COCO+GQA Main Jobs

These are the jobs to use for the final mixed-data main table.

| Method | Job ID | Partition | State | ExitCode | Start | End | Elapsed |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Answer-DPO | 64200 | A100 | COMPLETED | 0:0 | 2026-05-27 09:07:07 | 2026-05-27 10:05:33 | 00:58:26 |
| Evidence-Hint DPO | 64252 | RTX4090 | COMPLETED | 0:0 | 2026-05-27 14:13:18 | 2026-05-27 14:30:31 | 00:17:13 |
| Evidence-Hint DPO old ZeRO-3 | 64201 | RTX4090 | CANCELLED | 0:0 | 2026-05-27 09:07:10 | 2026-05-27 14:46:46 | 05:39:36 |

Mixed training was launched from the current 5,000-row COCO+GQA data export:

```text
experiments/llamafactory_data/cvpr_answer_dpo.json
experiments/llamafactory_data/cvpr_evidence_hint_dpo.json
```

The mixed adapters will be written to separate output directories so the old
COCO-only preliminary adapters remain identifiable:

```text
outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2/
```

Early log checks for both mixed jobs reached the LLaMA-Factory training loop
with `Num examples = 5,000` and `Total optimization steps = 157`. Job 64200
has completed and written the final mixed Answer-DPO adapter. Job 64201
underused RTX4090 memory, had no useful checkpoint before the final step, and
was cancelled after ZeRO-2 job 64252 completed. Job 64252 is now the default
mixed Evidence-Hint DPO run; it initialized at about 15.6GB allocated GPU
memory and trained at about 6s/step.

### COCO-Only Preliminary Jobs

Jobs 64167 and 64168 were trained before the 2026-05-27 mixed COCO+GQA data
refresh. Treat them as COCO-only preliminary/auxiliary runs only; do not use
them in the mixed-data main table.

| Method | Job ID | Partition | State | ExitCode | Start | End | Elapsed |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Answer-DPO | 64167 | A100 | COMPLETED | 0:0 | 2026-05-26 17:52:10 | 2026-05-26 18:51:03 | 00:58:53 |
| Evidence-Hint DPO | 64168 | RTX4090 | COMPLETED | 0:0 | 2026-05-26 17:52:26 | 2026-05-27 07:17:55 | 13:25:29 |

## Output Completeness

The mixed Answer-DPO output directory contains the expected final artifacts:

```text
outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/
```

Required files checked:

- `adapter_config.json`
- `adapter_model.safetensors`
- `trainer_state.json`
- `train_results.json`
- `all_results.json`
- tokenizer/preprocessor sidecar files

The mixed Evidence-Hint DPO output directory contains the expected final
artifacts:

```text
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo_zero2/
```

Required files checked:

- `adapter_config.json`
- `adapter_model.safetensors`
- `trainer_state.json`
- `train_results.json`
- `all_results.json`
- tokenizer/preprocessor sidecar files

The COCO-only preliminary LoRA output directories contain the expected final
artifacts:

```text
outputs/llamafactory/qwen25vl7b_answer_dpo/
outputs/llamafactory/qwen25vl7b_evidence_hint_dpo/
```

Required files checked:

- `adapter_config.json`
- `adapter_model.safetensors`
- `trainer_state.json`
- `train_results.json`
- `all_results.json`
- tokenizer/preprocessor sidecar files

The unified eval entrypoint previously dry-ran successfully for both
COCO-only adapters when supplied directly. The default `answer_dpo` registry
points to the mixed Answer-DPO adapter, and the default `evidence_hint_dpo`
registry now points to the completed ZeRO-2 mixed Evidence-Hint adapter. The
mixed Answer-DPO registry dry-run has passed for both COCO held-out and GQA
simple; the Evidence-Hint dry-run passed on the ZeRO-2 adapter.

```bash
python scripts/eval/run_vlm_inference.py \
  --model-key answer_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --output results/eval/generations/coco_heldout_object_existence/mixed/answer_dpo.jsonl \
  --dry-run

python scripts/eval/run_vlm_inference.py \
  --model-key evidence_hint_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --dry-run
```

## Train Metrics

Mixed train metrics:

| Method | Epoch | Steps | Train Loss | Runtime (s) | Runtime | Samples/sec | Steps/sec |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Answer-DPO | 1.0 | 157 | 0.3722 | 3417.2152 | 00:56:57 | 1.463 | 0.046 |
| Evidence-Hint DPO | 1.0 | 157 | 0.1347 | 950.9633 | 00:15:51 | 5.258 | 0.165 |

COCO-only preliminary metrics:

| Method | Epoch | Steps | Train Loss | Runtime (s) | Runtime | Samples/sec | Steps/sec |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Answer-DPO | 1.0 | 157 | 0.2791 | 3449.3963 | 00:57:29 | 1.450 | 0.046 |
| Evidence-Hint DPO | 1.0 | 157 | 0.1025 | 48163.7926 | 13:22:44 | 0.104 | 0.003 |

The old ZeRO-3 Evidence-Hint run was much slower despite low memory use. ZeRO-2
uses more GPU memory and is now the default Evidence-Hint setting.

## Log Health

A keyword scan across the COCO-only training logs, the completed mixed
Answer-DPO logs, and the completed mixed Evidence-Hint DPO ZeRO-2 logs found no
`Traceback`, `RuntimeError`, CUDA OOM, `nan`, or `inf` training failures. The
only matched line in the earlier COCO-only scan was the normal informational
message `Using torch SDPA for faster training and inference`. Job 64201 was
cancelled intentionally after replacement by job 64252.

## Next Step

Use the completed ZeRO-2 adapter as the default Evidence-Hint DPO adapter.
Normal-prompt eval jobs completed: 64255 COCO held-out Acc 0.961, 64256 GQA
simple Acc 0.766, and 64257 Hard COCO Acc 0.946. Evidence-style prompt jobs
also completed: 64258 COCO held-out Acc 0.955 and 64259 GQA simple Acc 0.767.
The old dependency jobs 64235 to 64239 and 64263 were cancelled along with job
64201.

Completed mixed-eval partial metrics are tracked in:

```text
experiments/eval_summary.md
```

Current partial result: COCO held-out Base Acc 0.959, mixed Answer-DPO Acc
0.961, and ZeRO-2 Evidence-Hint Acc 0.961; GQA simple Base Acc 0.764, mixed
Answer-DPO Acc 0.768, and ZeRO-2 Evidence-Hint Acc 0.766. Evidence-style prompt
results are complete: Base COCO Acc 0.955, Base GQA Acc 0.768, Answer-DPO COCO
Acc 0.956, Answer-DPO GQA Acc 0.766, ZeRO-2 Evidence-Hint COCO Acc 0.955, and
ZeRO-2 Evidence-Hint GQA Acc 0.767. Hard COCO Base Acc is 0.944, mixed
Answer-DPO Acc is 0.950, and ZeRO-2 Evidence-Hint Acc is 0.946.
