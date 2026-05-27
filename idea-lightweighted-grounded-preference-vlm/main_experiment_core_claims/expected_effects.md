# 预期效果与实际结论

更新日期：2026-05-27

## 1. 核心预期与当前实际结果

本文希望支持的最小结论是：

> 在 mixed COCO/GQA 偏好数据上，Evidence-Hint DPO 相比普通 Answer-DPO 能更有效地降低对象存在、简单属性和左右空间关系中的视觉幻觉，且收益不是由更高拒答率带来的。

这个结论必须以 mixed 数据重训后的正式评测结果为准。旧的 64167/64168 adapter 来自 COCO-only 数据，只能作为 preliminary run；当前 mixed 数据构造和自动检查通过，不能单独证明方法有效。

2026-05-27 的正式 mixed 结果不满足这个强结论。Evidence-Hint DPO 与 Answer-DPO 在普通 COCO held-out 上 Acc 同为 0.961，FPR 略低 0.016 vs. 0.018；但 GQA simple 为 0.766 vs. 0.768，Hard COCO 为 0.946 vs. 0.950，Base-error-mined recovery 为 0.030 vs. 0.063。因此当前论文应采用“模板化 evidence hint 的增益有限”的诊断型结论。

## 2. 理想结果形态

如果实验顺利，预期看到以下趋势：

| 对比 | 预期变化 | 解释 |
| --- | --- | --- |
| Evidence-Hint DPO vs Base | POPE/COCO/GQA 指标上升 | 偏好优化整体改善简单视觉判断 |
| Evidence-Hint DPO vs Answer-DPO | POPE F1、COCO Acc 或 GQA Simple Acc 小幅上升 | evidence hint 提供了比纯回答更明确的视觉依据信号 |
| Evidence-Hint DPO vs Answer-DPO | False positive rate 下降 | 不存在对象被回答为存在的情况减少 |
| Evidence-Hint DPO vs Answer-DPO | Attribute mismatch 下降 | 颜色/材质类错误减少 |
| Evidence-Hint DPO vs Answer-DPO | Left/right reversal 下降 | 简单空间关系答反减少 |
| Evidence-Hint DPO vs Answer-DPO | Refusal rate 基本不变 | 方法收益不是来自过度保守 |
| Evidence-Hint DPO vs Answer-DPO | Yes bias 不明显升高 | 模型没有简单学会更多回答 yes |

可接受的提升幅度不需要很大。对这篇小规模示例投稿来说，只要 Evidence-Hint DPO 相比 Answer-DPO 在 POPE/COCO 或 GQA simple 上有 1-3 points 的提升，并且 false positive、attribute mismatch 或 left/right reversal 等错误同步下降，就可以支撑基础结论。若收益只出现在 COCO/POPE 而不出现在 GQA，应把论文结论收窄为对象存在类幻觉。

## 3. 正常结果判定

结果可以视为正常的条件：

1. Evidence-Hint DPO 的 POPE/COCO/GQA 主指标不低于 Answer-DPO，最好有小幅提升。
2. Evidence-Hint DPO 的 false positive、attribute mismatch 或 left/right reversal 至少有一类低于 Answer-DPO。
3. Evidence-Hint DPO 的 refusal rate 不显著高于 Answer-DPO。
4. 生成文本没有大量携带训练时的 `Evidence hint:` 格式。
5. Base、Answer-DPO、Evidence-Hint DPO 三组输出差异能在若干 COCO/GQA case study 中被清楚解释。

如果只满足第 1 点但不满足第 2 点，说明提升可能不是来自幻觉减少，需要谨慎写结论。如果第 3 点不满足，则要把收益解释为“更保守”而不是“更 grounded”。

## 4. 可能出现的结果与论文写法

| 结果情况 | 论文结论写法 |
| --- | --- |
| Evidence-Hint DPO 在 COCO/POPE/GQA 上均优于 Answer-DPO，拒答率不升高 | 强结论：轻量 evidence hint 能改善简单视觉幻觉抑制，是一个低成本有效改法 |
| Evidence-Hint DPO 小幅优于 Answer-DPO | 正常结论：在 controlled COCO/GQA 设置下，evidence hint 带来稳定但有限的收益 |
| Evidence-Hint DPO 只在 COCO/POPE 上提升 | 收窄结论：方法主要改善对象存在类幻觉，GQA 属性/关系仍需更强信号 |
| Evidence-Hint DPO 与 Answer-DPO 接近 | 弱结论：模板化 evidence hint 对小规模 DPO 的增益有限，但提供了可复现诊断设置 |
| Evidence-Hint DPO 弱于 Answer-DPO | 负结果结论：evidence hint 可能引入格式漂移或训练难度，需进一步改进 hint 格式 |
| Evidence-Hint DPO 指标提升但拒答率明显升高 | 谨慎结论：收益可能来自保守回答，不能声称模型获得更强视觉 grounding |

当前匹配的结果情况介于“Evidence-Hint DPO 与 Answer-DPO 接近”和“部分指标弱于 Answer-DPO”之间。拒答率没有升高，normal prompt 下也没有 literal `Evidence hint` 格式泄漏；更可能的解释是模板 hint 造成了轻微 yes/no bias shift，降低一部分 false positive，同时提高一部分 false negative。

## 5. 推荐正文表述

如果结果支持预期，可以在摘要和结论中使用保守表述：

> Lightweight evidence hints offer a simple way to inject visual-support cues into preference tuning. In a controlled COCO/GQA setting covering object existence, simple attributes, and left/right spatial relations, Evidence-Hint DPO improves hallucinated visual-claim metrics over answer-only DPO without changing the model architecture or training objective.

中文含义：

> 轻量视觉证据提示提供了一种低成本方式，把视觉支持信号注入偏好优化。在 COCO/GQA 受控设定下，Evidence-Hint DPO 相比普通 Answer-DPO 改善了对象存在、简单属性和左右空间关系中的视觉幻觉指标，同时不需要修改模型结构或训练目标。

如果结果较弱，建议改为：

> Our controlled study shows that template-level evidence hints are not sufficient by themselves to consistently outperform answer-only DPO, suggesting that future lightweight grounding signals may need better hint design or stronger visual alignment.

中文含义：

> 受控实验表明，单纯模板化 evidence hint 未必足以稳定超过普通 Answer-DPO，说明后续轻量 grounding 信号可能需要更好的 hint 设计或更强视觉对齐。

当前 `paper/main.tex` 已采用这一较弱但真实的表述。

## 6. Case Study 预期

理想 case study 应展示以下类型：

1. Base 或 Answer-DPO 对不存在对象回答 yes，Evidence-Hint DPO 正确回答 no。
2. Answer-DPO 生成更流畅但错误的肯定句，Evidence-Hint DPO 更直接地纠正不存在对象。
3. Answer-DPO 答错颜色/材质，Evidence-Hint DPO 纠正为 scene graph 标注属性。
4. Answer-DPO 出现 left/right reversal，Evidence-Hint DPO 回答正确方向。
5. Evidence-Hint DPO 没有输出 evidence hint，只输出简短 answer。
6. 失败案例中，Evidence-Hint DPO 仍被常见共现对象、GQA scene graph 噪声或左右关系歧义误导。

正文不需要展示太多例子，4-6 个清晰样例足够，优先覆盖 3 个 COCO 对象例子和 1-3 个 GQA 属性/关系例子。Case study 的作用是帮助读者理解指标变化，而不是替代主表。

## 7. 风险边界

无论结果如何，论文都不应声称：

- 方法已经解决 VLM hallucination。
- 方法适用于复杂属性、计数、多步关系和开放式描述。
- evidence hint 等价于真实 grounding 或 box-level supervision。
- 单 seed、单 backbone 结果足以证明普遍性。

更稳妥的边界是：本文验证了一个轻量、低成本、可复现的数据格式改动，在对象存在、简单属性和左右空间关系上是否比普通回答级 DPO 更有效。
