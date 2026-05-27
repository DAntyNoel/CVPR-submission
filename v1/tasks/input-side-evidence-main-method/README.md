# Input-Side Evidence Main Method Task

Created: 2026-05-27

## 1. 目标

本任务用于把 Phase-2 中最稳的 `Input-Side Evidence DPO` 提升为下一版主改法候选，
解决当前 response-side `Evidence-Hint DPO` 结果偏负向的问题。

当前失败模式不是 evidence 完全无效，而是 response-side evidence hint 容易变成
保守偏置：false-positive rate 降一点，但 false-negative rate 上升，导致 Acc/F1
没有稳定超过 Answer-DPO。Input-Side Evidence 的核心想法是把轻量视觉证据放到
user-side context，让模型在训练时用证据条件化偏好判断，但 response 仍保持普通短答案。
这样可以降低训练 response 格式和最终 yes/no 评测格式之间的不匹配。

## 2. 方法定义

主方法候选命名：

```text
Input-Side Evidence DPO
```

与当前 Evidence-Hint DPO 的区别：

| 方法 | User-side input | Chosen response | Rejected response |
| --- | --- | --- | --- |
| Answer-DPO | 原始问题 | 正确短答案 | 错误短答案 |
| Response-side Evidence-Hint DPO | 原始问题 | 正确短答案 + evidence hint | 错误短答案 + unsupported hint |
| Input-Side Evidence DPO | 原始问题 + supported visual cue | 正确短答案 | 错误短答案 |

现有实现入口：

```text
scripts/data/04_export_dpo_formats.py::export_input_side_evidence
experiments/llamafactory_configs/qwen25vl_phase2_input_side_evidence_dpo.yaml
scripts/eval/run_vlm_inference.py model key: phase2_input_side_evidence_dpo
```

数据格式已经由 `export_input_side_evidence()` 实现：

```text
Visual cue: <supported evidence body>
```

会被附加到 user-side context；chosen/rejected response 仍然是普通答案文本。

## 3. 当前可复用产物

当前已经完成一轮 5k mixed Phase-2 Input-Side Evidence 实验，不需要重新跑才能做第一版分析。

训练产物：

```text
outputs/llamafactory/qwen25vl7b_phase2_input_side_evidence_dpo_zero2/
```

训练 job：

```text
64303  COMPLETED  Phase-2 Input-Side Evidence DPO train
```

评测产物：

```text
results/eval/generations/coco_heldout_object_existence/phase2/phase2_input_side_evidence_dpo.metrics.json
results/eval/generations/gqa_simple_heldout/phase2/phase2_input_side_evidence_dpo.metrics.json
results/eval/generations/coco_hard_object_existence/phase2/phase2_input_side_evidence_dpo.metrics.json
results/eval/generations/base_error_mined_object_existence/phase2/phase2_input_side_evidence_dpo.metrics.json
```

当前结果：

| Eval | Acc | F1 | FPR | FNR | Reading |
| --- | ---: | ---: | ---: | ---: | --- |
| COCO held-out | 0.961 | 0.960 | 0.016 | 0.062 | 与 Evidence-Hint 持平，FPR 低于 Answer-DPO |
| GQA simple | 0.768 | 0.747 | 0.150 | 0.314 | 与 Answer-DPO Acc 持平，F1 略低 |
| Hard COCO | 0.947 | 0.946 | 0.038 | 0.068 | 强于 response-side Evidence-Hint，但低于 Answer-DPO |
| Base-error-mined | 0.044 | 0.077 | 0.984 | 0.948 | 高于 Evidence-Hint，低于 Answer-DPO |

判读：Input-Side Evidence 是当前 evidence 变体中最稳的一组，但单独替换主方法还不够强。
它适合作为下一版主方法的结构基础，而不是直接宣称已经解决负结果。

## 4. Balanced Hard Input-Side Evidence 已完成

为了检验 Input-Side Evidence 能否作为下一版主改法，已完成小型增强版：

```text
Balanced Hard Input-Side Evidence DPO
```

它复用 Input-Side Evidence 格式，所有样本都把 `Visual cue:` 放在 user-side
context，chosen/rejected response 继续保持普通短答案，不再在 response 中追加
`Evidence:` 字段。

新增实现：

```text
tasks/input-side-evidence-main-method/build_input_side_main_balanced_hard_dpo.py
experiments/llamafactory_configs/qwen25vl_input_side_main_balanced_hard_dpo.yaml
experiments/slurm/train_input_side_main_balanced_hard_dpo.slurm
experiments/slurm/submit_input_side_main_balanced_hard_dpo.sh
scripts/eval/run_vlm_inference.py model key: input_side_main_balanced_hard_dpo
```

数据产物：

```text
data/processed/input_side_main_balanced_hard_dpo_train.jsonl
data/processed/input_side_main_balanced_hard_dpo_summary.json
experiments/llamafactory_data_input_side_main/cvpr_input_side_main_balanced_hard_dpo.json
experiments/llamafactory_data_input_side_main/dataset_info.json
```

数据构成：

| Source | Rows | Purpose |
| --- | ---: | --- |
| Hard COCO-style pairs | 1,000 | 增加 confusable absent-object 压力 |
| Base-error-mined pairs | 1,000 | 针对 Base 常见错误补强 |
| Canonical COCO paired rows | 2,500 | 保持主任务对象存在能力 |
| GQA anchors | 1,000 | 保留属性/关系泛化能力 |

总计 5,500 rows；其中 yes 2,250、no 2,250、non-yes/no GQA anchor 1,000。
`prompt_cue_rows=5500`，`response_evidence_rows=0`，unique images 为 2,791。

训练与主评测 jobs：

```text
64443  COMPLETED  Balanced Hard Input-Side Evidence DPO train
64444  COMPLETED  COCO held-out eval
64445  COMPLETED  GQA simple eval
64446  COMPLETED  Hard COCO eval
64447  COMPLETED  Base-error-mined eval
```

训练产物：

```text
outputs/llamafactory/qwen25vl7b_input_side_main_balanced_hard_dpo_zero2/
```

训练指标：1 epoch、172 steps、train loss 0.2708、runtime 1029.70s、
samples/sec 5.341。

主评测结果：

| Eval | Acc | F1 | FPR | FNR | Yes | Reading |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| COCO held-out | 0.966 | 0.965 | 0.018 | 0.050 | 0.484 | 高于 Answer-DPO 与 Phase-2 Input-Side |
| GQA simple | 0.766 | 0.748 | 0.162 | 0.306 | 0.428 | Acc 略低于 Answer-DPO，F1 持平左右 |
| Hard COCO | 0.947 | 0.947 | 0.048 | 0.058 | 0.495 | recall 改善，但 FPR 高于 Answer-DPO |
| Base-error-mined | 0.120 | 0.214 | 1.000 | 0.844 | 0.353 | recovery 明显高于其他 evidence 变体 |

外部 sanity check 也已完成：

```text
64457  COMPLETED  POPE random
64458  COMPLETED  POPE popular
64459  COMPLETED  POPE adversarial
64460  COMPLETED  AMBER discriminative
```

| Eval | Acc | F1 | FPR | FNR | Yes |
| --- | ---: | ---: | ---: | ---: | ---: |
| POPE random | 0.894 | 0.883 | 0.011 | 0.201 | 0.405 |
| POPE popular | 0.883 | 0.872 | 0.033 | 0.201 | 0.416 |
| POPE adversarial | 0.871 | 0.861 | 0.057 | 0.201 | 0.428 |
| AMBER discr. | 0.881 | 0.818 | 0.076 | 0.204 | 0.318 |

判读：Balanced Hard Input-Side Evidence 比 Phase-2 Input-Side 更像一个有效的
rescue run，主要收益来自更低 FNR 和更强 Base-error recovery；但 Hard COCO 与外部
POPE/AMBER 的 FPR/yes-bias 上升，说明它还没有稳定解决 false-positive control。
因此它适合写成 Input-Side placement 的增强诊断结果，而不是强 claim 主方法。

## 5. 与成功标准对照

| Eval | Required outcome |
| --- | --- |
| COCO held-out | 不低于 Answer-DPO 超过 0.2-0.3 pt |
| GQA simple | Acc/F1 不明显退化 |
| Hard COCO | FPR 低于 Answer-DPO，且 Acc/F1 接近或超过 Answer-DPO |
| Base-error-mined | recovery 明显高于 response-side Evidence-Hint，最好接近或超过 Answer-DPO |

实际结果：

- COCO held-out 达标：Acc 0.966，高于 Answer-DPO 0.961。
- GQA simple 基本可接受：Acc 0.766，略低于 Answer-DPO 0.768；F1 0.748 与 Answer-DPO 持平。
- Hard COCO 未完全达标：Acc/F1 接近，但 FPR 0.048 高于 Answer-DPO 0.040。
- Base-error-mined recovery 明显改善：0.120，高于 Evidence-Hint 0.030、Phase-2 Input-Side 0.044
  与 Answer-DPO 0.063。

结论：user-side evidence placement 和 hard-balanced 数据能改善 recall 与错误样本恢复，
但模板 evidence 仍不足以稳定改善 VLM preference tuning 的 false-positive control。

## 6. 已执行步骤

### Step 1: 固定现有 Input-Side 结果

已把 Phase-2 Input-Side 结果作为 baseline 记录，未覆盖：

```text
OUTPUT_VARIANT=phase2
MODEL_KEY=phase2_input_side_evidence_dpo
```

### Step 2: 论文快速改写试算

已完成现有 Input-Side 行的替换试算：

- COCO：Input-Side 与 Answer-DPO 持平，FPR 更低。
- GQA：Input-Side 与 Answer-DPO Acc 持平，F1 略低。
- Hard COCO：Input-Side 比 response-side Evidence-Hint 更好，但仍略低于 Answer-DPO。
- Base-error-mined：Input-Side 高于 response-side Evidence-Hint，但仍低于 Answer-DPO。

该叙事仍偏弱，因此进入 Step 3。

### Step 3: 构造 Balanced Hard Input-Side 数据

已使用独立名称，避免覆盖 Phase-2 默认产物：

```text
data/processed/input_side_main_balanced_hard_dpo_train.jsonl
experiments/llamafactory_data_input_side_main/cvpr_input_side_main_balanced_hard_dpo.json
```

脚本直接构造 paired input-side DPO rows，并写出独立 LLaMA-Factory registry。

### Step 4: 训练

训练已通过 Slurm 完成，未在交互环境启动 7B GPU 任务：

```text
experiments/llamafactory_configs/qwen25vl_input_side_main_balanced_hard_dpo.yaml
experiments/slurm/train_input_side_main_balanced_hard_dpo.slurm
experiments/slurm/submit_input_side_main_balanced_hard_dpo.sh
```

输出目录：

```text
outputs/llamafactory/qwen25vl7b_input_side_main_balanced_hard_dpo_zero2/
```

### Step 5: 评测

评测沿用普通 yes/no prompt，避免把收益写成 prompt engineering：

```text
COCO held-out
GQA simple
Hard COCO
Base-error-mined diagnostic
POPE/AMBER external sanity check
```

输出变体：

```text
OUTPUT_VARIANT=input_side_main
OUTPUT_VARIANT=input_side_main_external
```

## 7. 论文写法

如果采用 Input-Side Evidence 作为主改法，标题和贡献可以改成：

```text
A Controlled Study of Input-Side Evidence for VLM Preference Tuning
```

推荐 claim：

```text
Moving lightweight evidence from the response into the user-side training
context reduces the format mismatch of evidence-augmented preference tuning.
In our controlled setting, this placement is more stable than response-side
evidence hints, but the gains remain limited without harder and better-balanced
evidence supervision.
```

增强版完成后，推荐更具体地写成：

```text
Hard-balanced input-side evidence improves recall and recovery from base-model
errors, but it also increases false positives on the hard and external
benchmarks. This suggests that evidence placement helps with response-format
mismatch, while template-level cues remain too weak to provide reliable
false-positive control.
```

不推荐 claim：

```text
Input-Side Evidence solves object hallucination.
```

## 8. 当前决策

Balanced Hard Input-Side Evidence 的所有计划实验已完成。当前建议：

- 不再重复提交同一组 GPU 训练或主评测。
- 如果论文要保持三组主表，可把第三组从 response-side Evidence-Hint 改成
  Balanced Hard Input-Side Evidence DPO，但结论必须写成受控诊断，而不是强正向。
- 更稳妥的写法是：Input-Side placement 与 hard-balanced 数据改善 FNR/recovery，
  但 false-positive control 仍未稳定超过 Answer-DPO。

本任务的定位已经从“待启动主改法候选”更新为“已完成的 rescue/diagnostic 方案”。
