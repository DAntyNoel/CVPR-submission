# 轻量证据提示的 VLM 偏好优化实验大纲

更新日期：2026-05-26

## 0. 目标定位

目标是做一个小而有效的改进，能在 15 天项目周期内、用中等算力和少量数据得到基础结论：

> 在 VLM 偏好优化中，给 chosen answer 加入轻量视觉证据提示，例如对象名、区域短语或候选框描述，可以比普通回答级 DPO 更稳定地减少简单对象/属性幻觉。

本文不追求大规模数据集、不训练复杂 critic、不做 3D 扩展、不做完整 evidence schema。核心改进点控制在一个很小的层面：

**把偏好样本从“答案 A 优于答案 B”改成“有简短视觉证据支撑的答案 A 优于无证据或错误证据的答案 B”。**

## 1. 拟定标题

**Lightweight Evidence Hints Improve Preference Tuning for Reducing VLM Hallucination**

中文可写作：

**轻量视觉证据提示改善 VLM 偏好优化中的幻觉抑制**

## 2. 核心改进点

标准 DPO 样本：

```text
Image + Question
Chosen: The man is holding a tennis racket.
Rejected: The man is holding a baseball bat.
```

简化版方法只在 chosen/rejected 中加入一段非常短的 evidence hint：

```text
Chosen: The man is holding a tennis racket.
Evidence hint: visible object near the man's hand: tennis racket.

Rejected: The man is holding a baseball bat.
Evidence hint: unsupported object: baseball bat is not visible.
```

训练时仍然使用普通 DPO，不改模型结构，不引入额外 reward model。唯一变化是偏好回答里带有轻量证据提示。推理时默认不要求模型输出 evidence，只输出普通答案。

这个设计的优点：

- 实现成本低，只需要改数据格式。
- 训练代码可以复用现成 DPO pipeline。
- 数据构造不需要精细 box/mask，也不需要人工大规模标注。
- 结论简单：轻量 evidence hint 是否能让 DPO 少学语言偏好，多学视觉依据。

## 3. 研究问题

只回答三个问题：

1. 普通 DPO 是否能在小数据下减少简单 object hallucination？
2. 加入 evidence hint 后，是否比普通 DPO 更好？
3. evidence hint 是否会让模型变得过度保守，导致回答变短或频繁说“不确定”？

## 4. 数据构造

### 4.1 数据规模

总规模控制在 **5k-10k preference pairs**。如果脚本适配不顺利，可以先用 2k 做 smoke test；但在 4xA100 或 8x4090 的算力下，推荐默认跑 5k，时间允许再扩到 10k。

推荐配置：

| 数据 | 数量 | 用途 |
| --- | ---: | --- |
| POPE/COCO 风格对象存在问题 | 3k-5k | 主要测试 object hallucination |
| GQA 简单属性/关系问题 | 2k-5k | 测试 color、count、left/right 等简单错误 |
| 人工抽查小样本 | 100-200 | 检查数据质量和 case study |

### 4.2 低成本构造方式

不做复杂 evidence 标注，只使用已有标注或规则模板：

- 对象存在：来自 COCO object labels。
- 属性/关系：来自 GQA scene graph 的简单字段。
- 负样本：把正确对象替换为同类高频对象，例如 dog/cat、cup/bottle、bus/truck。
- evidence hint：直接用模板生成，不需要 box。

模板示例：

```text
Question: Is there a dog in the image?
Chosen: Yes, there is a dog in the image.
Evidence hint: annotated visible object: dog.
Rejected: Yes, there is a cat in the image.
Evidence hint: unsupported object: cat is not annotated as visible.
```

属性模板：

```text
Question: What color is the bus?
Chosen: The bus is yellow.
Evidence hint: annotated attribute of bus: yellow.
Rejected: The bus is red.
Evidence hint: mismatched attribute: red.
```

### 4.3 数据质量要求

只设最低限度门槛：

- 抽查 100 条，chosen 正确率不低于 85%。
- rejected 必须有明显错误，不追求细粒度困难负例。
- 如果 GQA 属性噪声较大，优先保留对象存在类问题。

### 4.4 数据处理执行计划

详细数据范式、JSONL schema、COCO/GQA 构造规则、质检标准和 15 天执行排期见 [`data_processing_plan.md`](./data_processing_plan.md)。主实验只需要产出两份训练文件：

```text
data/processed/answer_dpo_train.jsonl
data/processed/evidence_hint_dpo_train.jsonl
```

两份文件必须来自同一个 `canonical_pairs.jsonl`，保证 Answer-DPO 和 Evidence-Hint DPO 只差 evidence hint 格式，不引入额外数据差异。

## 5. 方法

### 5.1 模型

建议只选一个主模型，避免主实验膨胀：

- **Qwen2.5-VL-7B-Instruct**：优先推荐。你有 4xA100 或 8x4090，7B LoRA/QLoRA 完全可承受，比 3B 更适合作为模拟投稿的主结果。

如果训练脚本对 7B 适配不顺，备用模型为：

- **Qwen2.5-VL-3B-Instruct**：快速 debug 和 smoke test。
- **LLaVA-1.5-7B** 或 **LLaVA-OneVision 小模型**：仅在已有现成 pipeline 时使用。

为了控制工作量，不做多 backbone 对比。3B 只用于调通流程，不进入主表。

### 5.2 训练设置

- 训练方式：LoRA / QLoRA。
- 训练目标：标准 DPO。
- 训练轮数：1 epoch 起步，最多 2 epoch。
- 数据量：默认 5k，时间允许跑 10k；2k 只作为 smoke test。
- 推理格式：只输出答案，不输出 evidence hint。

### 5.3 三组主实验

主实验严格控制为三组：

| 组别 | 方法 | 说明 |
| --- | --- | --- |
| A | Base Instruct | 原始模型，不训练 |
| B | Answer-DPO | 普通 chosen/rejected 回答级 DPO |
| C | Evidence-Hint DPO | chosen/rejected 中加入轻量 evidence hint 的 DPO |

不加入 SFT、不加入 critic、不加入 3D、不加入多种 DPO 变体。这样主表非常清楚。

### 5.4 少量大实验扩展原则

如果资源充足但希望保持论文主线清楚，优先增加“评测视角”和“数据规模”，不要增加第四个方法组。推荐扩展仍围绕三组主实验：

1. **Hard COCO Eval**：从现有 COCO annotation/held-out pool 构造更难的 absent-object negative，优先选择常共现、易混淆但未标注为可见的同粗类类别，用来缓解普通 COCO held-out 接近 ceiling 的问题；当前已生成 1,000 条 yes/no balanced Hard COCO eval，Base Acc 0.944，mixed Answer-DPO Acc 0.950，mixed Evidence-Hint DPO ZeRO-2 Acc 0.946。
2. **Evidence-Style Prompt Eval**：评测时要求模型回答 yes/no 后简短说明视觉证据，比较 normal prompt 与 evidence-style prompt。它对应 future work 中 explicit/latent evidence 的简化版，不需要新训练。
3. **POPE/AMBER 小子集**：尽量补一个外部 hallucination benchmark。POPE 优先级高于 AMBER；AMBER object/attribute subset 只在数据准备顺利时加入。
4. **10k Mixed Scale-Up**：只扩大数据，不增加方法组。Base 不变，重训 10k Answer-DPO 与 10k Evidence-Hint DPO，用于观察 evidence hint 是否随数据规模更稳定。

这四项的优先级高于多 backbone、多 seed、SFT baseline 或 critic rerank。论文可以把它们组织成“更难评测、外部评测、推理格式分析、数据规模趋势”四个角度。

## 6. 评测

评测也保持小而明确。资源充足时，优先把评测做厚，而不是扩展方法组。

### 6.1 主指标

| 指标 | 数据 | 目的 |
| --- | --- | --- |
| POPE accuracy/F1 | POPE subset | 测对象幻觉 |
| AMBER object/attribute subset | AMBER 小子集 | 测对象和属性幻觉 |
| GQA simple subset accuracy | 自选 500-1k 条 | 测简单视觉问答 |
| Hard COCO accuracy/F1/FPR/FNR | 常共现难负例 | 测更强对象幻觉压力与可见对象召回 |
| Balanced accuracy / FPR / FNR | 所有 yes/no eval | 区分整体正确率、幻觉率和漏检率 |
| Other/invalid rate + response length | 所有 yes/no eval | 检查格式漂移和冗长回答 |

### 6.2 辅助分析

正文主分析优先保留两项：

- **Refusal rate**：统计 “I cannot determine / not sure / unclear” 等回答比例。
- **Case study**：展示 6-8 个例子，比较普通 DPO 与 Evidence-Hint DPO。

如果版面允许，再补充：

- **Prompt-mode analysis**：normal yes/no prompt vs evidence-style prompt，检查训练期 evidence hint 是否需要在推理格式中被显式激活。
- **Data-scale trend**：5k vs 10k mixed DPO，检查提升是否随数据量更稳定。

### 6.3 预期结果

预期不追求大幅提升：

- Evidence-Hint DPO 相比 Answer-DPO，在 POPE F1 上提升 **1-3 points**。
- 在 AMBER object/attribute 子集上提升 **2-5 points**。
- GQA simple subset 不下降，或下降不超过 **1 point**。
- Refusal rate 不明显升高，说明收益不是来自“更保守”。

只要能得到这个级别的结果，就足够支撑模拟投稿中的基础结论。

## 7. 算力与训练时间

### 7.1 推荐配置

| 资源 | 估计 |
| --- | --- |
| GPU | 4x A100 40/80GB，或 8x RTX 4090 |
| 主模型 | Qwen2.5-VL-7B-Instruct |
| 训练数据 | 5k-10k preference pairs |
| 训练方式 | A100 用 LoRA/bf16；4090 优先 QLoRA/4-bit |
| LoRA rank | 16 或 32 |
| 训练时长 | 1-3 小时 / 组 |
| 总训练时间 | 4-9 小时 |
| 全部评测 | 4-10 小时 |

15 天项目中，真实耗时主要不在训练，而在数据清洗、脚本适配和结果整理。额外算力建议用于：

- 跑 7B 主模型，而不是只跑 3B。
- 完整跑 COCO/GQA/Hard COCO/evidence-style prompt，而不是只抽极小子集。
- 争取补 POPE，AMBER object/attribute subset 作为次优先。
- 如果前述评测仍不足以支撑结论，再启动 10k mixed Answer-DPO 与 Evidence-Hint DPO 重训。
- 快速重跑失败配置，减少等待时间。

### 7.2 保守时间表

| 时间 | 任务 |
| --- | --- |
| Day 1-2 | 整理数据模板，生成 5k preference pairs |
| Day 3 | 人工抽查 100 条，修正模板 |
| Day 4-5 | 跑 Base、Answer-DPO、Evidence-Hint DPO |
| Day 6-7 | 跑 COCO/GQA/Hard COCO/evidence-style prompt 评测 |
| Day 8 | 补 POPE，AMBER 视数据准备情况加入 |
| Day 9 | 若主结论仍弱，启动 10k mixed Answer-DPO/Evidence-Hint DPO |
| Day 10 | 做 case study、refusal rate 和 prompt-mode analysis |
| Day 11-12 | 写正文、表格、图 |
| Day 13 | 整理 related work 和 limitation |
| Day 14 | internal review |
| Day 15 | 定稿 |

### 7.3 两种算力配置的使用建议

| 配置 | 建议用法 |
| --- | --- |
| 4x A100 | 首选。直接跑 Qwen2.5-VL-7B LoRA/bf16；三组实验可以顺序跑，必要时给 Answer-DPO 和 Evidence-Hint DPO 各补一个 seed。 |
| 8x RTX 4090 | 优先 QLoRA/4-bit，注意显存碎片和多卡通信稳定性；适合并行跑评测、数据生成和不同 seed。 |

不建议因为算力更充足就增加第四组主实验。更好的用法是提高主模型可靠性、补 seed、补完整评测。

## 8. 正文结构，6 页以内

建议正文控制在 **5-6 页**，附录可选。

### Page 1: Introduction

- VLM 幻觉仍然常见。
- DPO 可以缓解，但回答级偏好可能仍偏文本风格。
- 本文提出一个轻量改动：在 DPO 样本中加入 evidence hint。
- 贡献写三点即可：
  - 一个低成本 evidence-hint preference construction。
  - 三组实验验证它优于普通 Answer-DPO。
  - 简单分析说明收益不是来自过度拒答。

### Page 2: Related Work + Method

Related work 只写三类：

- VLM hallucination：POPE、AMBER、HallusionBench 等。
- VLM preference optimization：DPO、HA-DPO、OPA-DPO、TPO。
- Visual grounding / evidence：GQA、Visual Genome、RefCOCO。

Method 写清楚模板构造和训练格式即可，不引入复杂公式。DPO 公式可简单引用，不做理论推导。

### Page 3: Dataset Construction

- 数据来源：COCO/POPE style object labels + GQA simple subset。
- chosen/rejected 构造规则。
- evidence hint 模板。
- 人工抽查质量。

### Page 4: Experiments

主表只放三组：

| Method | POPE F1 | AMBER Obj | AMBER Attr | GQA Simple | Refusal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | - | - | - | - | - |
| Answer-DPO | - | - | - | - | - |
| Evidence-Hint DPO | - | - | - | - | - |

### Page 5: Analysis

- 6-8 个 qualitative examples。
- 对比 Answer-DPO 为什么仍会错：常见对象替换、属性猜测。
- Evidence-Hint DPO 改善哪些问题。
- 失败案例：小物体、遮挡、属性标注噪声。

### Page 6: Conclusion + Limitations

结论要克制：

- 轻量 evidence hint 是一种低成本改进。
- 在小规模模拟投稿设置下，它能带来基础幻觉缓解。
- 但还不是完整 grounding 方法，不能证明模型真正学会像素级证据。

Limitations：

- 数据规模小。
- evidence hint 是模板级，不是 box/mask 级。
- 只验证对象/属性简单幻觉。
- 没有多 backbone、大规模人评和 3D 实验。

## 9. Related Work 精简清单

必须引用：

- [Direct Preference Optimization](https://papers.neurips.cc/paper_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7-Abstract-Conference.html)
- [POPE: Evaluating Object Hallucination in Large Vision-Language Models](https://arxiv.org/abs/2305.10355)
- [AMBER: An LLM-free Multi-dimensional Benchmark for MLLMs Hallucination Evaluation](https://arxiv.org/abs/2311.07397)
- [HA-DPO](https://arxiv.org/abs/2311.16839)
- [Mitigating Hallucinations in Large Vision-Language Models via DPO: On-Policy Data Hold the Key](https://openaccess.thecvf.com/content/CVPR2025/html/Yang_Mitigating_Hallucinations_in_Large_Vision-Language_Models_via_DPO_On-Policy_Data_CVPR_2025_paper.html)
- [Task Preference Optimization](https://openaccess.thecvf.com/content/CVPR2025/html/Yan_Task_Preference_Optimization_Improving_Multimodal_Large_Language_Models_with_Vision_CVPR_2025_paper.html)

可选引用：

- [VL-RewardBench](https://openaccess.thecvf.com/content/CVPR2025/html/Li_VL-RewardBench_A_Challenging_Benchmark_for_Vision-Language_Generative_Reward_Models_CVPR_2025_paper.html)
- [Critic-V](https://openaccess.thecvf.com/content/CVPR2025/html/Zhang_Critic-V_VLM_Critics_Help_Catch_VLM_Errors_in_Multimodal_Reasoning_CVPR_2025_paper.html)
- [Qwen2.5-VL](https://arxiv.org/abs/2502.13923)

## 10. 最终预期结论

本文预期只给出一个基础结论：

> 在小数据、中等算力的 15 天项目设置下，将轻量视觉证据提示加入 VLM 偏好样本，可以比普通回答级 DPO 更有效地降低简单对象/属性幻觉，同时不会明显增加拒答率。
