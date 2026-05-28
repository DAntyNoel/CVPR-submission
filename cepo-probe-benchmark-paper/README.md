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
- completed negative/diagnostic evidence from V1 and CEPO-Latent;
- completed CEPO-Dual results for the final three-group benchmark comparison.

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

The minimal experiment matrix and table shells. It now points to the completed
CEPO-Dual decision and final paper tables.

```text
final_results.md
```

Final selected metrics for Base Instruct, CEPO Answer-DPO, and CEPO-Dual after
re-scoring with the current short-answer and evidence-probe scorers.

```text
paper_draft.tex
```

A final handoff note for the old prototype skeleton. The submission-style
version with final numbers has been ported into `paper/main.tex`.

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

CEPO-Dual is now the selected third main group: it preserves short-answer
behavior close to CEPO Answer-DPO and improves wrong-evidence rejection from
34.3% to 70.2%. The paper should still keep a diagnostic tone because relation
wrong-evidence rejection remains weak at 25.6%.
