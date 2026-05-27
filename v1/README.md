# V1 Archive: Lightweight Evidence-Hint DPO

Updated: 2026-05-27

This folder archives the first project line: a controlled diagnostic study of
whether template-level evidence hints improve VLM preference tuning beyond
plain Answer-DPO.

## Final Reading

The V1 result should be treated as closed. Template evidence hints produce a
small and sometimes useful false-positive reduction, but they do not
consistently beat Answer-DPO on accuracy, F1, hard negatives, or base-error
recovery.

Key completed results:

| Eval | Base | Answer-DPO | Evidence-Hint DPO | Reading |
| --- | ---: | ---: | ---: | --- |
| COCO held-out Acc | 0.959 | 0.961 | 0.961 | Evidence-Hint ties Answer-DPO. |
| GQA simple Acc | 0.764 | 0.768 | 0.766 | Evidence-Hint trails Answer-DPO. |
| Hard COCO Acc | 0.944 | 0.950 | 0.946 | Evidence-Hint lowers FPR slightly but loses recall. |
| Base-error recovery | 0.000 | 0.063 | 0.030 | Evidence-Hint does not recover base failures. |

The 10k scale-up, Phase-2 placement variants, Answer-Evidence Mix, and
Balanced Hard Input-Side rescue runs did not overturn this diagnosis. The
stable conclusion is:

> Response-level template hints are too weak to reliably force visual
> grounding. Future work should move from answer-level evidence style toward
> verifiable claim-evidence alignment.

## Archived Planning Files

```text
v1/idea-lightweighted-grounded-preference-vlm/
  plan.md
  data_processing_plan.md
  paper_outline_and_tasks.md
  midterm_report.md
  midterm_report_2.md
  main_experiment_core_claims/

v1/idea-imporve-evidence/
  phase2_method_ideas.md

v1/tasks/
  coco-hard-ceiling-diagnosis/
  base-error-mining/
  input-side-evidence-main-method/
  answer-evidence-mix-dpo/
  balanced-hard-evidence-dpo/
```

## What To Keep

Keep the following V1 assets as reusable infrastructure for the next project:

- Canonical pair construction, leakage checks, and audit-sheet workflow.
- LLaMA-Factory DPO training setup, ZeRO-2 preference-tuning configs, and Slurm
  submission patterns.
- Unified VLM inference and object-eval scoring scripts.
- COCO/GQA/Hard COCO/Base-error/POPE/AMBER evaluation files and metrics.
- The diagnostic paper framing, especially the FPR/FNR and yes-bias analysis.

Do not continue V1 by repeating the same template-hint training or evaluation
jobs. Any new work should change the research question, not only the ratio,
prompt wording, or data scale of the same response-side hint.
