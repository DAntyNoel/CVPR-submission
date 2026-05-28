# CEPO Verifier-Count Ablation

| Setting | Answer rows | Verifier rows | COCO Acc | GQA Acc | Hard Acc | Supp. Acc | Wrong Rej. | Object Wrong | Attr. Wrong | Rel. Wrong | Parse Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 0 | 0 | 96.0 | 76.2 | 94.4 | 86.5 | 44.3 | 59.5 | 53.7 | 17.6 | 0.0 |
| CEPO Answer-DPO | 6000 | 0 | 97.0 | 76.8 | 95.0 | 90.7 | 34.3 | 45.2 | 45.0 | 10.4 | 0.0 |
| Evidence-DPO only | 0 | 2000 | 95.9 | 76.7 | 94.4 | 87.8 | 53.0 | 77.0 | 63.8 | 16.0 | 0.0 |
| CEPO-Dual-500 | 6000 | 500 | 96.9 | 76.8 | 95.0 | 91.3 | 39.5 | 56.3 | 50.3 | 9.6 | 0.0 |
| CEPO-Dual-1k | 6000 | 1000 | 97.0 | 77.2 | 94.9 | 93.2 | 48.5 | 74.6 | 59.1 | 9.6 | 0.0 |
| CEPO-Dual-2k | 6000 | 2000 | 97.0 | 77.1 | 94.9 | 95.2 | 70.3 | 96.0 | 85.9 | 25.6 | 0.0 |

## Current Read

- Answer-DPO improves supported-claim behavior but lowers wrong-evidence rejection relative to the base; CEPO-Dual-2k restores rejection strongly.
- Relation wrong-evidence remains the bottleneck even when object wrong-evidence rejection is high.
- The verifier-count ablation is monotonic: wrong-evidence rejection is 39.5, 48.5, and 70.3 for 500/1k/2k verifier rows.
- Evidence-DPO-only has completed enough short-answer evaluation to test whether verifier supervision transfers or harms ordinary VQA behavior.
