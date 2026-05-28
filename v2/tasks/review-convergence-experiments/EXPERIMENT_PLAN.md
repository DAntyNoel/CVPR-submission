# Experiment Plan

## E0: Paper-Facing No-Compute Closure

Purpose: close the review items that do not require new model runs.

Current status:

- CEPO is already expanded on first use in `paper/main.tex`.
- Figure 1 already contrasts answer-level evaluation with CEPO-Probe.
- The main remaining no-compute check is citation/build hygiene: if AMBER is
  named as an external benchmark in the paper, either cite it or phrase it as
  an internal sanity-check dataset with documentation elsewhere.
- Keep the main paper at 6-8 pages after any edits.

Result location:

```text
results/paper_fixes/
```

Convergence gate:

- main PDF still builds;
- review PDF remains 6-8 pages;
- no missing citations or overfull table warnings.

## E1: Seed Stability

Purpose: test whether the core conclusion is an artifact of one LoRA-DPO run.

Design:

- Use the existing default run as seed 42.
- Add two additional seeds: 13 and 97.
- Train only the two groups needed for the central claim:
  CEPO Answer-DPO and CEPO-Dual-2k.
- Reuse Base Instruct, since it has no training seed.
- Use the same data, backbone, LoRA rank, DPO beta, epoch count, decoding, and
  scorers as V3.

Metrics:

- COCO / GQA / Hard COCO accuracy and FPR/FNR;
- BEM recovery;
- CEPO supported accuracy;
- CEPO wrong-evidence rejection;
- object / attribute / relation wrong-evidence rejection;
- strict JSON, scored-output rate, parse-failure rate.

Primary convergence criteria:

- Mean `CEPO-Dual-2k - CEPO Answer-DPO` wrong-evidence rejection is at least
  +20 percentage points.
- The lower end of the seed-level range is still at least +10 percentage
  points.
- CEPO-Dual-2k is not more than 1.0 point worse than CEPO Answer-DPO on COCO,
  GQA, or Hard COCO accuracy.
- Parse failure stays at 0 or remains too small to explain the result.

Fallback:

- If one seed reverses the conclusion, run one additional seed before changing
  the paper claim.
- If the seed range is wide but all signs are positive, keep the paper claim
  but report the variance in the appendix.

Result location:

```text
results/seed_stability/
```

## E2: Relation-Stress Probe

Purpose: verify that relation reversals are a real bottleneck rather than a
small-slice accident.

Design:

- Build a locked 200-300 row relation-only probe from held-out GQA images.
- Include only subject/object swap and left/right reversal cases.
- Do not use this probe for training or adapter selection.
- Evaluate Base, CEPO Answer-DPO, and CEPO-Dual-2k.

Metrics:

- wrong-evidence rejection accuracy;
- subject/object-swap rejection;
- left/right-reversal rejection;
- false accept rate when both objects are visible;
- parse failure rate;
- 12-18 qualitative cases split into correct rejection, false accept, and
  all-model failure.

Convergence criteria:

- If CEPO-Dual-2k relation rejection remains below 50% or at least 30 points
  below object wrong-evidence rejection, keep the V3 relation-bottleneck claim.
- If CEPO-Dual-2k exceeds 60% on the relation-stress probe, rewrite the
  limitation: relation reversals are still weaker than object/attribute checks
  but no longer the central unresolved failure.

Result location:

```text
results/relation_stress/
```

## E3: Optional Backbone Transfer

Purpose: address the single-backbone concern only if the paper needs stronger
empirical breadth after E1/E2.

Design:

- Use the locally available Qwen2.5-VL-32B-Instruct checkpoint.
- Run one seed only.
- Train CEPO Answer-DPO and CEPO-Dual-2k with the same row composition.
- Evaluate the same short-answer, evidence-probe, and external sanity checks.

Interpretation:

- If the 32B result matches the 7B direction, report it as appendix transfer
  evidence.
- If it weakens or reverses the claim, keep V3 as a one-backbone diagnostic
  study and explicitly report the 32B mismatch.

Result location:

```text
results/backbone_transfer/
```

Do not run E3 before E1/E2 unless the instructor explicitly asks for a second
backbone. It is compute-heavy and not necessary for the current five-group main
paper.
