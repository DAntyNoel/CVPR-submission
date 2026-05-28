# 证据绑定的 VLM 偏好优化项目大纲

更新日期：2026-05-27

## 0. 目标定位

V1 已经说明：在 DPO 的 response 里追加模板化 `Evidence hint:` 只能带来很小的 false-positive 变化，不能稳定超过 Answer-DPO。下一版不继续调模板，而是换一个更明确的研究问题：

> VLM 偏好优化是否应该从回答级偏好，升级为“回答中的视觉断言必须绑定可验证证据”的 claim-evidence preference？

本项目仍保持小规模 CVPR 示例投稿风格：

- 主实验不超过三组。
- 不改模型结构。
- 不训练额外 reward model 作为主方法。
- 数据构造控制在 5k-8k preference pairs。
- 训练仍基于 Qwen2.5-VL-7B、LoRA-DPO、ZeRO-2。
- 正文目标不超过 6 页。

## 1. 暂定标题

英文：

**Claim-Evidence Preference Optimization for Grounded Vision-Language Alignment**

简称：

```text
CEPO: Claim-Evidence Preference Optimization
```

中文工作名：

**面向视觉证据绑定的 VLM 偏好优化**

## 2. 核心判断

V1 的失败模式不是 evidence 完全无效，而是 template hint 太弱：

- 模型可能把 hint 学成回答风格。
- DPO 的主要边界变化表现为 yes/no bias，而不是视觉证据检查能力。
- 只降低 FPR 时，FNR 常常上升，导致 Acc/F1 不稳定。

V2 的核心改动是让 preference pair 显式区分：

1. 答案是否正确。
2. 答案里的视觉 claim 是否有证据。
3. 证据是否指向正确对象、属性或关系。

也就是说，chosen 不只是“回答对”，而是：

```text
answer correct + claim supported + evidence matched
```

rejected 可以是：

```text
answer wrong
answer correct but evidence wrong
claim unsupported
relation direction reversed
attribute mismatched
```

## 3. 方法概述

### 3.1 Answer-DPO Baseline

沿用 V1 的标准回答级 DPO：

```text
Image + Question
Chosen: short correct answer
Rejected: short incorrect answer
```

### 3.2 CEPO-Latent

训练时让 chosen/rejected 都包含结构化 claim-evidence block；推理主评测时仍只要求短答案。

示例：

```text
Question: Is the red cup to the left of the plate?

Chosen:
Yes, the red cup is to the left of the plate.
Claims:
- claim: red cup left of plate
  type: relation
  evidence: cup box + plate box + relation left_of
  support: supported

Rejected:
Yes, the red cup is to the right of the plate.
Claims:
- claim: red cup right of plate
  type: relation
  evidence: cup box + plate box + relation right_of
  support: contradicted
```

关键点：

- 仍使用标准 DPO loss。
- 不引入新网络结构。
- 不要求主评测输出 evidence。
- 另设 evidence-probe eval，专门检查模型是否学到证据一致性。

### 3.3 Wrong-Evidence Negatives

这是 V2 相比 V1 最重要的新增负样本。

旧 Evidence-Hint 主要区分答案对错；V2 必须加入答案相同但 evidence 错的 pair：

```text
Chosen:
Yes, there is a bus.
Claims:
- claim: bus visible
  evidence: bus box
  support: supported

Rejected:
Yes, there is a bus.
Claims:
- claim: bus visible
  evidence: truck box
  support: wrong_evidence
```

这样 DPO 不能只靠 yes/no 或答案文本区分 chosen/rejected，必须利用 evidence consistency。

## 4. 数据设计

第一版只做 2D 图像，不做 3D。

推荐 6k preference pairs：

| Slice | Rows | Evidence | Purpose |
| --- | ---: | --- | --- |
| COCO object existence | 2,000 | object label + box | 保留 V1 对象存在主线。 |
| GQA color/material attribute | 1,500 | object + attribute value | 测属性 evidence。 |
| GQA left/right relation | 1,500 | subject/object + relation edge | 测空间关系 evidence。 |
| Wrong-evidence pairs | 1,000 | deliberately mismatched evidence | 强制学习 evidence consistency。 |

保守版本可缩到 5k，总原则是 relation 和 wrong-evidence 不要被压得太少。

### 4.1 Canonical Schema

建议新增中间格式：

```json
{
  "id": "cepo_gqa_rel_000001",
  "source": "gqa",
  "image": "data/raw/gqa/images/123.jpg",
  "task_type": "relation_spatial",
  "question": "Is the cup to the left of the plate?",
  "chosen_answer": "Yes, the cup is to the left of the plate.",
  "rejected_answer": "No, the cup is not to the left of the plate.",
  "claims": [
    {
      "span": "cup to the left of the plate",
      "type": "relation",
      "support": "supported",
      "evidence": [
        {"role": "subject", "label": "cup", "box": [0.12, 0.30, 0.24, 0.50]},
        {"role": "object", "label": "plate", "box": [0.42, 0.33, 0.58, 0.55]}
      ],
      "relation": "left_of"
    }
  ],
  "negative_type": "relation_reversal"
}
```

如果 box 质量不稳定，第一版可以只训练文本化 evidence，保留 box 用于审计和 evidence eval。

## 5. 主实验设计

严格三组：

| Group | Method | Training Data | Eval Output |
| --- | --- | --- | --- |
| A | Base Instruct | none | short answer |
| B | Answer-DPO | answer-only pairs | short answer |
| C | CEPO-Latent | answer + claim-evidence pairs | short answer |

不把 SFT、CEPO-Explicit、critic rerank、多 backbone 放进主表。它们可以作为后续方向，但不进入本版主实验。

## 6. 评测设计

### 6.1 短答案主评测

继续复用 V1 的评测链路：

- COCO held-out object existence。
- GQA simple held-out。
- Hard COCO held-out。
- POPE random/popular/adversarial。
- AMBER discriminative。
- Base-error-mined diagnostic。

主要指标：

```text
Acc / BAcc / F1 / FPR / FNR / yes rate / other rate
```

### 6.2 Evidence-Probe 评测

新增一个轻量 evidence-probe，不作为主表唯一结论，但必须用来证明 V2 确实比 V1 更“看证据”。

Prompt：

```text
Answer yes or no, then list one visual claim and its evidence.
```

或更结构化：

```text
Return JSON with answer, claim, evidence_label, support.
```

指标：

- claim answer accuracy。
- evidence label match。
- relation direction accuracy。
- wrong-evidence rejection accuracy。
- invalid JSON / other rate。

第一版不要用闭源 LLM judge 做主评分；优先用 COCO/GQA annotations 规则评分。

## 7. 成功标准

CEPO-Latent 只有在同时满足以下多数条件时，才值得作为新主线：

| Eval | Gate |
| --- | --- |
| COCO held-out | Acc 不低于 Answer-DPO，FPR 不升高。 |
| GQA simple | attribute/relation 子集至少一个明显优于 Answer-DPO。 |
| Hard COCO | FPR 不高于 Answer-DPO，FNR 不明显恶化。 |
| Base-error-mined | recovery 高于 V1 Evidence-Hint，最好接近或超过 Answer-DPO。 |
| Evidence-probe | wrong-evidence rejection 明显高于 answer-only baseline。 |
| Format | other/invalid rate 接近 0，短答案评测不泄漏 evidence block。 |

如果 CEPO 只提升 evidence-probe，不提升短答案 hallucination，则论文写成诊断结论：

> Claim-evidence supervision improves verifiable evidence behavior, but latent transfer to short-answer hallucination remains limited.

这仍然比继续调 V1 模板更有研究价值。

## 8. 与 V1 的关系

V1 是必要的前置诊断：

- 它证明 response-level template hint 不够。
- 它提供了稳定的 Answer-DPO baseline。
- 它留下了 Hard COCO、Base-error-mined、POPE/AMBER 等压力测试。
- 它提醒 V2 必须报告 FPR/FNR，而不能只看 accuracy。

V2 不应继续声称“轻量 evidence hint 改善 hallucination”。更准确的主张是：

> Answer-level preference is too coarse for visual grounding. Preference data should explicitly distinguish correct answers from verifiable claim-evidence support.

## 9. 执行边界

本项目暂不做：

- 多 backbone。
- 多 seed。
- 3D scene understanding。
- 全参微调。
- 训练额外 critic 作为主方法。
- 使用商业 API 生成大规模训练标签。

这些可以保留在 future work，但不能进入当前 6 页主线。
