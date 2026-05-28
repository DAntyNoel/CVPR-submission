# CEPO-Probe Benchmark Improve

This directory records the review-driven improvement plan after
`official-review/20260528.md`.

The current CEPO-Probe manuscript is a coherent diagnostic report, but the
review points out that it still looks closer to a short workshop paper than a
full CVPR-style submission. The next stage should strengthen the paper without
turning it into a large open-ended benchmark project.

## Files

```text
project_plan.md
```

Review-to-action project plan. It maps each major reviewer concern to concrete
paper edits, lightweight analysis, and Slurm-only experiments.

```text
experiment_outline.md
```

Minimal experimental outline for the next run: confidence intervals, parser/BEM
clarification, CEPO-Dual verifier-count ablations, evidence-only control, and
relation-failure analysis.

```text
operation_checklist.md
```

Execution checklist with local-safe steps, Slurm submission rules, expected
artifacts, and stop conditions.

```text
artifacts/
```

Generated lightweight tables and qualitative samples from the improvement
pass.

Key artifacts now present:

```text
artifacts/table3_ci.md
artifacts/slice_ci.md
artifacts/parser_audit.md
artifacts/relation_failure_cases.md
artifacts/ablation_results.md
```

## Completed Improvement Pass

Updated: 2026-05-28

The review-driven local and Slurm experiments have completed.

- Probe CI: Base / CEPO Answer-DPO / CEPO-Dual-2k were re-scored and
  bootstrapped with 10,000 row resamples. Table 3 now has N and 95% CI:
  supported accuracy is 86.5 / 90.7 / 95.2, and wrong-evidence rejection is
  44.3 / 34.3 / 70.3.
- Parser audit: all 1,000 current probe generations per model are strict JSON
  valid and scored; parse-failure rate is 0.0.
- Relation analysis: sampled relation wrong-evidence cases show the dominant
  failure mode is accepting subject/object-swapped evidence.
- Verifier-count ablation: Slurm jobs 64635-64652 completed with exit code 0.
  Short-answer transfer stays stable, supported accuracy rises with verifier
  rows, and wrong-evidence rejection is monotonic for CEPO-Dual-500/1k/2k:
  39.5 / 48.5 / 70.3.

Conclusion for the paper:

```text
CEPO-Probe exposes a real separation between answer-level preference tuning and
claim-evidence verification. Answer-DPO improves supported claims but weakens
wrong-evidence rejection; adding verifier rows restores evidence checking, and
2k verifier rows are materially stronger than 500 or 1k. Relation reversals
remain the main unsolved slice.
```

## Working Decision

Keep the main paper benchmark-first:

```text
Preference tuning can improve answer-level behavior while degrading
evidence-level verification. CEPO-Probe provides a controlled way to reveal
this hidden failure mode.
```

Do not reframe CEPO-Dual as a major new method. Use CEPO-Dual as a controlled
evidence-aware baseline that demonstrates why CEPO-Probe is needed.

## Scope Rules

- Keep the main comparison to three model groups: Base Instruct, CEPO
  Answer-DPO, and CEPO-Dual.
- Put new ablations in a compact analysis table or appendix.
- Do not run GPU training or full inference directly in the interactive shell.
  Use Slurm and ZeRO-2.
- Prefer lightweight local work first: confidence intervals, table
  reconstruction, parser audit, BEM explanation, qualitative sampling, and
  paper edits.
- Treat additional backbones and full multi-seed matrices as optional stretch
  work unless required by the instructor.

## Target Outcome

The improved submission should have:

- at least 6 pages of main text;
- a stronger related-work comparison;
- a Figure 1 data/task diagram;
- explicit CEPO-Dual training sample format;
- confidence intervals or bootstrap standard errors for the probe table;
- clear BEM and parser definitions;
- a compact ablation showing why 2k verifier rows are used;
- a relation-reversal failure analysis with qualitative examples.
