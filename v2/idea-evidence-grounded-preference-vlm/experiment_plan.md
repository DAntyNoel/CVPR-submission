# CEPO 实验计划

更新日期：2026-05-27

## 0. 总体原则

本计划仿照 V1 的 `idea-lightweighted-grounded-preference-vlm/` 组织方式，但研究问题已经改变：

```text
V1: response 里加入 template evidence hint 是否优于 Answer-DPO？
V2: claim-evidence preference 是否比 answer-only preference 更能约束视觉断言？
```

所有重任务都必须通过 Slurm 提交。交互环境只做轻量数据构造、schema 检查、dry-run、文档整理。

## 1. 阶段划分

| Stage | 目标 | 产物 | 是否训练 |
| --- | --- | --- | --- |
| S0 | 固定 V1 资产与新 schema | reusable assets + schema draft | 否 |
| S1 | 构造 5k-6k CEPO 数据 | canonical + Answer-DPO + CEPO-Latent JSONL | 否 |
| S2 | 数据审计与泄漏检查 | audit csv/summary + overlap report | 否 |
| S3 | 训练主三组 | Base registry check, Answer-DPO, CEPO-Latent | 是 |
| S4 | 复用 V1 主评测 | COCO/GQA/Hard COCO/Base-error/POPE/AMBER | 是，推理 |
| S5 | 新增 evidence-probe eval | evidence correctness + wrong-evidence rejection | 是，推理 |
| S6 | 论文收口 | 6 页诊断或正向小结论 | 否 |

## 2. 数据构造计划

### 2.1 输入来源

优先复用现有本地数据：

```text
COCO train2017 annotations/images
GQA scene graphs and prepared VG images
data/processed/canonical_pairs_main.jsonl
data/eval/* held-out splits
```

第一版不引入大规模新下载。RefCOCO 可以作为后续增强，不进入主线第一轮。

### 2.2 输出路径

为避免覆盖 V1 产物，建议新建 v2 sidecar 目录：

```text
data/processed/cepo/
  claim_evidence_canonical.jsonl
  answer_dpo_train.jsonl
  cepo_latent_dpo_train.jsonl
  claim_evidence_audit_200.csv
  claim_evidence_summary.json
  leakage_report.json

experiments/llamafactory_data_cepo/
  cvpr_cepo_answer_dpo.json
  cvpr_cepo_latent_dpo.json
  dataset_info.json
```

训练输出：

```text
outputs/llamafactory/qwen25vl7b_cepo_answer_dpo_zero2/
outputs/llamafactory/qwen25vl7b_cepo_latent_dpo_zero2/
```

评测输出：

```text
results/eval/generations/<eval_name>/cepo/<model_key>.jsonl
results/eval/generations/<eval_name>/cepo_evidence_probe/<model_key>.jsonl
```

### 2.3 Canonical 样本字段

最小字段：

```json
{
  "id": "cepo_000001",
  "source": "coco|gqa",
  "image": "path/to/image.jpg",
  "image_id": "stable_image_id",
  "task_type": "object_existence|attribute_color|relation_spatial|wrong_evidence",
  "question": "Is there a bus in the image?",
  "chosen_answer": "Yes, there is a bus in the image.",
  "rejected_answer": "No, there is no bus in the image.",
  "chosen_claims": [],
  "rejected_claims": [],
  "negative_type": "answer_wrong|evidence_wrong|attribute_mismatch|relation_reversal"
}
```

Claim 字段：

```json
{
  "span": "bus visible",
  "type": "object",
  "support": "supported|contradicted|wrong_evidence",
  "evidence": [
    {
      "role": "target",
      "label": "bus",
      "box": [0.10, 0.20, 0.50, 0.70]
    }
  ],
  "attribute": null,
  "relation": null
}
```

### 2.4 样本配比

默认 6k：

| Slice | Rows | Negative type | Notes |
| --- | ---: | --- | --- |
| COCO object | 2,000 | object absent / wrong object | 复用 V1 object pipeline，并保留 COCO box。 |
| GQA attribute | 1,500 | attribute mismatch | color/material 优先。 |
| GQA relation | 1,500 | left/right reversal | 只保留方向明确关系。 |
| Wrong-evidence | 1,000 | answer same, evidence wrong | V2 核心诊断样本。 |

如果图像或 scene graph 准备不顺，降级到 5k：

```text
1,800 COCO object
1,300 GQA attribute
1,200 GQA relation
700 wrong-evidence
```

### 2.5 训练格式

Answer-DPO 导出：

```text
Prompt: <image> + question
Chosen: short correct answer
Rejected: short wrong answer
```

CEPO-Latent 导出：

```text
Prompt: <image> + question
Chosen: short answer + compact Claims block
Rejected: short answer + contradicted/wrong Claims block
```

Claims block 建议保持短、稳定、易解析：

```text
Answer: Yes, there is a bus in the image.
Claims:
- type: object
  claim: bus visible
  evidence: bus
  support: supported
```

第一轮不把完整 box 坐标放进训练文本，避免模型把坐标格式学成噪声。box 保留在 canonical metadata 和 evidence-probe scorer 中。

## 3. 数据审计

### 3.1 自动检查

必须检查：

- 训练与 eval image overlap 为 0。
- chosen/rejected answer 不为空。
- chosen/rejected claims 数量合法。
- wrong-evidence rows 的 answer 相同或语义等价。
- relation rows 的 subject/object 都有 evidence。
- attribute rows 的 attribute value 不相等。

### 3.2 人工抽查

抽查 200 条：

| Field | Gate |
| --- | --- |
| chosen answer correctness | >= 90% |
| rejected answer wrongness | >= 85% |
| chosen evidence correctness | >= 90% |
| rejected evidence error correctness | >= 85% |
| relation direction correctness | >= 85% |

如果 evidence precision 不达标，先修数据，不启动训练。

## 4. 训练计划

### 4.1 主三组

| Group | Model key | Adapter | Notes |
| --- | --- | --- | --- |
| Base Instruct | `base` | none | 复用 Qwen2.5-VL-7B-Instruct。 |
| Answer-DPO | `cepo_answer_dpo` | `qwen25vl7b_cepo_answer_dpo_zero2` | 与 CEPO 使用同一 canonical split。 |
| CEPO-Latent | `cepo_latent_dpo` | `qwen25vl7b_cepo_latent_dpo_zero2` | 唯一主方法。 |

训练配置沿用 V1：

```text
Qwen2.5-VL-7B-Instruct
LoRA-DPO
ZeRO-2
1 epoch
pref_beta = 0.1
LoRA rank = 16
```

### 4.2 Slurm 约束

不在当前 shell 直接启动 7B 训练。建议新增独立脚本：

```text
experiments/slurm/submit_cepo_main.sh
experiments/slurm/train_cepo_answer_dpo.slurm
experiments/slurm/train_cepo_latent_dpo.slurm
```

训练脚本应先 dry-run 检查：

- dataset registry 指向 `experiments/llamafactory_data_cepo/`。
- adapter 输出目录不存在或明确允许覆盖。
- `adapter_config.json` 和 `adapter_model.safetensors` 在训练后存在。

## 5. 评测计划

### 5.1 短答案主评测

复用 V1 eval：

| Eval | Purpose | Output variant |
| --- | --- | --- |
| COCO held-out | standard object existence | `cepo` |
| GQA simple | attribute/relation transfer | `cepo` |
| Hard COCO | hard absent-object FPR | `cepo` |
| Base-error-mined | repair base mistakes | `cepo` |
| POPE random/popular/adversarial | external object hallucination | `cepo_external` |
| AMBER discriminative | external existence/attribute/relation | `cepo_external` |

Prompt 仍使用普通 short yes/no，避免把主收益写成 prompt engineering。

### 5.2 Evidence-Probe Eval

新增 eval 文件可以从 canonical held-out 中派生：

```text
data/eval/cepo_evidence_probe.jsonl
data/eval/cepo_wrong_evidence_probe.jsonl
```

Prompt:

```text
Answer yes or no. Then provide one claim and the visual evidence label.
```

输出示例：

```json
{
  "answer": "yes",
  "claim": "bus visible",
  "evidence_label": "bus",
  "support": "supported"
}
```

Scoring:

- answer accuracy。
- evidence label exact/alias match。
- relation direction accuracy。
- wrong-evidence rejection accuracy。
- invalid JSON rate。

如果 JSON 输出不稳定，降级为 line-based format，不用 LLM judge 作为第一版主 scorer。

## 6. 实验矩阵

### 必做

| ID | Experiment | Goal | Success gate |
| --- | --- | --- | --- |
| E0 | Data audit | 验证 claim-evidence 数据质量 | chosen evidence >= 90%。 |
| E1 | Main short-answer eval | 比较 Base/Answer/CEPO | CEPO 不降低 Acc/F1，同时改善至少一个 FPR 或 relation/attribute 指标。 |
| E2 | Evidence-probe eval | 验证 evidence consistency | wrong-evidence rejection 明显优于 Answer-DPO。 |
| E3 | Base-error diagnostic | 看是否修复旧失败样本 | recovery 高于 V1 Evidence-Hint。 |
| E4 | External sanity | 防止只过拟合自建集 | POPE/AMBER 不明显退化。 |

### 可选

| ID | Experiment | Trigger |
| --- | --- | --- |
| A1 | Remove wrong-evidence negatives | 只有 E1/E2 有正向信号时才做。 |
| A2 | Evidence text with box coordinates | 只有 evidence-probe 明显需要定位细节时才做。 |
| A3 | Qwen2.5-VL-3B smoke model | 只有 7B 调试成本过高时才做。 |

可选项不进入主表；主表仍保持三组。

## 7. 结果解释路径

### Plan A: 正向小结论

如果 CEPO-Latent 同时改善短答案和 evidence-probe：

```text
Claim-evidence preference provides a stronger grounding signal than
response-level evidence hints, improving relation/attribute evidence
consistency without introducing over-refusal.
```

### Plan B: 诊断结论

如果 CEPO 只提升 evidence-probe，不提升短答案：

```text
Claim-evidence preference teaches verifiable evidence behavior, but latent
transfer to short yes/no hallucination remains limited.
```

### Plan C: 负结果

如果 CEPO 退化：

```text
Structured evidence supervision is sensitive to annotation quality and format
mismatch; high-quality evidence and better decoding interfaces are required
before it can improve short-answer hallucination.
```

Plan B/C 也可写，但不能过度包装成方法胜出。

## 8. 15 天排期

| Day | Task |
| --- | --- |
| 1 | 固定 schema，确认 COCO/GQA evidence 字段可读。 |
| 2-3 | 构造 5k-6k canonical CEPO 数据与两个 DPO 导出。 |
| 4 | 自动检查与 200 条审计。 |
| 5 | LLaMA-Factory registry、训练 dry-run、Slurm 脚本。 |
| 6 | 提交 Answer-DPO 与 CEPO-Latent 训练。 |
| 7 | adapter 完整性检查，提交 COCO/GQA/Hard COCO/Base-error eval。 |
| 8 | 提交 POPE/AMBER 外部 sanity eval。 |
| 9 | 构造并运行 evidence-probe eval。 |
| 10 | 汇总指标，做 FPR/FNR 和 evidence consistency 分析。 |
| 11 | 挑 case study，检查是否有 format leakage。 |
| 12-13 | 写 paper outline 与主表。 |
| 14 | 编译 PDF，控制正文 5-6 页。 |
| 15 | 收尾 README、实验摘要和 appendix。 |

## 9. Stop Rules

满足任一情况就停止扩展实验，直接写诊断：

- 数据审计 chosen evidence precision 低于 90%，且一天内无法修好。
- CEPO 短答案 Acc/F1 明显低于 Answer-DPO，并且 FPR 没有补偿性改善。
- evidence-probe invalid rate 高于 20%。
- 外部 POPE/AMBER 明显退化，说明方法只学了格式。
- 新增实验会使主表超过三组或正文超过 6 页。
