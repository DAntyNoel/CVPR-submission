# Balanced Hard Evidence-DPO Results

Updated: 2026-05-27

## Run Summary

Training job 64438 completed with exit code 0.

| Field | Value |
| --- | ---: |
| Rows | 5,000 |
| Steps | 157 |
| Runtime | 930.2164 s |
| Train loss | 0.3106 |
| Samples/sec | 5.375 |
| Steps/sec | 0.169 |

Adapter:

```text
outputs/llamafactory/qwen25vl7b_balanced_hard_evidence_dpo_zero2/
```

The output directory contains the expected LoRA artifacts, including
`adapter_config.json`, `adapter_model.safetensors`, `trainer_state.json`,
`train_results.json`, and tokenizer/preprocessor sidecar files.

## Evaluation Results

Eval jobs 64453-64456 completed with exit code 0. All results use
`OUTPUT_VARIANT=balanced_hard` and the completed adapter above.

| Eval | Method | N | Acc | F1 | FPR | FNR | Yes | Other |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| COCO held-out | Answer-DPO | 1000 | 0.961 | 0.960 | 0.018 | 0.060 | 0.479 | 0.000 |
| COCO held-out | Naive Evidence-Hint DPO | 1000 | 0.961 | 0.960 | 0.016 | 0.062 | 0.477 | 0.000 |
| COCO held-out | Balanced Hard Evidence-DPO | 1000 | 0.963 | 0.962 | 0.016 | 0.058 | 0.479 | 0.000 |
| GQA simple | Answer-DPO | 1000 | 0.768 | 0.748 | 0.152 | 0.312 | 0.420 | 0.000 |
| GQA simple | Naive Evidence-Hint DPO | 1000 | 0.766 | 0.743 | 0.144 | 0.324 | 0.410 | 0.000 |
| GQA simple | Balanced Hard Evidence-DPO | 1000 | 0.769 | 0.746 | 0.142 | 0.320 | 0.411 | 0.000 |
| Hard COCO | Answer-DPO | 1000 | 0.950 | 0.949 | 0.040 | 0.060 | 0.490 | 0.000 |
| Hard COCO | Naive Evidence-Hint DPO | 1000 | 0.946 | 0.945 | 0.038 | 0.070 | 0.484 | 0.000 |
| Hard COCO | Balanced Hard Evidence-DPO | 1000 | 0.945 | 0.944 | 0.040 | 0.070 | 0.485 | 0.000 |
| Base-error mined | Answer-DPO | 527 | 0.063 | 0.115 | 0.992 | 0.921 | 0.292 | 0.000 |
| Base-error mined | Naive Evidence-Hint DPO | 527 | 0.030 | 0.052 | 0.984 | 0.965 | 0.256 | 0.000 |
| Base-error mined | Balanced Hard Evidence-DPO | 527 | 0.044 | 0.077 | 0.984 | 0.948 | 0.269 | 0.000 |

## Reading

Balanced Hard Evidence-DPO partially improves the original failure mode but
does not solve it strongly enough to replace Answer-DPO in the main paper.

Positive signals:

- COCO held-out improves over Answer-DPO by 0.2 accuracy points while keeping
  lower FPR than Answer-DPO and lower FNR than naive Evidence-Hint DPO.
- GQA simple has the best accuracy among the three compared rows and the lowest
  FPR, though its F1 remains slightly below Answer-DPO.
- Base-error-mined recovery improves over naive Evidence-Hint DPO.

Negative signals:

- Hard COCO remains below Answer-DPO on Acc/F1 and does not preserve a lower
  FPR than Answer-DPO.
- Base-error-mined recovery is still below Answer-DPO.
- The rescue run still looks like a trade-off rather than a stable dominance
  result.

Conclusion: this is a useful ablation and a partial rescue, but the current
paper should still keep the diagnostic/Plan-B framing unless a stronger
variant improves Hard COCO and Base-error-mined recovery at the same time.
