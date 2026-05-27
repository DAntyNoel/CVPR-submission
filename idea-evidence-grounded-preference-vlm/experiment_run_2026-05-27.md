# CEPO Run Log

Date: 2026-05-27

## Prepared Artifacts

Local lightweight steps completed:

```text
data/processed/cepo/claim_evidence_canonical.jsonl  6,000 rows
data/processed/cepo/answer_dpo_train.jsonl          6,000 rows
data/processed/cepo/cepo_latent_dpo_train.jsonl     6,000 rows
experiments/llamafactory_data_cepo/dataset_info.json
data/eval/cepo_evidence_probe.jsonl                 600 rows
data/eval/cepo_wrong_evidence_probe.jsonl           400 rows
```

Data mix:

| Slice | Rows |
| --- | ---: |
| COCO object existence | 2,000 |
| GQA attribute | 1,500 |
| GQA left/right relation | 1,500 |
| Wrong-evidence negatives | 1,000 |

Checks:

```text
13_check_cepo_data.py: no blocking CEPO data quality errors
train/eval image overlap: 0
Answer-DPO identical chosen/rejected rows: 0
CEPO same-answer wrong-evidence rows: 1,000
```

## Submitted Slurm Jobs

Training:

| Job | Role |
| ---: | --- |
| 64465 | CEPO Answer-DPO, Qwen2.5-VL-7B, LoRA-DPO, ZeRO-2 |
| 64466 | CEPO-Latent, Qwen2.5-VL-7B, LoRA-DPO, ZeRO-2 |

Short-answer evals:

| Jobs | Eval family |
| --- | --- |
| 64467-64478 | COCO held-out, GQA simple, Hard COCO, Base-error-mined |
| 64479-64490 | POPE random/popular/adversarial and AMBER discriminative |

Evidence-probe evals:

| Jobs | Eval family |
| --- | --- |
| 64491-64493 | Supported evidence probe |
| 64494-64496 | Wrong-evidence rejection probe |

Adapter eval jobs use `afterok` dependencies on the corresponding training
job. Base eval jobs have no adapter dependency.

Status snapshot at 2026-05-27 23:18 Asia/Shanghai:

```text
64465 CEPO Answer-DPO train: RUNNING
64466 CEPO-Latent train: RUNNING
64467/64470/64473/64476 Base internal evals: COMPLETED
64479/64482/64485/64488 Base external evals: RUNNING
64491/64494 Base evidence-probe evals: RUNNING
Adapter evals: PENDING on training afterok dependencies
```

## Expected Conclusions

Most likely paper conclusion:

```text
Claim-evidence preference improves explicit evidence behavior, especially
wrong-evidence rejection, while transfer to short-answer hallucination is
expected to be smaller and diagnostic rather than a sweeping win.
```

Expected pattern:

| Metric family | Expected outcome |
| --- | --- |
| Evidence-probe | CEPO-Latent should beat Answer-DPO on support accuracy and wrong-evidence rejection. |
| GQA relation/attribute | CEPO-Latent may improve one of relation or attribute subgroups because training exposes typed claims. |
| COCO/Hard COCO FPR | CEPO-Latent should not exceed Answer-DPO FPR; a small FPR reduction is plausible. |
| FNR/yes rate | Watch for over-correction. A lower FPR with much higher FNR should be framed as a trade-off, not a win. |
| Base-error recovery | Expected to be modest; beating V1 Evidence-Hint is enough for a diagnostic claim. |
| POPE/AMBER | Should remain close to Answer-DPO; a clear drop would suggest format overfitting. |

If short-answer metrics are neutral but evidence-probe improves, use the Plan B
claim from the project plan:

```text
Claim-evidence preference teaches verifiable evidence behavior, but latent
transfer to short yes/no hallucination remains limited.
```

If CEPO also improves short-answer FPR or relation/attribute accuracy without
raising FNR, the stronger Plan A conclusion is justified:

```text
Claim-evidence preference provides a stronger grounding signal than
answer-only preference, improving evidence consistency without introducing
over-refusal.
```
