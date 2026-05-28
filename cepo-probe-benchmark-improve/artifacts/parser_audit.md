# Parser Audit

| Model | Rows | Strict JSON Valid | Scored Output | Parse Failure |
| --- | ---: | ---: | ---: | ---: |
| Base Instruct | 1000 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| CEPO Answer-DPO | 1000 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |
| CEPO-Dual-2k | 1000 | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] | 0.0 [0.0, 0.0] |

Scored output means that JSON parsing or fallback field/support inference recovered enough structure for scoring.
