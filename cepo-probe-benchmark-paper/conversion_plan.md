# Conversion Plan: From Method Paper to Diagnostic Benchmark

Updated: 2026-05-28

Final decision update: CEPO-Dual is complete and is selected as the third main
group. The final numbers are recorded in `final_results.md` and ported into
`paper/main.tex`.

## 1. New Paper Positioning

Old framing:

```text
Claim-evidence preference optimization is a method that should improve grounded
VLM alignment.
```

New framing:

```text
Claim-evidence consistency is a diagnostic dimension that current VLM
preference-tuning experiments can miss. CEPO-Probe is a small benchmark for
testing whether models can connect a visual claim to the correct evidence,
especially when the answer text alone is insufficient.
```

The paper should read like a benchmark and diagnostic study, not a method win.
The evidence-aware training variants become baselines/probes, not the central
claim.

## 2. What To Reuse

Reuse the current local assets as the benchmark foundation:

```text
data/processed/cepo/claim_evidence_canonical.jsonl
data/processed/cepo/answer_dpo_train.jsonl
data/processed/cepo/cepo_latent_dpo_train.jsonl
data/processed/cepo/claim_evidence_summary.json
data/processed/cepo/check_report.json
data/eval/cepo_evidence_probe.jsonl
data/eval/cepo_wrong_evidence_probe.jsonl
scripts/data/12_build_cepo_claim_evidence.py
scripts/data/13_check_cepo_data.py
scripts/eval/prepare_cepo_evidence_probe.py
scripts/eval/score_cepo_evidence_probe.py
```

Reuse the short-answer eval suite as transfer diagnostics:

```text
data/eval/coco_heldout_object_existence.jsonl
data/eval/gqa_simple_heldout.jsonl
data/eval/coco_hard_object_existence.jsonl
data/eval/base_error_mined_object_existence.jsonl
data/eval/pope_coco_random.jsonl
data/eval/pope_coco_popular.jsonl
data/eval/pope_coco_adversarial.jsonl
data/eval/amber_discriminative.jsonl
```

Reuse V1 as motivation, not as the main story:

- Template evidence hints did not reliably beat Answer-DPO.
- 10k scale-up did not reverse the trend.
- Input-side and chosen-only variants mostly exposed FPR/FNR trade-offs.
- Base-error-mined recovery remained weak for evidence-hint variants.

## 3. What To Change In The Existing Paper

The current `paper/main.tex` is a controlled diagnostic method paper about
Evidence-Hint DPO. For the new benchmark paper:

| Current Section | Change |
| --- | --- |
| Title | Rename from a method study to a benchmark/diagnostic title. |
| Abstract | Lead with the missing diagnostic: answer accuracy is not evidence consistency. |
| Introduction | Motivate claim-evidence verification, not a new optimization method. |
| Contributions | Benchmark, scorer, baseline diagnosis, and findings. |
| Method | Replace with Benchmark Construction and Probe Design. |
| Experiments | Keep at most three model groups; report short-answer transfer and evidence probes. |
| Main Results | Emphasize divergence between short-answer gains and evidence consistency. |
| Limitations | Acknowledge COCO/GQA-derived annotations, small scale, single backbone, and rule-based scoring. |
| Conclusion | State what the benchmark reveals; avoid claiming evidence training solves hallucination. |

## 4. Main Claims To Make

Safe claims already supported by current assets:

1. The project provides a controlled claim-evidence benchmark spanning object
   existence, attributes, spatial relations, and wrong-evidence negatives.
2. The benchmark separates answer correctness from evidence correctness.
3. Existing small-data DPO variants can improve short-answer behavior without
   reliably improving wrong-evidence rejection.
4. Relation evidence is a particularly fragile slice and should be reported
   separately.

Claims that require final evidence before use:

1. Any method is better than Answer-DPO on evidence consistency.
2. CEPO-Dual preserves short-answer accuracy while improving wrong-evidence
   rejection.
3. The benchmark generalizes beyond COCO/GQA-style object, attribute, and
   left/right relation claims.

## 5. Final Main Experiment Choice

Keep the main table to three groups:

| Slot | Preferred Model Group | Fallback |
| --- | --- | --- |
| A | Base Instruct | fixed |
| B | CEPO Answer-DPO | fixed |
| C | CEPO-Dual if final results pass gates | CEPO-Latent as a failed evidence-aware baseline |

Decision rule:

- If CEPO-Dual is complete and improves wrong-evidence rejection while keeping
  short-answer metrics close to Answer-DPO, use CEPO-Dual as Group C.
- If CEPO-Dual is incomplete or fails, use CEPO-Latent and present the paper as
  a benchmark exposing the failure of latent claim-evidence supervision.

Do not put Evidence-Hint, Phase-2 variants, 10k scale-up, CEPO-Latent, and
CEPO-Dual all into the main table. Those are appendix or motivation material.

## 6. What Is Still Needed

Required before a submission-style draft:

- Decide the final Group C model: CEPO-Dual or CEPO-Latent. **Done: CEPO-Dual.**
- Fill all placeholder metrics in the submission draft. **Done in `paper/main.tex`.**
- Re-score all selected generations with the current scorer to avoid mixed
  metric versions. **Done on 2026-05-28.**
- Ensure both supported and wrong-evidence probe metrics exist for all selected
  groups. **Done.**
- Add one audit summary for CEPO-Probe examples, ideally 100-200 rows.
  **Done as a 200-row annotation-consistency audit, not an independent
  pixel-level relabeling pass.**
- Add a small qualitative error table with 4-6 examples:
  object, attribute, relation, wrong object evidence, wrong relation evidence.
  **Done in `paper/appendix.tex`.**
- Write a data card paragraph: sources, licenses, derived annotations, intended
  use, and known limitations. **Done in `paper/main.tex`.**
- Decide whether AMBER metrics are included in the main paper or appendix based
  on completeness. **Done: compact external summary in main text, table in appendix.**

Optional but useful:

- Add bootstrap confidence intervals for the main probe metrics.
- Add slice-level tables for attribute color, material, object existence, and
  relation spatial.
- Add a compact appendix table linking each artifact path to the command that
  generated it.
- Add a leaderboard-style JSON schema for future model submissions.

## 7. Concrete File-Level Edit Path

When turning this prototype into the repository paper:

1. Copy the structure of `paper_draft.tex` into `paper/main.tex`.
2. Keep the existing CVPR template, bibliography, and Makefile under `paper/`.
3. Replace V1 Evidence-Hint-specific figures with a CEPO-Probe schema figure.
4. Replace current method table with benchmark task slices and probe metrics.
5. Move old Evidence-Hint results to a short motivation paragraph or appendix.
6. Update `paper/README.md` to describe the benchmark paper instead of the V1
   diagnostic draft.

## 8. Stop Criteria

Stop running new experiments once the paper can support this conclusion:

```text
CEPO-Probe shows that short-answer preference tuning and claim-evidence
verification are separable: a model can improve ordinary yes/no accuracy while
remaining weak at rejecting mismatched evidence, especially for relations.
```

That conclusion is sufficient for a compact diagnostic benchmark paper. A
positive CEPO-Dual result would strengthen the baseline section, but it is not
required for the benchmark contribution to exist.
