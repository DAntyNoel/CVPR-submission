# Fixed-Budget Control Summary

Status: complete.

## Fixed-Budget Rows

| Setting | Answer | Verifier | Total | COCO | GQA | Hard | BEM | Supported | Wrong | Obj | Attr | Rel | JSON obj | Parse fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Answer-4k | 4000 | 0 | 4000 | 96.7 | 77.0 | 94.9 | 11.2 | 89.2 | 39.2 | 54.0 | 49.0 | 12.8 | 100.0 | 0.0 |
| Dual-1k-fixed6k | 5000 | 1000 | 6000 | 96.9 | 77.0 | 95.1 | 17.6 | 91.5 | 48.2 | 73.8 | 58.4 | 10.4 | 100.0 | 0.0 |
| Dual-2k-fixed6k | 4000 | 2000 | 6000 | 96.9 | 76.9 | 95.1 | 17.1 | 94.5 | 62.7 | 92.9 | 78.5 | 13.6 | 100.0 | 0.0 |

## References

| Setting | Answer | Verifier | Total | COCO | GQA | Hard | BEM | Supported | Wrong | Obj | Attr | Rel | JSON obj | Parse fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CEPO Answer-DPO-6k | 6000 | 0 | 6000 | 97.0 | 76.8 | 95.0 | 18.0 | 90.7 | 34.2 | 45.2 | 45.0 | 10.4 | 100.0 | 0.0 |
| CEPO-Dual-2k original | 6000 | 2000 | 8000 | 97.0 | 77.1 | 94.9 | 19.4 | 95.2 | 70.2 | 96.0 | 85.9 | 25.6 | 100.0 | 0.0 |

## Paper Integration Read

- Dual-2k-fixed6k vs CEPO Answer-DPO-6k wrong-evidence rejection: +28.5 pp.
- Short-answer deltas: COCO -0.1, GQA +0.1, Hard +0.1.
- Paper action: add the fixed 6k-row appendix/control sentence that verifier replacement remains effective, so the original 2k gain is not only a total-row-count artifact.
