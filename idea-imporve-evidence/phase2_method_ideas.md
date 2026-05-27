# Phase 2 Method Ideas: Improving Evidence Use in VLM Preference Tuning

更新日期：2026-05-27

## 1. 背景与动机

一期实验验证了一个很轻量的方案：在 DPO 的 chosen/rejected response 后追加模板化
`Evidence hint:`。真实结果显示，这种做法只带来很小的 false-positive 下降，并没有在
COCO、GQA、Hard COCO 或 Base-error-mined diagnostic 上稳定超过 Answer-DPO。

因此二期不优先扩大 benchmark 或直接堆数据，而是先改进 evidence 信号进入偏好学习的方式。核心问题从：

> evidence hint 是否有用？

改为：

> 什么样的 evidence 表达形式，能让 DPO 更明确地学习“答案必须被视觉证据支持”，而不是只学习回答风格或 yes/no bias？

二期仍建议保持主干约束：

- 不新增复杂模型结构。
- 不训练额外 reward model。
- 不引入 box/mask grounding supervision。
- 优先复用现有 5k mixed COCO/GQA 数据构造与评测链路。
- 主评测仍使用 COCO held-out、Hard COCO、GQA simple 和 Base-error-mined diagnostic。

## 2. 方案 A：Input-Side Evidence Hint

### 核心想法

把 evidence hint 从 response 侧移到输入 prompt/context 侧，让 chosen/rejected response 仍然保持普通答案格式。

当前一期格式：

```text
Question: Is there a dog in the image?
Chosen: Yes, there is a dog in the image. Evidence hint: annotated visible object: dog.
Rejected: Yes, there is a cat in the image. Evidence hint: unsupported object: cat is not annotated as visible.
```

二期输入侧 evidence 格式：

```text
Image + Visual cue: annotated visible object: dog.
Question: Is there a dog in the image?
Chosen: Yes, there is a dog in the image.
Rejected: No, there is no dog in the image.
```

### 预期优势

- 减少训练/推理 response 格式 mismatch。
- 避免模型把 `Evidence hint:` 当作一种生成风格学习。
- evidence 更像条件上下文，答案仍保持短 yes/no。

### 风险

- 如果推理时不提供 evidence context，训练/推理输入仍然存在 mismatch。
- 模型可能依赖输入侧 cue，而不是图像本身。

### 推荐实验定位

作为二期最优先方法之一。可以设计两种推理模式：

- normal inference：不提供 evidence cue，测试是否内化。
- evidence-conditioned inference：提供同格式 cue，测试上限。

## 3. 方案 B：Evidence-Only Preference Pair

### 核心想法

保持答案本身一致，只让 evidence 是否正确成为 chosen/rejected 的区别。这样 DPO 的区分信号不能来自答案正确性，只能来自 evidence consistency。

示例：

```text
Question: Is there a dog in the image?
Chosen: Yes, there is a dog in the image. Evidence: annotated visible object: dog.
Rejected: Yes, there is a dog in the image. Evidence: unsupported object: cat.
```

属性示例：

```text
Question: Is the bus yellow?
Chosen: Yes, the bus is yellow. Evidence: annotated color of bus: yellow.
Rejected: Yes, the bus is yellow. Evidence: annotated color of bus: red.
```

### 预期优势

- 直接测试模型是否偏好“证据一致性”。
- 避免答案正确性掩盖 evidence 信号。
- 可作为机制诊断：如果这个方案仍无效，说明模板 evidence 很可能没有被 DPO 有效利用。

### 风险

- 推理时如果不要求生成 evidence，训练信号可能难以迁移到短答案判断。
- rejected answer 表面上仍然正确，可能使 DPO 学习目标更难。

### 推荐实验定位

作为机制诊断实验，优先小规模跑通。它不一定直接作为最终主方法，但能回答一期失败的关键原因：模型到底有没有学 evidence consistency。

## 4. 方案 C：Chosen-Only Evidence

### 核心想法

只给 chosen response 添加 supported evidence，不再给 rejected response 添加 unsupported evidence。

一期格式：

```text
Chosen: Yes, there is a dog. Evidence hint: annotated visible object: dog.
Rejected: Yes, there is a cat. Evidence hint: unsupported object: cat is not annotated as visible.
```

二期 chosen-only 格式：

```text
Chosen: Yes, there is a dog. Evidence: annotated visible object: dog.
Rejected: Yes, there is a cat.
```

### 预期优势

- 把 evidence 变成正向支撑信号，而不是同时训练“unsupported/no”的强模板。
- 可能减少一期观察到的轻微 yes-rate 下降和 FPR/FNR trade-off。
- 改动最小，容易直接复用现有导出脚本。

### 风险

- chosen/rejected 长度差异更大，DPO 可能偏好更长文本或更完整格式。
- 如果推理时不输出 evidence，收益仍可能有限。

### 推荐实验定位

作为低成本改进 baseline。建议与一期 Evidence-Hint DPO 做直接对比，检查是否缓解 false negative 增加。

## 5. 方案 D：Counterfactual Object Pairs

### 核心想法

减少语言差异，让每个 preference pair 更像最小视觉对比。正负样本尽量只改变目标 object / attribute / relation，而不改变其他回答风格。

对象存在示例：

```text
Question: Is there a motorcycle in the image?
Chosen: No, there is no motorcycle in the image.
Rejected: Yes, there is a motorcycle in the image.
Evidence cue: queried object = motorcycle; annotation support = absent.
```

同图像可配套另一个正对象：

```text
Question: Is there a bicycle in the image?
Chosen: Yes, there is a bicycle in the image.
Rejected: No, there is no bicycle in the image.
Evidence cue: queried object = bicycle; annotation support = present.
```

### 构造规则

- 负对象优先来自同粗类、强共现或易混淆类别。
- 同一图像中尽量构造 present/absent 成对问题。
- chosen/rejected 尽量只差 yes/no 和目标 claim，减少措辞差异。
- 对 GQA relation，优先使用 left/right 互为 counterfactual。

### 预期优势

- 降低语言模板捷径。
- 增强模型对“同一图像、相近对象、不同视觉事实”的敏感度。
- 可直接针对一期 Hard COCO 和 Base-error-mined 中暴露出的 false positive / false negative trade-off。

### 风险

- COCO 未标注对象可能导致 absent label 噪声。
- 更难的 counterfactual pair 可能降低整体训练稳定性。

### 推荐实验定位

作为二期数据构造的核心增强，但不以扩大数据量为目标。可以先在原 5k 规模内替换一部分普通 COCO pair。

## 6. 方案 E：Evidence as Check Step

### 核心想法

把 evidence hint 从“解释句”改成“检查步骤”，显式表达从证据到答案的映射。

示例：

```text
Check: queried object = motorcycle.
Check: annotation support = absent.
Answer: No, there is no motorcycle in the image.
```

属性示例：

```text
Check: queried attribute = bus color.
Check: annotation value = yellow.
Answer: Yes, the bus is yellow.
```

关系示例：

```text
Check: queried relation = refrigerator left of sweater.
Check: annotation support = present.
Answer: Yes, the refrigerator is to the left of the sweater.
```

### 预期优势

- 比一句 `Evidence hint:` 更明确地教模型 evidence-to-answer 映射。
- 更容易定位失败原因：模型是没利用 evidence，还是利用了但映射错了。
- 可与 input-side evidence 或 chosen-only evidence 组合。

### 风险

- 输出格式更长，训练/推理 mismatch 可能更明显。
- 如果推理仍只要求 yes/no，check step 信号未必会被激活。

### 推荐实验定位

适合作为结构化 hint 格式 ablation。建议先在小规模 smoke 上比较：

- plain evidence hint
- check-step evidence
- check-step + short final answer

## 7. 二期推荐优先级

建议不要一次性全跑。优先做 2-3 个最能回答问题的变体：

| 优先级 | 方案 | 目的 | 训练成本 |
| ---: | --- | --- | --- |
| 1 | Evidence-Only Preference Pair | 验证模型是否真的学习 evidence consistency | 低 |
| 2 | Input-Side Evidence Hint | 降低 response-format mismatch | 低 |
| 3 | Chosen-Only Evidence | 检查 unsupported hint 是否导致过度保守 | 低 |
| 4 | Counterfactual Object Pairs | 提高视觉对比难度，减少语言捷径 | 中 |
| 5 | Evidence as Check Step | 改进 hint 表达结构 | 低 |

推荐第一轮二期实验：

1. 保持 backbone、DPO 设置、5k 总规模不变。
2. 只新增 2-3 个方法变体，不新增 benchmark。
3. 优先比较 Answer-DPO、一期 Evidence-Hint DPO、Evidence-Only、Input-Side Evidence、Chosen-Only Evidence。
4. 使用已有 COCO held-out、Hard COCO、GQA simple、Base-error-mined diagnostic 评测。
5. 重点观察 FPR/FNR trade-off、yes bias、literal evidence leakage、evidence-style prompt delta。

## 8. 二期论文叙事方向

如果二期某个方案稳定优于 Answer-DPO，可以把论文从一期的 negative/diagnostic result 推进为：

> Template evidence hints are not automatically useful, but their placement and contrast structure matter. Evidence supervision becomes more effective when the preference pair isolates evidence consistency or reduces response-format mismatch.

如果二期仍无提升，则结论也有价值：

> Lightweight textual evidence alone may be too weak for small-scale VLM DPO unless paired with stronger grounding supervision, better negative verification, or inference-time evidence conditioning.

