# Qwen2.5-VL-32B Backbone Transfer Summary

Variant: `backbone_transfer/qwen25vl32b`

## Status

All planned T0/T1/T2 metrics are present.

## Acceptance Snapshot

### Qwen2.5-VL-32B Base
- coco.accuracy: 95.7%
- gqa.accuracy: 76.6%
- hard_coco.accuracy: 93.1%
- bem.accuracy: 22.6%
- cepo_supported.support_accuracy: 91.8%
- cepo_wrong.wrong_evidence_rejection: 24.5%
- cepo_wrong.object_wrong_rejection: 39.7%
- cepo_wrong.attribute_wrong_rejection: 22.1%
- cepo_wrong.relation_wrong_rejection: 12.0%
- relation_stress.overall_rejection: 31.7%
- relation_stress.subject_object_swap_rejection: 7.5%
- relation_stress.left_right_reversal_rejection: 55.8%
- relation_stress.false_accept_rate: 68.3%
- cepo_wrong.parse_failure_rate: 0.2%

### 32B CEPO Answer-DPO
- coco.accuracy: 95.9%
- gqa.accuracy: 76.7%
- hard_coco.accuracy: 93.8%
- bem.accuracy: 24.3%
- cepo_supported.support_accuracy: 93.5%
- cepo_wrong.wrong_evidence_rejection: 23.8%
- cepo_wrong.object_wrong_rejection: 41.3%
- cepo_wrong.attribute_wrong_rejection: 21.5%
- cepo_wrong.relation_wrong_rejection: 8.8%
- relation_stress.overall_rejection: 27.1%
- relation_stress.subject_object_swap_rejection: 5.0%
- relation_stress.left_right_reversal_rejection: 49.2%
- relation_stress.false_accept_rate: 72.9%
- cepo_wrong.parse_failure_rate: 0.0%

### 32B CEPO-Dual-2k
- coco.accuracy: 95.9%
- gqa.accuracy: 76.6%
- hard_coco.accuracy: 93.8%
- bem.accuracy: 24.7%
- cepo_supported.support_accuracy: 93.0%
- cepo_wrong.wrong_evidence_rejection: 24.5%
- cepo_wrong.object_wrong_rejection: 39.7%
- cepo_wrong.attribute_wrong_rejection: 23.5%
- cepo_wrong.relation_wrong_rejection: 10.4%
- relation_stress.overall_rejection: 31.7%
- relation_stress.subject_object_swap_rejection: 5.8%
- relation_stress.left_right_reversal_rejection: 57.5%
- relation_stress.false_accept_rate: 68.3%
- cepo_wrong.parse_failure_rate: 0.0%

CEPO-Dual-2k wrong-evidence delta over Answer-DPO: 0.8%
