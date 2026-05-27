# 主实验大纲

更新日期：2026-05-27

## 1. 实验目标

主实验只验证一个核心问题：

> 在相同 VLM、相同训练图片、相同问题和相同 chosen/rejected 语义下，把普通回答级 DPO 改成带轻量 evidence hint 的 DPO，是否能更稳定地减少对象存在、简单属性和左右空间关系中的视觉幻觉？

更新后的主实验范围从 COCO-only 扩展为 mixed COCO/GQA：覆盖 COCO 对象存在、GQA 简单颜色/材质属性和 GQA 左右空间关系。本实验仍不追求大规模 benchmark 覆盖，也不扩展到计数、多步关系或开放式描述。当前论文第一版应定位为一个 controlled visual-claim study。

## 2. 实验组设置

主实验严格保留三组，不再增加第四组：

| 组别 | 方法 | 训练 | 用途 |
| --- | --- | --- | --- |
| A | Base Instruct | 不训练 | 原始模型基线 |
| B | Answer-DPO | 普通 chosen/rejected answer DPO | 回答级偏好优化基线 |
| C | Evidence-Hint DPO | chosen/rejected answer 后加入模板化 evidence hint | 本文方法 |

Answer-DPO 和 Evidence-Hint DPO 使用同一份 mixed `canonical_pairs_main.jsonl` 导出，保证两组只差 response 格式，不引入数据来源差异。

## 3. 数据设定

训练数据：

- 文件：`data/processed/canonical_pairs_main.jsonl`
- 规模：5,000 条 preference pairs
- 来源：COCO train2017 + GQA train scene graph/VG images
- 构成：3,500 COCO object existence + 1,500 GQA simple attribute/relation
- GQA 细分：986 color attribute，64 material attribute，450 left/right spatial relation
- 质检：`data/audit/audit_200.csv`

评测数据：

- COCO held-out：`data/eval/coco_heldout_object_existence.jsonl`，1,000 条，yes/no 各 500 条
- GQA simple held-out：待准备，优先 500-1,000 条 color/left-right 样本
- POPE object hallucination：作为外部对象幻觉补充评测
- 图片重叠：train/eval image overlap = 0

如果 POPE 或 GQA simple 准备成本过高，第一版主表至少保留 COCO held-out，并把未完成部分写入 limitation；但优先级上 GQA simple 应尽量补齐，因为当前训练数据已经包含 GQA。

## 4. 训练设置

模型和训练方式保持一致：

- Backbone：Qwen2.5-VL-7B-Instruct
- Fine-tuning：LoRA DPO
- Epoch：1
- DPO beta：0.1
- LoRA rank：16
- 推理时不要求输出 evidence hint，只回答普通短答案

历史训练记录：

| 方法 | Job ID | 状态 | Train loss | Runtime |
| --- | ---: | --- | ---: | --- |
| Answer-DPO | 64167 | COMPLETED | 0.2791 | 00:57:29 |
| Evidence-Hint DPO | 64168 | COMPLETED | 0.1025 | 13:22:44 |

这两个 job 基于旧 5,000 条 COCO-only 数据，不进入 mixed 数据主结果表，但可以作为 COCO-only auxiliary/preliminary result 写入论文额外结果。它们适合在等待 mixed 数据重训时先跑 COCO held-out、POPE、refusal rate 和格式违规检查，用来展示纯对象存在子设定下的趋势。主实验仍需要基于 2026-05-27 mixed COCO+GQA 数据重新训练 Answer-DPO 与 Evidence-Hint DPO。Evidence-Hint DPO 更慢仍是预期现象，主要来自 response 变长带来的 DPO 计算成本增加。

## 5. COCO-only 额外结果

旧 5k COCO-only 训练可以作为额外结果，但需要单独成表，避免和 mixed 主结果混写。推荐定位：

- 正文空间允许时：放在 main results 后的 short auxiliary result。
- 正文空间紧张时：放入 appendix 或 supplementary。
- 作用：证明 evidence hint 在纯 object existence 设置下是否已有趋势，并为 mixed 主实验提供先行证据。
- 限制：不能用于声称方法改善 GQA 属性/关系，也不能替代 mixed COCO+GQA 主表。

辅助表模板：

| Setting | Method | COCO Held-out Acc | COCO Held-out F1 | POPE F1 | Refusal Rate |
| --- | --- | ---: | ---: | ---: | ---: |
| COCO-only training | Base Instruct | TBD | TBD | TBD | TBD |
| COCO-only training | Answer-DPO 64167 | TBD | TBD | TBD | TBD |
| COCO-only training | Evidence-Hint DPO 64168 | TBD | TBD | TBD | TBD |

## 6. 评测指标

主表建议包含以下指标：

| 指标 | 含义 | 关注点 |
| --- | --- | --- |
| Accuracy | yes/no 判断正确率 | 总体对象存在判断能力 |
| F1 | 二分类 F1 | 类别平衡下的稳健性 |
| False Positive Rate | 对不存在对象回答 yes 的比例 | 对象幻觉是否下降 |
| GQA Simple Accuracy | 属性/左右关系回答正确率 | 简单属性和关系是否改善 |
| Attribute Mismatch | 属性答错比例 | 颜色/材质幻觉是否下降 |
| Left/Right Reversal | 左右关系答反比例 | 简单空间关系是否改善 |
| Yes Bias | 回答 yes 的倾向 | 是否只是更爱回答 yes/no |
| Refusal Rate | 不确定、无法判断等拒答比例 | 是否靠保守拒答获得收益 |

最重要的比较是 Evidence-Hint DPO vs Answer-DPO，而不是只看 Evidence-Hint DPO 是否超过 Base。

## 7. 主结果表模板

| Method | POPE F1 | COCO Held-out Acc | GQA Simple Acc | Yes Bias | Refusal Rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | TBD | TBD | TBD | TBD | TBD |
| Answer-DPO | TBD | TBD | TBD | TBD | TBD |
| Evidence-Hint DPO | TBD | TBD | TBD | TBD | TBD |

填表后优先检查三件事：

1. Evidence-Hint DPO 的 POPE/COCO/GQA 指标是否高于 Answer-DPO。
2. Evidence-Hint DPO 的 false positive、attribute mismatch 或 left/right reversal 是否下降。
3. Evidence-Hint DPO 的 refusal rate 是否没有明显升高。

## 8. 执行顺序

1. 先跑旧 COCO-only Answer-DPO/Evidence-Hint DPO 的 COCO held-out、POPE 和 refusal/format 检查，形成 auxiliary result。
2. 基于 mixed `answer_dpo_train.jsonl` 重训 Answer-DPO。
3. 基于 mixed `evidence_hint_dpo_train.jsonl` 重训 Evidence-Hint DPO。
4. 准备 GQA simple held-out eval，并与训练 GQA image ids 去重。
5. 跑 Base Instruct、mixed Answer-DPO、mixed Evidence-Hint DPO 的正式推理。
6. 生成 POPE、COCO held-out、GQA simple、refusal rate 主表指标。
7. 对比错误类型，重点看 false positive object hallucination、attribute mismatch 和 left/right reversal。
8. 从三组输出中抽取 4-6 个清晰 case study，尽量覆盖 COCO 与 GQA。

## 9. 不做的内容

为了保持项目小而有效，主实验阶段暂不加入：

- 多 backbone 对比
- SFT 或 RLAIF 新基线
- 多种 DPO 变体
- box/mask grounding supervision
- 超过三组的主实验表

这些内容可以放进 future work 或 limitation，避免正文目标发散。
