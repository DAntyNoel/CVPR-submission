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
- GQA simple held-out：`data/eval/gqa_simple_heldout.jsonl`，1,000 条，500 color + 500 left/right relation，yes/no 各 500 条
- POPE object hallucination：作为外部对象幻觉补充评测
- 图片重叠：train/eval image overlap = 0

如果 POPE 准备成本过高，第一版主表至少保留 COCO held-out + GQA simple，并把 POPE 写入补充或 limitation。

## 4. 训练设置

模型和训练方式保持一致：

- Backbone：Qwen2.5-VL-7B-Instruct
- Fine-tuning：LoRA DPO
- Epoch：1
- DPO beta：0.1
- LoRA rank：16
- 推理时不要求输出 evidence hint，只回答普通短答案

mixed 主训练记录：

| 方法 | Job ID | 状态 | Train loss | Runtime |
| --- | ---: | --- | ---: | --- |
| Answer-DPO | 64200 | RUNNING | TBD | TBD |
| Evidence-Hint DPO | 64201 | RUNNING | TBD | TBD |

COCO-only preliminary 训练记录：

| 方法 | Job ID | 状态 | Train loss | Runtime |
| --- | ---: | --- | ---: | --- |
| Answer-DPO | 64167 | COMPLETED | 0.2791 | 00:57:29 |
| Evidence-Hint DPO | 64168 | COMPLETED | 0.1025 | 13:22:44 |

64167/64168 基于旧 5,000 条 COCO-only 数据，不进入 mixed 数据主结果表，但可以作为 COCO-only auxiliary/preliminary result 写入论文额外结果。它们适合在等待 mixed 数据重训时先跑 COCO held-out、POPE、refusal rate 和格式违规检查，用来展示纯对象存在子设定下的趋势。mixed job 64200/64201 已使用 2026-05-27 mixed COCO+GQA 数据启动；Evidence-Hint DPO 更慢仍是预期现象，主要来自 response 变长带来的 DPO 计算成本增加。

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

2026-05-27 已使用当前完成的 COCO-only 5k 训练结果启动 held-out COCO
object-existence 验证：

| Method | Eval Job ID | Adapter |
| --- | ---: | --- |
| Base Instruct | 64205 | none |
| Answer-DPO | 64206 | `outputs/llamafactory/qwen25vl7b_answer_dpo` |
| Evidence-Hint DPO | 64207 | `outputs/llamafactory/qwen25vl7b_evidence_hint_dpo` |

三个 job 均使用 `data/eval/coco_heldout_object_existence.jsonl`。输出路径为
`results/eval/generations/coco_heldout_object_existence/<model_key>.jsonl`，
并在推理结束后自动生成对应 `.metrics.json`。

2026-05-27 验证结果：

| Method | Acc | F1 | False Positive Rate | Yes Bias | Refusal Rate | Confusion |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Base Instruct | 0.959 | 0.958 | 0.018 | 0.477 | 0.000 | TP 468 / FP 9 / TN 491 / FN 32 |
| Answer-DPO 64167 | 0.961 | 0.960 | 0.018 | 0.479 | 0.000 | TP 470 / FP 9 / TN 491 / FN 30 |
| Evidence-Hint DPO 64168 | 0.960 | 0.959 | 0.016 | 0.476 | 0.000 | TP 468 / FP 8 / TN 492 / FN 32 |

Answer-DPO 与 Evidence-Hint DPO 的逐样本预测有 997/1000 条相同。Evidence-Hint
DPO 比 Answer-DPO 少 1 个 false positive，但多 2 个 false negative，因此
COCO-only held-out 结果只能支持“false positive 略低”，不能单独支持整体 Acc/F1
优于 Answer-DPO 的强结论。

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

1. 等 mixed Answer-DPO 64200 与 mixed Evidence-Hint DPO 64201 完成，并记录 train metrics。
2. 完成 mixed adapter dry-run，确认默认 `answer_dpo`/`evidence_hint_dpo` 指向 mixed 输出目录。
3. 跑 Base Instruct、mixed Answer-DPO、mixed Evidence-Hint DPO 的正式推理。
4. 生成 POPE、COCO held-out、GQA simple、refusal rate 主表指标。
5. 对比错误类型，重点看 false positive object hallucination、attribute mismatch 和 left/right reversal。
6. 从三组输出中抽取 4-6 个清晰 case study，尽量覆盖 COCO 与 GQA。

## 9. 不做的内容

为了保持项目小而有效，主实验阶段暂不加入：

- 多 backbone 对比
- SFT 或 RLAIF 新基线
- 多种 DPO 变体
- box/mask grounding supervision
- 超过三组的主实验表

这些内容可以放进 future work 或 limitation，避免正文目标发散。
