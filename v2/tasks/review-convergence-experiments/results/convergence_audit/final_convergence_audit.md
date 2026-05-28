# Final Convergence Audit

Status: pending

| Requirement | Evidence file | Status | Decision |
| --- | --- | --- | --- |
| V3 current evidence snapshot | `current_v3_snapshot.md`, `current_v3_snapshot.json` | ready | Snapshot generated from the existing CEPO ablation summarizer. |
| Paper no-compute fixes | `../paper_fixes/` | partial | CEPO acronym and Figure 1 are present; citation/build hygiene still needs final verification after edits. |
| Seed stability | `../seed_stability/metrics.csv` | submitted | Active train/eval jobs are 64699/64700-64705 and 64706-64726; failed cache-race chains were canceled and retried with serialized preprocessing. |
| Relation bottleneck | `../relation_stress/metrics.csv` | complete | Relation-stress jobs 64682-64684 completed. CEPO-Dual improves overall rejection to 71.25%, but subject/object swaps remain weak at 42.50%; update the paper claim toward swap fragility rather than broad left/right reversal fragility. |
| Optional backbone transfer | `../backbone_transfer/metrics.csv` | deferred | Run only if E1/E2 are insufficient or requested. |

Conclusion:

The V3 conclusion is not yet fully converged. Current single-seed evidence is
strong enough for the draft, and the major no-compute review fixes are already
in the paper. The task remains open until seed stability and relation-stress
evidence are available or the paper explicitly narrows the claim.
