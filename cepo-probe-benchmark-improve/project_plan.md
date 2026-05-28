# Review-Driven Project Plan

Date: 2026-05-28

Source review: `official-review/20260528.md`

## 1. Current Diagnosis

The review is positive about the core direction but says the current manuscript
is not yet strong enough for a CVPR-style main-conference paper. The main
problems are:

| Area | Reviewer concern | Required response |
| --- | --- | --- |
| Paper size | Main text is only about 4 pages. | Expand to 6 pages with real technical content, not filler. |
| Novelty framing | CEPO-Dual is not a strong standalone method. | Frame the paper as a diagnostic benchmark and controlled study. |
| Related work | Current related work is too short and weakly differentiated. | Compare directly against hallucination, grounding, rationale, and preference-tuning benchmarks. |
| Rigor | One backbone, one seed, one DPO recipe, small probes. | Add confidence intervals and a compact ablation; keep larger robustness checks optional. |
| Probe statistics | 600 supported and 400 wrong-evidence rows need uncertainty estimates. | Report slice counts and 95% CI/bootstrap SE. |
| BEM clarity | Base-error-mined metric is unclear. | Define construction, meaning, and why Base is 0.0. |
| Parser clarity | Invalid JSON is misleading because fallback parsing exists. | Separate strict JSON valid, scored-output rate, and parse-failure rate. |
| CEPO-Dual transparency | Training row format is underspecified. | Add prompt/chosen/rejected table and a concrete example. |
| Relation failures | Relation wrong-evidence rejection remains weak but underexplained. | Add a dedicated analysis section and qualitative examples. |

## 2. Target Paper Claim

The improved paper should not claim that CEPO-Dual solves VLM grounding.

Use this central claim:

```text
Preference tuning can improve answer-level behavior while degrading
evidence-level verification. CEPO-Probe provides a controlled way to reveal
this hidden failure mode.
```

The paper-level contribution is the diagnostic separation between answer
correctness and evidence correctness. CEPO-Dual is a useful controlled baseline,
not the main novelty.

## 3. Constraints

Project constraints:

- Main experiment should stay at no more than three primary groups.
- Data construction should remain lightweight.
- Main text should target 6 pages.
- Core improvement should stay small and effective.
- GPU training and full inference must run through Slurm.
- GPU experiments should use ZeRO-2 unless there is a specific reason not to.

Practical consequence:

- Keep Base / CEPO Answer-DPO / CEPO-Dual as the main table.
- Put verifier-count and evidence-only controls in an ablation table.
- Do not start with a second backbone or full three-seed matrix unless the
  compact additions still leave the paper empirically weak.

## 4. Work Packages

### P0: Paper and Framing Fixes

No heavy computation.

Deliverables:

- Explain CEPO on first use: `Claim-Evidence Preference Optimization Probe`.
- Replace repeated "small benchmark" language with "controlled diagnostic
  benchmark".
- Expand Related Work to four explicit comparison blocks:
  hallucination benchmarks, grounding benchmarks, rationale/explanation
  evaluation, and VLM preference tuning.
- Add Figure 1: answer-level evaluation versus CEPO-Probe claim-evidence
  verification.
- Add a training-format table:

| Training type | Input | Chosen | Rejected |
| --- | --- | --- | --- |
| Answer-DPO | image + question | correct yes/no answer | wrong yes/no answer |
| Evidence-DPO | image + question + claim + evidence | support JSON | opposite support JSON |

- Add one full CEPO-Dual row example in the method section.
- Add a BEM definition paragraph.
- Rename or split the parser metric:
  `strict_json_valid`, `scored_output_rate`, and `parse_failure_rate`.

### P1: Lightweight Statistical Strengthening

Local-safe work on existing generation files.

Deliverables:

- Add 95% CI or bootstrap SE for Table 3 headline metrics.
- Report slice N for object, attribute, and relation wrong-evidence rows.
- Recompute evidence-probe tables using the current scorer.
- Add a compact table like:

| Slice | N | Base wrong-rej. | Answer-DPO wrong-rej. | CEPO-Dual wrong-rej. |
| --- | ---: | ---: | ---: | ---: |
| Object | 126 | with CI | with CI | with CI |
| Attribute | 149 | with CI | with CI | with CI |
| Relation | 125 | with CI | with CI | with CI |

Implementation note:

- Add or extend a lightweight scoring utility rather than rerunning inference.
- Use existing `results/eval/generations/...` outputs.

### P2: Minimal Ablation

Run through Slurm only.

Purpose:

Show that CEPO-Dual is not an arbitrary 2k verifier-row add-on.

Required ablation settings:

| Setting | Answer rows | Verifier rows | Role |
| --- | ---: | ---: | --- |
| Base | 0 | 0 | Existing untuned reference. |
| CEPO Answer-DPO | 6,000 | 0 | Existing answer-only baseline. |
| Evidence-DPO only | 0 | 2,000 | Tests whether verifier data alone harms short-answer transfer. |
| CEPO-Dual-500 | 6,000 | 500 | Small verifier dose. |
| CEPO-Dual-1k | 6,000 | 1,000 | Mid verifier dose. |
| CEPO-Dual-2k | 6,000 | 2,000 | Existing selected model. |

Primary ablation metrics:

- supported support accuracy;
- wrong-evidence rejection;
- object/attribute/relation wrong-evidence rejection;
- invalid/unparseable rates;
- COCO, GQA, and Hard COCO short-answer accuracy/FPR.

Stop rule:

- If CEPO-Dual-500 and CEPO-Dual-1k clearly track the existing CEPO-Dual-2k
  trend, do not run larger verifier-count sweeps.
- If evidence-only collapses short-answer transfer, that is useful evidence for
  the "answer and evidence objectives are separable" claim.

### P3: Relation-Failure Analysis

Local-safe analysis on scored outputs.

Deliverables:

- Sample 12 to 18 relation wrong-evidence cases:
  correct rejections, false accepts by CEPO-Dual, and cases where all models
  fail.
- Categorize failures:
  subject/object swap, left/right ambiguity, object-existence shortcut,
  copied candidate evidence, and unsupported relation text.
- Add one paragraph explaining why relation evidence remains hard:
  relation verification requires locating two entities and preserving direction,
  while textual evidence labels do not force region-level grounding.

### P4: Optional Robustness

Only run if time and compute budget allow.

Candidate additions:

- Two extra seeds for the selected CEPO-Dual-2k setting.
- One smaller alternate backbone, preferably if already available locally.
- A strict JSON prompt variant to test whether parser fallback is masking
  format failures.

Decision:

These are not required for the next minimal improvement pass. They are stretch
items if the instructor asks for stronger empirical breadth.

## 5. Paper Update Plan

Target 6-page main text:

| Section | Change |
| --- | --- |
| Abstract | Add one concrete sentence on how CEPO-Probe constructs candidate claim/evidence pairs. |
| Introduction | Explain CEPO acronym and remove repeated "small" self-downplaying. |
| Related Work | Expand to about 0.75 page with explicit differentiation. |
| Benchmark | Add construction flow, Figure 1, and train/probe separation. |
| Method/Baselines | Add CEPO-Dual training format table and example. |
| Experiments | Add CI table and ablation table. |
| Analysis | Add relation failure analysis and qualitative examples. |
| Limitations | Keep one-backbone limitation, but say the new ablation and CI reduce the main empirical ambiguity. |

## 6. Success Gates

The improvement pass is successful if:

- the main body reaches at least 6 pages without filler;
- Table 3 includes N and uncertainty estimates;
- CEPO-Dual training samples are transparent;
- BEM and parser behavior are unambiguous;
- ablation shows a monotonic or interpretable verifier-row trend;
- relation failures are explained rather than merely reported.

## 7. Fallback Plan

If ablation results are noisy:

- Keep the main three-group table unchanged.
- Move ablation to appendix and describe it as a sensitivity check.
- Preserve the central benchmark claim: answer-level gains do not guarantee
  evidence-level gains.

If verifier-count ablation weakens CEPO-Dual:

- Do not hide it. Use the result to argue that explicit evidence supervision is
  sensitive and must be measured directly.

If extra training cannot be scheduled:

- Complete P0, P1, and P3 first. These directly address several reviewer
  concerns without heavy computation.
