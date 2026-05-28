# Submitted Fixed-Budget Jobs

Status: complete. Submitted on 2026-05-28 15:49:39 +08:00; all dependent eval
metrics are present and summarized.

## Training Jobs

| Variant | Job ID | Initial state |
| --- | ---: | --- |
| `answer4k` | 64747 | running |
| `dual1k_fixed6k` | 64754 | running |
| `dual2k_fixed6k` | 64761 | running |

## Dependent Eval Jobs

| Variant | COCO | GQA | Hard | BEM | Supported probe | Wrong probe |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `answer4k` | 64748 | 64749 | 64750 | 64751 | 64752 | 64753 |
| `dual1k_fixed6k` | 64755 | 64756 | 64757 | 64758 | 64759 | 64760 |
| `dual2k_fixed6k` | 64762 | 64763 | 64764 | 64765 | 64766 | 64767 |

Initial queue check at 2026-05-28 15:50 +08:00 showed the three training jobs
running on RTX4090 nodes and all fixed-budget eval jobs pending on their
training dependencies.
