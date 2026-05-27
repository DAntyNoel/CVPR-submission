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
- Hard COCO held-out：`data/eval/coco_hard_object_existence.jsonl`，1,000 条，yes/no 各 500 条，500 张 held-out 图像；负例为同粗类但未标注可见的 absent object，重点测试 false positive object hallucination
- GQA simple held-out：`data/eval/gqa_simple_heldout.jsonl`，1,000 条，500 color + 500 left/right relation，yes/no 各 500 条
- POPE object hallucination：作为外部对象幻觉补充评测
- AMBER object/attribute subset：数据准备顺利时加入，作为外部多维 hallucination 补充
- 图片重叠：train/eval image overlap = 0

如果 POPE/AMBER 准备成本过高，第一版主表至少保留 COCO held-out + Hard COCO + GQA simple，并把 POPE/AMBER 写入补充或 limitation。

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
| Answer-DPO | 64200 | COMPLETED | 0.3722 | 00:56:57 |
| Evidence-Hint DPO | 64252 | COMPLETED | 0.1347 | 00:15:51 |

COCO-only preliminary 训练记录：

| 方法 | Job ID | 状态 | Train loss | Runtime |
| --- | ---: | --- | ---: | --- |
| Answer-DPO | 64167 | COMPLETED | 0.2791 | 00:57:29 |
| Evidence-Hint DPO | 64168 | COMPLETED | 0.1025 | 13:22:44 |

64167/64168 基于旧 5,000 条 COCO-only 数据，不进入 mixed 数据主结果表，但可以作为 COCO-only auxiliary/preliminary result 写入论文额外结果。它们适合在等待 mixed 数据重训时先跑 COCO held-out、POPE、refusal rate 和格式违规检查，用来展示纯对象存在子设定下的趋势。mixed job 64200 已使用 2026-05-27 mixed COCO+GQA 数据完成 Answer-DPO 训练；Evidence-Hint DPO 改用已完成的 ZeRO-2 job 64252 作为默认主结果，原 ZeRO-3 job 64201 已取消。

若 5k mixed 主结果和新增评测仍不足以支撑清晰结论，可启动 10k mixed scale-up。该扩展只扩大训练数据，不增加方法组：Base Instruct 不变，只重训 10k Answer-DPO 与 10k Evidence-Hint DPO，并在 COCO held-out、Hard COCO、GQA simple、evidence-style prompt 上复评。

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
| Balanced Accuracy | yes/no 两类召回的平均 | 类别平衡外也可比较 |
| F1 | 二分类 F1 | 类别平衡下的稳健性 |
| False Positive Rate | 对不存在对象回答 yes 的比例 | 对象幻觉是否下降 |
| False Negative Rate | 对存在对象回答 no/other/refusal 的比例 | 是否牺牲可见对象召回 |
| Hard COCO FPR | 难负例中对不存在对象回答 yes 的比例 | ceiling effect 下的对象幻觉压力测试 |
| GQA Simple Accuracy | 属性/左右关系回答正确率 | 简单属性和关系是否改善 |
| Attribute Mismatch | 属性答错比例 | 颜色/材质幻觉是否下降 |
| Left/Right Reversal | 左右关系答反比例 | 简单空间关系是否改善 |
| Yes Bias | 回答 yes 的倾向 | 是否只是更爱回答 yes/no |
| Refusal Rate | 不确定、无法判断等拒答比例 | 是否靠保守拒答获得收益 |
| Other/Invalid Rate | 无法解析为 yes/no 的比例 | 是否出现格式漂移 |
| Evidence Cue / Length | evidence 词汇率与回答长度 | evidence-style prompt 和格式漂移分析 |
| Evidence-Style Delta | evidence-style prompt 相对 normal prompt 的变化 | 训练期 evidence hint 是否需要推理期显式触发 |

最重要的比较是 Evidence-Hint DPO vs Answer-DPO，而不是只看 Evidence-Hint DPO 是否超过 Base。

## 7. 主结果表模板

| Method | COCO Acc/BAcc | COCO FPR/FNR | Hard COCO FPR/FNR | GQA Acc/BAcc | Yes/Ref/Other |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base Instruct | TBD | TBD | TBD | TBD | TBD |
| Answer-DPO | TBD | TBD | TBD | TBD | TBD |
| Evidence-Hint DPO | TBD | TBD | TBD | TBD | TBD |

填表后优先检查三件事：

1. Evidence-Hint DPO 的 COCO/Hard COCO/GQA 指标是否高于 Answer-DPO。
2. Evidence-Hint DPO 的 false positive、attribute mismatch 或 left/right reversal 是否下降。
3. Evidence-Hint DPO 的 refusal rate 是否没有明显升高。

外部评测表可单独记录 POPE F1、AMBER object/attribute 指标。Prompt-mode analysis 表单独比较 normal prompt 与 evidence-style prompt。10k scale-up 若启动，放正文短表或 appendix trend table。

## 8. 执行顺序

1. 记录 mixed Evidence-Hint DPO ZeRO-2 job 64252 train metrics；mixed Answer-DPO 64200 已完成。
2. 完成 mixed adapter dry-run，确认默认 `answer_dpo`/`evidence_hint_dpo` 指向 mixed 输出目录。
3. 跑 Base Instruct、mixed Answer-DPO、mixed Evidence-Hint DPO 的正式推理。
4. 补齐 evidence-style prompt 评测，优先补 Evidence-Hint DPO 的 COCO/GQA。
5. 构造 Hard COCO Eval，并跑三组正式推理。
6. 如果 POPE/AMBER 数据快速可用，跑三组外部评测；否则不阻塞主线。
7. 生成 COCO held-out、Hard COCO、GQA simple、refusal rate 主表指标。
8. 对比错误类型，重点看 false positive object hallucination、attribute mismatch 和 left/right reversal。
9. 若主结论仍弱，启动 10k mixed scale-up，只重训 Answer-DPO 与 Evidence-Hint DPO。
10. 从三组输出中抽取 4-6 个清晰 case study，尽量覆盖 COCO 与 GQA。

当前执行进展：

- mixed Answer-DPO 64200 已完成，adapter 完整性和 COCO/GQA dry-run 已通过。
- mixed Evidence-Hint DPO ZeRO-2 job 64252 已完成，adapter、train metrics 和 dry-run 已检查。
- Base GQA 与 mixed Answer-DPO COCO/GQA 评测 jobs 64213-64215 已完成：Base GQA Acc 0.764，mixed Answer-DPO COCO Acc 0.961，mixed Answer-DPO GQA Acc 0.768。
- Base/Answer-DPO evidence-style prompt jobs 64216-64219 已完成：Base COCO Acc 0.955，Base GQA Acc 0.768，Answer-DPO COCO Acc 0.956，Answer-DPO GQA Acc 0.766，拒答率均为 0。
- Hard COCO held-out 已构造完成：`data/eval/coco_hard_object_existence.jsonl`，1,000 条、yes/no 各 500、train/eval image overlap = 0；Base 和 mixed Answer-DPO jobs 64233/64234 已完成，Base Acc 0.944，mixed Answer-DPO Acc 0.950。
- mixed Evidence-Hint DPO 的 old afterok:64201 依赖队列已取消；ZeRO-2 normal-prompt 评测 64255/64256/64257 已完成，evidence-style 64258/64259 也已完成。
- 官方 POPE 数据与 COCO val2014 图像当前不在仓库本地，POPE 暂放入 supplement/future work。
- 新增少量大实验优先级已确定：Hard COCO Eval > Evidence-Style Prompt Eval 补全 > POPE/AMBER 小子集 > 10k mixed scale-up。

## 9. 不做的内容

为了保持项目小而有效，主实验阶段暂不加入：

- 多 backbone 对比
- RLAIF 新基线
- 多种 DPO 变体
- box/mask grounding supervision
- 超过三组的主实验表
- SFT、critic rerank、RefCOCO grounding 或 3D transfer

这些内容可以放进 future work 或 limitation，避免正文目标发散。

10k mixed scale-up 是数据规模扩展，不算新增方法组；只有在前述评测不足以支撑论文时启动。
