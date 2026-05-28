# Table 3 CEPO-Probe CI

| Model | Supported N | Supported Acc. | Wrong N | Wrong-Evidence Rej. | Strict JSON | Scored Output | Parse Fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | 600 | 86.5 [83.7, 89.2] | 400 | 44.3 [39.5, 49.0] | 100.0 | 100.0 | 0.0 |
| CEPO Answer-DPO | 600 | 90.7 [88.3, 93.0] | 400 | 34.3 [29.8, 39.0] | 100.0 | 100.0 | 0.0 |
| CEPO-Dual-2k | 600 | 95.2 [93.3, 96.8] | 400 | 70.3 [65.8, 74.8] | 100.0 | 100.0 | 0.0 |

Values are row-bootstrap estimates with 10,000 resamples by default; intervals are percentile 95% CIs.
Strict JSON measures parseable JSON objects in raw generations; scored output also counts fallback parsing.
