# Training Summary

Updated: 2026-05-27

## Slurm Jobs

### CEPO-Probe / CEPO-Dual

Updated: 2026-05-28

The CEPO-Dual follow-up is complete and is the selected third group for the
CEPO-Probe benchmark paper. The final adapters are present:

```text
outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2/
outputs/llamafactory/qwen25vl7b_cepo_dual_dpo_zero2/
outputs/llamafactory/qwen25vl7b_cepo_latent_dpo_zero2/
```

Training metrics:

| Method | Epoch | Train Loss | Runtime (s) | Samples/sec | Steps/sec |
| --- | ---: | ---: | ---: | ---: | ---: |
| CEPO Answer-DPO | 1.0 | 0.3367 | 943.3365 | 6.360 | 0.199 |
| CEPO-Latent | 1.0 | 0.1327 | 1178.0651 | 5.093 | 0.160 |
| CEPO-Dual | 1.0 | 0.3298 | 1275.9316 | 6.270 | 0.196 |

CEPO-Latent remains a diagnostic negative result for short-answer transfer.
CEPO-Dual is used in the main benchmark paper because it keeps short-answer
performance near CEPO Answer-DPO while improving wrong-evidence rejection from
0.343 to 0.702.

### Balanced Hard Input-Side Evidence DPO

This run follows `tasks/input-side-evidence-main-method/README.md` and is the
completed Input-Side Evidence main-method rescue. It uses 5,500 balanced-hard
input-side DPO rows, Qwen2.5-VL-7B, LoRA-DPO, and ZeRO-2. Responses remain
plain short answers; evidence is only placed in the user prompt.

| Method | Job ID | Partition | State | ExitCode | Elapsed | Notes |
| --- | ---: | --- | --- | --- | --- | --- |
| Balanced Hard Input-Side Evidence DPO | 64443 | RTX4090 | COMPLETED | 0:0 | 00:18:19 | 5,500 rows; input-side visual cues; plain chosen/rejected responses. |

After-ok eval jobs also completed with exit code 0: 64444 for COCO held-out,
64445 for GQA simple, 64446 for Hard COCO, and 64447 for the Base-error-mined
diagnostic. External sanity jobs 64457-64460 completed for POPE
random/popular/adversarial and AMBER discriminative.

### Phase-2 Method Variants

The first Phase-2 round keeps the same 5k mixed COCO/GQA split, Qwen2.5-VL-7B
backbone, LoRA-DPO recipe, and ZeRO-2 setup. It changes only the preference
format, so these runs are diagnostic side experiments rather than replacements
for the three-group main table.

| Method | Job ID | Partition | State | ExitCode | Elapsed | Notes |
| --- | ---: | --- | --- | --- | --- | --- |
| Evidence-Only DPO | 64302 | RTX4090 | COMPLETED | 0:0 | 00:16:05 | Chosen/rejected share the answer text; evidence consistency differs. |
| Input-Side Evidence DPO | 64303 | RTX4090 | COMPLETED | 0:0 | 00:16:13 | Supported evidence is moved into the user prompt; responses stay plain. |
| Chosen-Only Evidence DPO | 64304 | RTX4090 | COMPLETED | 0:0 | 00:17:25 | Supported evidence is appended only to the chosen response. |

After-ok eval jobs also completed with exit code 0: jobs 64305-64308 for
Evidence-Only, 64309-64312 for Input-Side, and 64313-64316 for Chosen-Only.
All Phase-2 eval outputs use `OUTPUT_VARIANT=phase2`.

### 10k Mixed Scale-Up Diagnostic

The 10k scale-up is a diagnostic for whether data size changes the
Evidence-Hint trend, not a replacement for the 5k main table. It keeps the same
three method groups and uses separate data, adapters, and `mixed10k` eval
outputs.

| Method | Job ID | State | Dependency | Notes |
| --- | ---: | --- | --- | --- |
| Data prep | 64272 | CANCELLED | none | First attempt excluded both held-out and base-error-mining COCO image pools; local COCO subset only yielded 4,586 / 6,000 pairs. |
| Answer-DPO | 64273 | CANCELLED | afterok:64272 | Cancelled with first data attempt. |
| Evidence-Hint DPO | 64274 | CANCELLED | afterok:64272 | Cancelled with first data attempt. |
| Data prep | 64283 | CANCELLED | none | Second attempt was replaced before export so Phase-2 DPO sidecar files use mixed10k-specific names instead of overwriting defaults. |
| Answer-DPO | 64284 | CANCELLED | afterok:64283 | Cancelled with second data attempt. |
| Evidence-Hint DPO | 64285 | CANCELLED | afterok:64283 | Cancelled with second data attempt. |
| Data prep | 64293 | CANCELLED | none | Third attempt used the correct filenames but single-threaded GQA/VG downloading was too slow. |
| Answer-DPO | 64294 | CANCELLED | afterok:64293 | Cancelled with third data attempt. |
| Evidence-Hint DPO | 64295 | CANCELLED | afterok:64293 | Cancelled with third data attempt. |
| Data prep | 64321 | CANCELLED | none | Fourth attempt used concurrent downloading but still targeted all 5,000 GQA/VG images; replaced after reaching 1,600 / 5,000 with 0 failed downloads. |
| Answer-DPO | 64322 | CANCELLED | afterok:64321 | Cancelled with fourth data attempt. |
| Evidence-Hint DPO | 64323 | CANCELLED | afterok:64321 | Cancelled with fourth data attempt. |
| Data prep | 64369 | COMPLETED | none | Wrote 6,000 COCO + 4,000 GQA pairs, 10k DPO exports, audit summary, leakage report, and LLaMA-Factory registry. GQA/VG image prep finished 4,300 / 4,300 with 0 failed downloads. |
| Answer-DPO | 64370 | CANCELLED | afterok:64369 | Old ZeRO-3 10k Answer-DPO job; reached the LLaMA-Factory train loop with 10,000 examples and 313 steps, but was cancelled because it was too slow on RTX4090. |
| Evidence-Hint DPO | 64371 | COMPLETED | afterok:64369 | ZeRO-2 10k Evidence-Hint DPO training completed 313 / 313 steps in 33:51. |
| Answer-DPO | 64397 | COMPLETED | none | Replacement ZeRO-2 10k Answer-DPO job using `A100,L40S,ADA6000`; completed 313 / 313 steps in 30:50 after 64370 was cancelled. |

The ZeRO-2 replacement solved the Answer-DPO throughput issue: the cancelled
ZeRO-3 job 64370 was around one step per five minutes, while job 64397 ran at
roughly five to six seconds per step on ADA6000 and completed normally.

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

The Balanced Hard Input-Side Evidence DPO output directory contains the
expected final artifacts:

```text
outputs/llamafactory/qwen25vl7b_input_side_main_balanced_hard_dpo_zero2/
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

Phase-2 train metrics:

| Method | Epoch | Steps | Train Loss | Runtime (s) | Runtime | Samples/sec | Steps/sec |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Evidence-Only DPO | 1.0 | 157 | 0.1431 | 885.6483 | 00:14:46 | 5.646 | 0.177 |
| Input-Side Evidence DPO | 1.0 | 157 | 0.3334 | 895.0952 | 00:14:55 | 5.586 | 0.175 |
| Chosen-Only Evidence DPO | 1.0 | 157 | 0.1420 | 962.4549 | 00:16:02 | 5.195 | 0.163 |

Balanced Hard Input-Side train metrics:

| Method | Epoch | Steps | Train Loss | Runtime (s) | Runtime | Samples/sec | Steps/sec |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Balanced Hard Input-Side Evidence DPO | 1.0 | 172 | 0.2708 | 1029.7037 | 00:17:10 | 5.341 | 0.167 |

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

Completed mixed-eval metrics are tracked in:

```text
experiments/eval_summary.md
```

Current result: COCO held-out Base Acc 0.959, mixed Answer-DPO Acc
0.961, and ZeRO-2 Evidence-Hint Acc 0.961; GQA simple Base Acc 0.764, mixed
Answer-DPO Acc 0.768, and ZeRO-2 Evidence-Hint Acc 0.766. Evidence-style prompt
results are complete: Base COCO Acc 0.955, Base GQA Acc 0.768, Answer-DPO COCO
Acc 0.956, Answer-DPO GQA Acc 0.766, ZeRO-2 Evidence-Hint COCO Acc 0.955, and
ZeRO-2 Evidence-Hint GQA Acc 0.767. Hard COCO Base Acc is 0.944, mixed
Answer-DPO Acc is 0.950, and ZeRO-2 Evidence-Hint Acc is 0.946. Base-error
mining is also complete: Answer-DPO recovery is 0.063 and ZeRO-2 Evidence-Hint
recovery is 0.030 on the 527-row locked diagnostic set.

Balanced Hard Input-Side Evidence DPO also completed as job 64443 with four
main evals and four external sanity evals. It improves COCO held-out Acc to
0.966 and Base-error recovery to 0.120, but Hard COCO FPR rises to 0.048.
These results support the diagnostic Plan B reading rather than a strong
positive Evidence-Hint or Input-Side claim.
