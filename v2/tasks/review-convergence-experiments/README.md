# V3 Review-Convergence Experiments

Created: 2026-05-28

## Goal

This task tracks the extra evidence needed for the V3 CEPO-Probe conclusion to
converge:

> Answer-level preference tuning and claim-evidence verification are separable;
> explicit verifier preferences recover evidence rejection without making a
> broad hallucination-benchmark claim, while relation reversals remain the main
> bottleneck.

The task is intentionally scoped to the current paper constraints:

- no more than five main experimental groups in the paper body;
- lightweight data construction;
- no direct interactive GPU jobs;
- heavy training and full inference only through Slurm;
- ZeRO-2 for GPU training unless a specific run requires otherwise.

## Current Evidence

V3 already has strong single-seed evidence:

- five main groups: Base Instruct, CEPO Answer-DPO, Evidence-DPO-only,
  CEPO-Dual-1k, CEPO-Dual-2k;
- CEPO-Dual verifier-count ablation: 500 / 1k / 2k verifier rows;
- bootstrap CIs for Base, Answer-DPO, and CEPO-Dual-2k;
- parser audit split into strict JSON, scored output, and parse failure;
- relation failure examples and external POPE/AMBER sanity checks.

The remaining convergence gaps are:

1. seed stability for the central answer-vs-verifier conclusion;
2. a locked relation-stress probe to confirm the relation bottleneck;
3. optional backbone transfer if the course/instructor requires breadth beyond
   one Qwen2.5-VL-7B backbone;
4. paper-facing no-compute checks: the current paper already includes the CEPO
   acronym expansion and Figure 1; the remaining check is build/citation
   hygiene, especially if AMBER is cited formally.

## Result Directories

```text
results/
  paper_fixes/
  seed_stability/
  relation_stress/
  backbone_transfer/
  convergence_audit/
```

Each result directory contains its own README and metric template. Completed
results should be copied or summarized here rather than scattered only under
`results/eval/generations/`.

## Stop Rule

Stop adding experiments when the convergence audit proves all of the following:

- CEPO Answer-DPO still improves or preserves short-answer behavior but does
  not improve wrong-evidence rejection relative to Base.
- CEPO-Dual-2k improves wrong-evidence rejection over CEPO Answer-DPO by a
  large margin across the locked probe and seed checks.
- CEPO-Dual-2k does not collapse COCO, GQA, Hard COCO, POPE, or AMBER.
- Relation wrong-evidence remains materially weaker than object and attribute
  wrong-evidence, or the paper is rewritten if relation performance no longer
  supports the current bottleneck claim.

Do not run larger sweeps once these checks are satisfied.
