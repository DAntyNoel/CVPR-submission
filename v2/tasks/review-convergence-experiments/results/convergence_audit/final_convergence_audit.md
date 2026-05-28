# Final Convergence Audit

Status: complete

| Requirement | Evidence file | Status | Decision |
| --- | --- | --- | --- |
| V3 current evidence snapshot | `current_v3_snapshot.md`, `current_v3_snapshot.json` | ready | Snapshot generated from the existing CEPO ablation summarizer. |
| Paper no-compute fixes | `../paper_fixes/` | complete | CEPO acronym, Figure 1, parser wording, seed-stability wording, relation-stress wording, and bounded-claim edits are present in the paper draft. The review/full builds pass at 8/10 pages with no missing citations, missing references, or overfull table warnings. |
| Seed stability | `../seed_stability/metrics.csv` | complete | Jobs 64699/64700-64705 and 64706-64726 completed. Across seeds 13/42/97, CEPO-Dual-2k improves wrong-evidence rejection over CEPO Answer-DPO by +38.8/+36.0/+35.2 points while preserving COCO/GQA/Hard accuracy within 0.3 points. |
| Relation bottleneck | `../relation_stress/metrics.csv` | complete | Relation-stress jobs 64682-64684 completed. CEPO-Dual improves overall rejection to 71.25%, but subject/object swaps remain weak at 42.50%; the paper claim is narrowed toward role-swap fragility rather than broad left/right reversal fragility. |
| Paraphrased probe | `../paraphrase_probe/metrics.csv` | complete | Jobs 64741-64746 completed. With the same locked rows and labels but rewritten prompts/evidence, CEPO-Dual-2k keeps a wrong-evidence rejection advantage over CEPO Answer-DPO: 73.2% vs 61.8%, with both at 90.0% supported accuracy and 0.0 parse failures. |
| Optional backbone transfer | `../backbone_transfer/metrics.csv` | deferred | Run only if E1/E2 are insufficient or requested. |

Conclusion:

The V3 conclusion has converged for the current course-paper scope. The
three-seed check supports the central answer-vs-verifier claim, relation-stress
evidence narrows the bottleneck to subject/object role swaps, and the
row-preserving paraphrased probe weakens the template-dependence concern while
leaving human-written evidence as a future-validity check. External POPE/AMBER
checks remain sanity checks rather than the main claim. Backbone transfer
remains deferred rather than a blocker for this draft.
