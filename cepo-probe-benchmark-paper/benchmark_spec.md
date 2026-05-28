# CEPO-Probe Benchmark Specification

## 1. Benchmark Name

Primary name:

```text
CEPO-Probe
```

Dataset shorthand:

```text
ClaimEvidence-6K
```

The paper can use both:

> We introduce CEPO-Probe, a diagnostic benchmark built from ClaimEvidence-6K
> preference examples.

## 2. Goal

CEPO-Probe tests whether a VLM can verify that a visual claim is supported by
the correct evidence. The benchmark is intentionally narrower than general VQA:
it focuses on simple, verifiable claims where annotation-derived evidence is
available.

The benchmark separates four abilities:

1. Answer the visual question correctly.
2. Identify the claim being judged.
3. Match the evidence label to the claim.
4. Reject evidence that is plausible textually but mismatched visually or
   semantically.

## 3. Current Data Summary

Current canonical artifact:

```text
data/processed/cepo/claim_evidence_canonical.jsonl
```

Current size:

| Slice | Rows |
| --- | ---: |
| Object existence | 2,000 |
| Attribute color/material | 1,500 |
| Left/right relation | 1,500 |
| Wrong-evidence negatives | 1,000 |
| Total | 6,000 |

Current source mix:

| Source | Rows |
| --- | ---: |
| COCO-derived | 2,390 |
| GQA-derived | 3,610 |

Current data checks:

| Check | Status |
| --- | --- |
| Train/eval image overlap | 0 |
| Same-answer wrong-evidence rows | 1,000 |
| Identical Answer-DPO chosen/rejected rows | 0 |
| Main eval files included in overlap check | COCO, GQA, Hard COCO, Base-error-mined, POPE, AMBER |

## 4. Canonical Schema

Each row should contain:

```json
{
  "id": "cepo_000001",
  "source": "coco|gqa",
  "image": "path/to/image.jpg",
  "image_id": "stable_image_id",
  "task_type": "object_existence|attribute_color|attribute_material|relation_spatial|wrong_evidence",
  "question": "Is there a bus in the image?",
  "chosen_answer": "Yes, there is a bus in the image.",
  "rejected_answer": "No, there is no bus in the image.",
  "chosen_claims": [
    {
      "span": "bus visible",
      "type": "object",
      "support": "supported",
      "evidence": [
        {"role": "target", "label": "bus", "box": [0.10, 0.20, 0.50, 0.70]}
      ],
      "attribute": null,
      "relation": null
    }
  ],
  "rejected_claims": [],
  "negative_type": "answer_wrong|attribute_mismatch|relation_reversal|evidence_wrong"
}
```

Training exports may omit boxes from text. Evaluation metadata should retain
boxes when available for auditing and future region-aware scoring.

## 5. Probe Files

Supported-evidence probe:

```text
data/eval/cepo_evidence_probe.jsonl
```

Wrong-evidence probe:

```text
data/eval/cepo_wrong_evidence_probe.jsonl
```

The supported probe asks whether evidence supports a claim. The wrong-evidence
probe gives a candidate evidence label/relation that should be rejected.

## 6. Prompt Format

Default probe prompt:

```text
Answer yes or no. Then provide one claim and the visual evidence label.
Return JSON with keys: answer, claim, evidence_label, support.
```

Recommended output schema:

```json
{
  "answer": "yes",
  "claim": "bus visible",
  "evidence_label": "bus",
  "support": "supported"
}
```

Allowed support labels:

```text
supported
contradicted
wrong_evidence
```

## 7. Metrics

Main probe metrics:

| Metric | Meaning |
| --- | --- |
| Answer accuracy | Whether the yes/no answer matches the target. |
| Support accuracy | Whether `support` matches the target support label. |
| Evidence-label accuracy | Whether the predicted evidence label matches the expected label or alias. |
| Claim-match rate | Whether the output claim matches the queried claim. |
| Relation-direction accuracy | Whether left/right relation direction is preserved. |
| Wrong-evidence rejection accuracy | Whether mismatched evidence is rejected. |
| Invalid JSON rate | Whether output fails the requested parseable format. |

Short-answer transfer metrics:

| Metric | Meaning |
| --- | --- |
| Acc / BAcc / F1 | Standard yes/no performance. |
| FPR / FNR | False-positive and false-negative trade-off. |
| Yes rate | Bias toward affirmative answers. |
| Other / invalid rate | Non-yes/no output failures. |

## 8. Quality Gates

Minimum gates for the benchmark artifact:

| Gate | Target |
| --- | --- |
| Train/eval image overlap | 0 |
| Probe invalid JSON rate for baseline-capable models | Below 5% preferred |
| Manual audit size | 100-200 rows before submission |
| Wrong-evidence rows | At least 700; current target 1,000 |
| Relation rows | At least 1,000; current target 1,500 |
| Main baseline groups | At most 3 in the primary paper |

## 9. Known Limitations

- The benchmark is derived from COCO and GQA annotations rather than fresh
  human annotation.
- Textual evidence labels are weaker than region-level grounding.
- Some object boxes are missing for GQA-derived rows; current scoring mainly
  uses labels and relation metadata.
- The benchmark focuses on simple object, attribute, and left/right relation
  claims.
- Rule-based scoring is transparent and cheap, but it cannot capture all valid
  free-form evidence descriptions.

## 10. Submission-Ready Additions

Before release, add:

- data license notes for COCO, GQA, POPE, and AMBER-derived eval use;
- a data card covering intended use and misuse;
- deterministic regeneration commands;
- a small sample file with images omitted or paths redacted if redistribution
  is restricted;
- confidence intervals or bootstrap scripts for headline metrics.

