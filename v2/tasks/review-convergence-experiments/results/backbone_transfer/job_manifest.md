# Backbone Transfer Job Manifest

Status: deferred.

Backbone:

```text
models/Qwen2.5-VL-32B-Instruct
```

Run only after E1/E2 if the conclusion still needs stronger breadth.

Minimum matrix:

| Seed | Model | Output variant |
| ---: | --- | --- |
| 42 | CEPO Answer-DPO 32B | `cepo_backbone_transfer/qwen25vl32b` |
| 42 | CEPO-Dual-2k 32B | `cepo_backbone_transfer/qwen25vl32b` |

This is intentionally not part of the five-group main paper. If run, report it
as appendix transfer evidence.
