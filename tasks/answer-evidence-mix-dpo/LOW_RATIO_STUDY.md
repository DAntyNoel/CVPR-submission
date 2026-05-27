# Low Evidence Ratio Study

## Question

The 30% Answer-Evidence Mix run was designed as a low-cost rescue after
Evidence-Hint DPO showed a repeated false-positive/false-negative trade-off.
The run did help on COCO held-out and GQA, but it hurt Hard COCO and did not
recover the base-error-mined diagnostic set. This memo studies whether lowering
the response-side evidence ratio is likely to improve the trade-off.

## Completed 30% Mix Run

```text
train job: 64448
eval jobs: 64449 COCO, 64450 GQA, 64451 Hard COCO, 64452 Base-error
adapter: outputs/llamafactory/qwen25vl7b_answer_evidence_mix_dpo_zero2/
result variant: results/eval/generations/<eval_name>/answer_evidence_mix/
```

The training run completed 1 epoch over 5,000 examples with 157 optimization
steps and `train_loss=0.3820`. The exported data used 3,500 plain Answer-DPO
rows and 1,500 Evidence-Hint rows.

## Ratio Trend From Existing Points

The available points are not a perfect dense sweep, but they are enough to
diagnose direction:

- `0%` evidence is the 5k mixed Answer-DPO run.
- `30%` evidence is the new Answer-Evidence Mix DPO run.
- `100%` evidence is approximated by the 5k mixed Evidence-Hint DPO ZeRO-2 run.

| Eval | Ratio proxy | Acc | F1 | FPR | FNR | yes rate | Confusion tp/fp/tn/fn |
|---|---:|---:|---:|---:|---:|---:|---|
| COCO | 0% | 0.961 | 0.960 | 0.018 | 0.060 | 0.479 | 470/9/491/30 |
| COCO | 30% | 0.962 | 0.961 | 0.016 | 0.060 | 0.478 | 470/8/492/30 |
| COCO | 100% | 0.961 | 0.960 | 0.016 | 0.062 | 0.477 | 469/8/492/31 |
| GQA | 0% | 0.768 | 0.748 | 0.152 | 0.312 | 0.420 | 344/76/424/156 |
| GQA | 30% | 0.771 | 0.750 | 0.146 | 0.312 | 0.417 | 344/73/427/156 |
| GQA | 100% | 0.766 | 0.743 | 0.144 | 0.324 | 0.410 | 338/72/428/162 |
| Hard COCO | 0% | 0.950 | 0.949 | 0.040 | 0.060 | 0.490 | 470/20/480/30 |
| Hard COCO | 30% | 0.942 | 0.941 | 0.044 | 0.072 | 0.486 | 464/22/478/36 |
| Hard COCO | 100% | 0.946 | 0.945 | 0.038 | 0.070 | 0.484 | 465/19/481/35 |
| Base-error | 0% | 0.063 | 0.115 | 0.992 | 0.921 | 0.292 | 32/122/1/372 |
| Base-error | 30% | 0.042 | 0.073 | 0.984 | 0.950 | 0.268 | 20/121/2/384 |
| Base-error | 100% | 0.030 | 0.052 | 0.984 | 0.965 | 0.256 | 14/121/2/390 |

## Diagnosis

The 30% mix is not failing because the model visibly emits evidence during
short-answer evaluation. All four evals have `evidence_cue_rate=0`, `other=0`,
and one-word average generations. The damage is therefore decision-boundary
shift, not output-format leakage.

The evidence rows behave like a conservative regularizer. On COCO and GQA this
is useful: FPR drops without increasing FNR. On Hard COCO and Base-error, the
same shift reduces yes recall and does not recover enough true negatives to
compensate. This means the useful evidence signal is real but too strong or too
noisy when applied to 30% of all rows.

The base-error diagnostic remains the clearest warning. It is dominated by
examples where the base model was already wrong. Lowering the evidence ratio may
recover some Answer-DPO behavior, but ratio tuning alone is unlikely to solve
that set because both 30% and 100% mostly increase false negatives there.

## Candidate Ratios

| Ratio | Role | Expected behavior | Risk |
|---:|---|---|---|
| 10% | Safest conservative regularizer | Best chance to preserve Hard COCO recall | FPR reduction may be too small to narrate |
| 15% | Recommended next run | Keeps half of the 30% evidence signal while moving closer to Answer-DPO | Still may not improve base-error |
| 20% | Backup only | More FPR movement than 15% | More likely to reproduce Hard COCO drop |
| 50% | Do not prioritize | No reason to expect better than 30% given 100% trend | Likely worsens recall and base-error recovery |

The best next single run is `15%`. It is a compromise between keeping the small
COCO/GQA FPR gains and reducing the Hard COCO recall loss. If only one more GPU
run is allowed, 15% is more informative than 10% because it tests whether the
30% run was simply too much evidence, not whether evidence should be nearly
removed.

## Proposed Experiment

Run one additional ratio-ablation model:

```text
Answer-Evidence Mix DPO r015
85% plain Answer-DPO rows
15% Evidence-Hint DPO rows
seed 42
same 5k canonical pairs, Qwen2.5-VL-7B, LoRA-DPO, ZeRO-2
```

Use a separate dataset directory, output directory, model key, and result
variant so the completed 30% run is not overwritten.

Suggested artifact names:

```text
data/processed/answer_evidence_mix_r015_dpo_train.jsonl
experiments/llamafactory_data_answer_evidence_r015/
cvpr_answer_evidence_mix_dpo
outputs/llamafactory/qwen25vl7b_answer_evidence_mix_r015_dpo_zero2/
results/eval/generations/<eval_name>/answer_evidence_mix_r015/
```

The existing exporter already supports this data point:

```bash
python scripts/data/04_export_dpo_formats.py \
  --input data/processed/canonical_pairs_main.jsonl \
  --answer-evidence-mix-output data/processed/answer_evidence_mix_r015_dpo_train.jsonl \
  --answer-evidence-mix-evidence-ratio 0.15 \
  --answer-evidence-mix-seed 42
```

Then convert only through a separate LLaMA-Factory data directory:

```bash
python scripts/experiments/prepare_llamafactory_data.py \
  --answer-evidence-mix-input data/processed/answer_evidence_mix_r015_dpo_train.jsonl \
  --output-dir experiments/llamafactory_data_answer_evidence_r015
```

Because `prepare_llamafactory_data.py` keeps the dataset key stable, the train
config can reuse `dataset: cvpr_answer_evidence_mix_dpo` as long as
`dataset_dir` points to the r015 directory.

## Success Gates

Treat r015 as useful only if it passes most of these gates:

| Eval | Gate |
|---|---|
| COCO held-out | Acc >= 0.961, FPR <= 0.016, FNR <= 0.060 |
| GQA simple | Acc >= 0.769 or FPR <= 0.146 with FNR <= 0.314 |
| Hard COCO | Acc >= 0.948, FPR <= 0.040, FNR <= 0.064 |
| Base-error-mined | recovery >= 0.055 and not worse than 30% mix |

If r015 passes COCO/GQA but fails Hard COCO, keep the ratio result as an
ablation and do not promote Mix DPO to the main method. If r015 also recovers
Hard COCO close to Answer-DPO, it becomes the strongest response-side evidence
rescue candidate. If base-error remains weak, the paper should still frame the
method as controlled regularization rather than robust correction.

## Writing Implication

Lowering evidence ratio should not be narrated as a new method gain unless it
clearly improves Hard COCO. The safer paper language is:

```text
Sparse response-side evidence can mildly reduce false positives on standard
held-out splits, but the benefit is sensitive to the ratio and does not by
itself solve hard or base-error-conditioned examples.
```

This keeps the story honest and avoids over-claiming from small positive
changes on already saturated COCO/GQA splits.
