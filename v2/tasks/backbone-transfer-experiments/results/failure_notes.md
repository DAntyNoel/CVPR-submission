# Backbone Transfer Failure Notes

## 2026-05-28 15:50 CST: 4x RTX4090 ZeRO-2 Smoke

- Job: `64768`
- Profile: `rtx4090_z2_4`
- Config:
  `experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_answer_dpo_seed42_zero2.yaml`
- Outcome: failed during model weight loading before the first training step.
- Failure: CUDA OOM on all four RTX4090 ranks while loading 32B shards. The log
  reports each GPU at roughly `23.44 / 23.53 GiB` in use and failing on an
  additional `270 MiB` allocation.
- Decision: 4x RTX4090 ZeRO-2 is not viable for Qwen2.5-VL-32B DPO. Escalate
  to 8x RTX4090 smoke next, then 8x L40S / 8x ADA6000 if the 4090 profile still
  cannot load or is too slow for the two-day result deadline.

## 2026-05-28 15:54 CST: 8x RTX4090 ZeRO-2 Smoke

- Job: `64769`
- Profile: `rtx4090_z2_8`
- Config:
  `experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_answer_dpo_seed42_zero2.yaml`
- Outcome: failed during model weight loading before the first training step.
- Failure: CUDA OOM on RTX4090 ranks with each GPU at roughly
  `23.43 / 23.53 GiB` and failing on an additional `270 MiB` allocation.
- Interpretation: increasing RTX4090 count does not solve this ZeRO-2 load
  path because each rank still needs a full model replica.
- Decision: move to higher-memory GPUs. Test 8x L40S next; if 48GB-class GPUs
  still fail under ZeRO-2, switch the fixed training template to stronger
  sharding for the two-day result target.

## 2026-05-28 15:57 CST: 8x L40S ZeRO-2 Smoke

- Job: `64770`
- Profile: `l40s_z2_8`
- Config:
  `experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_answer_dpo_seed42_zero2.yaml`
- Outcome: failed during model weight loading before the first training step.
- Failure: CUDA OOM around shard `12/18`; each L40S rank reports roughly
  `44.37 / 44.40 GiB` in use and fails on an additional `270 MiB` allocation.
- Interpretation: 48GB-class GPUs are still insufficient for the ZeRO-2 path,
  because the full 32B model replica must fit on each rank before DPO starts.
- Decision: stop testing ZeRO-2 for this backbone and switch the fixed 32B
  training template to ZeRO-3 strong sharding, starting with 8x L40S smoke.

## 2026-05-28 16:15 CST: 8x ADA6000 ZeRO-3 Smoke

- Job: `64772`
- Profile: `ada6000_z3_8`
- Config:
  `experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_answer_dpo_seed42_zero3.yaml`
- Outcome: completed. The BF16 ZeRO-3 path loads and trains the 32B model.
- Speed: `train_runtime=234.47s` for one optimizer step over 8 samples.
- Projection: full Answer-DPO and Dual-DPO would require roughly 750 and 1000
  microsteps respectively at batch size 1, which risks missing the two-day
  result deadline even before full evaluation.
- Decision: keep ZeRO-3 as a memory fallback, but test a faster 4-bit QLoRA
  route before launching the full transfer.

## 2026-05-28 16:28 CST: 8x ADA6000 QLoRA4 Answer Smoke

- Job: `64775`
- Profile: `ada6000_qlora4_8`
- Config:
  `experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_answer_dpo_seed42_qlora4.yaml`
- Outcome: completed. The 4-bit bitsandbytes + ZeRO-2 path loads and trains.
- Speed: `train_runtime=18.10s`, `train_samples_per_second=2.652` for 48
  samples across 3 smoke steps.
- Decision: QLoRA4 is fast enough for the two-day deadline. Verify the dual
  dataset with the same setting before launching the full T1/T2 transfer.

## 2026-05-28 16:32 CST: 8x ADA6000 QLoRA4 Dual Smoke

- Job: `64777`
- Profile: `ada6000_qlora4_8`
- Config:
  `experiments/llamafactory_configs/smoke_qwen25vl32b_cepo_dual_dpo_seed42_qlora4.yaml`
- Outcome: completed.
- Speed: `train_runtime=18.76s`, `train_samples_per_second=2.559` for 48
  samples across 3 smoke steps.
- Decision: fix the full 32B transfer template to `ada6000_qlora4_8`, with
  `per_device_train_batch_size=2`, `gradient_accumulation_steps=4`, and
  higher-memory eval partitions (`A100,L40S,ADA6000`).

## 2026-05-28 18:31 CST: T1 CEPO-Supported Eval Triage

- Original job: `64793`
- Eval: `cepo_answer_dpo` on `cepo_evidence_probe`
- Outcome: cancelled after `01:06:05` on L40S because it projected too slowly
  and had not flushed any output.
- Follow-up: ADA6000 retry jobs `64803`, `64804`, and `64805` were cancelled
  during triage. The script was updated to disable Transformers
  `generate()` auto-compile by default and to flush JSONL output after each
  row for future monitoring.
- Speed check: A100 16-sample job `64806` completed in `00:02:20`.
- Final run: A100 full job `64807` completed 600 rows in `01:08:43` with
  `support_accuracy=0.935`, `invalid_json_rate=0.0`, and
  `parse_failure_rate=0.0`.
- Decision: for remaining 32B inference stragglers, prefer 4x A100 over
  L40S/ADA6000 when a two-day result deadline matters.
