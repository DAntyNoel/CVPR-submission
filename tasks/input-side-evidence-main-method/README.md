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

## 4. 最小晋升方案

如果需要把论文主改法从 response-side Evidence-Hint 改为 Input-Side Evidence，
建议只做以下最小变更，不新增第四组：

```text
Base Instruct
Answer-DPO
Input-Side Evidence DPO
```

需要改动的内容：

1. 将论文方法部分的 evidence placement 从 response-side 改为 user-side context。
2. 主表第三行使用 `phase2_input_side_evidence_dpo` 的现有结果。
3. 把 response-side Evidence-Hint DPO 降级为 ablation 或 diagnostic side result。
4. 保留三组主实验，不引入 Evidence-Only、Chosen-Only 或额外 backbone。
5. 明确写作口径：Input-Side Evidence 减少格式不匹配，但当前 5k 结果仍只是接近 Answer-DPO，
   尚不足以支撑强正向 claim。

这个最小晋升方案的优点是成本最低，且不需要重新训练；缺点是结果仍偏弱，
论文仍更像 diagnostic study。

## 5. 推荐增强方案

为了真正解决结果偏负向的问题，建议在 Input-Side Evidence 的基础上做一个小型增强版：

```text
Balanced Hard Input-Side Evidence DPO
```

核心原则：

- 仍保持三组主实验，不新增方法组。
- 数据量控制在 5k 到 6k，不做大规模扩张。
- 复用 Input-Side Evidence 格式，response 继续保持普通短答案。
- 训练样本中增加 Hard COCO 和 Base-error-mined 风格样本，但必须保持 yes/no 与
  present/absent 证据平衡，避免模型只学会保守回答 no。

推荐数据构成：

| Source | Rows | Purpose |
| --- | ---: | --- |
| Original mixed COCO/GQA | 3,500-4,000 | 保持主任务覆盖和稳定性 |
| Hard COCO-style pairs | 800-1,000 | 增加 confusable absent-object 压力 |
| Base-error-mined positives/negatives | 500-1,000 | 针对 Base 常见错误补强 |

成功标准应提前写死：

| Eval | Required outcome |
| --- | --- |
| COCO held-out | 不低于 Answer-DPO 超过 0.2-0.3 pt |
| GQA simple | Acc/F1 不明显退化 |
| Hard COCO | FPR 低于 Answer-DPO，且 Acc/F1 接近或超过 Answer-DPO |
| Base-error-mined | recovery 明显高于 response-side Evidence-Hint，最好接近或超过 Answer-DPO |

如果增强版失败，结论应写成：user-side evidence placement 缓解了 response-format mismatch，
但模板 evidence 仍不足以稳定改善 VLM preference tuning。

## 6. 实施步骤

### Step 1: 固定现有 Input-Side 结果

先把已完成的 Phase-2 Input-Side 结果作为 baseline 记录，不要覆盖：

```text
OUTPUT_VARIANT=phase2
MODEL_KEY=phase2_input_side_evidence_dpo
```

### Step 2: 论文快速改写试算

在不重训的前提下，先用现有 Input-Side 行替换主表第三行，检查叙事是否更自然：

- COCO：Input-Side 与 Answer-DPO 持平，FPR 更低。
- GQA：Input-Side 与 Answer-DPO Acc 持平，F1 略低。
- Hard COCO：Input-Side 比 response-side Evidence-Hint 更好，但仍略低于 Answer-DPO。
- Base-error-mined：Input-Side 高于 response-side Evidence-Hint，但仍低于 Answer-DPO。

如果这版叙事仍然太弱，再进入 Step 3。

### Step 3: 构造 Balanced Hard Input-Side 数据

新增数据文件建议使用独立名称，避免覆盖 Phase-2 默认产物：

```text
data/processed/input_side_main_balanced_hard_dpo_train.jsonl
experiments/llamafactory_data_input_side_main/cvpr_input_side_main_balanced_hard_dpo.json
```

需要的脚本改动应优先复用现有函数：

```text
scripts/data/04_export_dpo_formats.py::export_input_side_evidence
scripts/experiments/prepare_llamafactory_data.py
```

### Step 4: 训练

训练必须通过 Slurm，不要在交互环境启动 7B GPU 任务。建议复制现有 ZeRO-2 配置为：

```text
experiments/llamafactory_configs/qwen25vl_input_side_main_balanced_hard_dpo.yaml
experiments/slurm/train_input_side_main_balanced_hard_dpo.slurm
```

输出目录：

```text
outputs/llamafactory/qwen25vl7b_input_side_main_balanced_hard_dpo_zero2/
```

### Step 5: 评测

评测仍沿用普通 yes/no prompt，避免把收益写成 prompt engineering：

```text
COCO held-out
GQA simple
Hard COCO
Base-error-mined diagnostic
POPE/AMBER optional external sanity check
```

建议输出变体：

```text
OUTPUT_VARIANT=input_side_main
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

不推荐 claim：

```text
Input-Side Evidence solves object hallucination.
```

## 8. 当前决策

短期建议：

- 不马上提交新 GPU 训练。
- 先用现有 Phase-2 Input-Side 结果做一次论文主表替换试算。
- 如果仍不足以支撑更强结论，再启动 Balanced Hard Input-Side Evidence DPO。

本任务的定位是“主改法候选与 rescue 方案”，不是新增第四个主实验组。
