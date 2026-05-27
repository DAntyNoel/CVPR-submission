# 中期进展报告

更新日期：2026-05-27

## 1. 实验进展

当前项目已从 COCO-only 设定更新为一个仍然小而可控的 mixed COCO/GQA 设定：在 Qwen2.5-VL-7B-Instruct 上比较 Base Instruct、Answer-DPO 和 Evidence-Hint DPO 三组方法，重点验证轻量视觉证据提示是否能减少对象存在、简单属性和简单左右空间关系中的视觉幻觉。

数据侧已经完成 mixed 主训练集构造。当前 `data/processed/canonical_pairs_main.jsonl` 共 5,000 条，其中 3,500 条来自 COCO object existence，1,500 条来自 GQA simple attribute/relation。GQA 部分包括 986 条 color attribute、64 条 material attribute 和 450 条 left/right spatial relation。Answer-DPO 与 Evidence-Hint DPO 仍来自同一份 canonical pairs，只改变 response 中是否加入 evidence hint。`data/processed/check_report_main.json` 显示 0 error、0 warning，训练与评测图片去重检查通过，当前 train/eval image overlap 为 0。mixed audit 已重新汇总，`data/audit/audit_200_summary.json` 中 chosen correctness、rejected wrongness、hint correctness 三项均为 200/200。

训练侧需要区分旧结果和新主实验。Answer-DPO job 64167 与 Evidence-Hint DPO job 64168 已正常结束，它们基于旧 5,000 条 COCO-only 数据，不应放入 mixed 数据论文主表。不过这两组 adapter 仍然有价值，可以作为 COCO-only auxiliary/preliminary result 写入论文补充结果或分析部分，用来展示 evidence hint 在纯对象存在设定下的先行趋势。2026-05-27 mixed LLaMA-Factory 数据已重新导出，两组 mixed DPO 已完成：Answer-DPO job 64200，Evidence-Hint DPO ZeRO-2 job 64252。训练设置保持 LoRA DPO、1 epoch、`pref_beta=0.1`、LoRA rank 16；原 Evidence-Hint ZeRO-3 job 64201 已取消。

评测侧已经完成 COCO held-out、GQA simple、Hard COCO、evidence-style prompt 和 Base-error-mined diagnostic。COCO held-out 上 Base/Answer-DPO/Evidence-Hint DPO Acc 分别为 0.959/0.961/0.961；GQA simple 为 0.764/0.768/0.766；Hard COCO 为 0.944/0.950/0.946。Base-error-mined locked set 上 Answer-DPO recovery 为 0.063，Evidence-Hint DPO recovery 为 0.030。官方 POPE/AMBER 数据当前不在本地，本轮不阻塞主线。

## 2. 预期结论是否正常

当前结果支持诊断型结论，而不是强正向方法结论。Evidence-Hint DPO 在 COCO/Hard COCO/GQA 上只表现出轻微 false-positive 下降，整体 Acc/F1 与 Base-error recovery 未稳定超过 Answer-DPO；refusal 和 other/invalid rate 均未升高，normal prompt 下也没有 literal `Evidence hint` 格式泄漏。论文应明确说明模板化 evidence hint 的当前形式不足以稳定改善小规模 DPO，但提供了一个可复现的 controlled diagnostic setting。

## 3. 论文核心目标是否有变化

核心方法目标没有变化：仍然是不改模型结构、不改 DPO loss、不引入额外 reward model，只通过偏好数据格式加入轻量视觉证据提示。

论文任务范围发生了适度扩展：从旧版 COCO-only object existence 扩展到 5k mixed COCO/GQA，覆盖对象存在、简单颜色/材质属性和左右空间关系。不过这个扩展仍然是小范围的，不应声称覆盖复杂推理、计数、多步关系或开放式描述。主实验仍保持三组，不增加额外方法组。

## 4. 潜在问题和解决方案

1. mixed 数据上的正式主训练与主要评测均已完成。当前状态是 64167/64168 已明确标记为 COCO-only auxiliary/preliminary run，mixed Answer-DPO 64200 和 mixed Evidence-Hint DPO ZeRO-2 64252 是主训练结果。

2. GQA simple held-out eval 已准备完成。后续风险转为评测噪声：如果 GQA eval 噪声较高，主结论按 COCO/POPE 收窄，GQA 作为补充分析。

3. 普通 COCO 和 Hard COCO 都接近 ceiling。解决方案已执行：加入 evidence-style prompt 与 Base-error-mined diagnostic，并在论文中解释这些评测仍未显示稳定正向 Evidence-Hint delta。

4. POPE 或 AMBER 数据准备可能拖慢主表。解决方案是先把 COCO held-out + GQA simple 作为最小主表，POPE 作为强补充；AMBER 只在脚本顺利时加入，不为它扩大实验范围。

5. Evidence-Hint DPO 可能出现推理格式漂移，例如回答中继续输出 evidence hint。解决方案是在评测 prompt 中保持短回答要求，同时统计格式违规率和 refusal rate；若格式漂移严重，在论文中作为失败模式分析。

6. mixed 数据的人审仍需特别关注 GQA 噪声。当前 mixed audit 汇总已通过阈值；论文 limitation 中仍需说明 evidence hint 来自模板和 scene graph，不是独立像素级 grounding。

## 5. 下一步优先级

当前不再重复提交已完成的 COCO/GQA/Hard COCO/evidence-style/base-error-mined 评测。下一步优先级是：编译并检查诊断型论文页数；如需更强结论，再单独决定是否启动 10k mixed scale-up 或准备官方 POPE/AMBER 数据。无论是否扩展，当前论文都应维持三组主实验和 6 页以内的简洁设定。
