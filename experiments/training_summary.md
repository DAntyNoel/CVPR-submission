# Training Summary

Updated: 2026-05-27

## Slurm Jobs

| Method | Job ID | Partition | State | ExitCode | Start | End | Elapsed |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Answer-DPO | 64167 | A100 | COMPLETED | 0:0 | 2026-05-26 17:52:10 | 2026-05-26 18:51:03 | 00:58:53 |
| Evidence-Hint DPO | 64168 | RTX4090 | COMPLETED | 0:0 | 2026-05-26 17:52:26 | 2026-05-27 07:17:55 | 13:25:29 |

There are no current RUNNING or PENDING Slurm jobs for user `fhshao` at the
time of this check.

## Output Completeness

Both trained LoRA output directories contain the expected final artifacts:

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

The unified eval entrypoint dry-runs successfully for both adapters:

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

Proceed to D: run Base Instruct, Answer-DPO, and Evidence-Hint DPO evaluation
with `experiments/slurm/eval_vlm_object_hallucination.slurm`.
