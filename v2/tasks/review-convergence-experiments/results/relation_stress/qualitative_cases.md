# Relation-Stress Qualitative Cases

Generated from completed jobs 64682, 64683, and 64684.

## CEPO-Dual Fixes Answer-DPO False Accepts

| ID | Stress type | Claim | Wrong evidence | Base | Answer-DPO | CEPO-Dual-2k |
| --- | --- | --- | --- | --- | --- | --- |
| `relation_stress_000005` | subject/object swap | `man right_of girl` | `girl right_of man` | supported | supported | contradicted |
| `relation_stress_000013` | subject/object swap | `cds left_of glass` | `glass left_of cds` | supported | supported | contradicted |
| `relation_stress_000019` | subject/object swap | `sky left_of number` | `number left_of sky` | supported | supported | contradicted |

## Remaining All-Model False Accepts

| ID | Stress type | Claim | Wrong evidence | Base | Answer-DPO | CEPO-Dual-2k |
| --- | --- | --- | --- | --- | --- | --- |
| `relation_stress_000002` | subject/object swap | `pole left_of weeds` | `weeds left_of pole` | supported | supported | supported |
| `relation_stress_000003` | subject/object swap | `cat right_of luggage` | `luggage right_of cat` | supported | supported | supported |
| `relation_stress_000008` | subject/object swap | `hands left_of paper` | `paper left_of hands` | supported | supported | supported |

## Easy Left/Right Reversal Rejects

| ID | Stress type | Claim | Wrong evidence | Base | Answer-DPO | CEPO-Dual-2k |
| --- | --- | --- | --- | --- | --- | --- |
| `relation_stress_000001` | left/right reversal | `box left_of jeans` | `box right_of jeans` | contradicted | contradicted | contradicted |
| `relation_stress_000004` | left/right reversal | `locomotive right_of leaves` | `locomotive left_of leaves` | contradicted | contradicted | contradicted |
| `relation_stress_000006` | left/right reversal | `horse left_of boot` | `horse right_of boot` | contradicted | contradicted | contradicted |

Takeaway: CEPO-Dual-2k improves relation stress overall, but the real residual
failure is subject/object role swapping. The paper should avoid implying that
pure left/right reversal is still equally hard after this stress test.
