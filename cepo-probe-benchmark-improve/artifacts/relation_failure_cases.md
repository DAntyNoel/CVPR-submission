# Relation Wrong-Evidence Failure Cases

These samples are drawn from the locked CEPO wrong-evidence relation slice. Categories are heuristic triage labels for writing the analysis section.

## CEPO-Dual correctly rejects relation wrong-evidence

| ID | Category | Claim | Candidate evidence | Base | Answer-DPO | CEPO-Dual-2k |
| --- | --- | --- | --- | --- | --- | --- |
| cepo_wrong_ev_000836_probe_000152 | subject/object swap | pepper left_of bottle | subject=bottle; object=pepper; relation=left_of | accept/supported | accept/supported | reject/contradicted |
| cepo_wrong_ev_000244_probe_000132 | subject/object swap | jacket right_of entrance | subject=entrance; object=jacket; relation=right_of | accept/supported | accept/supported | reject/contradicted |
| cepo_wrong_ev_000500_probe_000283 | subject/object swap | man left_of girl | subject=girl; object=man; relation=left_of | accept/supported | accept/supported | reject/wrong_evidence |
| cepo_wrong_ev_000533_probe_000128 | subject/object swap | ear right_of lake | subject=lake; object=ear; relation=right_of | accept/supported | accept/supported | reject/contradicted |

## CEPO-Dual falsely accepts relation wrong-evidence

| ID | Category | Claim | Candidate evidence | Base | Answer-DPO | CEPO-Dual-2k |
| --- | --- | --- | --- | --- | --- | --- |
| cepo_wrong_ev_000313_probe_000365 | subject/object swap | drinks right_of soda | subject=soda; object=drinks; relation=right_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000681_probe_000148 | subject/object swap | refrigerator left_of shelf | subject=shelf; object=refrigerator; relation=left_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000005_probe_000263 | subject/object swap | cooler right_of uniform | subject=uniform; object=cooler; relation=right_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000274_probe_000185 | subject/object swap | umbrella left_of van | subject=van; object=umbrella; relation=left_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000524_probe_000236 | subject/object swap | mouse pad right_of keyboard | subject=keyboard; object=mouse pad; relation=right_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000391_probe_000002 | subject/object swap | man right_of parking meter | subject=parking meter; object=man; relation=right_of | accept/supported | accept/supported | accept/supported |

## All models fail

| ID | Category | Claim | Candidate evidence | Base | Answer-DPO | CEPO-Dual-2k |
| --- | --- | --- | --- | --- | --- | --- |
| cepo_wrong_ev_000379_probe_000378 | subject/object swap | lamp right_of building | subject=building; object=lamp; relation=right_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000259_probe_000324 | subject/object swap | table left_of pole | subject=pole; object=table; relation=left_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000335_probe_000171 | subject/object swap | frame right_of bookshelf | subject=bookshelf; object=frame; relation=right_of | accept/supported | accept/supported | accept/supported |
| cepo_wrong_ev_000876_probe_000108 | subject/object swap | tree right_of bus | subject=bus; object=tree; relation=right_of | accept/supported | accept/supported | accept/supported |

## Answer-DPO fails but CEPO-Dual succeeds

| ID | Category | Claim | Candidate evidence | Base | Answer-DPO | CEPO-Dual-2k |
| --- | --- | --- | --- | --- | --- | --- |
| cepo_wrong_ev_000406_probe_000008 | subject/object swap | shirt left_of hose | subject=hose; object=shirt; relation=left_of | accept/supported | accept/supported | reject/contradicted |
| cepo_wrong_ev_000459_probe_000330 | subject/object swap | curtain left_of arm | subject=arm; object=curtain; relation=left_of | accept/supported | accept/supported | reject/contradicted |
| cepo_wrong_ev_000526_probe_000153 | subject/object swap | hair left_of uniform | subject=uniform; object=hair; relation=left_of | accept/supported | accept/supported | reject/contradicted |
| cepo_wrong_ev_000523_probe_000167 | subject/object swap | tree left_of leaves | subject=leaves; object=tree; relation=left_of | reject/wrong_evidence | accept/supported | reject/wrong_evidence |

## Takeaway

Relation wrong-evidence rejection remains the bottleneck: CEPO-Dual improves the overall rejection rate, but many relation cases still accept swapped subject/object evidence. This supports the paper claim that answer-level correctness and evidence-level verification can move independently, and that relation verification likely needs stronger region-aware supervision.
