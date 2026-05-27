# 中期进展报告

更新日期：2026-05-27

## 1. 实验进展

当前项目已从 COCO-only 设定更新为一个仍然小而可控的 mixed COCO/GQA 设定：在 Qwen2.5-VL-7B-Instruct 上比较 Base Instruct、Answer-DPO 和 Evidence-Hint DPO 三组方法，重点验证轻量视觉证据提示是否能减少对象存在、简单属性和简单左右空间关系中的视觉幻觉。

数据侧已经完成 mixed 主训练集构造。当前 `data/processed/canonical_pairs_main.jsonl` 共 5,000 条，其中 3,500 条来自 COCO object existence，1,500 条来自 GQA simple attribute/relation。GQA 部分包括 986 条 color attribute、64 条 material attribute 和 450 条 left/right spatial relation。Answer-DPO 与 Evidence-Hint DPO 仍来自同一份 canonical pairs，只改变 response 中是否加入 evidence hint。`data/processed/check_report_main.json` 显示 0 error、0 warning，训练与评测图片去重检查通过，当前 train/eval image overlap 为 0。需要注意的是，旧的 `data/audit/audit_summary.md` 仍记录 COCO-only 版本；mixed 版本还需要重新汇总人工抽查，尤其检查 GQA 属性和左右关系噪声。

训练侧需要区分旧结果和新主实验。Answer-DPO job 64167 与 Evidence-Hint DPO job 64168 已正常结束，它们基于旧 5,000 条 COCO-only 数据，不应放入 mixed 数据论文主表。不过这两组 adapter 仍然有价值，可以作为 COCO-only auxiliary/preliminary result 写入论文补充结果或分析部分，用来展示 evidence hint 在纯对象存在设定下的先行趋势。根据更新后的大纲，两组 DPO 仍需要使用 2026-05-27 的 mixed COCO+GQA 数据重新训练，作为最终主表结果。训练设置保持 LoRA DPO、1 epoch、`pref_beta=0.1`、LoRA rank 16。

评测侧已经准备好 1,000 条 COCO held-out object-existence eval，yes/no 各 500 条；统一推理入口、adapter 加载检查和 COCO held-out dry-run 流程已有基础。等待 mixed 数据重新训练期间，可以先把旧 COCO-only adapter 的后续评测跑完，包括 COCO held-out、POPE、refusal rate 和格式违规检查。这些结果可作为额外表格或 appendix 结果，但表头必须标注为 `COCO-only training`。更新后的 mixed 设定还需要补一个 GQA simple held-out eval，优先覆盖 color attribute 与 left/right relation，并与训练 GQA image ids 去重。目前 `results/eval/generations/coco_heldout_object_existence/` 下仍只有旧 dry-run metadata，尚未生成正式推理结果和最终打分表。

## 2. 预期结论是否正常

目前看项目方向正常，但主结论还不能提前确认。数据已经从 COCO-only 扩展到 mixed COCO+GQA，并且自动检查通过；这让论文范围比旧版更完整，但也意味着旧 adapter 不能直接支撑最终主表。旧 COCO-only 结果可以先作为“对象存在子设定”的额外证据，Evidence-Hint DPO 的最终主结论仍必须等待 mixed 数据重训后的 held-out、POPE 和 GQA simple 评测结果。

预期结论更新为：如果 Evidence-Hint DPO 相比 Answer-DPO 在 POPE/COCO object existence 或 GQA simple attribute/relation 上有稳定提升，同时 refusal rate 没有明显升高，就可以支持“轻量 evidence hint 有助于回答级 DPO 学到更强视觉依据”的基础结论。如果收益只出现在 COCO 而不出现在 GQA，则正文应把结论收窄为对象存在类幻觉；如果整体提升不明显，也可以改写为可复现的负结果或诊断性结论。

## 3. 论文核心目标是否有变化

核心方法目标没有变化：仍然是不改模型结构、不改 DPO loss、不引入额外 reward model，只通过偏好数据格式加入轻量视觉证据提示。

论文任务范围发生了适度扩展：从旧版 COCO-only object existence 扩展到 5k mixed COCO/GQA，覆盖对象存在、简单颜色/材质属性和左右空间关系。不过这个扩展仍然是小范围的，不应声称覆盖复杂推理、计数、多步关系或开放式描述。主实验仍保持三组，不增加额外方法组。

## 4. 潜在问题和解决方案

1. mixed 数据上的正式主训练尚未完成。解决方案是把 64167/64168 明确标记为 COCO-only auxiliary/preliminary run，然后基于当前 mixed `answer_dpo_train.jsonl` 和 `evidence_hint_dpo_train.jsonl` 重新跑 Answer-DPO 与 Evidence-Hint DPO。

2. GQA simple held-out eval 尚未准备完成。解决方案是优先抽取 500-1,000 条 color/left-right 样本，保证与训练 GQA image ids 去重；如果 GQA eval 噪声较高，主结论按 COCO/POPE 收窄，GQA 作为补充分析。

3. 等待 mixed 重训期间可能出现空档。解决方案是先跑旧 COCO-only adapter 的 COCO held-out/POPE/refusal 评测，把结果作为额外结果保存；这些结果只和 COCO-only 训练设定对应，不与 mixed 主表直接混写。

4. POPE 或 AMBER 数据准备可能拖慢主表。解决方案是先把 COCO held-out + GQA simple 作为最小主表，POPE 作为强补充；AMBER 只在脚本顺利时加入，不为它扩大实验范围。

5. Evidence-Hint DPO 可能出现推理格式漂移，例如回答中继续输出 evidence hint。解决方案是在评测 prompt 中保持短回答要求，同时统计格式违规率和 refusal rate；若格式漂移严重，在论文中作为失败模式分析。

6. mixed 数据的人审仍需特别关注 GQA 噪声。解决方案是重新汇总 mixed audit 的 chosen correctness、rejected wrongness 和 hint correctness；论文 limitation 中说明 evidence hint 来自模板和 scene graph，不是独立像素级 grounding。

## 5. 下一步优先级

下一步最重要的是一边启动 mixed 数据重训，一边利用等待时间拿到旧 COCO-only adapter 的额外评测结果。推荐顺序是：先跑旧 COCO-only Answer-DPO/Evidence-Hint DPO 的 COCO held-out/POPE/refusal 评测并保存为 auxiliary result；同时重训 mixed Answer-DPO 和 mixed Evidence-Hint DPO；随后准备 GQA simple held-out eval，跑 Base/mixed Answer-DPO/mixed Evidence-Hint DPO，生成 POPE/COCO/GQA/refusal 主表指标。无论结果强弱，当前论文都应维持三组主实验和 6 页以内的简洁设定。
