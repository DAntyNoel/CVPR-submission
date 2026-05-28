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

Placeholder for generated lightweight tables and qualitative samples from the
improvement pass.

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
