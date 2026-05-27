# Training Summary

Updated: 2026-05-27

## Slurm Jobs

### Mixed COCO+GQA Main Jobs

These are the jobs to use for the final mixed-data main table.

| Method | Job ID | Partition | State | ExitCode | Start | End | Elapsed |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Answer-DPO | 64200 | A100 | RUNNING | 0:0 | 2026-05-27 09:07:07 | Unknown | 00:00:11 at status check |
| Evidence-Hint DPO | 64201 | RTX4090 | RUNNING | 0:0 | 2026-05-27 09:07:10 | Unknown | 00:00:08 at status check |

Mixed training was launched from the current 5,000-row COCO+GQA data export:

```text
experiments/llamafactory_data/cvpr_answer_dpo.json
experiments/llamafactory_data/cvpr_evidence_hint_dpo.json
```

The mixed adapters will be written to separate output directories so the old
COCO-only preliminary adapters remain identifiable:

```text
outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/
outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo/
```

Early log checks for both mixed jobs reached the LLaMA-Factory training loop
with `Num examples = 5,000` and `Total optimization steps = 157`.

### COCO-Only Preliminary Jobs

Jobs 64167 and 64168 were trained before the 2026-05-27 mixed COCO+GQA data
refresh. Treat them as COCO-only preliminary/auxiliary runs only; do not use
them in the mixed-data main table.

| Method | Job ID | Partition | State | ExitCode | Start | End | Elapsed |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Answer-DPO | 64167 | A100 | COMPLETED | 0:0 | 2026-05-26 17:52:10 | 2026-05-26 18:51:03 | 00:58:53 |
| Evidence-Hint DPO | 64168 | RTX4090 | COMPLETED | 0:0 | 2026-05-26 17:52:26 | 2026-05-27 07:17:55 | 13:25:29 |

## Output Completeness

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
COCO-only adapters when supplied directly. The default `answer_dpo` and
`evidence_hint_dpo` registry entries now point to the mixed adapter directories,
so their dry-run should be repeated after jobs 64200 and 64201 finish.

```bash
python scripts/eval/run_vlm_inference.py \
  --model-key answer_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --dry-run

python scripts/eval/run_vlm_inference.py \
  --model-key evidence_hint_dpo \
  --eval data/eval/coco_heldout_object_existence.jsonl \
  --dry-run
```

## Train Metrics

Mixed train metrics are pending completion of jobs 64200 and 64201.

COCO-only preliminary metrics:

| Method | Epoch | Steps | Train Loss | Runtime (s) | Runtime | Samples/sec | Steps/sec |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Answer-DPO | 1.0 | 157 | 0.2791 | 3449.3963 | 00:57:29 | 1.450 | 0.046 |
| Evidence-Hint DPO | 1.0 | 157 | 0.1025 | 48163.7926 | 13:22:44 | 0.104 | 0.003 |

Evidence-Hint DPO is much slower because its chosen/rejected responses include
the extra evidence hint text, increasing sequence length and DPO compute cost.
The job still completed within the 1-day wall-clock limit and wrote the final
adapter.

## Log Health

A keyword scan across the Answer-DPO and Evidence-Hint DPO Slurm logs and
trainer logs found no `Traceback`, `RuntimeError`, CUDA OOM, `nan`, or `inf`
training failures. The only matched line was the normal informational message
`Using torch SDPA for faster training and inference`.

## Next Step

Wait for jobs 64200 and 64201 to complete, then record mixed train metrics,
dry-run adapter loading from the mixed output directories, and proceed to D:
run Base Instruct, mixed Answer-DPO, and mixed Evidence-Hint DPO evaluation
with `experiments/slurm/eval_vlm_object_hallucination.slurm`.
