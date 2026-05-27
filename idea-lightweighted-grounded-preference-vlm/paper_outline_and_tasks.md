# 论文大纲与后续任务清单

更新日期：2026-05-27

## 0. 当前状态

项目当前定位为一篇小规模 CVPR 示例投稿，目标是在不扩大工程变量的前提下验证一个基础结论：

> 在 VLM 回答级 DPO 中，把偏好回答扩展为带有轻量视觉证据提示的回答，是否能更稳定地降低简单对象幻觉。

当前训练数据已经更新为一个更完整但仍然很小的设定：

- 模型：Qwen2.5-VL-7B-Instruct。
- 数据：5,000 条 mixed preference pairs，其中 3,500 条来自 COCO object existence，1,500 条来自 GQA simple attribute/relation。
- GQA 构成：986 条 color attribute，64 条 material attribute，450 条 left/right spatial relation。
- 三组主实验：Base Instruct、Answer-DPO、Evidence-Hint DPO。
- 训练方式：LoRA DPO，1 epoch，`pref_beta=0.1`，LoRA rank 16。
- 已完成：GQA scene graph 与 2,500 张对应 VG 图像下载，`canonical_gqa_main.jsonl` 已生成 1,500 条。
- 已完成：重新生成 mixed `canonical_pairs_main.jsonl`、Answer-DPO/Evidence-Hint DPO JSONL，并通过 leakage check；`train_eval_image_overlap = 0`。
- 已完成：mixed audit 重新汇总，`data/audit/audit_200_summary.json` 显示 200/200 chosen correctness、200/200 rejected wrongness、200/200 hint correctness，抽样中包含 139 条 COCO 和 61 条 GQA。
- 已完成：GQA simple held-out eval，`data/eval/gqa_simple_heldout.jsonl` 共 1,000 条，color 与 left/right relation 各 500 条，yes/no 各 500 条，训练 GQA image overlap 为 0。
- 训练中：mixed Answer-DPO job 64200 与 mixed Evidence-Hint DPO job 64201 已通过 Slurm 启动，默认输出到 mixed adapter 目录；完成后再记录 mixed train metrics。
- 历史训练：Answer-DPO job 64167 和 Evidence-Hint DPO job 64168 是旧 COCO-only 数据上的训练结果，只作为 preliminary/旧设置记录，不放入 mixed 数据论文主结果。

因此实验规划需要相应调整：主实验仍保持三组不扩张，但两组 DPO 需要在当前 mixed 数据上重新训练。论文结论可以从“只验证 COCO 对象存在幻觉”扩展为“验证对象存在、简单属性和简单左右空间关系上的轻量 evidence hint”，但仍不能声称覆盖复杂推理、计数、多步关系或开放式描述。

## 1. 暂定题目

英文：

**Lightweight Evidence Hints Improve Preference Tuning for Reducing Object Hallucination in Vision-Language Models**

中文工作名：

**轻量视觉证据提示改善 VLM 偏好优化中的对象幻觉抑制**

## 2. 核心贡献

1. 提出一个低成本的偏好数据改写方式：不改模型结构、不训练额外 reward model，只在 DPO 的 chosen/rejected response 中加入模板化 evidence hint。
2. 构造一个 5k mixed preference set，覆盖 COCO 对象存在和 GQA 简单属性/左右空间关系，保证 Answer-DPO 与 Evidence-Hint DPO 使用同一批图像、问题和语义标签，只改变回答格式。
3. 在 Qwen2.5-VL-7B-Instruct 上做三组小规模对比，验证 evidence hint 是否比普通 Answer-DPO 更能抑制对象、属性和简单关系层面的幻觉，并检查是否带来过度拒答。

## 3. 论文结构

### Abstract

一句话动机：VLM 偏好优化常在完整回答层面学习偏好，可能学到回答风格而非视觉依据。

一句话方法：我们把 DPO 样本从纯回答偏好改成带轻量 evidence hint 的回答偏好。

一句话实验：在 5k mixed COCO/GQA preference pairs 和 Qwen2.5-VL-7B 上比较 Base、Answer-DPO、Evidence-Hint DPO。

一句话结论：若结果支持，强调 evidence hint 在不增加模型结构复杂度的情况下改善对象幻觉指标；若结果一般，强调它提供了一个可复现的小型诊断设置。

### 1. Introduction

要讲清楚三个点：

- VLM 幻觉问题中，对象存在、简单属性和空间关系错误是最基础、最可控的一组子问题。
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

写 mixed COCO/GQA 规则：

- 从 COCO train2017 构造对象存在问题：正对象来自标注可见类别，负对象来自该图未标注类别，并过滤容易漏标的小物体类别。
- 从 GQA train scene graphs 构造简单属性和左右空间关系问题：属性只保留 color/material，关系只保留 left/right 这类方向明确的模板。
- 最终保留 5,000 aligned pairs：3,500 COCO object-existence + 1,500 GQA simple attribute/relation。
- 训练图像与 held-out eval image ids 已做泄漏检查，当前 overlap 为 0。
- 人工抽查文件为 `data/audit/audit_200.csv`。

这里要如实说明当前数据只覆盖对象存在、简单属性和简单左右关系，因此实验仍是一个最小可验证设定，不覆盖复杂推理。

### 4. Experiments

#### 4.1 Setup

写清楚：

- Backbone：Qwen2.5-VL-7B-Instruct。
- Fine-tuning：LoRA DPO。
- Train split：5k mixed preference pairs，3,500 COCO + 1,500 GQA。
- Groups：Base Instruct、Answer-DPO、Evidence-Hint DPO。
- Main comparison：所有训练组使用相同图片、问题、chosen/rejected 语义。
- 注意：旧的 64167/64168 adapter 来自 COCO-only 数据；最终主表必须使用 mixed 数据重训后的 adapter。

#### 4.2 Evaluation

优先级从高到低：

1. POPE object hallucination subset。
2. 自建 COCO object-existence held-out eval。
3. GQA simple held-out eval，至少覆盖 color attribute 和 left/right relation 的小子集。
4. AMBER object/attribute subset，如果脚本来得及。
5. Refusal rate，统计回答中 `not sure`、`cannot determine`、`unclear` 等表达。

如果时间紧，主表只放 POPE + 自建 COCO held-out + GQA simple + refusal rate。

#### 4.3 Main Results

主表建议：

| Method | POPE F1 | COCO Held-out Acc | GQA Simple Acc | Yes Bias | Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | TBD | TBD | TBD | TBD | TBD |
| Answer-DPO | TBD | TBD | TBD | TBD | TBD |
| Evidence-Hint DPO | TBD | TBD | TBD | TBD | TBD |

只要 Evidence-Hint DPO 相比 Answer-DPO 在 POPE/COCO 或 GQA simple 上有稳定提升，并且 refusal rate 没有明显升高，就足够支撑这篇示例论文的主结论。若收益只出现在 COCO 而不出现在 GQA，应在正文中把结论收窄为对象存在类幻觉。

#### 4.4 Analysis

正文最多放两项分析：

- 错误类型：false positive object hallucination、attribute mismatch、left/right reversal 是否下降。
- 案例展示：6 个例子，对比 Answer-DPO 与 Evidence-Hint DPO，优先覆盖 3 个 COCO 对象例子和 3 个 GQA 属性/关系例子。

不要新增复杂 ablation，避免超过三组主实验。

### 5. Limitations

必须主动收窄：

- 当前数据只覆盖 COCO 对象存在、GQA 简单属性和左右空间关系，不覆盖计数、多步关系和开放式描述。
- Evidence hint 来自模板，不是人工标注或精确 grounding。
- 没有验证多 backbone、多 seed、大规模数据扩展。
- 结果主要证明这个轻量信号值得进一步研究，而不是完整解决 VLM hallucination。

### 6. Conclusion

结论写成保守版本：

> Lightweight evidence hints provide a simple way to inject visual-support cues into VLM preference tuning. In a controlled COCO/GQA setting covering object existence, simple attributes, and left/right spatial relations, the method tests whether grounding-flavored preference responses can reduce hallucinated visual claims beyond answer-only DPO, without changing the model architecture or training objective.

## 4. 图表计划

正文控制在 6 页内，图表不要超过 3 个。

| 编号 | 类型 | 内容 | 状态 |
| --- | --- | --- | --- |
| Figure 1 | 方法图 | Answer-DPO vs Evidence-Hint DPO 数据格式对比 | 待画 |
| Table 1 | 主结果表 | Base / Answer-DPO / Evidence-Hint DPO | 等评测 |
| Figure 2 | Case study | 4-6 个对象/属性/关系幻觉例子 | 等推理输出 |

可选补充材料：

- 数据构造模板。
- 训练配置。
- 更多 case study。

## 5. 后续任务清单

### A. 训练收尾

- [x] 确认 job 64167 Answer-DPO 正常完成。
- [x] 等待 job 64168 Evidence-Hint DPO 完成：状态 `COMPLETED`，ExitCode `0:0`，2026-05-27 07:17:55 结束。
- [x] 检查 `outputs/llamafactory/qwen25vl7b_evidence_hint_dpo/` 是否生成完整 adapter、trainer state 和 train results：`adapter_config.json`、`adapter_model.safetensors`、`trainer_state.json`、`train_results.json` 均已生成。
- [x] 记录两组训练的 train loss、runtime、steps、samples/sec：见 `experiments/training_summary.md`。Answer-DPO：loss 0.2791，runtime 3449.4s，157 steps，1.450 samples/sec；Evidence-Hint DPO：loss 0.1025，runtime 48163.8s，157 steps，0.104 samples/sec。
- [x] 如果 64168 失败或明显卡住，先查看 `logs/train_evidence_hint_dpo.64168.err`，只修训练/数据格式问题，不扩大实验设定：64168 未失败；日志健康扫描未发现 Traceback、RuntimeError、CUDA OOM、nan 或 inf。
- [x] 基于 2026-05-27 的 mixed COCO+GQA 数据重新跑 Answer-DPO：已重新导出 mixed LLaMA-Factory 数据并启动 Slurm job 64200，状态检查时为 `RUNNING`，输出目录为 `outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/`。
- [x] 基于 2026-05-27 的 mixed COCO+GQA 数据重新跑 Evidence-Hint DPO：已重新导出 mixed LLaMA-Factory 数据并启动 Slurm job 64201，状态检查时为 `RUNNING`，输出目录为 `outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo/`。
- [x] 将 64167/64168 标记为 COCO-only preliminary run，不放入 mixed 数据主表：见 `experiments/training_summary.md`，旧输出目录保留为 preliminary/auxiliary 记录。

### B. 数据质检

- [x] 完成 GQA 官方 scene graph 下载与按需 VG 图片下载：`train_sceneGraphs.json` 可读，2,500/2,500 张 VG 图片成功下载。
- [x] 生成 mixed `canonical_pairs_main.jsonl`：3,500 COCO + 1,500 GQA，共 5,000 条。
- [x] GQA 训练构成已记录：986 color、64 material、450 left/right relation。
- [x] 完成 `data/audit/audit_200.csv` 抽查标注；需要重新人工扫一遍 mixed 版本，重点看 GQA 属性和 relation 噪声。
- [x] 汇总 chosen correctness、rejected wrongness、hint correctness：三项均为 200/200 = 100.0%，见 `data/audit/audit_200_summary.json`。
- [x] 重新汇总 mixed audit 的 chosen correctness、rejected wrongness、hint correctness；阈值仍为 chosen correctness 高于 85%，hint correctness 高于 90%：`data/audit/audit_200_summary.json` 中三项均为 200/200 = 100.0%，抽样来源为 139 COCO + 61 GQA。
- [x] 准备评测 image-id overlap 文件 `data/eval/heldout_object_existence_image_ids.txt`，并重跑 leakage check；当前 train/eval image overlap = 0，eval image-id warning 已解决。

### C. 评测脚本

- [x] 准备 Base Instruct、Answer-DPO、Evidence-Hint DPO 的统一推理入口：`scripts/eval/run_vlm_inference.py` + `experiments/slurm/eval_vlm_object_hallucination.slurm`。
- [x] 确认 LoRA adapter 加载方式，避免评测时只跑到 base 模型：`answer_dpo`/`evidence_hint_dpo` 缺少 `adapter_config.json` 或 `adapter_model.safetensors` 时脚本会直接报错退出；默认 adapter 路径已切到 mixed 输出目录，需在 64200/64201 完成后重跑 dry-run。
- [x] 准备 POPE object hallucination 评测：`scripts/eval/prepare_pope_eval.py` 可将官方 POPE JSON/JSONL/CSV 规范化为统一 eval JSONL，后续复用同一推理与打分脚本。
- [x] 准备一个 COCO held-out object-existence eval JSONL：`data/eval/coco_heldout_object_existence.jsonl`，共 1,000 条，yes/no 各 500 条，见 `data/eval/coco_heldout_object_existence.summary.json`。
- [x] 准备 GQA simple held-out eval JSONL，优先抽 500-1,000 条 color/left-right 样本，并与训练 GQA image ids 去重：`data/eval/gqa_simple_heldout.jsonl` 共 1,000 条，500 color + 500 left/right relation，yes/no 各 500，`train_eval_image_overlap = 0`。
- [x] 实现 refusal rate 统计脚本：`scripts/eval/score_object_eval.py` 输出 Acc、F1、yes bias、refusal rate 和二分类混淆矩阵。
- [x] 保存每组模型的原始生成结果，后续做 case study：统一输出到 `results/eval/generations/<eval_name>/<model_key>.jsonl`，保留 image、question、target、prompt、generation、model key 和 method。

### D. 主结果

- [ ] 跑 Base Instruct 评测。
- [ ] 跑 mixed Answer-DPO 评测。
- [ ] 跑 mixed Evidence-Hint DPO 评测。
- [ ] 填 Table 1：POPE F1、COCO held-out Acc、GQA simple Acc、yes bias、refusal rate。
- [ ] 检查 Evidence-Hint DPO 的收益是否不是由更高拒答率造成。
- [ ] 如果 Evidence-Hint DPO 结果弱于 Answer-DPO，优先分析是否 evidence hint 训练导致推理格式漂移。

### E. Case Study

- [ ] 从三组模型的生成结果中抽取 20 个候选例子。
- [ ] 选择 4-6 个最清晰的例子放正文。
- [ ] 每个例子只展示 image、question、Answer-DPO output、Evidence-Hint DPO output。
- [ ] 至少包含 1-2 个 GQA 属性/关系例子；如果 GQA 例子噪声高，就只放 COCO case 并在 limitation 中说明。
- [ ] 不要堆太多文字解释，让读者能直接看到对象幻觉是否减少。

### F. 写作

- [ ] 新建 CVPR LaTeX 草稿目录。
- [ ] 写 Abstract 和 Introduction 初稿。
- [ ] 写 Method，重点保持“只改数据格式，不改训练目标”。
- [ ] 写 Experiment Setup，明确 mixed COCO+GQA 范围和 GQA simple 限定。
- [ ] 填主结果表和 case study。
- [ ] 写 Limitations，主动承认数据范围小。
- [ ] 全文压到 6 页以内。

### G. 风险与备选方案

- [ ] 若 64168 训练失败：先用 smoke 版 adapter 做端到端评测链路演练，再修 full run。
- [ ] 若 POPE 数据准备耗时：先用自建 held-out object-existence eval 出趋势表。
- [ ] 若 Evidence-Hint DPO 生成时总带 evidence：在评测 prompt 中明确要求 `Answer with a short yes/no sentence only.`，并统计格式违规率。
- [ ] 若 Answer-DPO 与 Evidence-Hint DPO 都退化：检查 DPO 数据中 rejected 是否过于模板化，必要时降低学习率或减少 epoch 后重训。
- [ ] 若主结果没有提升：论文可转为负结果分析，题目改为 evidence hint 对 object DPO 的诊断研究，仍保留可复现实验价值。
