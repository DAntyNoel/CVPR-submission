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
- 已完成：mixed Answer-DPO job 64200，输出目录为 `outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/`，train loss 0.3722，runtime 3417.2s。
- 训练中：mixed Evidence-Hint DPO job 64201，默认输出到 `outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo/`；完成后再记录 train metrics 并启动 mixed 主评测。
- 历史训练：Answer-DPO job 64167 和 Evidence-Hint DPO job 64168 是旧 COCO-only 数据上的训练结果，只作为 preliminary/旧设置记录，不放入 mixed 数据论文主结果。
- 已完成 COCO-only auxiliary eval：Base Acc 0.959、Answer-DPO Acc 0.961、Evidence-Hint DPO Acc 0.960；Evidence-Hint DPO false positive rate 从 0.018 降到 0.016，但整体 Acc/F1 未超过 Answer-DPO。
- 已完成：mixed Answer-DPO 在 COCO held-out 和 GQA simple 上的 adapter dry-run，确认默认 registry 指向 mixed adapter 且不会误跑 base。
- 已完成：等待 64201 时先跑的 Base GQA 与 mixed Answer-DPO COCO/GQA 评测 jobs 64213-64215；Base GQA Acc 0.764，mixed Answer-DPO COCO Acc 0.961，mixed Answer-DPO GQA Acc 0.768。
- 已完成：Base/Answer-DPO 的 evidence-style prompt 评测 jobs 64216-64219；Base COCO Acc 0.955，Base GQA Acc 0.768，Answer-DPO COCO Acc 0.956，Answer-DPO GQA Acc 0.766，拒答率均为 0。
- 已完成：新建 `paper/` CVPR LaTeX 草稿目录，写入 Abstract、Introduction、Related Work、Method、Experiment Setup、Limitations 与结果占位。
- 新决策：在不增加方法组的前提下，允许新增少量更大实验来丰富论文。优先级为 Hard COCO Eval、Evidence-Style Prompt Eval 补全、POPE/AMBER 小子集、10k mixed scale-up。所有新增实验仍围绕 Base / Answer-DPO / Evidence-Hint DPO 三组，不加入 SFT、critic、多 backbone 或 3D。

因此实验规划需要相应调整：主实验仍保持三组不扩张，但两组 DPO 需要在当前 mixed 数据上重新训练。论文结论可以从“只验证 COCO 对象存在幻觉”扩展为“验证对象存在、简单属性和简单左右空间关系上的轻量 evidence hint”，但仍不能声称覆盖复杂推理、计数、多步关系或开放式描述。
后续写作采用两手准备：若 mixed/Hard COCO/POPE/GQA 结果支持，则写成轻量 evidence hint 的正向小结论；若收益仍很小，则收窄为一个 controlled diagnostic study，重点解释 ceiling effect、评测难度、evidence-style prompting 和数据规模趋势对结论的影响。

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

格式与页数约束：

- 使用 CVPR 2026 LaTeX 格式，当前草稿已切到官方 `cvpr.sty` review mode。
- 正文按 6/7/8 页弹性控制：优先 6 页，7 页可接受，8 页为硬上限。
- 参考文献加可选附录部分不超过 10 页；附录非必须，除非需要补数据模板、训练配置或更多 case study。

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

1. 自建 COCO object-existence held-out eval 与 GQA simple held-out eval，保证主链路完整。
2. Hard COCO Eval：从 COCO pool 构造常共现、易混淆的 absent-object negative，专门测试 false positive object hallucination。
3. Evidence-Style Prompt Eval：normal yes/no prompt vs `Answer yes or no, then briefly mention the visual evidence.`，检查训练期 evidence hint 是否需要在推理格式中被激活。
4. POPE object hallucination subset，作为外部 benchmark 门面。
5. AMBER object/attribute subset，如果脚本和数据准备来得及。
6. Refusal rate，统计回答中 `not sure`、`cannot determine`、`unclear` 等表达。

如果时间紧，主表至少放 COCO held-out + GQA simple + Hard COCO + refusal rate；POPE/AMBER 放入外部评测表或 supplement。

#### 4.2.1 少量大实验但不新增方法组

允许增加以下实验来让论文更饱满，但它们不改变主方法集合：

| 优先级 | 实验 | 目的 | 训练成本 |
| ---: | --- | --- | --- |
| 1 | Hard COCO Eval | 打破普通 COCO held-out 的 ceiling effect，观察 absent-object false positive | 无新训练 |
| 2 | Evidence-Style Prompt Eval | 对应 latent vs explicit evidence 的简化分析 | 无新训练 |
| 3 | POPE / AMBER 小子集 | 增加外部 hallucination benchmark 可信度 | 无新训练 |
| 4 | 10k Mixed Scale-Up | 检查 evidence hint 的数据规模趋势 | 重训 Answer-DPO 与 Evidence-Hint DPO |

10k scale-up 只在前 3 项仍不足以支撑论文时启动。Base 不变，主比较仍是 Answer-DPO vs Evidence-Hint DPO。

#### 4.3 Main Results

主表建议：

| Method | COCO Held-out Acc | Hard COCO FPR | GQA Simple Acc | Yes Bias | Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | TBD | TBD | TBD | TBD | TBD |
| Answer-DPO | TBD | TBD | TBD | TBD | TBD |
| Evidence-Hint DPO | TBD | TBD | TBD | TBD | TBD |

只要 Evidence-Hint DPO 相比 Answer-DPO 在 POPE/COCO 或 GQA simple 上有稳定提升，并且 refusal rate 没有明显升高，就足够支撑这篇示例论文的主结论。若收益只出现在 COCO 而不出现在 GQA，应在正文中把结论收窄为对象存在类幻觉。

两条结果解释路线：

- Plan A：Evidence-Hint DPO 在 mixed 主评测中优于 Answer-DPO，尤其是 false positive、attribute mismatch 或 left/right reversal 下降，同时 refusal rate 不升高。论文主结论写成“轻量 evidence hint 能在受控视觉声明任务中带来小而稳定的 hallucination reduction”。
- Plan B：Evidence-Hint DPO 与 Answer-DPO 差异仍然很小，或只降低 false positive 但不提升 Acc/F1。论文改写为诊断型结果：当前 easy COCO held-out 存在 ceiling effect，yes/no-only 推理未充分激活 evidence hint；保留 COCO-only 结果作为 sanity check，并把 Hard COCO Eval、evidence-style prompt 和 10k scale-up 作为下一步核心。

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

正文控制在 6 页内，正文优先放 3 个高价值图表；Hard/外部评测、prompt-mode 和 scale-up 如果放不下，移到 appendix 或 supplementary。

| 编号 | 类型 | 内容 | 状态 |
| --- | --- | --- | --- |
| Figure 1 | 方法图 | Answer-DPO vs Evidence-Hint DPO 数据格式对比 | LaTeX 初稿已放入 `paper/main.tex` |
| Table 1 | 主结果表 | Base / Answer-DPO / Evidence-Hint DPO | 等评测 |
| Table 2 | Hard / external eval | Hard COCO，POPE/AMBER 小子集视数据可用性加入 | 待构造/准备 |
| Table 3 | Prompt-mode analysis | normal prompt vs evidence-style prompt | Base/Answer-DPO 已完成，Evidence-Hint 待 64201 |
| Table 4 | Scale-up trend | 5k vs 10k mixed Answer-DPO/Evidence-Hint DPO | 条件触发 |
| Appendix Table | COCO-only auxiliary | 旧 5k COCO-only adapter 的 sanity check | 已有结果，视篇幅放正文或补充 |
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
- [x] 基于 2026-05-27 的 mixed COCO+GQA 数据重新跑 Answer-DPO：Slurm job 64200 已完成，ExitCode `0:0`，输出目录为 `outputs/llamafactory/qwen25vl7b_mixed_answer_dpo/`，train loss 0.3722，runtime 3417.2s。
- [x] 基于 2026-05-27 的 mixed COCO+GQA 数据重新跑 Evidence-Hint DPO：已重新导出 mixed LLaMA-Factory 数据并启动 Slurm job 64201，状态检查时为 `RUNNING`，输出目录为 `outputs/llamafactory/qwen25vl7b_mixed_evidence_hint_dpo/`。
- [x] 将 64167/64168 标记为 COCO-only preliminary run，不放入 mixed 数据主表：见 `experiments/training_summary.md`，旧输出目录保留为 preliminary/auxiliary 记录。
- [ ] 等 mixed Evidence-Hint DPO job 64201 完成后，记录 train loss、runtime、adapter 完整性和日志健康状态。
- [ ] 条件触发 10k scale-up：如果 Hard COCO / evidence-style / POPE 后主结论仍不够稳，重新导出 10k mixed 数据，并只重训 10k Answer-DPO 与 10k Evidence-Hint DPO；Base 不变，不新增方法组。

### B. 数据质检

- [x] 完成 GQA 官方 scene graph 下载与按需 VG 图片下载：`train_sceneGraphs.json` 可读，2,500/2,500 张 VG 图片成功下载。
- [x] 生成 mixed `canonical_pairs_main.jsonl`：3,500 COCO + 1,500 GQA，共 5,000 条。
- [x] GQA 训练构成已记录：986 color、64 material、450 left/right relation。
- [x] 完成 `data/audit/audit_200.csv` 抽查标注；需要重新人工扫一遍 mixed 版本，重点看 GQA 属性和 relation 噪声。
- [x] 汇总 chosen correctness、rejected wrongness、hint correctness：三项均为 200/200 = 100.0%，见 `data/audit/audit_200_summary.json`。
- [x] 重新汇总 mixed audit 的 chosen correctness、rejected wrongness、hint correctness；阈值仍为 chosen correctness 高于 85%，hint correctness 高于 90%：`data/audit/audit_200_summary.json` 中三项均为 200/200 = 100.0%，抽样来源为 139 COCO + 61 GQA。
- [x] 准备评测 image-id overlap 文件 `data/eval/heldout_object_existence_image_ids.txt`，并重跑 leakage check；当前 train/eval image overlap = 0，eval image-id warning 已解决。
- [ ] 构造 Hard COCO Eval：从 unused/held-out COCO pool 选常共现或同粗类易混淆的 absent-object negative，保留 yes/no 平衡、image overlap=0，并输出 summary。
- [ ] 条件触发 expanded 10k 数据：生成 `canonical_pairs_expanded.jsonl` 或等价 10k mixed canonical 文件，并重新导出 10k Answer-DPO/Evidence-Hint DPO 格式。

### C. 评测脚本

- [x] 准备 Base Instruct、Answer-DPO、Evidence-Hint DPO 的统一推理入口：`scripts/eval/run_vlm_inference.py` + `experiments/slurm/eval_vlm_object_hallucination.slurm`。
- [x] 确认 LoRA adapter 加载方式，避免评测时只跑到 base 模型：`answer_dpo`/`evidence_hint_dpo` 缺少 `adapter_config.json` 或 `adapter_model.safetensors` 时脚本会直接报错退出；默认 adapter 路径已切到 mixed 输出目录，需在 64200/64201 完成后重跑 dry-run。
- [x] 支持评测输出变体和 evidence-style prompt：Slurm 脚本新增 `OUTPUT_VARIANT` 和 `INSTRUCTION_SUFFIX`，避免 mixed 主结果、COCO-only auxiliary 和 evidence-style prompt 互相覆盖。
- [x] 准备 POPE object hallucination 评测：`scripts/eval/prepare_pope_eval.py` 可将官方 POPE JSON/JSONL/CSV 规范化为统一 eval JSONL，后续复用同一推理与打分脚本。
- [x] 准备一个 COCO held-out object-existence eval JSONL：`data/eval/coco_heldout_object_existence.jsonl`，共 1,000 条，yes/no 各 500 条，见 `data/eval/coco_heldout_object_existence.summary.json`。
- [ ] 新增 Hard COCO eval 准备脚本或参数模式，输出 `data/eval/coco_hard_object_existence.jsonl`，避免覆盖普通 COCO held-out。
- [x] 准备 GQA simple held-out eval JSONL，优先抽 500-1,000 条 color/left-right 样本，并与训练 GQA image ids 去重：`data/eval/gqa_simple_heldout.jsonl` 共 1,000 条，500 color + 500 left/right relation，yes/no 各 500，`train_eval_image_overlap = 0`。
- [x] 实现 refusal rate 统计脚本：`scripts/eval/score_object_eval.py` 输出 Acc、F1、yes bias、refusal rate 和二分类混淆矩阵。
- [x] 保存每组模型的原始生成结果，后续做 case study：统一输出到 `results/eval/generations/<eval_name>/<model_key>.jsonl`，保留 image、question、target、prompt、generation、model key 和 method。
- [ ] 准备 POPE 官方数据与所需图片；如果官方数据下载阻塞，则明确把 POPE 放入 supplement/future work，不阻塞 Hard COCO。
- [ ] 评估 AMBER object/attribute subset 的本地准备成本，只在能快速接入统一 yes/no scorer 时加入。

### D. 主结果

- [x] 跑 COCO-only auxiliary Base / Answer-DPO / Evidence-Hint DPO 评测：jobs 64205/64206/64207 均已完成，三组各 1,000 条输出。
- [x] 汇总 COCO-only auxiliary 表：Base Acc 0.959、Answer-DPO Acc 0.961、Evidence-Hint DPO Acc 0.960；Evidence-Hint DPO false positive rate 0.016，低于 Answer-DPO 的 0.018。
- [x] 对 mixed Answer-DPO 做 COCO held-out 与 GQA simple dry-run，确认 adapter registry 和路径正确：输出变体为 `mixed`。
- [ ] 等 mixed Evidence-Hint DPO 64201 完成后，对 mixed Evidence-Hint DPO 做 dry-run，确认 adapter registry 和路径正确。
- [x] 跑 mixed Base Instruct 评测，至少覆盖 COCO held-out 与 GQA simple：COCO held-out 复用已完成 Base 输出，Acc 0.959；GQA simple job 64213 已完成，Acc 0.764。
- [x] 跑 mixed Answer-DPO 评测，至少覆盖 COCO held-out 与 GQA simple：jobs 64214/64215 已完成，COCO Acc 0.961，GQA Acc 0.768。
- [ ] 跑 mixed Evidence-Hint DPO 评测，至少覆盖 COCO held-out 与 GQA simple。
- [x] 检查 POPE 官方数据本地可用性：当前仓库未发现官方 POPE 标注或 COCO val2014 图像；本轮先把 POPE 放入 supplement/future work，除非后续单独准备官方数据。
- [ ] 额外补一组 evidence-style prompt eval：提示模型回答 yes/no 后简短说明视觉证据，再复用 yes/no parser，检查 Evidence-Hint DPO 的训练信号是否需要在推理格式中被激活；Base/Answer-DPO jobs 64216-64219 已完成，Base COCO Acc 0.955，Base GQA Acc 0.768，Answer-DPO COCO Acc 0.956，Answer-DPO GQA Acc 0.766，Evidence-Hint DPO 等 64201 完成后再补。
- [ ] 跑 Hard COCO 三组评测：Base、mixed Answer-DPO、mixed Evidence-Hint DPO，重点记录 false positive rate 和逐样本差异。
- [ ] 如果 POPE 数据准备完成，跑 POPE 三组评测；AMBER object/attribute subset 作为次优先。
- [ ] 条件触发 10k scale-up 评测：10k Answer-DPO 与 10k Evidence-Hint DPO 至少跑 COCO held-out、Hard COCO、GQA simple 和 evidence-style prompt。
- [ ] 填 Table 1：COCO held-out Acc、Hard COCO FPR、GQA simple Acc、yes bias、refusal rate。
- [ ] 填 Table 2：Hard COCO 与 POPE/AMBER 外部结果，POPE/AMBER 若不可用则如实说明。
- [ ] 填 Table 3：normal prompt vs evidence-style prompt。
- [ ] 填 Table 4 或 appendix：5k vs 10k scale-up trend，只有条件触发后才写入正文。
- [ ] 检查 Evidence-Hint DPO 的收益是否不是由更高拒答率造成。
- [ ] 如果 Evidence-Hint DPO 结果弱于 Answer-DPO，优先分析是否 evidence hint 训练导致推理格式漂移。
- [ ] 如果 mixed 结果仍与 Answer-DPO 接近，优先解释 ordinary COCO ceiling effect，并用 Hard COCO、evidence-style prompt 与 scale-up trend 做补充判断。

### E. Case Study

- [ ] 从三组模型的生成结果中抽取 20 个候选例子。
- [ ] 选择 4-6 个最清晰的例子放正文。
- [ ] 每个例子只展示 image、question、Answer-DPO output、Evidence-Hint DPO output。
- [ ] 至少包含 1-2 个 GQA 属性/关系例子；如果 GQA 例子噪声高，就只放 COCO case 并在 limitation 中说明。
- [ ] 不要堆太多文字解释，让读者能直接看到对象幻觉是否减少。

### F. 写作

- [x] 新建 CVPR LaTeX 草稿目录：`paper/`。
- [x] 切换到 CVPR 2026 官方格式：`paper/main.tex` 使用 `\usepackage[review]{cvpr}`，并加入 `cvpr.sty` 与 `ieeenat_fullname.bst`。
- [x] 写 Abstract 和 Introduction 初稿：见 `paper/main.tex`，保留 Plan A/Plan B 结果占位。
- [x] 写 Method，重点保持“只改数据格式，不改训练目标”：见 `paper/main.tex`。
- [x] 写 Experiment Setup，明确 mixed COCO+GQA 范围和 GQA simple 限定：见 `paper/main.tex`。
- [ ] 填主结果表和 case study。
- [x] 写 Limitations，主动承认数据范围小：见 `paper/main.tex`。
- [ ] 全文按 6/7/8 页控制：优先 6 页，7 页可接受，8 页为正文硬上限；参考文献加可选附录不超过 10 页。当前环境缺少 `latexmk`/`pdflatex`/`tectonic`，待 LaTeX 工具可用后编译确认页数。

### G. 风险与备选方案

- [x] Plan A 写作路线：若 Evidence-Hint DPO 在 mixed COCO/GQA 或 POPE 上稳定优于 Answer-DPO，主文强调“小而有效”的 hallucination reduction，并把 COCO-only auxiliary 作为先行 sanity check。
- [x] Plan B 写作路线：若 mixed 结果仍然差异很小，主文收窄为 controlled diagnostic study，明确说明 Base/Answer-DPO 已接近 ceiling、yes/no-only 推理弱化了 evidence hint 信号，并把 Hard COCO Eval、evidence-style prompt 与 10k scale-up 作为后续验证。
- [ ] Plan B 实验补强：保留三组主实验不变，只增加评测视角，不新增训练组；evidence-style prompt 入口已完成并提交 Base/Answer-DPO，hard COCO eval 与 paired bootstrap/McNemar 仍待主结果后决定。
- [ ] 少量大实验优先级：Hard COCO Eval > Evidence-Style Prompt Eval 补全 > POPE/AMBER 小子集 > 10k mixed scale-up。除 10k scale-up 外都不需要新训练。
- [ ] 若 64201 训练失败：先用已完成的 COCO-only adapter 和 mixed Answer-DPO 结果完成评测链路，修复 mixed Evidence-Hint DPO 训练后再补主表。
- [ ] 若 POPE 数据准备耗时：先用自建 held-out object-existence eval 出趋势表。
- [ ] 若 Evidence-Hint DPO 生成时总带 evidence：在评测 prompt 中明确要求 `Answer with a short yes/no sentence only.`，并统计格式违规率。
- [ ] 若 Answer-DPO 与 Evidence-Hint DPO 都退化：检查 DPO 数据中 rejected 是否过于模板化，必要时降低学习率或减少 epoch 后重训。
- [ ] 若主结果没有提升：题目可改为 `A Controlled Diagnostic Study of Lightweight Evidence Hints for VLM Preference Tuning`，保留可复现实验价值，避免强行声称提升。
