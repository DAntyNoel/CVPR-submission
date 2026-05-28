# CEPO-Probe Benchmark Paper Prototype

This folder reframes the current project from a positive method paper into a
small diagnostic benchmark paper.

Working title:

```text
CEPO-Probe: A Claim-Evidence Consistency Benchmark for Diagnosing VLM Preference Tuning
```

## Why This Pivot

The current experiments do not support the original positive hypothesis that
lightweight evidence text or latent claim-evidence blocks reliably improve
short-answer hallucination control. The stronger and more honest contribution
is a diagnostic benchmark:

> Do VLM preference-tuning methods that improve short-answer accuracy also learn
> to verify whether a visual claim is supported by the correct evidence?

The existing project already has the ingredients for this:

- a 6,000-row claim-evidence canonical set;
- object, attribute, relation, and wrong-evidence slices;
- zero train/eval image overlap against the fixed eval suite;
- supported-evidence and wrong-evidence probes;
- short-answer baselines on COCO, GQA, Hard COCO, Base-error-mined, POPE, and
  AMBER;
- completed negative/diagnostic evidence from V1 and CEPO-Latent.

## Files

```text
conversion_plan.md
```

How to change the paper story, which existing files to reuse, what to remove
from the method-centered framing, and what is still needed before submission.

```text
benchmark_spec.md
```

Concrete benchmark definition: data schema, task slices, evaluation prompts,
metrics, scoring assumptions, and quality gates.

```text
experiment_blueprint.md
```

The minimal experiment matrix and table shells. Numbers are intentionally left
as placeholders where a final rerun or final model choice is needed.

```text
paper_draft.tex
```

A full CVPR-style draft skeleton for the benchmark/diagnostic paper. It is
written as a standalone draft body with placeholder metric cells, ready to be
ported into `paper/main.tex` after the final experiment set is fixed.

## Recommended Final Shape

Use a benchmark-first narrative:

1. Introduce claim-evidence consistency as a missing diagnostic dimension for
   VLM preference tuning.
2. Present CEPO-Probe / ClaimEvidence-6K as a small controlled benchmark.
3. Evaluate at most three main model groups:
   Base Instruct, Answer-DPO, and one evidence-aware training variant.
4. Report both short-answer metrics and evidence-probe metrics.
5. Make the main conclusion diagnostic: answer preference can improve ordinary
   yes/no accuracy while failing to improve, or even worsening, evidence
   consistency on wrong-evidence cases.

Do not claim that CEPO-Latent is a successful main method unless a final run
proves it. CEPO-Dual can become the third main group only if its final results
are complete and pass the gates in `experiment_blueprint.md`.

