# 论文大纲与后续任务清单

更新日期：2026-05-26

## 0. 当前状态

项目当前定位为一篇小规模 CVPR 示例投稿，目标是在不扩大工程变量的前提下验证一个基础结论：

> 在 VLM 回答级 DPO 中，把偏好回答扩展为带有轻量视觉证据提示的回答，是否能更稳定地降低简单对象幻觉。

当前训练数据已经收敛到一个干净的小设定：

- 模型：Qwen2.5-VL-7B-Instruct。
- 数据：5,000 条 COCO-only object-existence preference pairs。
- 三组主实验：Base Instruct、Answer-DPO、Evidence-Hint DPO。
- 训练方式：LoRA DPO，1 epoch，`pref_beta=0.1`，LoRA rank 16。
- 已完成：Answer-DPO job 64167，正常结束。
- 进行中：Evidence-Hint DPO job 64168。

因为 GQA 数据下载在集群镜像路径下失败，第一版论文不要声称覆盖属性、关系或复杂推理。正文结论应收窄为：轻量 evidence hint 对 COCO 风格对象存在幻觉的影响。

## 1. 暂定题目

英文：

**Lightweight Evidence Hints Improve Preference Tuning for Reducing Object Hallucination in Vision-Language Models**

中文工作名：

**轻量视觉证据提示改善 VLM 偏好优化中的对象幻觉抑制**

## 2. 核心贡献

1. 提出一个低成本的偏好数据改写方式：不改模型结构、不训练额外 reward model，只在 DPO 的 chosen/rejected response 中加入模板化 evidence hint。
2. 构造一个 5k COCO object-existence preference set，保证 Answer-DPO 与 Evidence-Hint DPO 使用同一批图像、问题和语义标签，只改变回答格式。
3. 在 Qwen2.5-VL-7B-Instruct 上做三组小规模对比，验证 evidence hint 是否比普通 Answer-DPO 更能抑制对象幻觉，并检查是否带来过度拒答。

## 3. 论文结构

### Abstract

一句话动机：VLM 偏好优化常在完整回答层面学习偏好，可能学到回答风格而非视觉依据。

一句话方法：我们把 DPO 样本从纯回答偏好改成带轻量 evidence hint 的回答偏好。

一句话实验：在 5k COCO object-existence pairs 和 Qwen2.5-VL-7B 上比较 Base、Answer-DPO、Evidence-Hint DPO。

一句话结论：若结果支持，强调 evidence hint 在不增加模型结构复杂度的情况下改善对象幻觉指标；若结果一般，强调它提供了一个可复现的小型诊断设置。

### 1. Introduction

要讲清楚三个点：

- VLM 幻觉问题中，对象存在类错误是最基础、最可控的子问题。
- 回答级 DPO 能利用偏好信号，但 chosen/rejected 本身不显式说明视觉证据，模型可能只学到语言模板。
- 轻量 evidence hint 是一个工程成本很低的中间方案：比完整 grounding/box supervision 简单，比纯回答偏好更接近视觉依据。

推荐最后用一段列贡献，不超过三条。

### 2. Related Work

控制篇幅，最多半页到三分之二页。

建议分三小段：

- VLM hallucination evaluation：POPE、AMBER、CHAIR 等。
- Preference tuning for VLMs：DPO、hallucination-aware preference tuning、视觉偏好学习。
- Grounding and evidence supervision：强调完整 grounding 成本较高，而本文只使用模板化轻量 evidence hint。

### 3. Method

核心写法要非常简单。

#### 3.1 Answer-Level DPO Baseline

定义标准样本：

```text
x = (image, question)
y+ = correct answer
y- = hallucinated answer
```

训练目标使用标准 DPO，不改损失。

#### 3.2 Evidence-Hint DPO

把回答改写为：

```text
y+ = correct answer + evidence hint for visible object
y- = hallucinated answer + evidence hint for unsupported object
```

示例：

```text
Question: Is there a dog in the image?
Chosen: Yes, there is a dog in the image.
Evidence hint: annotated visible object: dog.
Rejected: Yes, there is a cat in the image.
Evidence hint: unsupported object: cat is not annotated as visible.
```

强调三点：

- 不使用 box/mask。
- 不修改 DPO loss。
- 推理评测时仍只问普通问题，不要求输出 evidence。

#### 3.3 Data Construction

写 COCO-only 规则：

- 从 COCO train2017 构造对象存在问题。
- 正对象来自标注可见类别。
- 负对象来自该图未标注类别，并过滤容易漏标的小物体类别。
- 最终保留 5,000 aligned pairs。
- 人工抽查文件为 `data/audit/audit_200.csv`。

这里要如实说明当前数据只覆盖 object existence，因此实验是一个最小可验证设定。

### 4. Experiments

#### 4.1 Setup

写清楚：

- Backbone：Qwen2.5-VL-7B-Instruct。
- Fine-tuning：LoRA DPO。
- Train split：5k COCO object-existence preference pairs。
- Groups：Base Instruct、Answer-DPO、Evidence-Hint DPO。
- Main comparison：所有训练组使用相同图片、问题、chosen/rejected 语义。

#### 4.2 Evaluation

优先级从高到低：

1. POPE object hallucination subset。
2. 自建 COCO object-existence held-out eval。
3. AMBER object existence subset，如果脚本来得及。
4. Refusal rate，统计回答中 `not sure`、`cannot determine`、`unclear` 等表达。

如果时间紧，主表只放 POPE + 自建 held-out + refusal rate。

#### 4.3 Main Results

主表建议：

| Method | POPE Acc | POPE F1 | Held-out Acc | Yes Bias | Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | TBD | TBD | TBD | TBD | TBD |
| Answer-DPO | TBD | TBD | TBD | TBD | TBD |
| Evidence-Hint DPO | TBD | TBD | TBD | TBD | TBD |

只要 Evidence-Hint DPO 相比 Answer-DPO 在 F1/Acc 有稳定提升，并且 refusal rate 没有明显升高，就足够支撑这篇示例论文的主结论。

#### 4.4 Analysis

正文最多放两项分析：

- 错误类型：false positive object hallucination 是否下降。
- 案例展示：6 个例子，对比 Answer-DPO 与 Evidence-Hint DPO。

不要新增复杂 ablation，避免超过三组主实验。

### 5. Limitations

必须主动收窄：

- 当前数据是 COCO-only object existence，不覆盖属性、关系、计数和开放式描述。
- Evidence hint 来自模板，不是人工标注或精确 grounding。
- 没有验证多 backbone、多 seed、大规模数据扩展。
- 结果主要证明这个轻量信号值得进一步研究，而不是完整解决 VLM hallucination。

### 6. Conclusion

结论写成保守版本：

> Lightweight evidence hints provide a simple way to inject visual-support cues into VLM preference tuning. In a controlled COCO object-existence setting, the method tests whether grounding-flavored preference responses can reduce hallucinated object mentions beyond answer-only DPO, without changing the model architecture or training objective.

## 4. 图表计划

正文控制在 6 页内，图表不要超过 3 个。

| 编号 | 类型 | 内容 | 状态 |
| --- | --- | --- | --- |
| Figure 1 | 方法图 | Answer-DPO vs Evidence-Hint DPO 数据格式对比 | 待画 |
| Table 1 | 主结果表 | Base / Answer-DPO / Evidence-Hint DPO | 等评测 |
| Figure 2 | Case study | 4-6 个对象幻觉例子 | 等推理输出 |

可选补充材料：

- 数据构造模板。
- 训练配置。
- 更多 case study。

## 5. 后续任务清单

### A. 训练收尾

- [x] 确认 job 64167 Answer-DPO 正常完成。
- [ ] 等待 job 64168 Evidence-Hint DPO 完成。
- [ ] 检查 `outputs/llamafactory/qwen25vl7b_evidence_hint_dpo/` 是否生成完整 adapter、trainer state 和 train results。
- [ ] 记录两组训练的 train loss、runtime、steps、samples/sec。
- [ ] 如果 64168 失败或明显卡住，先查看 `logs/train_evidence_hint_dpo.64168.err`，只修训练/数据格式问题，不扩大实验设定。

### B. 数据质检

- [x] 完成 `data/audit/audit_200.csv` 抽查标注；当前为基于 COCO canonical label 的 annotation-grounded consistency audit。
- [x] 汇总 chosen correctness、rejected wrongness、hint correctness：三项均为 200/200 = 100.0%，见 `data/audit/audit_200_summary.json`。
- [x] 阈值检查通过：chosen correctness 高于 85%，hint correctness 高于 90%，无需先修数据过滤规则或重训。
- [x] 准备评测 image-id overlap 文件 `data/eval/heldout_object_existence_image_ids.txt`，并重跑 leakage check；当前 train/eval image overlap = 0，eval image-id warning 已解决。

### C. 评测脚本

- [ ] 准备 Base Instruct、Answer-DPO、Evidence-Hint DPO 的统一推理入口。
- [ ] 确认 LoRA adapter 加载方式，避免评测时只跑到 base 模型。
- [ ] 准备 POPE object hallucination 评测。
- [ ] 准备一个 COCO held-out object-existence eval JSONL，用于快速复核趋势。
- [ ] 实现 refusal rate 统计脚本。
- [ ] 保存每组模型的原始生成结果，后续做 case study。

### D. 主结果

- [ ] 跑 Base Instruct 评测。
- [ ] 跑 Answer-DPO 评测。
- [ ] 跑 Evidence-Hint DPO 评测。
- [ ] 填 Table 1：POPE Acc/F1、held-out Acc、yes bias、refusal rate。
- [ ] 检查 Evidence-Hint DPO 的收益是否不是由更高拒答率造成。
- [ ] 如果 Evidence-Hint DPO 结果弱于 Answer-DPO，优先分析是否 evidence hint 训练导致推理格式漂移。

### E. Case Study

- [ ] 从三组模型的生成结果中抽取 20 个候选例子。
- [ ] 选择 4-6 个最清晰的例子放正文。
- [ ] 每个例子只展示 image、question、Answer-DPO output、Evidence-Hint DPO output。
- [ ] 不要堆太多文字解释，让读者能直接看到对象幻觉是否减少。

### F. 写作

- [ ] 新建 CVPR LaTeX 草稿目录。
- [ ] 写 Abstract 和 Introduction 初稿。
- [ ] 写 Method，重点保持“只改数据格式，不改训练目标”。
- [ ] 写 Experiment Setup，明确 COCO-only 限定。
- [ ] 填主结果表和 case study。
- [ ] 写 Limitations，主动承认数据范围小。
- [ ] 全文压到 6 页以内。

### G. 风险与备选方案

- [ ] 若 64168 训练失败：先用 smoke 版 adapter 做端到端评测链路演练，再修 full run。
- [ ] 若 POPE 数据准备耗时：先用自建 held-out object-existence eval 出趋势表。
- [ ] 若 Evidence-Hint DPO 生成时总带 evidence：在评测 prompt 中明确要求 `Answer with a short yes/no sentence only.`，并统计格式违规率。
- [ ] 若 Answer-DPO 与 Evidence-Hint DPO 都退化：检查 DPO 数据中 rejected 是否过于模板化，必要时降低学习率或减少 epoch 后重训。
- [ ] 若主结果没有提升：论文可转为负结果分析，题目改为 evidence hint 对 object DPO 的诊断研究，仍保留可复现实验价值。
